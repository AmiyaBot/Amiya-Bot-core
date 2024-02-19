from playwright.async_api import Page


class PageContext:
    def __init__(self, page: Page):
        self.page = page

    async def __aenter__(self):
        return self.page

    async def __aexit__(self, *args, **kwargs):
        await self.page.close()
