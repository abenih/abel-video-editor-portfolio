/* ============================================================
   Owner edit mode — staff only.

   Kept out of main.js on purpose: a syntax error in one file must not take the
   other down. Every badge stays a real link to a real, working page; this file
   only upgrades that link into a docked side panel that saves in place. If
   fetch, FormData or DOMParser are missing, nothing here binds and the plain
   links keep working.

   Security: request URLs are only ever built from a registry key the server
   printed plus same-origin paths this file constructed. Server HTML is moved
   across with importNode, never re-serialised through a string.
   ============================================================ */
(function () {
  'use strict';

  var script = document.currentScript;
  var urlTemplate = script ? script.getAttribute('data-panel-url-template') || '' : '';
  var STORAGE_KEY = 'portfolio:edit-mode';
  var KEY_MARKER = '__key__';
  var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), '
    + 'textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
  /* Badges are injected here; .edit-tool entries are server-rendered links that open the same panel. */
  var TRIGGER = '.edit-badge, .edit-tool';

  var panelPrefix = '';
  var canEnhance = !!(window.fetch && window.FormData && window.DOMParser && window.URL);

  var panel = null;
  var panelBody = null;
  var panelTitle = null;
  var currentUrl = '';
  var currentKey = '';
  var lastTrigger = null;
  /* The form exactly as the server last sent it — anything else means unsaved work. */
  var savedSignature = '';
  var rejectedSave = false;

  function collect(root, selector) {
    var found = Array.prototype.slice.call(root.querySelectorAll(selector));
    if (root.nodeType === 1 && root.matches(selector)) found.unshift(root);
    return found;
  }

  function reducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  /* Modified/middle clicks must keep opening the full page in a new tab. */
  function isPlainClick(e) {
    return e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey;
  }

  function panelUrl(el, key) {
    var section = el.closest('[id]');
    var back = window.location.pathname + window.location.search;
    if (section && section.id) back += '#' + section.id;
    var url = urlTemplate.replace(KEY_MARKER, encodeURIComponent(key));
    // Regions that edit one specific row name it here; the server still decides the table.
    var pk = el.getAttribute('data-edit-pk');
    if (pk && /^[0-9]+$/.test(pk)) url += pk + '/';
    return url + '?next=' + encodeURIComponent(back);
  }

  function addBadge(el) {
    var key = el.getAttribute('data-edit-key');
    if (!key) return;
    // A toolbar entry is already its own trigger; it just needs to know where to return to.
    if (el.classList.contains('edit-tool')) {
      el.setAttribute('href', panelUrl(el, key));
      return;
    }
    if (el.querySelector(':scope > .edit-badge')) return;

    var badge = document.createElement('a');
    badge.className = 'edit-badge';
    badge.href = panelUrl(el, key);
    badge.setAttribute('data-edit-badge-for', key);

    var pencil = document.createElement('span');
    pencil.className = 'edit-badge-pencil';
    pencil.setAttribute('aria-hidden', 'true');
    pencil.textContent = '\u270E';

    var label = el.getAttribute('data-edit-label') || 'this part';
    badge.appendChild(pencil);
    badge.appendChild(document.createTextNode('Edit ' + label));
    badge.setAttribute('aria-label', 'Edit ' + label);

    el.insertBefore(badge, el.firstChild);
  }

  function markRegions(root) {
    collect(root, '[data-edit-key]').forEach(addBadge);
  }

  function regionNode(scope, key) {
    var match = null;
    collect(scope, '[data-edit-key]').forEach(function (el) {
      if (!match && el.getAttribute('data-edit-key') === key) match = el;
    });
    return match;
  }

  /* ---------- the panel shell ---------- */

  function buildPanel() {
    panel = document.createElement('aside');
    panel.id = 'editPanel';
    panel.className = 'edit-panel';
    panel.hidden = true;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Edit panel');

    var bar = document.createElement('div');
    bar.className = 'edit-panel-bar';

    panelTitle = document.createElement('span');
    panelTitle.className = 'edit-panel-bar-title';
    panelTitle.textContent = 'Editing';

    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'edit-panel-close';
    close.setAttribute('aria-label', 'Close the edit panel');
    close.textContent = '\u00D7';
    close.addEventListener('click', function () { closePanel(); });

    bar.appendChild(panelTitle);
    bar.appendChild(close);

    panelBody = document.createElement('div');
    panelBody.className = 'edit-panel-body';

    panel.appendChild(bar);
    panel.appendChild(panelBody);
    panel.addEventListener('click', onPanelClick);
    panel.addEventListener('submit', onPanelSubmit);
    panel.addEventListener('keydown', onPanelKeydown);
    document.body.appendChild(panel);
    return panel;
  }

  function setBusy(on) {
    if (!panel) return;
    panel.classList.toggle('is-busy', on);
    panel.setAttribute('aria-busy', String(on));
  }

  /* The Save button is the double-submit guard: on a slow connection a second
     click would post the same new item twice. The label carries the state too,
     so it is announced and not only greyed out. */
  function setSaving(on) {
    var button = panelBody && panelBody.querySelector('.panel-form button[type="submit"]');
    if (!button) return;
    if (on) {
      button.setAttribute('data-idle-label', button.textContent);
      button.textContent = 'Saving\u2026';
      button.disabled = true;
      return;
    }
    if (button.hasAttribute('data-idle-label')) {
      button.textContent = button.getAttribute('data-idle-label');
      button.removeAttribute('data-idle-label');
    }
    button.disabled = false;
    // Disabling a focused button drops focus to the page behind the panel.
    if (document.activeElement === document.body) button.focus();
  }

  /* ---------- unsaved work ---------- */

  function formSignature() {
    var form = panelBody && panelBody.querySelector('.panel-form');
    if (!form) return '';
    var parts = [];
    // Files arrive as File objects; the chosen name is enough to spot a new pick.
    new FormData(form).forEach(function (value, name) {
      parts.push(name + '=' + (typeof value === 'string' ? value : value.name));
    });
    return parts.join('\n');
  }

  function isDirty() {
    // A rejected save is still the owner's typing, even though the server sent it back.
    return rejectedSave || formSignature() !== savedSignature;
  }

  function discardOk() {
    return !isDirty()
      || window.confirm('Your changes haven\u2019t been saved yet. Close this and lose them?');
  }

  function notice(text, kind) {
    if (!panelBody) return;
    var old = panelBody.querySelector('.panel-notice');
    if (old) old.remove();
    var box = document.createElement('p');
    box.className = 'panel-notice panel-notice-' + (kind || 'ok');
    box.setAttribute('role', 'status');
    box.textContent = text;
    panelBody.insertBefore(box, panelBody.firstChild);
  }

  function panelFetch(url, options) {
    options = options || {};
    options.credentials = 'same-origin';
    options.headers = Object.assign({ 'X-Panel': '1' }, options.headers || {});
    return fetch(url, options);
  }

  function parse(text) {
    return new DOMParser().parseFromString(text, 'text/html');
  }

  /* Moves the server's own nodes across — no HTML is ever rebuilt from strings. */
  function showFragment(doc, sourceUrl) {
    var fragment = doc.querySelector('[data-panel-key]');
    if (!fragment) return false;

    currentUrl = sourceUrl;
    currentKey = fragment.getAttribute('data-panel-key') || '';
    panelBody.textContent = '';
    panelBody.appendChild(document.importNode(fragment, true));

    var form = panelBody.querySelector('.panel-form');
    // The fragment posts to itself; in the panel "itself" is the page, so say it outright.
    if (form) form.setAttribute('action', sourceUrl);

    var heading = panelBody.querySelector('.panel-title');
    if (heading) {
      panelTitle.textContent = heading.textContent;
      panel.setAttribute('aria-label', heading.textContent);
    }
    savedSignature = formSignature();
    rejectedSave = false;
    return true;
  }

  function focusPanel() {
    var errored = panelBody.querySelector('.errorlist, .form-errors');
    var row = errored && errored.closest ? errored.closest('.form-row, .formset-row') : null;
    var target = (row && row.querySelector('input:not([type="hidden"]), textarea, select'))
      || panelBody.querySelector('input:not([type="hidden"]), textarea, select, a[href], button');
    if (target) target.focus({ preventScroll: true });
  }

  function revealRegion(key) {
    var node = regionNode(document, key);
    if (!node) return;
    node.scrollIntoView({ block: 'center', behavior: reducedMotion() ? 'auto' : 'smooth' });
  }

  function openPanel(url, trigger, regionKey) {
    if (panel && !panel.hidden && !discardOk()) return;
    if (trigger) lastTrigger = trigger;
    if (!panel) buildPanel();
    panel.hidden = false;
    document.body.classList.add('panel-open');
    setBusy(true);

    return panelFetch(url)
      .then(function (res) {
        if (!res.ok) throw new Error('panel ' + res.status);
        return res.text();
      })
      .then(function (text) {
        if (!showFragment(parse(text), url)) throw new Error('no fragment');
        setBusy(false);
        if (regionKey) revealRegion(regionKey);
        focusPanel();
      })
      .catch(function () {
        setBusy(false);
        closePanel(true);
        window.location.href = url;
      });
  }

  function closePanel(force) {
    if (!panel || panel.hidden) return;
    if (!force && !discardOk()) return;
    panel.hidden = true;
    panelBody.textContent = '';
    document.body.classList.remove('panel-open');
    currentUrl = '';
    currentKey = '';
    savedSignature = '';
    rejectedSave = false;
    // swapRegion re-points lastTrigger at the rebuilt badge, so this survives a save.
    if (lastTrigger && document.contains(lastTrigger)) lastTrigger.focus();
    lastTrigger = null;
  }

  /* ---------- saving ---------- */

  /* Colours belong to no region — they are one <style> block in the head. */
  function syncThemeVars(pageDoc) {
    var incoming = pageDoc.querySelector('style[data-theme-vars]');
    var current = document.querySelector('style[data-theme-vars]');
    // textContent, so this is CSS text either way and never parsed as markup.
    if (incoming && current) current.textContent = incoming.textContent;
  }

  function swapRegion(pageDoc, key) {
    syncThemeVars(pageDoc);
    var incoming = regionNode(pageDoc, key);
    var target = regionNode(document, key);
    if (!incoming || !target) return;

    var node = document.importNode(incoming, true);
    // Already-revealed regions must not fade out and back in on every save.
    if (target.classList.contains('in-view')) node.classList.add('in-view');
    target.replaceWith(node);
    markRegions(node);
    if (typeof window.portfolioInit === 'function') window.portfolioInit(node);
    if (lastTrigger && !document.contains(lastTrigger)) {
      lastTrigger = node.matches(TRIGGER) ? node : node.querySelector(':scope > .edit-badge');
    }
  }

  function refreshPage(key) {
    return panelFetch(window.location.href)
      .then(function (res) { return res.text(); })
      .then(function (text) { swapRegion(parse(text), key); });
  }

  /* The open form has to be re-read after a save, or an extra formset row would
     be posted a second time and create the same item twice. */
  function refreshFragment(url) {
    return panelFetch(url)
      .then(function (res) { return res.text(); })
      .then(function (text) { showFragment(parse(text), url); })
      .catch(function () { /* The save landed; a stale form beats a false error. */ });
  }

  function savePanel(form) {
    var token = form.querySelector('input[name="csrfmiddlewaretoken"]');
    var action = form.getAttribute('action') || currentUrl;
    if (!token || !action) { form.submit(); return; }

    var savedKey = currentKey;
    setBusy(true);
    setSaving(true);

    panelFetch(action, {
      method: 'POST',
      body: new FormData(form),
      headers: { 'X-CSRFToken': token.value },
    })
      .then(function (res) {
        return res.text().then(function (text) { return { res: res, doc: parse(text) }; });
      })
      .then(function (out) {
        setBusy(false);
        setSaving(false);
        if (!out.res.ok) {
          notice('That didn\u2019t save. Open the full editor and try again.', 'error');
          rejectedSave = true;
          return null;
        }

        // The view redirects on success and re-renders the form on failure.
        if (!out.res.redirected) {
          if (!showFragment(out.doc, action)) {
            window.location.href = action;
            return null;
          }
          notice('Nothing was saved \u2014 please check the highlighted fields.', 'error');
          rejectedSave = true;
          focusPanel();
          return null;
        }

        var landed = new URL(out.res.url);
        var landedOnPanel = landed.pathname.indexOf(panelPrefix) === 0;
        var done;

        if (landedOnPanel) {
          // A brand-new nested item redirects to its own edit panel — keep it open.
          showFragment(out.doc, landed.pathname + landed.search);
          done = refreshPage(savedKey);
        } else if (landed.pathname === window.location.pathname) {
          // The redirect already re-rendered this page, so reuse it.
          swapRegion(out.doc, savedKey);
          done = refreshFragment(action);
        } else {
          done = refreshPage(savedKey).then(function () { return refreshFragment(action); });
        }

        return done.then(function () {
          notice('Saved \u2713 \u2014 this is now live.', 'ok');
        });
      })
      .catch(function () {
        setBusy(false);
        setSaving(false);
        rejectedSave = true;
        notice('That didn\u2019t save. Open the full editor and try again.', 'error');
      });
  }

  /* ---------- events ---------- */

  function onPanelClick(e) {
    var link = e.target.closest ? e.target.closest('a[href]') : null;
    if (!link || !isPlainClick(e)) return;

    var url = new URL(link.href, window.location.href);
    if (url.origin !== window.location.origin) return;

    if (url.pathname.indexOf(panelPrefix) === 0) {
      e.preventDefault();
      openPanel(url.pathname + url.search, null, '');
    } else if (url.pathname === window.location.pathname) {
      e.preventDefault();
      closePanel();
    }
  }

  function onPanelSubmit(e) {
    var form = e.target;
    // The delete form keeps its plain full-page POST: it needs the confirm and a reload.
    if (!form.classList || !form.classList.contains('panel-form')) return;
    e.preventDefault();
    savePanel(form);
  }

  function onPanelKeydown(e) {
    if (e.key !== 'Tab') return;
    var items = Array.prototype.filter.call(panel.querySelectorAll(FOCUSABLE), function (el) {
      return el.offsetWidth || el.offsetHeight || el === document.activeElement;
    });
    if (!items.length) return;

    var firstEl = items[0];
    var lastEl = items[items.length - 1];
    if (e.shiftKey && document.activeElement === firstEl) {
      e.preventDefault();
      lastEl.focus();
    } else if (!e.shiftKey && document.activeElement === lastEl) {
      e.preventDefault();
      firstEl.focus();
    }
  }

  function onBadgeClick(e) {
    var badge = e.target.closest ? e.target.closest(TRIGGER) : null;
    if (!badge || !isPlainClick(e)) return;
    e.preventDefault();
    var region = badge.closest('[data-edit-key]');
    openPanel(badge.getAttribute('href'), badge, region ? region.getAttribute('data-edit-key') : '');
  }

  function init() {
    if (!urlTemplate || urlTemplate.indexOf(KEY_MARKER) === -1) return;
    if (!document.querySelectorAll('[data-edit-key]').length) return;

    panelPrefix = urlTemplate.slice(0, urlTemplate.indexOf(KEY_MARKER));
    markRegions(document);

    if (canEnhance) {
      document.addEventListener('click', onBadgeClick);
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && panel && !panel.hidden) {
          e.preventDefault();
          closePanel();
        }
      });
    }

    var toggle = document.getElementById('editModeToggle');
    if (!toggle) return;

    var apply = function (on) {
      document.body.classList.toggle('edit-mode', on);
      toggle.setAttribute('aria-pressed', String(on));
      toggle.textContent = on ? 'Done editing' : 'Edit this page';
      if (!on) closePanel();
    };

    toggle.hidden = false;
    apply(window.sessionStorage.getItem(STORAGE_KEY) === '1');

    toggle.addEventListener('click', function () {
      var on = !document.body.classList.contains('edit-mode');
      apply(on);
      try {
        window.sessionStorage.setItem(STORAGE_KEY, on ? '1' : '0');
      } catch (e) {
        /* Private mode with storage blocked — the toggle still works for this page. */
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
