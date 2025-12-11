import asyncio
import os
import tempfile
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pyppeteer import launch
from PIL import Image

app = FastAPI()

# Railway Chromium path
CHROME_PATH = "/usr/bin/google-chrome-stable"

# Required Chromium args for Railway
CHROME_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--single-process",
    "--no-zygote",
    "--disable-software-rasterizer"
]


async def get_browser():
    return await launch(
        headless=True,
        executablePath=CHROME_PATH,  # Chrome is preinstalled in Railway
        args=CHROME_ARGS
    )


async def capture_scribd_screenshots(url: str):
    browser = await get_browser()
    page = await browser.newPage()

    await page.setViewport({"width": 1200, "height": 1600})

    await page.goto(url, {"waitUntil": "networkidle2"})
    await asyncio.sleep(5)  # Wait for Scribd to stabilize

    await page.waitForSelector("body")

    # Hide toolbar
    await page.evaluate("""
        () => {
            const toolbar = document.querySelector('[data-testid="sticky-wrapper"]');
            if (toolbar) toolbar.style.display = 'none';
        }
    """)

    temp_dir = tempfile.mkdtemp()
    screenshots = []

    page_number = 1

    while True:
        div_id = f"page{page_number}"

        exists = await page.evaluate(
            f"() => document.getElementById('{div_id}') !== null"
        )

        if not exists:
            break

        # Scroll into view
        await page.evaluate(f"""
            () => document.getElementById('{div_id}').scrollIntoView()
        """)

        await asyncio.sleep(1)

        # Bounding box
        bounding = await page.evaluate(f"""
            () => {{
                const el = document.getElementById("{div_id}");
                const r = el.getBoundingClientRect();
                return {{
                    x: r.left,
                    y: r.top + window.scrollY,
                    width: r.width,
                    height: r.height
                }};
            }}
        """)

        image_path = os.path.join(temp_dir, f"page_{page_number}.png")

        await page.screenshot({
            "path": image_path,
            "clip": bounding
        })

        screenshots.append(image_path)
        page_number += 1

    await browser.close()
    return screenshots


def images_to_pdf(image_paths, output_path):
    images = [Image.open(x).convert("RGB") for x in image_paths]
    images[0].save(output_path, save_all=True, append_images=images[1:])
    return output_path


@app.get("/pdf")
async def get_pdf(url: str):
    screenshots = await capture_scribd_screenshots(url)

    if not screenshots:
        return {"error": "No pages captured"}

    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "scribd.pdf")

    images_to_pdf(screenshots, pdf_path)

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="scribd.pdf"
    )
