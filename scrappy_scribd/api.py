import asyncio
import os
import tempfile
import base64
from fastapi import FastAPI
from pyppeteer import launch

app = FastAPI()


async def capture_scribd_screenshots(url: str):
    browser = await launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    page = await browser.newPage()
    await page.setViewport({'width': 1200, 'height': 1600})

    await page.goto(url, {'waitUntil': 'networkidle2'})
    await page.waitForSelector("body")

    # Hide sticky header
    await page.evaluate("""
        () => {
            const t = document.querySelector('[data-testid="sticky-wrapper"]');
            if (t) t.style.display = "none";
        }
    """)

    temp_dir = tempfile.mkdtemp()
    screenshot_files = []

    page_number = 1
    while True:
        div_id = f"page{page_number}"

        exists = await page.evaluate(f"""
            () => document.getElementById("{div_id}") !== null
        """)

        if not exists:
            break

        await page.evaluate(f"""
            () => document.getElementById("{div_id}").scrollIntoView()
        """)

        await asyncio.sleep(1)

        # Get bounding box
        box = await page.evaluate(f"""
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

        path = os.path.join(temp_dir, f"page_{page_number}.png")

        await page.screenshot({
            "path": path,
            "clip": {
                "x": box["x"],
                "y": box["y"],
                "width": box["width"],
                "height": box["height"]
            }
        })

        screenshot_files.append(path)
        page_number += 1

    await browser.close()
    return screenshot_files


@app.get("/screenshots")
async def api_screenshots(url: str):
    files = await capture_scribd_screenshots(url)

    if not files:
        return {"error": "No pages found."}

    output = {}

    for i, img_path in enumerate(files, start=1):
        with open(img_path, "rb") as f:
            b64img = base64.b64encode(f.read()).decode("utf-8")
        output[i] = f"data:image/png;base64,{b64img}"

    return output
