import asyncio
import json
import os
from base64 import b64decode
from collections import deque
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMConfig,
    LLMExtractionStrategy,
)
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field


class ExtractedData(BaseModel):
    urls: List[str] = Field(..., description="List of URLs to visit")
    buttons: List[str] = Field(..., description="List of button selectors to click")


crawler_config = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    excluded_tags=["script", "style"],
    exclude_external_links=True,
    screenshot=False,
    # stream=True,
)


async def complex_web_extraction(cdp_url: str, url_to_crawl: str):
    # 1. Define the LLM extraction strategy
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-4o-mini", api_token=os.getenv("OPENAI_API_KEY")
        ),
        schema=ExtractedData.model_json_schema(),  # Or use model_json_schema()
        extraction_type="schema",
        instruction="Extract all the URLs and button selectors from the following content. Some site might be using input or form tags as buttons, so try to extract those as well. Return the result in JSON format.",
        chunk_token_threshold=1000,
        overlap_rate=0.0,
        apply_chunking=True,
        input_format="html",  # or "html", "fit_markdown"
        extra_args={"temperature": 0.0, "max_tokens": 1200},
    )

    # 2. Build the crawler config
    crawl_config = CrawlerRunConfig(
        extraction_strategy=llm_strategy, cache_mode=CacheMode.BYPASS
    )

    # 3. Create a browser config if needed
    browser_cfg = BrowserConfig(headless=True, cdp_url=cdp_url)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        # 4. Let's say we want to crawl a single page
        result = await crawler.arun(url=url_to_crawl, config=crawl_config)

        if result.success:  # type: ignore
            # 5. The extracted content is presumably JSON
            data = json.loads(result.extracted_content)  # type: ignore
            print("Extracted items:", data)

            # 6. Show usage stats
            llm_strategy.show_usage()  # prints token usage
        else:
            print("Error:", result.error_message)  # type: ignore


async def take_screenshot(url: str, cdp_url: str):
    await save_screenshot_with_different_viewports(
        url=url,
        cdp_url=cdp_url,
        viewports=[
            (1920, 1080),  # Desktop
            (375, 667),  # Mobile
            (768, 1024),  # Tablet (iPad portrait)
            (1024, 768),  # Tablet (iPad landscape)
        ],
    )


async def save_screenshot_with_different_viewports(
    url: str, cdp_url: str, viewports: List[Tuple[int, int]]
):
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        screenshot=True,
        pdf=False,
    )
    for width, height in viewports:
        async with AsyncWebCrawler(
            config=BrowserConfig(
                cdp_url=cdp_url, viewport_height=height, viewport_width=width
            )
        ) as crawler:
            result = await crawler.arun(
                url=url,
                config=run_config,
            )
            if result.success:  # type: ignore
                print(f"Screenshot data present: {result.screenshot is not None}")  # type: ignore
                print(f"PDF data present: {result.pdf is not None}")  # type: ignore

                if result.screenshot:  # type: ignore
                    print(f"[OK] Screenshot captured, size: {len(result.screenshot)} bytes")  # type: ignore
                    # Extract name from URL and create output path
                    name = urlparse(url).netloc.replace(".", "_")
                    output_dir = "./output"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(
                        output_dir, f"{name}_{width}x{height}.png"
                    )

                    with open(output_path, "wb") as f:
                        f.write(b64decode(result.screenshot))  # type: ignore
                else:
                    print("[WARN] Screenshot data is None.")

            else:
                print("[ERROR]", result.error_message)  # type: ignore


async def get_clean_markdown(url: str, cdp_url: str):
    browser_cfg = BrowserConfig(cdp_url=cdp_url)

    run_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=["script", "style"],
        exclude_external_links=True,
        screenshot=False,
        # stream=True,
    )
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=run_cfg)
        _response = {
            "markdown": result.markdown,  # type: ignore
            "links": result.links,  # type: ignore
        }

        print(_response)
        return _response


def _is_same_origin(url: str, root: str) -> bool:
    parsed_url = urlparse(url)
    parsed_root = urlparse(root)
    return (
        parsed_url.scheme in {"http", "https"}
        and parsed_url.netloc == parsed_root.netloc
    )


def _extract_links(html: str, base_url: str) -> Tuple[List[str], List[str]]:
    internal: List[str] = []
    external: List[str] = []
    try:
        soup = BeautifulSoup(html or "", "html.parser")
    except Exception:
        return internal, external

    for a in soup.find_all("a", href=True):
        href = a.get("href")
        absolute = urljoin(base_url, href)  # type: ignore
        if _is_same_origin(absolute, base_url):
            if absolute not in internal:
                internal.append(absolute)
        else:
            if absolute not in external:
                external.append(absolute)
    return internal, external


def _extract_title(html: str) -> str:
    try:
        soup = BeautifulSoup(html or "", "html.parser")
        if soup.title and soup.title.string:
            return soup.title.string.strip()
    except Exception:
        pass
    return ""


async def crawl_site(
    start_url: str,
    max_pages: int = 50,
    concurrency: int = 5,
    cdp_endpoint: Optional[str] = None,
) -> List[Dict]:
    visited: Set[str] = set()
    queue: deque[str] = deque([start_url])
    results: List[Dict] = []

    semaphore = asyncio.Semaphore(concurrency)

    # Use Playwright with CDP if endpoint provided, otherwise use crawl4ai
    if cdp_endpoint:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(cdp_endpoint)
            context = await browser.new_context()

            async def fetch(url: str) -> Tuple[str, Dict]:
                async with semaphore:
                    page = await context.new_page()
                    try:
                        await page.goto(url)
                        await page.wait_for_load_state("domcontentloaded")
                        html = await page.content()
                        title = await page.title()
                        internal_links, external_links = _extract_links(html, url)
                        page_data: Dict = {
                            "url": url,
                            "title": title,
                            "markdown": "",  # No markdown generation in Playwright path
                            "html": html,
                            "links": {
                                "internal": internal_links,
                                "external": external_links,
                            },
                        }
                        return url, page_data
                    finally:
                        await page.close()

            while queue and len(visited) < max_pages:
                batch: List[str] = []
                while (
                    queue
                    and len(batch) < concurrency
                    and len(visited) + len(batch) < max_pages
                ):
                    next_url = queue.popleft()
                    if next_url in visited:
                        continue
                    batch.append(next_url)

                if not batch:
                    break

                tasks = [asyncio.create_task(fetch(u)) for u in batch]
                for task in asyncio.as_completed(tasks):
                    try:
                        url, page = await task
                    except Exception:
                        continue

                    if url in visited:
                        continue
                    visited.add(url)
                    results.append(page)

                    for link in page["links"]["internal"]:
                        if link not in visited and _is_same_origin(link, start_url):
                            queue.append(link)

            await context.close()
            await browser.close()
    else:
        # Original crawl4ai implementation
        async with AsyncWebCrawler() as crawler:

            async def fetch(url: str) -> Tuple[str, Dict]:
                async with semaphore:
                    result = await crawler.arun(url=url, config=crawler_config)
                    page_html = getattr(result, "cleaned_html", "") or ""
                    page_markdown = getattr(result, "markdown", "") or ""
                    title = _extract_title(page_html)
                    internal_links, external_links = _extract_links(page_html, url)
                    page_data: Dict = {
                        "url": url,
                        "title": title,
                        "markdown": page_markdown,
                        "html": page_html,
                        "links": {
                            "internal": internal_links,
                            "external": external_links,
                        },
                    }
                    return url, page_data

            while queue and len(visited) < max_pages:
                batch: List[str] = []
                while (
                    queue
                    and len(batch) < concurrency
                    and len(visited) + len(batch) < max_pages
                ):
                    next_url = queue.popleft()
                    if next_url in visited:
                        continue
                    batch.append(next_url)

                if not batch:
                    break

                tasks = [asyncio.create_task(fetch(u)) for u in batch]
                for task in asyncio.as_completed(tasks):
                    try:
                        url, page = await task
                    except Exception:
                        continue

                    if url in visited:
                        continue
                    visited.add(url)
                    results.append(page)

                    for link in page["links"]["internal"]:
                        if link not in visited and _is_same_origin(link, start_url):
                            queue.append(link)

    return results


if __name__ == "__main__":
    asyncio.run(crawl_site("https://www.saucedemo.com/", max_pages=10))


# @agent.tool()
# async def screenshot_current_page(ctx: RunContext[BaseDep], current_page_url: str):
#     """Takes a screenshot of the current page. Use this method to take a screenshot of the current page."""
#     # This is a placeholder function. Implement screenshot logic as needed.
#     await take_screenshot(url=current_page_url, cdp_url=ctx.deps.cdp_endpoint or "")
#     return f"Screenshot taken for {current_page_url}"
