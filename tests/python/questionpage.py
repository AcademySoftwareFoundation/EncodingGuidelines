"""
A self-contained HTML page of display tests, one question per test. Each test flips between two or three files
(Space), says what to look at, and maps what you see to an answer. Optional reference renders (R) show what a
player that obeys the metadata gives, and optional page-white rectangles are drawn over the video (the
browser's own SDR white, which cannot be part of the video).

Used by tests/hdr_metadata_simple.py.

    write_question_page(path, title, tests, intro_html, footer_html="")

tests: [{"title": "...", "question": "...", "look": "...", "outcomes": [["what you see", "answer"], ...],
         "note": "optional", "items": [{"src": "a.mp4", "label": "...", "ref": "refs/a.png" or None,
                                        "white": [{"x":..,"y":..,"w":..,"h":..}], "width": 1920, "height": 1080}]}]
"""
import html
import json
from pathlib import Path

from machelp import MAC_HELP

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<style>
  html, body { margin: 0; background: #111; color: #bbb; font: 14px -apple-system, Helvetica, sans-serif; height: 100%; }
  #wrap { display: flex; height: 100vh; }
  #panel { width: 380px; flex: none; overflow-y: auto; padding: 10px 14px; box-sizing: border-box;
           border-right: 1px solid #333; line-height: 1.4; }
  #panel h1 { font-size: 16px; margin: 0 0 8px; color: #ddd; }
  #panel h2 { font-size: 18px; margin: 14px 0 6px; color: #e8d670; }
  #panel h3 { font-size: 13px; margin: 12px 0 4px; color: #999; text-transform: uppercase; letter-spacing: .05em; }
  #panel p { margin: 4px 0; }
  button { background: #2a2a2a; color: #ccc; border: 1px solid #444; border-radius: 4px; padding: 4px 9px;
           font: inherit; cursor: pointer; margin: 2px 2px 2px 0; }
  button.on { background: #6a5d10; color: #fff; border-color: #a90; }
  #tests button { display: block; width: 100%; text-align: left; }
  table { border-collapse: collapse; width: 100%; }
  td { border-top: 1px solid #333; padding: 4px 4px; vertical-align: top; }
  td:last-child { color: #e8e8e8; font-weight: 600; }
  .note { color: #888; font-size: 13px; }
  kbd { background: #2a2a2a; padding: 0 4px; border-radius: 3px; border: 1px solid #444; }
  #main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  #itembar { padding: 6px 10px; display: flex; gap: 4px; align-items: center; flex-wrap: wrap; }
  #file { margin-left: 10px; color: #999; }
  #file a { color: #99f; }
  #stagewrap { flex: 1; display: flex; align-items: flex-start; justify-content: center; min-height: 0; }
  #stage { position: relative; background: #000; }
  #stage > .item { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; visibility: hidden; }
  #stage > .item.show { visibility: visible; }
  .white { position: absolute; background: #fff; }
  #cap { position: absolute; left: 8px; bottom: 8px; background: rgba(0,0,0,.65); color: #ddd; padding: 4px 10px;
         border-radius: 3px; font-size: 15px; pointer-events: none; }
  #cap.ref { color: #000; background: #e8d670; }
  body.fs #panel, body.fs #itembar { display: none; }
  .hidden { display: none !important; }
  #intro { display: none; }
  #intro.show { display: block; }
</style>
</head>
<body>
<div id="wrap">
  <div id="panel">
    <h1>__TITLE__</h1>
    <div id="tests"></div>
    <h2 id="q"></h2>
    <p id="question"></p>
    <h3>Flip</h3>
    <p><kbd>Space</kbd> switches between the files: <span id="flipnames"></span></p>
    <h3>Look at</h3>
    <p id="look"></p>
    <h3>What it means</h3>
    <table id="outcomes"></table>
    <p class="note" id="note"></p>
    <p class="note" id="refnote"><kbd>R</kbd> shows the reference: the same file rendered by libplacebo (FFmpeg),
      a player that uses all of the metadata, tone mapped to SDR Display P3. It shows what a difference looks like;
      it is not what your screen should show.</p>
    <p class="note">Keys: <kbd>1</kbd>-<kbd>9</kbd> or <kbd>&uarr;</kbd><kbd>&darr;</kbd> pick a test,
      <kbd>Space</kbd> or <kbd>&larr;</kbd><kbd>&rarr;</kbd> flip, <kbd>R</kbd> reference, <kbd>Enter</kbd> full
      screen, <kbd>H</kbd> about these tests.</p>
    <button id="bintro">About these tests</button>
    <div id="intro">__INTRO__</div>
    __FOOTER__
  </div>
  <div id="main">
    <div id="itembar"><span id="items"></span>
      <button id="bref" title="R">Reference</button>
      <button id="bfs" title="Enter">Full screen</button><span id="file"></span></div>
    <div id="stagewrap"><div id="stage"><div id="cap"></div></div></div>
  </div>
</div>
<script>
const TESTS = __TESTS__;
const LETTERS = "ABCDEFGH";
const isVideo = s => /\.(mp4|mov|m4v|webm|mkv)$/i.test(s);
const $ = id => document.getElementById(id);
const stage = $("stage");
let t = 0, i = 0, ref = false;

function media(src) {
  const el = document.createElement(isVideo(src) ? "video" : "img");
  el.src = src; el.className = "item";
  if (isVideo(src)) { el.muted = true; el.loop = true; el.playsInline = true; el.preload = "auto"; }
  stage.insertBefore(el, $("cap"));
  return el;
}
// One element per file (files can appear in several tests) and per reference.
const els = {};
const get = src => els[src] || (els[src] = media(src));
TESTS.forEach(T => T.items.forEach(it => { get(it.src); if (it.ref) get(it.ref); }));

TESTS.forEach((T, k) => {
  const b = document.createElement("button");
  b.textContent = (k + 1) + "  " + T.title;
  b.onclick = () => pick(k, 0);
  $("tests").appendChild(b);
});

function size() {
  const it = TESTS[t].items[i], w = it.width || 1920, h = it.height || 1080;
  const box = $("stagewrap").getBoundingClientRect();
  const fs = document.body.classList.contains("fs");
  const availW = fs ? window.innerWidth : box.width, availH = fs ? window.innerHeight : box.height;
  const width = Math.min(availW, availH * w / h);
  stage.style.width = width + "px"; stage.style.height = (width * h / w) + "px";
  const s = width / w;
  stage.querySelectorAll(".white").forEach(e => e.remove());
  (it.white || []).forEach(r => {
    const d = document.createElement("div");
    d.className = "white";
    Object.assign(d.style, {left: r.x * s + "px", top: r.y * s + "px", width: r.w * s + "px", height: r.h * s + "px"});
    stage.insertBefore(d, $("cap"));
  });
}

function pick(k, n) {
  t = (k + TESTS.length) % TESTS.length;
  const T = TESTS[t];
  i = (n + T.items.length) % T.items.length;
  const it = T.items[i];
  if (ref && !it.ref) ref = false;
  const src = ref ? it.ref : it.src;
  Object.entries(els).forEach(([s, el]) => {
    const on = s === src;
    el.classList.toggle("show", on);
    if (el.tagName === "VIDEO") { if (on) el.play().catch(() => {}); else el.pause(); }
  });
  [...$("tests").children].forEach((b, j) => b.classList.toggle("on", j === t));
  $("q").textContent = (t + 1) + ". " + T.title;
  $("question").innerHTML = T.question;
  $("look").innerHTML = T.look;
  $("note").innerHTML = T.note || "";
  $("outcomes").innerHTML = T.outcomes.map(o => "<tr><td>" + o[0] + "</td><td>" + o[1] + "</td></tr>").join("");
  $("flipnames").textContent = T.items.map((x, j) => LETTERS[j] + " " + x.label).join(", ");
  const items = $("items");
  items.innerHTML = "";
  T.items.forEach((x, j) => {
    const b = document.createElement("button");
    b.textContent = LETTERS[j] + "  " + x.label;
    b.className = j === i ? "on" : "";
    b.onclick = () => pick(t, j);
    items.appendChild(b);
  });
  const anyRef = T.items.some(x => x.ref);
  $("bref").classList.toggle("hidden", !anyRef);
  $("refnote").classList.toggle("hidden", !anyRef);
  $("bref").classList.toggle("on", ref);
  $("cap").textContent = (t + 1) + LETTERS[i] + "  " + it.label + (ref ? "   REFERENCE (libplacebo, SDR)" : "");
  $("cap").classList.toggle("ref", ref);
  const name = src.split("/").pop();
  $("file").innerHTML = 'File: <a href="' + src + '" download="' + name + '">' + name + ' &#x2913;</a>';
  size();
}

$("bref").onclick = () => { ref = !ref; pick(t, i); };
$("bfs").onclick = () => document.fullscreenElement ? document.exitFullscreen()
                                                    : document.documentElement.requestFullscreen();
$("bintro").onclick = () => $("intro").classList.toggle("show");
document.addEventListener("fullscreenchange", () => {
  document.body.classList.toggle("fs", !!document.fullscreenElement); size();
});
window.addEventListener("resize", size);
document.addEventListener("keydown", e => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (/^[1-9]$/.test(k) && +k <= TESTS.length) pick(+k - 1, 0);
  else if (k === "arrowdown") pick(t + 1, 0);
  else if (k === "arrowup") pick(t - 1, 0);
  else if (k === " " || k === "arrowright") pick(t, i + 1);
  else if (k === "arrowleft") pick(t, i - 1);
  else if (k === "r") $("bref").click();
  else if (k === "h") $("bintro").click();
  else if (k === "enter") $("bfs").click();
  else return;
  e.preventDefault();
});
pick(0, 0);
</script>
</body>
</html>
"""


def write_question_page(path, title, tests, intro_html, footer_html=""):
    page = (PAGE.replace("</body>", MAC_HELP + "</body>").replace("__TITLE__", html.escape(title))
            .replace("__INTRO__", intro_html)
            .replace("__FOOTER__", footer_html)
            .replace("__TESTS__", json.dumps(tests, indent=1)))
    Path(path).write_text(page)
