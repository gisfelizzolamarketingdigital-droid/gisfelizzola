"""
Whole-campaign self-review contact sheet: START / MIDDLE / END frames for every
clip in one image, labeled with clip id, character and (if available) the
transcript QA status from clip_qa.json. Generalizes scan_clip_endings.py (which
only samples near the end, for the reference-bleed artifact specifically) into
the full SKILL.md step 5b check -- so one image covers anatomy glitches,
identity drift and format/scene drift too, not just the end-of-clip bleed.

This module only assembles images -- read the result yourself (or hand it to
an image-reading tool) and judge what's in it, same as scan_clip_endings.py.
"""

import json
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

OFFSET_FRACTIONS = (0.04, 0.5, 0.96)  # start / middle / end, as a fraction of clip duration
MAX_ROWS_PER_SHEET = 10
THUMB_WIDTH = 260
LABEL_H = 26


def _duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def _font(size):
    for candidate in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if os.path.isfile(candidate):
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                pass
    return ImageFont.load_default()


def build_review_sheets(job, clips_dir, output_prefix, only_ids=None):
    """Writes one or more '<output_prefix>_N.jpg' contact sheets (paginated at
    MAX_ROWS_PER_SHEET clips each). Returns the list of written paths."""
    qa_path = os.path.join(os.path.dirname(clips_dir.rstrip("/")), "clip_qa.json")
    qa = {}
    if os.path.isfile(qa_path):
        with open(qa_path) as f:
            qa = {int(k): v for k, v in json.load(f).items()}

    clips = [c for c in job["clips"] if not only_ids or c["id"] in only_ids]
    rows = []
    tmp = tempfile.mkdtemp(prefix="review_clips_")
    for clip in clips:
        cid = clip["id"]
        path = os.path.join(clips_dir, f"clip_{cid:02d}.mp4")
        if not os.path.isfile(path):
            continue
        dur = _duration(path)
        if not dur:
            continue
        frames = []
        for frac in OFFSET_FRACTIONS:
            t = max(0.05, min(dur - 0.05, dur * frac))
            fp = os.path.join(tmp, f"c{cid}_{frac}.jpg")
            subprocess.run(["ffmpeg", "-y", "-ss", str(t), "-i", path, "-frames:v", "1", "-q:v", "3", fp], capture_output=True)
            if os.path.exists(fp):
                frames.append(fp)
        if not frames:
            continue
        entry = qa.get(cid, {})
        status = entry.get("status", "")
        similarity = entry.get("similarity")
        label = f"clip {cid} ({clip.get('character', '?')})"
        if similarity is not None:
            label += f" | {similarity:.0%} match"
        if status:
            label += f" | {status[:40]}"
        rows.append((label, frames))

    if not rows:
        return []

    written = []
    cols = len(OFFSET_FRACTIONS)
    for page_start in range(0, len(rows), MAX_ROWS_PER_SHEET):
        page_rows = rows[page_start:page_start + MAX_ROWS_PER_SHEET]
        thumb_h = None
        sheet = None
        draw = None
        font = _font(13)
        for r, (label, frame_paths) in enumerate(page_rows):
            for c, fp in enumerate(frame_paths):
                im = Image.open(fp)
                if thumb_h is None:
                    thumb_h = int(THUMB_WIDTH * im.height / im.width)
                    sheet = Image.new("RGB", (cols * THUMB_WIDTH, len(page_rows) * (thumb_h + LABEL_H)), "white")
                    draw = ImageDraw.Draw(sheet)
                im = im.resize((THUMB_WIDTH, thumb_h))
                y = r * (thumb_h + LABEL_H)
                sheet.paste(im, (c * THUMB_WIDTH, y + LABEL_H))
            draw.rectangle([0, r * (thumb_h + LABEL_H), cols * THUMB_WIDTH, r * (thumb_h + LABEL_H) + LABEL_H], fill=(20, 20, 20))
            draw.text((6, r * (thumb_h + LABEL_H) + 5), page_rows[r][0], fill="white", font=font)

        page_no = page_start // MAX_ROWS_PER_SHEET + 1
        out_path = f"{output_prefix}_{page_no}.jpg" if len(rows) > MAX_ROWS_PER_SHEET else f"{output_prefix}.jpg"
        sheet.save(out_path, quality=88)
        written.append(out_path)

    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    return written
