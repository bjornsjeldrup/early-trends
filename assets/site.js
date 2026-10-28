/* Early Trends — tiny vanilla JS. Site works fully without it. */
(function () {
  document.documentElement.classList.remove('no-js');

  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // Category filter chips on the trends listing page
  var chips = document.querySelectorAll('[data-filter]');
  var cards = document.querySelectorAll('[data-category]');
  if (chips.length && cards.length) {
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        var f = chip.getAttribute('data-filter');
        chips.forEach(function (c) { c.setAttribute('aria-pressed', c === chip ? 'true' : 'false'); });
        cards.forEach(function (card) {
          var match = f === 'all' || card.getAttribute('data-category').split(' ').indexOf(f) !== -1;
          card.hidden = !match;
        });
      });
    });
  }

  // Current year in footer
  var y = document.getElementById('year');
  if (y) y.textContent = new Date().getFullYear();

  // Magnifying-glass pupils follow the pointer. Centered when motion is reduced.
  var pupils = document.querySelectorAll('.brand-mark .pupil, .brand-mark .glint');
  var motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var MAX_SHIFT = 2.3;

  function centerPupils() {
    pupils.forEach(function (pupil) {
      pupil.setAttribute('cx', pupil.getAttribute('data-cx'));
      pupil.setAttribute('cy', pupil.getAttribute('data-cy'));
    });
  }

  function onPointerMove(event) {
    var marks = document.querySelectorAll('.brand-mark');
    marks.forEach(function (mark) {
      var rect = mark.getBoundingClientRect();
      var dx = event.clientX - (rect.left + rect.width / 2);
      var dy = event.clientY - (rect.top + rect.height / 2);
      var len = Math.hypot(dx, dy);
      var ox = 0;
      var oy = 0;
      if (len > 0.5) {
        var reach = Math.min(MAX_SHIFT, len / 28);
        ox = (dx / len) * reach;
        oy = (dy / len) * reach;
      }
      mark.querySelectorAll('.pupil, .glint').forEach(function (node) {
        var baseX = parseFloat(node.getAttribute('data-cx'));
        var baseY = parseFloat(node.getAttribute('data-cy'));
        node.setAttribute('cx', (baseX + ox).toFixed(2));
        node.setAttribute('cy', (baseY + oy).toFixed(2));
      });
    });
  }

  function bindEyes() {
    document.removeEventListener('pointermove', onPointerMove);
    if (motion.matches) {
      centerPupils();
      document.querySelectorAll('.brand-mark').forEach(function (mark) {
        mark.classList.remove('eyes-wide', 'eyes-blink');
      });
      return;
    }
    document.addEventListener('pointermove', onPointerMove);
  }

  var marks = document.querySelectorAll('.brand-mark');
  var blinkTimer = 0;
  var clickableSelector = 'a[href], button, [role="button"], summary, label, input[type="checkbox"], input[type="radio"], input[type="submit"], input[type="button"]';

  function clickableTarget(node) {
    return node && node.closest ? node.closest(clickableSelector) : null;
  }

  function setWide(on) {
    if (motion.matches) on = false;
    marks.forEach(function (mark) {
      mark.classList.toggle('eyes-wide', on);
    });
  }

  function blink() {
    if (motion.matches) return;
    marks.forEach(function (mark) { mark.classList.add('eyes-blink'); });
    window.clearTimeout(blinkTimer);
    blinkTimer = window.setTimeout(function () {
      marks.forEach(function (mark) { mark.classList.remove('eyes-blink'); });
    }, 150);
  }

  if (pupils.length) {
    bindEyes();
    if (motion.addEventListener) motion.addEventListener('change', bindEyes);
    else if (motion.addListener) motion.addListener(bindEyes);

    document.addEventListener('pointerover', function (event) {
      if (clickableTarget(event.target)) setWide(true);
    });
    document.addEventListener('pointerout', function (event) {
      if (!clickableTarget(event.target)) return;
      if (clickableTarget(event.relatedTarget)) return;
      setWide(false);
    });
    document.addEventListener('pointerdown', function () {
      blink();
    });
  }
})();
