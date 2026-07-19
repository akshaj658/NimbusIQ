/**
 * StadiumIQ - Match-Day Readiness Controller
 * Handles domain status selection, notes, AI report generation.
 */
(function () {
  'use strict';

  const domainsEl = document.getElementById('stadiumiq-domains-data');
  let domains = [];
  if (domainsEl) {
    try {
      domains = JSON.parse(domainsEl.textContent);
    } catch (_) {}
  }

  // -- Mark all green --------------------------------------------------------

  document.getElementById('all-green-btn')?.addEventListener('click', function () {
    document.querySelectorAll('.readiness-status-select').forEach(function (sel) {
      sel.value = 'green';
    });
  });

  // -- Generate AI report ----------------------------------------------------

  document.getElementById('generate-report-btn')?.addEventListener('click', async function () {
    const btn = this;
    btn.setAttribute('disabled', 'true');
    btn.textContent = 'Generating...';

    // Collect domain statuses
    const domainStatuses = [];
    document.querySelectorAll('.readiness-domain-row').forEach(function (row) {
      const domainId = row.getAttribute('data-domain-id');
      const status   = row.querySelector('.readiness-status-select')?.value || 'amber';
      const notes    = row.querySelector('.readiness-notes')?.value || '';
      const domain   = domains.find(function (d) { return d.id === domainId; });
      if (domain) {
        domainStatuses.push({
          id: domainId,
          title: domain.title,
          status: status,
          notes: notes,
        });
      }
    });

    // Build situation description
    const venue      = document.getElementById('r-venue')?.value || 'Venue not specified';
    const attendance = document.getElementById('r-attendance')?.value || 'Unknown';
    const kickoff    = document.getElementById('r-kickoff')?.value || 'Unknown';
    const teams      = document.getElementById('r-teams')?.value || 'TBC';

    const greenDomains  = domainStatuses.filter(function (d) { return d.status === 'green'; });
    const amberDomains  = domainStatuses.filter(function (d) { return d.status === 'amber'; });
    const redDomains    = domainStatuses.filter(function (d) { return d.status === 'red'; });

    const situationLines = [
      'PRE-MATCH READINESS REPORT REQUEST',
      'Venue: ' + venue,
      'Match: ' + teams,
      'Kickoff: ' + kickoff,
      'Expected attendance: ' + attendance,
      '',
      'DOMAIN STATUS SUMMARY:',
      'GREEN (' + greenDomains.length + '): ' + greenDomains.map(function (d) { return d.title; }).join(', '),
      'AMBER (' + amberDomains.length + '): ' + amberDomains.map(function (d) { return d.title + (d.notes ? ' [' + d.notes + ']' : ''); }).join(', '),
      'RED (' + redDomains.length + '): ' + redDomains.map(function (d) { return d.title + (d.notes ? ' [' + d.notes + ']' : ''); }).join(', '),
    ].join('\n');

    try {
      const res = await fetch('/api/ai-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain_id: 'match_readiness',
          situation: situationLines,
          context: { venue, attendance: attendance + ' fans', kickoff_time: kickoff, match: teams },
        }),
      });

      const data = await res.json();
      renderReport(data, redDomains.length, amberDomains.length);

    } catch (err) {
      renderReport({
        response: 'Failed to generate report: ' + err.message,
        source: 'error',
      }, redDomains.length, amberDomains.length);
    } finally {
      btn.removeAttribute('disabled');
      btn.textContent = 'Generate AI Report';
    }
  });

  function renderReport(data, redCount, amberCount) {
    const reportCard  = document.getElementById('readiness-report');
    const verdictEl   = document.getElementById('readiness-verdict');
    const responseEl  = document.getElementById('readiness-response-text');
    const sourceBadge = document.getElementById('report-source-badge');

    if (!reportCard) return;
    reportCard.classList.remove('d-none');
    reportCard.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Verdict badge
    let verdictClass, verdictText;
    if (redCount > 0) {
      verdictClass = 'verdict-hold';
      verdictText  = '🔴 HOLD - ' + redCount + ' critical domain(s) not ready';
    } else if (amberCount > 0) {
      verdictClass = 'verdict-conditional';
      verdictText  = '🟡 CONDITIONAL GO - ' + amberCount + ' domain(s) need resolution';
    } else {
      verdictClass = 'verdict-go';
      verdictText  = '🟢 GO - All domains ready';
    }

    if (verdictEl) {
      verdictEl.className = 'readiness-verdict ' + verdictClass;
      verdictEl.textContent = verdictText;
    }

    if (sourceBadge) {
      sourceBadge.textContent = data.source === 'gemini' ? 'Gemini AI' : 'AI Analysis';
      sourceBadge.className = 'ai-source-badge ' + (data.source === 'gemini' ? 'gemini' : 'local');
    }

    if (responseEl) {
      const formatted = (data.response || '')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n\n+/g, '</p><p>')
        .replace(/\n/g, '<br>');
      responseEl.innerHTML = '<p>' + formatted + '</p>';
    }
  }

  // Close report
  document.getElementById('close-report-btn')?.addEventListener('click', function () {
    document.getElementById('readiness-report')?.classList.add('d-none');
  });

}());
