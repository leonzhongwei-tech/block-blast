"""
Generate Audio Sprite for Block Blast game.
Creates individual WAV sound effects using synthesis, then merges them into
a single audio sprite file (webm + m4a) with a JSON manifest for timestamps.

Sound effects:
1. place   - Block placement sound (short click/thud)
2. clear   - Row/column clear sound (ascending sweep)
3. combo   - Combo multiplier sound (triumphant chord)
4. gameover - Game over sound (descending sad tone)
"""

import numpy as np
import struct
import json
import subprocess
import os

SAMPLE_RATE = 44100
OUTPUT_DIR = "/home/ubuntu/user-block-blast/h5-game/audio"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def write_wav(filename, samples):
    """Write a mono WAV file from float samples (-1 to 1)."""
    # Clip and convert to 16-bit PCM
    samples = np.clip(samples, -1.0, 1.0)
    pcm = (samples * 32767).astype(np.int16)
    
    with open(filename, 'wb') as f:
        # WAV header
        data_size = len(pcm) * 2
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + data_size))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))  # chunk size
        f.write(struct.pack('<H', 1))   # PCM
        f.write(struct.pack('<H', 1))   # mono
        f.write(struct.pack('<I', SAMPLE_RATE))
        f.write(struct.pack('<I', SAMPLE_RATE * 2))  # byte rate
        f.write(struct.pack('<H', 2))   # block align
        f.write(struct.pack('<H', 16))  # bits per sample
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        f.write(pcm.tobytes())

def generate_place_sound(duration=0.08):
    """Short percussive click for block placement."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Short noise burst with fast decay
    noise = np.random.uniform(-1, 1, len(t))
    envelope = np.exp(-t * 60)
    # Add a low thud
    thud = np.sin(2 * np.pi * 80 * t) * np.exp(-t * 40)
    return (noise * envelope * 0.3 + thud * 0.7) * 0.8

def generate_clear_sound(duration=0.35):
    """Ascending sweep for row/column clear."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Frequency sweep from 300Hz to 1200Hz
    freq = 300 + 900 * (t / duration)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    wave = np.sin(phase)
    # Add harmonics
    wave += 0.3 * np.sin(phase * 2)
    wave += 0.15 * np.sin(phase * 3)
    # Envelope: quick attack, sustain, quick release
    envelope = np.minimum(t * 20, 1.0) * np.exp(-t * 3)
    return wave * envelope * 0.6

def generate_combo_sound(duration=0.5):
    """Triumphant chord for combo multiplier."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Major chord: root + major third + fifth
    root = 523.25  # C5
    wave = np.sin(2 * np.pi * root * t)
    wave += 0.7 * np.sin(2 * np.pi * root * 1.26 * t)  # E5
    wave += 0.5 * np.sin(2 * np.pi * root * 1.5 * t)   # G5
    wave += 0.3 * np.sin(2 * np.pi * root * 2 * t)     # C6 octave
    # Envelope
    envelope = np.minimum(t * 30, 1.0) * np.exp(-t * 4)
    return wave * envelope * 0.4

def generate_gameover_sound(duration=1.0):
    """Descending sad tone for game over."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Descending frequency from 440Hz to 110Hz
    freq = 440 * np.exp(-t * 1.5)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    wave = np.sin(phase)
    # Add minor third for sad feeling
    wave += 0.5 * np.sin(phase * 1.2)  # minor third
    # Slow decay envelope
    envelope = np.exp(-t * 2)
    return wave * envelope * 0.5

# Generate individual sound effects
sounds = {
    'place': generate_place_sound(),
    'clear': generate_clear_sound(),
    'combo': generate_combo_sound(),
    'gameover': generate_gameover_sound()
}

# Write individual WAV files
wav_files = []
for name, samples in sounds.items():
    wav_path = os.path.join(OUTPUT_DIR, f"{name}.wav")
    write_wav(wav_path, samples)
    wav_files.append(wav_path)
    print(f"Generated {name}.wav: {len(samples)/SAMPLE_RATE:.3f}s ({len(samples)} samples)")

# Add 50ms silence gap between sounds
gap_samples = int(SAMPLE_RATE * 0.05)
gap = np.zeros(gap_samples)

# Concatenate all sounds with gaps to create sprite
sprite_data = []
manifest = {"src": "audio-sprite", "sprite": {}}
current_offset = 0.0

for name, samples in sounds.items():
    duration = len(samples) / SAMPLE_RATE
    manifest["sprite"][name] = {
        "start": round(current_offset * 1000),  # ms
        "end": round((current_offset + duration) * 1000),  # ms
        "duration": round(duration * 1000)  # ms
    }
    sprite_data.append(samples)
    sprite_data.append(gap)
    current_offset += duration + 0.05  # 50ms gap
    print(f"  {name}: {manifest['sprite'][name]['start']}ms - {manifest['sprite'][name]['end']}ms")

# Write combined sprite WAV
sprite_wav = os.path.join(OUTPUT_DIR, "sprite.wav")
combined = np.concatenate(sprite_data)
write_wav(sprite_wav, combined)
print(f"\nCombined sprite: {len(combined)/SAMPLE_RATE:.3f}s total")

# Convert to WebM (Opus codec, 64kbps, mono)
sprite_webm = os.path.join(OUTPUT_DIR, "sprite.webm")
subprocess.run([
    'ffmpeg', '-y', '-i', sprite_wav,
    '-c:a', 'libopus', '-b:a', '64k', '-ac', '1',
    '-vbr', 'on', '-application', 'audio',
    sprite_webm
], capture_output=True, text=True)
print(f"Generated sprite.webm")

# Convert to M4A (AAC codec, 64kbps, mono) as fallback
sprite_m4a = os.path.join(OUTPUT_DIR, "sprite.m4a")
subprocess.run([
    'ffmpeg', '-y', '-i', sprite_wav,
    '-c:a', 'aac', '-b:a', '64k', '-ac', '1',
    sprite_m4a
], capture_output=True, text=True)
print(f"Generated sprite.m4a")

# Write manifest JSON
manifest_path = os.path.join(OUTPUT_DIR, "sprite-manifest.json")
with open(manifest_path, 'w') as f:
    json.dump(manifest, f, indent=2)
print(f"\nManifest written to sprite-manifest.json")
print(json.dumps(manifest, indent=2))

# Show file sizes
print("\n=== File Sizes ===")
for ext in ['webm', 'm4a', 'wav']:
    path = os.path.join(OUTPUT_DIR, f"sprite.{ext}")
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  sprite.{ext}: {size:,} bytes ({size/1024:.1f} KB)")

# Clean up individual WAV files and combined WAV (keep only webm + m4a + manifest)
for name in sounds:
    os.remove(os.path.join(OUTPUT_DIR, f"{name}.wav"))
os.remove(sprite_wav)
print("\nCleaned up intermediate WAV files.")
