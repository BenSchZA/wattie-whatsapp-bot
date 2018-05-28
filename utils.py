from datetime import datetime, timezone


def time_in_millis_utc():
    return datetime.utcnow().replace(tzinfo=timezone.utc).timestamp() * 1000
