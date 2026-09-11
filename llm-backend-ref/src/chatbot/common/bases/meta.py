from __future__ import annotations

import threading


class SingletonMeta(type):
    """Thread-safe metaclass for singleton"""

    _instances: dict = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]

    def clear(cls):
        with cls._lock:
            _ = cls._instances.pop(cls, None)
