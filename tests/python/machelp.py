"""
A help dialog for the HDR test pages, shown on a Mac: how to set up the display so the result means something.
Shown once automatically (remembered in localStorage), and from a "Mac HDR setup" button after that.

    page = page.replace("</body>", MAC_HELP + "</body>")
"""

MAC_HELP = r"""
<style>
  #machelp { position: fixed; inset: 0; background: rgba(0,0,0,.7); display: none; z-index: 10;
             align-items: center; justify-content: center; }
  #machelp.show { display: flex; }
  #machelp > div { max-width: 760px; background: #1c1c1c; border: 1px solid #555; border-radius: 6px;
                   padding: 16px 24px; line-height: 1.45; color: #ccc; font: 14px -apple-system, Helvetica, sans-serif; }
  #machelp h2 { color: #e8d670; font-size: 18px; margin: 4px 0 10px; }
  #machelp b { color: #eee; }
  #machelp li { margin: 4px 0; }
  #macbtn { position: fixed; right: 10px; bottom: 10px; z-index: 9; display: none; background: #2a2a2a; color: #ccc;
            border: 1px solid #444; border-radius: 4px; padding: 4px 9px; font: 13px -apple-system, Helvetica, sans-serif;
            cursor: pointer; }
  body.fs #macbtn { display: none !important; }
</style>
<button id="macbtn">Mac HDR setup</button>
<div id="machelp"><div>
  <h2>Testing HDR on a Mac</h2>
  <p>macOS changes how HDR is shown depending on the display preset, the brightness setting and which window is
    active. Set it up first, or the results describe your settings rather than the files.</p>
  <ul>
    <li><b>MacBook Pro with an XDR screen (14"/16", M1 Pro/Max or later) or Pro Display XDR:</b> System Settings
      &rarr; Displays &rarr; Preset &rarr; <b>HDR Video (P3-ST 2084)</b>. PQ is then shown at its true level: SDR
      white is 100 cd/m<sup>2</sup>, it clips at 1000, and in our tests the mastering display, MaxCLL and the
      mastering primaries changed nothing. This is the setup to review in. Switch back afterwards.</li>
    <li><b>The default preset (Apple XDR Display)</b> tone maps relative to the brightness slider: below full
      brightness the picture went past 1000 cd/m<sup>2</sup>; at full brightness SDR white sat at PQ 160, and
      metadata claiming 4000 compressed the whole range. Use full brightness if you must use it, and note it.</li>
    <li><b>Keep the browser window active</b>, or use full screen: the result changed when another window had
      focus.</li>
    <li><b>Other Macs and external SDR monitors</b> have no such preset: macOS tone maps HDR to the screen.</li>
  </ul>
  <p style="color:#888">Measured on a MacBook Pro (M2 Max), macOS 26.6, in Safari (colour also in Chrome). Repeat in the players you use.</p>
  <button id="machelpclose">OK</button>
</div></div>
<script>
(() => {
  const mac = /Macintosh/.test(navigator.userAgent) && !("ontouchend" in document);  // not an iPad
  if (!mac) return;
  const d = document.getElementById("machelp"), b = document.getElementById("macbtn");
  b.style.display = "block";
  b.onclick = () => d.classList.add("show");
  document.getElementById("machelpclose").onclick = () => d.classList.remove("show");
  d.onclick = e => { if (e.target === d) d.classList.remove("show"); };
  if (!localStorage.getItem("machelp-seen")) { d.classList.add("show"); localStorage.setItem("machelp-seen", "1"); }
})();
</script>
"""
