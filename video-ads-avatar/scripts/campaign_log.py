"""
Cross-campaign learning log. A flat JSON list at <skill_dir>/campaign_log.json,
one entry per `generate` run, so the next campaign with the same (or a similar)
avatar doesn't start from zero -- read it before writing a new job config for
an avatar that has run before.

Auto-logged (objective, from the run itself): campaign name, format, realism
preset, whether the reference was prepped, clip count, cost, and a summary of
the transcript QA / tail-trim results (mismatches, trims applied). Optional
free-text `campaign_notes` in the job config is carried over verbatim -- put
observations there while writing the job (e.g. "reusing avatar from the
arcangeles campaign, worked well").

Subjective outcome (how it actually looked after self-review) is added
afterward with `pipeline.py log-campaign --config job.json --outcome "..."`,
since only a human/visual review can judge that -- the auto-entry alone is not
a verdict.
"""

import json
import os
import time


def log_path(skill_dir):
    return os.path.join(skill_dir, "campaign_log.json")


def _load(skill_dir):
    path = log_path(skill_dir)
    if not os.path.isfile(path):
        return []
    with open(path) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save(skill_dir, entries):
    with open(log_path(skill_dir), "w") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def auto_log(skill_dir, job, model, clip_paths_count, cost, realism_preset, clip_qa=None):
    """Called at the end of a `generate` run. Appends one entry; safe to call
    repeatedly for the same campaign (e.g. on resume) -- updates the latest
    entry for that output_dir instead of duplicating it."""
    entries = _load(skill_dir)
    trimmed = mismatched = 0
    for e in (clip_qa or {}).values():
        status = e.get("status", "")
        if status.startswith("cut "):
            trimmed += 1
        elif "NOT trimmed" in status:
            mismatched += 1

    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "campaign_name": job.get("campaign_name"),
        "output_dir": job.get("output_dir"),
        "format": job.get("format"),
        "model": model,
        "realism_preset": realism_preset,
        "reference_prepped": bool(job.get("reference_prepped", False)),
        "clip_count": clip_paths_count,
        "estimated_cost": round(cost, 3),
        "clips_trimmed": trimmed,
        "clips_transcript_mismatch": mismatched,
        "campaign_notes": job.get("campaign_notes"),
        "outcome": None,
    }
    entries = [e for e in entries if e.get("output_dir") != entry["output_dir"]]
    entries.append(entry)
    _save(skill_dir, entries)
    return entry


def add_outcome(skill_dir, output_dir, outcome):
    entries = _load(skill_dir)
    for e in entries:
        if e.get("output_dir") == output_dir:
            e["outcome"] = outcome
            _save(skill_dir, entries)
            return e
    return None


def show(skill_dir, keyword=None, limit=15):
    entries = _load(skill_dir)
    if keyword:
        kw = keyword.lower()
        entries = [
            e for e in entries
            if kw in json.dumps(e, ensure_ascii=False).lower()
        ]
    return entries[-limit:]
