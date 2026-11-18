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
    "/wildberries/": ["wildberries", "вайлдберриз", "вб ", " вб", "wb"],
    "/wildberries/logistika/": ["логистик"],
    "/ozon/": ["озон", "ozon"],
    "/yandex-market/": ["яндекс маркет", "маркет"],
    "/nalogi/": ["ндс", "усн", "налог"],
    "/vykup/": ["выкуп"],
    "/nacenka-i-marzha/": ["наценк", "марж"],
    "/fbo-ili-fbs/": ["fbo", "fbs", "фбо", "фбс"],
}


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
            seen[q] = max(seen.get(q, 0), c)
        for q, c in assoc:
            seen.setdefault(q, c)
        time.sleep(0.3)
    rows = sorted(({"query": q, "count": c, "pages": cover(q)} for q, c in seen.items()), key=lambda r: -r["count"])
    gaps = [r for r in rows if not r["pages"]]
    (ROOT / "wordstat-report.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    tr = lambda r: (f"<tr><td>{html.escape(r['query'])}</td><td>{r['count']:,}</td>"
                    f"<td>{', '.join(r['pages']) or '<b>нет страницы</b>'}</td></tr>").replace(",", " ")
    css = ("body{font:15px/1.5 system-ui,sans-serif;max-width:1000px;margin:30px auto;padding:0 16px}"
           "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #e4e7ec;padding:5px 8px;text-align:left}th{background:#f6f7f9}")
    head = "<tr><th>Запрос</th><th>Частота / мес</th><th>Страница сайта</th></tr>"
    (ROOT / "wordstat-report.html").write_text(
        f'<!doctype html><html lang="ru"><meta charset="utf-8"><title>Вордстат</title><style>{css}</style>'
        f"<h1>Вордстат: запросы селлеров</h1><p>Фраз: {len(rows)}, без страницы: {len(gaps)}</p>"
        f"<h2>Не покрыты сайтом</h2><table>{head}{''.join(tr(r) for r in gaps[:150])}</table>"
        f"<h2>Все запросы</h2><table>{head}{''.join(tr(r) for r in rows[:800])}</table></html>", encoding="utf-8")
    print(f"Готово: wordstat-report.html — {len(rows)} запросов, без страницы {len(gaps)}")


if __name__ == "__main__":
    main()
