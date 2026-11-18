/* Shared UI: toasts, loading overlay, sidebar, confirmations, dashboard charts. */
(function () {
  // ---------- Toasts
  const ICONS = { success: 'fa-circle-check', error: 'fa-circle-xmark', warning: 'fa-triangle-exclamation', info: 'fa-circle-info' };
  window.toast = function (message, type) {
    type = ICONS[type] ? type : (type === 'message' ? 'info' : 'info');
    const box = document.getElementById('toasts');
    const el = document.createElement('div');
    el.className = 'toast toast-' + type;
    const icon = document.createElement('i');
    icon.className = 'fa-solid ' + ICONS[type];
    const text = document.createElement('span');
    text.textContent = message;
    const close = document.createElement('button');
    close.className = 'toast-close';
    close.setAttribute('aria-label', 'Dismiss');
    close.innerHTML = '&times;';
    close.onclick = function () { el.remove(); };
    el.append(icon, text, close);
    box.appendChild(el);
    setTimeout(function () { el.classList.add('hide'); setTimeout(function () { el.remove(); }, 400); }, type === 'error' || type === 'warning' ? 7000 : 4500);
  };
  try {
    JSON.parse(document.getElementById('flash-data').textContent || '[]').forEach(function (m) {
      window.toast(m[1], m[0] === 'message' ? 'info' : m[0]);
    });
  } catch (e) { /* ignore */ }

  // ---------- Loading overlay on forms with data-loading
  const overlay = document.getElementById('loading');
  document.addEventListener('submit', function (e) {
    const form = e.target;
    if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) { e.preventDefault(); return; }
    if (e.defaultPrevented) return;
    if (form.dataset.loading && overlay) {
      document.getElementById('loading-text').textContent = form.dataset.loading;
      overlay.hidden = false;
      form.querySelectorAll('button').forEach(function (b) { b.disabled = true; });
      // Keep the clicked button's name/value (e.g. action=skip) since disabled buttons are not submitted.
      if (e.submitter && e.submitter.name) {
        const h = document.createElement('input');
        h.type = 'hidden'; h.name = e.submitter.name; h.value = e.submitter.value;
        form.appendChild(h);
      }
    }
  });
  window.addEventListener('pageshow', function () { if (overlay) overlay.hidden = true; });

  // ---------- Sidebar (mobile)
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  const menuBtn = document.getElementById('menu-btn');
  function setMenu(open) { sidebar.classList.toggle('open', open); backdrop.classList.toggle('show', open); }
  if (menuBtn) {
    menuBtn.addEventListener('click', function () { setMenu(!sidebar.classList.contains('open')); });
    backdrop.addEventListener('click', function () { setMenu(false); });
  }

  // ---------- Password visibility
  document.querySelectorAll('.toggle-password').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const input = btn.parentElement.querySelector('input');
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.innerHTML = '<i class="fa-solid ' + (show ? 'fa-eye-slash' : 'fa-eye') + '"></i>';
    });
  });

  // ---------- File drop zone
  const fileInput = document.getElementById('resume-file');
  if (fileInput) {
    const zone = document.getElementById('dropzone');
    const label = document.getElementById('file-label');
    const update = function () {
      const f = fileInput.files[0];
      if (!f) return;
      const ok = /\.(pdf|docx)$/i.test(f.name);
      label.textContent = ok ? f.name + ' (' + Math.round(f.size / 1024) + ' KB)' : 'Only PDF or DOCX files are allowed';
      zone.classList.toggle('has-file', ok);
      if (!ok) { fileInput.value = ''; window.toast('Only PDF and DOCX files are allowed.', 'error'); }
    };
    fileInput.addEventListener('change', update);
    ['dragenter', 'dragover'].forEach(function (ev) { zone.addEventListener(ev, function () { zone.classList.add('drag'); }); });
    ['dragleave', 'drop'].forEach(function (ev) { zone.addEventListener(ev, function () { zone.classList.remove('drag'); }); });
  }

  // ---------- Dashboard charts
  window.dashboardCharts = function (data) {
    if (typeof Chart === 'undefined') return;
    Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
    Chart.defaults.color = '#64748b';
    const palette = ['#6366f1', '#3b82f6', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'];
    if (data.categories) {
      new Chart(document.getElementById('categoryChart'), {
        type: 'bar',
        data: { labels: data.categories.labels, datasets: [{ label: 'Score (%)', data: data.categories.values,
          backgroundColor: data.categories.values.map(function (v) { return v >= 75 ? '#10b981' : v >= 45 ? '#6366f1' : '#f59e0b'; }),
          borderRadius: 6, maxBarThickness: 26 }] },
        options: { indexAxis: 'y', maintainAspectRatio: false, plugins: { legend: { display: false } },
          scales: { x: { min: 0, max: 100, ticks: { callback: function (v) { return v + '%'; } } }, y: { grid: { display: false } } } },
      });
    }
    if (data.history) {
      new Chart(document.getElementById('historyChart'), {
        type: 'line',
        data: { labels: data.history.labels, datasets: [{ label: 'Resume score', data: data.history.values, borderColor: '#6366f1',
          backgroundColor: 'rgba(99,102,241,.12)', fill: true, tension: .35, pointRadius: 4, pointBackgroundColor: '#6366f1' }] },
        options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100 } } },
      });
    }
    if (data.interview) {
      new Chart(document.getElementById('interviewChart'), {
        type: 'doughnut',
        data: { labels: data.interview.labels, datasets: [{ data: data.interview.values, backgroundColor: palette, borderWidth: 0 }] },
        options: { maintainAspectRatio: false, cutout: '62%', plugins: { legend: { position: 'right' } } },
      });
    }
  };
})();
