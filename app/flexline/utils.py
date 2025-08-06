import re


def generate_count_query(original_query: str) -> str:
    """
    Wraps a given SQL Server query to produce a COUNT(*) version of it,
    correctly handling:
      1) Leading CTEs (WITH ... AS (...), ...)
      2) Trailing ORDER BY clauses (which are not allowed inside subqueries)
      3) A final semicolon

    Args:
        original_query: The full SQL Server query you want to count rows for.

    Returns:
        A new SQL query string which, when executed, returns the total row
        count of the original query.
    """
    # 1) Clean up
    q = original_query.strip()
    if q.endswith(";"):
        q = q[:-1]

    # 2) Extract any leading CTE block
    cte_block = ""
    main_sql = q
    if re.match(r"^\s*WITH\b", q, re.IGNORECASE):
        # Find the SELECT that starts the main query (i.e. the one after all CTEs)
        # We look for the first occurrence of “) SELECT” (parenthesis that closes
        # the last CTE definition, followed by the main SELECT).
        m = re.search(r"\)\s*SELECT", q, flags=re.IGNORECASE)
        if m:
            # split point is just before that SELECT
            split_pos = m.start() + 1
            cte_block = q[:split_pos].rstrip()
            main_sql = q[split_pos:].lstrip()

    # 3) Remove trailing ORDER BY from the main SQL
    #    This regex will drop any "ORDER BY ... [LIMIT/OFFSET]?" at the very end.
    main_sql = re.sub(
        r"\bORDER\s+BY\b[\s\S]*$", "", main_sql, flags=re.IGNORECASE
    ).rstrip()

    # 4) Build the final COUNT query
    wrapped = f"SELECT COUNT(*) AS total_rows FROM (\n    {main_sql}\n) AS subq"
    if cte_block:
        return f"{cte_block}\n{wrapped};"
    else:
        return wrapped + ";"
