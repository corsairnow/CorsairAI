import os
from typing import Any, Dict, List, Set, Tuple
import yaml

class SchemaRegistry:
    def __init__(self, path: str):
        self.path = path
        self._mtime = 0.0
        self._data: Dict[str, Any] = {}
        self._tables: Set[str] = set()
        self._joins: List[Tuple[str, str]] = []
        self._dialect = "mysql"
        self._timezone = "UTC"
        self.reload_if_changed(force=True)

    @property
    def dialect(self) -> str:
        return self._dialect

    @property
    def timezone(self) -> str:
        return self._timezone

    @property
    def tables(self) -> Set[str]:
        return self._tables

    def reload_if_changed(self, force: bool = False) -> None:
        try:
            mtime = os.path.getmtime(self.path)
        except FileNotFoundError:
            return
        if force or mtime != self._mtime:
            with open(self.path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._data = data
            self._mtime = mtime
            self._dialect = str(data.get("dialect", "mysql")).lower()
            self._timezone = str(data.get("timezone", "UTC"))
            self._tables = {t.get("name") for t in data.get("tables", []) if t.get("name")}
            self._joins = []
            for j in data.get("joins", []):
                left = j.get("left")
                right = j.get("right")
                if left and right:
                    self._joins.append((left, right))

    def render_for_prompt(self) -> str:
    
        lines: List[str] = [
            f"dialect: {self._dialect}",
            f"timezone: {self._timezone}",
            "tables:",
        ]

        for t in self._data.get("tables", []):
            name = t.get("name")
            cols = t.get("columns", [])
            desc = t.get("description")  # optional table-level description
            col_desc = t.get("columns_description", {})  # optional dict

            if not name:
                continue

            # Always keep the single-line columns output
            joined_cols = ", ".join(cols)
            lines.append(f"  - {name}({joined_cols})")

            # Add table description if provided
            if desc:
                lines.append(f"    # {desc}")

            # Add each column description if present
            if isinstance(col_desc, dict):
                for col_name, col_text in col_desc.items():
                    safe_text = str(col_text).replace("\n", " ")  # remove any hard line breaks
                    lines.append(f"    # {col_name}: {safe_text}")

        if self._joins:
            lines.append("joins:")
            for left, right in self._joins:
                lines.append(f"  - {left} = {right}")

        return "\n".join(lines)
