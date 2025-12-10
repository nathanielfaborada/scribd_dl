import asyncio
import os
import tempfile
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pyppeteer import launch
from PIL import Image

app = FastAPI()

MAX_PAGES = 100  # Prevent infinite loops for very large documents
PAGE_WIDTH = 1200
PAGE_HEIGHT = 1600

async def capture_scribd_screenshots(url: str, temp_dir: str):
    """
    Capture each Scribd page as an image and return a list of file paths.
    """
    browser = await launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    )
    page = await browser.newPage()
    await page.setViewport({'width': PAGE_WIDTH, 'height': PAGE_HEIGHT})

    # Navigate with timeout
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

        # Scroll page into view and wait for lazy-loaded images
        await page.evaluate(f'''() => {{
            document.getElementById("{div_id}").scrollIntoView();
        }}''')
        await asyncio.sleep(1)

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
    Capture all Scribd pages as screenshots and return a PDF.
    """
    try:
        # Single temporary directory for screenshots and PDF
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
