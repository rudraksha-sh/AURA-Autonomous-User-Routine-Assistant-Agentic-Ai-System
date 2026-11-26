import time
from collections import OrderedDict, deque
from threading import Lock


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int, *, max_keys: int = 16_384):
        if max_requests <= 0:
            raise ValueError("max_requests must be greater than 0")

        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than 0")

        if max_keys <= 0:
            raise ValueError("max_keys must be greater than 0")
        self.max_keys = max_keys
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        with self._lock:
            now = time.monotonic()
            window_start = now - self.window_seconds
            while self._requests:
                oldest = next(iter(self._requests.values()))
                if oldest[-1] > window_start:
                    break
                self._requests.popitem(last=False)

            timestamps = self._requests.get(key)
            if timestamps is None:
                if len(self._requests) >= self.max_keys:
                    return False
                timestamps = self._requests[key] = deque()
            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()
            if len(timestamps) >= self.max_requests:
                return False
            timestamps.append(now)
            self._requests.move_to_end(key)
            return True

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()