#!/usr/bin/env python3
"""Данные поиска для semrack.ru: Google Search Console + Яндекс.Вебмастер → отчёт с точками роста.

Установка (один раз):  pip install google-auth requests
Доступы (никогда не коммитятся — папка .keys/ в .gitignore):
  .keys/gsc-key.json      JSON-ключ служебного аккаунта Google (или ~/.semrack/gsc-key.json, или env GSC_KEY_FILE)
  .keys/yandex-token.txt  OAuth-токен Вебмастера (или ~/.semrack/yandex-token.txt, или env YANDEX_WEBMASTER_TOKEN)
Запуск:
  python3 _tools/search_data.py              # последние 28 дней
  python3 _tools/search_data.py --days 90
Результат: search-report.html и search-report.json в текущей папке.
"""
import argparse, datetime as dt, html, json, os, sys
from pathlib import Path

SITE = "https://semrack.ru/"
GSC_PROPERTY = os.environ.get("GSC_PROPERTY", SITE)          # для доменного ресурса: sc-domain:semrack.ru
YA_HOST = "https:semrack.ru:443"
HOME = Path.home() / ".semrack"
REPO_KEYS = Path(__file__).resolve().parent.parent / ".keys"


def keyfile(name):
    for d in (REPO_KEYS, HOME):
        if (d / name).exists(): return d / name
    return REPO_KEYS / name


def gsc_rows(days):
    key = Path(os.environ.get("GSC_KEY_FILE", keyfile("gsc-key.json"))).expanduser()
    if not key.exists():
        print(f"[GSC] нет ключа {key} — пропускаю"); return None
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    creds = service_account.Credentials.from_service_account_file(
        str(key), scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    s = AuthorizedSession(creds)
    end = dt.date.today() - dt.timedelta(days=2)   # данные GSC приходят с задержкой ~2 дня
    start = end - dt.timedelta(days=days)
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{requests_quote(GSC_PROPERTY)}/searchAnalytics/query"
    body = {"startDate": str(start), "endDate": str(end), "dimensions": ["query", "page"], "rowLimit": 5000}
    r = s.post(url, json=body, timeout=30)
    if r.status_code != 200:
        print("[GSC] ошибка", r.status_code, r.text[:300]); return None
    out = []
    for row in r.json().get("rows", []):
        q, page = row["keys"]
        out.append(dict(src="Google", query=q, page=page, shows=row["impressions"], clicks=row["clicks"],
                        ctr=row["ctr"] * 100, pos=row["position"]))
    print(f"[GSC] строк: {len(out)} ({start} — {end})")
    return out


def requests_quote(s):
    from urllib.parse import quote
    return quote(s, safe="")


def ya_rows(days):
    tok = os.environ.get("YANDEX_WEBMASTER_TOKEN")
    f = keyfile("yandex-token.txt")
    if not tok and f.exists(): tok = f.read_text().strip()
    if not tok:
        print("[Вебмастер] нет токена — пропускаю"); return None
    import requests
    h = {"Authorization": f"OAuth {tok}"}
    base = "https://api.webmaster.yandex.net/v4"
    r = requests.get(f"{base}/user", headers=h, timeout=30)
    if r.status_code != 200:
        print("[Вебмастер] ошибка авторизации", r.status_code, r.text[:300]); return None
    uid = r.json()["user_id"]
    # ищем сайт среди добавленных в этот аккаунт Вебмастера
    r = requests.get(f"{base}/user/{uid}/hosts", headers=h, timeout=30)
    hosts = r.json().get("hosts", []) if r.status_code == 200 else []
    mine = [x for x in hosts if "semrack.ru" in x.get("host_id", "")]
    if not mine:
        print(f"[Вебмастер] в аккаунте (user_id {uid}) нет semrack.ru. Сайты аккаунта: "
              + (", ".join(x.get("host_id", "?") for x in hosts) or "нет ни одного")
              + ". Получите токен под тем Яндекс-аккаунтом, где подтверждён semrack.ru.")
        return None
    best = sorted(mine, key=lambda x: (not x.get("verified"), not x["host_id"].startswith("https")))[0]
    host = best["host_id"]
    print(f"[Вебмастер] сайт {host}, подтверждён: {best.get('verified')}")
    if not best.get("verified"):
        print("[Вебмастер] сайт добавлен, но права не подтверждены — подтвердите в Вебмастере."); return None
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    params = [("order_by", "TOTAL_SHOWS"), ("query_indicator", "TOTAL_SHOWS"), ("query_indicator", "TOTAL_CLICKS"),
              ("query_indicator", "AVG_SHOW_POSITION"), ("date_from", str(start)), ("date_to", str(end)), ("limit", 500)]
    r = requests.get(f"{base}/user/{uid}/hosts/{host}/search-queries/popular", headers=h, params=params, timeout=30)
    if r.status_code != 200:
        print("[Вебмастер] ошибка", r.status_code, r.text[:300]); return None
    out = []
    for q in r.json().get("queries", []):
        ind = q.get("indicators", {})
        shows, clicks = ind.get("TOTAL_SHOWS") or 0, ind.get("TOTAL_CLICKS") or 0
        out.append(dict(src="Яндекс", query=q["query_text"], page="", shows=shows, clicks=clicks,
                        ctr=clicks / shows * 100 if shows else 0, pos=ind.get("AVG_SHOW_POSITION") or 0))
    # статус индексации
    r = requests.get(f"{base}/user/{uid}/hosts/{host}/summary", headers=h, timeout=30)
    if r.status_code == 200:
        sm = r.json()
        print(f"[Вебмастер] в поиске страниц: {sm.get('searchable_pages_count')}, ИКС: {sm.get('sqi')}")
    print(f"[Вебмастер] запросов: {len(out)}")
    return out


def tips(rows):
    """Точки роста: правила, по которым стоит дорабатывать страницы."""
    t = []
    for r in rows:
        if r["shows"] < 5: continue
        if 4 <= r["pos"] <= 20:
            t.append((r, "Близко к топу", f"Позиция {r['pos']:.1f}. Добавьте запрос «{r['query']}» в title/H2, ответьте на него в блоке «Коротко» или FAQ."))
        if r["pos"] <= 5 and r["ctr"] < 3 and r["shows"] >= 20:
            t.append((r, "Низкий CTR", f"Высокая позиция, но CTR {r['ctr']:.1f}%. Перепишите title и description: цифры, год, выгода."))
    return sorted(t, key=lambda x: -x[0]["shows"])


def report(rows, out):
    def tr(r):
        page = r["page"].replace(SITE.rstrip("/"), "") or "—"
        return (f"<tr><td>{r['src']}</td><td>{html.escape(r['query'])}</td><td>{html.escape(page)}</td>"
                f"<td>{r['shows']}</td><td>{r['clicks']}</td><td>{r['ctr']:.1f}%</td><td>{r['pos']:.1f}</td></tr>")
    tot = lambda src, k: sum(r[k] for r in rows if r["src"] == src)
    tp = tips(rows)
    css = ("body{font:15px/1.5 system-ui,sans-serif;max-width:1100px;margin:30px auto;padding:0 16px;color:#16181d}"
           "table{border-collapse:collapse;width:100%;margin:8px 0 22px}td,th{border-bottom:1px solid #e4e7ec;padding:6px 8px;text-align:left}"
           "th{background:#f6f7f9}.s{display:flex;gap:12px;flex-wrap:wrap}.s div{background:#f6f7f9;border-radius:12px;padding:12px 20px}.s b{display:block;font-size:26px}")
    head = "<tr><th>Поиск</th><th>Запрос</th><th>Страница</th><th>Показы</th><th>Клики</th><th>CTR</th><th>Позиция</th></tr>"
    body = [f"<h1>Поисковые данные semrack.ru</h1><p>{dt.date.today():%d.%m.%Y}</p><div class=s>"]
    for src in ("Google", "Яндекс"):
        body.append(f"<div><b>{tot(src,'shows')}</b>показов {src}</div><div><b>{tot(src,'clicks')}</b>кликов {src}</div>")
    body.append("</div><h2>Точки роста</h2>")
    body.append("<table><tr><th>Тип</th><th>Запрос</th><th>Показы</th><th>Что сделать</th></tr>" + "".join(
        f"<tr><td>{k}</td><td>{html.escape(r['query'])}</td><td>{r['shows']}</td><td>{html.escape(a)}</td></tr>" for r, k, a in tp[:50])
        + "</table>" if tp else "<p>Пока мало данных: точки роста появятся, когда у запросов будет хотя бы 5 показов.</p>")
    body.append("<h2>Все запросы</h2><table>" + head + "".join(tr(r) for r in sorted(rows, key=lambda r: -r["shows"])[:500]) + "</table>")
    Path(out + ".html").write_text(f'<!doctype html><html lang="ru"><meta charset="utf-8"><title>Поисковые данные</title><style>{css}</style>{"".join(body)}</html>', encoding="utf-8")
    Path(out + ".json").write_text(json.dumps(dict(rows=rows, tips=[dict(r, type=k, action=a) for r, k, a in tp]), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Отчёт: {out}.html, точек роста: {len(tp)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--out", default="search-report")
    a = ap.parse_args()
    rows = (gsc_rows(a.days) or []) + (ya_rows(a.days) or [])
    report(rows, a.out)


if __name__ == "__main__":
    main()
