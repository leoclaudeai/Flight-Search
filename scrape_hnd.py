import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime, timedelta

async def scrape_hkg_hnd(date_str: str):
    """date_str format: YYYY-MM-DD"""
    url = (
        f"https://www.google.com/travel/flights?"
        f"hl=zh-HK&curr=HKD&"
        f"q=Flights%20from%20HKG%20to%20HND%20on%20{date_str}"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(8000)

            prices = await page.evaluate('''() => {
                const results = [];
                const all = document.querySelectorAll('span, div');
                all.forEach(el => {
                    const t = el.innerText || "";
                    const match = t.match(/HK\\$?\\s*([0-9,]{3,})/);
                    if (match) {
                        const num = parseInt(match[1].replace(/,/g, ""));
                        if (num > 300 && num < 20000) {
                            results.push(num);
                        }
                    }
                });
                return [...new Set(results)].sort((a, b) => a - b);
            }''')

            return {
                "date": date_str,
                "route": "HKG-HND",
                "prices_found": prices[:10],
                "cheapest": prices[0] if prices else None,
                "scraped_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {"date": date_str, "error": str(e)}
        finally:
            await browser.close()

async def main():
    results = []
    today = datetime.now()
    for i in range(4):
        days_ahead = (2 - today.weekday() + 7) % 7  # next Wednesday
        if days_ahead == 0:
            days_ahead = 7
        target = today + timedelta(days=days_ahead + i * 7)
        date_str = target.strftime("%Y-%m-%d")
        print(f"Scraping {date_str}...")
        result = await scrape_hkg_hnd(date_str)
        results.append(result)
        await asyncio.sleep(2)

    # Save to file
    with open("prices_hnd.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("Saved to prices_hnd.json")
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
