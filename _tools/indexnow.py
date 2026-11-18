#!/usr/bin/env python3
"""Сообщить Яндексу (и другим поисковикам IndexNow) о новых/изменённых страницах.
Запуск: python3 _tools/indexnow.py            — все страницы из sitemap.xml
        python3 _tools/indexnow.py /ozon/ /    — только указанные пути
Ключ — файл <ключ>.txt в корне сайта."""
import glob, json, os, re, sys
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "semrack.ru"
key = next(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(ROOT, "*.txt"))
           if re.fullmatch(r"[0-9a-f]{32}\.txt", os.path.basename(f)))
if len(sys.argv) > 1:
    urls = [f"https://{HOST}{p}" for p in sys.argv[1:]]
else:
    urls = re.findall(r"<loc>(.*?)</loc>", open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read())
body = json.dumps({"host": HOST, "key": key, "keyLocation": f"https://{HOST}/{key}.txt", "urlList": urls}).encode()
req = Request("https://yandex.com/indexnow", data=body, headers={"Content-Type": "application/json; charset=utf-8"})
with urlopen(req, timeout=20) as r:
    print(r.status, "— отправлено URL:", len(urls))
