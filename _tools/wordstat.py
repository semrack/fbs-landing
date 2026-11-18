#!/usr/bin/env python3
"""Подбор запросов через Вордстат (Yandex Search API) и сверка с семантикой сайта.

Доступ (папка .keys/ в .gitignore):
  .keys/yandex-cloud-key.txt     API-ключ служебного аккаунта (роль search-api.webSearch.user)
  .keys/yandex-cloud-folder.txt  ID каталога Yandex Cloud
Запуск:
  python _tools/wordstat.py                       # фразы по умолчанию (SEEDS ниже)
  python _tools/wordstat.py "калькулятор дрр" ... # свои фразы
Результат: wordstat-report.html и wordstat-report.json — запросы с частотой,
отмечено, какие уже покрыты страницами сайта, а какие — кандидаты на новые страницы.
"""
import html, json, re, sys, time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
KEYS = ROOT / ".keys"
URL = "https://searchapi.api.cloud.yandex.net/v2/wordstat/topRequests"
import os
OUT = Path(os.environ.get("WORDSTAT_OUT", str(ROOT / "wordstat-report")))

SEEDS = [
    "калькулятор маркетплейс", "калькулятор wildberries", "калькулятор вб", "калькулятор озон",
    "калькулятор яндекс маркет", "юнит экономика", "комиссия wildberries", "комиссия вайлдберриз",
    "комиссия озон", "комиссия яндекс маркет", "логистика wildberries", "логистика вб", "логистика озон",
    "процент выкупа", "наценка и маржа", "fbo fbs", "ндс маркетплейс", "усн маркетплейс",
    "себестоимость товара маркетплейс", "дрр", "оборачиваемость товара", "хранение wildberries",
]

# какие слова означают, что тема уже покрыта страницей
PAGES = {
    "/": ["юнит", "калькулятор маркетплейс", "прибыл", "калькулятор селлер"],
    "/wildberries/": ["wildberries", "вайлдберриз", "валберис", "вб ", " вб", "wb"],
    "/wildberries/logistika/": ["логистика вб", "логистика wildberries", "логистика вайлдберриз", "вб логистика", "стоимость логистики"],
    "/ozon/": ["озон", "ozon"],
    "/yandex-market/": ["яндекс маркет", "маркетплейс яндекс"],
    "/nalogi/": ["усн", "налог"],
    "/nds-kalkulyator/": ["ндс"],
    "/vykup/": ["выкуп"],
    "/nacenka-i-marzha/": ["наценк", "марж", "рентабел"],
    "/fbo-ili-fbs/": ["fbo", "fbs", "фбо", "фбс"],
    "/sebestoimost/": ["себестоим", "калькуляци"],
    "/drr/": ["дрр", "drr", "доля рекламных"],
    "/oborachivaemost/": ["оборачива"],
}

# запросы продавцов и явный шум (покупатели, банк, вакансии, посторонние калькуляторы)
SELLER = re.compile(r"калькул|комисс|логистик|тариф|селлер|продав|юнит|марж|наценк|выкуп|fbo|fbs|фбо|фбс|ндс|усн|"
                    r"себестоим|дрр|drr|оборачива|хранени|рентабел|прибыл|квв|остатк|поставк|приемк|приёмк|эквайр|невыкуп|штраф")
NOISE = re.compile(r"купить|пвз|пункт|до скольки|со скольки|работает|джоб|job|банк|снять|снятие|пополн|положить|заказ|"
                   r"посылк|кбжу|бжу|роста|дат|зп|кадастр|земел|участк|ламода|выкупные платеж|ооо ")


def read(name):
    f = KEYS / name
    if not f.exists():
        sys.exit(f"Нет файла {f}")
    return f.read_text(encoding="utf-8").strip()


def top(phrase, key, folder):
    body = {"phrase": phrase, "numPhrases": "200", "regions": ["225"], "devices": ["DEVICE_ALL"], "folderId": folder}
    r = requests.post(URL, headers={"Authorization": f"Api-Key {key}"}, json=body, timeout=30)
    if r.status_code != 200:
        print(f"  ! {phrase}: {r.status_code} {r.text[:200]}")
        return [], []
    d = r.json()
    res = [(x.get("phrase", ""), int(x.get("count", 0))) for x in d.get("results", [])]
    assoc = [(x.get("phrase", ""), int(x.get("count", 0))) for x in d.get("associations", [])]
    return res, assoc


def cover(q):
    ql = f" {q.lower()} "
    hits = [p for p, words in PAGES.items() if any(w in ql for w in words)]
    # самые узкие совпадения важнее главной
    return [h for h in hits if h != "/"] or hits


def main():
    seeds = sys.argv[1:] or SEEDS
    key, folder = read("yandex-cloud-key.txt"), read("yandex-cloud-folder.txt")
    seen = {}
    for s in seeds:
        res, assoc = top(s, key, folder)
        print(f"{s}: {len(res)} запросов" + (f", всего показов фразы: {res[0][1]}" if res else ""))
        for q, c in res:
            seen[q] = (max(seen.get(q, (0, ""))[0], c), "top")
        for q, c in assoc:
            seen.setdefault(q, (c, "similar"))
        time.sleep(0.3)
    rows = sorted(({"query": q, "count": c, "source": src, "pages": cover(q),
                    "seller": bool(SELLER.search(q.lower())) and not NOISE.search(q.lower())}
                   for q, (c, src) in seen.items()), key=lambda r: -r["count"])
    sel = [r for r in rows if r["seller"]]
    gaps = [r for r in sel if not r["pages"]]
    Path(str(OUT) + ".json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    tr = lambda r: (f"<tr><td>{html.escape(r['query'])}</td><td>{r['count']:,}</td>"
                    f"<td>{', '.join(r['pages']) or '<b>нет страницы</b>'}</td></tr>").replace(",", " ")
    css = ("body{font:15px/1.5 system-ui,sans-serif;max-width:1000px;margin:30px auto;padding:0 16px}"
           "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #e4e7ec;padding:5px 8px;text-align:left}th{background:#f6f7f9}")
    head = "<tr><th>Запрос</th><th>Частота / мес</th><th>Страница сайта</th></tr>"
    Path(str(OUT) + ".html").write_text(
        f'<!doctype html><html lang="ru"><meta charset="utf-8"><title>Вордстат</title><style>{css}</style>'
        f"<h1>Вордстат: запросы селлеров</h1><p>Всего фраз: {len(rows)}, запросов продавцов: {len(sel)}, из них без страницы: {len(gaps)}</p>"
        f"<h2>Запросы продавцов без страницы на сайте</h2><table>{head}{''.join(tr(r) for r in gaps[:150])}</table>"
        f"<h2>Запросы продавцов</h2><table>{head}{''.join(tr(r) for r in sel[:600])}</table>"
        f"<h2>Остальное (покупатели, шум, похожие запросы)</h2><table>{head}{''.join(tr(r) for r in rows if not r['seller'])}</table></html>", encoding="utf-8")
    print(f"Готово: wordstat-report.html — {len(rows)} фраз, продавцов {len(sel)}, без страницы {len(gaps)}")


if __name__ == "__main__":
    main()
