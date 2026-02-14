#!/usr/bin/env python3
"""Generate the gentle_pong sound pack for peon-ping.

Usage:
    python generate.py                  # generate + install
    python generate.py --preview        # play each sound after generating
    python generate.py --synth marimba  # use marimba instead of glockenspiel
"""

import argparse
import json
import os
import subprocess
import sys

from dsp import lowpass, reverb, normalize, trim_silence, fade_out, to_int16
from synth import glockenspiel, sine_tone, marimba, ambient, bowl
from wav_utils import write_wav, silence_wav

SR = 44100

# ── Where to install ──────────────────────────────────────────────
PEON_PING_DIR = os.path.expanduser("~/.claude/hooks/peon-ping")
PACK_NAME = "gentle_pong"
PACK_DIR = os.path.join(PEON_PING_DIR, "packs", PACK_NAME)
SOUNDS_DIR = os.path.join(PACK_DIR, "sounds")

# ── DSP chain ─────────────────────────────────────────────────────
LOWPASS_HZ = 1800       # cutoff frequency
LOWPASS_POLES = 3        # filter steepness
REVERB_DECAY = 0.5
REVERB_DELAYS = [41, 89, 149, 211, 283, 367, 449]  # ms — long, spacious hall

# ── Synth selection ───────────────────────────────────────────────
SYNTHS = {
    "glockenspiel": glockenspiel,
    "sine": sine_tone,
    "marimba": marimba,
    "ambient": ambient,
    "bowl": bowl,
}


def process(samples):
    """Apply DSP chain: lowpass → reverb → trim → normalize → int16."""
    s = lowpass(samples, cutoff_hz=LOWPASS_HZ, sr=SR, poles=LOWPASS_POLES)
    s = reverb(s, sr=SR, decay=REVERB_DECAY, delays_ms=REVERB_DELAYS)
    s = trim_silence(s)
    s = fade_out(s, fade_ms=200, sr=SR)
    s = normalize(s, peak=0.9)
    return to_int16(s)


def gen_single(filename, synth_fn, freq, duration_ms=600, volume=0.4):
    """Generate a single note, process, and write."""
    samples = synth_fn(freq, duration_ms, volume, sr=SR)
    path = os.path.join(SOUNDS_DIR, filename)
    return write_wav(path, process(samples))


def gen_chord(filename, synth_fn, freqs, duration_ms=800, volume=0.25):
    """Generate simultaneous notes (a chord), process, and write."""
    per_voice = volume / len(freqs)
    voices = [synth_fn(f, duration_ms, per_voice, sr=SR) for f in freqs]
    max_len = max(len(v) for v in voices)
    mixed = [0.0] * max_len
    for voice in voices:
        for i, s in enumerate(voice):
            mixed[i] += s
    path = os.path.join(SOUNDS_DIR, filename)
    return write_wav(path, process(mixed))


def gen_sequence(filename, synth_fn, notes, gap_ms=120, duration_ms=500, volume=0.35):
    """Generate a sequence of notes with overlap, process, and write."""
    gap_frames = int(SR * gap_ms / 1000)
    note_samples = [synth_fn(f, duration_ms, volume, sr=SR) for f in notes]

    stride = max(len(note_samples[0]) // 3, 1) + gap_frames
    total = stride * (len(notes) - 1) + len(note_samples[-1]) + int(SR * 0.5)
    mixed = [0.0] * total

    offset = 0
    for ns in note_samples:
        for i, s in enumerate(ns):
            if i + offset < len(mixed):
                mixed[i + offset] += s
        offset += stride

    path = os.path.join(SOUNDS_DIR, filename)
    return write_wav(path, process(mixed))


# ── Sound definitions ─────────────────────────────────────────────
# Each entry: (filename, type, synth_name, kwargs)
# Types: "single", "sequence", "chord"
# Each event uses a DIFFERENT synth for distinct timbre.
#
# C major pentatonic: C D E G A
# C3=131  D3=147  E3=165  G3=196  A3=220
# C4=262  D4=294  E4=330  G4=392  A4=440
SOUNDS = {
    # ── START: Singing bowl chord — deep, resonant, unmistakable ─────
    "session.start": [
        ("start_chord.wav", "chord", "bowl", dict(freqs=[131, 165, 196], duration_ms=1800, volume=0.3)),
        ("start_fifth.wav", "chord", "bowl", dict(freqs=[131, 196], duration_ms=1500, volume=0.28)),
    ],
    # ── ACKNOWLEDGE: Tiny sine blip — clean, minimal, just a nod ─────
    "task.acknowledge": [
        ("ack_blip.wav",  "single", "sine", dict(freq=392, duration_ms=200, volume=0.15)),
        ("ack_blip2.wav", "single", "sine", dict(freq=330, duration_ms=200, volume=0.15)),
    ],
    # ── COMPLETE: Ambient pad chord — warm, wide, satisfying ─────────
    "task.complete": [
        ("done_chord.wav",  "chord", "ambient", dict(freqs=[262, 330, 392], duration_ms=1400, volume=0.28)),
        ("done_resolve.wav", "chord", "ambient", dict(freqs=[196, 262], duration_ms=1200, volume=0.25)),
    ],
    # ── ERROR: Glockenspiel drop — percussive, metallic, stands out ──
    "task.error": [
        ("error_drop.wav", "sequence", "glockenspiel", dict(notes=[262, 131], gap_ms=200, duration_ms=600, volume=0.25)),
        ("error_hit.wav",  "single",   "glockenspiel", dict(freq=147, duration_ms=700, volume=0.22)),
    ],
    # ── INPUT NEEDED: Quick sine boop-boop — clean, attention poke ───
    "input.required": [
        ("input_boop.wav",  "sequence", "sine", dict(notes=[330, 440], gap_ms=60, duration_ms=180, volume=0.22)),
        ("input_boop2.wav", "sequence", "sine", dict(notes=[262, 392], gap_ms=60, duration_ms=180, volume=0.22)),
    ],
    # ── RATE LIMIT: Deep bowl hum — patience, slow, meditative ───────
    "resource.limit": [
        ("limit_hum.wav", "single", "bowl", dict(freq=131, duration_ms=2000, volume=0.18)),
    ],
    # ── SPAM: Rapid marimba taps — woody, playful, rhythmic ──────────
    "user.spam": [
        ("spam_taps.wav", "sequence", "marimba", dict(notes=[392, 392, 392, 440], gap_ms=40, duration_ms=150, volume=0.2)),
    ],
}

LABELS = {
    "start_chord.wav": "Bowl chord", "start_fifth.wav": "Bowl fifth",
    "ack_blip.wav": "Sine blip", "ack_blip2.wav": "Sine blip low",
    "done_chord.wav": "Pad chord", "done_resolve.wav": "Pad resolve",
    "error_drop.wav": "Metal drop", "error_hit.wav": "Metal hit",
    "input_boop.wav": "Boop boop", "input_boop2.wav": "Boop boop wide",
    "limit_hum.wav": "Deep hum", "spam_taps.wav": "Rapid taps",
}


def generate_all(preview=False):
    """Generate all sounds and return {filename: sha256}."""
    os.makedirs(SOUNDS_DIR, exist_ok=True)
    shas = {}

    for category, entries in SOUNDS.items():
        for filename, stype, synth_name, kwargs in entries:
            synth_fn = SYNTHS[synth_name]
            if stype == "single":
                sha = gen_single(filename, synth_fn, **kwargs)
            elif stype == "chord":
                sha = gen_chord(filename, synth_fn, **kwargs)
            else:
                sha = gen_sequence(filename, synth_fn, **kwargs)
            shas[filename] = sha
            print(f"  {category:20s} [{synth_name:13s}] {filename:20s} {sha[:12]}...")

            if preview:
                path = os.path.join(SOUNDS_DIR, filename)
                subprocess.run(["afplay", "-v", "1.0", path], check=False)

    return shas


def write_manifest(shas):
    """Write the CESP v1.0 openpeon.json manifest."""
    manifest = {
        "cesp_version": "1.0",
        "name": PACK_NAME,
        "display_name": "Gentle Pong",
        "version": "1.0.0",
        "author": {"name": "julvalen", "github": "julvalen"},
        "license": "MIT",
        "language": "en",
        "categories": {},
    }

    for category, entries in SOUNDS.items():
        sounds = []
        for filename, _, _, _ in entries:
            sounds.append({
                "file": f"sounds/{filename}",
                "label": LABELS.get(filename, filename),
                "sha256": shas[filename],
            })
        manifest["categories"][category] = {"sounds": sounds}

    manifest_path = os.path.join(PACK_DIR, "openpeon.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest: {manifest_path}")


def generate_silence():
    """Generate the BT pre-roll silence file."""
    path = os.path.join(PEON_PING_DIR, ".silence.wav")
    silence_wav(path, duration_ms=300)
    print(f"Silence: {path}")


def build_preview():
    """Concatenate all sounds into a single preview WAV and play it."""
    import wave, struct
    filenames = [f for entries in SOUNDS.values() for f, _, _, _ in entries]
    gap = [0] * int(SR * 0.5)
    all_samples = []
    for f in filenames:
        path = os.path.join(SOUNDS_DIR, f)
        with wave.open(path, 'r') as w:
            n = w.getnframes()
            raw = w.readframes(n)
            all_samples.extend(list(struct.unpack(f'<{n}h', raw)))
            all_samples.extend(gap)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(script_dir, "preview_all.wav")
    with wave.open(out, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(struct.pack(f'<{len(all_samples)}h', *all_samples))
    print(f"\nPreview: {out} ({len(all_samples)/SR:.1f}s)")
    subprocess.run(["afplay", "-v", "1.0", out], check=False)


def main():
    parser = argparse.ArgumentParser(description="Generate gentle_pong sound pack")
    parser.add_argument("--preview", action="store_true", help="Play each sound individually after generating")
    parser.add_argument("--preview-all", action="store_true", help="Generate and play all sounds back-to-back")
    args = parser.parse_args()

    print("Generating sounds (multi-timbre)...\n")

    shas = generate_all(preview=args.preview)
    write_manifest(shas)
    generate_silence()

    print(f"\nDone! Pack installed at: {PACK_DIR}")

    if args.preview_all:
        build_preview()


if __name__ == "__main__":
    main()
