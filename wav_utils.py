"""WAV file I/O and helpers."""

import wave
import struct
import hashlib
import os

SR = 44100


def write_wav(path, int_samples, sr=SR):
    """Write int16 samples to a mono WAV file. Returns sha256 hex digest."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(struct.pack(f'<{len(int_samples)}h', *int_samples))
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def silence_wav(path, duration_ms=300, sr=SR):
    """Generate a silent WAV file (useful for BT audio pre-roll)."""
    frames = int(sr * duration_ms / 1000)
    return write_wav(path, [0] * frames, sr)
