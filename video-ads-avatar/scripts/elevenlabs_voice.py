#!/usr/bin/env python3
"""
Real voice cloning via ElevenLabs -- used when a descriptive voice_profile
fed to Veo (see pipeline.py) isn't close enough to a specific real voice
(e.g. matching the exact narrator of a source video the user wants to add a
CTA to). Two independent steps, each usable on its own:

    python3 elevenlabs_voice.py clone-voice --name "narrador-x" --samples ref1.wav [ref2.wav ...] --output-dir out/
    python3 elevenlabs_voice.py generate-speech --voice-id <id> --text "..." --output out/narration.mp3

Unlike apimart/Veo, ElevenLabs generates audio ONLY (no video, no per-clip
duration cap) -- the matching visual (b-roll, Ken Burns over AI images, etc.)
is built separately and combined with this narration track in editar-anuncios.
"""

import argparse
import json
import os
import sys

import requests

API_BASE = "https://api.elevenlabs.io/v1"
import bcc_env  # keys live in ~/.bcc-toolkit/.env (they survive plugin updates); the skill's own .env is still honoured
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = bcc_env.ENV_PATH   # messages point at the persistent file


def load_env_file(path):
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
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        key = load_env_file(ENV_FILE).get("ELEVENLABS_API_KEY")

    if key in (None, "", "pega-aqui-tu-key-de-elevenlabs"):
        print(
            f"ELEVENLABS_API_KEY is not set.\n\n"
            f"Open this file:\n  {ENV_FILE}\n"
            "and replace the placeholder with your real key, e.g.:\n"
            "  ELEVENLABS_API_KEY=xi-xxxxxxxxxxxxxxxx\n\n"
            "Get your key from https://elevenlabs.io/app/settings/api-keys",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def run_clone_voice(args):
    api_key = get_api_key()

    for path in args.samples:
        if not os.path.isfile(path):
            print(f"Sample not found: {path}", file=sys.stderr)
            sys.exit(1)

    files = [("files", (os.path.basename(p), open(p, "rb"))) for p in args.samples]
    data = {"name": args.name, "remove_background_noise": "true"}
    if args.description:
        data["description"] = args.description

    resp = requests.post(
        f"{API_BASE}/voices/add",
        headers={"xi-api-key": api_key},
        data=data,
        files=files,
        timeout=120,
    )
    for _, (_, fh) in files:
        fh.close()

    if resp.status_code != 200:
        print(f"ElevenLabs returned {resp.status_code}:\n{resp.text}", file=sys.stderr)
        sys.exit(1)

    result = resp.json()
    voice_id = result.get("voice_id")
    if not voice_id:
        print(f"Unexpected response, no voice_id found:\n{json.dumps(result, indent=2)}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    dest = os.path.join(args.output_dir, "voice_clone.json")
    with open(dest, "w") as f:
        json.dump({"voice_id": voice_id, "name": args.name, "samples": args.samples}, f, indent=2)

    print(f"Cloned voice '{args.name}' -> voice_id: {voice_id}")
    if result.get("requires_verification"):
        print("NOTE: ElevenLabs flagged this voice as requiring verification -- check the account dashboard.")
    print(f"Saved to {dest} -- pass this voice_id to generate-speech.")


def run_generate_speech(args):
    api_key = get_api_key()

    if args.text_file:
        with open(args.text_file) as f:
            text = f.read().strip()
    else:
        text = args.text

    if not text:
        print("No text provided (use --text or --text-file).", file=sys.stderr)
        sys.exit(1)

    body = {
        "text": text,
        "model_id": args.model,
        "voice_settings": {
            "stability": args.stability,
            "similarity_boost": args.similarity_boost,
        },
    }

    resp = requests.post(
        f"{API_BASE}/text-to-speech/{args.voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json=body,
        params={"output_format": "mp3_44100_128"},
        timeout=120,
    )
    if resp.status_code != 200:
        print(f"ElevenLabs returned {resp.status_code}:\n{resp.text}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "wb") as f:
        f.write(resp.content)

    print(f"Done. Narration audio: {args.output}")


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    clone_parser = subparsers.add_parser("clone-voice", help="Create an Instant Voice Clone from audio sample(s)")
    clone_parser.add_argument("--name", required=True, help="Label for this voice in the ElevenLabs dashboard")
    clone_parser.add_argument("--samples", nargs="+", required=True, help="1+ clean audio file(s) of the target voice (wav/mp3)")
    clone_parser.add_argument("--description", default=None)
    clone_parser.add_argument("--output-dir", required=True, help="Where to save voice_clone.json (voice_id)")
    clone_parser.set_defaults(func=run_clone_voice)

    speech_parser = subparsers.add_parser("generate-speech", help="Synthesize speech text in a cloned/library voice")
    speech_parser.add_argument("--voice-id", required=True)
    speech_parser.add_argument("--text", default=None)
    speech_parser.add_argument("--text-file", default=None)
    speech_parser.add_argument("--output", required=True, help="Output audio path (.mp3)")
    speech_parser.add_argument("--model", default="eleven_multilingual_v2", help="Default supports Spanish")
    speech_parser.add_argument("--stability", type=float, default=0.5, help="Lower = more emotional range, higher = more consistent/monotone")
    speech_parser.add_argument("--similarity-boost", type=float, default=0.8, help="How closely to stick to the cloned voice's timbre")
    speech_parser.set_defaults(func=run_generate_speech)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
