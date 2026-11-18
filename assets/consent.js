/* Cookie-баннер (информирование): Яндекс Метрика работает, пока посетитель её не отключил. semrack.ru */
(function () {
  'use strict';
  var KEY = 'cookie_consent';
  var TTL = 365 * 24 * 3600 * 1000; // согласие спрашиваем заново через год

  function read() {
    try { var v = JSON.parse(localStorage.getItem(KEY) || 'null'); return v && Date.now() - v.t < TTL ? v.v : null; } catch (e) { return null; }
  }
  function save(v) { try { localStorage.setItem(KEY, JSON.stringify({ v: v, t: Date.now() })); } catch (e) {} }

  function loadMetrika() {
    if (window.ym) return;
    /* Yandex.Metrika counter */
    (function(m,e,t,r,i,k,a){
        m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
        m[i].l=1*new Date();
        for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
        k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)
    })(window, document,'script','https://mc.yandex.ru/metrika/tag.js?id=114271586', 'ym');
    ym(114271586, 'init', {ssr:true, webvisor:true, clickmap:true, ecommerce:"dataLayer", referrer: document.referrer, url: location.href, accurateTrackBounce:true, trackLinks:true});
    /* /Yandex.Metrika counter */
  }

  function removeMetrikaCookies() {
    document.cookie.split(';').forEach(function (c) {
      var name = c.split('=')[0].trim();
      if (/^_ym|^yandexuid|^ymex/.test(name)) {
        document.cookie = name + '=; Max-Age=0; path=/';
        document.cookie = name + '=; Max-Age=0; path=/; domain=.' + location.hostname;
      }
    });
    try { Object.keys(localStorage).forEach(function (k) { if (/^_ym/.test(k)) localStorage.removeItem(k); }); } catch (e) {}
  }

  function banner() {
    if (document.getElementById('cc')) return;
    var d = document.createElement('div');
    d.id = 'cc'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-label', 'Согласие на cookie');
    d.innerHTML =
      '<p>Мы используем cookie и Яндекс Метрику для статистики посещений. Нажимая «Понятно», вы даёте ' +
      '<a href="/soglasie/">согласие на обработку данных</a> по <a href="/politika/">политике конфиденциальности</a>. ' +
      'Не согласны — нажмите «Отключить».</p>' +
      '<div class="cc-b"><button type="button" data-v="yes">Понятно</button><button type="button" data-v="no" class="cc-no">Отключить</button></div>';
    d.addEventListener('click', function (e) {
      var v = e.target.getAttribute && e.target.getAttribute('data-v');
      if (!v) return;
      save(v); d.remove();
      if (v === 'yes') loadMetrika();
      else { removeMetrikaCookies(); if (window.ym) location.reload(); }
    });
    document.body.appendChild(d);
  }

  // ссылка «Настройки cookie» в подвале снова открывает баннер
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('[data-cookie-settings]');
    if (a) { e.preventDefault(); banner(); }
  });

  var c = read();
  if (c !== 'no') loadMetrika();
  if (c === null) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', banner); else banner();
  }
})();
