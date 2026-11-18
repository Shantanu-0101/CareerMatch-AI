/* Resume builder: editable form + live preview. State is saved as JSON through the Save form. */
(function () {
  const state = JSON.parse(document.getElementById('builder-initial').textContent);
  ['education', 'projects', 'experience', 'certifications', 'achievements', 'hidden'].forEach(function (k) {
    if (!Array.isArray(state[k])) state[k] = [];
  });
  state.personal = state.personal || {};

  const editor = document.getElementById('editor');
  const preview = document.getElementById('preview');
  const form = document.getElementById('builder-form');
  const templateSelect = document.getElementById('template-select');

  const LISTS = {
    education: { title: 'Education', icon: 'fa-graduation-cap', add: 'Add education',
      fields: [['degree', 'Degree / course', 'B.Tech in Computer Engineering'], ['institution', 'Institution', 'ABC College of Engineering'],
               ['year', 'Year', '2021 - 2025'], ['score', 'CGPA / %', 'CGPA 8.4/10']] },
    projects: { title: 'Projects', icon: 'fa-diagram-project', add: 'Add project',
      fields: [['title', 'Project title', 'Career Match AI'], ['tech', 'Technologies', 'Python, Flask, SQLite'],
               ['link', 'Link (optional)', 'github.com/you/project'], ['description', 'Description (one point per line)', 'Built ...\nImproved ... by 30%', true]] },
    experience: { title: 'Work Experience', icon: 'fa-briefcase', add: 'Add experience',
      fields: [['role', 'Role', 'Software Intern'], ['company', 'Company', 'XYZ Pvt Ltd'], ['duration', 'Duration', 'Jun 2024 - Aug 2024'],
               ['description', 'Responsibilities / results (one per line)', 'Developed ...\nReduced ...', true]] },
    certifications: { title: 'Certifications', icon: 'fa-certificate', add: 'Add certification',
      fields: [['name', 'Certification', 'Python for Data Science'], ['issuer', 'Issuer', 'NPTEL'], ['year', 'Year', '2024']] },
    achievements: { title: 'Achievements', icon: 'fa-trophy', add: 'Add achievement',
      fields: [['text', 'Achievement', 'Winner, college hackathon 2024']] },
  };
  const TEXTS = {
    summary: { title: 'Professional Summary', icon: 'fa-align-left', area: true, ph: '2-3 lines about who you are and what you are looking for.' },
    skills: { title: 'Technical Skills', icon: 'fa-code', ph: 'Python, SQL, Flask, Git (comma separated)' },
    languages: { title: 'Languages', icon: 'fa-language', ph: 'English, Hindi, Marathi' },
  };
  const ORDER = ['summary', 'education', 'skills', 'projects', 'experience', 'certifications', 'achievements', 'languages'];
  const PERSONAL = [['full_name', 'Full name *'], ['email', 'Email'], ['phone', 'Phone'], ['location', 'Location'],
                    ['linkedin', 'LinkedIn URL'], ['github', 'GitHub URL'], ['website', 'Portfolio / website']];

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }
  function attr(s) { return esc(s).replace(/"/g, '&quot;'); }
  function isHidden(key) { return state.hidden.indexOf(key) !== -1; }

  function toggleHtml(key) {
    return '<label class="switch" title="Include this section"><input type="checkbox" data-toggle="' + key + '" ' +
      (isHidden(key) ? '' : 'checked') + '><span></span> Include</label>';
  }

  function renderEditor() {
    let html = '<section class="b-section"><h3><i class="fa-solid fa-user"></i> Personal details</h3><div class="form-grid">';
    PERSONAL.forEach(function (f) {
      html += '<div class="form-group"><label>' + f[1] + '</label><input data-personal="' + f[0] + '" value="' +
        attr(state.personal[f[0]] || '') + '" maxlength="200"></div>';
    });
    html += '</div></section>';

    ORDER.forEach(function (key) {
      const hiddenCls = isHidden(key) ? ' is-hidden' : '';
      if (TEXTS[key]) {
        const t = TEXTS[key];
        html += '<section class="b-section' + hiddenCls + '"><div class="b-head"><h3><i class="fa-solid ' + t.icon + '"></i> ' + t.title + '</h3>' + toggleHtml(key) + '</div>';
        html += t.area
          ? '<textarea data-text="' + key + '" rows="3" maxlength="1500" placeholder="' + attr(t.ph) + '">' + esc(state[key] || '') + '</textarea>'
          : '<input data-text="' + key + '" maxlength="1000" placeholder="' + attr(t.ph) + '" value="' + attr(state[key] || '') + '">';
        html += '</section>';
        return;
      }
      const L = LISTS[key];
      html += '<section class="b-section' + hiddenCls + '"><div class="b-head"><h3><i class="fa-solid ' + L.icon + '"></i> ' + L.title + '</h3>' + toggleHtml(key) + '</div>';
      if (!state[key].length) html += '<p class="muted small">No entries yet.</p>';
      state[key].forEach(function (entry, i) {
        html += '<div class="b-entry"><button type="button" class="icon-btn danger b-remove" data-remove="' + key + '" data-index="' + i + '" title="Remove"><i class="fa-solid fa-xmark"></i></button><div class="form-grid">';
        L.fields.forEach(function (f) {
          const val = entry[f[0]] || '';
          const common = ' data-list="' + key + '" data-index="' + i + '" data-field="' + f[0] + '" placeholder="' + attr(f[2]) + '"';
          html += '<div class="form-group' + (f[3] || key === 'achievements' ? ' full' : '') + '"><label>' + f[1] + '</label>' +
            (f[3] ? '<textarea rows="3"' + common + '>' + esc(val) + '</textarea>' : '<input' + common + ' value="' + attr(val) + '">') + '</div>';
        });
        html += '</div></div>';
      });
      html += '<button type="button" class="btn btn-ghost btn-sm" data-add="' + key + '"><i class="fa-solid fa-plus"></i> ' + L.add + '</button></section>';
    });
    editor.innerHTML = html;
  }

  function bullets(text) {
    const lines = (text || '').split('\n').map(function (l) { return l.replace(/^[\s\-•]+/, '').trim(); }).filter(Boolean);
    return lines.length ? '<ul>' + lines.map(function (l) { return '<li>' + esc(l) + '</li>'; }).join('') + '</ul>' : '';
  }

  function renderPreview() {
    const p = state.personal;
    let html = '<h1>' + esc(p.full_name || 'Your Name') + '</h1>';
    const contact = ['email', 'phone', 'location', 'linkedin', 'github', 'website'].map(function (k) { return p[k]; }).filter(Boolean);
    html += '<p class="contact">' + contact.map(esc).join(' | ') + '</p>';
    ORDER.forEach(function (key) {
      if (isHidden(key)) return;
      const v = state[key];
      if (!v || (Array.isArray(v) && !v.length)) return;
      const title = (TEXTS[key] || LISTS[key]).title;
      let body = '';
      if (key === 'summary' || key === 'skills' || key === 'languages') body = '<p>' + esc(v) + '</p>';
      else if (key === 'education') body = v.map(function (e) {
        return '<div class="item"><b>' + esc(e.degree) + '</b>' + (e.institution ? ', ' + esc(e.institution) : '') +
          '<div class="meta">' + [e.year, e.score].filter(Boolean).map(esc).join(' | ') + '</div></div>';
      }).join('');
      else if (key === 'projects') body = v.map(function (e) {
        return '<div class="item"><b>' + esc(e.title) + '</b>' + (e.tech ? ' | <i>' + esc(e.tech) + '</i>' : '') +
          (e.link ? '<div class="meta">' + esc(e.link) + '</div>' : '') + bullets(e.description) + '</div>';
      }).join('');
      else if (key === 'experience') body = v.map(function (e) {
        return '<div class="item"><b>' + esc(e.role) + '</b>' + (e.company ? ', ' + esc(e.company) : '') +
          (e.duration ? '<div class="meta">' + esc(e.duration) + '</div>' : '') + bullets(e.description) + '</div>';
      }).join('');
      else if (key === 'certifications') body = v.map(function (e) {
        const meta = [e.issuer, e.year].filter(Boolean).map(esc).join(', ');
        return '<div class="item"><b>' + esc(e.name) + '</b>' + (meta ? ' - ' + meta : '') + '</div>';
      }).join('');
      else if (key === 'achievements') body = bullets(v.map(function (a) { return a.text; }).join('\n'));
      html += '<section><h2>' + title + '</h2>' + body + '</section>';
    });
    preview.innerHTML = html;
  }

  editor.addEventListener('input', function (e) {
    const t = e.target;
    if (t.dataset.personal) state.personal[t.dataset.personal] = t.value;
    else if (t.dataset.text) state[t.dataset.text] = t.value;
    else if (t.dataset.list) state[t.dataset.list][+t.dataset.index][t.dataset.field] = t.value;
    renderPreview();
  });

  editor.addEventListener('change', function (e) {
    const key = e.target.dataset.toggle;
    if (!key) return;
    state.hidden = state.hidden.filter(function (h) { return h !== key; });
    if (!e.target.checked) state.hidden.push(key);
    e.target.closest('.b-section').classList.toggle('is-hidden', !e.target.checked);
    renderPreview();
  });

  editor.addEventListener('click', function (e) {
    const add = e.target.closest('[data-add]');
    const remove = e.target.closest('[data-remove]');
    if (add) {
      const key = add.dataset.add;
      const entry = {};
      LISTS[key].fields.forEach(function (f) { entry[f[0]] = ''; });
      state[key].push(entry);
      state.hidden = state.hidden.filter(function (h) { return h !== key; });
      renderEditor(); renderPreview();
      const inputs = editor.querySelectorAll('[data-list="' + key + '"][data-index="' + (state[key].length - 1) + '"]');
      if (inputs.length) inputs[0].focus();
    } else if (remove) {
      state[remove.dataset.remove].splice(+remove.dataset.index, 1);
      renderEditor(); renderPreview();
    }
  });

  templateSelect.addEventListener('change', function () {
    preview.className = 'paper template-' + templateSelect.value;
  });

  form.addEventListener('submit', function (e) {
    if (!(state.personal.full_name || '').trim()) {
      e.preventDefault();
      window.toast('Please enter your full name in Personal details.', 'error');
      return;
    }
    document.getElementById('builder-then').value = (e.submitter && e.submitter.dataset.then) || '';
    document.getElementById('builder-data').value = JSON.stringify(state);
  });

  renderEditor();
  renderPreview();
})();
