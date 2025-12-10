import asyncio
import os
import tempfile
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pyppeteer import launch
from PIL import Image

app = FastAPI()

async def capture_scribd_screenshots(url: str):
    """
    Capture each Scribd page as an image and return a list of file paths.
    """
    browser = await launch(headless=True, executablePath="C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe", args=['--no-sandbox', '--disable-setuid-sandbox'])
    page = await browser.newPage()
    
    await page.setViewport({'width': 1200, 'height': 1600})
    
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
    screenshots = await capture_scribd_screenshots(url)
    if not screenshots:
        return {"error": "No pages found"}

    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "scribd_document.pdf")
    images_to_pdf(screenshots, pdf_path)
    return FileResponse(pdf_path, media_type="application/pdf", filename="scribd_document.pdf")


