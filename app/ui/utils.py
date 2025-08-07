from datetime import datetime

def format_timestamp(ts_str: str) -> str:
    """Formats an ISO 8601 timestamp into a user-friendly string."""
    if not ts_str:
        return "N/A"
    try:
        # Parse the timestamp, handling potential timezone offsets
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return ts.strftime("%b %d, %Y at %I:%M %p %Z")
    except (ValueError, TypeError):
        return "Invalid Date"
