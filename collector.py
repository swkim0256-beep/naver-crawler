import asyncio
from datetime import datetime
import os
import pandas as pd
from playwright.async_api import async_playwright

CSV_PATH = "naver_titles.csv"

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        page = await context.new_page()
        await page.goto("https://m.naver.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(3500)

        elements = await page.locator("a strong, a .title, .feed_title, a span").all_text_contents()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        records = []

        for text in elements:
            cleaned = text.strip()
            if 15 <= len(cleaned) <= 40 and not cleaned.startswith(("http", "더보기")):
                records.append({
                    "수집일시": now,
                    "제목": cleaned,
                    "글자수": len(cleaned)
                })

        await browser.close()
        return records

if __name__ == "__main__":
    items = asyncio.run(scrape())
    df_new = pd.DataFrame(items).drop_duplicates(subset=["제목"])

    if os.path.exists(CSV_PATH):
        try:
            df_old = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
            df_final = pd.concat([df_old, df_new]).drop_duplicates(subset=["제목"])
        except Exception:
            df_final = df_new
    else:
        df_final = df_new

    df_final.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
