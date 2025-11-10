import re

JOIN_KEYWORDS = r'(?:LEFT|RIGHT|INNER|OUTER|CROSS)?\s*JOIN'

# Pattern to match a single JOIN clause (non-greedy), stops when next JOIN keyword occurs or end of string.
_join_clause_pattern = re.compile(
    rf'(?is)\b{JOIN_KEYWORDS}\b.*?(?=(?:\b{JOIN_KEYWORDS}\b)|$)'
)

def move_joins_before_where(sql: str) -> str:
    """
    Move any JOIN clauses appearing after WHERE up above the WHERE clause.
    Preserves exact JOIN clause text and order. Avoids duplicating joins already present before WHERE.
    Returns corrected SQL (with a trailing semicolon).
    """
    if not sql:
        return sql

    # Normalize whitespace at ends, keep interior whitespace
    sql = sql.strip()
    # Remove trailing semicolon temporarily
    has_semicolon = sql.endswith(';')
    if has_semicolon:
        sql = sql[:-1].rstrip()

    # Find first top-level WHERE (case-insensitive)
    where_match = re.search(r'(?i)\bWHERE\b', sql)
    if not where_match:
        # No WHERE — nothing to do
        return (sql + ';') if has_semicolon else sql + ';'

    where_pos = where_match.start()
    before_where = sql[:where_pos].rstrip()
    after_where = sql[where_pos:].lstrip()  # includes the WHERE token

    # Search for join clauses in the after_where part
    joins_after = _join_clause_pattern.findall(after_where)
    print(joins_after)
    if not joins_after:
        # no misplaced joins
        return (sql + ';') if has_semicolon else sql + ';'

    # Build a set of normalized join texts already present before WHERE to avoid duplicates
    # Normalization: collapse whitespace and lowercase
    def normalize(s: str) -> str:
        return re.sub(r'\s+', ' ', s).strip().lower()

    existing_joins_before = []
    # find joins present in before_where (so we don't add duplicates)
    for m in _join_clause_pattern.finditer(before_where):
        existing_joins_before.append(normalize(m.group(0)))

    moved = []
    cleaned_after = after_where
    for join_text in joins_after:
        norm = normalize(join_text)
        # Remove only the first occurrence of this exact text in the after_where string
        # Use re.escape to match exact text (but ignore case/whitespace differences)
        # We'll remove by searching for the original text (as found)
        if norm not in existing_joins_before and norm not in [normalize(j) for j in moved]:
            moved.append(join_text.strip())
        # remove the occurrence from cleaned_after (first occurrence)
        cleaned_after = cleaned_after.replace(join_text, '', 1)

    # If no unique joins to move, still clean duplicates that were after WHERE
    cleaned_after = re.sub(r'\s+', ' ', cleaned_after).strip()
    # Reconstruct: put moved joins after the FROM/user_payran block (i.e., appended after before_where)
    insertion = ' '.join(moved)
    if insertion:
        # ensure before_where ends with a newline
        corrected = before_where.rstrip() + ' ' + insertion + ' ' + cleaned_after
    else:
        corrected = before_where + ' ' + cleaned_after

    # Clean multiple spaces/newlines and format WHERE line nicely
    corrected = re.sub(r'\n\s*\n+', ' ', corrected).strip()
    # Ensure it ends with semicolon
    corrected = corrected + (';' if has_semicolon else ';')
    return corrected
