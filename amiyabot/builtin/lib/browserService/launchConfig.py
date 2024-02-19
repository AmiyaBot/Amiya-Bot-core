from typing import Union, Optional
from playwright.async_api import Browser, BrowserType, BrowserContext, Page, Playwright
from amiyabot.util import argv
from amiyabot.log import LoggerManager

DEFAULT_WIDTH = argv('browser-width', int) or 1280
DEFAULT_HEIGHT = argv('browser-height', int) or 720
DEFAULT_RENDER_TIME = argv('browser-render-time', int) or 200
BROWSER_PAGE_POOL_SIZE = argv('browser-page-pool-size', int) or 0
BROWSER_LAUNCH_WITH_HEADED = argv('browser-launch-with-headed', bool)

log = LoggerManager('Browser')


class BrowserLaunchConfig:
    def __init__(self):
        self.browser_type: str = 'chromium'
        self.browser_name: [Optional] = None
        self.page_pool_size: int = BROWSER_PAGE_POOL_SIZE
        self.debug: bool = argv('debug', bool)

    @property
    def name(self):
        return f'browser({self.browser_name or self.browser_type})'

    async def launch_browser(self, playwright: Playwright) -> Union[Browser, BrowserContext]:
        browser: BrowserType = getattr(playwright, self.browser_type)

        return await browser.launch(headless=not BROWSER_LAUNCH_WITH_HEADED)

    async def on_context_created(self, context: BrowserContext) -> Optional[BrowserContext]:
        ...

    async def on_page_created(self, page: Page) -> Optional[Page]:
        ...
