import asyncio

from typing import Optional, Callable
from dataclasses import dataclass
from amiyabot.signalHandler import SignalHandler

from .scheduler import scheduler


@dataclass
class Task:
    func: Callable
    each: Optional[int]
    tag: str
    sub_tag: str
    run_when_added: bool
    kwargs: dict


class TasksControl:
    @classmethod
    def start(cls):
        if not scheduler.state:
            scheduler.start()
            SignalHandler.on_shutdown.append(scheduler.shutdown)

    @classmethod
    def add_timed_task(cls, task: Task):
        if task.run_when_added:
            asyncio.create_task(task.func())

        if task.each is not None:
            scheduler.add_job(
                task.func,
                id=f'{task.tag}.{task.sub_tag}',
                trigger='interval',
                seconds=task.each,
                **task.kwargs,
            )
        else:
            scheduler.add_job(
                task.func,
                id=f'{task.tag}.{task.sub_tag}',
                **task.kwargs,
            )

    @classmethod
    def remove_task(cls, tag: str, sub_tag: Optional[str] = None):
        for job in scheduler.get_jobs():
            job_id: str = job.id

            if sub_tag:
                if job_id.startswith(f'{tag}.{sub_tag}'):
                    job.remove()
            else:
                if job_id.startswith(tag):
                    job.remove()
