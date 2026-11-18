This folder holds the graphs used in the documentation, and the results (OTIO) of the runs that made them. We do not
include the encoded media, since it gets quite large.

`graphs.yml` lists each set of graphs with the test config that made it and its OTIO file. The OTIO records the
FFmpeg version, the date of the run and the commands used. Graphs drawn since November 2026 also have the FFmpeg
version, config file and run date printed in their top right corner.

Run these from `enctests/`, in the test environment:

```bash
# Check graphs.yml against the pages, the configs and the OTIO files, and list the FFmpeg version of each set.
python reference-results/update_doc_graphs.py --check

# After running a config (python -m testframework.main --test-config <config> --results-folder wedge_results),
# copy its graphs and OTIO here.
python reference-results/update_doc_graphs.py --update intra-test422 --version 9.0.2

# Redraw a set of graphs from the OTIO here, without encoding (e.g. to add the version stamp).
python reference-results/update_doc_graphs.py --redraw intra-test422
```

When you add graphs to a page, add an entry to `graphs.yml` as well. If a page's text quotes numbers from a graph,
check the text after updating it.
