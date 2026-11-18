/* Узкие калькуляторы селлера. semrack.ru */
(function () {
  'use strict';
  var root = document.getElementById('tool');
  if (!root) return;
  var $ = function (id) { return document.getElementById(id); };
  var n = function (id) { var v = parseFloat(String($(id).value).replace(',', '.')); return isFinite(v) ? v : 0; };
  var rub = function (v, d) { if (!isFinite(v)) return '—'; var k = Math.pow(10, d || 0); return (v < 0 ? '−' : '') + (Math.round(Math.abs(v) * k) / k).toLocaleString('ru-RU') + ' ₽'; };
  var pct = function (v) { return isFinite(v) ? (Math.round(v * 10) / 10).toLocaleString('ru-RU') + '%' : '—'; };
  var num = function (v, d) { var k = Math.pow(10, d || 0); return isFinite(v) ? (Math.round(v * k) / k).toLocaleString('ru-RU') : '—'; };
  var set = function (id, t, cls) { var el = $(id); if (!el) return; el.textContent = t; if (cls !== undefined) el.className = cls; };

  var TOOLS = {
    // Логистика Wildberries по литражу
    'wb-logistics': function () {
      var liters = n('t-l') * n('t-w') * n('t-h') / 1000;
      var base = liters <= 1 ? n('t-base') : n('t-base') + (liters - 1) * n('t-extra');
      var withCoef = base * n('t-coef') / 100 * n('t-ktr');
      var irp = n('t-price') * n('t-irp') / 100;
      var total = withCoef + irp;
      set('o-liters', num(liters, 2) + ' л');
      set('o-base', rub(base, 2));
      set('o-coef', rub(withCoef, 2));
      set('o-irp', rub(irp, 2));
      set('o-total', rub(total, 2), 'big');
      var b = n('t-buyout') / 100;
      set('o-per-sale', b > 0 ? rub(total + (1 - b) / b * (total + n('t-back')), 0) : '—');
    },
    // Процент выкупа и стоимость невыкупов
    'buyout': function () {
      var orders = n('t-orders'), bought = n('t-bought');
      var b = orders > 0 ? Math.min(bought / orders, 1) : 0;
      var L = n('t-logi'), R = n('t-back');
      set('o-buyout', pct(b * 100), 'big');
      var perSale = b > 0 ? L + (1 - b) / b * (L + R) : NaN;
      set('o-per-sale', rub(perSale));
      set('o-loss', b > 0 ? rub(perSale - L) : '—');
      set('o-month', rub((orders - bought) * (L + R)));
      var rows = [30, 40, 50, 60, 70, 80, 90, 100].map(function (p) {
        var x = p / 100, v = L + (1 - x) / x * (L + R);
        return '<tr><td>' + p + '%</td><td>' + rub(v) + '</td><td>×' + num(v / L, 1) + '</td></tr>';
      }).join('');
      $('o-table').innerHTML = '<tr><th>Выкуп</th><th>Логистика на продажу</th><th>К тарифу</th></tr>' + rows;
    },
    // Наценка и маржа
    'markup': function () {
      var c = n('t-cost'), p = n('t-price');
      set('o-markup', c > 0 ? pct((p - c) / c * 100) : '—', 'big');
      set('o-margin', p > 0 ? pct((p - c) / p * 100) : '—');
      set('o-gross', rub(p - c));
      var m = n('t-target-markup');
      set('o-price-markup', rub(c * (1 + m / 100)));
      var g = n('t-target-margin');
      set('o-price-margin', g < 100 ? rub(c / (1 - g / 100)) : 'маржа должна быть меньше 100%');
    },
    // FBO или FBS
    'fbo-fbs': function () {
      var P = n('t-price'), C = n('t-cost'), b = n('t-buyout') / 100, q = n('t-qty');
      function unit(k, logi, back, extra) {
        var l = b > 0 ? logi + (1 - b) / b * (logi + back) : NaN;
        return P - C - P * k / 100 - l - extra;
      }
      var fbo = unit(n('t-k-fbo'), n('t-logi-fbo'), n('t-back'), n('t-store-fbo') + n('t-supply-fbo'));
      var fbs = unit(n('t-k-fbs'), n('t-logi-fbs'), n('t-back'), n('t-own-fbs'));
      set('o-fbo', rub(fbo), 'big ' + (fbo >= 0 ? 'pos' : 'neg'));
      set('o-fbs', rub(fbs), 'big ' + (fbs >= 0 ? 'pos' : 'neg'));
      var d = (fbo - fbs) * q;
      set('o-diff', Math.abs(d) < 1 ? 'Схемы примерно равны' :
        (d > 0 ? 'FBO выгоднее на ' : 'FBS выгоднее на ') + rub(Math.abs(d)) + ' в месяц');
    }
  };

  // Себестоимость единицы товара
  TOOLS['cost'] = function () {
    var qty = Math.max(n('t-qty'), 1), defect = Math.min(n('t-defect'), 99) / 100;
    var batch = n('t-buy') * qty + n('t-delivery') + n('t-customs') + n('t-batch-other');
    var perUnitVar = n('t-pack') + n('t-mark') + n('t-ff');
    var good = qty * (1 - defect);
    var unit = good > 0 ? batch / good + perUnitVar * qty / good : NaN;
    set('o-unit', rub(unit, 2), 'big');
    set('o-batch', rub(batch + perUnitVar * qty));
    set('o-good', num(good, 0) + ' шт');
    set('o-markup', n('t-buy') > 0 ? pct((unit / n('t-buy') - 1) * 100) : '—');
  };
  // ДРР
  TOOLS['drr'] = function () {
    var ads = n('t-ads'), rev = n('t-rev');
    set('o-drr', rev > 0 ? pct(ads / rev * 100) : '—', 'big');
    var P = n('t-price'), pre = n('t-pre');
    var maxDrr = P > 0 ? pre / P * 100 : NaN;
    set('o-max', pct(maxDrr));
    var cur = rev > 0 ? ads / rev * 100 : NaN;
    set('o-left', isFinite(cur) && isFinite(maxDrr) ? rub(pre - P * cur / 100) : '—');
    set('o-verdict', !isFinite(cur) || !isFinite(maxDrr) ? '' : cur < maxDrr ? 'Реклама окупается: ДРР ниже допустимого' : 'Реклама съедает всю прибыль: ДРР выше допустимого');
  };
  // НДС
  TOOLS['vat'] = function () {
    var s = n('t-sum'), r = n('t-rate'), mode = $('t-mode').value;
    var vat, net, gross;
    if (mode === 'out') { vat = s * r / (100 + r); net = s - vat; gross = s; }
    else { vat = s * r / 100; net = s; gross = s + vat; }
    set('o-vat', rub(vat, 2), 'big');
    set('o-net', rub(net, 2));
    set('o-gross', rub(gross, 2));
  };
  // Оборачиваемость
  TOOLS['turnover'] = function () {
    var stock = n('t-stock'), sold = n('t-sold'), days = Math.max(n('t-days'), 1);
    var perDay = sold / days;
    var d = perDay > 0 ? stock / perDay : NaN;
    set('o-days', isFinite(d) ? num(d, 1) + ' дн.' : '—', 'big');
    set('o-times', stock > 0 ? num(sold / stock, 2) + ' раза' : '—');
    set('o-perday', num(perDay, 1) + ' шт/день');
    set('o-store', isFinite(d) ? rub(n('t-store') * d, 2) : '—');
  };

  var fn = TOOLS[root.getAttribute('data-tool')];
  if (!fn) return;
  root.addEventListener('input', fn);
  fn();
})();
