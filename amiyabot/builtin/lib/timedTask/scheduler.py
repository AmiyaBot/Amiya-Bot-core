from amiyabot.log import LoggerManager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import *

log = LoggerManager('Schedule')


class Scheduler(AsyncIOScheduler):
    options = {
        'executors': {
            'default': AsyncIOExecutor(),
        },
        'job_defaults': {
            'coalesce': False,
            'max_instances': 1,
        },
    }

    def event_listener(self, mask):
        def register(task):
            self.add_listener(task, mask)
            return task

        return register


scheduler = Scheduler(**Scheduler.options)


@scheduler.event_listener(mask=EVENT_JOB_ADDED)
def _(event: JobEvent):
    log.debug(f'added timed task: {event.job_id}')


@scheduler.event_listener(mask=EVENT_JOB_REMOVED)
def _(event: JobEvent):
    log.debug(f'removed timed task: {event.job_id}')


@scheduler.event_listener(mask=EVENT_JOB_EXECUTED)
def _(event: JobExecutionEvent):
    log.debug(f'timed task executed: {event.job_id}')
