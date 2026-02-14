"""Synthesizers: glockenspiel, sine tones, ambient pads, and more."""

import math

SR = 44100


def _note_fadeout(i, frames):
    """Cosine fade-out over last 15% of a note to prevent pops."""
    fade_start = int(frames * 0.85)
    if i >= fade_start:
        t = (i - fade_start) / (frames - fade_start)
        return 0.5 * (1.0 + math.cos(math.pi * t))
    return 1.0


def glockenspiel(freq, duration_ms=600, volume=0.4, sr=SR):
    """Glockenspiel: sharp attack, exponential decay, metallic partials."""
    frames = int(sr * duration_ms / 1000)
    partials = [
        (1.0,  1.0),    # fundamental
        (2.76, 0.45),   # metallic partial
        (5.4,  0.20),   # bright shimmer
        (8.93, 0.08),   # high sparkle
    ]
    decay_rates = [4.0, 6.0, 10.0, 16.0]
    attack_frames = int(sr * 0.002)

    samples = []
    for i in range(frames):
        t = i / sr
        s = 0.0
        for (ratio, amp), dr in zip(partials, decay_rates):
            s += amp * math.sin(2 * math.pi * freq * ratio * t) * math.exp(-dr * t)
        if i < attack_frames:
            s *= i / attack_frames
        samples.append(s * volume * _note_fadeout(i, frames))
    return samples


def sine_tone(freq, duration_ms=200, volume=0.3, fade_ms=60, sr=SR):
    """Simple sine tone with fade in/out."""
    frames = int(sr * duration_ms / 1000)
    fade_frames = int(sr * fade_ms / 1000)
    samples = []
    for i in range(frames):
        t = i / sr
        s = math.sin(2 * math.pi * freq * t) * volume
        if i < fade_frames:
            s *= i / fade_frames
        if i > frames - fade_frames:
            s *= (frames - i) / fade_frames
        samples.append(s)
    return samples


def marimba(freq, duration_ms=500, volume=0.4, sr=SR):
    """Marimba-like: warm, fewer inharmonic partials, rounder attack."""
    frames = int(sr * duration_ms / 1000)
    partials = [
        (1.0,  1.0),
        (4.0,  0.30),
        (9.2,  0.08),
    ]
    decay_rates = [3.5, 7.0, 14.0]
    attack_frames = int(sr * 0.004)

    samples = []
    for i in range(frames):
        t = i / sr
        s = 0.0
        for (ratio, amp), dr in zip(partials, decay_rates):
            s += amp * math.sin(2 * math.pi * freq * ratio * t) * math.exp(-dr * t)
        if i < attack_frames:
            s *= i / attack_frames
        samples.append(s * volume * _note_fadeout(i, frames))
    return samples


def ambient(freq, duration_ms=900, volume=0.3, sr=SR):
    """Soft ambient pad: slow attack, gentle chorus detuning, long decay.

    Two slightly detuned voices + a quiet octave create a warm,
    non-intrusive wash of sound. No sharp transients.
    """
    frames = int(sr * duration_ms / 1000)
    attack_ms = 120  # slow fade in
    attack_frames = int(sr * attack_ms / 1000)
    decay_rate = 0.5  # very slow decay — long sustain and ring out

    # Slight detuning for chorus warmth (±1.5 Hz)
    detune = 1.5
    f1 = freq - detune
    f2 = freq + detune
    f_oct = freq * 2.0  # quiet octave above

    # Fade out the last 15% of the note to prevent pops when
    # notes are mixed in sequences and the sample array ends.
    fade_start = int(frames * 0.85)
    fade_len = frames - fade_start

    samples = []
    for i in range(frames):
        t = i / sr
        env = math.exp(-decay_rate * t)

        # Slow cosine attack (smoother than linear)
        if i < attack_frames:
            env *= 0.5 * (1.0 - math.cos(math.pi * i / attack_frames))

        # Per-note fade-out (cosine)
        if i >= fade_start:
            ft = (i - fade_start) / fade_len
            env *= 0.5 * (1.0 + math.cos(math.pi * ft))

        # Two detuned voices + soft octave
        s = 0.0
        s += 0.5 * math.sin(2 * math.pi * f1 * t)
        s += 0.5 * math.sin(2 * math.pi * f2 * t)
        s += 0.12 * math.sin(2 * math.pi * f_oct * t)  # airy shimmer

        samples.append(s * env * volume)
    return samples


def bowl(freq, duration_ms=1200, volume=0.3, sr=SR):
    """Singing bowl: slow attack, harmonic partials, very long ring.

    Based on Tibetan singing bowl overtone structure.
    Slow amplitude modulation gives the characteristic wobble.
    """
    frames = int(sr * duration_ms / 1000)
    attack_ms = 80
    attack_frames = int(sr * attack_ms / 1000)

    # Singing bowl partials (approximately harmonic, warm)
    partials = [
        (1.0,  1.0,  1.2),   # fundamental — slow decay
        (2.0,  0.35, 1.8),   # octave
        (3.01, 0.15, 2.5),   # slightly sharp 3rd partial
        (4.98, 0.06, 3.5),   # high shimmer
    ]

    samples = []
    for i in range(frames):
        t = i / sr

        # Cosine attack
        if i < attack_frames:
            att = 0.5 * (1.0 - math.cos(math.pi * i / attack_frames))
        else:
            att = 1.0

        s = 0.0
        for ratio, amp, dr in partials:
            # Gentle amplitude modulation (bowl wobble, ~4 Hz)
            mod = 1.0 + 0.06 * math.sin(2 * math.pi * 4.1 * t)
            s += amp * math.sin(2 * math.pi * freq * ratio * t) * math.exp(-dr * t) * mod

        samples.append(s * att * volume * _note_fadeout(i, frames))
    return samples
