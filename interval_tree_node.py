def _java_div(a, b):
    """Integer division that truncates toward zero (exactly like Java's '/')."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q
