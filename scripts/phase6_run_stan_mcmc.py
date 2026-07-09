import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import json
import os
import argparse

import numpy as np
import pandas as pd

SHARED_DEPS = Path(r"E:\WPSDrive\198731884\WPS云盘\WeiPHD\.python_deps")
if SHARED_DEPS.exists():
    sys.path.append(str(SHARED_DEPS))

try:
    from cmdstanpy import CmdStanModel, set_cmdstan_path
except ImportError as exc:
    raise SystemExit(
        "cmdstanpy is not installed in this project runtime. "
        "Install cmdstanpy and CmdStan, then rerun this script."
    ) from exc


def configure_local_toolchain():
    cmdstan_candidates = [
        Path(r"F:\Rprogram\WeiPHD\.cmdstan_local\cmdstan-2.38.0"),
        Path(r"C:\Users\philo\.cmdstan\cmdstan-2.36.0"),
    ]
    for cmdstan in cmdstan_candidates:
        if (cmdstan / "makefile").exists() and (cmdstan / "bin/stanc.exe").exists():
            set_cmdstan_path(str(cmdstan))
            print(f"Using CmdStan: {cmdstan}")
            break
    else:
        raise SystemExit("No usable CmdStan root found. Expected a directory with makefile and bin/stanc.exe.")
    rtools_bin = Path(r"C:\rtools45\usr\bin")
    rtools_gcc = Path(r"C:\rtools45\x86_64-w64-mingw32.static.posix\bin")
    wrapper_bin = PROJECT / "scripts"
    prepend = [str(p) for p in [wrapper_bin, rtools_bin, rtools_gcc] if p.exists()]
    if prepend:
        os.environ["PATH"] = os.pathsep.join(prepend + [os.environ.get("PATH", "")])


def summarize_posterior(fit, out_dir):
    key_path = PROJECT / "data/processed/phase6/phase6_stan_test_keys.csv"
    meta_path = PROJECT / "data/processed/phase6/stan_selected_core_metadata.json"
    keys = pd.read_csv(key_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    tau = meta["train_positive_rows"] / meta["train_rows"]

    p_new = fit.stan_variable("p_new")
    if p_new.ndim != 2:
        raise RuntimeError(f"Expected p_new as draws x rows, got shape {p_new.shape}")

    row = keys.copy()
    row["posterior_mean"] = p_new.mean(axis=0)
    row["posterior_p_exposure_gt_tau"] = (p_new > tau).mean(axis=0)
    row["posterior_p05"] = np.quantile(p_new, 0.05, axis=0)
    row["posterior_p95"] = np.quantile(p_new, 0.95, axis=0)
    row.to_csv(out_dir / "phase6_stan_row_posterior_predictions.csv", index=False)
    row.to_parquet(out_dir / "phase6_stan_row_posterior_predictions.parquet", index=False)

    segment_ids = keys["segment_id"].drop_duplicates().to_numpy()
    segment_draws = np.zeros((p_new.shape[0], len(segment_ids)), dtype="float64")
    for j, segment_id in enumerate(segment_ids):
        idx = np.flatnonzero(keys["segment_id"].to_numpy() == segment_id)
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
    parser = argparse.ArgumentParser(description="Run Stan MCMC for Phase 6 selected-core exposure model.")
    parser.add_argument("--chains", type=int, default=2)
    parser.add_argument("--parallel-chains", type=int, default=2)
    parser.add_argument("--warmup", type=int, default=200)
    parser.add_argument("--sampling", type=int, default=200)
    parser.add_argument("--suffix", default="pilot")
    args = parser.parse_args()

    configure_local_toolchain()
    stan_file = PROJECT / "stan/exogenous_logistic_selected_core.stan"
    data_file = PROJECT / "data/processed/phase6/stan_selected_core_data.json"
    out_dir = PROJECT / "data/processed/phase6" / f"stan_mcmc_{args.suffix}"
    out_dir.mkdir(parents=True, exist_ok=True)
    model = CmdStanModel(stan_file=str(stan_file))
    fit = model.sample(
        data=str(data_file),
        chains=args.chains,
        parallel_chains=args.parallel_chains,
        iter_warmup=args.warmup,
        iter_sampling=args.sampling,
        seed=20260701,
        output_dir=str(out_dir),
    )
    fit.save_csvfiles(dir=str(out_dir))
    print(fit.diagnose())
    print(fit.summary().head(30))
    print(json.dumps(summarize_posterior(fit, out_dir), indent=2))


if __name__ == "__main__":
    main()
