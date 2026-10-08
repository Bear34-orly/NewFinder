/* Page Concurrence : analyse de ta chaîne et comparaison avec ses concurrents directs. */
(function () {
  const root = document.getElementById('page-competition');
  const CP = {
    code: null, me: null, channels: [], markets: [],
    selected: null, analyses: [], analysis: null, activeComp: null,
    poll: null, loginError: '', error: '', busy: false, opened: false,
  };

  const esc = v => { const d = document.createElement('div'); d.textContent = v == null ? '' : String(v); return d.innerHTML; };
  const num = n => (n == null ? 'n/d' : Math.round(n).toLocaleString('fr-FR'));
  const GROUPS = { scale: 'Taille', performance: 'Performance', rhythm: 'Rythme de publication', style: 'Style (titres et durée)' };
  const LEVELS = { observed: 'Observé', calculated: 'Calculé', inferred: 'Inféré' };

  try { CP.code = localStorage.getItem('nf_access_code'); } catch (e) {}

  async function api(path, options) {
    const opts = Object.assign({ headers: {} }, options || {});
    opts.headers = Object.assign({ 'X-Access-Code': CP.code || '' }, opts.headers);
    if (opts.body && typeof opts.body !== 'string') {
      opts.body = JSON.stringify(opts.body);
      opts.headers['Content-Type'] = 'application/json';
    }
    const resp = await fetch('/api/competition' + path, opts);
    let data = null;
    try { data = await resp.json(); } catch (e) {}
    if (resp.status === 401) {
      CP.code = null; CP.me = null;
      try { localStorage.removeItem('nf_access_code'); } catch (e) {}
      throw new Error('Code d\'accès invalide.');
    }
    if (!resp.ok) throw new Error((data && data.error) || ('Erreur ' + resp.status));
    return data;
  }

  /* ------------------------------------------------------------ ouverture */
  window.cpOpen = async function () {
    if (!CP.opened) {
      CP.opened = true;
      render();
      if (CP.code) await loadAll();
    } else if (CP.code && !CP.analysis && !CP.poll) {
      await loadAll();
    }
  };

  async function loadAll() {
    try {
      CP.me = await api('/me');
      CP.channels = await api('/channels');
      try { CP.markets = await (await fetch('/api/markets')).json(); } catch (e) { CP.markets = []; }
      if (!CP.selected && CP.channels.length) CP.selected = CP.channels[0].channel_id;
      CP.error = '';
      render();
      if (CP.selected) await loadAnalyses();
    } catch (e) {
      CP.loginError = e.message;
      render();
    }
  }

  async function loadAnalyses() {
    CP.analyses = await api('/analyses?channel_id=' + encodeURIComponent(CP.selected));
    const running = CP.analyses.find(a => a.status === 'running');
    const latestDone = CP.analyses.find(a => a.status === 'done');
    if (running) { startPolling(running.id); }
    else if (latestDone) { await openAnalysis(latestDone.id); }
    else { CP.analysis = null; render(); }
  }

  async function openAnalysis(id) {
    CP.analysis = await api('/analyses/' + id);
    if (CP.analysis.report && (!CP.activeComp ||
        !CP.analysis.report.competitors.some(c => c.profile.channel_id === CP.activeComp))) {
      CP.activeComp = CP.analysis.report.competitors.length ? CP.analysis.report.competitors[0].profile.channel_id : null;
    }
    render();
  }

  function startPolling(id) {
    stopPolling();
    const tick = async () => {
      try {
        const a = await api('/analyses/' + id);
        CP.analysis = a;
        if (a.status === 'running') {
          const el = document.getElementById('cp-progress-text');
          if (el) el.textContent = a.progress || '...'; else render();
          CP.poll = setTimeout(tick, 3000);
        } else {
          CP.poll = null;
          CP.me = await api('/me');
          if (a.status === 'done') { await openAnalysis(id); await loadAnalysesList(); }
          else render();
        }
      } catch (e) { CP.poll = null; CP.error = e.message; render(); }
    };
    tick();
  }
  function stopPolling() { if (CP.poll) { clearTimeout(CP.poll); CP.poll = null; } }
  async function loadAnalysesList() { CP.analyses = await api('/analyses?channel_id=' + encodeURIComponent(CP.selected)); render(); }

  /* ------------------------------------------------------------ actions */
  async function login() {
    const v = document.getElementById('cp-code').value.trim();
    if (!v) return;
    CP.code = v; CP.loginError = '';
    try { localStorage.setItem('nf_access_code', v); } catch (e) {}
    await loadAll();
  }

  function logout() {
    stopPolling();
    CP.code = null; CP.me = null; CP.channels = []; CP.selected = null; CP.analysis = null; CP.analyses = [];
    try { localStorage.removeItem('nf_access_code'); } catch (e) {}
    render();
  }

  async function addChannel() {
    const url = document.getElementById('cp-url').value.trim();
    const market = document.getElementById('cp-market').value;
    if (!url) return;
    CP.busy = true; CP.error = ''; render();
    try {
      const ch = await api('/channels', { method: 'POST', body: { url, market } });
      CP.channels = await api('/channels');
      CP.selected = ch.channel_id; CP.analysis = null; CP.analyses = [];
      stopPolling();
    } catch (e) { CP.error = e.message; }
    CP.busy = false; render();
  }

  async function selectChannel(cid) {
    if (cid === CP.selected) return;
    stopPolling();
    CP.selected = cid; CP.analysis = null; CP.activeComp = null; CP.error = '';
    render();
    await loadAnalyses();
  }

  async function removeChannel(cid) {
    if (!confirm('Supprimer cette chaîne et ses analyses ?')) return;
    try {
      await api('/channels/' + encodeURIComponent(cid), { method: 'DELETE' });
      CP.channels = await api('/channels');
      if (CP.selected === cid) { CP.selected = CP.channels.length ? CP.channels[0].channel_id : null; CP.analysis = null; CP.analyses = []; stopPolling(); }
      render();
      if (CP.selected) await loadAnalyses();
    } catch (e) { CP.error = e.message; render(); }
  }

  async function startAnalysis() {
    CP.error = ''; CP.busy = true; render();
    try {
      const r = await api('/analyses', { method: 'POST', body: { channel_id: CP.selected } });
      CP.busy = false; CP.activeComp = null;
      startPolling(r.id);
    } catch (e) { CP.busy = false; CP.error = e.message; render(); }
  }

  async function addCompetitor() {
    const url = document.getElementById('cp-comp-url').value.trim();
    if (!url) return;
    CP.busy = true; CP.error = ''; render();
    try {
      CP.analysis = await api('/analyses/' + CP.analysis.id + '/competitors', { method: 'POST', body: { url } });
      const comps = CP.analysis.report.competitors;
      const manual = comps.filter(c => c.source === 'manuel');
      if (manual.length) CP.activeComp = manual[manual.length - 1].profile.channel_id;
    } catch (e) { CP.error = e.message; }
    CP.busy = false; render();
  }

  async function removeCompetitor(cid) {
    try {
      CP.analysis = await api('/analyses/' + CP.analysis.id + '/competitors/' + encodeURIComponent(cid), { method: 'DELETE' });
      if (CP.activeComp === cid) {
        const c = CP.analysis.report.competitors;
        CP.activeComp = c.length ? c[0].profile.channel_id : null;
      }
    } catch (e) { CP.error = e.message; }
    render();
  }

  /* ------------------------------------------------------------ rendu */
  function render() {
    if (!CP.code || !CP.me) { root.innerHTML = loginView(); bindLogin(); return; }
    const sel = CP.channels.find(c => c.channel_id === CP.selected);
    root.innerHTML = '<div class="cp-wrap">' + headerView() + channelsView() + (sel ? analysisView(sel) : emptyView()) + '</div>';
    bindMain();
  }

  function loginView() {
    return '<div class="cp-panel cp-login"><h2>Concurrence</h2>' +
      '<p class="cp-muted">Entre ton code d\'accès personnel pour analyser tes chaînes et les comparer à leurs concurrents directs.</p>' +
      '<div class="cp-row"><input class="cp-input" id="cp-code" placeholder="Code d\'accès" autocomplete="off">' +
      '<button class="cp-btn" id="cp-login">Entrer</button></div>' +
      (CP.loginError ? '<div class="cp-error">' + esc(CP.loginError) + '</div>' : '') + '</div>';
  }
  function bindLogin() {
    const b = document.getElementById('cp-login'), i = document.getElementById('cp-code');
    if (b) b.onclick = login;
    if (i) i.onkeydown = e => { if (e.key === 'Enter') login(); };
  }

  function headerView() {
    const left = CP.me.daily_limit - CP.me.used_today;
    return '<div class="cp-panel cp-spread"><div><h2 style="margin:0">Concurrence — ' + esc(CP.me.name) + '</h2>' +
      '<div class="cp-muted">Analyses restantes (24 h) : ' + Math.max(0, left) + ' / ' + CP.me.daily_limit + '</div></div>' +
      '<button class="cp-btn ghost small" id="cp-logout">Changer de code</button></div>';
  }

  function channelsView() {
    const marketOpts = '<option value="">Marché (facultatif)</option>' +
      CP.markets.map(m => '<option value="' + esc(m) + '">' + esc(m.replace(/_/g, ' ')) + '</option>').join('');
    let list = '';
    if (CP.channels.length) {
      list = '<div class="cp-channels">' + CP.channels.map(c =>
        '<div class="cp-chan' + (c.channel_id === CP.selected ? ' active' : '') + '" data-select="' + esc(c.channel_id) + '">' +
        '<div class="avatar" style="background-image:url(\'' + esc(c.thumbnail || '') + '\')"></div>' +
        '<div class="head-text"><div class="card-title">' + esc(c.channel_title) + '</div>' +
        '<div class="card-sub">' + esc(c.market ? c.market.replace(/_/g, ' ') : 'marché non précisé') + '</div></div>' +
        '<button class="cp-btn danger small" data-remove="' + esc(c.channel_id) + '" title="Supprimer">✕</button></div>'
      ).join('') + '</div>';
    }
    return '<div class="cp-panel"><h2>Mes chaînes</h2>' + list +
      '<h3>Ajouter une chaîne</h3><div class="cp-row">' +
      '<input class="cp-input" id="cp-url" placeholder="Lien de la chaîne (https://www.youtube.com/@nom)">' +
      '<select class="cp-select" id="cp-market">' + marketOpts + '</select>' +
      '<button class="cp-btn" id="cp-add"' + (CP.busy ? ' disabled' : '') + '>Ajouter</button></div>' +
      (CP.error && !CP.analysis ? '<div class="cp-error">' + esc(CP.error) + '</div>' : '') + '</div>';
  }

  function emptyView() {
    return '<div class="cp-panel cp-muted">Ajoute ta première chaîne ci-dessus pour lancer une analyse.</div>';
  }

  function analysisView(sel) {
    const a = CP.analysis;
    const running = a && a.status === 'running';
    const left = CP.me.daily_limit - CP.me.used_today;

    let head = '<div class="cp-panel"><div class="cp-spread"><div><h2 style="margin:0">Analyse — ' + esc(sel.channel_title) + '</h2>' +
      '<div class="cp-muted">Une analyse lit tes dernières vidéos, cherche des concurrents directs et les compare avec toi (≈ 220 unités de quota).</div></div>' +
      '<div class="cp-row">' + historySelect() +
      '<button class="cp-btn" id="cp-start"' + (running || CP.busy || left <= 0 ? ' disabled' : '') + '>' +
      (a && a.status === 'done' ? 'Relancer l\'analyse' : 'Lancer l\'analyse') + '</button></div></div>';

    if (running) {
      head += '<div class="cp-progress"><i></i></div><div class="cp-muted" id="cp-progress-text">' + esc(a.progress || '...') + '</div>';
    }
    if (a && a.status === 'error') head += '<div class="cp-error">' + esc(a.error) + '</div>';
    if (CP.error) head += '<div class="cp-error">' + esc(CP.error) + '</div>';
    head += '</div>';

    if (a && a.status === 'done' && a.report) return head + reportView(a.report);
    return head;
  }

  function historySelect() {
    const done = CP.analyses.filter(x => x.status === 'done');
    if (done.length < 2) return '';
    return '<select class="cp-select" id="cp-history">' + done.map(x =>
      '<option value="' + x.id + '"' + (CP.analysis && CP.analysis.id === x.id ? ' selected' : '') + '>Analyse du ' +
      esc(new Date(x.created_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })) + '</option>').join('') + '</select>';
  }

  function reportView(r) {
    return legendView() + mineView(r) + competitorsView(r) + comparisonView(r) + associationsView(r) + footerView(r);
  }

  function legendView() {
    return '<div class="cp-panel"><div class="cp-tags">' +
      '<span class="cp-tag observed">Observé</span><span class="cp-muted">donnée brute de YouTube</span>' +
      '<span class="cp-tag calculated">Calculé</span><span class="cp-muted">résultat d\'un calcul sur ces données</span>' +
      '<span class="cp-tag inferred">Inféré</span><span class="cp-muted">association constatée, pas une preuve de cause</span></div></div>';
  }

  function kpi(label, value) { return '<div class="cp-kpi"><b>' + value + '</b><span>' + label + '</span></div>'; }

  function mineView(r) {
    const m = r.mine;
    let hist = '';
    if (m.history) {
      const d = m.history.subs_change;
      hist = kpi('Abonnés depuis ' + m.history.days + ' j', (d >= 0 ? '+' : '') + num(d));
    }
    const notes = (r.notes || []).map(n => '<div class="cp-muted">⚠ ' + esc(n) + '</div>').join('');
    return '<div class="cp-panel"><h2>Ta chaîne</h2><div class="cp-kpis">' +
      kpi('Abonnés', num(m.subscribers)) + kpi('Vues médianes', num(m.median_views)) +
      kpi('Vues médianes par abonné', m.views_per_sub == null ? 'n/d' : m.views_per_sub.toFixed(2)) +
      kpi('Vidéos longues / mois', m.videos_per_month) +
      kpi('Vidéos à 3× la médiane', m.breakout_rate == null ? 'n/d' : Math.round(m.breakout_rate * 100) + ' %') +
      kpi('Durée médiane (min)', m.median_duration_min == null ? 'n/d' : m.median_duration_min) + hist +
      '</div>' + notes + '</div>';
  }

  function sourceLabel(s) { return s === 'base' ? 'Base Niche Finder' : s === 'manuel' ? 'Ajouté par toi' : 'Recherche YouTube'; }
  const PART_LABELS = { size: 'Taille', topics: 'Sujets', duration: 'Durée', frequency: 'Rythme', market: 'Marché' };

  function competitorsView(r) {
    let cards = r.competitors.map(c => {
      const p = c.profile, s = c.similarity || { score: 0, parts: {} };
      const parts = Object.keys(PART_LABELS).filter(k => s.parts[k] != null)
        .map(k => '<span class="cp-tag">' + PART_LABELS[k] + ' ' + s.parts[k] + '</span>').join('');
      const common = (s.common_keywords || []).length ? '<div class="cp-muted">Mots communs : ' + esc(s.common_keywords.join(', ')) + '</div>' : '';
      return '<div class="cp-comp' + (p.channel_id === CP.activeComp ? ' active' : '') + '">' +
        '<div class="cp-row"><div class="avatar" style="background-image:url(\'' + esc(p.thumbnail || '') + '\')"></div>' +
        '<div class="head-text"><div class="card-title"><a href="' + esc(p.url) + '" target="_blank" rel="noopener" style="color:inherit;text-decoration:none">' + esc(p.title) + '</a></div>' +
        '<div class="card-sub">' + num(p.subscribers) + ' abonnés · ' + esc(sourceLabel(c.source)) + '</div></div>' +
        '<div class="cp-score" title="Proximité calculée /100">' + s.score + '</div></div>' +
        '<div class="cp-tags">' + parts + '</div>' + common +
        '<div class="cp-row"><button class="cp-btn small" data-compare="' + esc(p.channel_id) + '">Comparer</button>' +
        '<button class="cp-btn ghost small" data-drop="' + esc(p.channel_id) + '">Retirer</button></div></div>';
    }).join('');
    if (!cards) cards = '<div class="cp-muted">Aucun concurrent trouvé automatiquement. Ajoute-en un à la main ci-dessous.</div>';
    return '<div class="cp-panel"><h2>Concurrents directs proposés</h2>' +
      '<div class="cp-muted" style="margin-bottom:10px">Le score /100 est calculé (taille, sujets des titres, durée, rythme). ' +
      'Il ne mesure pas le format : c\'est à toi de retirer ceux qui n\'ont pas le même format que toi.</div>' +
      '<div class="cp-comps">' + cards + '</div>' +
      '<h3>Ajouter un concurrent</h3><div class="cp-row"><input class="cp-input" id="cp-comp-url" placeholder="Lien de sa chaîne">' +
      '<button class="cp-btn" id="cp-comp-add"' + (CP.busy ? ' disabled' : '') + '>Ajouter</button></div>' +
      (CP.error && CP.analysis ? '<div class="cp-error">' + esc(CP.error) + '</div>' : '') + '</div>';
  }

  function comparisonView(r) {
    const c = r.competitors.find(x => x.profile.channel_id === CP.activeComp);
    if (!c) return '';
    const cmp = c.comparison;
    let out = '<div class="cp-panel"><h2>Toi contre ' + esc(c.profile.title) + '</h2>';

    if (cmp.main_gap) out += '<div class="cp-call loss"><b>Écart principal observé (il te dépasse)</b><br>' + esc(cmp.main_gap) + '</div>';
    if (cmp.main_advantage) out += '<div class="cp-call win"><b>Ton avantage principal observé</b><br>' + esc(cmp.main_advantage) + '</div>';
    if (!cmp.main_gap && !cmp.main_advantage) out += '<div class="cp-muted">Pas d\'écart de performance de plus de 15 % entre vous deux.</div>';
    if (c.profile.history) {
      const h = c.profile.history;
      out += '<div class="cp-muted">Depuis ' + h.days + ' j, ce concurrent a ' + (h.subs_change >= 0 ? 'gagné ' : 'perdu ') + num(Math.abs(h.subs_change)) + ' abonnés.</div>';
    }

    out += '<h3>Pourquoi il te dépasse / pourquoi tu le dépasses</h3><div class="cp-two"><div><b>Il te dépasse sur</b><ul class="cp-list">' +
      (cmp.other_ahead.length ? cmp.other_ahead.map(t => '<li>' + esc(t) + '</li>').join('') : '<li class="cp-muted">Rien de mesurable</li>') +
      '</ul></div><div><b>Tu le dépasses sur</b><ul class="cp-list">' +
      (cmp.mine_ahead.length ? cmp.mine_ahead.map(t => '<li>' + esc(t) + '</li>').join('') : '<li class="cp-muted">Rien de mesurable</li>') +
      '</ul></div></div>';

    out += '<h3>Toutes les mesures</h3><div class="table-wrap"><table><thead><tr><th>Mesure</th><th>Niveau</th><th class="num">Toi</th><th class="num">Lui</th><th>Écart</th></tr></thead><tbody>';
    let group = '';
    cmp.rows.forEach(row => {
      if (row.group !== group) { group = row.group; out += '<tr class="cp-group"><td colspan="5">' + GROUPS[group] + '</td></tr>'; }
      let verdict = '—', cls = '';
      if (row.verdict === 'other') { verdict = 'Il te dépasse' + (row.ratio ? ' (' + (row.ratio >= 1 ? row.ratio : 1 / row.ratio).toFixed(1) + '×)' : ''); cls = 'cp-verdict-other'; }
      else if (row.verdict === 'mine') { verdict = 'Tu le dépasses' + (row.ratio ? ' (' + (row.ratio >= 1 ? row.ratio : 1 / row.ratio).toFixed(1) + '×)' : ''); cls = 'cp-verdict-mine'; }
      else if (row.verdict === 'equal') verdict = '≈ égal';
      out += '<tr><td>' + esc(row.label) + '</td><td><span class="cp-tag ' + row.level + '">' + LEVELS[row.level] + '</span></td>' +
        '<td class="num">' + esc(row.mine_text) + '</td><td class="num">' + esc(row.other_text) + '</td><td class="' + cls + '">' + verdict + '</td></tr>';
    });
    out += '</tbody></table></div>';

    out += '<h3>Meilleures vidéos récentes</h3><div class="cp-vids"><div><b>Toi</b>' + videosList(cmp.best_videos.mine) +
      '</div><div><b>' + esc(c.profile.title) + '</b>' + videosList(cmp.best_videos.other) + '</div></div></div>';
    return out;
  }

  function videosList(list) {
    if (!list.length) return '<div class="cp-muted">Aucune vidéo</div>';
    return list.map(v => '<div class="cp-vid"><img loading="lazy" src="https://i.ytimg.com/vi/' + esc(v.id) + '/mqdefault.jpg" alt="">' +
      '<div><a href="https://www.youtube.com/watch?v=' + esc(v.id) + '" target="_blank" rel="noopener">' + esc(v.title) + '</a>' +
      '<div class="cp-muted">' + num(v.views) + ' vues · ' + v.duration_min + ' min</div></div></div>').join('');
  }

  function associationsView(r) {
    if (!r.associations.length) return '';
    let out = '<div class="cp-panel"><h2>Ce qui est associé à de meilleures vues <span class="cp-tag inferred">Inféré</span></h2>' +
      '<div class="cp-muted" style="margin-bottom:10px">Sur toutes les vidéos de ta chaîne et de ses concurrents, chaque vidéo est comparée à la médiane de sa propre chaîne. ' +
      'Une association n\'est pas une cause : elle indique seulement ce qui revient dans les vidéos qui marchent le mieux dans cet échantillon.</div>' +
      '<div class="table-wrap"><table><thead><tr><th>Caractéristique</th><th class="num">Avec (vidéos)</th><th class="num">Sans (vidéos)</th><th class="num">Écart</th></tr></thead><tbody>';
    r.associations.forEach(a => {
      out += '<tr><td>' + esc(a.label) + '</td><td class="num">' + a.with_ratio + '× (' + a.n_with + ')</td><td class="num">' +
        a.without_ratio + '× (' + a.n_without + ')</td><td class="num">' + (a.lift ? a.lift + '×' : 'n/d') + '</td></tr>';
    });
    return out + '</tbody></table></div></div>';
  }

  function footerView(r) {
    return '<div class="cp-muted">Recherches utilisées : ' + esc((r.queries || []).map(q => '« ' + q + ' »').join(' · ') || 'aucune') +
      ' · ' + num(r.units_used) + ' unités de quota · analyse du ' +
      esc(r.generated_at ? new Date(r.generated_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '') + '</div>';
  }

  /* ------------------------------------------------------------ liaisons */
  function bindMain() {
    const on = (id, fn) => { const el = document.getElementById(id); if (el) el.onclick = fn; };
    on('cp-logout', logout);
    on('cp-add', addChannel);
    on('cp-start', startAnalysis);
    on('cp-comp-add', addCompetitor);
    const url = document.getElementById('cp-url');
    if (url) url.onkeydown = e => { if (e.key === 'Enter') addChannel(); };
    const curl = document.getElementById('cp-comp-url');
    if (curl) curl.onkeydown = e => { if (e.key === 'Enter') addCompetitor(); };
    const hist = document.getElementById('cp-history');
    if (hist) hist.onchange = () => openAnalysis(Number(hist.value));

    root.querySelectorAll('[data-select]').forEach(el => el.onclick = () => selectChannel(el.dataset.select));
    root.querySelectorAll('[data-remove]').forEach(el => el.onclick = e => { e.stopPropagation(); removeChannel(el.dataset.remove); });
    root.querySelectorAll('[data-compare]').forEach(el => el.onclick = () => { CP.activeComp = el.dataset.compare; render(); });
    root.querySelectorAll('[data-drop]').forEach(el => el.onclick = () => removeCompetitor(el.dataset.drop));
  }
})();
