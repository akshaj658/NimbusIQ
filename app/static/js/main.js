/**
 * StadiumIQ - FIFA World Cup 2026 Operations Intelligence
 * UI Controller: theme, tabs, sliders, form, admin, live-status polling
 */
(function () {
  'use strict';

  // -- Theme ------------------------------------------------------------------

  const THEME_KEY = 'stadiumiq-theme';

  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    const sun  = document.getElementById('icon-sun');
    const moon = document.getElementById('icon-moon');
    if (sun)  sun.style.display  = t === 'dark' ? 'none' : '';
    if (moon) moon.style.display = t === 'dark' ? '' : 'none';
  }

  function initTheme() {
    const saved       = localStorage.getItem(THEME_KEY);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(saved || (prefersDark ? 'dark' : 'light'));

    document.getElementById('theme-toggle')?.addEventListener('click', function () {
      const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      localStorage.setItem(THEME_KEY, next);
    });
  }

  // -- Tabbed form ------------------------------------------------------------

  let currentTab = 0;
  const tabIds = ['tab-service', 'tab-infra', 'tab-timeline', 'tab-pricing'];

  function showTab(index) {
    const btns   = document.querySelectorAll('.tab-btn');
    const panels = document.querySelectorAll('.tab-panel');
    if (!btns.length) return;

    index = Math.max(0, Math.min(index, tabIds.length - 1));
    currentTab = index;

    btns.forEach((b, i) => {
      b.classList.toggle('active', i === index);
      b.setAttribute('aria-selected', i === index ? 'true' : 'false');
    });
    panels.forEach((p, i) => p.classList.toggle('active', i === index));

    const prev = document.getElementById('tab-prev');
    const next = document.getElementById('tab-next');
    if (prev) prev.disabled = index === 0;
    if (next) next.disabled = index === tabIds.length - 1;
  }

  function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(function (btn, i) {
      btn.addEventListener('click', function () { showTab(i); });
    });
    document.getElementById('tab-prev')?.addEventListener('click', function () { showTab(currentTab - 1); });
    document.getElementById('tab-next')?.addEventListener('click', function () { showTab(currentTab + 1); });
    showTab(0);
  }

  // -- Sliders ----------------------------------------------------------------

  function initSlider(sliderId, valId) {
    const slider = document.getElementById(sliderId);
    const val    = document.getElementById(valId);
    if (!slider || !val) return;
    const sync = () => { val.textContent = Math.round(slider.value) + '%'; };
    sync();
    ['input', 'change'].forEach(e => slider.addEventListener(e, sync));
  }

  // -- Form submit state ------------------------------------------------------

  function initForm() {
    const form = document.getElementById('prediction-form');
    if (!form) return;
    form.addEventListener('submit', function () {
      const btn     = document.getElementById('submit-btn');
      const label   = btn?.querySelector('.btn-label');
      const spinner = btn?.querySelector('.spinner');
      if (btn)     btn.setAttribute('disabled', 'true');
      if (label)   label.textContent = 'Analysing...';
      if (spinner) spinner.classList.remove('d-none');
    });

    document.getElementById('clear-form-btn')?.addEventListener('click', resetEstimateForm);
  }

  function resetEstimateForm() {
    const form   = document.getElementById('prediction-form');
    const cpuVal = document.getElementById('cpu-val');
    const memVal = document.getElementById('mem-val');
    if (form)   form.reset();
    if (cpuVal) cpuVal.textContent = '50%';
    if (memVal) memVal.textContent = '50%';
    showTab(0);
  }

  // -- Delete handlers --------------------------------------------------------

  function initDeleteHandlers() {
    document.addEventListener('click', async function (e) {
      if (!e.target?.classList.contains('del-btn')) return;
      const id = e.target.getAttribute('data-id');
      if (!id || !confirm('Remove this assessment record?')) return;

      e.target.setAttribute('disabled', 'true');
      try {
        const res = await fetch('/api/delete/' + id, {
          method: 'DELETE',
          credentials: 'include',
        });
        if (res.ok) {
          e.target.closest('tr')?.remove();
        } else if (res.status === 401) {
          alert('Authentication required. Please log in to the admin dashboard first.');
        } else {
          const d = await res.json().catch(() => ({}));
          alert('Could not remove: ' + (d.message || res.statusText));
        }
      } catch (err) {
        alert('Request failed: ' + err);
      } finally {
        e.target.removeAttribute('disabled');
      }
    });
  }

  // -- Admin search -----------------------------------------------------------

  function formatINR(v) {
    try {
      return '\u20B9 ' + Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    } catch (_) { return v; }
  }

  function renderTable(rows) {
    const tbody = document.getElementById('history-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!rows?.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="color:var(--text-3);font-size:0.8rem;padding:16px 12px">No assessments match your search.</td></tr>';
      return;
    }
    rows.forEach(function (item) {
      const tr = document.createElement('tr');
      tr.innerHTML =
        '<td>' + item.id + '</td>' +
        '<td>' + item.timestamp + '</td>' +
        '<td>' + (item.service_name || '') + '</td>' +
        '<td>' + (item.region || '') + '</td>' +
        '<td>' + formatINR(item.predicted_cost) + '</td>' +
        '<td><button class="del-btn" data-id="' + item.id + '" type="button" aria-label="Remove assessment ' + item.id + '">Remove</button></td>';
      tbody.appendChild(tr);
    });
  }

  async function doSearch(q) {
    q = q !== undefined ? q : (document.getElementById('search-input')?.value || '');
    try {
      const res = await fetch('/history?q=' + encodeURIComponent(q), {
        credentials: 'include',
      });
      if (res.ok) renderTable((await res.json()).predictions || []);
    } catch (_) {}
  }

  function initAdmin() {
    document.getElementById('search-btn')?.addEventListener('click', () => doSearch());
    document.getElementById('search-input')?.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') doSearch();
    });
    document.getElementById('export-btn')?.addEventListener('click', function () {
      const q = document.getElementById('search-input')?.value || '';
      window.location.href = '/download?q=' + encodeURIComponent(q);
    });
  }

  // -- Live stadium status polling --------------------------------------------

  function renderStatusBar(data) {
    const venuesEl = document.getElementById('status-venues');
    const globalEl = document.getElementById('status-global');
    if (!venuesEl || !data?.venues) return;

    venuesEl.innerHTML = data.venues.map(function (v) {
      return '<span class="status-chip ' + v.alert_class + '">' +
        v.venue + ' \u2014 ' + v.capacity_pct + '% Capacity' +
        '</span>';
    }).join('');

    if (globalEl) globalEl.textContent = data.global_alert || 'ALL SYSTEMS NOMINAL';
  }

  async function fetchStadiumStatus() {
    try {
      const res = await fetch('/api/stadium-status');
      if (res.ok) renderStatusBar(await res.json());
    } catch (_) {}
  }

  function initStatusBar() {
    if (!document.getElementById('status-bar')) return;
    fetchStadiumStatus();
    setInterval(fetchStadiumStatus, 30_000);
  }

  // -- Boot -------------------------------------------------------------------

  function boot() {
    initTheme();
    initTabs();
    initSlider('cpu-slider', 'cpu-val');
    initSlider('mem-slider', 'mem-val');
    initForm();
    initDeleteHandlers();
    initAdmin();
    initStatusBar();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

}());
