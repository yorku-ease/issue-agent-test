import re
import time
import functools
from collections import defaultdict

_rate_limit_store: dict = defaultdict(list)


def retry(times=3, delay=1):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(times):
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    if attempt == times - 1:
                        raise
                    time.sleep(delay)
        return wrapper
    return decorator


def paginate(items: list, page: int, per_page: int = 10) -> dict:
    start = page * per_page
    end = start + per_page
    return {
        "items": items[start:end],
        "page": page,
        "total": len(items),
        "pages": (len(items) + per_page - 1) // per_page,
    }


def sanitize_string(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[\x00-\x1f\x7f]", "", value)
    value = re.sub(r" +", " ", value)
    return value


def is_rate_limited(key: str, max_calls: int = 10, window_seconds: int = 60) -> bool:
    now = time.time()
    timestamps = _rate_limit_store[key]
    _rate_limit_store[key] = [t for t in timestamps if now - t < window_seconds]
    if len(_rate_limit_store[key]) >= max_calls:
        return True
    _rate_limit_store[key].append(now)
    return False
