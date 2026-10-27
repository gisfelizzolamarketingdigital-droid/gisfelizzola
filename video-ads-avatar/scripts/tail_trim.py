"""
Per-clip transcript QA + precise tail trim for Veo talking clips.

Problem: Veo clips often end with a low-frequency rumble/thump in the last
~0.3-0.8s (visible on a spectrogram, present with the old v1 prompt too). The
prompt-v2 "timing" block makes speech end ~0.5-1s before the clip does, so there
is room to cut it -- but only if the cut lands right after the last word.

Safety rules (learned the hard way, see SKILL.md "trim ate the last word"):
  * The cut point comes from real word timestamps (AssemblyAI), never a blanket
    "trim N seconds".
  * A clip is only trimmed if its transcript matches the dialogue it was
    generated from (same word count +-1, same last word). Anything else is
    reported and left untouched: a mismatch means Veo dropped/added a word or ASR
    hiccuped, and trimming on top of that risks eating real speech.
  * Cut = last word end + margin (default 0.30s), with a 60ms audio fade-out so
    there is no click. Never cuts if it would gain less than 0.15s.
  * The untouched original is kept as clip_NN.raw.mp4 next to the clip, so a
    different margin can be retried without re-downloading. A clip that already
    has a .raw.mp4 is considered processed and skipped (idempotent).
"""

import concurrent.futures
import difflib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

import requests
import bcc_env  # keys live in ~/.bcc-toolkit/.env (they survive plugin updates); the skill's own .env is still honoured

ASSEMBLY = "https://api.assemblyai.com/v2"
DEFAULT_MARGIN_S = 0.30
MIN_GAIN_S = 0.15
FADE_S = 0.06
POLL_SECONDS = 3
POLL_TIMEOUT_S = 300


def _read_env(path):
    values = {}
    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def get_assembly_key(skill_dir):
    """ASSEMBLYAI_KEY from env, this skill's .env, or the sibling editar-anuncios/.env.
    Returns None if not configured. Never prints the key."""
    candidates = [
        os.environ.get("ASSEMBLYAI_KEY"),
        _read_env(os.path.join(skill_dir, ".env")).get("ASSEMBLYAI_KEY"),
        _read_env(os.path.join(os.path.dirname(skill_dir), "editar-anuncios", ".env")).get("ASSEMBLYAI_KEY"),
    ]
    for key in candidates:
        if key and "pega" not in key.lower() and key.lower() not in ("changeme", "your-key"):
            return key
    return None


def _norm(word):
    word = unicodedata.normalize("NFD", word.lower())
    word = "".join(c for c in word if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", word)


def _words(text):
    return [w for w in (_norm(t) for t in re.findall(r"[\wÀ-ÿ]+", text or "", re.UNICODE)) if w]


def duration_of(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def transcribe_words(key, video_path, tmp_dir):
    """Word list [{'text','start','end'}] (ms) for a clip's audio, or None on failure."""
    headers = {"authorization": key}
    wav = os.path.join(tmp_dir, os.path.basename(video_path) + ".16k.wav")
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", wav],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return None
    try:
        with open(wav, "rb") as f:
            upload_url = requests.post(f"{ASSEMBLY}/upload", headers=headers, data=f, timeout=120).json()["upload_url"]
        tid = requests.post(
            f"{ASSEMBLY}/transcript", headers=headers, timeout=60,
            json={"audio_url": upload_url, "speech_models": ["universal-3-5-pro", "universal-2"], "language_code": "es"},
        ).json()["id"]
        deadline = time.time() + POLL_TIMEOUT_S
        while time.time() < deadline:
            data = requests.get(f"{ASSEMBLY}/transcript/{tid}", headers=headers, timeout=60).json()
            if data["status"] == "completed":
                return data.get("words") or []
            if data["status"] == "error":
                return None
            time.sleep(POLL_SECONDS)
    except (requests.RequestException, KeyError, ValueError):
        return None
    finally:
        if os.path.exists(wav):
            os.remove(wav)
    return None


def check_clip(dialogue, words):
    """Compare transcript to intended dialogue. Returns dict with ok/reasons/timing."""
    expected = _words(dialogue)
    got = [_norm(w["text"]) for w in words if _norm(w["text"])]
    ratio = difflib.SequenceMatcher(None, expected, got).ratio() if expected else 0.0
    reasons = []
    if abs(len(got) - len(expected)) > 1:
        reasons.append(f"word count {len(got)} vs expected {len(expected)}")
    if got and expected and got[-1] != expected[-1]:
        reasons.append(f"last word '{got[-1]}' vs expected '{expected[-1]}'")
    if not got:
        reasons.append("no speech detected")
    return {
        "ok": not reasons,
        "reasons": reasons,
        "similarity": round(ratio, 3),
        "first_word_s": words[0]["start"] / 1000 if words else None,
        "last_word_end_s": words[-1]["end"] / 1000 if words else None,
        "transcript": " ".join(w["text"] for w in words),
    }


def cut_tail(path, cut_s):
    """Re-encode `path` in place, ending at cut_s with a short audio fade. Keeps <path minus .mp4>.raw.mp4."""
    raw = path[:-4] + ".raw.mp4"
    os.replace(path, raw)
    fade_start = max(cut_s - FADE_S, 0)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", raw, "-t", f"{cut_s:.3f}",
         "-af", f"afade=t=out:st={fade_start:.3f}:d={FADE_S}",
         "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", path],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        os.replace(raw, path)  # restore the original
        return False, r.stderr
    return True, ""


def process_clips(job, clips_dir, skill_dir, margin_s=None, dry_run=False, only_ids=None, workers=4):
    """Transcribe each clip, QA it against its dialogue, and trim the noisy tail.
    Returns a report dict {clip_id: {...}} (also useful for the caller to print)."""
    margin_s = margin_s if margin_s is not None else job.get("tail_margin_s", DEFAULT_MARGIN_S)
    key = get_assembly_key(skill_dir)
    if not key:
        print("  tail trim skipped: no ASSEMBLYAI_KEY found (env var, video-ads-avatar/.env or editar-anuncios/.env).", file=sys.stderr)
        return {}

    todo = []
    report = {}
    for clip in job["clips"]:
        cid = clip["id"]
        if only_ids and cid not in only_ids:
            continue
        path = os.path.join(clips_dir, f"clip_{cid:02d}.mp4")
        raw = path[:-4] + ".raw.mp4"
        if not os.path.isfile(path):
            continue
        if os.path.isfile(raw):
            report[cid] = {"status": "already processed (raw kept)"}
            continue
        todo.append((clip, path))

    tmp_dir = os.path.join(clips_dir, ".tailtmp")
    os.makedirs(tmp_dir, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(transcribe_words, key, path, tmp_dir): (clip, path) for clip, path in todo}
        results = {}
        for fut in concurrent.futures.as_completed(futures):
            clip, path = futures[fut]
            results[clip["id"]] = (clip, path, fut.result())
    try:
        os.rmdir(tmp_dir)
    except OSError:
        pass

    for cid in sorted(results):
        clip, path, words = results[cid]
        if words is None:
            report[cid] = {"status": "transcription failed, left untouched"}
            continue
        qa = check_clip(clip.get("dialogue", ""), words)
        dur = duration_of(path)
        entry = {**qa, "duration_s": dur}
        if not qa["ok"]:
            entry["status"] = "NOT trimmed: transcript does not match dialogue (" + "; ".join(qa["reasons"]) + ")"
        elif dur is None:
            entry["status"] = "NOT trimmed: could not read duration"
        else:
            cut = qa["last_word_end_s"] + margin_s
            if dur - cut < MIN_GAIN_S:
                entry["status"] = f"kept: speech ends at {qa['last_word_end_s']:.2f}s of {dur:.2f}s, nothing worth cutting"
            elif dry_run:
                entry["status"] = f"would cut {dur:.2f}s -> {cut:.2f}s"
                entry["cut_s"] = round(cut, 3)
            else:
                ok, err = cut_tail(path, cut)
                entry["status"] = f"cut {dur:.2f}s -> {cut:.2f}s" if ok else f"cut FAILED, original kept: {err.strip()[:120]}"
                entry["cut_s"] = round(cut, 3)
        report[cid] = entry
    return report


def print_report(report):
    for cid in sorted(report):
        e = report[cid]
        timing = ""
        if e.get("first_word_s") is not None:
            timing = f" | speech {e['first_word_s']:.2f}s -> {e['last_word_end_s']:.2f}s | match {e['similarity']:.0%}"
        print(f"  clip {cid}: {e['status']}{timing}")
