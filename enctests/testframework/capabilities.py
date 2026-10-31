"""
Work out what the FFmpeg build (and machine) can do, so tests that need something it lacks are skipped rather
than failed.

A test, or a single wedge, can say what it needs with a `requires:` block:

    requires:
      ffmpeg: ">=8.1"              # version range, a string or a list that must all hold
      encoders: [liboapv]          # must be in `ffmpeg -encoders`
      decoders: [...]              # `ffmpeg -decoders`
      filters: [ocio, zscale]      # `ffmpeg -filters`
      hwaccels: [videotoolbox]     # `ffmpeg -hwaccels`
      hardware: [hevc_nvenc]       # encoders that must actually work: checked with a one-frame trial encode
      platform: [darwin]           # sys.platform values

Without a `requires:` block, a wedge's `-c:v` encoder must still be in the build, and hardware encoders
(`*_nvenc`, `*_videotoolbox`, ...) must pass the trial encode, so most hardware and codec tests need no
changes.

Version specifiers are `>=`, `>`, `<=`, `<`, `==` and `!=`. `==9.0` matches any 9.0.x. Git builds report no
release number (`N-124257-g73262c9136`); they are placed after the newest release whose libavutil they include,
as `8.1+dev`, which is newer than any 8.1.x and older than 9.0. To ask for a feature that is only in development
builds, write e.g. `>=9.0+dev`.

A `known_issue:` block (test or wedge level) marks a result that is expected to fail on some versions, so the
tests can show both that nothing has broken and when an upstream fix arrives:

    known_issue:
      ffmpeg: ">=8.0"              # the versions affected, as in requires: (default: all)
      platform: [darwin]           # optional, as in requires:
      note: "libswscale full range gain too high (384fe39623)"

On an affected version a failure is reported as a known issue rather than a failure, and a pass as an
unexpected pass, which usually means it has been fixed. On other versions the wedge is an ordinary test.
"""
import re
import subprocess
import sys

DEV = 9999  # patch level given to git builds, so they sort after every release of the same major.minor

# libavutil (major, minor) at each release, used to place git builds. From libavutil/version.h at each tag;
# add new releases here.
RELEASE_LIBAVUTIL = [
    ((5, 0), (57, 17)),
    ((5, 1), (57, 28)),
    ((6, 0), (58, 2)),
    ((6, 1), (58, 29)),
    ((7, 0), (59, 8)),
    ((7, 1), (59, 39)),
    ((8, 0), (60, 8)),
    ((8, 1), (60, 26)),
    ((9, 0), (61, 1)),
]

# Wedge keys that are read by the test framework, not passed to ffmpeg.
FRAMEWORK_KEYS = ('requires', 'known_issue')

HARDWARE_SUFFIXES = ('_nvenc', '_videotoolbox', '_qsv', '_vaapi', '_amf', '_vulkan', '_mf', '_v4l2m2m', '_d3d12va')

SPECIFIER = re.compile(r'^\s*(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+){0,2})(\+dev)?\s*$')


def parse_version(text):
    """'9.0.2' -> (9, 0, 2); '9.0+dev' -> (9, 0, DEV)."""
    numbers, _, dev = text.partition('+')
    parts = tuple(int(p) for p in numbers.split('.'))
    if dev:
        return (parts + (0, 0))[:2] + (DEV,)
    return parts


def format_version(version):
    if version is None:
        return 'unknown'
    if len(version) == 3 and version[2] == DEV:
        return f'{version[0]}.{version[1]}+dev'
    return '.'.join(str(p) for p in version)


def version_matches(version, specifier):
    match = SPECIFIER.match(specifier)
    if not match:
        raise ValueError(f'Unrecognised FFmpeg version requirement "{specifier}"')
    op, number, dev = match.groups()
    wanted = parse_version(number + (dev or ''))
    if op in ('==', '!='):
        # Compare only the parts given, so ==9.0 matches 9.0.2 and 9.0+dev.
        same = version[:len(wanted)] == wanted
        return same if op == '==' else not same
    padded = (wanted + (0, 0, 0))[:3]
    current = (version + (0, 0, 0))[:3]
    return {'>=': current >= padded, '>': current > padded,
            '<=': current <= padded, '<': current < padded}[op]


class FFmpegCapabilities:
    """What one FFmpeg binary supports. Each query runs ffmpeg at most once."""

    def __init__(self, ffmpeg_bin):
        self.ffmpeg_bin = ffmpeg_bin
        self._version = False
        self._lists = {}
        self._trials = {}

    def _run(self, args, timeout=60):
        try:
            return subprocess.run([self.ffmpeg_bin, '-hide_banner'] + args, capture_output=True, text=True,
                                  timeout=timeout)
        except (OSError, subprocess.TimeoutExpired):
            return None

    @property
    def version(self):
        """(major, minor, patch), (major, minor, DEV) for a git build, or None if it cannot be worked out."""
        if self._version is False:
            self._version = None
            result = self._run(['-version'])
            text = result.stdout if result else ''
            release = re.search(r'ffmpeg version n?(\d+)\.(\d+)(?:\.(\d+))?', text)
            avutil = re.search(r'libavutil\s+(\d+)\.\s*(\d+)\.', text)
            if release:
                self._version = tuple(int(p or 0) for p in release.groups())
            elif avutil:
                built = (int(avutil.group(1)), int(avutil.group(2)))
                older = [rel for rel, lib in RELEASE_LIBAVUTIL if lib <= built]
                if older:
                    self._version = older[-1] + (DEV,)
        return self._version

    def _list(self, kind):
        """Names from `ffmpeg -encoders`, `-decoders`, `-filters` or `-hwaccels`."""
        if kind not in self._lists:
            result = self._run([f'-{kind}'])
            names = set()
            for line in (result.stdout if result else '').splitlines():
                fields = line.split()
                if kind == 'hwaccels':
                    if len(fields) == 1 and not line.endswith(':'):
                        names.add(fields[0])
                elif len(fields) >= 2 and re.fullmatch(r'[A-Z.|]{2,}', fields[0]) and fields[1] != '=':
                    names.add(fields[1])
            self._lists[kind] = names
        return self._lists[kind]

    def encoder_works(self, encoder):
        """Encode one small frame, for hardware encoders that are built in but may have no device."""
        if encoder not in self._trials:
            result = self._run(['-v', 'error', '-f', 'lavfi', '-i', 'color=c=gray:s=1280x720:r=25',
                                '-frames:v', '1', '-c:v', encoder, '-f', 'null', '-'])
            self._trials[encoder] = result is not None and result.returncode == 0
        return self._trials[encoder]

    def unmet(self, requires):
        """The requirements in a `requires:` dict that this build or machine does not meet, as messages."""
        missing = []
        requires = requires or {}

        specifiers = requires.get('ffmpeg', [])
        if isinstance(specifiers, str):
            specifiers = [specifiers]
        if specifiers:
            if self.version is None:
                missing.append(f'FFmpeg {", ".join(specifiers)} (version unknown)')
            elif not all(version_matches(self.version, s) for s in specifiers):
                missing.append(f'FFmpeg {", ".join(specifiers)} (this is {format_version(self.version)})')

        for kind in ('encoders', 'decoders', 'filters', 'hwaccels'):
            for name in requires.get(kind, []):
                if name not in self._list(kind):
                    missing.append(f'{kind[:-1]} {name}')

        for encoder in requires.get('hardware', []):
            if encoder not in self._list('encoders'):
                missing.append(f'encoder {encoder}')
            elif not self.encoder_works(encoder):
                missing.append(f'{encoder} hardware')

        platforms = requires.get('platform', [])
        if isinstance(platforms, str):
            platforms = [platforms]
        if platforms and sys.platform not in platforms:
            missing.append(f'platform {" or ".join(platforms)}')

        return missing

    def known_issue_applies(self, known_issue):
        """Whether a `known_issue:` block covers this build and machine."""
        return not self.unmet({k: v for k, v in known_issue.items() if k in ('ffmpeg', 'platform')})


def wedge_encoder(wedge):
    """The video encoder a wedge asks for, if any."""
    for key in ('-c:v', '-vcodec', '-codec:v'):
        if wedge.get(key):
            return str(wedge[key]).strip('"\'')
    return None


def implied_requires(wedge):
    """What a wedge needs without saying so: its encoder, and a working device for a hardware encoder."""
    encoder = wedge_encoder(wedge)
    if not encoder or encoder == 'copy':
        return {}
    if encoder.endswith(HARDWARE_SUFFIXES):
        return {'hardware': [encoder]}
    return {'encoders': [encoder]}


def merge_requires(*blocks):
    """Combine `requires:` dicts (test level, wedge level, implied); lists are joined."""
    merged = {}
    for block in blocks:
        for key, value in (block or {}).items():
            values = [value] if isinstance(value, str) else list(value)
            merged.setdefault(key, [])
            merged[key].extend(v for v in values if v not in merged[key])
    return merged
