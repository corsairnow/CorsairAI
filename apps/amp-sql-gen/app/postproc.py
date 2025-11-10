import re
from html import unescape

SQL_TAG_RE = re.compile(r"<SQL>\s*(.*?)\s*</SQL>", re.IGNORECASE | re.DOTALL)
FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)

def extract_sql(text: str) -> str:
    """
    Try hard to extract a single SQL statement from a chatty model output.
    Preference order: <SQL>...</SQL>, then ```sql fences```, then first SELECT/WITH; trim to first semicolon.
    """
    if not text:
        return ""

    s = unescape(text)

    m = SQL_TAG_RE.search(s)
    if m:
        return m.group(1).strip()

    m = FENCE_RE.search(s)
    if m:
        return m.group(1).strip()

    # strip HTML/markdown tags
    no_tags = re.sub(r"<[^>]+>", " ", s)

    # find the first SELECT/WITH statement that ends with a semicolon
    m = re.search(r"(?is)\b(SELECT|WITH)\b.*?;", no_tags)
    if m:
        return m.group(0).strip()

    return s.strip()
