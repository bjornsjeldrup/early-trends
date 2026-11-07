/* Early Trends — Amazon affiliate click events.
   Clicks on amazon.* links with tag=earlytrends-20 (Where to buy, photo credits, source lists)
   send a GoatCounter event and, when gtag exists, a Google Analytics affiliate_click.
   This file only listens. It does not change href, the Associates tag, or navigation.
   New pages copied from trends/how-we-spot-trends.html or any existing page must keep
   the script tag so those clicks stay tracked. */
(function () {
  var AFFILIATE_TAG = 'earlytrends-20';
  var SKIP_PAGE = { index: 1, 'how-we-spot-trends': 1 };

  function cleanText(node) {
    if (!node) return '';
    return (node.textContent || '').replace(/\s+/g, ' ').trim();
  }

  function slugFromHref(href) {
    if (!href) return '';
    var raw = String(href).trim().split('#')[0].split('?')[0];
    if (raw.indexOf('./') === 0) raw = raw.slice(2);
    var match = raw.match(/(?:^|\/)trends\/([a-z0-9-]+)\.html$/i);
    if (!match && /\/trends\//i.test(location.pathname || '') && /^[a-z0-9-]+\.html$/i.test(raw)) {
      match = raw.match(/^([a-z0-9-]+)\.html$/i);
    }
    if (!match) return '';
    var slug = match[1].toLowerCase();
    if (SKIP_PAGE[slug]) return '';
    return slug;
  }

  function pageProductSlug() {
    var match = (location.pathname || '').match(/\/trends\/([a-z0-9-]+)\.html$/i);
    if (!match) return '';
    var slug = match[1].toLowerCase();
    if (SKIP_PAGE[slug]) return '';
    return slug;
  }

  function firstSlugIn(root) {
    if (!root || !root.querySelectorAll) return '';
    var links = root.querySelectorAll('a[href]');
    for (var i = 0; i < links.length; i++) {
      var slug = slugFromHref(links[i].getAttribute('href'));
      if (slug) return slug;
    }
    return '';
  }

  function pageLinksTo(slug) {
    var links = document.getElementsByTagName('a');
    for (var i = 0; i < links.length; i++) {
      if (slugFromHref(links[i].getAttribute('href')) === slug) return true;
    }
    return false;
  }

  function currentWeekSlug(anchor) {
    if (anchor.closest('#previous-weeks')) return '';
    var img = document.querySelector('#current-week img[src*="assets/products/"]');
    if (!img) return '';
    var match = (img.getAttribute('src') || '').match(/assets\/products\/([a-z0-9-]+)\./i);
    if (!match) return '';
    var slug = match[1].toLowerCase();
    return pageLinksTo(slug) ? slug : '';
  }

  function nearestSlug(anchor) {
    var links = document.getElementsByTagName('a');
    var before = '';
    var seen = false;
    for (var i = 0; i < links.length; i++) {
      var link = links[i];
      if (link === anchor) {
        seen = true;
        continue;
      }
      if (link.closest && link.closest('#previous-weeks')) {
        if (seen) break;
        continue;
      }
      var slug = slugFromHref(link.getAttribute('href'));
      if (!slug) continue;
      if (!seen) before = slug;
      else return slug;
    }
    return before;
  }

  function pathFallback() {
    var path = (location.pathname || '/').replace(/\/index\.html$/i, '/').replace(/\.html$/i, '');
    var bits = path.split('/').filter(Boolean);
    var last = bits.length ? bits[bits.length - 1].toLowerCase() : 'home';
    if (last === 'early-trends') return 'home';
    return last;
  }

  function productSlug(anchor) {
    var page = pageProductSlug();
    if (page) return page;
    var card = anchor.closest('.trend-card');
    if (card) {
      var fromCard = firstSlugIn(card);
      if (fromCard) return fromCard;
    }
    var archiveItem = anchor.closest('#previous-weeks li');
    if (archiveItem) {
      var fromArchive = firstSlugIn(archiveItem);
      if (fromArchive) return fromArchive;
    }
    return currentWeekSlug(anchor) || nearestSlug(anchor) || pathFallback();
  }

  function productTitle(anchor) {
    var card = anchor.closest('.trend-card');
    if (card) {
      var cardName = cleanText(card.querySelector('h3'));
      if (cardName) return cardName;
    }
    if (pageProductSlug()) {
      var pageName = cleanText(document.querySelector('main h1'));
      if (pageName) return pageName;
    }
    var weekName = cleanText(document.querySelector('#current-week h1'));
    if (weekName && !anchor.closest('#previous-weeks')) return weekName;
    return cleanText(anchor);
  }

  function isTrackedAffiliate(anchor) {
    var href = anchor.getAttribute('href') || '';
    if (href.indexOf('amazon.') === -1) return false;
    try {
      var url = new URL(href, window.location.href);
      var host = url.hostname.toLowerCase();
      if (!/(^|\.)amazon\./.test(host)) return false;
      return url.searchParams.get('tag') === AFFILIATE_TAG;
    } catch (err) {
      return false;
    }
  }

  function sendGoat(payload) {
    function send() {
      var gc = window.goatcounter;
      if (!gc || typeof gc.count !== 'function') return false;
      gc.count(payload);
      return true;
    }
    try {
      if (send()) return;
    } catch (err) {
      return;
    }
    window.setTimeout(function () {
      try { send(); } catch (err) {}
    }, 400);
  }

  function track(anchor) {
    if (!isTrackedAffiliate(anchor)) return;
    var slug = productSlug(anchor);
    var title = productTitle(anchor) || slug;
    sendGoat({
      path: 'amazon-click/' + slug,
      title: title,
      event: true
    });
    if (typeof window.gtag === 'function') {
      window.gtag('event', 'affiliate_click', {
        product_slug: slug,
        product_name: title,
        link_url: anchor.getAttribute('href'),
        page_path: location.pathname,
        transport_type: 'beacon'
      });
    }
  }

  function clickTarget(node) {
    if (!node) return null;
    if (node.nodeType === 3) node = node.parentElement;
    return node && node.closest ? node.closest('a[href*="amazon."]') : null;
  }

  document.addEventListener('click', function (event) {
    var anchor = clickTarget(event.target);
    if (!anchor) return;
    try {
      track(anchor);
    } catch (err) {}
  });
})();
