import sys
import traceback

from typing import Any
from functools import wraps


class Helper:
    @classmethod
    def record(cls, func) -> Any:
        @wraps(func)
        def decorated(*args, **kwargs):
            if not hasattr(sys, 'frozen'):
                trace = traceback.extract_stack()[-2]

            return func(*args, **kwargs)

        return decorated
