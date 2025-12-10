from fastapi import FastAPI
from playwright.async_api import async_playwright
import tempfile
import base64
import asyncio
import os

app = FastAPI()


async def capture_scribd_screenshots(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ])
        page = await browser.new_page(viewport={"width": 1200, "height": 1600})
        await page.goto(url, wait_until="networkidle")

        # hide toolbar
        await page.evaluate("""
            () => {
                let t = document.querySelector('[data-testid="sticky-wrapper"]');
                if (t) t.style.display = "none";
            }
        """)

        images = {}
        page_number = 1

        while True:
            element_id = f"page{page_number}"

            exists = await page.evaluate(f"""
                () => document.getElementById("{element_id}") !== null
            """)

            if not exists:
                break

            await page.evaluate(f"""
                () => document.getElementById("{element_id}").scrollIntoView()
            """)

            await asyncio.sleep(0.5)

            element = await page.query_selector(f"#{element_id}")
            if element:
                buffer = await element.screenshot()
                images[page_number] = "data:image/png;base64," + base64.b64encode(buffer).decode()

            page_number += 1

        await browser.close()
        return images


@app.get("/screenshots")
async def screenshots(url: str):
    return await capture_scribd_screenshots(url)
