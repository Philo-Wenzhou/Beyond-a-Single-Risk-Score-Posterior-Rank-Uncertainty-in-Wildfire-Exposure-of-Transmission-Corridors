import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import requests

from phase2_data_config import DIRS, STUDY_BBOX_WGS84, ensure_phase2_dirs


BASE = "https://lfps.usgs.gov"
DEFAULT_LAYERS = "LF2024_FBFM40;LF2024_CC;LF2024_CH;LF2024_CBH;LF2024_CBD"


def payload(email: str | None, layers: str, resolution: int):
    west, south, east, north = STUDY_BBOX_WGS84
    body = {
        "Layer_List": layers,
        "Include_Layer_List_XML_File": True,
        "Area_of_Interest": f"{west} {south} {east} {north}",
        "Output_Projection": "5070",
        "Resample_Resolution": resolution,
        "Edit_Rule": None,
        "Edit_Mask": None,
        "Priority_Code": None,
    }
    if email:
        body["Email"] = email
    return body


def post_job(body):
    response = requests.post(f"{BASE}/api/job/submit", json=body, timeout=90)
    response.raise_for_status()
    return response.json()


def get_status(job_id: str):
    response = requests.get(f"{BASE}/api/job/status", params={"JobId": job_id}, timeout=60)
    response.raise_for_status()
    return response.json()


def download_output(url: str):
    parsed = urlparse(url)
    name = Path(parsed.path).name or "landfire_lfps_output.bin"
    out = DIRS["raw_landfire"] / name
    if out.exists() and out.stat().st_size > 1024:
        return out
    with requests.get(url, stream=True, timeout=180) as response:
        response.raise_for_status()
        tmp = out.with_suffix(out.suffix + ".part")
        with tmp.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
        tmp.replace(out)
    return out


def redact_email(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if key.lower() in {"email", "requesteremail"}:
                redacted[key] = "<redacted>"
            else:
                redacted[key] = redact_email(item)
        return redacted
    if isinstance(value, list):
        return [redact_email(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser(description="Submit and poll a LANDFIRE LFPS fuel-layer job.")
    parser.add_argument("--submit", action="store_true", help="Submit the LFPS job. Requires LANDFIRE_EMAIL.")
    parser.add_argument("--job-id", default=None, help="Existing LFPS job id to poll.")
    parser.add_argument("--poll", action="store_true", help="Poll until completion or timeout.")
    parser.add_argument("--layers", default=DEFAULT_LAYERS)
    parser.add_argument("--resolution", type=int, default=90)
    parser.add_argument("--max-wait-minutes", type=float, default=60)
    parser.add_argument("--poll-seconds", type=float, default=30)
    args = parser.parse_args()

    ensure_phase2_dirs()
    email = os.environ.get("LANDFIRE_EMAIL")
    body = payload(email, args.layers, args.resolution)
    manifest = {
        "source": BASE,
        "submit_endpoint": f"{BASE}/api/job/submit",
        "status_endpoint": f"{BASE}/api/job/status",
        "payload": redact_email(body),
        "submitted": False,
        "job_id": args.job_id,
        "status_history": [],
        "output_file": None,
        "role": "static fuel and canopy covariates for wildfire exposure modeling",
    }

    if args.submit:
        if not email:
            raise RuntimeError("Set LANDFIRE_EMAIL before submitting an LFPS job.")
        submission = post_job(body)
        manifest["submitted"] = True
        manifest["submission"] = redact_email(submission)
        manifest["job_id"] = submission.get("jobId") or submission.get("job_id")

    if args.poll and manifest["job_id"]:
        deadline = time.time() + args.max_wait_minutes * 60
        while time.time() < deadline:
            status = get_status(manifest["job_id"])
            manifest["status_history"].append(status)
            output_url = status.get("outputFile")
            if output_url:
                output = download_output(output_url)
                manifest["output_file"] = str(output)
                break
            if str(status.get("status", "")).lower() in {"failed", "error", "canceled", "cancelled"}:
                break
            time.sleep(args.poll_seconds)

    out = DIRS["tables"] / "landfire_lfps_job_manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(out)
    if not args.submit and not args.job_id:
        print("[dry-run] Set LANDFIRE_EMAIL and pass --submit --poll to create and retrieve an LFPS job.")


if __name__ == "__main__":
    main()
