from datetime import datetime, timezone
import inspect

MILLIS_1_HOUR = 3600000
MILLIS_24_HOURS = 86400000


def time_in_millis_utc():
    return datetime.utcnow().replace(tzinfo=timezone.utc).timestamp() * 1000


def whos_calling(msg):
    frm = inspect.stack()[1]
    mod = inspect.getmodule(frm[0])
    return '[Called from %s] %s' % (mod.__name__, msg)


def generator_len(gen):
    return sum(1 for _ in gen)
