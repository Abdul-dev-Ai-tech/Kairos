/* KAIROS progressive enhancements. All prices, permissions and stock are verified on the server. */
(() => {
  'use strict';
  document.documentElement.classList.add('js-enabled');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const money = value => 'PKR ' + Number(value).toLocaleString('en-PK', {minimumFractionDigits: Number(value) % 1 ? 2 : 0, maximumFractionDigits: 2});
  let toastTimer;
  function toast(message) {
    const node = $('.toast');
    if (!node) return;
    node.textContent = message; node.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => {node.hidden = true;}, 4800);
  }
  function busy(button, value) {
    if (!button) return;
    button.classList.toggle('is-busy', value);
    button.setAttribute('aria-busy', String(value));
    button.disabled = value;
  }
  async function postForm(form, data = new FormData(form), signal) {
    const response = await fetch(form.action, {method: 'POST', body: data, credentials: 'same-origin', signal,
      headers: {'Accept': 'application/json', 'X-CSRFToken': data.get('csrfmiddlewaretoken') || ''}});
    const content = await response.json().catch(() => ({}));
    if (!response.ok) throw Error(content.error || 'This action could not be completed. Refresh and try again.');
    return content;
  }
  $$('[data-dismiss]').forEach(button => button.addEventListener('click', () => button.parentElement.remove()));
  const menuButton = $('.mobile-menu-toggle');
  menuButton?.addEventListener('click', () => {
    const open = menuButton.getAttribute('aria-expanded') !== 'true';
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    $('#main-nav').classList.toggle('is-open', open);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menuButton) {
      menuButton.setAttribute('aria-expanded', 'false'); menuButton.setAttribute('aria-label', 'Open navigation'); $('#main-nav')?.classList.remove('is-open');
    }
  });
  const welcome = $('#welcome');
  if (welcome && !reduced) {
    let seen = false;
    try { seen = sessionStorage.getItem('kairos-welcome') === '1'; } catch (_) { seen = true; }
    if (!seen) {
      try { sessionStorage.setItem('kairos-welcome', '1'); } catch (_) {}
      welcome.hidden = false;
      function closeIntro() { welcome.classList.add('closing'); setTimeout(() => {welcome.hidden = true;}, 400); }
      $('[data-skip-intro]')?.addEventListener('click', closeIntro);
      setTimeout(closeIntro, 1450);
    }
  }
  if (!reduced && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.animate([{opacity: 0, transform: 'translateY(19px)'}, {opacity: 1, transform: 'translateY(0)'}],
          {duration: 650, easing: 'cubic-bezier(.22,.61,.36,1)'});
        observer.unobserve(entry.target);
      }
    }), {threshold: .08});
    $$('.reveal').forEach(node => observer.observe(node));
    $$('.hero-reveal').forEach((node, i) => node.animate([{opacity: 0, transform: 'translateY(15px)'}, {opacity: 1, transform: 'translateY(0)'}],
      {duration: 800, delay: 150 + i * 100, easing: 'ease-out', fill: 'backwards'}));
    if (matchMedia('(min-width: 1000px)').matches && (navigator.hardwareConcurrency || 4) >= 4) {
      const hero = $('.hero-image');
      if (hero) {
        let ticking = false;
        addEventListener('scroll', () => {
          if (!ticking && scrollY < 1000) {
            ticking = true; requestAnimationFrame(() => {
              hero.style.transform = `translateY(${Math.min(35, scrollY * .06)}px) scale(1.07)`; ticking = false;
            });
          }
        }, {passive: true});
      }
    }
  }
  $$('dialog').forEach(dialog => {
    $$('[data-close-dialog]', dialog).forEach(button => button.addEventListener('click', () => dialog.close()));
    dialog.addEventListener('click', event => { if (event.target === dialog) {
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    }});
  });
  $('[data-open-search]')?.addEventListener('click', () => {$('#search-dialog').showModal(); $('#global-search').focus();});
  function updateCount(count) { $$('[data-cart-count]').forEach(node => {node.textContent = count;}); }
  const drawer = $('#cart-dialog');
  let drawerGeneration = 0;
  async function loadDrawer() {
    const generation = ++drawerGeneration;
    const body = $('[data-cart-body]');
    if (!body) return;
    body.setAttribute('aria-busy', 'true');
    body.innerHTML = '<div class="skeleton" role="status" aria-label="Loading your shopping bag"><div></div><div></div></div>';
    try {
      const response = await fetch('/bag/summary/', {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
      if (!response.ok) throw Error('Unable to load your bag.');
      const content = await response.json();
      if (generation === drawerGeneration) {body.innerHTML = content.html; updateCount(content.count);}
    } catch (_) {
      if (generation === drawerGeneration) body.innerHTML = '<div class="empty-state"><h2>A short pause.</h2><p>Your bag could not load. Please try again.</p><button type="button" class="button" data-retry-cart>Try again</button><p><a href="/bag/">View your bag →</a></p></div>';
    } finally { if (generation === drawerGeneration) body.removeAttribute('aria-busy'); }
  }
  function openDrawer() { if (!drawer.open) drawer.showModal(); loadDrawer(); }
  $('[data-open-cart]')?.addEventListener('click', event => { if (!event.ctrlKey && !event.metaKey && !event.shiftKey) {event.preventDefault(); openDrawer();} });
  document.addEventListener('click', event => {
    if (event.target.closest('[data-retry-cart]')) loadDrawer();
    const quantity = event.target.closest('[data-quantity]');
    if (quantity) {
      const input = $('input[type=number]', quantity.parentElement);
      input.value = Math.max(Number(input.min || 1), Math.min(Number(input.max || 99), Number(input.value || 1) + Number(quantity.dataset.quantity)));
      input.dispatchEvent(new Event('change', {bubbles: true}));
    }
    const thumbnail = event.target.closest('[data-image]');
    if (thumbnail) selectImage(thumbnail.dataset.image, thumbnail.dataset.full, thumbnail.dataset.alt, thumbnail);
  });
  function selectImage(url, full, alt, selected) {
    const image = $('#main-product-image');
    if (!image) return;
    image.src = url; image.dataset.full = full || url; image.alt = alt || '';
    if (!reduced) image.animate([{opacity: .3}, {opacity: 1}], {duration: 280});
    $$('[data-thumbnails] button').forEach(button => button.setAttribute('aria-pressed', String(button === selected)));
  }
  const variantSelector = $('[data-variant-selector]');
  if (variantSelector) {
    let variants = [];
    try {variants = JSON.parse($('#variant-data').textContent);} catch (_) {}
    variantSelector.addEventListener('change', () => {
      const variant = variants.find(v => String(v.id) === variantSelector.value);
      if (!variant) return;
      $('[data-variant-input]').value = variant.id;
      $('[data-variant-price]').textContent = money(variant.price);
      $('[data-variant-regular]').textContent = money(variant.regular_price);
      $('[data-variant-regular]').hidden = Number(variant.price) >= Number(variant.regular_price);
      $('[data-variant-sku]').textContent = variant.sku;
      $('[data-stock-status]').textContent = variant.stock ? `${variant.stock} available` : 'Currently out of stock';
      const input = $('#quantity'); input.max = Math.max(1, variant.stock); input.value = 1;
      $$('[data-stock-button]').forEach(button => {button.disabled = !variant.stock;});
      const thumbnails = $('[data-thumbnails]'); thumbnails.replaceChildren();
      variant.images.forEach((image, i) => {
        const button = document.createElement('button'); button.type = 'button';
        button.dataset.image = image.medium; button.dataset.full = image.url; button.dataset.alt = image.alt;
        button.setAttribute('aria-label', 'View image ' + (i + 1)); button.setAttribute('aria-pressed', String(i === 0));
        const thumb = document.createElement('img'); thumb.src = image.thumbnail; thumb.alt = image.alt; thumb.width = 100; thumb.height = 100;
        button.append(thumb); thumbnails.append(button);
      });
      if (variant.images.length) selectImage(variant.images[0].medium, variant.images[0].url, variant.images[0].alt, $('button', thumbnails));
      else selectImage('/static/images/product-placeholder.svg', '', 'Photograph to be added', null);
      const url = new URL(location.href); url.searchParams.set('variant', variant.id); history.replaceState(null, '', url);
    });
  }
  $('[data-zoom]')?.addEventListener('click', () => {
    const source = $('#main-product-image'); const image = $('#zoom-image');
    image.src = source.dataset.full || source.src; image.alt = source.alt; image.style.width = '100%';
    $('[data-zoom-range]').value = 100; $('#zoom-dialog').showModal();
  });
  $('[data-zoom-range]')?.addEventListener('input', event => {$('#zoom-image').style.width = event.target.value + '%';});
  document.addEventListener('submit', async event => {
    const form = event.target;
    if (form.matches('[data-wishlist]')) {
      event.preventDefault(); const button = $('button[type=submit]', form); busy(button, true);
      try {
        const result = await postForm(form);
        $$('[data-wishlist]').filter(other => other.action === form.action).forEach(other => {
          const otherButton = $('button[type=submit]', other);
          otherButton.classList.toggle('is-saved', result.saved); otherButton.setAttribute('aria-pressed', String(result.saved));
        });
        toast(result.message);
      } catch (error) {toast(error.message);} finally {busy(button, false);}
      return;
    }
    if (form.matches('[data-add-cart]') && event.submitter?.name !== 'buy_now') {
      event.preventDefault(); const button = event.submitter; busy(button, true);
      const errorNode = $('[data-cart-error]', form); if (errorNode) errorNode.textContent = '';
      try {const result = await postForm(form); updateCount(result.count); openDrawer();}
      catch (error) {if (errorNode) errorNode.textContent = error.message; else toast(error.message);}
      finally {busy(button, false);}
      return;
    }
    if (form.matches('[data-remove-cart]')) {
      event.preventDefault(); const button = $('button', form); busy(button, true);
      try {const result = await postForm(form); updateCount(result.count); await loadDrawer();}
      catch (error) {toast(error.message); busy(button, false);}
      return;
    }
    // Preserve a named submit button (Buy now / coupon removal) while disabling
    // the actual control. Native forms retain progressive enhancement semantics.
    if (form.dataset.submitting) {event.preventDefault(); return;}
    const button = event.submitter;
    if (button?.name) {const hidden = document.createElement('input'); hidden.type = 'hidden'; hidden.name = button.name; hidden.value = button.value; hidden.dataset.submitClone = '1'; form.append(hidden);}
    form.dataset.submitting = '1'; busy(button, true);
  });
  addEventListener('pageshow', () => {
    $$('form[data-submitting]').forEach(form => {delete form.dataset.submitting; $$('[data-submit-clone]', form).forEach(node => node.remove());});
    $$('.is-busy').forEach(button => busy(button, false));
  });
  const checkout = $('[data-checkout]');
  if (checkout) {
    let quoteController, quoteTimer;
    const shipping = $('[name=shipping_zone]', checkout), city = $('[name=city]', checkout);
    const feedback = $('[data-shipping-feedback]');
    async function updateQuote() {
      quoteController?.abort();
      if (!shipping.value || !city.value.trim()) return;
      quoteController = new AbortController();
      const data = new FormData(checkout); feedback.textContent = 'Calculating delivery…'; feedback.classList.remove('is-error');
      try {
        const response = await fetch('/checkout/quote/', {method: 'POST', body: data, credentials: 'same-origin',
          signal: quoteController.signal, headers: {'Accept': 'application/json', 'X-CSRFToken': data.get('csrfmiddlewaretoken')}});
        const result = await response.json(); if (!response.ok) throw Error(result.error || 'Unable to calculate delivery.');
        $('[data-shipping-total]').textContent = money(result.shipping); $('[data-order-total]').textContent = money(result.total);
        feedback.textContent = result.estimate || 'Delivery charge confirmed for your selection.';
      } catch (error) {if (error.name !== 'AbortError') {feedback.textContent = error.message; feedback.classList.add('is-error'); $('[data-shipping-total]').textContent = 'Check delivery zone'; $('[data-order-total]').textContent = 'Confirm delivery';}}
    }
    shipping.addEventListener('change', updateQuote);
    city.addEventListener('input', () => {clearTimeout(quoteTimer); quoteTimer = setTimeout(updateQuote, 350);});
    function paymentInfo() {const selected = $('[name=payment_method]:checked', checkout)?.value; $$('[data-method-info]').forEach(node => {node.hidden = node.dataset.methodInfo !== selected;});}
    $$('[name=payment_method]', checkout).forEach(input => input.addEventListener('change', paymentInfo));
    paymentInfo(); updateQuote();
  }
  const filters = $('.filters details');
  if (filters && matchMedia('(max-width: 760px)').matches) filters.open = false;
})();
