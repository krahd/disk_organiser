// Demo main.js — adds simulated scan, sample data, and small D3 visualisation
/* eslint-env browser */
/* global d3 */

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  const units = ['KB','MB','GB','TB'];
  let u = -1;
  do { bytes /= 1024; u++; } while (bytes >= 1024 && u < units.length - 1);
  return bytes.toFixed(1) + ' ' + units[u];
}

document.addEventListener('DOMContentLoaded', () => {
  const scanBtn = document.getElementById('scan-btn');
  const scanStatus = document.getElementById('scan-status');
  const duplicatesList = document.getElementById('duplicates-list');
  const viz = document.getElementById('viz');
  const previewModal = document.getElementById('preview-modal');
  const previewBody = document.getElementById('preview-modal-body');
  const previewClose = document.getElementById('preview-modal-close');

  const sample = {
    duplicates: [
      { name: 'Photos/IMG_001.jpg', size: 14_200_000, note: 'Shot on phone' },
      { name: 'Photos/IMG_001 (copy).jpg', size: 14_200_000, note: 'Duplicate copy' },
      { name: 'Music/track01.mp3', size: 5_200_000, note: 'Album rip' },
      { name: 'Music/track01 (1).mp3', size: 5_200_000, note: 'Duplicate copy' },
      { name: 'Documents/report.pdf', size: 340_000, note: 'Quarterly report' },
      { name: 'Documents/report (copy).pdf', size: 340_000, note: 'Duplicate copy' }
    ],
    byType: [
      { label: 'Photos', value: 28_400_000 },
      { label: 'Music', value: 10_400_000 },
      { label: 'Documents', value: 680_000 }
    ],
    recycle: [
      { name: 'Videos/clip_old.mp4', size: 56_400_000, note: 'Low quality duplicate' },
      { name: 'Temp/tmp123.tmp', size: 2_400, note: 'Temporary file' },
      { name: 'Downloads/manual.pdf', size: 1_240_000, note: 'Installer manual (old)'}
    ],
    organise: [
      { file: 'Documents/report.pdf', suggestion: 'Reports/2026/report.pdf', reason: 'Group by year' },
      { file: 'Music/track01.mp3', suggestion: 'Music/Album/track01.mp3', reason: 'Place in album folder' }
    ]
  };

  function renderDuplicates(list) {
    duplicatesList.innerHTML = '';
    list.forEach((f, i) => {
      const li = document.createElement('li');
      li.className = 'dup-item';
      li.tabIndex = 0;
      li.innerHTML = `<div class="dup-name">${f.name}</div><div class="dup-meta">${formatBytes(f.size)}</div>`;
      li.addEventListener('click', () => showPreview(f));
      li.addEventListener('keydown', (e) => { if (e.key === 'Enter') showPreview(f); });
      duplicatesList.appendChild(li);
    });
  }

  function showPreview(file) {
    previewBody.innerHTML = `<p><strong>${file.name}</strong></p><p>Size: ${formatBytes(file.size)}</p><p>${file.note || ''}</p>`;
    previewModal.classList.remove('hidden');
    previewModal.setAttribute('aria-hidden','false');
    // focus management
    previewModal.__lastFocus = document.activeElement;
    previewClose.focus();
  }

  previewClose.addEventListener('click', () => {
    previewModal.classList.add('hidden');
    previewModal.setAttribute('aria-hidden','true');
    if (previewModal.__lastFocus) previewModal.__lastFocus.focus();
  });

  // close on ESC
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !previewModal.classList.contains('hidden')) {
      previewModal.classList.add('hidden');
      previewModal.setAttribute('aria-hidden','true');
      if (previewModal.__lastFocus) previewModal.__lastFocus.focus();
    }
  });

  function renderViz(data) {
    viz.innerHTML = '';
    const width = Math.min(480, viz.clientWidth || 480);
    const height = 220;
    const svg = d3.select(viz).append('svg').attr('width', width).attr('height', height);

    const margin = {top:20,right:20,bottom:30,left:100};
    const w = width - margin.left - margin.right;
    const h = height - margin.top - margin.bottom;

    const x = d3.scaleLinear().range([0, w]).domain([0, d3.max(data, d => d.value)]);
    const y = d3.scaleBand().range([0, h]).domain(data.map(d => d.label)).padding(0.2);

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
    g.append('g').call(d3.axisLeft(y));
    g.selectAll('.bar').data(data).enter().append('rect')
      .attr('class','bar')
      .attr('y', d => y(d.label))
      .attr('height', y.bandwidth())
      .attr('x', 0)
      .attr('width', d => x(d.value))
      .style('fill','#2563eb');

    g.selectAll('.label').data(data).enter().append('text')
      .attr('x', d => x(d.value) + 8)
      .attr('y', d => y(d.label) + y.bandwidth() / 2 + 4)
      .text(d => formatBytes(d.value))
      .style('font-size','12px')
      .style('fill','#0f172a');
  }

  function displayResults() {
    renderDuplicates(sample.duplicates);
    renderViz(sample.byType);
    // populate recycle and organise panels as well
    renderRecycleList(sample.recycle);
    renderOrganiseList(sample.organise);
  }

  // --- recycle flow ---
  function renderRecycleList(items) {
    const ul = document.getElementById('recycle-list');
    ul.innerHTML = '';
    items.forEach((it, idx) => {
      const li = document.createElement('li');
      li.className = 'dup-item';
      li.innerHTML = `<label><input type="checkbox" data-idx="${idx}" /> <span class="dup-name">${it.name}</span></label><div class="dup-meta">${formatBytes(it.size)}</div>`;
      ul.appendChild(li);
    });
  }

  document.getElementById('apply-recycle-btn').addEventListener('click', () => {
    const checks = Array.from(document.querySelectorAll('#recycle-list input[type=checkbox]'));
    const selected = checks.filter(c => c.checked).map(c => sample.recycle[Number(c.dataset.idx)]);
    if (selected.length === 0) {
      previewBody.innerHTML = '<p>No items selected for removal.</p>';
    } else {
      previewBody.innerHTML = `<p><strong>${selected.length} items</strong> selected for preview:</p><ul>${selected.map(s => `<li>${s.name} — ${formatBytes(s.size)}</li>`).join('')}</ul>`;
    }
    previewModal.classList.remove('hidden');
    previewModal.setAttribute('aria-hidden','false');
    previewModal.__lastFocus = document.activeElement;
    previewClose.focus();
  });

  // --- organise flow ---
  function renderOrganiseList(items) {
    const ul = document.getElementById('organise-list');
    ul.innerHTML = '';
    items.forEach((it, idx) => {
      const li = document.createElement('li');
      li.className = 'dup-item';
      li.innerHTML = `<div class="dup-name">${it.file} → ${it.suggestion}</div><div class="dup-meta">${it.reason}</div>`;
      ul.appendChild(li);
    });
  }

  document.getElementById('apply-organise-btn').addEventListener('click', () => {
    const items = sample.organise;
    previewBody.innerHTML = `<p>Preview suggested moves (${items.length}):</p><ul>${items.map(i => `<li>${i.file} → ${i.suggestion} (${i.reason})</li>`).join('')}</ul>`;
    previewModal.classList.remove('hidden');
    previewModal.setAttribute('aria-hidden','false');
    previewModal.__lastFocus = document.activeElement;
    previewClose.focus();
  });

  // panel show/hide helpers
  function showPanel(panelId) {
    ['duplicates-panel','viz-panel','recycle-panel','organise-panel','preferences-panel'].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      if (id === panelId) { el.classList.remove('hidden'); el.setAttribute('aria-hidden','false'); }
      else { el.classList.add('hidden'); el.setAttribute('aria-hidden','true'); }
    });
  }

  // Simulated scan
  scanBtn.addEventListener('click', () => {
    scanBtn.disabled = true;
    scanStatus.textContent = 'Scanning: 0%';
    let p = 0;
    const t = setInterval(() => {
      p += Math.floor(Math.random() * 18) + 7;
      if (p >= 100) {
        p = 100;
        scanStatus.textContent = 'Scan complete — sample data loaded.';
        clearInterval(t);
        scanBtn.disabled = false;
        displayResults();
      } else {
        scanStatus.textContent = `Scanning: ${p}%`;
      }
    }, 300);
  });

  // navigation behaviour (show panels)
  const navButtons = document.querySelectorAll('.site-nav .nav-btn');
  function setNavActive(id) {
    navButtons.forEach(b => b.setAttribute('aria-pressed','false'));
    const btn = document.getElementById(id);
    if (btn) btn.setAttribute('aria-pressed','true');
  }

  document.getElementById('nav-duplicates').addEventListener('click', () => { setNavActive('nav-duplicates'); showPanel('duplicates-panel'); duplicatesList.parentElement.scrollIntoView({behavior:'smooth'}); });
  document.getElementById('nav-visualisation').addEventListener('click', () => { setNavActive('nav-visualisation'); showPanel('viz-panel'); viz.parentElement.scrollIntoView({behavior:'smooth'}); });
  document.getElementById('nav-recycle').addEventListener('click', () => { setNavActive('nav-recycle'); showPanel('recycle-panel'); document.getElementById('recycle-list').scrollIntoView({behavior:'smooth'}); });
  document.getElementById('nav-organise').addEventListener('click', () => { setNavActive('nav-organise'); showPanel('organise-panel'); document.getElementById('organise-list').scrollIntoView({behavior:'smooth'}); });
  document.getElementById('nav-preferences').addEventListener('click', () => { setNavActive('nav-preferences'); showPanel('preferences-panel'); alert('Preferences (demo): preview only.'); });

  // initial small hint
  scanStatus.textContent = 'No scan yet. Click "Run simulated scan" to populate demo data.';
});
