/**
 * StadiumIQ — AI Incident Console Controller
 * Handles domain selection, situation submission, Gemini AI response rendering,
 * session history management, and example auto-fill.
 */
(function () {
  'use strict';

  const domains = window.STADIUMIQ_DOMAINS || [];
  const domainMap = {};
  domains.forEach(function (d) { domainMap[d.id] = d; });

  let sessionHistory = [];

  // ── Element refs ──────────────────────────────────────────────────────────

  const domainSelect    = document.getElementById('domain-select');
  const situationInput  = document.getElementById('situation-input');
  const exampleText     = document.getElementById('example-text');
  const useExampleBtn   = document.getElementById('use-example-btn');
  const queryBtn        = document.getElementById('ai-query-btn');
  const clearBtn        = document.getElementById('clear-console-btn');
  const responsePanel   = document.getElementById('response-panel');
  const emptyState      = document.getElementById('console-empty');
  const loadingState    = document.getElementById('console-loading');
  const contentState    = document.getElementById('console-content');
  const responseText    = document.getElementById('response-text');
  const sourceBadge     = document.getElementById('response-source-badge');
  const domainBadge     = document.getElementById('response-domain-badge');
  const copyBtn         = document.getElementById('copy-response-btn');
  const newQueryBtn     = document.getElementById('new-query-btn');
  const historyList     = document.getElementById('history-list');
  const clearHistoryBtn = document.getElementById('clear-history-btn');
  const domainPills     = document.querySelectorAll('.domain-pill');

  // Context refs
  const ctxVenue    = document.getElementById('ctx-venue');
  const ctxCrowd    = document.getElementById('ctx-crowd');
  const ctxKickoff  = document.getElementById('ctx-kickoff');
  const ctxSeverity = document.getElementById('ctx-severity');

  // ── Domain selection ──────────────────────────────────────────────────────

  function updateExample(domainId) {
    const domain = domainMap[domainId];
    if (!domain || !exampleText) return;
    exampleText.textContent = domain.example || '';
    situationInput.placeholder = domain.placeholder || 'Describe the situation...';
  }

  function selectDomain(domainId) {
    if (domainSelect) domainSelect.value = domainId;
    domainPills.forEach(function (pill) {
      const isActive = pill.getAttribute('data-domain') === domainId;
      pill.classList.toggle('active', isActive);
      pill.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
    updateExample(domainId);
  }

  // Initialise from URL ?domain= param or first domain
  function initDomainFromURL() {
    const params = new URLSearchParams(window.location.search);
    const domainParam = params.get('domain');
    const firstDomain = domains[0]?.id || '';
    const initial = domainMap[domainParam] ? domainParam : firstDomain;
    selectDomain(initial);
  }

  if (domainSelect) {
    domainSelect.addEventListener('change', function () {
      selectDomain(this.value);
    });
  }

  domainPills.forEach(function (pill) {
    pill.addEventListener('click', function () {
      selectDomain(this.getAttribute('data-domain'));
    });
  });

  if (useExampleBtn) {
    useExampleBtn.addEventListener('click', function () {
      const domain = domainMap[domainSelect?.value];
      if (domain && situationInput) {
        situationInput.value = domain.example || '';
        situationInput.focus();
      }
    });
  }

  // ── State rendering ───────────────────────────────────────────────────────

  function show(el) { el?.classList.remove('d-none'); }
  function hide(el) { el?.classList.add('d-none'); }

  function showLoading() {
    hide(emptyState);
    hide(contentState);
    show(loadingState);
  }

  function showResponse(data) {
    hide(loadingState);
    hide(emptyState);
    show(contentState);

    const domain = domainMap[data.domain_id] || {};
    if (domainBadge) domainBadge.textContent = data.domain_title || domain.title || 'AI Response';

    if (sourceBadge) {
      sourceBadge.textContent = data.source === 'gemini' ? 'Gemini AI' : 'AI Analysis';
      sourceBadge.className = 'ai-source-badge ' + (data.source === 'gemini' ? 'gemini' : 'local');
    }

    if (responseText) {
      // Format the response — preserve paragraph breaks, bold headers
      const formatted = (data.response || '')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n\n+/g, '</p><p>')
        .replace(/\n/g, '<br>');
      responseText.innerHTML = '<p>' + formatted + '</p>';
    }
  }

  function resetToEmpty() {
    hide(loadingState);
    hide(contentState);
    show(emptyState);
    if (sourceBadge) {
      sourceBadge.textContent = 'Awaiting input';
      sourceBadge.className = 'ai-source-badge local';
    }
  }

  // ── Query submission ──────────────────────────────────────────────────────

  async function submitQuery() {
    const domainId   = domainSelect?.value;
    const situation  = situationInput?.value?.trim();

    if (!situation) {
      situationInput?.focus();
      situationInput?.classList.add('input-error');
      setTimeout(() => situationInput?.classList.remove('input-error'), 1500);
      return;
    }

    // Build context
    const context = {};
    if (ctxVenue?.value)    context['venue']          = ctxVenue.value;
    if (ctxCrowd?.value)    context['crowd_size']     = ctxCrowd.value + ' fans';
    if (ctxKickoff?.value)  context['match_time']     = ctxKickoff.value;
    if (ctxSeverity?.value) context['severity_level'] = ctxSeverity.value;

    // UI state
    if (queryBtn) {
      queryBtn.setAttribute('disabled', 'true');
      queryBtn.querySelector('.btn-label').textContent = 'Analysing...';
      queryBtn.querySelector('.spinner')?.classList.remove('d-none');
    }
    showLoading();

    try {
      const res = await fetch('/api/ai-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain_id: domainId, situation, context }),
      });

      const data = await res.json();
      data.domain_id = domainId;

      showResponse(data);
      addToHistory(domainId, situation, data);

    } catch (err) {
      showResponse({
        domain_title: domainMap[domainId]?.title || 'Error',
        response: 'Failed to reach the AI Director. Please check your connection and try again.\n\nError: ' + err.message,
        source: 'error',
      });
    } finally {
      if (queryBtn) {
        queryBtn.removeAttribute('disabled');
        queryBtn.querySelector('.btn-label').textContent = 'Get AI Guidance';
        queryBtn.querySelector('.spinner')?.classList.add('d-none');
      }
    }
  }

  if (queryBtn)   queryBtn.addEventListener('click', submitQuery);
  if (clearBtn)   clearBtn.addEventListener('click', function () {
    if (situationInput) situationInput.value = '';
    resetToEmpty();
  });
  if (newQueryBtn) newQueryBtn.addEventListener('click', function () {
    situationInput?.focus();
    resetToEmpty();
  });

  // Copy response
  if (copyBtn) {
    copyBtn.addEventListener('click', function () {
      const text = responseText?.innerText || '';
      navigator.clipboard.writeText(text).then(function () {
        copyBtn.textContent = 'Copied!';
        setTimeout(() => { copyBtn.textContent = 'Copy Response'; }, 2000);
      });
    });
  }

  // Keyboard shortcut: Ctrl+Enter to submit
  if (situationInput) {
    situationInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        submitQuery();
      }
    });
  }

  // ── Session history ───────────────────────────────────────────────────────

  function addToHistory(domainId, situation, result) {
    const entry = {
      id: Date.now(),
      domain_id: domainId,
      domain_title: result.domain_title,
      situation: situation.substring(0, 100) + (situation.length > 100 ? '...' : ''),
      response: result.response,
      source: result.source,
      ts: new Date().toLocaleTimeString(),
    };
    sessionHistory.unshift(entry);
    renderHistory();
  }

  function renderHistory() {
    if (!historyList) return;
    if (!sessionHistory.length) {
      historyList.innerHTML = '<p class="history-empty">No queries this session.</p>';
      return;
    }
    historyList.innerHTML = sessionHistory.map(function (entry) {
      return '<div class="history-entry" data-id="' + entry.id + '">' +
        '<div class="history-entry-header">' +
          '<span class="history-domain">' + (entry.domain_title || '') + '</span>' +
          '<span class="history-ts">' + entry.ts + '</span>' +
        '</div>' +
        '<p class="history-situation">' + entry.situation + '</p>' +
        '<button class="btn-link history-recall" data-id="' + entry.id + '">View response</button>' +
      '</div>';
    }).join('');

    historyList.querySelectorAll('.history-recall').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const id = parseInt(this.getAttribute('data-id'));
        const entry = sessionHistory.find(function (e) { return e.id === id; });
        if (entry) {
          showResponse({ domain_title: entry.domain_title, response: entry.response, source: entry.source });
          selectDomain(entry.domain_id);
          if (situationInput) situationInput.value = entry.situation;
        }
      });
    });
  }

  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', function () {
      sessionHistory = [];
      renderHistory();
    });
  }

  // ── Boot ─────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', function () {
    initDomainFromURL();
    renderHistory();
  });

}());
