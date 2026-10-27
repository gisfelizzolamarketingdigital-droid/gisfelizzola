#!/usr/bin/env python3
"""
Runs the apimart.ai (Veo 3.1) video-ad pipeline: uploads avatar reference images,
submits one generation per clip, polls until each is done, downloads the clips,
and stitches them into a single final video with ffmpeg.

Also generates 3x3 character sheets (via apimart's image API) used to keep a
character consistent across the varied scenes of a "voiceover" format ad.

Usage:
    python3 pipeline.py generate --config job.json
    python3 pipeline.py character-sheet --image /path/to/ref.jpg --output-dir /path/to/dir

See SKILL.md and references/formats.md for the job config schema and format guide.
"""

import argparse
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import campaign_log  # noqa: E402  (cross-campaign learning log, same folder)
import prompting  # noqa: E402  (prompt system v2 + lint, same folder)
import review_clips  # noqa: E402  (whole-campaign start/middle/end contact sheet, same folder)
import tail_trim  # noqa: E402  (per-clip transcript QA + precise tail trim)

API_BASE = "https://api.apimart.ai/v1"
POLL_INTERVAL_SECONDS = 8
POLL_TIMEOUT_SECONDS = 480  # 8 minutes per clip/image
PRICE_PER_CLIP = {"veo3.1-fast": 0.083, "veo3.1-quality": 0.60, "veo3.1-lite": 0.05}
PRICE_PER_IMAGE = {"gpt-image-2": 0.014, "nano-banana": 0.0125}  # at 2k / default resolution
# Other apimart image models can be passed to `generate-image --model` (price not tracked here, ~US$0.01-0.05 per image).
# Measured 2026-10 on the same selfie prompt: gpt-image-2.5-flare = most natural skin/face (recommended for avatars),
# seedream-5-0-pro = natural but a bit more polished, gemini-3-pro-image-preview = good but tends to stage a mirror selfie,
# flux-2-max = exaggerates freckles/blemishes.


def price_label(model):
    return f"~${PRICE_PER_IMAGE[model]:.3f}" if model in PRICE_PER_IMAGE else "price varies, ~$0.01-0.05"
DEFAULT_ACCENT = "Spanish with a neutral Latin American accent."
CONTINUOUS_TAKE_SUFFIX = "Single continuous take, no cuts or scene changes."

CHARACTER_SHEET_PROMPT = """Using the reference image as the ONLY source of identity, generate a professional 3×3 character sheet showing the exact same person from multiple angles and expressions.
The identity must remain absolutely identical to the reference:
- Same facial structure
- Same eye shape and spacing
- Same nose
- Same lips
- Same jawline
- Same hairstyle and hairline
- Same skin tone
- Same proportions
- Same age
- Same ethnicity
- Same facial asymmetries and unique identifying features
Do NOT beautify, stylize, or reinterpret the person in any way.
Create a clean character sheet with nine evenly spaced portraits on a neutral light gray background.
Include:
• Front view (neutral)
• Left profile (90°)
• Right profile (90°)
• Left three-quarter view
• Right three-quarter view
• Slight downward gaze
• Slight upward gaze
• Serious expression
• Neutral expression
Lighting should be soft and perfectly consistent across every frame, similar to a professional modeling digitization session.
Hair, clothing, makeup and accessories must remain identical in every portrait.
The camera distance, focal length and framing should stay consistent throughout.
Ultra high realism.
Extremely accurate identity preservation.
No artistic interpretation.
No beauty filters.
No skin smoothing.
No extra accessories.
No background variation.
The final result should look like a facial identity reference sheet used by professional VFX, AAA game studios, or film character departments."""


import bcc_env  # keys live in ~/.bcc-toolkit/.env (they survive plugin updates); the skill's own .env is still honoured
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = bcc_env.ENV_PATH   # messages point at the persistent file


def load_env_file(path):
    """Minimal .env parser (KEY=VALUE per line, no external dependency)."""
    values = {}
    if not os.path.isfile(path):
        return values
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_api_key():
    key = os.environ.get("APIMART_API_KEY")
    if not key:
        key = load_env_file(ENV_FILE).get("APIMART_API_KEY")

    placeholder = key in (None, "", "pega-aqui-tu-key-de-apimart")
    if placeholder:
        print(
            f"APIMART_API_KEY is not set.\n\n"
            f"Open this file:\n  {ENV_FILE}\n"
            "and replace the placeholder with your real key, e.g.:\n"
            "  APIMART_API_KEY=sk-xxxxxxxxxxxxxxxx\n\n"
            "Get your key from https://apimart.ai/keys",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def check_ffmpeg():
    if not shutil.which("ffmpeg"):
        print(
            "ffmpeg is not installed or not on PATH. Install it, e.g.:\n"
            "  brew install ffmpeg",
            file=sys.stderr,
        )
        sys.exit(1)


def auth_headers(api_key):
    return {"Authorization": f"Bearer {api_key}"}


def upload_image(api_key, path_or_url):
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url

    if not os.path.isfile(path_or_url):
        print(f"Reference image not found: {path_or_url}", file=sys.stderr)
        sys.exit(1)

    mime_type = mimetypes.guess_type(path_or_url)[0] or "image/jpeg"
    with open(path_or_url, "rb") as f:
        resp = requests.post(
            f"{API_BASE}/uploads/images",
            headers=auth_headers(api_key),
            files={"file": (os.path.basename(path_or_url), f, mime_type)},
            timeout=60,
        )
    resp.raise_for_status()
    data = resp.json()

    url = _find_url(data)
    if not url:
        print(
            f"Could not find an image URL in the upload response. Raw response:\n{json.dumps(data, indent=2)}",
            file=sys.stderr,
        )
        sys.exit(1)
    return url


def _find_url(obj):
    """Best-effort search for a URL string in a JSON response, since exact
    response shape may vary (url / data.url / data[0].url / image_url /
    result.images[0].url[0])."""
    if isinstance(obj, str) and obj.startswith("http"):
        return obj
    if isinstance(obj, dict):
        for key in ("url", "image_url", "video_url", "file_url"):
            if key in obj:
                found = _find_url(obj[key])
                if found:
                    return found
        for value in obj.values():
            found = _find_url(value)
            if found:
                return found
    if isinstance(obj, list):
        for item in obj:
            found = _find_url(item)
            if found:
                return found
    return None


def _find_status(obj):
    if isinstance(obj, dict):
        if "status" in obj and isinstance(obj["status"], str):
            return obj["status"].lower()
        for value in obj.values():
            found = _find_status(value)
            if found:
                return found
    if isinstance(obj, list):
        for item in obj:
            found = _find_status(item)
            if found:
                return found
    return None


def poll_task(api_key, task_id):
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    last_raw = None
    while time.time() < deadline:
        resp = requests.get(f"{API_BASE}/tasks/{task_id}", headers=auth_headers(api_key), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        last_raw = data

        status = _find_status(data)
        if status in ("completed", "success", "succeeded"):
            result_url = _find_url(data)
            if result_url:
                return result_url, None
            return None, f"Task completed but no result URL found. Raw:\n{json.dumps(data, indent=2)}"
        if status in ("failed", "error"):
            return None, f"Task failed. Raw:\n{json.dumps(data, indent=2)}"

        time.sleep(POLL_INTERVAL_SECONDS)

    return None, f"Timed out after {POLL_TIMEOUT_SECONDS}s. Last response:\n{json.dumps(last_raw, indent=2)}"


def poll_tasks_round_robin(api_key, pending):
    """Poll MANY tasks concurrently (one HTTP round-robin sweep per interval)
    instead of waiting out each task's full completion before even checking
    the next one. `pending` is {clip_id: task_id}. Returns {clip_id: (url, error)}.

    Real cost of the old one-at-a-time approach: apimart generates all
    submitted clips in parallel on its own side, but polling them via a
    `for clip in clips: poll_task(...)` loop serializes the WAIT -- clip 2
    isn't even checked until clip 1's task reaches a terminal state. For a
    14-clip campaign at ~3min/clip actually generating in parallel, that
    turned a ~3-5 minute wall-clock wait into 48 minutes (sum of every
    clip's time instead of the max). This function checks every still-pending
    task once per sweep, sleeps once, and repeats -- wall-clock time tracks
    the SLOWEST clip, not the sum of all of them.
    """
    results = {}
    remaining = dict(pending)
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    while remaining and time.time() < deadline:
        for clip_id, task_id in list(remaining.items()):
            resp = requests.get(f"{API_BASE}/tasks/{task_id}", headers=auth_headers(api_key), timeout=30)
            resp.raise_for_status()
            data = resp.json()
            status = _find_status(data)
            if status in ("completed", "success", "succeeded"):
                result_url = _find_url(data)
                if result_url:
                    results[clip_id] = (result_url, None)
                else:
                    results[clip_id] = (None, f"Task completed but no result URL found. Raw:\n{json.dumps(data, indent=2)}")
                del remaining[clip_id]
            elif status in ("failed", "error"):
                results[clip_id] = (None, f"Task failed. Raw:\n{json.dumps(data, indent=2)}")
                del remaining[clip_id]
        if remaining:
            time.sleep(POLL_INTERVAL_SECONDS)

    for clip_id, task_id in remaining.items():
        results[clip_id] = (None, f"Timed out after {POLL_TIMEOUT_SECONDS}s waiting for task {task_id}.")

    return results


def download(url, dest_path, retries=3):
    """A flaky network read here used to crash the entire `generate` run --
    real case: a ConnectionResetError partway through downloading one clip
    (out of 14, most already polled successfully) killed the whole process,
    discarding the completed polling work for every other clip. Retrying a
    transient read failure a few times is cheap; losing 10+ clips' worth of
    already-finished polling to one dropped connection is not."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            urllib.request.urlretrieve(url, dest_path)
            return
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
            last_error = e
            print(f"  download attempt {attempt}/{retries} failed ({e}), retrying...", file=sys.stderr)
            time.sleep(3)
    raise last_error


def is_valid_video(path):
    """A quick ffprobe duration read -- returns False for a missing, empty, or
    truncated/corrupt file (e.g. one left behind by a process killed mid-write).
    Used to make `generate` idempotent: a clip whose file already exists AND
    is valid is skipped entirely (no poll, no re-download, no re-trim) instead
    of unconditionally re-fetching every clip on every run. That unconditional
    re-fetch is what turned a "fix 2 clips" job into a "re-download all 27"
    job in practice -- much slower, and the extra runtime made it more likely
    a session boundary would kill the process mid-write, corrupting whichever
    file was in flight at that moment (a real, repeated failure mode)."""
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return False
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip()) > 0
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Clip merges: a short clip that keeps getting blocked by an apparent content-
# policy false positive (see the auto-retry in run_generate) gets merged into
# a neighboring clip of the same character instead of endlessly retried --
# matches the documented real-world fix in references/realism-playbook.md.
# The merge is recorded as an overlay (merges.json) on top of the untouched
# job.json, applied by apply_merges() at the top of every command that reads
# clips, so job.json stays a clean record of the original intent.
# ---------------------------------------------------------------------------


def _merges_path(output_dir):
    return os.path.join(output_dir, "merges.json")


def load_merges(output_dir):
    path = _merges_path(output_dir)
    if not os.path.isfile(path):
        return []
    with open(path) as f:
        return json.load(f)


def save_merges(output_dir, merges):
    with open(_merges_path(output_dir), "w") as f:
        json.dump(merges, f, indent=2, ensure_ascii=False)


def apply_merges(job):
    """Returns a copy of `job` with merged-away clips dropped and their dialogue
    folded into the clip they were merged into, per merges.json (if any)."""
    merges = load_merges(job["output_dir"])
    if not merges:
        return job
    job = dict(job)
    clips = [dict(c) for c in job["clips"]]
    by_id = {c["id"]: c for c in clips}
    drop_ids = set()
    for m in merges:
        drop_ids.add(m["drop"])
        target = by_id.get(m["into"])
        if target is not None:
            target["dialogue"] = m["merged_dialogue"]
    job["clips"] = [c for c in clips if c["id"] not in drop_ids]
    return job


def clear_clip_state(output_dir, clip_ids):
    """Removes the saved task_id and any local file(s) for the given clip ids,
    so the next `generate` treats them as never-submitted and resubmits fresh.
    Used by both `regenerate` and `merge-clips`."""
    clip_ids = set(clip_ids)
    task_ids_path = os.path.join(output_dir, "task_ids.json")
    if os.path.isfile(task_ids_path):
        with open(task_ids_path) as f:
            ids = {int(k): v for k, v in json.load(f).items()}
        for cid in clip_ids:
            ids.pop(cid, None)
        with open(task_ids_path, "w") as f:
            json.dump(ids, f, indent=2)
    clips_dir = os.path.join(output_dir, "clips")
    for cid in clip_ids:
        for suffix in (".mp4", ".raw.mp4"):
            p = os.path.join(clips_dir, f"clip_{cid:02d}{suffix}")
            if os.path.isfile(p):
                os.remove(p)


def _neighbor_same_character(clips, clip_id):
    """The next clip of the same character after `clip_id`, or the previous one
    if there's no next -- the natural merge target for a short blocked line."""
    ids = [c["id"] for c in clips]
    if clip_id not in ids:
        return None
    idx = ids.index(clip_id)
    char = clips[idx]["character"]
    for j in list(range(idx + 1, len(clips))) + list(range(idx - 1, -1, -1)):
        if clips[j]["character"] == char:
            return clips[j]["id"]
    return None


CONTENT_POLICY_RE = re.compile(r"content polic", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Video generation pipeline (the "generate" subcommand)
# ---------------------------------------------------------------------------


def _with_continuous_take(camera_realism):
    camera_realism = (camera_realism or "").strip()
    if camera_realism and "continuous take" not in camera_realism.lower() and "no cuts" not in camera_realism.lower():
        if not camera_realism.endswith((".", "!", "?")):
            camera_realism += "."
        camera_realism += f" {CONTINUOUS_TAKE_SUFFIX}"
    return camera_realism


def build_prompt(job, clip, character, is_first_for_character, has_multi_ref=False):
    """Assembles the final Veo 3.1 prompt.

    Two structurally different modes, per what references/avatarhype-library.md
    documents as proven technique:

    - Talking formats (selfie/talking_head/podcast/dual_cast): the avatar
      speaks on camera, Veo generates the voice. Built from reusable pieces
      (character's avatar/voice, shared camera/format setting) plus per-clip
      pieces (delivery, dialogue, optional visual_override for insert/POV
      shots, optional post_dialogue_action for a gesture during/after the
      line).
    - voiceover format: the avatar NEVER talks on camera (b-roll only, "no
      talking, mouth closed") -- the real narration is recorded separately
      and added in CapCut, matching the library's proven "voz en off"
      technique. Every clip needs a visual_override describing the action +
      setting; the clip's dialogue is narration text, not spoken audio, and
      is written to narration_script.txt instead of the Veo prompt.

    Reusing avatar_descriptor/voice_profile word-for-word per character, and
    camera_realism word-for-word across the whole job, is what keeps
    character/voice/setting consistent across separate generation calls --
    Veo has no memory between calls, so identical wording each time is the
    only real lever. A continuity phrase is prepended to every clip after a
    character's first appearance as an extra nudge in the same direction.
    "Single continuous take, no cuts or scene changes" is auto-appended to
    camera_realism if not already present -- without it Veo tends to insert
    an unwanted scene cut mid-clip.
    """
    camera_realism = _with_continuous_take(job.get("camera_realism"))

    if job.get("format") == "voiceover":
        visual = (clip.get("visual_override") or "").strip()
        if not visual:
            raise ValueError(
                f"Clip {clip['id']}: format 'voiceover' requires visual_override "
                "(the acción + sitio/luz for this b-roll shot) on every clip."
            )
        parts = []
        if camera_realism:
            parts.append(camera_realism)
        parts.append("cinematic, no talking.")
        parts.append("Keep the SAME person from the reference.")
        parts.append(visual)
        parts.append("No text, no watermark.")
        return " ".join(parts)

    if job.get("prompt_style", "v2") != "legacy":
        return prompting.build_prompt_v2(
            job, clip, character, CONTINUOUS_TAKE_SUFFIX, DEFAULT_ACCENT, has_multi_ref=has_multi_ref
        )

    # ---- legacy (v1) assembly: only reached with "prompt_style": "legacy" ----
    parts = []

    visual_override = clip.get("visual_override")
    no_face = clip.get("no_face", False)
    if visual_override:
        parts.append(visual_override.strip())
    else:
        parts.append(character["avatar_descriptor"].strip())

    pronoun = character.get("pronoun", "she").capitalize()

    voice_profile = character["voice_profile"].strip()
    accent = character.get("accent", DEFAULT_ACCENT)
    if "accent" not in voice_profile.lower() and "spanish" not in voice_profile.lower():
        voice_profile += f" {accent}"
    parts.append(voice_profile)

    if camera_realism:
        parts.append(camera_realism)

    delivery = clip["delivery"].strip()
    if not is_first_for_character:
        continuity = (
            "Continuing in the exact same voice as before, "
            if no_face
            else "Continuing as the same person, with the exact same voice and appearance as before, "
        )
        delivery = continuity + delivery[0].lower() + delivery[1:]
    parts.append(delivery)

    parts.append(f'{pronoun} says: "{clip["dialogue"].strip()}"')

    post_action = clip.get("post_dialogue_action")
    if post_action:
        parts.append(post_action.strip())

    if has_multi_ref:
        # Real, recurring failure mode when more than one avatar_images entry
        # is attached (e.g. photo + character sheet): Veo sometimes morphs
        # the shot -- often but not only in the last ~1s -- toward the
        # multi-image reference grid itself, visibly blending in a
        # ghosted/duplicated-face collage. trim_end() below is a post-hoc
        # safety net for whatever slips through, but this explicit negative
        # instruction is the first line of defense -- told twice, once
        # before and once after, because a single mention got dropped for a
        # some clips of a real ~27-clip campaign.
        parts.append(
            "The shot must show ONLY this one real person, normally and continuously, in a single "
            "unbroken take -- never a grid, contact sheet, collage, multiple angles, or duplicated/ghosted "
            "faces of her at any point, including the very end of the clip."
        )

    return " ".join(parts)


class InsufficientBalanceError(Exception):
    """Raised when apimart returns 402 Payment Required -- account is out of credits."""


def submit_video_clip(api_key, prompt, clip_id, image_urls, model, aspect_ratio, resolution):
    body = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
    }
    if image_urls:
        body["image_urls"] = image_urls

    resp = requests.post(
        f"{API_BASE}/videos/generations",
        headers={**auth_headers(api_key), "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    if resp.status_code == 402:
        raise InsufficientBalanceError(
            "apimart returned 402 Payment Required -- the account is out of credits. "
            "Top up at https://apimart.ai before retrying."
        )
    resp.raise_for_status()
    data = resp.json()

    try:
        return data["data"][0]["task_id"]
    except (KeyError, IndexError, TypeError):
        print(
            f"Unexpected response submitting clip {clip_id}. Raw response:\n{json.dumps(data, indent=2)}",
            file=sys.stderr,
        )
        return None


def trim_end(path, seconds=1.3):
    """Cut the last `seconds` off a clip in place. Used to strip the reference-image
    bleed-through Veo sometimes renders in the last ~1s of a clip when more than one
    avatar_images entry (e.g. reference photo + character sheet) was attached — the
    grid/sheet visibly fades in near the very end of the take. Re-encodes (not stream
    copy) so the cut lands exactly on the requested timestamp rather than the nearest
    keyframe."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        duration = float(probe.stdout.strip())
    except ValueError:
        print(f"  could not read duration for {path}, skipping trim", file=sys.stderr)
        return
    new_duration = max(duration - seconds, 1.0)
    tmp_path = path + ".trimmed.mp4"
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", path, "-t", f"{new_duration:.3f}",
         "-c:v", "libx264", "-c:a", "aac", tmp_path],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  trim failed for {path}, keeping untrimmed:\n{result.stderr}", file=sys.stderr)
        return
    os.replace(tmp_path, path)


def concat_clips(clip_paths, final_path):
    list_file = final_path + ".list.txt"
    with open(list_file, "w") as f:
        for path in clip_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")

    result = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", final_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Stream copy concat failed, retrying with re-encode...", file=sys.stderr)
        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
             "-c:v", "libx264", "-c:a", "aac", final_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"ffmpeg concat failed:\n{result.stderr}", file=sys.stderr)
            sys.exit(1)

    os.remove(list_file)


def report_lint(job):
    """Prints lint findings (free, no API call). Returns the number of errors."""
    issues = prompting.lint_job(job)
    for level, cid, msg in issues:
        where = f"clip {cid}" if cid is not None else "job"
        print(f"  [{level.upper()}] {where}: {msg}", file=sys.stderr if level == "error" else sys.stdout)
    if not issues:
        print("  lint: no issues found.")
    return sum(1 for level, _, _ in issues if level == "error")


def run_preview(args):
    """Dry run: assemble every prompt exactly as `generate` would, print them with
    word count and estimated speech time, run the lint. Submits nothing, costs nothing."""
    with open(args.config) as f:
        job = json.load(f)
    job = apply_merges(job)
    print(f"Prompt style: {job.get('prompt_style', 'v2')} | realism preset: "
          f"{prompting.resolve_realism(job)[0] if job.get('format') != 'voiceover' else 'n/a (voiceover)'}\n")
    seen = set()
    for clip in job["clips"]:
        character = job["characters"][clip["character"]]
        first = clip["character"] not in seen
        seen.add(clip["character"])
        refs = character.get("avatar_images", [])
        prompt = build_prompt(job, clip, character, first, has_multi_ref=not clip.get("no_face") and len(refs) > 1)
        secs = prompting.est_speech_seconds(clip.get("dialogue", ""), prompting.speech_wpm(job, character))
        print(f"=== clip {clip['id']} ({clip['character']}) | {prompting.count_words(prompt)} prompt words | ~{secs:.1f}s speech ===")
        print(prompt + "\n")
    print("Lint:")
    errors = report_lint(job)
    sys.exit(2 if errors else 0)


def run_generate(args):
    api_key = get_api_key()
    check_ffmpeg()

    with open(args.config) as f:
        job = json.load(f)
    job = apply_merges(job)

    if report_lint(job) and not getattr(args, "skip_lint", False):
        print("\nFix the errors above before spending anything (or re-run with --skip-lint to submit anyway).", file=sys.stderr)
        sys.exit(2)

    model = job.get("model", "veo3.1-fast")
    aspect_ratio = job.get("aspect_ratio", "9:16")
    resolution = job.get("resolution", "1080p")
    output_dir = job["output_dir"]
    clips_dir = os.path.join(output_dir, "clips")
    os.makedirs(clips_dir, exist_ok=True)

    task_ids_path = os.path.join(output_dir, "task_ids.json")
    task_ids = {}
    if os.path.isfile(task_ids_path):
        with open(task_ids_path) as f:
            # JSON object keys are always strings -- clip ids are ints everywhere else in this script.
            task_ids = {int(k): v for k, v in json.load(f).items()}

    clip_count = len(job["clips"])
    to_submit_count = len([c for c in job["clips"] if c["id"] not in task_ids])
    price = PRICE_PER_CLIP.get(model, 0)
    estimate = to_submit_count * price
    if task_ids:
        print(f"Resuming: {len(task_ids)} clip(s) already submitted previously (found in {task_ids_path}) -- will NOT resubmit or recharge those.")
    print(f"About to submit {to_submit_count} new clip(s) on {model} (~${price:.3f}/clip) — estimated cost ~${estimate:.2f} for this run.")
    if model == "veo3.1-quality" or estimate > 2.0:
        print("NOTE: this is a higher-cost run than the usual fast/small test — double check this is intentional.")

    characters = job["characters"]
    print(f"Uploading reference images for {len(characters)} character(s)...")
    # character_image_urls[char_id] is a dict of {variant_name: [urls]}. "default" is
    # always character["avatar_images"]; a character can optionally define extra named
    # "variants" (e.g. a second setting/outfit prepped with prep-reference) and a clip
    # picks one with "avatar_variant": "<name>" -- see references/realism-playbook.md
    # "Scene variety across a long campaign".
    character_image_urls = {}
    for char_id, character in characters.items():
        variants = {"default": character.get("avatar_images", [])}
        variants.update(character.get("variants", {}))
        character_image_urls[char_id] = {
            name: [upload_image(api_key, p) for p in paths] for name, paths in variants.items()
        }

    clips = job["clips"]

    if job.get("format") == "voiceover":
        narration_path = os.path.join(output_dir, "narration_script.txt")
        with open(narration_path, "w") as f:
            f.write(
                "Narration script -- the avatar never talks on camera in this format (proven\n"
                "technique from references/avatarhype-library.md). Record this yourself, or\n"
                "generate it as a separate voice track, and lay it over the silent clips in\n"
                "CapCut in this order.\n\n"
            )
            for clip in clips:
                f.write(f"[clip {clip['id']}] {clip['dialogue'].strip()}\n\n")
        print(f"Wrote narration script (avatar stays silent on camera): {narration_path}")

    prompts_path = os.path.join(output_dir, "prompts_used.json")

    seen_characters = set()
    prompts_log = {}
    freshly_submitted_ids = set()
    print(f"Submitting {to_submit_count} clip(s) to {model}...")
    stopped_early = False
    for clip in clips:
        char_id = clip["character"]
        character = characters[char_id]
        is_first_for_character = char_id not in seen_characters
        seen_characters.add(char_id)

        variant = clip.get("avatar_variant", "default")
        variant_urls = character_image_urls.get(char_id, {}).get(variant, [])
        has_multi_ref = not clip.get("no_face") and len(variant_urls) > 1
        prompt = build_prompt(job, clip, character, is_first_for_character, has_multi_ref=has_multi_ref)
        prompts_log[clip["id"]] = prompt
        with open(prompts_path, "w") as f:
            json.dump(prompts_log, f, indent=2, ensure_ascii=False)

        if clip["id"] in task_ids:
            print(f"  clip {clip['id']} ({char_id}): already submitted previously (task {task_ids[clip['id']]}), reusing")
            continue

        image_urls = [] if clip.get("no_face") else variant_urls
        try:
            task_id = submit_video_clip(api_key, prompt, clip["id"], image_urls, model, aspect_ratio, resolution)
        except InsufficientBalanceError as e:
            print(f"\n{e}", file=sys.stderr)
            # The clip that just raised InsufficientBalanceError was never
            # actually submitted/charged (the error fires before that), so it
            # belongs in "remaining" too -- excluding it used to leave a
            # permanent silent gap in the campaign on resume.
            remaining = [c["id"] for c in clips if c["id"] not in task_ids]
            print(
                f"Stopped early: {len(task_ids)} clip(s) already submitted (and likely already charged) are "
                f"saved in {task_ids_path} -- do NOT resubmit them, they'll be recovered from their task IDs "
                f"once there's balance again. Still need to submit: {remaining}",
                file=sys.stderr,
            )
            stopped_early = True
            break

        if task_id:
            task_ids[clip["id"]] = task_id
            freshly_submitted_ids.add(clip["id"])
            with open(task_ids_path, "w") as f:
                json.dump(task_ids, f, indent=2)
            print(f"  clip {clip['id']} ({char_id}): submitted (task {task_id})")
        else:
            print(f"  clip {clip['id']} ({char_id}): submission failed, skipping")

    if not task_ids:
        print("No clips were submitted, nothing to do.", file=sys.stderr)
        sys.exit(1)

    clips_by_id = {c["id"]: c for c in clips}

    print("Polling for completion (concurrent -- wall time tracks the slowest clip, not the sum of all of them)...")
    clip_paths = {}
    failures = []
    to_poll = {}
    for clip in clips:
        clip_id = clip["id"]
        if clip_id not in task_ids:
            failures.append((clip_id, "not submitted"))
            continue
        dest = os.path.join(clips_dir, f"clip_{clip_id:02d}.mp4")
        # Only skip the re-fetch for a clip that was REUSED (task_id already
        # existed before this run) -- a freshly submitted clip means the user
        # deliberately cleared its old task_id to regenerate it (e.g. to fix a
        # defect), and any file still sitting at `dest` is the STALE version
        # being replaced, not something to keep.
        if clip_id not in freshly_submitted_ids and is_valid_video(dest):
            print(f"  clip {clip_id}: already downloaded and valid, skipping re-fetch -> {dest}")
            clip_paths[clip_id] = dest
            continue
        to_poll[clip_id] = task_ids[clip_id]

    poll_results = poll_tasks_round_robin(api_key, to_poll) if to_poll else {}

    # Auto-retry ONCE any clip that failed on an apparent content-policy block.
    # Real case: a 7-word line got blocked twice with an unrelated-looking policy
    # message, credits_cost 0 both times, every other clip on the same avatar
    # passed fine -- a false positive that a clean retry usually resolves. Only
    # ever retried once per clip (tracked in policy_retries.json, persists across
    # resumed runs) -- a SECOND identical block means the line itself trips the
    # filter in isolation, and the fix is to merge it into a neighboring clip
    # (`merge-clips`), not to keep burning retries on the same input.
    policy_retries_path = os.path.join(output_dir, "policy_retries.json")
    policy_retries = {}
    if os.path.isfile(policy_retries_path):
        with open(policy_retries_path) as f:
            policy_retries = {int(k): v for k, v in json.load(f).items()}

    retry_ids = [
        cid for cid, (_, error) in poll_results.items()
        if error and CONTENT_POLICY_RE.search(error) and policy_retries.get(cid, 0) == 0
    ]
    if retry_ids:
        print(f"  {len(retry_ids)} clip(s) blocked by an apparent content-policy false positive -- retrying once: {retry_ids}")
        retry_to_poll = {}
        for cid in retry_ids:
            clip = clips_by_id[cid]
            variant = clip.get("avatar_variant", "default")
            image_urls = [] if clip.get("no_face") else character_image_urls.get(clip["character"], {}).get(variant, [])
            try:
                task_id = submit_video_clip(api_key, prompts_log[cid], cid, image_urls, model, aspect_ratio, resolution)
            except InsufficientBalanceError as e:
                print(f"  clip {cid}: retry skipped, out of balance ({e})", file=sys.stderr)
                task_id = None
            policy_retries[cid] = policy_retries.get(cid, 0) + 1
            if task_id:
                task_ids[cid] = task_id
                retry_to_poll[cid] = task_id
                with open(task_ids_path, "w") as f:
                    json.dump(task_ids, f, indent=2)
        if retry_to_poll:
            poll_results.update(poll_tasks_round_robin(api_key, retry_to_poll))
        with open(policy_retries_path, "w") as f:
            json.dump(policy_retries, f, indent=2)

    for clip_id, (video_url, error) in poll_results.items():
        if error:
            if CONTENT_POLICY_RE.search(error) and policy_retries.get(clip_id, 0) >= 1:
                neighbor = _neighbor_same_character(clips, clip_id)
                merge_hint = (
                    f"pipeline.py merge-clips --config {args.config} --drop {clip_id} --into {neighbor}"
                    if neighbor else "no other clip of this character to merge into -- rewrite the line instead"
                )
                error = (
                    "Blocked by content policy twice in a row (not charged either time). Per the documented "
                    "real-world pattern, this usually means the isolated short line itself trips the filter, "
                    f"not its content -- the fix is to merge it into a neighboring clip, not retry again: {merge_hint}"
                )
            print(f"  clip {clip_id}: FAILED — {error}", file=sys.stderr)
            failures.append((clip_id, error))
            continue
        dest = os.path.join(clips_dir, f"clip_{clip_id:02d}.mp4")
        try:
            download(video_url, dest)
        except Exception as e:
            # A persistent download failure on ONE clip used to crash the
            # whole run, discarding the already-completed polling results for
            # every other clip. Record it as a per-clip failure (same as a
            # generation error) and keep going -- re-running `generate`
            # afterward will resume just this one from its saved task_id.
            print(f"  clip {clip_id}: download FAILED after retries — {e}", file=sys.stderr)
            failures.append((clip_id, str(e)))
            continue
        stale_raw = dest[:-4] + ".raw.mp4"
        if os.path.isfile(stale_raw):
            os.remove(stale_raw)  # belongs to the version this download replaces
        # NOTE: no automatic post-trim here anymore, even for multi-ref clips.
        # A blanket "always trim 1.3s off the end" used to run here as a
        # preventive measure against reference-image bleed-through -- real
        # campaign data showed it doing more harm than good (4 of 14 clips in
        # one campaign had their trim slice into real dialogue, dropping the
        # last word entirely, while 0 of those 14 clips actually had visible
        # bleed-through). The prompt-level negative instruction in
        # build_prompt() is the real defense now. Bleed-through is real but
        # now rare enough with that prompt in place that a blanket trim isn't
        # worth the guaranteed risk of clipping real speech on every clip --
        # scan with scripts/scan_clip_endings.py after generating, and only
        # call trim_end() by hand on a clip that ACTUALLY shows the artifact.
        print(f"  clip {clip_id}: downloaded -> {dest}")
        clip_paths[clip_id] = dest

    if (job.get("format") != "voiceover" and job.get("trim_tails", True)
            and not getattr(args, "no_trim_tails", False) and clip_paths):
        print("Transcript QA + tail trim (cuts Veo's end-of-clip rumble at last word + margin; skips any clip whose transcript doesn't match its dialogue)...")
        report = tail_trim.process_clips(job, clips_dir, SKILL_DIR, only_ids=set(clip_paths))
        tail_trim.print_report(report)
        with open(os.path.join(output_dir, "clip_qa.json"), "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    clip_paths = [clip_paths[c["id"]] for c in clips if c["id"] in clip_paths]

    if not clip_paths:
        print("No clips succeeded, nothing to stitch.", file=sys.stderr)
        sys.exit(1)

    final_path = os.path.join(output_dir, "final_video.mp4")
    print(f"Stitching {len(clip_paths)} clip(s) into {final_path}...")
    concat_clips(clip_paths, final_path)

    cost = len(clip_paths) * PRICE_PER_CLIP.get(model, 0)
    print(f"\nDone. Final video: {final_path}")
    print(f"Estimated cost: {len(clip_paths)} clip(s) x ~${PRICE_PER_CLIP.get(model, 0):.3f} = ~${cost:.2f}")
    if failures:
        label = "clip(s) not yet submitted (ran out of balance mid-run)" if stopped_early else "clip(s) failed and were excluded from the final video"
        print(f"\n{len(failures)} {label}:")
        for clip_id, error in failures:
            print(f"  clip {clip_id}: {error.splitlines()[0]}")

    qa_report = {}
    qa_path = os.path.join(output_dir, "clip_qa.json")
    if os.path.isfile(qa_path):
        with open(qa_path) as f:
            qa_report = json.load(f)
    preset_name = prompting.resolve_realism(job)[0] if job.get("format") != "voiceover" else None
    campaign_log.auto_log(SKILL_DIR, job, model, len(clip_paths), cost, preset_name, clip_qa=qa_report)
    print(f"\nLogged to {campaign_log.log_path(SKILL_DIR)} -- add how it actually looked with:\n"
          f"  python3 {os.path.abspath(__file__)} log-campaign --config {args.config} --outcome \"...\"")


# ---------------------------------------------------------------------------
# Character sheet generation (the "character-sheet" subcommand, used for the
# "voiceover" format so Veo has multiple angles to stay consistent across
# varied scenes)
# ---------------------------------------------------------------------------


def generate_image(api_key, prompt, reference_image_paths, model="gpt-image-2", size="1:1", resolution="2k"):
    """Generic image generation via apimart's image API (upload references,
    submit, poll, return the result URL). Used for character sheets, and for
    any other one-off image need -- e.g. the library's "Segundo invitado"
    prompt for a consistent second podcast guest.
    """
    image_urls = [upload_image(api_key, p) for p in reference_image_paths]

    resp = requests.post(
        f"{API_BASE}/images/generations",
        headers={**auth_headers(api_key), "Content-Type": "application/json"},
        json={
            "model": model,
            "prompt": prompt,
            "image_urls": image_urls,
            "size": size,
            "resolution": resolution,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        task_id = data["data"][0]["task_id"]
    except (KeyError, IndexError, TypeError):
        print(f"Unexpected response. Raw:\n{json.dumps(data, indent=2)}", file=sys.stderr)
        sys.exit(1)

    print(f"Task {task_id} submitted, polling...")
    result_url, error = poll_task(api_key, task_id)
    if error:
        print(f"FAILED — {error}", file=sys.stderr)
        sys.exit(1)
    return result_url


def run_character_sheet(args):
    api_key = get_api_key()
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Generating character sheet ({args.model}, {price_label(args.model)})...")
    result_url = generate_image(api_key, CHARACTER_SHEET_PROMPT, [args.image], model=args.model)

    dest = os.path.join(args.output_dir, "character_sheet.png")
    download(result_url, dest)
    print(f"\nDone. Character sheet: {dest}")
    print(
        "For voiceover-format campaigns, add both the original reference photo\n"
        "and this sheet to that character's avatar_images (stays within the 3-image\n"
        "cap) so Veo has multiple angles to stay consistent across varied scenes."
    )


def run_trim_tails(args):
    """Transcript QA + tail trim on clips already downloaded in <output_dir>/clips (any past campaign)."""
    check_ffmpeg()
    with open(args.config) as f:
        job = json.load(f)
    job = apply_merges(job)
    clips_dir = os.path.join(job["output_dir"], "clips")
    report = tail_trim.process_clips(
        job, clips_dir, SKILL_DIR, margin_s=args.margin, dry_run=args.dry_run,
        only_ids=set(args.clips) if args.clips else None,
    )
    if not report:
        print("Nothing processed.")
        return
    tail_trim.print_report(report)
    if not args.dry_run:
        with open(os.path.join(job["output_dir"], "clip_qa.json"), "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    if args.restitch and not args.dry_run:
        paths = [os.path.join(clips_dir, f"clip_{c['id']:02d}.mp4") for c in job["clips"]]
        paths = [p for p in paths if os.path.isfile(p)]
        final_path = os.path.join(job["output_dir"], "final_video.mp4")
        concat_clips(paths, final_path)
        print(f"Re-stitched {len(paths)} clip(s) -> {final_path}")


def run_regenerate(args):
    """Clears local state (task_id + downloaded file) for the given clip ids and
    immediately re-runs `generate`, which then only resubmits those -- the rest of
    the campaign is untouched (same idempotent skip-logic as any other resume)."""
    with open(args.config) as f:
        job = json.load(f)
    job = apply_merges(job)
    valid_ids = {c["id"] for c in job["clips"]}
    ids = [i for i in args.clips if i in valid_ids]
    missing = sorted(set(args.clips) - valid_ids)
    if missing:
        print(f"clip(s) {missing} are not in the current clip list (already merged away, or never existed) -- skipping them.", file=sys.stderr)
    if not ids:
        print("Nothing to regenerate.", file=sys.stderr)
        sys.exit(1)
    clear_clip_state(job["output_dir"], ids)
    print(f"Cleared local state for clip(s) {ids} -- resubmitting just these now.")
    run_generate(args)


def run_merge_clips(args):
    """Folds a clip's dialogue into a neighboring clip of the same character and
    drops it from the campaign for good -- the documented fix for a short line
    that keeps tripping a content-policy false positive in isolation (see the
    auto-retry in run_generate). Invalidates the target clip's local state so the
    next `generate` resubmits it with the merged line; the dropped clip's own
    (already-paid) task/file, if any, is left alone -- harmless once excluded."""
    with open(args.config) as f:
        job = json.load(f)
    job = apply_merges(job)
    clips = job["clips"]
    by_id = {c["id"]: c for c in clips}
    if args.drop not in by_id:
        print(f"clip {args.drop} not found in the current (possibly already-merged) clip list.", file=sys.stderr)
        sys.exit(1)
    if args.into not in by_id:
        print(f"clip {args.into} not found in the current (possibly already-merged) clip list.", file=sys.stderr)
        sys.exit(1)
    drop_clip, into_clip = by_id[args.drop], by_id[args.into]
    if drop_clip["character"] != into_clip["character"] and not args.force:
        print(f"clip {args.drop} ({drop_clip['character']}) and clip {args.into} ({into_clip['character']}) "
              "are different characters -- merging their dialogue into one clip would put both lines in one "
              "person's mouth. Pass --force if that's really what you want.", file=sys.stderr)
        sys.exit(1)

    ids = [c["id"] for c in clips]
    idx_drop, idx_into = ids.index(args.drop), ids.index(args.into)
    merged = (f"{drop_clip['dialogue'].strip()} {into_clip['dialogue'].strip()}" if idx_drop < idx_into
              else f"{into_clip['dialogue'].strip()} {drop_clip['dialogue'].strip()}")

    character = job["characters"][into_clip["character"]]
    secs = prompting.est_speech_seconds(merged, prompting.speech_wpm(job, character))
    if secs > prompting.HARD_SPEECH_LIMIT_S and not args.force:
        print(f"Merged line would run ~{secs:.1f}s of speech, over the ~{prompting.HARD_SPEECH_LIMIT_S:.1f}s an 8s "
              "clip can hold -- it would just get cut or rushed again. Shorten one of the two lines, or pass "
              "--force to merge anyway.", file=sys.stderr)
        sys.exit(1)

    merges = [m for m in load_merges(job["output_dir"]) if m["drop"] != args.drop]
    merges.append({"drop": args.drop, "into": args.into, "merged_dialogue": merged})
    save_merges(job["output_dir"], merges)
    clear_clip_state(job["output_dir"], [args.into])
    print(f"Merged clip {args.drop} into clip {args.into}: \"{merged}\"")
    print(f"Clip {args.drop} is dropped from the campaign for good (recorded in {_merges_path(job['output_dir'])}).")

    if not args.no_generate:
        print(f"Regenerating clip {args.into} with the merged line now...")
        args.clips = [args.into]
        run_regenerate(args)
    else:
        print(f"Run `generate --config {args.config}` (or `regenerate --clips {args.into}`) when ready to submit it.")


def run_review(args):
    """Builds a whole-campaign START/MIDDLE/END contact sheet for the visual half
    of SKILL.md step 5b (anatomy glitches, identity drift, format/scene drift) --
    one image instead of opening every clip by hand. Free, local ffmpeg only."""
    with open(args.config) as f:
        job = json.load(f)
    job = apply_merges(job)
    clips_dir = os.path.join(job["output_dir"], "clips")
    prefix = args.out or os.path.join(job["output_dir"], "review")
    only_ids = set(args.clips) if args.clips else None
    written = review_clips.build_review_sheets(job, clips_dir, prefix, only_ids=only_ids)
    if not written:
        print("No downloaded clips found to review.", file=sys.stderr)
        sys.exit(1)
    print(f"Wrote {len(written)} review sheet(s):")
    for w in written:
        print(f"  {w}")
    print("Read each image yourself: check anatomy glitches, identity drift, and format/scene drift "
          "at the start, middle and end of every clip.")


def run_log_campaign(args):
    with open(args.config) as f:
        job = json.load(f)
    entry = campaign_log.add_outcome(SKILL_DIR, job["output_dir"], args.outcome)
    if entry:
        print(f"Logged outcome for '{entry['campaign_name']}': {args.outcome}")
    else:
        print("No log entry for this campaign yet -- run `generate` at least once first.", file=sys.stderr)
        sys.exit(1)


def run_show_log(args):
    entries = campaign_log.show(SKILL_DIR, keyword=args.keyword, limit=args.limit)
    if not entries:
        print("No campaigns logged yet.")
        return
    for e in entries:
        print(f"{e['timestamp']} | {e['campaign_name']} | {e['format']} | preset={e['realism_preset']} | "
              f"prepped_ref={e['reference_prepped']} | {e['clip_count']} clips | ${e['estimated_cost']:.2f} | "
              f"trimmed={e['clips_trimmed']} mismatch={e['clips_transcript_mismatch']}")
        if e.get("campaign_notes"):
            print(f"    notes: {e['campaign_notes']}")
        if e.get("outcome"):
            print(f"    outcome: {e['outcome']}")


REFERENCE_REALISM_PROMPT = """Using the reference image as the ONLY source of identity, recreate the exact same person as an authentic, unretouched phone photo.
Identity must stay identical: same face structure, eyes, nose, lips, jaw, hairstyle and hairline, skin tone, age, body proportions, tattoos, marks and outfit. Do NOT beautify, stylize or reinterpret.
Scene: {setting}
Composition: fills a full vertical 9:16 frame edge to edge with no bars or borders, head and upper torso, eye level, natural phone selfie framing with a slight wide-angle phone-lens perspective, room and background visible top to bottom.
Realism: natural skin with visible pores, fine facial hair, small blemishes and uneven tone, slight shine on forehead and nose, a few flyaway hairs; no retouching, no beauty filter, no skin smoothing, no airbrushed glow. Light from one believable source with natural falloff (one side of the face slightly brighter), slight phone-camera noise and mild compression, natural white balance.
Expression: relaxed and neutral, mouth closed, eyes looking into the lens, as if about to start talking.
{extra}No text, no watermark, no logo, no filters, no cinematic color grade."""


def run_prep_reference(args):
    """Realism pass on the avatar's reference photo. The reference dominates the look of
    every clip (Veo copies its skin, framing, aspect ratio and background), so an
    over-polished or wrong-shaped photo caps realism no matter how good the text prompt is."""
    api_key = get_api_key()
    os.makedirs(args.output_dir, exist_ok=True)
    prompt = REFERENCE_REALISM_PROMPT.format(
        setting=args.setting.strip(),
        extra=(args.extra.strip() + "\n") if args.extra else "",
    )
    print(f"Preparing realistic reference ({args.model}, {price_label(args.model)})...")
    result_url = generate_image(api_key, prompt, [args.image], model=args.model, size="9:16")
    dest = os.path.join(args.output_dir, args.filename)
    download(result_url, dest)
    print(f"\nDone: {dest}")
    print("Look at it before using it: same person? skin textured (not smooth)? full-bleed 9:16? setting as intended? "
          "Then point avatar_images at it and validate with ONE test clip.")


def run_generate_image(args):
    api_key = get_api_key()
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Generating image ({args.model}, {price_label(args.model)})...")
    result_url = generate_image(api_key, args.prompt, args.images or [], model=args.model, size=args.size)

    dest = os.path.join(args.output_dir, args.filename)
    download(result_url, dest)
    print(f"\nDone: {dest}")


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Run the full video ad pipeline from a job config")
    generate_parser.add_argument("--config", required=True, help="Path to job config JSON")
    generate_parser.add_argument("--skip-lint", action="store_true", help="Submit even if the pre-flight lint reports errors")
    generate_parser.set_defaults(func=run_generate)

    generate_parser.add_argument("--no-trim-tails", action="store_true", help="Skip the transcript QA + end-of-clip rumble trim")

    trim_parser = subparsers.add_parser("trim-tails", help="Transcript QA + cut the end-of-clip rumble on already-downloaded clips (uses AssemblyAI, pennies)")
    trim_parser.add_argument("--config", required=True, help="Path to the job config JSON (uses its output_dir and dialogue)")
    trim_parser.add_argument("--margin", type=float, default=None, help="Seconds kept after the last word (default 0.30, or job.tail_margin_s)")
    trim_parser.add_argument("--dry-run", action="store_true", help="Report what would be cut without touching any file")
    trim_parser.add_argument("--clips", nargs="*", type=int, help="Only these clip ids")
    trim_parser.add_argument("--restitch", action="store_true", help="Rebuild final_video.mp4 from the clips afterwards")
    trim_parser.set_defaults(func=run_trim_tails)

    preview_parser = subparsers.add_parser("preview", help="Dry run: print the exact prompts + lint for a job config. Costs nothing.")
    preview_parser.add_argument("--config", required=True, help="Path to job config JSON")
    preview_parser.set_defaults(func=run_preview)

    regen_parser = subparsers.add_parser("regenerate", help="Clear local state for specific clip ids and resubmit just those")
    regen_parser.add_argument("--config", required=True, help="Path to job config JSON")
    regen_parser.add_argument("--clips", nargs="+", type=int, required=True, help="Clip id(s) to regenerate")
    regen_parser.add_argument("--skip-lint", action="store_true", help="Submit even if the pre-flight lint reports errors")
    regen_parser.add_argument("--no-trim-tails", action="store_true", help="Skip the transcript QA + end-of-clip rumble trim")
    regen_parser.set_defaults(func=run_regenerate)

    merge_parser = subparsers.add_parser("merge-clips", help="Fold a repeatedly content-policy-blocked short clip's line into a neighboring clip and drop it for good")
    merge_parser.add_argument("--config", required=True, help="Path to job config JSON")
    merge_parser.add_argument("--drop", type=int, required=True, help="Clip id to remove (its dialogue gets folded into --into)")
    merge_parser.add_argument("--into", type=int, required=True, help="Clip id to merge the dialogue into")
    merge_parser.add_argument("--force", action="store_true", help="Merge even across different characters, or over the speech-time budget")
    merge_parser.add_argument("--no-generate", action="store_true", help="Only record the merge; don't resubmit the target clip now")
    merge_parser.add_argument("--skip-lint", action="store_true")
    merge_parser.add_argument("--no-trim-tails", action="store_true")
    merge_parser.set_defaults(func=run_merge_clips)

    review_parser = subparsers.add_parser("review", help="Build a whole-campaign START/MIDDLE/END contact sheet for visual self-review (free, local)")
    review_parser.add_argument("--config", required=True, help="Path to job config JSON")
    review_parser.add_argument("--out", default=None, help="Output path prefix (default: <output_dir>/review)")
    review_parser.add_argument("--clips", nargs="*", type=int, help="Only these clip ids")
    review_parser.set_defaults(func=run_review)

    log_parser = subparsers.add_parser("log-campaign", help="Record how a campaign actually looked after self-review, in the cross-campaign log")
    log_parser.add_argument("--config", required=True, help="Path to job config JSON")
    log_parser.add_argument("--outcome", required=True, help="Free-text verdict, e.g. 'skin still too smooth, use prep-reference next time'")
    log_parser.set_defaults(func=run_log_campaign)

    showlog_parser = subparsers.add_parser("show-log", help="Print the cross-campaign learning log (read before starting a new campaign with a reused avatar)")
    showlog_parser.add_argument("--keyword", default=None, help="Filter entries containing this text (e.g. an avatar or campaign name)")
    showlog_parser.add_argument("--limit", type=int, default=15, help="Max entries to show (default 15, most recent)")
    showlog_parser.set_defaults(func=run_show_log)

    prep_parser = subparsers.add_parser("prep-reference", help="Realism pass on an avatar reference photo (unretouched phone-photo look, full-bleed 9:16, chosen setting)")
    prep_parser.add_argument("--image", required=True, help="Path to the original reference photo")
    prep_parser.add_argument("--setting", required=True, help="Positive description of the ONE setting + light, e.g. 'standing in a lived-in living room, beige wall behind, daylight from a window on the left'")
    prep_parser.add_argument("--extra", default="", help="Optional extra instruction line (outfit change, hair, etc.)")
    prep_parser.add_argument("--output-dir", required=True, help="Directory to save the result")
    prep_parser.add_argument("--filename", default="ref_realistic_9x16.png", help="Output filename")
    prep_parser.add_argument("--model", default="gpt-image-2", choices=list(PRICE_PER_IMAGE), help="Image model (default gpt-image-2)")
    prep_parser.set_defaults(func=run_prep_reference)

    sheet_parser = subparsers.add_parser("character-sheet", help="Generate a 3x3 character sheet from a reference image")
    sheet_parser.add_argument("--image", required=True, help="Path to the reference image")
    sheet_parser.add_argument("--output-dir", required=True, help="Directory to save character_sheet.png")
    sheet_parser.add_argument("--model", default="gpt-image-2", choices=list(PRICE_PER_IMAGE), help="Image model (default gpt-image-2)")
    sheet_parser.set_defaults(func=run_character_sheet)

    image_parser = subparsers.add_parser("generate-image", help="Generate one image from a prompt + optional reference images (e.g. the library's 'Segundo invitado' prompt)")
    image_parser.add_argument("--prompt", required=True, help="Full image generation prompt")
    image_parser.add_argument("--images", nargs="*", default=[], help="Reference image path(s), 0-3")
    image_parser.add_argument("--output-dir", required=True, help="Directory to save the result")
    image_parser.add_argument("--filename", default="generated.png", help="Output filename (default generated.png)")
    image_parser.add_argument("--model", default="gpt-image-2", help="Image model (default gpt-image-2). Any apimart image model works; for the most natural-looking avatar photos use gpt-image-2.5-flare")
    image_parser.add_argument("--size", default="1:1", help="Output aspect ratio, e.g. '1:1' (default -- fine for character sheets), '9:16' (use this when fixing/creating a reference photo meant to fill a vertical video frame -- see SKILL.md's letterbox-bars note)")
    image_parser.set_defaults(func=run_generate_image)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
