import os
import json

from typing import Optional, Union
from playwright.async_api import Browser, BrowserType, Page, ViewportSize, Playwright, async_playwright
from amiyabot import log


class BrowserLaunchConfig:
    def __init__(self):
        self.browser_type: str = 'chromium'
        self.debug: bool = False

    async def launch_browser(self, playwright: Playwright):
        browser: BrowserType = getattr(playwright, self.browser_type)

        return await browser.launch(headless=not self.debug)


class BrowserService:
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None

        self.launched = False

    async def launch(self, config: BrowserLaunchConfig):
        if self.launched:
            return None
        self.launched = True

        log.info(f'launching browser...')

        self.playwright = await async_playwright().start()
        self.browser = await config.launch_browser(self.playwright)

        log.info(f'browser({self.browser._impl_obj._browser_type.name}) launched successful.')

    async def close(self):
        await self.browser.close()
        await self.playwright.stop()
        log.info('browser closed.')

    async def open_page(self, url: str, width: int, height: int, is_file: bool = False):
        if self.browser:
            page = await self.browser.new_page(no_viewport=True, viewport=ViewportSize(width=width, height=height))

            if is_file:
                url = 'file:///' + os.path.abspath(url)

            try:
                await page.goto(url)
                await page.wait_for_load_state()
            except Exception as e:
                log.critical(e)
                await page.close()
                return None

            return PageController(page)


class PageController:
    def __init__(self, page: Page):
        self.page = page

    async def init_data(self, data: Union[dict, list]):
        await self.page.evaluate(f'init({json.dumps(data)})')

    async def make_image(self):
        return await self.page.screenshot(full_page=True)

    async def close(self):
        await self.page.close()


basic_browser_service = BrowserService()
