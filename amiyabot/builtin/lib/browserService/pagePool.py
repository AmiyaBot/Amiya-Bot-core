import asyncio

from playwright.async_api import ViewportSize
from contextlib import asynccontextmanager

from .launchConfig import *


class PagePool:
    def __init__(self, browser: Union[Browser, BrowserContext], config: BrowserLaunchConfig):
        self.config = config
        self.browser = browser

        self.queue = asyncio.Queue()
        self.pages = []

        self.queuing_num = 0

    @property
    def size(self):
        return len(self.pages)

    @property
    def max_size(self):
        return self.config.page_pool_size

    @property
    def queue_size(self):
        return self.queue.qsize()

    @asynccontextmanager
    async def __queuing(self):
        self.queuing_num += 1
        yield
        self.queuing_num -= 1

    async def acquire_page(self, viewport_size: ViewportSize):
        log.debug(
            f'{self.config.name} -- idle pages: {self.queue_size} opened: {self.size} queuing: {self.queuing_num}'
        )

        if self.queue_size == 0 and self.size < self.max_size:
            if isinstance(self.browser, BrowserContext):
                page = await self.browser.new_page()
            else:
                context = await self.browser.new_context(no_viewport=True)
                hook_res = await self.config.on_context_created(context)
                if hook_res:
                    context = hook_res

                page = await context.new_page()

            self.pages.append(page)

            log.debug(f'{self.config.name} -- page created. curr size: {self.size}/{self.max_size}')
        else:
            async with self.__queuing():
                page: Page = await self.queue.get()

        try:
            await page.set_viewport_size(viewport_size)
        except Exception as e:
            log.error(e)

        return PagePoolContext(self, page)

    async def release_page(self, page: Page):
        await page.context.clear_cookies()
        await page.evaluate(
            '''
            localStorage.clear();
            sessionStorage.clear();
            '''
        )
        await page.goto('about:blank')
        await self.queue.put(page)

        log.debug(f'{self.config.name} -- page released. idle pages: {self.queue_size}')


class PagePoolContext:
    def __init__(self, pool: PagePool, page: Page):
        self.pool = pool
        self.page = page

    async def __aenter__(self):
        return self.page

    async def __aexit__(self, *args, **kwargs):
        await self.pool.release_page(self.page)
