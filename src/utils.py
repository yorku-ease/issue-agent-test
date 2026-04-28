import re
import time
import functools


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
