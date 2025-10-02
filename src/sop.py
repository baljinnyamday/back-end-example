from typing import List, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def extract_links(html_path: str, base_url: str) -> Tuple[List[str], List[str]]:
    internal: List[str] = []
    external: List[str] = []
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
    except Exception:
        return internal, external

    for a in soup.find_all("a", href=True):
        href = a.get("href")
        absolute = urljoin(base_url, href)  # type: ignore
        external.append(absolute)

    return internal, external


if __name__ == "__main__":
    internal_links, external_links = extract_links(
        "./index.html", "https://en.wikipedia.org/wiki/List_of_common_misconceptions"
    )
    print("Internal Links:")
    for link in internal_links:
        print(link)

    print("\nExternal Links:")
    for link in external_links:
        print(link)
