from fastapi import FastAPI
from playwright.async_api import async_playwright
import asyncio
import base64

app = FastAPI()


async def capture_scribd_screenshots(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )

        page = await browser.new_page(viewport={"width": 1200, "height": 1600})
        await page.goto(url, wait_until="networkidle")

        # hide toolbar
        await page.evaluate("""
            () => {
                const t = document.querySelector('[data-testid="sticky-wrapper"]');
                if (t) t.style.display = "none";
            }
        """)

        result = {}
        page_number = 1

        while True:
            element_id = f"page{page_number}"

            exists = await page.evaluate(
                f"() => document.getElementById('{element_id}') !== null"
            )

            if not exists:
                break

            await page.evaluate(
                f"() => document.getElementById('{element_id}').scrollIntoView()"
            )

            await asyncio.sleep(0.5)

            element = await page.query_selector(f"#{element_id}")
            if element:
                img_bytes = await element.screenshot()
                result[page_number] = (
                    "data:image/png;base64," + base64.b64encode(img_bytes).decode()
                )

            page_number += 1

        await browser.close()
        return result


@app.get("/screenshots")
async def screenshots(url: str):
    return await capture_scribd_screenshots(url)
