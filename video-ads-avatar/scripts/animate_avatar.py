#!/usr/bin/env python3
"""Bring avatar photos to life in SILENCE: blinks, a smile forming, a glance, a hand to the glasses/cap.

Use it for the "people" shots of an ad (montage of faces, a wall of avatars, b-roll of a person) — NOT for talking
avatars (that is pipeline.py generate). Each photo becomes one ~8 s vertical clip, no voice, no music.

  python3 animate_avatar.py --images valeria.png andres.png camila.png --out-dir clips/
  python3 animate_avatar.py --images a.png --names ana --action "she laughs silently and tucks her hair" --out-dir clips/
  python3 animate_avatar.py --images a.png b.png --model veo3.1-fast --out-dir clips/    # Veo first, Seedance if Veo's safety filter refuses

Models (apimart, measured 2026-10):
  seedance-2.0-mini  default. ~US$0.16 / 8 s, 720p, passes the face filter, natural motion.
  veo3.1-fast        ~US$0.08 / 8 s, 1080p, sharper — but its safety filter refused 5 of 6 realistic faces in tests.
                     Refusals cost nothing; with --model veo3.1-fast they are retried automatically with --fallback.
"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline as p  # noqa: E402
import requests  # noqa: E402

DEFAULT_ACTIONS = [
    "a slow natural blink, a small warm smile slowly forming, a glance to the side as if something caught their attention, then back to the lens, a hand tucks a strand of hair behind the ear",
    "a slight confident nod, eyebrows lift once, a small exhale through the nose with a half-smile, a finger adjusts the glasses or collar, then looks back at the lens",
    "a light silent laugh with a bright smile, a small head tilt, a glance at the phone screen then back at the lens, a quick natural blink",
    "a slow confident nod, a half-smile, one eyebrow rises, a brief look off to the side, then back to the lens with a calm look",
    "a warm friendly smile, a gentle nod, a hand pushes the glasses or hair back, a natural blink and a small tilt of the head",
    "a slight squint at the sunlight, the smile grows, a hand adjusts the cap or hair, then a straight look at the lens",
]


def build_prompt(desc, action):
    return (f"Subject: {desc} Same person, outfit, hairstyle, room and light as in the reference image.\n"
            "Camera: front-camera selfie held at arm's length: natural hand tremor, tiny reframing drift, slight autofocus and exposure breathing, "
            "mild wide-angle lens, no gimbal smoothness. Single continuous take, no cuts or scene changes.\n"
            "Look: one believable light source, natural contrast, real unretouched skin with visible pores and small imperfections, no beauty filter. "
            "Eyes with catchlights, natural blinks and small gaze shifts. Phone-camera look: mild sharpening and compression, natural white balance, no filters.\n"
            f"Performance: completely silent, mouth closed, no talking. {action}. Visible breathing, slight head and shoulder sway, clothing folding "
            "as the person moves; one hand holds the phone out of frame, exactly two hands, five fingers each.\n"
            "Audio: only faint natural ambient room sound, no music, no voices, no speech.\n"
            "No subtitles, captions, on-screen text, watermark or logo; no extra people.")


def submit(key, model, prompt, img_url):
    H = {**p.auth_headers(key), "Content-Type": "application/json"}
    if model.startswith("seedance"):
        body = {"model": model, "prompt": prompt, "duration": 8, "size": "9:16", "resolution": "720p", "generate_audio": False, "image_urls": [img_url]}
    else:
        body = {"model": model, "prompt": prompt, "aspect_ratio": "9:16", "resolution": "1080p", "image_urls": [img_url]}
    r = requests.post(f"{p.API_BASE}/videos/generations", headers=H, json=body, timeout=60)
    if r.status_code == 402:
        sys.exit("apimart: out of credits (402). Top up at https://apimart.ai")
    try:
        return r.json()["data"][0]["task_id"]
    except Exception:
        print(f"  submit failed ({r.status_code}): {r.text[:250]}"); return None


def run_batch(key, model, jobs, out_dir):
    """jobs: {name: (prompt, img_url)} -> returns the names that failed."""
    tasks = {}
    for name, (prompt, img_url) in jobs.items():
        t = submit(key, model, prompt, img_url)
        if t: tasks[name] = t; print(f"  {name}: {model} submitted")
    res = p.poll_tasks_round_robin(key, tasks) if tasks else {}
    failed = [n for n in jobs if n not in tasks]
    for name, (url, err) in res.items():
        if url:
            dest = os.path.join(out_dir, f"{name}.mp4"); p.download(url, dest); print("  ok", dest)
        else:
            why = "content-safety refusal" if err and "safety" in err.lower() else "failed"
            print(f"  {name}: {why} ({model})"); failed.append(name)
    return failed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", nargs="+", required=True)
    ap.add_argument("--names", nargs="*")
    ap.add_argument("--descs", nargs="*", help="one short description per image (age, look, setting) — helps keep identity; optional")
    ap.add_argument("--action", help="the same silent action for every clip (default: a different natural one per avatar)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--model", default="seedance-2.0-mini")
    ap.add_argument("--fallback", default="seedance-2.0-mini", help="model to retry with when --model refuses a face")
    a = ap.parse_args()

    names = a.names or [os.path.splitext(os.path.basename(x))[0] for x in a.images]
    if len(names) != len(a.images):
        sys.exit("--names needs one name per image")
    os.makedirs(a.out_dir, exist_ok=True)
    key = p.get_api_key()
    jobs = {}
    for i, (name, img) in enumerate(zip(names, a.images)):
        desc = (a.descs[i] if a.descs and i < len(a.descs) else "The person in the reference image.")
        jobs[name] = (build_prompt(desc, a.action or DEFAULT_ACTIONS[i % len(DEFAULT_ACTIONS)]), p.upload_image(key, img))
    failed = run_batch(key, a.model, jobs, a.out_dir)
    if failed and a.fallback and a.fallback != a.model:
        print(f"Retrying {len(failed)} with {a.fallback}...")
        failed = run_batch(key, a.fallback, {n: jobs[n] for n in failed}, a.out_dir)
    print("\nDone." if not failed else f"\nStill failing: {failed}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
