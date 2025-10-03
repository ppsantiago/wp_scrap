from playwright.async_api import async_playwright

async def check_domain_status(domain: str) -> dict:
    if not domain.startswith("http"):
        domain = f"http://{domain}"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            response = await page.goto(domain, timeout=10000)
            await browser.close()
            if response:
                return {"domain": domain, "status_code": response.status, "success": True}
            else:
                return {"domain": domain, "error": "No response received", "success": False}
    except Exception as e:
        return {"domain": domain, "error": str(e), "success": False}