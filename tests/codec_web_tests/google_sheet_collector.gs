/**
 * @OnlyCurrentDoc
 * Collects results from the codec test page (tests/codec_web_tests/web_compatibility.html) and the chroma siting
 * check viewer (sourceimages/chroma_siting_check/view.html) into one Google Sheet, in separate tabs.
 *
 * Setup (once):
 *  1. Create a Google Sheet. Extensions > Apps Script, replace the code with this file, and save.
 *  2. Deploy > New deployment > type "Web app". Execute as: Me. Who has access: Anyone.
 *     Authorize when asked (it only needs access to this spreadsheet).
 *  3. Copy the web app URL (https://script.google.com/macros/s/.../exec) into SUBMIT_URL in build_page.py
 *     (then run build_page.py) and in sourceimages/chroma_siting_check/view.html.
 * After changing this script, use Deploy > Manage deployments > Edit > Version: New version, so the URL stays the same.
 *
 * Each codec test submission adds one row to "Submissions" (with the full JSON) and one row per movie to "Results".
 * Each chroma siting submission adds one row to "Chroma siting submissions" and one row per panel answered to
 * "Chroma siting results".
 * The header rows are written when a tab is created: after adding columns, delete or rename the old tabs.
 * The URL is public, so anyone can post to it: rows are only accepted in the page's format, with a size limit.
 * Submissions from pages older than MIN_PAGE_VERSION (MIN_CHROMA_VERSION for the viewer) are rejected: they judged
 * results differently. When a page's measurements change, raise its minimum to the new PAGE_VERSION and start fresh tabs.
 */
const MAX_BYTES = 200000;
const MIN_PAGE_VERSION = '2026-11-28l';
const MIN_CHROMA_VERSION = '2026-11-28a';
const SUBMISSION_HEADERS = ['Received', 'Submission ID', 'Page version', 'Browser', 'Browser version', 'OS',
  'OS version', 'GPU', 'Color gamut', 'Dynamic range', 'Note', 'OK', 'Wrong colors', 'Reduced chroma', 'Failed',
  'User agent', 'JSON'];
const RESULT_HEADERS = ['Received', 'Submission ID', 'Browser', 'Browser version', 'OS', 'OS version', 'GPU',
  'File', 'Codec', 'Bit depth', 'Layout', 'Codec string', 'Status', 'Max error', 'Claims supported',
  'Claims power efficient', 'canPlayType', 'Error code', 'Measured by', 'Samples', 'Decoder max error',
  'Decoder format', 'Decoder matrix', 'Decoder full range', 'Decoder note', 'Copy blue error', 'Chroma across',
  'Chroma down', 'Screen error (other movies)', 'Screen error (reference)'];
const CHROMA_SUBMISSION_HEADERS = ['Received', 'Submission ID', 'Page version', 'Browser', 'Browser version', 'OS',
  'OS version', 'GPU', 'Color gamut', 'Dynamic range', 'Device pixel ratio', 'Framebuffer', 'Rescaled', 'Note',
  'Files answered', 'Panels WRONG', 'User agent', 'JSON'];
const CHROMA_RESULT_HEADERS = ['Received', 'Submission ID', 'Browser', 'Browser version', 'OS', 'OS version', 'GPU',
  'Dynamic range', 'File', 'Label', 'Panel', 'Answer', 'Pixelated', 'Controls', 'Device pixel ratio', 'Framebuffer',
  'Rescaled', 'Answered at'];

function doPost(e) {
  const body = e && e.postData && e.postData.contents;
  if (!body || body.length > MAX_BYTES) return reply('rejected: size');
  let r;
  try { r = JSON.parse(body); } catch (err) { return reply('rejected: not JSON'); }
  if (!r || !r.environment || !r.pageVersion) return reply('rejected: format');
  if (r.kind === 'chroma_siting_check') return chromaSiting(r, body);
  if (!Array.isArray(r.results) || r.results.length > 200) return reply('rejected: format');
  if (String(r.pageVersion) < MIN_PAGE_VERSION) return reply('rejected: old page version, please reload the page');
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const subs = sheet(ss, 'Submissions', SUBMISSION_HEADERS);
    const res = sheet(ss, 'Results', RESULT_HEADERS);
    const now = new Date();
    const id = Utilities.getUuid().slice(0, 8);
    const env = r.environment;
    const count = s => r.results.filter(x => x.status === s).length;
    const okCount = count('OK'), wrong = count('Wrong colors'), reduced = count('Reduced chroma');
    subs.appendRow([now, id, str(r.pageVersion), str(env.browser), str(env.browserVersion), str(env.os),
      str(env.osVersion), str(env.gpu), str(env.colorGamut), str(env.dynamicRange), str(r.note).slice(0, 200),
      okCount, wrong, reduced, r.results.length - okCount - wrong - reduced, str(env.userAgent), body.slice(0, 49000)]);
    const num = v => typeof v === 'number' ? v : '';
    const rows = r.results.map(x => [now, id, str(env.browser), str(env.browserVersion), str(env.os),
      str(env.osVersion), str(env.gpu), str(x.file), str(x.codec), x.depth || '', str(x.layout), str(x.codecs),
      str(x.status), x.maxError === undefined ? '' : x.maxError, str(x.supported), str(x.powerEfficient),
      str(x.canPlayType), x.errorCode || '', str(x.measuredBy), x.samples ? JSON.stringify(x.samples) : '',
      num(x.decoder && x.decoder.maxError), str(x.decoder && x.decoder.format),
      str(x.decoder && x.decoder.matrix), str(x.decoder && x.decoder.fullRange),
      str(x.decoder && (x.decoder.error || x.decoder.note)), num(x.blueError), num(x.chroma && x.chroma.across),
      num(x.chroma && x.chroma.down), num(x.screen && x.screen.relError), num(x.screen && x.screen.maxError)]);
    if (rows.length) res.getRange(res.getLastRow() + 1, 1, rows.length, RESULT_HEADERS.length).setValues(rows);
  } finally {
    lock.releaseLock();
  }
  return reply('ok');
}

/* The chroma siting check viewer: one row per submission, and one per panel answered. */
function chromaSiting(r, body) {
  if (!Array.isArray(r.answers) || !r.answers.length || r.answers.length > 50) return reply('rejected: format');
  if (String(r.pageVersion) < MIN_CHROMA_VERSION) return reply('rejected: old page version, please reload the page');
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const subs = sheet(ss, 'Chroma siting submissions', CHROMA_SUBMISSION_HEADERS);
    const res = sheet(ss, 'Chroma siting results', CHROMA_RESULT_HEADERS);
    const now = new Date();
    const id = Utilities.getUuid().slice(0, 8);
    const env = r.environment, d = r.display || {};
    const num = v => typeof v === 'number' ? v : '';
    const rows = [];
    r.answers.forEach(a => {
      const v = a.viewed || {};
      (Array.isArray(a.panels) ? a.panels : []).slice(0, 2).forEach(p => {
        if (!p || !p.answer) return;
        rows.push([now, id, str(env.browser), str(env.browserVersion), str(env.os), str(env.osVersion), str(env.gpu),
          str(env.dynamicRange), str(a.file), str(a.label), str(p.panel), str(p.answer), str(v.pixelated),
          str(v.controls), num(v.dpr), str(v.framebuffer), str(v.rescaled), str(v.time)]);
      });
    });
    const wrong = rows.filter(x => x[11] === 'word').length;
    subs.appendRow([now, id, str(r.pageVersion), str(env.browser), str(env.browserVersion), str(env.os),
      str(env.osVersion), str(env.gpu), str(env.colorGamut), str(env.dynamicRange), num(d.dpr), str(d.framebuffer),
      str(d.rescaled), str(r.note).slice(0, 200), r.answers.length, wrong, str(env.userAgent), body.slice(0, 49000)]);
    if (rows.length) res.getRange(res.getLastRow() + 1, 1, rows.length, CHROMA_RESULT_HEADERS.length).setValues(rows);
  } finally {
    lock.releaseLock();
  }
  return reply('ok');
}

/* Opening the URL in a browser sends a GET: show that the collector is running and how many submissions it has. */
function doGet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const count = name => { const t = ss.getSheetByName(name); return t ? Math.max(t.getLastRow() - 1, 0) : 0; };
  return reply('Results collector is running. Submissions so far: ' + count('Submissions') + ' codec tests, ' +
    count('Chroma siting submissions') + ' chroma siting checks. Results are sent here by the test pages, with a POST.');
}

function sheet(ss, name, headers) {
  let s = ss.getSheetByName(name);
  if (!s) {
    s = ss.insertSheet(name);
    s.appendRow(headers);
    s.setFrozenRows(1);
  }
  return s;
}

/* Values are written as text, and a leading = + - @ is escaped so a submission cannot inject a formula. */
function str(v) {
  if (v === undefined || v === null) return '';
  const s = String(v).slice(0, 1000);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function reply(text) {
  return ContentService.createTextOutput(text).setMimeType(ContentService.MimeType.TEXT);
}
