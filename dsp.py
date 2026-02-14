"""DSP primitives: lowpass, reverb, normalization."""

import math

def lowpass(samples, cutoff_hz=2800, sr=44100, poles=2):
    """Multi-pole IIR lowpass filter."""
    rc = 1.0 / (2.0 * math.pi * cutoff_hz)
    dt = 1.0 / sr
    alpha = dt / (rc + dt)
    buf = list(samples)
    for _ in range(poles):
        out = [0.0] * len(buf)
        out[0] = buf[0] * alpha
        for i in range(1, len(buf)):
            out[i] = out[i - 1] + alpha * (buf[i] - out[i - 1])
        buf = out
    return buf


def reverb(samples, sr=44100, decay=0.35, delays_ms=None, tail_s=1.5):
    """Multi-tap delay reverb."""
    if delays_ms is None:
        delays_ms = [23, 53, 89, 131, 173]
    max_delay = int(sr * max(delays_ms) / 1000)
    out = [0.0] * (len(samples) + max_delay + int(sr * tail_s))
    for i, s in enumerate(samples):
        out[i] += s
    for d_ms in delays_ms:
        d = int(sr * d_ms / 1000)
        atten = decay ** (d_ms / delays_ms[0])
        for i, s in enumerate(samples):
            out[i + d] += s * atten
    return out


def normalize(samples, peak=0.9):
    """Normalize to target peak amplitude."""
    mx = max(abs(s) for s in samples) or 1.0
    if mx > peak:
        return [s * peak / mx for s in samples]
    return list(samples)


def trim_silence(samples, threshold=0.0001, chunk=200):
    """Trim trailing silence."""
    out = list(samples)
    while len(out) > chunk and all(abs(s) < threshold for s in out[-chunk:]):
        out = out[:-chunk]
    return out


def fade_out(samples, fade_ms=200, sr=44100):
    """Apply a long cosine fade-out + silent padding on both ends.

    The padding prevents afplay from popping when it opens/closes
    the audio device.
    """
    pad = [0.0] * int(sr * 0.05)  # 50ms silence
    fade_frames = min(int(sr * fade_ms / 1000), len(samples))
    out = list(samples)
    start = len(out) - fade_frames
    for i in range(fade_frames):
        t = i / fade_frames
        out[start + i] *= 0.5 * (1.0 + math.cos(math.pi * t))
    # Pad both ends with silence
    return pad + out + pad


def to_int16(samples):
    """Convert float samples [-1, 1] to int16."""
    return [int(max(-1.0, min(1.0, s)) * 32767) for s in samples]
