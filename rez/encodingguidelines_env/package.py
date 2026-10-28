name = "encodingguidelines_env"

version = "1.0.0"

description = (
    "Python environment for the ORI Encoding Guidelines test framework (enctests). "
    "FFmpeg is deliberately not included, so it can be picked per run, e.g. "
    "rez-env encodingguidelines_env ffmpeg-8.1 -- python -m testframework.main ..."
)

authors = ["Sam Richards"]

# Keep these in sync with requirements.txt at the repo root.
requires = [
    "python-3.11",
    "numpy-2.2",
    "PyYAML-6",
    "Fileseq-2.1",
    "Jinja2-3.1",
    "pandas-2.3",
    "plotly-6.2",
    # plotly uses kaleido to write the report graphs; kaleido 1.x needs Chrome installed.
    "kaleido-1.5",
    "OpenTimelineIO-0.18",
    # The PyPI wheel provides the Python bindings as well as idiff and oiiotool.
    "OpenImageIO-3.1.12",
]

# Nothing to build, this package only defines the environment.
build_command = False


def commands():
    # The ffmpeg packages do not ship the VMAF models, fall back to Homebrew's.
    if not defined("VMAF_MODEL_DIR"):
        env.VMAF_MODEL_DIR = "/opt/homebrew/share/libvmaf/model"
