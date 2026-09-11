from __future__ import annotations

import json
import time
from functools import lru_cache
from functools import wraps

from common.logs import get_logger
from common.settings import Settings


@lru_cache
def get_settings():
    return Settings()  # type: ignore


def load_json_file(path) -> dict:
    """
    Load and return the contents of a JSON file as a dictionary.

    Args:
        path (str): The file path to the JSON file to be loaded.

    Returns:
        dict: The contents of the JSON file as a Python dictionary.
    """
    with open(path, encoding='utf-8') as file:
        # Load the dictionary from the JSON file
        dict_output = json.load(file)
    return dict_output


def profile(func):
    """Decorator to profile execution time. Using default logger with info level\n
    Output: [module.function] executed in: 0.0s
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        logger = get_logger('profiler')
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        logger.info(
            f'[{func.__module__}.{func.__name__}] executed in: {end_time - start_time}s',
        )

        if hasattr(result, 'processing_time'):
            setattr(result, 'processing_time', end_time - start_time)

        return result

    return wrapper


settings = get_settings()