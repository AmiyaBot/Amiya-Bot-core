import os
import sys
import asyncio
import inspect
import importlib

from typing import Callable
from functools import partial
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor


executor = ThreadPoolExecutor(min(32, (os.cpu_count() or 1) + 4))


class Singleton(type):
    instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.instances:
            cls.instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.instances[cls]


async def run_in_thread_pool(block_func: Callable, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, partial(block_func, *args, **kwargs))


@contextmanager
def temp_sys_path(path: str):
    sys.path.insert(0, path)
    yield
    sys.path.remove(path)


def import_module(path: str, self_only: bool = True):
    if path in sys.modules:
        module = sys.modules[path]

        def reload_submodules(parent):
            for attr in [n for n in dir(parent) if not n.startswith('__')]:
                submodule = getattr(parent, attr)

                if inspect.ismodule(submodule):
                    if self_only and path not in submodule.__name__:
                        continue

                    reload_submodules(submodule)
                    importlib.reload(submodule)

        reload_submodules(module)

        return importlib.reload(module)

    return importlib.import_module(path)


def delete_module(module_name: str):
    if module_name in sys.modules:
        to_delete = [module_name]

        for name in sys.modules:
            if name.startswith(module_name + '.'):
                to_delete.append(name)

        for name in to_delete:
            del sys.modules[name]


def append_sys_path(path: str):
    if path not in sys.path:
        sys.path.append(path)


def argv(name: str, formatter: Callable = str):
    key = f'--{name}'
    if key in sys.argv:
        index = sys.argv.index(key) + 1

        if index >= len(sys.argv):
            return True

        if sys.argv[index].startswith('--'):
            return True

        return formatter(sys.argv[index])
    return formatter()
