from typing import Optional, Callable
from amiyabot.network.httpServer import ServerEventHandler

from .scheduler import scheduler


class TasksControl:
    @classmethod
    def start(cls):
        if not scheduler.state:
            scheduler.start()
            ServerEventHandler.on_shutdown.append(scheduler.shutdown)

    @classmethod
    def add_timed_task(
        cls, task: Callable, each: Optional[int] = None, tag: str = '__default__', sub_tag: str = '__sub__', **kwargs
    ):
        """
        注册定时任务

        :param task:    任务函数
        :param each:    循环执行间隔时间，单位（秒）
        :param tag:     标签
        :param sub_tag: 子标签
        :param kwargs:  scheduler.add_job 参数
        :return:
        """
        if each:
            scheduler.add_job(task, id=f'{tag}.{sub_tag}', trigger='interval', seconds=each, **kwargs)
        else:
            scheduler.add_job(task, id=f'{tag}.{sub_tag}', **kwargs)

    @classmethod
    def remove_tag(cls, tag: str, sub_tag: Optional[str] = None):
        """
        取消定时任务

        :param tag:     标签
        :param sub_tag: 子标签
        :return:
        """
        for job in scheduler.get_jobs():
            job_id: str = job.id

            if sub_tag:
                if job_id.startswith(f'{tag}.{sub_tag}'):
                    job.remove()
            else:
                if job_id.startswith(tag):
                    job.remove()
