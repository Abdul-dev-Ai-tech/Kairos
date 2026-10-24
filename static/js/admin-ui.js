/* Kairos Store Manager: small, dependency-free enhancements for Django admin. */
(() => {
  'use strict';
  const sidebar = document.querySelector('.km-sidebar');
  const toggle = document.querySelector('.km-menu-button');
  const backdrop = document.querySelector('.km-sidebar-backdrop');
  const closeButton = document.querySelector('.km-sidebar-close');
  let previousFocus;
  const isMobile = () => window.matchMedia('(max-width: 1100px)').matches;

  function setNavigation(open) {
    if (!sidebar || !toggle || !backdrop) return;
    if (open) previousFocus = document.activeElement;
    document.body.classList.toggle('km-navigation-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    backdrop.hidden = !open;
    sidebar.inert = isMobile() && !open;
    document.querySelectorAll('#header, #main, #footer').forEach(element => {
      element.inert = isMobile() && open;
    });
    if (isMobile()) {
      sidebar.setAttribute('role', open ? 'dialog' : 'complementary');
      if (open) sidebar.setAttribute('aria-modal', 'true');
      else sidebar.removeAttribute('aria-modal');
    }
    if (open) closeButton?.focus();
    else if (previousFocus?.isConnected) previousFocus.focus();
  }
  toggle?.addEventListener('click', () => setNavigation(toggle.getAttribute('aria-expanded') !== 'true'));
  closeButton?.addEventListener('click', () => setNavigation(false));
  backdrop?.addEventListener('click', () => setNavigation(false));
  sidebar?.addEventListener('click', event => {
    if (isMobile() && event.target.closest('a')) setNavigation(false);
  });
  document.addEventListener('keydown', event => {
    if (!document.body.classList.contains('km-navigation-open')) return;
    if (event.key === 'Escape') { event.preventDefault(); setNavigation(false); }
    if (event.key === 'Tab' && sidebar) {
      const items = [...sidebar.querySelectorAll('a,button,input')].filter(node => node.offsetParent !== null);
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
  });
  window.matchMedia('(max-width: 1100px)').addEventListener('change', () => {
    setNavigation(false);
    sidebar?.removeAttribute('role');
    sidebar?.removeAttribute('aria-modal');
  });
  // Preserve the sidebar position across server-rendered admin navigation.
  const nav = document.querySelector('.km-navigation');
  if (sidebar) sidebar.inert = isMobile();
  if (nav) {
    try { nav.scrollTop = Number(sessionStorage.getItem('kairos-admin-navigation-scroll') || 0); } catch {}
    nav.addEventListener('scroll', () => {
      try { sessionStorage.setItem('kairos-admin-navigation-scroll', String(nav.scrollTop)); } catch {}
    }, {passive: true});
  }
  // Compact native filter disclosures on narrow screens.
  if (window.matchMedia('(max-width: 700px)').matches) {
    document.querySelectorAll('#changelist-filter details').forEach(details => { details.open = false; });
  }
  // Show the selected local photograph before it is uploaded by the Django form.
  const previews = new WeakMap();
  document.addEventListener('change', event => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || input.type !== 'file' || !input.name.includes('image')) return;
    const old = previews.get(input);
    if (old) { URL.revokeObjectURL(old.url); old.node.remove(); previews.delete(input); }
    const file = input.files?.[0];
    if (!file || !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return;
    const image = document.createElement('img');
    const url = URL.createObjectURL(file);
    image.className = 'km-file-preview';
    image.alt = 'Selected photograph: ' + file.name;
    image.src = url;
    image.width = 100;
    image.height = 100;
    input.insertAdjacentElement('afterend', image);
    previews.set(input, {node: image, url});
  });
})();
