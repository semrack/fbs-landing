#!/usr/bin/env python3
"""SEO / GEO / AEO-аудитор сайта. Только стандартная библиотека Python.

Запуск:
  python3 _tools/audit.py https://semrack.ru            # отчёт в audit-report.html и audit-report.json
  python3 _tools/audit.py http://localhost:8000 --max 50

SEO — классические технические и on-page проверки.
GEO (Generative Engine Optimization) — насколько сайт удобен AI-поискам для цитирования:
  доступ AI-ботов в robots.txt, llms.txt, структурированные данные, автор и дата, ссылки на источники.
AEO (Answer Engine Optimization) — готовность давать короткие ответы: блок-ответ в начале,
  вопросы в заголовках, FAQ-разметка, таблицы и списки.
"""
import argparse, json, re, sys, time, html
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

UA = "Mozilla/5.0 (compatible; SemrackAudit/1.0; +https://semrack.ru/o-proekte/)"
AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "PerplexityBot",
           "Google-Extended", "YandexBot", "YandexAdditional"]


def fetch(url, timeout=15):
    t = time.time()
    try:
        with urlopen(Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
            body = r.read()
            return r.status, r.headers, body, time.time() - t, r.geturl()
    except HTTPError as e:
        return e.code, e.headers, e.read() if hasattr(e, "read") else b"", time.time() - t, url
    except (URLError, TimeoutError, OSError) as e:
        return 0, {}, str(e).encode(), time.time() - t, url


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""; self.meta = {}; self.links = []; self.canonical = None; self.lang = None
        self.h = []; self.imgs = []; self.jsonld = []; self.text = []; self.tables = 0; self.lists = 0
        self.details = 0; self._stack = []; self._buf = None; self._skip = 0

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == "html": self.lang = a.get("lang")
        if tag == "meta":
            k = (a.get("name") or a.get("property") or "").lower()
            if k: self.meta[k] = a.get("content", "")
        if tag == "link" and "canonical" in (a.get("rel") or ""): self.canonical = a.get("href")
        if tag == "a" and a.get("href"): self.links.append((a["href"], a.get("rel", "")))
        if tag == "img": self.imgs.append(a)
        if tag == "table": self.tables += 1
        if tag in ("ul", "ol"): self.lists += 1
        if tag == "details": self.details += 1
        if tag in ("script", "style"):
            self._skip += 1
            if tag == "script" and a.get("type") == "application/ld+json": self._buf = ["ld"]
        if tag in ("title", "h1", "h2", "h3", "p") and self._buf is None: self._buf = [tag]
        self._stack.append(tag)

    def handle_endtag(self, tag):
        if tag in ("script", "style"): self._skip = max(0, self._skip - 1)
        if self._buf and self._buf[0] == tag or (self._buf and self._buf[0] == "ld" and tag == "script"):
            kind, txt = self._buf[0], "".join(self._buf[1:]).strip()
            if kind == "title": self.title = txt
            elif kind == "ld": self.jsonld.append(txt)
            elif kind in ("h1", "h2", "h3"): self.h.append((kind, re.sub(r"\s+", " ", txt)))
            elif kind == "p": self.text.append(("p", re.sub(r"\s+", " ", txt)))
            self._buf = None

    def handle_data(self, d):
        if self._buf is not None: self._buf.append(d)
        if not self._skip: self.text.append(("t", d))


def words(s): return len(re.findall(r"\w+", s))


def ld_types(blocks):
    types, errors = [], 0
    for b in blocks:
        try:
            data = json.loads(b)
        except Exception:
            errors += 1; continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                t = x.get("@type")
                types += t if isinstance(t, list) else ([t] if t else [])
                stack += [v for v in x.values() if isinstance(v, (dict, list))]
                if "@graph" in x: stack += x["@graph"]
            elif isinstance(x, list): stack += x
    return types, errors


def check(ok, weight, cat, code, msg, fix=""):
    return dict(ok=bool(ok), w=weight, cat=cat, code=code, msg=msg, fix=fix)


def audit_page(url, status, headers, body, dt):
    p = Page(); p.feed(body.decode("utf-8", "replace"))
    all_text = " ".join(t for _, t in p.text)
    wc = words(all_text)
    h1 = [t for k, t in p.h if k == "h1"]
    h2 = [t for k, t in p.h if k == "h2"]
    types, ld_err = ld_types(p.jsonld)
    desc = p.meta.get("description", "")
    robots = p.meta.get("robots", "").lower()
    paras = [t for k, t in p.text if k == "p" and words(t) > 5]
    first = paras[0] if paras else ""
    ext = [h for h, _ in p.links if urlparse(h).netloc and urlparse(h).netloc != urlparse(url).netloc]
    has_date = bool(re.search(r"(обновлено|updated|дата)", all_text, re.I)) or "dateModified" in " ".join(p.jsonld)
    has_author = any(k in " ".join(p.jsonld) for k in ("\"author\"", "\"publisher\"")) or bool(re.search(r"автор", all_text, re.I))
    q_heads = [t for t in h2 + [t for k, t in p.h if k == "h3"] if t.strip().endswith("?")]
    faq_items = p.details
    c = [
        check(status == 200, 5, "SEO", "status", f"HTTP {status}", "Страница должна отдавать 200"),
        check(30 <= len(p.title) <= 70, 3, "SEO", "title", f"Title: {len(p.title)} симв.", "30–70 символов, главный запрос в начале"),
        check(70 <= len(desc) <= 170, 2, "SEO", "description", f"Description: {len(desc)} симв.", "70–170 символов, с выгодой и призывом"),
        check(len(h1) == 1, 3, "SEO", "h1", f"H1: {len(h1)}", "Ровно один H1"),
        check(p.canonical, 2, "SEO", "canonical", "Canonical " + ("есть" if p.canonical else "нет"), "Добавьте <link rel=canonical>"),
        check("noindex" not in robots, 5, "SEO", "indexable", "Индексация " + ("запрещена" if "noindex" in robots else "разрешена")),
        check(p.lang, 1, "SEO", "lang", f"lang={p.lang}", "Укажите <html lang>"),
        check(p.meta.get("viewport"), 2, "SEO", "viewport", "Мобильный viewport", "Добавьте meta viewport"),
        check(all(i.get("alt") is not None for i in p.imgs), 1, "SEO", "alt", f"Картинок без alt: {sum(1 for i in p.imgs if i.get('alt') is None)}"),
        check(wc >= 300, 3, "SEO", "content", f"Слов на странице: {wc}", "Тонкий контент: добавьте полезный текст от 300 слов"),
        check(p.meta.get("og:title") and p.meta.get("og:image"), 1, "SEO", "og", "Open Graph", "og:title, og:image для соцсетей и мессенджеров"),
        check(dt < 1.5, 2, "SEO", "speed", f"Ответ сервера: {dt:.2f} с", "Цель — меньше 1,5 с"),
        check(len(body) < 300_000, 1, "SEO", "weight", f"HTML: {len(body)//1024} КБ"),
        check(p.jsonld and not ld_err, 3, "GEO", "jsonld", f"JSON-LD: {', '.join(sorted(set(types))) or 'нет'}" + (f", ошибок {ld_err}" if ld_err else ""), "Добавьте schema.org в JSON-LD"),
        check(has_author, 2, "GEO", "author", "Автор или издатель " + ("указан" if has_author else "не указан"), "Укажите автора или издателя (author/publisher в schema.org) и страницу «О проекте»"),
        check(has_date, 2, "GEO", "date", "Дата обновления " + ("есть" if has_date else "нет"), "Покажите дату обновления и dateModified в разметке"),
        check(len(ext) >= 1, 2, "GEO", "sources", f"Внешних ссылок на источники: {len(ext)}", "Сошлитесь на первоисточники — AI-поиск это ценит"),
        check(first and words(first) <= 60, 3, "AEO", "answer", f"Первый абзац: {words(first)} слов", "Начните с короткого ответа на главный вопрос (до 60 слов)"),
        check(len(q_heads) >= 2 or faq_items >= 3, 2, "AEO", "questions", f"Вопросов в заголовках/FAQ: {len(q_heads) + faq_items}", "Сформулируйте подзаголовки и FAQ как вопросы пользователей"),
        check("FAQPage" in types if faq_items else True, 2, "AEO", "faq_schema", "FAQ-разметка " + ("есть" if "FAQPage" in types else "нет"), "Разметьте FAQ через FAQPage"),
        check(p.tables + p.lists >= 1, 1, "AEO", "structure", f"Таблиц: {p.tables}, списков: {p.lists}", "Таблицы и списки легко цитируются в ответах"),
    ]
    return dict(url=url, title=p.title, words=wc, checks=c,
                links=[urldefrag(urljoin(url, h))[0] for h, _ in p.links], noindex="noindex" in robots)


def site_checks(base):
    out = []
    st, _, body, _, _ = fetch(base + "/robots.txt")
    rtxt = body.decode("utf-8", "replace") if st == 200 else ""
    out.append(check(st == 200, 3, "SEO", "robots", f"robots.txt: HTTP {st}", "Создайте robots.txt"))
    out.append(check("sitemap:" in rtxt.lower(), 2, "SEO", "robots_sitemap", "Sitemap в robots.txt", "Добавьте строку Sitemap: …"))
    blocked = []
    for bot in AI_BOTS:
        block = re.search(rf"user-agent:\s*{re.escape(bot)}\s*\n(?:(?!user-agent).*\n)*?\s*disallow:\s*/\s*$", rtxt, re.I | re.M)
        if block: blocked.append(bot)
    out.append(check(not blocked, 3, "GEO", "ai_bots", "AI-боты: " + ("закрыты " + ", ".join(blocked) if blocked else "доступ открыт"), "Не закрывайте GPTBot, ClaudeBot, PerplexityBot и др., если хотите попадать в AI-ответы"))
    st, _, body, _, _ = fetch(base + "/sitemap.xml")
    locs = re.findall(r"<loc>(.*?)</loc>", body.decode("utf-8", "replace")) if st == 200 else []
    out.append(check(st == 200 and locs, 3, "SEO", "sitemap", f"sitemap.xml: HTTP {st}, URL: {len(locs)}", "Создайте sitemap.xml"))
    st, _, body, _, _ = fetch(base + "/llms.txt")
    out.append(check(st == 200 and body.strip().startswith(b"#"), 2, "GEO", "llms_txt", f"llms.txt: HTTP {st}", "Добавьте /llms.txt — краткую карту сайта для LLM"))
    st, *_ = fetch(base + "/this-page-should-not-exist-404")
    out.append(check(st == 404, 2, "SEO", "soft404", f"Несуществующая страница: HTTP {st}", "Должна отдавать 404, а не 200"))
    out.append(check(base.startswith("https://") or "localhost" in base, 3, "SEO", "https", "HTTPS", "Включите HTTPS"))
    # адреса из sitemap переносим на проверяемый хост (полезно при локальном прогоне)
    b = urlparse(base)
    return out, [urldefrag(urlparse(l)._replace(scheme=b.scheme, netloc=b.netloc).geturl())[0] for l in locs]


def score(checks, cat=None):
    cs = [x for x in checks if cat is None or x["cat"] == cat]
    tot = sum(x["w"] for x in cs) or 1
    return round(100 * sum(x["w"] for x in cs if x["ok"]) / tot)


def crawl(base, limit):
    site, locs = site_checks(base)
    host = urlparse(base).netloc
    queue, seen, pages, broken = list(dict.fromkeys([base + "/"] + locs)), set(), [], []
    while queue and len(pages) < limit:
        url = queue.pop(0)
        if url in seen: continue
        seen.add(url)
        st, hd, body, dt, final = fetch(url)
        ctype = (hd.get("Content-Type") if hd else "") or ""
        if st != 200:
            broken.append((url, st)); continue
        if "html" not in ctype: continue
        pg = audit_page(url, st, hd, body, dt)
        pages.append(pg)
        for l in pg["links"]:
            u = urlparse(l)
            if u.netloc == host and u.scheme in ("http", "https") and l not in seen and not re.search(r"\.(png|jpe?g|svg|webp|pdf|css|js)$", u.path):
                queue.append(l)
    titles = {}
    for p in pages:
        if not p["noindex"]: titles.setdefault(p["title"], []).append(p["url"])
    dups = {t: u for t, u in titles.items() if len(u) > 1}
    site.append(check(not broken, 3, "SEO", "broken", f"Битых внутренних ссылок: {len(broken)}", "; ".join(f"{u} → {s}" for u, s in broken[:5])))
    site.append(check(not dups, 2, "SEO", "dup_titles", f"Дублей title: {len(dups)}", "Сделайте title уникальными"))
    return site, pages


def report_html(base, site, pages, out):
    idx = [p for p in pages if not p["noindex"]]
    allc = site + [c for p in idx for c in p["checks"]]
    def badge(v): return f'<b style="color:{"#0a7d4f" if v >= 85 else "#b26b00" if v >= 60 else "#c0262d"}">{v}</b>'
    def rows(cs): return "".join(
        f'<tr><td>{"✅" if c["ok"] else "❌"}</td><td>{c["cat"]}</td><td>{html.escape(c["msg"])}</td><td>{"" if c["ok"] else html.escape(c["fix"])}</td></tr>' for c in cs)
    body = [f"<h1>Аудит {html.escape(base)}</h1><p>{time.strftime('%d.%m.%Y %H:%M')} · страниц: {len(pages)} (в индексе {len(idx)})</p>",
            "<div class=s>" + "".join(f"<div>{badge(score(allc, k))}<span>{k}</span></div>" for k in ("SEO", "GEO", "AEO")) +
            f"<div>{badge(score(allc))}<span>Итого</span></div></div>",
            f"<h2>Сайт целиком</h2><table>{rows(site)}</table>"]
    for p in sorted(idx, key=lambda x: score(x["checks"])):
        bad = [c for c in p["checks"] if not c["ok"]]
        body.append(f'<h3>{badge(score(p["checks"]))} <a href="{p["url"]}">{html.escape(p["url"])}</a></h3>'
                    + (f"<table>{rows(bad)}</table>" if bad else "<p>Все проверки пройдены.</p>"))
    skipped = [p["url"] for p in pages if p["noindex"]]
    if skipped: body.append("<p class=m>Закрыты от индексации (не оцениваются): " + ", ".join(skipped) + "</p>")
    css = ("body{font:15px/1.5 system-ui,sans-serif;max-width:1000px;margin:30px auto;padding:0 16px;color:#16181d}"
           "table{border-collapse:collapse;width:100%;margin:8px 0 18px}td{border-bottom:1px solid #e4e7ec;padding:6px 8px;vertical-align:top}"
           ".s{display:flex;gap:12px;flex-wrap:wrap}.s div{background:#f6f7f9;border-radius:12px;padding:14px 22px;text-align:center}"
           ".s b{display:block;font-size:34px}.s span{color:#5b6270}.m{color:#5b6270}")
    with open(out, "w", encoding="utf-8") as f:
        f.write(f'<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Аудит {html.escape(base)}</title><style>{css}</style>{"".join(body)}</html>')
    return {k: score(allc, k) for k in ("SEO", "GEO", "AEO")} | {"total": score(allc)}


def main():
    ap = argparse.ArgumentParser(description="SEO/GEO/AEO-аудит сайта")
    ap.add_argument("url"); ap.add_argument("--max", type=int, default=100)
    ap.add_argument("--out", default="audit-report")
    a = ap.parse_args()
    base = a.url.rstrip("/")
    site, pages = crawl(base, a.max)
    scores = report_html(base, site, pages, a.out + ".html")
    with open(a.out + ".json", "w", encoding="utf-8") as f:
        json.dump(dict(base=base, scores=scores, site=site, pages=[{k: v for k, v in p.items() if k != "links"} for p in pages]), f, ensure_ascii=False, indent=1)
    print(json.dumps(scores, ensure_ascii=False))
    for c in site:
        if not c["ok"]: print("  ✗ сайт:", c["msg"])
    for p in pages:
        if p["noindex"]: continue
        for c in p["checks"]:
            if not c["ok"]: print(f"  ✗ {urlparse(p['url']).path}: {c['msg']}")


if __name__ == "__main__":
    main()
