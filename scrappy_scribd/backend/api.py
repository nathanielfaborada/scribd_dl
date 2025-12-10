import asyncio
import os
import tempfile
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pyppeteer import launch
from PIL import Image

app = FastAPI()

# Configuration
MAX_PAGES = 50
VIEWPORT_WIDTH = 1024
VIEWPORT_HEIGHT = 1200
SYSTEM_CHROMIUM_PATH = "/usr/bin/chromium-browser"  # Railway system Chromium

async def capture_scribd_screenshots(url: str, temp_dir: str):
    """
    Capture Scribd pages as images and return list of file paths.
    """
    # Launch system Chromium
    browser = await launch(
        headless=True,
        executablePath=SYSTEM_CHROMIUM_PATH,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',  # important for low-memory containers
            '--single-process',
            '--disable-gpu'
        ]
    )

    page = await browser.newPage()
    await page.setViewport({'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT})

    # Navigate to Scribd
    await page.goto(url, {'waitUntil': 'networkidle2', 'timeout': 30000})
    await page.waitForSelector('body', {'timeout': 15000})

    # Hide sticky toolbar
    await page.evaluate('''() => {
        const toolbar = document.querySelector('[data-testid="sticky-wrapper"]');
        if (toolbar) toolbar.style.display = 'none';
    }''')

    screenshots = []
    page_number = 1

    while page_number <= MAX_PAGES:
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
        await asyncio.sleep(0.5)

        # Get bounding box
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

def images_to_pdf(image_paths, output_path):
    """
    Convert list of images to a single PDF.
    """
    if not image_paths:
        return None
    images = [Image.open(p).convert('RGB') for p in image_paths]
    images[0].save(output_path, save_all=True, append_images=images[1:])
    return output_path

@app.get("/pdf")
async def get_scribd_pdf(url: str):
    """
    Capture Scribd pages and return as PDF.
    """
    try:
        temp_dir = tempfile.mkdtemp()
        screenshots = await capture_scribd_screenshots(url, temp_dir)

        if not screenshots:
            return {"error": "No pages found"}

        pdf_path = os.path.join(temp_dir, "scribd_document.pdf")
        images_to_pdf(screenshots, pdf_path)

        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename="scribd_document.pdf"
        )

    except Exception as e:
        return {"error": f"Failed to generate PDF: {str(e)}"}
