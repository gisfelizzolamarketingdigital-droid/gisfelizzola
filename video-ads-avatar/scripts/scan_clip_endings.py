#!/usr/bin/env python3
"""
Builds one contact-sheet image sampling several points near the END of each
clip in a folder -- the fastest way to visually scan a whole campaign for the
reference-bleed-through artifact (see SKILL.md) without opening every clip
by hand.

Why multiple points per clip, not just one frame at the very end: real data
from a 27-clip campaign showed the artifact surviving the auto-trim in 7
clips, and in 6 of those 7 it only showed up in the single frame closest to
the (already-trimmed) end -- a single check at, say, duration-0.3s would have
missed most of them. Sampling a few points across the last ~2s catches both
the "creeps in gradually" and the "flashes right at the very end" cases.

Usage:
    python3 scan_clip_endings.py --clips-dir /path/to/clips --output /tmp/scan.jpg
    python3 scan_clip_endings.py --clips-dir /path/to/clips --offsets 1.5 1.0 0.5 0.15

Look at the output image yourself (read it with an image-reading tool) --
this script only assembles the contact sheet, it does not judge what's in it.
"""
import argparse
import glob
import os
import re
import subprocess
import tempfile

from PIL import Image


def get_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips-dir", required=True, help="Folder containing clip_NN.mp4 files")
    ap.add_argument("--pattern", default="clip_*.mp4", help="Glob pattern within --clips-dir (default: clip_*.mp4)")
    ap.add_argument("--offsets", type=float, nargs="+", default=[1.5, 1.0, 0.5, 0.15],
                     help="Seconds before each clip's end to sample (default: 1.5 1.0 0.5 0.15)")
    ap.add_argument("--output", required=True, help="Output contact sheet path (.jpg)")
    ap.add_argument("--thumb-width", type=int, default=200)
    args = ap.parse_args()

    clips = sorted(glob.glob(os.path.join(args.clips_dir, args.pattern)))
    if not clips:
        print(f"No files matched {args.pattern} in {args.clips_dir}")
        return

    with tempfile.TemporaryDirectory() as tmp:
        rows = []
        for clip_path in clips:
            name = os.path.splitext(os.path.basename(clip_path))[0]
            dur = get_duration(clip_path)
            row_frames = []
            for off in args.offsets:
                t = max(0.05, dur - off)
                frame_path = os.path.join(tmp, f"{name}_{off}.jpg")
                subprocess.run(
                    ["ffmpeg", "-y", "-ss", str(t), "-i", clip_path, "-frames:v", "1", "-q:v", "3", frame_path],
                    capture_output=True,
                )
                if os.path.exists(frame_path):
                    row_frames.append(frame_path)
            if row_frames:
                rows.append((name, row_frames))

        if not rows:
            print("No frames extracted -- check --clips-dir and --pattern.")
            return

        thumb_h = None
        sheet = None
        cols = len(args.offsets)
        for r, (name, row_frames) in enumerate(rows):
            for c, frame_path in enumerate(row_frames):
                im = Image.open(frame_path)
                if thumb_h is None:
                    aspect = im.height / im.width
                    thumb_h = int(args.thumb_width * aspect)
                    sheet = Image.new("RGB", (cols * args.thumb_width, len(rows) * thumb_h), "black")
                im = im.resize((args.thumb_width, thumb_h))
                sheet.paste(im, (c * args.thumb_width, r * thumb_h))

        sheet.save(args.output, quality=85)
        print(f"Wrote {args.output} -- {len(rows)} clip(s) x {cols} offset(s) ({args.offsets}).")
        print("Row order (top to bottom):")
        for name, _ in rows:
            print(f"  {name}")


if __name__ == "__main__":
    main()
