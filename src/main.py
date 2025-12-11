# backend/main.py

import asyncio
import os
import tempfile
import zipfile
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pyppeteer import launch, chromium_downloader

app = FastAPI(title="Scribd Screenshot Downloader")

# -----------------------------
# Utility functions
# -----------------------------
async def capture_scribd_screenshots(url: str):
    """
    Capture each Scribd page as an image and return a list of file paths.
    Fully Linux-compatible for Railway deployment.
    """

    # Ensure Chromium is downloaded inside container
    chromium_downloader.download_chromium()

    browser = await launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--single-process",
            "--disable-gpu",
            "--disable-software-rasterizer"
        ]
    )

    page = await browser.newPage()
    await page.setViewport({'width': 800, 'height': 1000})  # smaller viewport to save memory
    await page.goto(url, {'waitUntil': 'networkidle2'})
    await page.waitForSelector('body')

    # Hide sticky toolbar
    await page.evaluate('''() => {
        const toolbar = document.querySelector('[data-testid="sticky-wrapper"]');
        if (toolbar) toolbar.style.display = 'none';
    }''')

    temp_dir = tempfile.mkdtemp()
    screenshots = []

    page_number = 1
    while True:
        div_id = f'page{page_number}'
        exists = await page.evaluate(f'''() => {{
            return document.getElementById("{div_id}") !== null;
        }}''')
        if not exists:
            break

        # Scroll page into view
        await page.evaluate(f'''() => {{
            document.getElementById("{div_id}").scrollIntoView();
        }}''')
        await asyncio.sleep(1)  # wait for lazy-loaded images

        bounding_box = await page.evaluate(f'''() => {{
            const rect = document.getElementById("{div_id}").getBoundingClientRect();
            return {{x: rect.left, y: rect.top + window.scrollY, width: rect.width, height: rect.height}};
        }}''')

        screenshot_path = os.path.join(temp_dir, f'page_{page_number}.png')
        await page.screenshot({
            'path': screenshot_path,
            'clip': {
                'x': bounding_box['x'],
                'y': bounding_box['y'],
                'width': bounding_box['width'],
                'height': bounding_box['height']
            }
        })
        screenshots.append(screenshot_path)
        page_number += 1

    await browser.close()
    return screenshots


def create_zip(file_paths, output_path):
    """
    Zip all image files into a single archive.
    """
    with zipfile.ZipFile(output_path, 'w') as zipf:
        for file_path in file_paths:
            zipf.write(file_path, os.path.basename(file_path))
    return output_path


# -----------------------------
# FastAPI endpoints
# -----------------------------
@app.get("/screenshots")
async def get_scribd_screenshots(url: str = Query(..., description="Scribd document URL")):
    """
    Capture all Scribd pages as screenshots and return a ZIP file.
    """
    try:
        screenshots = await capture_scribd_screenshots(url)
        if not screenshots:
            return {"error": "No pages found"}

        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "scribd_screenshots.zip")
        create_zip(screenshots, zip_path)

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="scribd_screenshots.zip"
        )
    except Exception as e:
        return {"error": f"Failed to capture screenshots: {str(e)}"}
