"""
Footprints of a downsize, for the resize tests (tests/resize-test.py, resize-highlightcomp.py, resize-antiring.py).

Each output pixel covers a rectangle of the source: for a resize by a whole factor k, exactly its own k x k block;
otherwise (4096 to 1920 is x2.133) the rectangle cuts through the source pixels at its edges, which count by how much
of them it covers.
"""
import numpy as np


def area_matrix(n, m):
    """m x n weights: how much of each of n source pixels each of m output pixels covers, as a fraction of it."""
    s = n / m
    a = np.zeros((m, n))
    for i in range(m):
        lo, hi = i * s, (i + 1) * s
        for j in range(int(np.floor(lo)), min(int(np.ceil(hi)), n)):
            a[i, j] = min(j + 1, hi) - max(j, lo)
    return a / s


def area_resize(img, w, h):
    """The average of each output pixel's footprint (h x w x channels), in whatever space img is in. For a whole
    factor, this is the plain block average."""
    ay, ax = area_matrix(img.shape[0], h), area_matrix(img.shape[1], w)
    return np.stack([ay @ img[..., c] @ ax.T for c in range(img.shape[2])], -1)


def spans(n, m):
    """For each of m output pixels, the range [a, b) of the n source pixels its footprint touches."""
    s = n / m
    return [(int(np.floor(i * s)), min(int(np.ceil((i + 1) * s - 1e-9)), n)) for i in range(m)]


def footprint_range(img, w, h):
    """Per-channel minimum and maximum of the source pixels each output pixel's footprint touches (h x w x
    channels each): the limits of the anti-ringing clamp."""
    xs, ys = spans(img.shape[1], w), spans(img.shape[0], h)
    lo = np.stack([img[:, a:b].min(1) for a, b in xs], 1)
    hi = np.stack([img[:, a:b].max(1) for a, b in xs], 1)
    return (np.stack([lo[a:b].min(0) for a, b in ys], 0),
            np.stack([hi[a:b].max(0) for a, b in ys], 0))
