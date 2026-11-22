"""
A self-contained HTML page for comparing test patterns on a display: flip between full-screen images or videos
(instant, as every file is loaded and stacked), or show them side by side.

Used by tests/hdr_metadata_display_chart.py and gamuttests/make_gamut_tag_test.py.

    write_flipbook(path, title, items, intro_html, strips=None, overlay=None, mode="flip")

items:   [{"src": "01-none.mp4", "label": "01 no metadata"}, ...]  (".mp4"/".mov"/".webm" are videos, others images)
strips:  the same, for the side-by-side view (e.g. narrow versions of each item); default: the items themselves.
mode:    the view it opens in: "flip" or "grid" (side by side).
overlay: an optional SDR white rectangle drawn over the flip view, in source pixels:
         {"x": 140, "y": 800, "w": 100, "h": 140, "width": 1920, "height": 1080, "label": "SDR white"}
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
  html, body { margin: 0; background: #111; color: #bbb; font: 14px -apple-system, Helvetica, sans-serif; }
  #bar { display: flex; gap: 6px; align-items: center; padding: 6px 10px; flex-wrap: wrap; }
  #bar h1 { font-size: 15px; margin: 0 12px 0 0; color: #ddd; }
  button { background: #2a2a2a; color: #ccc; border: 1px solid #444; border-radius: 4px; padding: 4px 9px;
           font: inherit; cursor: pointer; }
  button.on { background: #6a5d10; color: #fff; border-color: #a90; }
  #picker { display: flex; gap: 4px; flex-wrap: wrap; padding: 4px 10px; align-items: center; }
  #file { margin-left: 10px; color: #999; }
  a { color: #99f; }
  #grid .dl { font-size: 11px; }
  #stage { position: relative; margin: 0 auto; background: #000; }
  #stage > .item { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; visibility: hidden; }
  #stage > .item.show { visibility: visible; }
  #cap { position: absolute; left: 8px; bottom: 8px; background: rgba(0,0,0,.6); color: #ddd; padding: 3px 8px;
         border-radius: 3px; font-size: 13px; pointer-events: none; }
  #sdrwhite { position: absolute; background: #fff; display: none; }
  #sdrwhite.show { display: block; }
  #grid { display: none; gap: 6px; padding: 6px 10px; overflow-x: auto; align-items: flex-start; }
  #grid figure { margin: 0; display: flex; flex-direction: column; align-items: center; flex: 1 1 0; min-width: 0; }
  #grid figcaption { font-size: 12px; padding: 2px 0 4px; white-space: nowrap; overflow: hidden; max-width: 100%; }
  #grid .strip { width: 100%; height: auto; max-height: calc(100vh - 110px); object-fit: contain; }
  #grid.tiles { display: none; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); }
  #grid.tiles .strip { height: auto; width: 100%; }
  #help { display: none; max-width: 1100px; margin: 10px auto; padding: 10px 20px; background: #1c1c1c;
          border: 1px solid #333; line-height: 1.45; }
  #help.show { display: block; }
  #help code, #help kbd { background: #2a2a2a; padding: 0 4px; border-radius: 3px; }
  .hidden { display: none !important; }
  body.fs #bar, body.fs #picker { display: none; }
</style>
</head>
<body>
<div id="bar">
  <h1>__TITLE__</h1>
  <button id="bflip" class="on" title="F">Flip</button>
  <button id="bgrid" title="S">Side by side</button>
  <button id="blabels" class="on" title="L">Labels</button>
  <button id="bwhite" title="W">SDR white</button>
  <button id="bfs" title="Enter">Full screen</button>
  <button id="bhelp" title="H">Help</button>
  <span id="keys" style="margin-left:10px;color:#777">Keys: 1-9 0 Q E R T Y U I O P pick, &larr; &rarr; cycle, Space back to the
    previous, S side by side, F flip, W SDR white, L labels, Enter full screen, H help</span>
</div>
<div id="help">__INTRO__</div>
<div id="flipview">
  <div id="picker"></div><div style="padding:0 10px 4px" id="file"></div>
  <div id="stage"><div id="sdrwhite"></div><div id="cap"></div></div>
</div>
<div id="grid"></div>
<script>
const ITEMS = __ITEMS__;
const STRIPS = __STRIPS__;
const OVERLAY = __OVERLAY__;
const KEYS = "1234567890qertyuiop";  // no w, s, f, l, h: those are commands
const isVideo = s => /\.(mp4|mov|m4v|webm|mkv)$/i.test(s);
const $ = id => document.getElementById(id);
let cur = 0, prev = 0, mode = "flip";

function link(src) {
  const name = src.split("/").pop();
  return 'File: <a href="' + src + '" download="' + name + '">' + src + ' &#x2913;</a>';
}

function media(src, cls) {
  const el = document.createElement(isVideo(src) ? "video" : "img");
  el.src = src; el.className = cls;
  if (isVideo(src)) { el.muted = true; el.loop = true; el.playsInline = true; el.preload = "auto"; }
  return el;
}

const stage = $("stage"), picker = $("picker");
const els = ITEMS.map((it, i) => {
  const el = media(it.src, "item");
  stage.insertBefore(el, $("sdrwhite"));
  const b = document.createElement("button");
  b.textContent = (KEYS[i] || "") + "  " + it.label;
  b.onclick = () => show(i);
  picker.appendChild(b);
  return el;
});

function size() {
  const w = OVERLAY ? OVERLAY.width : 16, h = OVERLAY ? OVERLAY.height : 9;
  const top = stage.getBoundingClientRect().top + window.scrollY;
  const avail = Math.max(200, window.innerHeight - (document.body.classList.contains("fs") ? 0 : top) - 4);
  const width = Math.min(window.innerWidth, avail * w / h);
  stage.style.width = width + "px"; stage.style.height = (width * h / w) + "px";
  if (OVERLAY) {
    const o = $("sdrwhite").style, s = width / OVERLAY.width;
    o.left = OVERLAY.x * s + "px"; o.top = OVERLAY.y * s + "px";
    o.width = OVERLAY.w * s + "px"; o.height = OVERLAY.h * s + "px";
  }
}

function show(i) {
  if (i < 0 || i >= ITEMS.length) return;
  if (i !== cur) prev = cur;
  cur = i;
  els.forEach((el, k) => {
    el.classList.toggle("show", k === i);
    if (el.tagName === "VIDEO") { if (k === i && mode === "flip") el.play().catch(() => {}); else el.pause(); }
  });
  [...picker.children].forEach((b, k) => b.classList.toggle("on", k === i));
  $("cap").textContent = ITEMS[i].label;
  $("file").innerHTML = link(ITEMS[i].src);
}

const grid = $("grid");
const strips = (STRIPS || ITEMS).map(it => {
  const fig = document.createElement("figure");
  const cap = document.createElement("figcaption");
  const cb = document.createElement("input");
  cb.type = "checkbox"; cb.checked = true;
  const el = media(it.src, "strip");
  cb.onchange = () => { el.classList.toggle("hidden", !cb.checked); };
  cap.appendChild(cb); cap.appendChild(document.createTextNode(" " + it.label));
  const dl = document.createElement("div");
  dl.className = "dl"; dl.innerHTML = link(it.src).replace("File: ", "");
  fig.appendChild(cap); fig.appendChild(el); fig.appendChild(dl); grid.appendChild(fig);
  return el;
});
if (!STRIPS) grid.classList.add("tiles");

function setMode(m) {
  mode = m;
  $("flipview").classList.toggle("hidden", m !== "flip");
  grid.style.display = m === "grid" ? (STRIPS ? "flex" : "grid") : "none";
  $("bflip").classList.toggle("on", m === "flip"); $("bgrid").classList.toggle("on", m === "grid");
  strips.forEach(el => { if (el.tagName === "VIDEO") { if (m === "grid") el.play().catch(() => {}); else el.pause(); } });
  show(cur); size();
}

function toggle(id, cls, target, invert) {
  const on = target.classList.toggle(cls); $(id).classList.toggle("on", invert ? !on : on);
}
$("bflip").onclick = () => setMode("flip");
$("bgrid").onclick = () => setMode("grid");
$("blabels").onclick = () => toggle("blabels", "hidden", $("cap"), true);
$("bwhite").onclick = () => toggle("bwhite", "show", $("sdrwhite"));
$("bhelp").onclick = () => { toggle("bhelp", "show", $("help")); size(); };
$("bfs").onclick = () => document.fullscreenElement ? document.exitFullscreen()
                                                    : document.documentElement.requestFullscreen();
if (!OVERLAY) $("bwhite").classList.add("hidden");
document.addEventListener("fullscreenchange", () => {
  document.body.classList.toggle("fs", !!document.fullscreenElement); size();
});
window.addEventListener("resize", size);
document.addEventListener("keydown", e => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key.toLowerCase(), n = KEYS.indexOf(k);
  if (n >= 0 && n < ITEMS.length) { if (mode !== "flip") setMode("flip"); show(n); }
  else if (k === "arrowright") show((cur + 1) % ITEMS.length);
  else if (k === "arrowleft") show((cur + ITEMS.length - 1) % ITEMS.length);
  else if (k === " ") { show(prev); }
  else if (k === "s") setMode("grid");
  else if (k === "f") setMode("flip");
  else if (k === "w") $("bwhite").click();
  else if (k === "l") $("blabels").click();
  else if (k === "h") $("bhelp").click();
  else if (k === "enter") $("bfs").click();
  else return;
  e.preventDefault();
});
setMode(__MODE__);
</script>
</body>
</html>
"""


def write_flipbook(path, title, items, intro_html, strips=None, overlay=None, mode="flip"):
    page = (PAGE.replace("</body>", MAC_HELP + "</body>").replace("__TITLE__", html.escape(title))
            .replace("__INTRO__", intro_html)
            .replace("__ITEMS__", json.dumps(items, indent=1))
            .replace("__STRIPS__", json.dumps(strips, indent=1))
            .replace("__OVERLAY__", json.dumps(overlay))
            .replace("__MODE__", json.dumps(mode)))
    Path(path).write_text(page)
