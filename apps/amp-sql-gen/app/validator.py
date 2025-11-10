from typing import Dict, Any, Set
import sqlglot
from sqlglot import exp

def _get_tables(expr: exp.Expression) -> Set[str]:
    tables = set()
    for t in expr.find_all(exp.Table):
        if t.this:
            tables.add(t.this.name.lower())
    return tables

def _has_select_star(expr: exp.Expression) -> bool:
    return any(isinstance(node, exp.Star) for node in expr.find_all(exp.Star))

def _get_limit_value(expr: exp.Expression):
    limit = expr.args.get("limit")
    if isinstance(limit, exp.Limit):
        value = limit.expression
        try:
            return int(value.this) if value is not None else None
        except Exception:
            return None
    return None

def validate_sql(sql: str, dialect: str, allowed_tables: Set[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "parse_ok": False,
        "select_only": False,
        "no_star": False,
        "limit_ok": False,
        "tables_ok": False,
        "tables_used": [],
    }
    try:
        read = {"postgres":"postgres", "postgresql":"postgres", "mysql":"mysql"}.get(dialect, None)
        expr = sqlglot.parse_one(sql, read=read)
        out["parse_ok"] = True
    except Exception:
        return out

    out["select_only"] = isinstance(expr, (exp.Select, exp.Subquery, exp.Union))
    out["no_star"] = not _has_select_star(expr)
    limit_val = _get_limit_value(expr)
    out["limit_ok"] = (isinstance(limit_val, int))
    used_tables = {t.lower() for t in _get_tables(expr)}
    out["tables_used"] = sorted(used_tables)
    out["tables_ok"] = used_tables.issubset({t.lower() for t in allowed_tables})
    return out