/**
 * StadiumIQ — FIFA World Cup 2026 Operations Admin Dashboard Charts
 */
(function () {
  'use strict';

  // Read server-injected JSON data from the DOM
  const statsElement = document.getElementById('stadiumiq-stats-data');
  if (!statsElement) return;

  let stats, zoneAliases, venueAliases;
  try {
    const data = JSON.parse(statsElement.textContent);
    stats = data.stats;
    zoneAliases = data.zoneAliases;
    venueAliases = data.venueAliases;
  } catch (e) {
    console.error('Failed to parse admin stats data:', e);
    return;
  }

  const daily = stats.predictions_per_day;
  const service = stats.top_services;
  const region = stats.top_regions;

  function aliasLabels(labels, map) {
    return labels.map(function(l) { return map[l] || l; });
  }

  const isDark = () => document.documentElement.getAttribute('data-theme') !== 'light';
  const gridColor = () => isDark() ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
  const tickColor = () => isDark() ? '#636a8a' : '#8b93b8';

  const palette = ['#1a6b3c','#22c55e','#4ade80','#15803d','#86efac','#dcfce7','#6366f1','#818cf8'];

  const baseOpts = (hasLegend) => ({
    responsive: true,
    plugins: {
      legend: { display: !!hasLegend, position: 'bottom', labels: { color: tickColor(), boxWidth: 12, padding: 14, font: { size: 11 } } },
      tooltip: { callbacks: {} }
    },
    scales: {
      x: { ticks: { color: tickColor(), font: { size: 11 } }, grid: { color: gridColor() } },
      y: { beginAtZero: true, ticks: { color: tickColor(), font: { size: 11 }, stepSize: 1 }, grid: { color: gridColor() } }
    }
  });

  window.dailyChart = new Chart(document.getElementById('daily-chart'), {
    type: 'bar',
    data: { labels: daily.labels, datasets: [{ label: 'Assessments', data: daily.values, backgroundColor: palette[0], borderRadius: 5, borderSkipped: false }] },
    options: baseOpts(false)
  });

  window.serviceChart = new Chart(document.getElementById('service-chart'), {
    type: 'doughnut',
    data: { labels: aliasLabels(service.labels, zoneAliases), datasets: [{ data: service.values, backgroundColor: palette, borderWidth: 0 }] },
    options: { responsive: true, plugins: { legend: { display: true, position: 'bottom', labels: { color: tickColor(), boxWidth: 10, padding: 12, font: { size: 10 } } } } }
  });

  window.regionChart = new Chart(document.getElementById('region-chart'), {
    type: 'bar',
    data: { labels: aliasLabels(region.labels, venueAliases), datasets: [{ label: 'Count', data: region.values, backgroundColor: palette[1], borderRadius: 4, borderSkipped: false }] },
    options: { ...baseOpts(false), indexAxis: 'y' }
  });

  async function refreshCharts() {
    try {
      const res = await fetch('/api/stats');
      if (!res.ok) return;
      const d = await res.json();
      [['dailyChart','predictions_per_day'],['serviceChart','top_services'],['regionChart','top_regions']].forEach(([c, k]) => {
        if (window[c] && d[k]) {
          window[c].data.labels = k === 'top_services'
            ? aliasLabels(d[k].labels, zoneAliases)
            : k === 'top_regions'
              ? aliasLabels(d[k].labels, venueAliases)
              : d[k].labels;
          window[c].data.datasets[0].data = d[k].values;
          window[c].update();
        }
      });
    } catch (_) {}
  }

  setInterval(refreshCharts, 30_000);
}());
