# Замер GEO в Яндексе («Быстрый ответ ИИ»)

Как повторить: для каждого вопроса открыть `https://ya.ru/search/?text=<вопрос>` во встроенном браузере,
подождать 4 с и выполнить скрипт ниже. Результаты складывать в `reports/geo-ГГГГ-ММ-ДД.json`
(формат — как в первом замере 2026-11-18). Капчу не обходить: если появилась — пауза, решает человек.

## Вопросы → целевая страница
| Вопрос | Страница |
|---|---|
| сколько берёт ozon с продавца | /ozon/ |
| какая комиссия на wildberries 2026 | /wildberries/ |
| как рассчитать юнит экономику маркетплейс | / |
| как посчитать логистику wildberries по литражу | /wildberries/logistika/ |
| как рассчитать процент выкупа вб | /vykup/ |
| чем наценка отличается от маржи | /nacenka-i-marzha/ |
| fbo или fbs что выгоднее | /fbo-ili-fbs/ |
| как рассчитать себестоимость товара для маркетплейса | /sebestoimost/ |
| как посчитать дрр | /drr/ |
| как выделить ндс 22 из суммы | /nds-kalkulyator/ |
| как посчитать оборачиваемость товара в днях | /oborachivaemost/ |
| сколько стоит авито доставка для продавца | /avito/ |
| комиссия яндекс маркет для продавцов | /yandex-market/ |
| ндс для селлеров на усн 2026 | /nalogi/ |
| калькулятор юнит экономики для маркетплейсов | / |

## Скрипт разбора выдачи
```js
const host=h=>{try{return new URL(h).hostname.replace(/^www\./,'')}catch(e){return ''}};
const bad=h=>!h||/^(ya\.ru|yandex\.ru|yabs\.yandex\.ru|passport\.yandex\.ru)$/.test(h);
const ai=document.querySelector('li.serp-item__futuris-snippet');
const aiLinks=ai?[...new Set([...ai.querySelectorAll('a[href^="http"]')].map(a=>host(a.href)).filter(h=>!bad(h)))]:null;
const org=[...document.querySelectorAll('li.serp-item')].filter(li=>li!==ai&&!/Промо|Реклама/.test(li.innerText.slice(0,300)))
  .map(li=>[...li.querySelectorAll('a[href^="http"]')].map(x=>host(x.href)).find(h=>!bad(h))||'').filter(Boolean);
({q:document.title.split(' — ')[0], captcha:/captcha/.test(location.href), ai:aiLinks, org:org.slice(0,10)})
```
