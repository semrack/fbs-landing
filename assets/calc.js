/* Калькулятор юнит-экономики для маркетплейсов. semrack.ru */
(function () {
  'use strict';

  // Типовые значения на ноябрь 2026. Это примеры для старта: точные ставки — в личном кабинете продавца.
  var PRESETS = {
    wb: { name: 'Wildberries', commission: 30, acquiring: 2, logistics: 80, back: 50, buyout: 80, storage: 5 },
    ozon: { name: 'Ozon', commission: 45, acquiring: 1.5, logistics: 90, back: 40, buyout: 90, storage: 5 },
    ym: { name: 'Яндекс Маркет', commission: 20, acquiring: 2.8, logistics: 140, back: 60, buyout: 95, storage: 3 }
  };
  var COLORS = { cost: '#8a94a6', fee: '#5b3df5', logi: '#2f9bff', ads: '#f08a24', other: '#c3a3ff', tax: '#d6455d', profit: '#0a7d4f' };

  var root = document.getElementById('calc');
  if (!root) return;
  var $ = function (id) { return document.getElementById(id); };
  var num = function (id) { var v = parseFloat(String($(id).value).replace(',', '.')); return isFinite(v) ? v : 0; };
  var rub = function (v) { return (v < 0 ? '−' : '') + Math.abs(Math.round(v)).toLocaleString('ru-RU') + ' ₽'; };
  var pct = function (v) { return (isFinite(v) ? (Math.round(v * 10) / 10).toLocaleString('ru-RU') : '—') + '%'; };

  function compute(P, s) {
    var b = Math.min(Math.max(s.buyout, 1), 100) / 100;
    var logi = s.logistics + (1 - b) / b * (s.logistics + s.back); // логистика на одну выкупленную единицу с учётом невыкупов
    var fee = P * s.commission / 100 + P * s.acquiring / 100;
    var ads = P * s.ads / 100;
    var vat = s.vat > 0 ? P * s.vat / (100 + s.vat) : 0;
    var income = P - vat;
    var expenses = s.cost + fee + logi + s.storage + s.other + ads;
    var tax;
    if (s.tax === 'usn15') tax = Math.max((income - expenses) * s.taxRate / 100, income * 0.01);
    else tax = income * s.taxRate / 100;
    var profit = income - expenses - tax;
    return {
      fee: fee, logi: logi, ads: ads, vat: vat, tax: tax, profit: profit,
      other: s.storage + s.other, payout: P - fee - logi - s.storage,
      margin: P > 0 ? profit / P * 100 : NaN, roi: s.cost > 0 ? profit / s.cost * 100 : NaN
    };
  }

  function read() {
    return {
      cost: num('c-cost'), commission: num('c-commission'), acquiring: num('c-acquiring'),
      logistics: num('c-logistics'), back: num('c-back'), buyout: num('c-buyout') || 100,
      storage: num('c-storage'), other: num('c-other'), ads: num('c-ads'),
      tax: $('c-tax').value, taxRate: num('c-taxrate'), vat: num('c-vat')
    };
  }

  function solvePrice(s, targetMargin) {
    // цена, при которой маржа = targetMargin; бисекция, прибыль растёт с ценой
    var lo = 1, hi = 1e7;
    var f = function (P) { return compute(P, s).profit - P * targetMargin / 100; };
    if (f(hi) < 0) return NaN;
    for (var i = 0; i < 80; i++) { var mid = (lo + hi) / 2; if (f(mid) >= 0) hi = mid; else lo = mid; }
    return hi;
  }

  function render() {
    var P = num('c-price'), s = read(), r = compute(P, s);
    var big = $('r-profit');
    big.textContent = rub(r.profit);
    big.className = 'big ' + (r.profit >= 0 ? 'pos' : 'neg');
    $('r-margin').textContent = pct(r.margin);
    $('r-roi').textContent = pct(r.roi);
    $('r-payout').textContent = rub(r.payout);
    $('r-be').textContent = rub(solvePrice(s, 0));

    var parts = [
      ['cost', 'Себестоимость', s.cost], ['fee', 'Комиссия и эквайринг', r.fee],
      ['logi', 'Логистика с учётом невыкупов', r.logi], ['ads', 'Реклама', r.ads],
      ['other', 'Хранение и прочее', r.other], ['tax', 'Налоги (УСН + НДС)', r.tax + r.vat],
      ['profit', 'Прибыль', Math.max(r.profit, 0)]
    ];
    var total = parts.reduce(function (a, p) { return a + Math.max(p[2], 0); }, 0) || 1;
    $('r-bar').innerHTML = parts.map(function (p) {
      return '<i style="width:' + (Math.max(p[2], 0) / total * 100) + '%;background:' + COLORS[p[0]] + '"></i>';
    }).join('');
    $('r-legend').innerHTML = parts.map(function (p) {
      return '<li style="--c:' + COLORS[p[0]] + '"><em>' + p[1] + '</em><span>' + rub(p[2]) + (P > 0 ? ' · ' + pct(p[2] / P * 100) : '') + '</span></li>';
    }).join('');

    var t = solvePrice(s, num('c-target'));
    $('r-target').textContent = isFinite(t) ? rub(Math.ceil(t)) : 'недостижимо при этих ставках';
    try { localStorage.setItem('mpcalc', JSON.stringify(collect())); } catch (e) {}
  }

  function collect() {
    var o = {};
    root.querySelectorAll('input,select').forEach(function (el) { o[el.id] = el.value; });
    o.mp = current; return o;
  }

  var current = root.getAttribute('data-mp') || 'wb';
  function applyPreset(mp) {
    var p = PRESETS[mp]; current = mp;
    $('c-commission').value = p.commission; $('c-acquiring').value = p.acquiring;
    $('c-logistics').value = p.logistics; $('c-back').value = p.back;
    $('c-buyout').value = p.buyout; $('c-storage').value = p.storage;
    root.querySelectorAll('.tabs button').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.mp === mp); });
    render();
  }

  root.querySelectorAll('.tabs button').forEach(function (b) {
    b.addEventListener('click', function () { applyPreset(b.dataset.mp); });
  });
  $('c-tax').addEventListener('change', function () { $('c-taxrate').value = this.value === 'usn15' ? 15 : 6; render(); });
  root.addEventListener('input', render);

  // восстановление прошлых значений на этой же странице
  var saved = null;
  try { saved = JSON.parse(localStorage.getItem('mpcalc') || 'null'); } catch (e) {}
  if (saved && (saved.mp === current || root.hasAttribute('data-any'))) {
    current = saved.mp || current;
    Object.keys(saved).forEach(function (k) { if ($(k)) $(k).value = saved[k]; });
    root.querySelectorAll('.tabs button').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.mp === current); });
    render();
  } else applyPreset(current);
})();
