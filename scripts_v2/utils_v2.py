import json
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))


def project_path(*parts):
    return PROJECT.joinpath(*parts)


def read_json(path):
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_config():
    import yaml

    path = PROJECT / "config_v2.yaml"
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def rel(path):
    path = Path(path)
    try:
        return path.resolve().relative_to(PROJECT.resolve()).as_posix()
    except ValueError:
        return str(path)


def fail_if_missing(path, label):
    path = PROJECT / path if not Path(path).is_absolute() else Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{label} missing: {path}")
    return path


def require_audit_first():
    audit = PROJECT / "outputs/v2/audit/V2_INPUT_AUDIT.md"
    if not audit.exists():
        raise SystemExit("Run scripts_v2/00_audit_project.py before this module.")
