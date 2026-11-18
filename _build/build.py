#!/usr/bin/env python3
"""Генератор статического сайта semrack.ru.
Запуск: python3 _build/build.py  (из корня репозитория)
Папки, начинающиеся с "_", GitHub Pages (Jekyll) не публикует.
"""
import json, os, html
from pages import PAGES, SITE, UPDATED_ISO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOOLS_LINKS = ('<a href="/wildberries/logistika/">Логистика WB</a> · <a href="/vykup/">Процент выкупа</a> · '
               '<a href="/nacenka-i-marzha/">Наценка и маржа</a> · <a href="/fbo-ili-fbs/">FBO или FBS</a>')
NAV = [("/", "Калькулятор"), ("/wildberries/", "Wildberries"), ("/ozon/", "Ozon"),
       ("/yandex-market/", "Яндекс Маркет"), ("/nalogi/", "Налоги"), ("/o-proekte/", "О проекте")]


def calc_block(mp, any_mp=False):
    tabs = "".join(
        f'<button type="button" data-mp="{k}" aria-pressed="{str(k == mp).lower()}">{n}</button>'
        for k, n in (("wb", "Wildberries"), ("ozon", "Ozon"), ("ym", "Яндекс Маркет")))

    def field(id_, label, unit, value, hint="", step="any"):
        h = f'<p class="hint">{hint}</p>' if hint else ""
        return (f'<div><label for="{id_}">{label}</label><div class="inp">'
                f'<input id="{id_}" type="number" inputmode="decimal" step="{step}" min="0" value="{value}">'
                f'<span>{unit}</span></div>{h}</div>')

    return f'''<section class="calc" id="calc" data-mp="{mp}"{' data-any' if any_mp else ''} aria-label="Калькулятор">
<form class="panel" onsubmit="return false">
<div class="tabs" role="group" aria-label="Маркетплейс">{tabs}</div>
<fieldset><legend>Товар</legend><div class="grid">
{field("c-price", "Цена продажи", "₽", 1500, "Цена, от которой маркетплейс считает комиссию")}
{field("c-cost", "Себестоимость", "₽", 450, "Закупка + доставка до склада + упаковка")}
</div></fieldset>
<fieldset><legend>Удержания маркетплейса</legend><div class="grid">
{field("c-commission", "Комиссия", "%", 30, "Ставка вашей категории из личного кабинета")}
{field("c-acquiring", "Эквайринг / перевод", "%", 2)}
{field("c-logistics", "Логистика к покупателю", "₽", 80, "За одну доставку")}
{field("c-back", "Обратная логистика", "₽", 50, "За один невыкуп или возврат")}
{field("c-buyout", "Процент выкупа", "%", 80)}
{field("c-storage", "Хранение на единицу", "₽", 5)}
</div></fieldset>
<fieldset><legend>Ваши расходы и налоги</legend><div class="grid">
{field("c-ads", "Реклама <small>от цены</small>", "%", 5)}
{field("c-other", "Прочее на единицу", "₽", 0, "Маркировка, фулфилмент, приёмка")}
<div><label for="c-tax">Налоговый режим</label><div class="inp"><select id="c-tax">
<option value="usn6">УСН «Доходы»</option><option value="usn15">УСН «Доходы минус расходы»</option></select></div></div>
{field("c-taxrate", "Ставка налога", "%", 6, "В части регионов ниже")}
<div><label for="c-vat">НДС <small>для УСН</small></label><div class="inp"><select id="c-vat">
<option value="0">Без НДС (доход до 20 млн ₽)</option><option value="5">5%</option><option value="7">7%</option><option value="22">22%</option></select></div>
<p class="hint">НДС 22% считается без вычетов</p></div>
</div></fieldset>
</form>
<div class="panel res" aria-live="polite">
<div class="upd">Прибыль с одной продажи</div>
<div class="big" id="r-profit">—</div>
<div class="kpis">
<div class="kpi"><b id="r-margin">—</b><span>маржинальность</span></div>
<div class="kpi"><b id="r-roi">—</b><span>ROI на себестоимость</span></div>
<div class="kpi"><b id="r-payout">—</b><span>перечислит маркетплейс</span></div>
<div class="kpi"><b id="r-be">—</b><span>цена без убытка</span></div>
</div>
<div class="bar" id="r-bar" aria-hidden="true"></div>
<ul class="legend" id="r-legend"></ul>
<div class="target"><div class="row"><div>
<label for="c-target">Какую цену поставить для маржи</label>
<div class="inp"><input id="c-target" type="number" inputmode="decimal" min="0" max="90" value="20"><span>%</span></div>
</div></div><p style="margin:10px 0 0">Нужна цена: <b id="r-target">—</b></p></div>
<p class="note">Ставки по умолчанию — типовые на {SITE["updated_human"]}. Подставьте свои из личного кабинета: тарифы меняются по нескольку раз в год.</p>
</div>
</section>'''


def faq_html(faq):
    items = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
    return f'<h2 id="faq">Частые вопросы</h2>{items}'


def strip_tags(s):
    import re
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def page_html(p):
    url = SITE["base"] + p["path"]
    crumbs = ""
    ld = [{
        "@context": "https://schema.org", "@type": "WebPage", "@id": url + "#page", "url": url,
        "name": p["title"], "description": p["description"], "inLanguage": "ru",
        "dateModified": UPDATED_ISO, "datePublished": SITE["published_iso"],
        "isPartOf": {"@type": "WebSite", "name": SITE["name"], "url": SITE["base"] + "/"},
        "publisher": {"@type": "Organization", "name": SITE["name"], "url": SITE["base"] + "/"},
    }]
    if p["path"] != "/":
        trail = [("/", "Главная")] + ([p["parent"]] if p.get("parent") else []) + [(p["path"], p["crumb"])]
        crumbs = ('<nav class="crumbs" aria-label="Хлебные крошки">'
                  + " → ".join(f'<a href="{h}">{n}</a>' for h, n in trail[:-1])
                  + f' → <span>{p["crumb"]}</span></nav>')
        ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE["base"] + h}
            for i, (h, n) in enumerate(trail)]})
    if p.get("calc"):
        ld.append({"@context": "https://schema.org", "@type": "WebApplication", "name": p["app_name"],
                   "url": url, "applicationCategory": "BusinessApplication", "operatingSystem": "Any",
                   "inLanguage": "ru", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "RUB"}})
    if p.get("faq"):
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a)}}
            for q, a in p["faq"]]})
    if p["path"] == "/":
        ld.append({"@context": "https://schema.org", "@type": "WebSite", "name": SITE["name"],
                   "url": SITE["base"] + "/", "inLanguage": "ru"})

    nav = "".join(f'<a href="{h}"{" aria-current=page" if h == p["path"] else ""}>{n}</a>' for h, n in NAV)
    answer = f'<div class="answer"><strong>Коротко</strong>{p["answer"]}</div>' if p.get("answer") else ""
    calc = calc_block(p["calc"], p.get("calc_any", False)) if p.get("calc") else ""
    script = '<script src="/assets/calc.js?v=1" defer></script>' if p.get("calc") else ""
    if p.get("tool"):
        calc = f'<section class="calc" id="tool" data-tool="{p["tool"]}" aria-label="Калькулятор">{p["tool_html"]}</section>'
        script = '<script src="/assets/tools.js?v=1" defer></script>'
        ld.append({"@context": "https://schema.org", "@type": "WebApplication", "name": p["app_name"],
                   "url": url, "applicationCategory": "BusinessApplication", "operatingSystem": "Any",
                   "inLanguage": "ru", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "RUB"}})
    faq = faq_html(p["faq"]) if p.get("faq") else ""
    lds = "\n".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{p["title"]}</title>
<meta name="description" content="{p["description"]}">
<link rel="canonical" href="{url}">
<meta name="robots" content="{p.get("robots", "index, follow, max-snippet:-1, max-image-preview:large")}">
<meta property="og:type" content="website">
<meta property="og:locale" content="ru_RU">
<meta property="og:site_name" content="{SITE["name"]}">
<meta property="og:title" content="{p["title"]}">
<meta property="og:description" content="{p["description"]}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE["base"]}/assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/style.css?v=1">
{lds}
<script src="/assets/consent.js?v=1" defer></script>
</head>
<body>
<header class="hdr"><div class="wrap"><a class="logo" href="/"><i aria-hidden="true"></i>{SITE["name"]}</a><nav class="nav" aria-label="Разделы">{nav}</nav></div></header>
<main>
<div class="wrap">{crumbs}
<section class="hero"><h1>{p["h1"]}</h1><p class="lead">{p["lead"]}</p>
<p class="upd">Обновлено {SITE["updated_human"]} · <a href="/o-proekte/">Методика расчёта</a></p>{answer}</section>
{calc}
<article class="content narrow">{p["body"]}{faq}</article>
</div>
</main>
<footer class="ftr"><div class="wrap"><div>© 2026 {SITE["name"]}. Расчёты справочные и не заменяют тарифы маркетплейсов и консультацию бухгалтера.</div>
<div>{TOOLS_LINKS} · <a href="/o-proekte/">О проекте и методика</a> · <a href="/politika/">Политика конфиденциальности</a> · <a href="#" data-cookie-settings>Настройки cookie</a></div></div></footer>
{script}
</body>
</html>
'''


def main():
    for p in PAGES:
        out = os.path.join(ROOT, p["file"])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(page_html(p))
    # sitemap
    urls = "".join(
        f"<url><loc>{SITE['base']}{p['path']}</loc><lastmod>{UPDATED_ISO}</lastmod></url>"
        for p in PAGES if p.get("sitemap", True))
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    # llms.txt — краткая карта сайта для AI-ассистентов
    lines = [f"# {SITE['name']}", "", f"> {SITE['tagline']}", "",
             f"Обновлено: {SITE['updated_human']}.", "", "## Страницы", ""]
    for p in PAGES:
        if p.get("sitemap", True):
            lines.append(f"- [{p['h1']}]({SITE['base']}{p['path']}): {p['description']}")
    with open(os.path.join(ROOT, "llms.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("ok:", len(PAGES), "pages")


if __name__ == "__main__":
    main()
