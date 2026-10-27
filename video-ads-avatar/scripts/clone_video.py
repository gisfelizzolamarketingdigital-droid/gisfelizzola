#!/usr/bin/env python3
"""Clone a video with other avatars: same gestures, same rhythm, different person (apimart / Kling Motion Control).

You give it ONE reference video (a clip that already works) and one or more avatar photos. For every photo it
generates the same performance — hand gestures, head and face movement — with that person, in that person's own
setting. The original audio is NOT carried over (lips follow the original speech, so overlay your own voice-over,
or use it as a silent "this is how one video becomes many" demo).

  python3 clone_video.py --video original.mp4 --avatars valeria.png andres.png camila.png --out-dir clones/
  python3 clone_video.py --video original.mp4 --avatars ana.png --names Ana --who woman --out-dir clones/
  python3 clone_video.py --video-url https://.../original.mp4 --avatars ana.png --out-dir clones/ --dry-run

Cost (measured 2026-10): ~US$0.40 per 7-8 s clip in std mode (720p). --dry-run prints the estimate and exits.

PRIVACY: apimart cannot host video, so a LOCAL --video is uploaded to a temporary public host (litterbox.catbox.moe,
auto-deleted after 24 h) to get a URL. The agent running this script must ask the user before using --video; if
the video must not leave the machine, host it yourself and pass --video-url.
"""
import argparse, json, os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline as p  # noqa: E402  (reuses the apimart key loading, image upload, polling and download)
import requests  # noqa: E402

LITTERBOX = "https://litterbox.catbox.moe/resources/internals/api.php"
MODEL = "kling-v2-6-motion-control"   # kling-v3-motion-control gave a near-identical result in tests


def duration_s(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                             capture_output=True, text=True).stdout.strip()
        return float(out)
    except Exception:
        return None


def host_video(path):
    with open(path, "rb") as f:
        r = requests.post(LITTERBOX, data={"reqtype": "fileupload", "time": "24h"}, files={"fileToUpload": f},
                          headers={"User-Agent": "curl/8.7.1"}, timeout=300)   # the host rejects python-requests' default UA (HTTP 412)
    url = r.text.strip()
    if not url.startswith("http"):
        sys.exit(f"Could not host the video temporarily ({r.status_code}): {url[:200]}")
    return url


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", help="local reference video (mp4/mov, ideally 3-10 s) — uploaded to a temporary public host")
    src.add_argument("--video-url", help="already-public URL of the reference video")
    ap.add_argument("--avatars", nargs="+", required=True, help="one photo per avatar (full-bleed vertical selfie works best)")
    ap.add_argument("--names", nargs="*", help="output names, same order as --avatars (default: file names)")
    ap.add_argument("--who", default="person", help="'woman' / 'man' / 'person' — used in the prompt")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--mode", default="std", choices=["std", "pro"])
    ap.add_argument("--prompt", help="override the default prompt")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and the estimated cost, spend nothing")
    a = ap.parse_args()

    names = a.names or [os.path.splitext(os.path.basename(x))[0] for x in a.avatars]
    if len(names) != len(a.avatars):
        sys.exit("--names needs one name per avatar")
    dur = duration_s(a.video) if a.video else None
    est = 0.40 * len(a.avatars) * (1 if not dur or dur <= 8 else dur / 8) * (1.6 if a.mode == "pro" else 1)
    print(f"{len(a.avatars)} clone(s) with {a.model} ({a.mode})" + (f", reference {dur:.1f}s" if dur else "") + f" — estimated cost ~US${est:.2f}")
    if dur and dur > 30:
        sys.exit("The reference video is longer than 30 s; cut it first.")
    if a.dry_run:
        return

    key = p.get_api_key()
    H = {**p.auth_headers(key), "Content-Type": "application/json"}
    vid = a.video_url or host_video(a.video)
    print("reference video:", vid)
    os.makedirs(a.out_dir, exist_ok=True)
    tasks = {}
    for name, img in zip(names, a.avatars):
        url = p.upload_image(key, img)
        prompt = a.prompt or (
            f"The {a.who} from the reference image, in their own real surroundings from the image, talks to camera in a handheld "
            "phone selfie, copying exactly the gestures, hand movements, head movements and facial expressions of the reference video. "
            "Natural phone-camera look, realistic skin, no filters.")
        body = {"model": a.model, "prompt": prompt, "image_url": url, "video_url": vid, "keep_original_sound": "no",
                "character_orientation": "video", "mode": a.mode, "watermark_info": {"enabled": False}}
        r = requests.post(f"{p.API_BASE}/videos/generations", headers=H, json=body, timeout=60)
        if r.status_code == 402:
            sys.exit("apimart: out of credits (402). Top up at https://apimart.ai")
        try:
            tasks[name] = r.json()["data"][0]["task_id"]; print(f"  {name}: submitted {tasks[name]}")
        except Exception:
            print(f"  {name}: FAILED to submit -> {r.status_code} {r.text[:300]}")
    if not tasks:
        sys.exit(1)
    res = p.poll_tasks_round_robin(key, tasks)
    ok = 0
    for name, (url, err) in res.items():
        if url:
            dest = os.path.join(a.out_dir, f"clone_{name}.mp4"); p.download(url, dest); ok += 1; print("  ok", dest)
        else:
            print(f"  FAIL {name}: {(err or '')[:300]}")
    print(f"\nDone: {ok}/{len(tasks)} clones in {a.out_dir}. Clip length matches the reference; audio is silent.")


if __name__ == "__main__":
    main()
