import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import numpy as np
import pandas as pd


PHASE6 = PROJECT / "data/processed/phase6"
LABEL = "exogenous_fire_exposure"


def header_columns(csv_path):
    with csv_path.open("rb") as f:
        for raw in f:
            if raw.startswith(b"#"):
                continue
            return raw.decode("ascii", errors="ignore").strip().split(",")
    raise RuntimeError(f"No data header found in {csv_path}")


def read_p_new(csv_path):
    columns = header_columns(csv_path)
    p_cols = [c for c in columns if c.startswith("p_new.")]
    if not p_cols:
        raise RuntimeError(f"No p_new columns found in {csv_path}")
    df = pd.read_csv(csv_path, comment="#", usecols=p_cols, encoding="latin1")
    return df.to_numpy(dtype="float64")


def summarize_posterior(p_new, out_dir):
    key_path = PHASE6 / "phase6_stan_test_keys.csv"
    meta_path = PHASE6 / "stan_selected_core_metadata.json"
    keys = pd.read_csv(key_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    tau = meta["train_positive_rows"] / meta["train_rows"]

    row = keys.copy()
    row["posterior_mean"] = p_new.mean(axis=0)
    row["posterior_p_exposure_gt_tau"] = (p_new > tau).mean(axis=0)
    row["posterior_p05"] = np.quantile(p_new, 0.05, axis=0)
    row["posterior_p95"] = np.quantile(p_new, 0.95, axis=0)
    row.to_csv(out_dir / "phase6_stan_row_posterior_predictions.csv", index=False)
    row.to_parquet(out_dir / "phase6_stan_row_posterior_predictions.parquet", index=False)

    segment_ids = keys["segment_id"].drop_duplicates().to_numpy()
    key_segment = keys["segment_id"].to_numpy()
    segment_draws = np.zeros((p_new.shape[0], len(segment_ids)), dtype="float64")
    for j, segment_id in enumerate(segment_ids):
        idx = np.flatnonzero(key_segment == segment_id)
        segment_draws[:, j] = p_new[:, idx].mean(axis=1)

    top_k = max(1, int(np.ceil(0.10 * len(segment_ids))))
    top_counts = np.zeros(len(segment_ids), dtype="float64")
    for draw in segment_draws:
        top_idx = np.argpartition(draw, -top_k)[-top_k:]
        top_counts[top_idx] += 1

    seg = pd.DataFrame(
        {
            "segment_id": segment_ids,
            "posterior_mean_exposure_probability": segment_draws.mean(axis=0),
            "p_exposure_gt_tau": (segment_draws > tau).mean(axis=0),
            "p_rank_in_top10": top_counts / segment_draws.shape[0],
            "posterior_p05": np.quantile(segment_draws, 0.05, axis=0),
            "posterior_p95": np.quantile(segment_draws, 0.95, axis=0),
        }
    ).sort_values("posterior_mean_exposure_probability", ascending=False)
    seg.to_csv(out_dir / "phase6_stan_segment_posterior_decision_metrics.csv", index=False)
    seg.to_parquet(out_dir / "phase6_stan_segment_posterior_decision_metrics.parquet", index=False)

    summary = {
        "tau": tau,
        "posterior_draws": int(p_new.shape[0]),
        "test_rows": int(p_new.shape[1]),
        "segments": int(len(segment_ids)),
        "top_decile_k": int(top_k),
        "row_output": str(out_dir / "phase6_stan_row_posterior_predictions.parquet"),
        "segment_output": str(out_dir / "phase6_stan_segment_posterior_decision_metrics.parquet"),
    }
    (out_dir / "phase6_stan_posterior_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Extract p_new draws from Stan CSV files when cmdstanpy metadata parsing fails.")
    parser.add_argument("--suffix", default="pilot")
    args = parser.parse_args()
    out_dir = PHASE6 / f"stan_mcmc_{args.suffix}"
    csv_files = sorted(out_dir.glob("*.csv"))
    if not csv_files:
        raise SystemExit(f"No Stan CSV files found in {out_dir}")
    draws = []
    for csv_path in csv_files:
        print(f"Reading p_new from {csv_path}")
        draws.append(read_p_new(csv_path))
    p_new = np.vstack(draws)
    summary = summarize_posterior(p_new, out_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
