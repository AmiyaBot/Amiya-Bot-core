import asyncio

from typing import Coroutine, Callable, Any, List, Dict
from amiyabot.network.httpServer import ServerEventHandler
from amiyabot.util import Singleton
from amiyabot import log

TASK_CORO = Callable[[], Coroutine[Any, Any, None]]
CUSTOM_CHECK = Callable[[int], Coroutine[Any, Any, bool]]


class TimedTask:
    def __init__(self, task: TASK_CORO, each: int = None, custom: CUSTOM_CHECK = None):
        self.task = task
        self.each = each
        self.custom = custom

    async def check(self, t) -> bool:
        if self.custom:
            return await self.custom(t)
        if self.each:
            return t >= self.each and t % self.each == 0
        return False


class TasksControl(metaclass=Singleton):
    def __init__(self):
        self.alive = True
        self.start = False

        self._timed_tasks: Dict[str, List[TimedTask]] = dict()

        ServerEventHandler.on_shutdown.append(self.stop)

    async def run_tasks(self, step: int = 1, max_step: int = 31536000):
        if self.start:
            return None

        self.start = True
        try:
            t = 0
            while self.alive:
                await asyncio.sleep(step)

                t += step
                if t > max_step:
                    t = 0

                if not self._timed_tasks:
                    continue

                for tag, tasks in self._timed_tasks.items():
                    for task in tasks:
                        if await task.check(t):
                            async with log.catch('TimedTask Error:'):
                                await task.task()

        except KeyboardInterrupt:
            pass

    def timed_task(self, each: int = None, custom: CUSTOM_CHECK = None, tag: str = 'no_tag'):
        """
        注册定时任务
        非严格定时，因为执行协程会产生切换的耗时。所以此注册器定义的循环时间为"约等于"。

        :param each:     循环执行间隔时间，单位（秒）
        :param custom:   自定义循环规则
        :param tag:      标签
        :return:
        """

        def register(task: TASK_CORO):
            if tag not in self._timed_tasks:
                self._timed_tasks[tag] = []

            self._timed_tasks[tag].append(TimedTask(task, each, custom))

        return register

    def remove_tag(self, tag: str):
        if tag in self._timed_tasks:
            del self._timed_tasks[tag]

    def stop(self):
        self.alive = False


tasks_control = TasksControl()
