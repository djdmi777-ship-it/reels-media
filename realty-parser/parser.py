"""Парсер объявлений недвижимости (ЦИАН, Авито, Домклик) -> XLSX/CSV.

Примеры:
  python parser.py "https://www.cian.ru/cat.php?deal_type=sale&offer_type=flat&region=1&room1=1" --pages 3
  python parser.py URL_CIAN URL_AVITO URL_DOMCLICK --pages 2 -o flats.xlsx

Каждый URL - обычная страница поиска с уже выставленными фильтрами в браузере.
"""
import argparse
import csv
import os
import random
import re
import sys
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
FIELDS = ["source", "url", "price", "title", "area_m2", "rooms", "floor", "address"]

# JS, выполняемый на странице: возвращает список сырых карточек
JS = {
    "cian": """() => [...document.querySelectorAll("article[data-name='CardComponent']")].map(c => {
        const q = s => (c.querySelector(s) || {}).innerText || '';
        const a = c.querySelector("a[href*='/sale/'], a[href*='/rent/']");
        return {url: a ? a.href : '', title: q("[data-mark='OfferTitle']"),
                price: q("[data-mark='MainPrice']"),
                address: [...c.querySelectorAll("[data-name='GeoLabel']")].map(e => e.innerText).join(', '),
                text: c.innerText};
    })""",
    "avito": """() => [...document.querySelectorAll("[data-marker='item']")].map(c => {
        const q = s => (c.querySelector(s) || {}).innerText || '';
        const a = c.querySelector("a[data-marker='item-title']");
        return {url: a ? a.href : '', title: q("[data-marker='item-title']"),
                price: q("[data-marker='item-price']"),
                address: q("[data-marker='item-address']"), text: c.innerText};
    })""",
    "domclick": """() => [...document.querySelectorAll("a[href*='/card/']")].map(a => {
        const c = a.closest('article, [data-e2e-id], li, div') || a;
        return {url: a.href, title: a.innerText, price: '', address: '', text: c.innerText};
    })""",
}


def detect_site(url):
    host = urlparse(url).netloc
    for name, key in (("cian", "cian"), ("avito", "avito"), ("domclick", "domclick")):
        if key in host:
            return name
    raise SystemExit(f"Неизвестный сайт: {host}")


def page_url(site, url, n):
    """Подставляет номер страницы в URL поиска."""
    u = urlparse(url)
    q = dict(parse_qsl(u.query))
    if n > 1:
        if site == "domclick":
            q["offset"] = str((n - 1) * 20)
        else:
            q["p"] = str(n)
    return urlunparse(u._replace(query=urlencode(q)))


def clean_url(site, url):
    """Убирает трекинговые параметры, оставляя постоянную ссылку."""
    u = urlparse(url)
    return urlunparse(u._replace(query="", fragment=""))


def pick_title(raw):
    """Заголовок вида «1-комн. квартира, 39 м², 5/6 этаж»; у ЦИАН в OfferTitle бывает реклама."""
    m = re.search(r"(?:\d+-комн\.|\d+-к\.|студия|апартаменты)[^\n]*?м²[^\n]*", raw["text"], re.I)
    return re.sub(r"\s+", " ", (m.group(0) if m else raw["title"])).strip()


def normalize(site, raw):
    text = " ".join([raw["title"], raw["text"]])
    area = re.search(r"(\d+[.,]?\d*)\s*м²", text) or re.search(r"(\d+[.,]?\d*)\s*сот", text)
    rooms = re.search(r"(\d+)-?\s*(?:к\.|комн)", text) or (
        re.search(r"(студи[яи])", text, re.I))
    floor = re.search(r"(\d+/\d+)\s*(?:эт|этаж)", text)
    price = re.sub(r"\s+", " ", raw["price"]).strip()
    if not price:
        m = re.search(r"\d[\d\s ]{4,}\s*₽", raw["text"])
        price = re.sub(r"\s+", " ", m.group(0)).strip() if m else ""
    return {
        "source": site,
        "url": clean_url(site, raw["url"]),
        "price": price,
        "title": pick_title(raw),
        "area_m2": area.group(1).replace(",", ".") if area else "",
        "rooms": rooms.group(1) if rooms else "",
        "floor": floor.group(1) if floor else "",
        "address": re.sub(r"\s+", " ", raw["address"]).strip(),
    }


def proxy_for(site):
    """Прокси только для Авито: AVITO_PROXY_URL=http://user:pass@host:port (остальные сайты идут напрямую)."""
    raw = os.getenv("AVITO_PROXY_URL") if site == "avito" else None
    if not raw:
        return None
    u = urlparse(raw)
    cfg = {"server": f"{u.scheme or 'http'}://{u.hostname}:{u.port}"}
    if u.username:
        cfg["username"] = unquote(u.username)
        cfg["password"] = unquote(u.password or "")
    return cfg


def _skip_heavy(route):
    # картинки, видео и шрифты не нужны: экономим трафик платного прокси
    if route.request.resource_type in ("image", "media", "font"):
        return route.abort()
    return route.continue_()


def scrape(urls, pages, headless=True, delay=(3, 6)):
    rows, seen, failures = [], set(), []
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    launch = {"headless": headless, "args": ["--no-sandbox"]}
    if proxy:
        launch["proxy"] = {"server": proxy}
    elif os.getenv("AVITO_PROXY_URL"):
        launch["proxy"] = {"server": "per-context"}  # заглушка, реальный прокси задаётся в контексте
    if os.getenv("CHROME_CHANNEL"):  # на GitHub Actions: предустановленный google-chrome
        launch["channel"] = os.getenv("CHROME_CHANNEL")
    elif os.path.exists("/opt/pw-browsers/chromium"):
        launch["executable_path"] = "/opt/pw-browsers/chromium"
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch)
        pages_by_site = {}
        for url in urls:
            site = detect_site(url)
            if site not in pages_by_site:
                kw = {"proxy": proxy_for(site)} if proxy_for(site) else {}
                ctx = browser.new_context(locale="ru-RU", user_agent=UA, **kw)
                ctx.route("**/*", _skip_heavy)
                pages_by_site[site] = ctx.new_page()
            page = pages_by_site[site]
            for n in range(1, pages + 1):
                target = page_url(site, url, n)
                try:
                    resp = page.goto(target, timeout=45000, wait_until="domcontentloaded")
                    page.wait_for_timeout(4000)
                    page.mouse.wheel(0, 6000)  # дозагрузка ленивых карточек
                    page.wait_for_timeout(1500)
                    items = page.evaluate(JS[site])
                except Exception as e:
                    print(f"[{site} p{n}] ошибка: {str(e)[:100]}", file=sys.stderr)
                    failures.append(f"{site}: {str(e)[:80]}")
                    break
                new = 0
                for raw in items:
                    if not raw["url"]:
                        continue
                    row = normalize(site, raw)
                    if row["url"] in seen:
                        continue
                    seen.add(row["url"])
                    rows.append(row)
                    new += 1
                status = resp.status if resp else "?"
                print(f"[{site} p{n}] HTTP {status}, карточек: {len(items)}, новых: {new}")
                if not items:
                    failures.append(f"{site} p{n}: HTTP {status}, карточек нет (блокировка?)")
                if new == 0:
                    if site == "domclick":
                        print("  Домклик закрыт антибот-защитой (Qrator): "
                              "попробуй --headed на своём компьютере.", file=sys.stderr)
                    break
                lo, hi = (10, 20) if site == "avito" else delay  # Авито быстро режет по частоте
                page.wait_for_timeout(int(random.uniform(lo, hi) * 1000))
        browser.close()
    return rows, failures


def save(rows, path):
    if path.endswith(".csv"):
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, FIELDS)
            w.writeheader()
            w.writerows(rows)
        return
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Объявления"
    ws.append(FIELDS)
    for r in rows:
        ws.append([r[k] for k in FIELDS])
        ws.cell(ws.max_row, 2).hyperlink = r["url"]
    for col, w in zip("ABCDEFGH", (10, 60, 16, 40, 10, 8, 8, 50)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    wb.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="+", help="URL страниц поиска (ЦИАН / Авито / Домклик)")
    ap.add_argument("--pages", type=int, default=1, help="сколько страниц выдачи на каждый URL")
    ap.add_argument("-o", "--output", default="listings.xlsx", help=".xlsx или .csv")
    ap.add_argument("--headed", action="store_true", help="показать окно браузера")
    a = ap.parse_args()
    rows, _ = scrape(a.urls, a.pages, headless=not a.headed)
    save(rows, a.output)
    print(f"Готово: {len(rows)} объявлений -> {a.output}")


if __name__ == "__main__":
    main()
