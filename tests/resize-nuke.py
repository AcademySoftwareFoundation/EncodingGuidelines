"""
Make the Nuke results for the resize comparison (tests/resize-test.py), which uses them if they exist.

Paste into Nuke's Script Editor and run (Nuke's terminal mode needs a render licence; the GUI does not). Set REPO to
your checkout first. Resizes the Sparks EXR (enctests/sources/hdr_sources/download_media.sh) to 1024x540 with
Reformat, with each filter and clamp off and on, and writes scene-linear float EXRs to tests/resize-compare/nuke/
(raw in and raw out, so Nuke's colour management is not involved; resize-test.py applies the view). The EXRs are about
6 MB each and are not committed.

Measured with Nuke 17.1v1. Reformat's clamp "sets negative intermediate and final results to zero" (its tooltip).
"""
import os

import nuke

REPO = os.path.expanduser("~/git/EncodingGuidelines")
SRC = os.path.join(REPO, "enctests/sources/hdr_sources/sparks/SPARKS_ACES_06100.exr")
OUT = os.path.join(REPO, "tests/resize-compare/nuke")
os.makedirs(OUT, exist_ok=True)

read = nuke.nodes.Read(file=SRC)
read["raw"].setValue(True)
written = []
for filt in ("Cubic", "Mitchell", "Lanczos4", "Lanczos6", "Keys", "Simon", "Rifman"):
    for clamp in (False, True):
        r = nuke.nodes.Reformat(inputs=[read])
        r["type"].setValue("to box")
        r["box_fixed"].setValue(True)
        r["box_width"].setValue(1024)
        r["box_height"].setValue(540)
        r["resize"].setValue("distort")
        r["filter"].setValue(filt)
        r["clamp"].setValue(clamp)
        r["black_outside"].setValue(False)
        name = f"nuke-{filt.lower()}{'-clamp' if clamp else ''}.exr"
        w = nuke.nodes.Write(inputs=[r], file=os.path.join(OUT, name), file_type="exr")
        w["raw"].setValue(True)
        w["datatype"].setValue("32 bit float")
        w["channels"].setValue("rgb")
        nuke.execute(w, 1, 1)
        written.append(name)
print("Nuke", nuke.NUKE_VERSION_STRING, "wrote", len(written), "files to", OUT)
