// Bible Translate: collect a speaker's word list and sample verses, review AI drafts, export approved chapters.
// Everything is kept in this browser (localStorage) and in the downloadable project file.
(() => {
  'use strict';
  const KEY = 'bibletranslate-project-v1';
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  // ---------- Project state ----------
  const blank = () => ({
    format: 'bibletranslate-project', version: 1,
    language: { name: '', code: '', script: '', dir: 'ltr', region: '', related: '', notes: '' },
    wordlist: [], samples: [], drafts: [], reviewer: '',
  });
  let P = blank();
  try { P = Object.assign(blank(), JSON.parse(localStorage.getItem(KEY)) || {}); } catch (e) { /* start fresh */ }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(P)); }
    catch (e) { toast('Could not save in this browser. Download the project file to keep your work.'); }
  }

  let toastTimer;
  function toast(msg) {
    const t = $('#toast');
    t.textContent = msg; t.classList.add('show');
    clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('show'), 2600);
  }

  function download(name, data) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: name });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  const slug = (s) => String(s || 'language').toLowerCase().replace(/\W+/g, '-').replace(/^-|-$/g, '') || 'language';
  const targetAttrs = () => `lang="${esc(P.language.code || 'und')}" dir="${P.language.dir === 'rtl' ? 'rtl' : 'ltr'}"`;

  // ---------- KJV and references ----------
  let KJV = null;   // [[bookName, [[verse, ...], ...]], ...]
  async function kjv() {
    if (!KJV) KJV = await (await fetch('data/kjv.json')).json();
    return KJV;
  }
  const clean = (t) => String(t || '').replace(/¶\s*/g, '').trim();
  const refName = (b, c, v) => `${KJV ? KJV[b][0] : 'Book ' + b} ${c}:${v}`;

  // "Mark 1:4" -> {b, c, v} in KJV numbering, or an error message.
  function parseRef(text) {
    const m = String(text).trim().match(/^(.+?)\s+(\d+)\s*[:.]\s*(\d+)$/);
    if (!m) return { error: 'Use the form "Mark 1:4".' };
    const key = m[1].toLowerCase().replace(/\s+/g, ' ');
    const names = KJV.map((b) => b[0].toLowerCase());
    let hits = names.flatMap((n, i) => (n === key ? [i] : []));
    if (!hits.length) hits = names.flatMap((n, i) => (n.startsWith(key) ? [i] : []));
    if (hits.length !== 1) return { error: `Unknown book "${m[1]}".` };
    const b = hits[0], c = +m[2], v = +m[3];
    const chs = KJV[b][1];
    if (c < 1 || c > chs.length) return { error: `${KJV[b][0]} has ${chs.length} chapters.` };
    if (v < 1 || v > chs[c - 1].length) return { error: `${KJV[b][0]} ${c} has ${chs[c - 1].length} verses.` };
    return { b, c, v };
  }
  function nextRef(b, c, v) {
    const chs = KJV[b][1];
    if (v < chs[c - 1].length) return { b, c, v: v + 1 };
    if (c < chs.length) return { b, c: c + 1, v: 1 };
    if (b < KJV.length - 1) return { b: b + 1, c: 1, v: 1 };
    return null;
  }

  // ---------- Tabs ----------
  function showTab(name) {
    $$('.tabs button').forEach((t) => t.setAttribute('aria-selected', String(t.dataset.tab === name)));
    $$('.tab').forEach((s) => { s.hidden = s.id !== 'tab-' + name; });
    if (name === 'needs') renderNeeds().catch(() => toast('Could not load the language list'));
    try { sessionStorage.setItem('bt-tab', name); } catch (e) { /* ignore */ }
  }
  $('.tabs').addEventListener('click', (e) => e.target.dataset.tab && showTab(e.target.dataset.tab));

  // ---------- Language ----------
  function renderLanguage() {
    const f = $('#lang-form');
    for (const [k, v] of Object.entries(P.language)) if (f.elements[k]) f.elements[k].value = v || '';
    $('#lang-label').textContent = P.language.name ? '· ' + P.language.name : '';
    $$('.target').forEach((el) => { el.lang = P.language.code || 'und'; el.dir = P.language.dir === 'rtl' ? 'rtl' : 'ltr'; });
  }
  $('#lang-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const f = e.target;
    for (const k of Object.keys(P.language)) if (f.elements[k]) P.language[k] = f.elements[k].value.trim();
    save(); renderLanguage(); toast('Saved');
  });

  // ---------- Word list ----------
  function renderWords() {
    const words = [...P.wordlist].sort((a, b) => a.en.localeCompare(b.en));
    $('#word-list').innerHTML = words.map((w) => `<tr>
      <td>${esc(w.en)}</td><td ${targetAttrs()}>${esc(w.word)}</td><td class="muted">${esc(w.notes)}</td>
      <td><button class="link" data-del-word="${esc(w.en)}" aria-label="Remove ${esc(w.en)}">Remove</button></td></tr>`).join('');
    $('#word-empty').hidden = words.length > 0;
  }
  $('#word-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const f = e.target;
    const w = { en: f.elements.en.value.trim(), word: f.elements.word.value.trim(), notes: f.elements.notes.value.trim() };
    if (!w.en || !w.word) return;
    P.wordlist = P.wordlist.filter((x) => x.en.toLowerCase() !== w.en.toLowerCase()).concat(w);
    save(); renderWords(); f.reset(); f.elements.en.focus();
  });
  $('#word-list').addEventListener('click', (e) => {
    const en = e.target.dataset.delWord;
    if (en === undefined) return;
    P.wordlist = P.wordlist.filter((x) => x.en !== en);
    save(); renderWords();
  });

  // ---------- Sample verses ----------
  let current = null;   // {b, c, v} shown in the sample form
  const sampleKey = (s) => `${s.b}:${s.c}:${s.v}`;
  function showSampleRef(r) {
    current = r;
    $('#ref-form').elements.ref.value = refName(r.b, r.c, r.v);
    $('#ref-kjv').innerHTML = `<span class="ref">KJV</span>${esc(clean(KJV[r.b][1][r.c - 1][r.v - 1]))}`;
    const f = $('#sample-form');
    const have = P.samples.find((s) => sampleKey(s) === sampleKey(r));
    f.hidden = false;
    f.elements.text.value = have ? have.text : '';
    f.elements.by.value = have ? have.by || '' : f.elements.by.value || P.lastSpeaker || '';
    f.elements.text.focus();
  }
  $('#ref-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    await kjv();
    const r = parseRef(e.target.elements.ref.value);
    if (r.error) return toast(r.error);
    showSampleRef(r);
  });
  $('#ref-next').addEventListener('click', async () => {
    await kjv();
    const from = current || parseRef($('#ref-form').elements.ref.value);
    const n = from.error ? null : nextRef(from.b, from.c, from.v);
    if (n) showSampleRef(n);
  });
  $('#sample-form').addEventListener('submit', (e) => {
    e.preventDefault();
    if (!current) return;
    const f = e.target;
    const s = { ...current, text: f.elements.text.value.trim(), by: f.elements.by.value.trim(), source: 'speaker' };
    if (!s.text) return;
    P.samples = P.samples.filter((x) => sampleKey(x) !== sampleKey(s)).concat(s);
    P.lastSpeaker = s.by;
    save(); renderSamples(); toast('Saved ' + refName(s.b, s.c, s.v));
    const n = nextRef(s.b, s.c, s.v);
    if (n) showSampleRef(n);
  });
  function renderSamples() {
    const list = [...P.samples].sort((a, b) => a.b - b.b || a.c - b.c || a.v - b.v);
    $('#sample-list').innerHTML = list.map((s) => `<li>
      <span class="ref">${esc(refName(s.b, s.c, s.v))}</span>${s.by ? `<span class="muted">· ${esc(s.by)}</span>` : ''}
      <span class="target" ${targetAttrs()}>${esc(s.text)}</span>
      <span class="actions"><button class="link" data-edit="${sampleKey(s)}">Edit</button><button class="link" data-del="${sampleKey(s)}">Remove</button></span></li>`).join('');
    $('#sample-empty').hidden = list.length > 0;
    $('#sample-count').textContent = list.length ? `(${list.length})` : '';
  }
  $('#sample-list').addEventListener('click', async (e) => {
    const { edit, del } = e.target.dataset;
    if (del) { P.samples = P.samples.filter((s) => sampleKey(s) !== del); save(); renderSamples(); }
    if (edit) { await kjv(); const [b, c, v] = edit.split(':').map(Number); showSampleRef({ b, c, v }); window.scrollTo(0, 0); }
  });

  // ---------- Review drafts ----------
  // Draft files come from tools/draft.py: {passage, target_language, model, notice, verses: [{book, chapter, verse,
  // kjv, translation, back_translation, confidence, notes, expected?, score?, review: {...}}]}.
  const draftId = (d) => `${d.passage}|${d.created}`;
  function addDrafts(list) {
    let added = 0;
    for (const d of list) {
      if (!d || !Array.isArray(d.verses) || !d.passage) continue;
      P.drafts = P.drafts.filter((x) => draftId(x) !== draftId(d)).concat(d);
      added++;
    }
    save(); renderDrafts();
    toast(added ? `Opened ${added} draft${added > 1 ? 's' : ''}` : 'That file is not a draft from tools/draft.py');
  }
  $('#draft-files').addEventListener('change', async (e) => {
    const out = [];
    for (const file of e.target.files) {
      try { out.push(JSON.parse(await file.text())); } catch (err) { toast(`Could not read ${file.name}`); }
    }
    e.target.value = '';
    addDrafts(out);
  });
  $('#reviewer').addEventListener('change', (e) => { P.reviewer = e.target.value.trim(); save(); });

  function verseHTML(d, di, v, vi) {
    const r = v.review || {};
    const status = r.status || 'pending';
    const text = r.approved_text ?? v.translation;
    return `<div class="verse ${status}" data-d="${di}" data-v="${vi}">
      <div><span class="ref">${esc(v.ref || `${d.passage.replace(/:.*$/, '')}:${v.verse}`)}</span>
        <span class="chip ${esc(v.confidence)}">${esc(v.confidence)} confidence</span>
        <span class="chip st ${status}">${status === 'approved' ? (confirmed(v) ? 'confirmed' : `approved by ${independent(v).length} of ${CONFIRM}`) : status.replace('-', ' ')}</span>
        ${approvals(v).length ? `<span class="muted small">${approvals(v).map((a) => esc(a.reviewer)).join(', ')}</span>` : ''}
        ${r.edited_by ? `<span class="muted small">wording by ${esc(r.edited_by)}</span>` : ''}
        ${v.score != null ? `<span class="chip">match ${Math.round(v.score)}</span>` : ''}
        ${v.meaning_score != null ? `<span class="chip ${v.meaning_score >= 90 ? 'high' : v.meaning_score >= 70 ? 'medium' : 'low'}">meaning ${v.meaning_score}</span>` : ''}</div>
      <p class="kjv">${esc(v.kjv)}</p>
      <textarea class="target" rows="2" data-field="text" ${targetAttrs()}>${esc(text)}</textarea>
      <p class="bt"><b>Back-translation</b> ${esc(v.back_translation)}</p>
      ${v.independent_back_translation ? `<p class="bt"><b>Independent back-translation</b> ${esc(v.independent_back_translation)}${v.meaning_match != null ? ` <span class="muted small">(${v.meaning_match}% of the verse's key words${v.meaning_score != null ? `; meaning kept ${v.meaning_score} of 100` : ''})</span>` : ''}</p>` : ''}
      ${(v.meaning_missing || []).length || (v.meaning_changed || []).length ? `<p class="muted small">${[...(v.meaning_missing || []).map((m) => `Missing: ${esc(m)}`), ...(v.meaning_changed || []).map((m) => `Changed: ${esc(m)}`)].join(' · ')}</p>` : ''}
      ${(v.checks || []).length ? `<ul class="checks">${v.checks.map((c) => `<li>${esc(c)}</li>`).join('')}</ul>` : ''}
      ${v.expected ? `<p class="expected"><b>Speaker's own translation</b> <span ${targetAttrs()}>${esc(v.expected)}</span></p>` : ''}
      ${(v.notes || []).length ? `<ul class="notes">${v.notes.map((n) => `<li>${esc(n)}</li>`).join('')}</ul>` : ''}
      <div class="controls">
        <button class="primary" data-act="approved">Approve</button>
        <button class="secondary" data-act="needs-work">Needs work</button>
        <input data-field="comments" placeholder="Comment for the team" value="${esc(r.comments || '')}">
      </div></div>`;
  }
  function renderDrafts() {
    $('#reviewer').value = P.reviewer || '';
    $('#drafts').innerHTML = P.drafts.map((d, di) => {
      const done = d.verses.filter((v) => v.review && v.review.status !== 'pending').length;
      return `<section class="draft">
        <div class="draft-head"><h2>${esc(d.passage)}</h2>
          <span class="muted">${done} of ${d.verses.length} reviewed · ${esc(d.model || '')}${d.test ? ' · test run' : ''}</span>
          <button class="link" data-dl="${di}">Download reviewed file</button>
          <button class="link" data-close="${di}">Close</button></div>
        <p class="notice">${esc(d.notice || 'AI draft. Needs review by speakers of the language.')}</p>
        ${d.test ? `<p class="muted">Test run: the AI translated verses a speaker already translated, without seeing them. Average match ${Math.round(d.test.average_score)} out of 100 (chrF).</p>` : ''}
        ${d.meaning ? `<p class="muted">Meaning kept: ${Math.round(d.meaning.average_score)} out of 100 on average, graded by a separate AI from the independent back-translation. It points reviewers at verses to check; it is not a speaker's judgement.</p>` : ''}
        ${d.verses.map((v, vi) => verseHTML(d, di, v, vi)).join('')}</section>`;
    }).join('');
    $('#drafts-empty').hidden = P.drafts.length > 0;
  }
  function setReview(di, vi, patch) {
    const v = P.drafts[di].verses[vi];
    v.review = Object.assign({ status: 'pending', reviewer: null, approved_text: null, comments: null }, v.review, patch);
    save();
  }
  // Like Wikipedia, anyone can edit, but a verse is only confirmed once two different speakers approve
  // the same wording. Changing the wording clears earlier approvals.
  const CONFIRM = 2;
  // The person who wrote the current wording can approve it, but two OTHER speakers must confirm it
  // (Fluent keeps drafter and checker separate for the same reason).
  const approvals = (v) => (v.review && v.review.approvals) || [];
  const independent = (v) => approvals(v).filter((a) => a.reviewer !== (v.review && v.review.edited_by));
  const confirmed = (v) => v.review && v.review.status === 'approved' && independent(v).length >= CONFIRM;
  const logEvent = (v, action, extra) => {
    v.review.history = (v.review.history || []).concat({ at: new Date().toISOString(), who: P.reviewer || null, action, ...extra });
  };
  $('#drafts').addEventListener('click', (e) => {
    const t = e.target;
    if (t.dataset.dl) {
      const d = P.drafts[+t.dataset.dl];
      return download(`${slug(d.target_language)}-${slug(d.passage)}-reviewed.json`, d);
    }
    if (t.dataset.close) {
      if (!confirm('Close this draft? Download it first to keep your review.')) return;
      P.drafts.splice(+t.dataset.close, 1); save(); return renderDrafts();
    }
    const act = t.dataset.act;
    const box = t.closest('.verse');
    if (!act || !box) return;
    const di = +box.dataset.d, vi = +box.dataset.v;
    const v = P.drafts[di].verses[vi];
    const text = $('[data-field="text"]', box).value.trim();
    const who = ($('#reviewer').value || '').trim();
    if (!who) { toast('Enter your name as reviewer first'); $('#reviewer').focus(); return; }
    P.reviewer = who;
    const comment = $('[data-field="comments"]', box).value.trim();
    if (act === 'needs-work' && !comment) { toast('Say what needs work in the comment box'); $('[data-field="comments"]', box).focus(); return; }
    const before = (v.review && v.review.approved_text) ?? v.translation;
    let list = text === before ? approvals(v) : [];
    if (act === 'approved') list = list.filter((a) => a.reviewer !== who).concat({ reviewer: who, at: new Date().toISOString() });
    else list = list.filter((a) => a.reviewer !== who);
    setReview(di, vi, { status: list.length ? 'approved' : act, reviewer: who, approved_text: text, approvals: list,
      comments: comment || null });
    logEvent(v, act === 'approved' ? 'approved' : 'needs work', { text, comment: comment || undefined });
    save();
    box.outerHTML = verseHTML(P.drafts[di], di, P.drafts[di].verses[vi], vi);
    const head = $$('.draft')[di];
    const d = P.drafts[di];
    $('.draft-head .muted', head).textContent = `${d.verses.filter((v) => v.review && v.review.status !== 'pending').length} of ${d.verses.length} reviewed · ${d.model || ''}${d.test ? ' · test run' : ''}`;
  });
  $('#drafts').addEventListener('change', (e) => {
    const box = e.target.closest('.verse');
    if (!box) return;
    const field = e.target.dataset.field;
    if (field === 'text') {
      const v = P.drafts[+box.dataset.d].verses[+box.dataset.v];
      setReview(+box.dataset.d, +box.dataset.v, { approved_text: e.target.value.trim(), approvals: [], status: 'pending',
        edited_by: ($('#reviewer').value || '').trim() || null });
      logEvent(v, 'edited', { text: e.target.value.trim() });
      save();
      // Update in place: re-rendering here would swallow a click on Approve that caused this change.
      const st = $('.chip.st', box);
      st.className = 'chip st pending'; st.textContent = 'edited, needs approval';
      box.classList.remove('approved', 'needs-work');
    }
    if (field === 'comments') setReview(+box.dataset.d, +box.dataset.v, { comments: e.target.value.trim() || null });
  });

  // ---------- Approved verses ----------
  // Approved draft verses plus speaker samples, keyed "b:c:v". A speaker's own translation wins.
  function approvedVerses(onlyConfirmed) {
    const out = new Map();
    for (const d of P.drafts) {
      if (d.test) continue;   // test runs re-translate sample verses; the speaker's version stands
      for (const v of d.verses) {
        if (v.book != null && (onlyConfirmed ? confirmed(v) : v.review && v.review.status === 'approved')) {
          out.set(`${v.book}:${v.chapter}:${v.verse}`, (v.review.approved_text || v.translation).trim());
        }
      }
    }
    for (const s of P.samples) out.set(sampleKey(s), s.text.trim());
    return out;
  }

  // ---------- Export ----------
  $('#export-project').addEventListener('click', () => {
    const sure = approvedVerses(true);
    const data = { ...P, exported: new Date().toISOString(), approved: [...approvedVerses()].map(([k, text]) => {
      const [b, c, v] = k.split(':').map(Number);
      return { b, c, v, text, confirmed: sure.get(k) === text };
    }) };
    download(`${slug(P.language.name)}-project.json`, data);
  });
  $('#import-project').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    e.target.value = '';
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      if (data.format !== 'bibletranslate-project') throw new Error('not a project');
      if ((P.samples.length || P.drafts.length) && !confirm('Replace the project in this browser with this file?')) return;
      delete data.approved; delete data.exported;
      P = Object.assign(blank(), data);
      save(); renderAll(); toast('Project opened');
    } catch (err) { toast('That file is not a Bible Translate project file'); }
  });

  // BibleApp text format: {"books": {"<KJV book index>": [[verse, ...] per chapter]}}. Positions matter, so
  // only whole chapters go in; a book's missing chapters before the last approved one would shift numbering,
  // so books are cut at the first chapter that is not fully approved.
  $('#export-bibleapp').addEventListener('click', async () => {
    await kjv();
    const ok = approvedVerses(true);
    const books = {};
    let chapters = 0, partial = 0, waiting = 0;
    for (let b = 0; b < KJV.length; b++) {
      const chs = [];
      let gap = false;
      for (let c = 1; c <= KJV[b][1].length; c++) {
        const n = KJV[b][1][c - 1].length;
        const verses = Array.from({ length: n }, (_, i) => ok.get(`${b}:${c}:${i + 1}`));
        const have = verses.filter(Boolean).length;
        if (have === n && !gap) chs.push(verses);
        else if (have === n) waiting++;          // complete, but an earlier chapter of the book isn't
        else { gap = true; if (have) partial++; }
      }
      if (chs.length) { books[b] = chs; chapters += chs.length; }
    }
    const plural = (n, word) => `${n} ${word}${n > 1 ? 's' : ''}`;
    const left = [partial && `${plural(partial, 'partly approved chapter')} left out`,
      waiting && `${plural(waiting, 'complete chapter')} held back until the chapters before it in its book are approved`]
      .filter(Boolean).join('; ');
    const sum = $('#export-summary');
    if (!chapters) {
      sum.textContent = `Nothing to export yet${left ? ': ' + left : ''}. A book is included from chapter 1 up to its first chapter that is not fully approved.`;
      return;
    }
    download(`${P.language.code || slug(P.language.name)}-draft.json`, {
      books,
      notice: 'Approved by reviewers in Bible Translate. Check with the language community before publishing.',
      language: P.language,
    });
    sum.textContent = `Exported ${plural(chapters, 'chapter')}${left ? '; ' + left : ''}.`;
  });

  $('#reset').addEventListener('click', () => {
    if (!confirm('Clear this project from this browser? This cannot be undone.')) return;
    P = blank(); save(); renderAll();
  });

  // ---------- Languages still needing a Bible ----------
  let NEEDS = null;
  async function loadNeeds() {
    if (!NEEDS) NEEDS = await (await fetch('data/languages-needing.json')).json();
    return NEEDS;
  }
  async function renderNeeds() {
    const data = await loadNeeds();
    // Joshua Project's terms ask for this exact credit, linked.
    $('#needs-attrib').innerHTML = `<a href="https://joshuaproject.net" target="_blank" rel="noopener">Data provided by Joshua Project</a>. ` +
      `Families from <a href="https://glottolog.org" target="_blank" rel="noopener">Glottolog</a> (CC BY 4.0); Bibles listed from ` +
      `<a href="https://ebible.org" target="_blank" rel="noopener">eBible.org</a>. List built ${esc(data.built)}.`;
    const q = $('#needs-search').value.trim().toLowerCase();
    const status = $('#needs-status').value;
    const rec = $('#needs-rec').checked;
    const rows = data.languages.filter((l) => (!status || l.status === status) && (!rec || l.recordings) &&
      (!q || [l.name, l.code, l.country, l.family, l.group].some((v) => v && v.toLowerCase().includes(q))));
    $('#needs-count').textContent = `${rows.length} languages`;
    $('#needs-list').innerHTML = rows.slice(0, 300).map((l) => `<tr>
      <td>${esc(l.name)}<span class="code">${esc(l.code)}</span></td>
      <td>${esc(l.country)}</td>
      <td>${esc(l.family || '')}${l.group && l.group !== l.family ? ` · ${esc(l.group)}` : ''}</td>
      <td>${l.recordings ? `<a href="${esc(l.recordings)}" target="_blank" rel="noopener">Listen</a>` : ''}</td>
      <td>${(l.relatives_with_bible || []).map((r) => `${esc(r.name)} <span class="code">${esc(r.bible)}</span>`).join(', ')}</td>
      <td><button class="link" data-start="${esc(l.code)}">Start</button></td></tr>`).join('');
    if (rows.length > 300) $('#needs-count').textContent += ' (showing the first 300; search to narrow)';
  }
  // 'input' only for the search box: its 'change' fires on blur and the re-render would swallow a click on Start.
  $('#needs-search').addEventListener('input', renderNeeds);
  ['#needs-status', '#needs-rec'].forEach((s) => $(s).addEventListener('change', renderNeeds));
  $('#needs-list').addEventListener('click', (e) => {
    const code = e.target.dataset.start;
    if (!code) return;
    const l = NEEDS.languages.find((x) => x.code === code);
    if (P.language.name && P.language.code !== code &&
        !confirm(`This browser already has a project for ${P.language.name}. Download its project file first. Replace it with ${l.name}?`)) return;
    if (P.language.code !== code) P = blank();
    const rel = (l.relatives_with_bible || [])[0];
    Object.assign(P.language, {
      name: l.name, code: l.code, region: l.country,
      related: rel ? `${rel.name} (${rel.code}), same ${rel.shared_group} group` : P.language.related,
    });
    save(); renderAll(); showTab('language'); toast(`Started a project for ${l.name}`);
  });

  // ---------- Start ----------
  function renderAll() { renderLanguage(); renderWords(); renderSamples(); renderDrafts(); }
  renderAll();
  let tab = 'language';
  try { tab = sessionStorage.getItem('bt-tab') || (P.language.name ? 'samples' : 'needs'); } catch (e) { /* ignore */ }
  showTab(tab);
  kjv().then(renderSamples).catch(() => toast('Could not load the KJV text'));
})();
