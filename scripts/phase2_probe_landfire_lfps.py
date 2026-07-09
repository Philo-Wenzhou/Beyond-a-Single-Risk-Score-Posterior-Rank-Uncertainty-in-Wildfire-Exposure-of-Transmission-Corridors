import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import requests

from phase2_data_config import DIRS, ensure_phase2_dirs


BASE = "https://lfps.usgs.gov"


def main():
    ensure_phase2_dirs()
    raw = DIRS["raw_landfire"]
    js_dir = raw / "lfps_js"
    js_dir.mkdir(parents=True, exist_ok=True)

    html_path = raw / "lfps_home.html"
    if not html_path.exists():
        html = requests.get(BASE, timeout=60).text
        html_path.write_text(html, encoding="utf-8")
    else:
        html = html_path.read_text(encoding="utf-8")

    js_urls = sorted(set(re.findall(r'src="([^"]+\.js)"', html)))
    saved = []
    for url in js_urls:
        out = js_dir / Path(url).name
        if not out.exists() or out.stat().st_size == 0:
            response = requests.get(BASE + url, timeout=60)
            response.raise_for_status()
            out.write_bytes(response.content)
        saved.append({"url": BASE + url, "path": str(out), "bytes": out.stat().st_size})

    hits = []
    patterns = [
        "api",
        "submit",
        "job",
        "Layer_List",
        "Area_of_Interest",
        "Email",
        "Download",
        "arcgis/rest",
        "LF2024_FBFM40",
    ]
    for js_path in sorted(js_dir.glob("*.js")):
        text = js_path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern in text:
                snippets = []
                for match in re.finditer(re.escape(pattern), text):
                    start = max(0, match.start() - 180)
                    end = min(len(text), match.end() + 260)
                    snippets.append(text[start:end])
                    if len(snippets) >= 8:
                        break
                hits.append({"file": js_path.name, "pattern": pattern, "snippets": snippets})

    report = {"base": BASE, "html": str(html_path), "js_files": saved, "hits": hits}
    out = DIRS["tables"] / "landfire_lfps_probe.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
