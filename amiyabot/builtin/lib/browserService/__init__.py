from playwright.async_api import async_playwright, ConsoleMessage, Error as PageError

from .launchConfig import *
from .pagePool import *
from .pageContext import PageContext


class BrowserService:
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Union[Browser, BrowserContext]] = None
        self.config: Optional[BrowserLaunchConfig] = None
        self.pool: Optional[PagePool] = None

        self.launched = False

    def __str__(self):
        return self.config.name if self.config else 'Not Launched'

    async def launch(self, config: BrowserLaunchConfig):
        if self.launched:
            return None

        self.launched = True

        log.info('launching browser...')

        self.playwright = await async_playwright().start()
        self.browser = await config.launch_browser(self.playwright)
        self.config = config

        if self.config.page_pool_size:
            self.pool = PagePool(self.browser, config)

        # if not config.browser_name:
        #     config.browser_name = self.browser._impl_obj._browser_type.name

        log.info(f'{self} launched successful.')

    async def close(self):
        await self.browser.close()
        await self.playwright.stop()

        log.info(f'{self} closed.')

    async def open_page(self, width: int, height: int):
        if self.browser:
            size = ViewportSize(width=width, height=height)

            if self.pool:
                page_context = await self.pool.acquire_page(size)
            else:
                page_context = PageContext(
                    await self.browser.new_page(no_viewport=True, viewport=size),
                )

            if self.config.debug:
                page_context.page.once('console', self.__console)
                page_context.page.once('pageerror', self.__page_error)

            hook_res = await self.config.on_page_created(page_context.page)
            if hook_res:
                page_context.page = hook_res

            return page_context

    @staticmethod
    async def __console(message: ConsoleMessage):
        text = f'console: {message.text}' + '\n    at {url}:{lineNumber}:{columnNumber}'.format(**message.location)

        if message.type == 'warning':
            log.warning(text)
        elif message.type == 'error':
            log.error(text)
        else:
            log.info(text)

    @staticmethod
    async def __page_error(error: PageError):
        log.error(error.stack)


basic_browser_service = BrowserService()
