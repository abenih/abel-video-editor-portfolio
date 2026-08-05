document.addEventListener('DOMContentLoaded', () => {
  // Sticky nav shadow/blur once the page has scrolled a little.
  const nav = document.getElementById('siteNav');
  const onScroll = () => {
    if (!nav) return;
    nav.classList.toggle('scrolled', window.scrollY > 12);
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  // Mobile nav toggle.
  const navToggle = document.getElementById('navToggle');
  const navLinks = document.getElementById('navLinks');
  if (navToggle && navLinks) {
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

  // Portfolio category filter tabs.
  const tabs = document.querySelectorAll('.filter-tab');
  const cards = document.querySelectorAll('.project-card');
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      tabs.forEach((t) => t.classList.remove('active'));
      tab.classList.add('active');
      const filter = tab.dataset.filter;
      cards.forEach((card) => {
        const show = filter === 'all' || card.dataset.category === filter;
        card.classList.toggle('is-hidden', !show);
      });
    });
  });

  // Fade/slide elements into view as the user scrolls.
  const revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && revealEls.length) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });
    revealEls.forEach((el) => observer.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add('in-view'));
  }

  // Lightweight 3D tilt — pure CSS transforms driven by mouse position, no library.
  const initTilt = (selector, intensity) => {
    document.querySelectorAll(selector).forEach((el) => {
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
  if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
    initTilt('.project-card', 8);
    initTilt('.skill-card', 6);
    initTilt('.tool-badge', 14);
    initTilt('.form-card', 3);
  }

  // Subtle parallax on the hero glow as the cursor moves.
  const hero = document.querySelector('.hero');
  if (hero && window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
    hero.addEventListener('mousemove', (e) => {
      const rect = hero.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      hero.style.setProperty('--mx', `${(x * 40).toFixed(1)}px`);
      hero.style.setProperty('--my', `${(y * 40).toFixed(1)}px`);
    });
  }

  // Auto-dismiss flash messages.
  document.querySelectorAll('.toast').forEach((toast, i) => {
    setTimeout(() => {
      toast.classList.add('toast-hide');
      setTimeout(() => toast.remove(), 400);
    }, 4000 + i * 300);
  });
});
