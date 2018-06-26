from datetime import datetime, timezone
import inspect


def time_in_millis_utc():
    return datetime.utcnow().replace(tzinfo=timezone.utc).timestamp() * 1000


def whos_calling(msg):
    frm = inspect.stack()[1]
    mod = inspect.getmodule(frm[0])
    return '[Called from %s] %s' % (mod.__name__, msg)
