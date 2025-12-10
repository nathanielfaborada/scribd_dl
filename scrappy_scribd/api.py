from fastapi import FastAPI
from playwright.sync_api import sync_playwright

app = FastAPI()

@app.get("/scrape")
def scrape():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://scribd.com", timeout=15000)
            title = page.title()
            browser.close()
        return {"title": title}
    except Exception as e:
        return {"error": str(e)}
