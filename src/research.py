"""The tool layer: reach the web to fill a knowledge/ability gap.

SAFETY: everything fetched here is UNTRUSTED DATA, never instructions. The engine
distills it and the owner approves what persists. Nothing here is executed or obeyed.
"""
import re
import urllib.parse

import httpx

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
_WIKI = "https://en.wikipedia.org/w/api.php"
_DDG = "https://html.duckduckgo.com/html/"


def _client():
    return httpx.Client(timeout=12, headers=_UA, follow_redirects=True)


def strip_html(html):
    html = re.sub(r"(?is)<(script|style|nav|footer|header)\b.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"&[a-z#0-9]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def wiki_search(query, n=3):
    params = {"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": n}
    try:
        with _client() as c:
            data = c.get(_WIKI, params=params).raise_for_status().json()
        return [h["title"] for h in data.get("query", {}).get("search", [])]
    except Exception:
        return []                                   # some networks block Wikipedia; web search is the primary path


def wiki_extract(title, max_chars=6000):
    params = {"action": "query", "prop": "extracts", "explaintext": 1, "titles": title, "format": "json"}
    try:
        with _client() as c:
            data = c.get(_WIKI, params=params).raise_for_status().json()
        for p in data.get("query", {}).get("pages", {}).values():
            return (p.get("extract") or "")[:max_chars]
    except Exception:
        pass
    return ""


_DDG_LITE = "https://lite.duckduckgo.com/lite/"


def web_search(query, n=3):
    """Best-effort general web search via DuckDuckGo (html then lite endpoint).
    Returns [(title, url)]. Scraping is inherently flaky / rate-limited; treat as
    best-effort and degrade gracefully when it returns nothing."""
    out, seen = [], set()
    for endpoint in (_DDG, _DDG_LITE):
        try:
            with _client() as c:
                html = c.post(endpoint, data={"q": query}).raise_for_status().text
        except Exception:
            continue
        for m in re.finditer(r'href="(https?://[^"]+)"[^>]*class="[^"]*result[^"]*"[^>]*>(.*?)</a>', html):
            url, title = m.group(1), strip_html(m.group(2))
            if url not in seen and title and "duckduckgo.com" not in url:
                seen.add(url)
                out.append((title, url))
        for m in re.finditer(r'class="result__a"[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', html):
            url, title = m.group(1), strip_html(m.group(2))
            if url not in seen and title:
                seen.add(url)
                out.append((title, url))
        if out:
            break
    return out[:n]


def fetch_url(url, max_chars=6000):
    with _client() as c:
        r = c.get(url).raise_for_status()
    if "html" in r.headers.get("content-type", ""):
        return strip_html(r.text)[:max_chars]
    return r.text[:max_chars]


def research(query, n=4):
    """Return {'source', 'url', 'text'} for a query: general web (DuckDuckGo) first,
    fetching the first result page that yields real text; Wikipedia as a fallback."""
    for title, url in web_search(query, n):
        try:
            text = fetch_url(url)
        except Exception:
            continue
        if len(text) > 300:
            return {"source": title, "url": url, "text": text}
    titles = wiki_search(query, 2)          # fallback (may be blocked on some networks)
    if titles:
        text = wiki_extract(titles[0])
        if text:
            url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(titles[0].replace(" ", "_"))
            return {"source": titles[0], "url": url, "text": text}
    return None
