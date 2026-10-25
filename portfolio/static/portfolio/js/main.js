/* ============================================================
   Public-site behaviours.

   Everything lives in window.portfolioInit(root) so the owner's edit panel can
   re-run it over a region it just swapped in. Two rules keep that safe: every
   lookup is scoped to `root` (which may be an element, not the document), and
   every binding is claimed once so a second pass over the same node cannot
   double-bind. Listeners that belong to window/document are bound with the
   element that owns them, which only ever appears once.
   ============================================================ */
(function () {
  'use strict';

  const bound = new WeakSet();
  let revealObserver = null;

  // Module-level so a region swap cannot orphan a playing frame: editor.js replaces
  // the node and calls portfolioInit again, but `active` outlives both.
  let active = null;
  let hoverTimer = null;
  let previewObserver = null;
  let lightboxReturnFocus = null;

  // The only origins an embed iframe may point at. Mirrors PROVIDER_ORIGINS in models.py.
  const ALLOWED_FRAME_ORIGINS = [
    'https://www.youtube-nocookie.com',
    'https://player.vimeo.com',
    'https://www.tiktok.com',
  ];

  // querySelectorAll skips `root` itself, and a swapped region is often the match.
  const collect = (root, selector) => {
    const found = Array.prototype.slice.call(root.querySelectorAll(selector));
    if (root.nodeType === 1 && root.matches(selector)) found.unshift(root);
    return found;
  };

  const first = (root, selector) => collect(root, selector)[0] || null;

  const claim = (el) => {
    if (bound.has(el)) return false;
    bound.add(el);
    return true;
  };

  const canHover = () => window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const saveData = () => !!(navigator.connection && navigator.connection.saveData);

  // Reduced motion and save-data take the same branch as touch: badge only, never hover.
  const hoverPreviewsAllowed = () => canHover() && !reducedMotion() && !saveData();

  /* ---------- Single-active media preview ---------- */

  const deactivate = (frame) => {
    if (!frame) return;
    frame.classList.remove('is-playing');
    const video = frame.querySelector('video.media-native');
    if (video) {
      video.pause();
      video.currentTime = 0;
    }
    // Removing the node is the uniform kill switch: it stops the picture *and* the
    // stream for every provider, with no third-party SDK. A postMessage pause would
    // leave a warm player downloading.
    const iframe = frame.querySelector('iframe');
    if (iframe) iframe.remove();
    if (active === frame) active = null;
  };

  const releaseActive = () => {
    if (active && !active.isConnected) {
      active = null;
      return;
    }
    deactivate(active);
  };

  const activate = (frame) => {
    if (active === frame && frame.classList.contains('is-playing')) return;
    releaseActive();
    active = frame;
    frame.classList.add('is-playing');

    if (frame.dataset.previewKind === 'file') {
      const video = frame.querySelector('video.media-native');
      if (!video) {
        deactivate(frame);
        return;
      }
      const started = video.play();
      if (started && started.catch) started.catch(() => deactivate(frame));
      return;
    }

    let url;
    try {
      url = new URL(frame.dataset.previewSrc || '', window.location.href);
    } catch (err) {
      deactivate(frame);
      return;
    }
    // Defence in depth: the server already rebuilds this URL from an extracted id,
    // but a template mistake must not be enough to frame an arbitrary origin.
    if (ALLOWED_FRAME_ORIGINS.indexOf(url.origin) === -1) {
      deactivate(frame);
      return;
    }

    const iframe = document.createElement('iframe');
    iframe.src = url.href;
    iframe.title = 'Video';
    iframe.setAttribute('allow', 'autoplay; encrypted-media; picture-in-picture; fullscreen');
    iframe.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    iframe.setAttribute('loading', 'lazy');
    iframe.setAttribute('allowfullscreen', '');
    // allow-scripts + allow-same-origin only voids a sandbox for a same-origin frame,
    // where the frame could reach out and drop its own sandbox attribute. These are
    // cross-origin, so "same-origin" means "same-origin as the video host" and the
    // pair is safe. allow-top-navigation is omitted on purpose.
    iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-popups allow-presentation');
    frame.appendChild(iframe);
  };

  const initMediaPreview = (root) => {
    const frames = collect(root, '.media-frame');
    if (!frames.length) return;

    if ('IntersectionObserver' in window && !previewObserver) {
      previewObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (!entry.target.isConnected) previewObserver.unobserve(entry.target);
          else if (!entry.isIntersecting && entry.target === active) deactivate(entry.target);
        });
      }, { threshold: 0 });
    }

    frames.forEach((frame) => {
      if (!claim(frame)) return;
      if (previewObserver) previewObserver.observe(frame);

      const badge = frame.querySelector('.play-badge');
      if (badge) {
        badge.addEventListener('click', (e) => {
          e.preventDefault();
          // The badge sits over a card link — a tap here must not open the lightbox.
          e.stopPropagation();
          if (frame.classList.contains('is-playing')) deactivate(frame);
          else activate(frame);
        });
      }

      if (!frame.dataset.hover || !hoverPreviewsAllowed()) return;
      frame.addEventListener('pointerenter', (e) => {
        // Some hybrids fire pointerenter for a touch as well as a real hover.
        if (e.pointerType === 'touch') return;
        window.clearTimeout(hoverTimer);
        hoverTimer = window.setTimeout(() => activate(frame), 120);
      });
      frame.addEventListener('pointerleave', (e) => {
        if (e.pointerType === 'touch') return;
        window.clearTimeout(hoverTimer);
        deactivate(frame);
      });
    });
  };

  /* ---------- Click-to-expand lightbox ---------- */

  const closeLightbox = () => {
    const box = document.getElementById('mediaLightbox');
    if (!box || box.hidden) return;
    releaseActive();
    // Emptying the body drops every cloned iframe and <video> with it.
    box.querySelector('.lightbox-body').textContent = '';
    box.hidden = true;
    document.body.classList.remove('lightbox-open');
    if (lightboxReturnFocus && lightboxReturnFocus.isConnected) lightboxReturnFocus.focus();
    lightboxReturnFocus = null;
  };

  const openLightbox = (card) => {
    const box = document.getElementById('mediaLightbox');
    const source = card.querySelector('template.card-videos');
    if (!box || !source || !source.content.children.length) return false;

    releaseActive();
    const body = box.querySelector('.lightbox-body');
    body.textContent = '';
    body.appendChild(source.content.cloneNode(true));
    box.querySelector('.lightbox-title').textContent = card.dataset.title || '';
    box.hidden = false;
    document.body.classList.add('lightbox-open');
    lightboxReturnFocus = card.querySelector('.project-card-link') || card;
    initMediaPreview(body);
    box.querySelector('.lightbox-close').focus();
    return true;
  };

  const FOCUSABLE = 'button, [href], input, select, textarea, video[controls], [tabindex]:not([tabindex="-1"])';

  const trapFocus = (box, e) => {
    const items = Array.prototype.filter.call(
      box.querySelectorAll(FOCUSABLE),
      (el) => el.offsetParent !== null || el === document.activeElement
    );
    if (!items.length) return;
    const firstItem = items[0];
    const lastItem = items[items.length - 1];
    if (e.shiftKey && document.activeElement === firstItem) {
      e.preventDefault();
      lastItem.focus();
    } else if (!e.shiftKey && document.activeElement === lastItem) {
      e.preventDefault();
      firstItem.focus();
    }
  };

  const initLightbox = (root) => {
    const box = first(root, '#mediaLightbox') || document.getElementById('mediaLightbox');
    if (box && claim(box)) {
      box.addEventListener('click', (e) => {
        if (e.target.closest('[data-lightbox-close]')) closeLightbox();
      });
      box.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          e.preventDefault();
          closeLightbox();
        } else if (e.key === 'Tab') {
          trapFocus(box, e);
        }
      });
    }

    collect(root, '.project-card-link').forEach((link) => {
      if (!claim(link)) return;
      link.addEventListener('click', (e) => {
        const card = link.closest('.project-card');
        // The link stays the JS-free route to the detail page; only swallow the click
        // when there is actually a collection to expand.
        if (card && openLightbox(card)) e.preventDefault();
      });
    });
  };

  // Lightweight 3D tilt — pure CSS transforms driven by mouse position, no library.
  const initTilt = (root, selector, intensity) => {
    collect(root, selector).forEach((el) => {
      if (!claim(el)) return;
      let frame = null;
      el.addEventListener('mousemove', (e) => {
        const rect = el.getBoundingClientRect();
        const px = (e.clientX - rect.left) / rect.width - 0.5;
        const py = (e.clientY - rect.top) / rect.height - 0.5;
        if (frame) cancelAnimationFrame(frame);
        frame = requestAnimationFrame(() => {
          el.style.transform = `perspective(700px) rotateX(${(-py * intensity).toFixed(2)}deg) `
            + `rotateY(${(px * intensity).toFixed(2)}deg) translateY(-4px)`;
        });
      });
      el.addEventListener('mouseleave', () => {
        if (frame) cancelAnimationFrame(frame);
        el.style.transform = '';
      });
    });
  };

  window.portfolioInit = function (root) {
    root = root || document;

    // Sticky nav shadow/blur once the page has scrolled a little.
    const nav = first(root, '#siteNav');
    if (nav && claim(nav)) {
      const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 12);
      onScroll();
      window.addEventListener('scroll', onScroll, { passive: true });
    }

    // Mobile nav toggle.
    const navToggle = first(root, '#navToggle');
    const navLinks = first(root, '#navLinks');
    if (navToggle && navLinks && claim(navToggle)) {
      navToggle.addEventListener('click', () => {
        const isOpen = navLinks.classList.toggle('open');
        navToggle.classList.toggle('open', isOpen);
        navToggle.setAttribute('aria-expanded', String(isOpen));
      });
      navLinks.querySelectorAll('a').forEach((link) => {
        link.addEventListener('click', () => {
          navLinks.classList.remove('open');
          navToggle.classList.remove('open');
          navToggle.setAttribute('aria-expanded', 'false');
        });
      });
    }

    // Video previews, and the collection that expands in place when a card is clicked.
    initMediaPreview(root);
    initLightbox(root);

    // Window/document listeners are owned by `document`, which only ever appears once.
    if (claim(document)) {
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) releaseActive();
      });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeLightbox();
      });
    }

    // Fade/slide elements into view as the user scrolls.
    const revealEls = collect(root, '.reveal');
    if ('IntersectionObserver' in window) {
      if (!revealObserver) {
        revealObserver = new IntersectionObserver((entries) => {
          entries.forEach((entry) => {
            // A region swapped out by the editor reports once on the way out.
            if (!entry.target.isConnected) {
              revealObserver.unobserve(entry.target);
            } else if (entry.isIntersecting) {
              entry.target.classList.add('in-view');
              revealObserver.unobserve(entry.target);
            }
          });
        }, { threshold: 0.15 });
      }
      revealEls.forEach((el) => revealObserver.observe(el));
    } else {
      revealEls.forEach((el) => el.classList.add('in-view'));
    }

    if (canHover()) {
      // A tilting card makes the play target wobble under the cursor, so cards that
      // carry a preview frame opt out entirely.
      collect(root, '.project-card').forEach((card) => {
        if (!card.querySelector('.media-frame')) initTilt(card, '.project-card', 8);
      });
      initTilt(root, '.skill-card', 6);
      initTilt(root, '.tool-badge', 14);
      initTilt(root, '.form-card', 3);
    }

    // Subtle parallax on the hero glow as the cursor moves.
    const hero = first(root, '.hero');
    if (hero && canHover() && claim(hero)) {
      hero.addEventListener('mousemove', (e) => {
        const rect = hero.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        hero.style.setProperty('--mx', `${(x * 40).toFixed(1)}px`);
        hero.style.setProperty('--my', `${(y * 40).toFixed(1)}px`);
      });
    }

    // Auto-dismiss flash messages.
    collect(root, '.toast').forEach((toast, i) => {
      if (!claim(toast)) return;
      setTimeout(() => {
        toast.classList.add('toast-hide');
        setTimeout(() => toast.remove(), 400);
      }, 4000 + i * 300);
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.portfolioInit(document));
  } else {
    window.portfolioInit(document);
  }
})();
