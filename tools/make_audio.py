"""Synthesize all game audio: python3 tools/make_audio.py <output_dir> [name_filter]"""
import sys
import time

sys.path.insert(0, "malchorya")
from sound.library import generate_all

if __name__ == "__main__":
    started = time.time()
    generate_all(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None, force=len(sys.argv) > 2)
    print(f"done in {time.time() - started:.0f}s")
