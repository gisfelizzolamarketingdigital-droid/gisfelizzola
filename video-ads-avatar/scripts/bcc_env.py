"""API keys of the Black Ads AI live in ONE persistent file: ~/.bcc-toolkit/.env  (Windows: C:\\Users\\<you>\\.bcc-toolkit\\.env).

Why: Claude Code replaces the plugin folder on every update, so a .env saved inside the plugin folder disappears
when the toolkit updates. The home-folder file survives updates and is shared by all the toolkit's skills.

Importing this module (every script that needs a key does) fills os.environ from, in this order of priority:
  1. variables already set in the environment (never overridden),
  2. ~/.bcc-toolkit/.env,
  3. the skills' own .env files next to the scripts (old layout, still honoured).
First run after an update: if ~/.bcc-toolkit/.env does not exist yet, it is created from the .env files of older plugin
versions still on disk (~/.claude/plugins/cache/**), so nobody has to retype their keys. Values are never printed.
Placeholders ("pega-aqui-...") are ignored.
"""
import glob, os

HOME_DIR = os.path.join(os.path.expanduser("~"), ".bcc-toolkit")
ENV_PATH = os.path.join(HOME_DIR, ".env")
SKILLS = ("video-ads-avatar", "editar-anuncios")
_THIS_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SKILLS_ROOT = os.path.dirname(_THIS_SKILL)


def _parse(path):
    values = {}
    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                values[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return values


def _real(v):
    return bool(v) and not v.lower().startswith("pega-aqui") and v.lower() not in ("changeme", "your-key")


def _migrate_from_plugin_cache():
    """Collect real keys from .env files of any toolkit version left in the plugin cache and save them persistently."""
    found = {}
    cache = os.path.join(os.path.expanduser("~"), ".claude", "plugins", "cache")
    paths = []
    for skill in SKILLS:
        paths += glob.glob(os.path.join(cache, "**", skill, ".env"), recursive=True)
    for p in sorted(paths, key=lambda x: os.path.getmtime(x)):      # newest wins
        for k, v in _parse(p).items():
            if _real(v):
                found[k] = v
    if found:
        try:
            os.makedirs(HOME_DIR, exist_ok=True)
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.write("# API keys of the Black Ads AI (private: never share or upload this file)\n")
                for k, v in found.items():
                    f.write(f"{k}={v}\n")
            try:
                os.chmod(ENV_PATH, 0o600)
            except OSError:
                pass
        except OSError:
            pass
    return found


def load():
    values = {}
    for skill in SKILLS:                                               # old layout (lowest priority)
        values.update({k: v for k, v in _parse(os.path.join(_SKILLS_ROOT, skill, ".env")).items() if _real(v)})
    if not os.path.isfile(ENV_PATH):
        values.update(_migrate_from_plugin_cache())
    values.update({k: v for k, v in _parse(ENV_PATH).items() if _real(v)})   # persistent file wins over old layout
    for k, v in values.items():
        os.environ.setdefault(k, v)
    return values


load()
