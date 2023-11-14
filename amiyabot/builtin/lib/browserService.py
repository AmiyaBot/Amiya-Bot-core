import os

from typing import Optional, Union
from amiyabot.log import LoggerManager
from amiyabot.util import argv
from playwright.async_api import (
    async_playwright,
    Page,
    Browser,
    BrowserType,
    BrowserContext,
    ViewportSize,
    Playwright,
    ConsoleMessage,
    Error as PageError,
)

log = LoggerManager('Browser')

DEFAULT_WIDTH = argv('browser-width', int) or 1280
DEFAULT_HEIGHT = argv('browser-height', int) or 720
DEFAULT_RENDER_TIME = argv('browser-render-time', int) or 200
BROWSER_PAGE_NOT_CLOSE = argv('browser-page-not-close', bool)
BROWSER_LAUNCH_WITH_HEADED = argv('browser-launch-with-headed', bool)


class BrowserLaunchConfig:
    def __init__(self):
        self.browser_type: str = 'chromium'
        self.debug: bool = argv('debug', bool)

    async def launch_browser(self, playwright: Playwright) -> Union[Browser, BrowserContext]:
        browser: BrowserType = getattr(playwright, self.browser_type)

        return await browser.launch(headless=not BROWSER_LAUNCH_WITH_HEADED)

    async def new_page(self, browser: Union[Browser, BrowserContext], viewport_size: ViewportSize) -> Page:
        return await browser.new_page(no_viewport=True, viewport=viewport_size)


class BrowserService:
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Union[Browser, BrowserContext]] = None

        self._launched = False
        self._launch_config: Optional[BrowserLaunchConfig] = None
        self._type = 'unknown'

    def __str__(self):
        return f'browser({self._type})'

    async def launch(self, config: BrowserLaunchConfig):
        if self._launched:
            return None

        self._launched = True
        self._launch_config = config

        log.info('launching browser...')

        self.playwright = await async_playwright().start()
        self.browser = await config.launch_browser(self.playwright)

        self._type = self.browser._impl_obj._browser_type.name

        log.info(f'{self} launched successful.')

    async def close(self):
        await self.browser.close()
        await self.playwright.stop()
        log.info(f'{self} closed.')

    async def open_page(self, url: str, width: int, height: int, is_file: bool = False):
        if self.browser:
            page = await self._launch_config.new_page(self.browser, ViewportSize(width=width, height=height))

            if self._launch_config.debug:
                page.on('console', self.__console)
                page.on('pageerror', self.__page_error)

            if is_file:
                url = 'file:///' + os.path.abspath(url)

            try:
                await page.goto(url)
                await page.wait_for_load_state()
            except Exception as e:
                log.critical(e)
                await page.close()
                return None

            return page

    @staticmethod
    async def __console(message: ConsoleMessage):
        text = message.text + '\n    at {url}:{lineNumber}:{columnNumber}'.format(**message.location)

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
