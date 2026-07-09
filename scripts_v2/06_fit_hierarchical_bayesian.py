import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import numpy as np
import pandas as pd

from utils_v2 import PROJECT, load_config, require_audit_first, write_json, write_text


STAN_DIR = PROJECT / "data_model/v2/stan"
AUDIT_DIR = PROJECT / "outputs/v2/audit"
TABLE_DIR = PROJECT / "outputs/v2/tables"
CMDSTAN_ROOT = Path(r"F:\Rprogram\WeiPHD\.cmdstan_local\cmdstan-2.38.0")
MAKE_EXE = Path(r"C:\rtools45\usr\bin\make.exe")
GPP_DIR = Path(r"C:\rtools45\x86_64-w64-mingw32.static.posix\bin")

FEATURES = [
    "v2_phys_dryness_process_index",
    "v2_phys_fuel_structure_index",
    "v2_phys_dryness_x_fuel",
    "z_vpd_season_p95",
    "z_erc_season_p95",
    "z_bi_season_p95",
    "z_vs_season_p95",
    "z_fm100_season_p05",
    "z_fm1000_season_p05",
    "z_rmin_season_p05",
    "z_pr_season_sum",
    "z_hot_dry_windy_train_threshold_frac",
    "z_dry_spell_max_days",
    "z_cc_mean",
    "z_ch_positive_fraction",
    "z_cbd_mean",
    "z_slope_mean_deg",
    "z_terrain_ruggedness_mean",
]


STAN_CODE = r"""
data {
  int<lower=1> N;
  int<lower=1> K;
  matrix[N, K] X;
  array[N] int<lower=0, upper=1> y;
  int<lower=1> B;
  array[N] int<lower=1, upper=B> block_id;
  int<lower=1> T;
  array[N] int<lower=1, upper=T> year_id;
}
parameters {
  real alpha;
  vector[K] beta;
  vector[B] z_block;
  vector[T] z_year;
  real<lower=0> sigma_block;
  real<lower=0> sigma_year;
}
transformed parameters {
  vector[B] a_block = sigma_block * z_block;
  vector[T] a_year = sigma_year * z_year;
}
model {
  alpha ~ normal(-3.5, 1.5);
  beta ~ normal(0, 1);
  z_block ~ normal(0, 1);
  z_year ~ normal(0, 1);
  sigma_block ~ exponential(1);
  sigma_year ~ exponential(1);
  y ~ bernoulli_logit(alpha + X * beta + a_block[block_id] + a_year[year_id]);
}
generated quantities {
  vector[N] log_lik;
  for (n in 1:N) {
    log_lik[n] = bernoulli_logit_lpmf(y[n] | alpha + X[n] * beta + a_block[block_id[n]] + a_year[year_id[n]]);
  }
}
"""


def load_imputer():
    path = TABLE_DIR / "v2_model_ladder_train_median_imputer.csv"
    imp = pd.read_csv(path)
    return dict(zip(imp["feature"], imp["train_median_impute"]))


def write_run_script(stan_file, data_file):
    exe = STAN_DIR / "hier_logit_block_year.exe"
    ps1 = PROJECT / "RUN_STAN_MCMC_V2.ps1"
    lines = [
        '$ErrorActionPreference = "Stop"',
        f'$env:PATH = "{GPP_DIR};" + $env:PATH',
        f'$CmdStan = "{CMDSTAN_ROOT}"',
        f'$Make = "{MAKE_EXE}"',
        f'$Model = "{stan_file}"',
        f'$Exe = "{exe}"',
        f'$Data = "{data_file}"',
        f'& $Make -C $CmdStan "{stan_file.with_suffix("").as_posix()}"',
        "New-Item -ItemType Directory -Force -Path \"data_model/v2/stan/chains\" | Out-Null",
        "for ($chain = 1; $chain -le 4; $chain++) {",
        "  $seed = 20260708 + $chain",
        "  & $Exe sample num_warmup=500 num_samples=500 save_warmup=0 thin=1 adapt delta=0.95 data file=$Data random seed=$seed output file=\"data_model/v2/stan/chains/hier_logit_block_year_chain${chain}.csv\"",
        "}",
    ]
    write_text(ps1, "\n".join(lines) + "\n")
    return ps1


def main():
    require_audit_first()
    STAN_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
    label = config["models"]["label"]

    read_cols = ["block_50km_id", "year", label, "is_train_year"] + FEATURES
    df = pd.read_parquet(PROJECT / "data_intermediate/v2/model_table/segment_year_v2.parquet", columns=read_cols)
    train = df.loc[df["is_train_year"].eq(1), ["block_50km_id", "year", label] + FEATURES].copy()
    imputer = load_imputer()
    for col in FEATURES:
        if col not in train.columns:
            raise KeyError(f"Missing V2 Stan feature: {col}")
        train[col] = train[col].fillna(imputer.get(col, 0.0))

    block_levels = sorted(train["block_50km_id"].astype(str).unique())
    year_levels = sorted(int(x) for x in train["year"].unique())
    block_map = {v: i + 1 for i, v in enumerate(block_levels)}
    year_map = {v: i + 1 for i, v in enumerate(year_levels)}

    x = train[FEATURES].to_numpy(dtype="float64")
    payload = {
        "N": int(len(train)),
        "K": int(len(FEATURES)),
        "X": x.tolist(),
        "y": train[label].astype(int).tolist(),
        "B": len(block_levels),
        "block_id": train["block_50km_id"].astype(str).map(block_map).astype(int).tolist(),
        "T": len(year_levels),
        "year_id": train["year"].astype(int).map(year_map).astype(int).tolist(),
    }
    stan_file = STAN_DIR / "hier_logit_block_year.stan"
    data_file = STAN_DIR / "hier_logit_block_year_train.json"
    write_text(stan_file, STAN_CODE.strip() + "\n")
    write_text(data_file, json.dumps(payload))

    pd.DataFrame({"feature_index": range(1, len(FEATURES) + 1), "feature": FEATURES}).to_csv(
        TABLE_DIR / "v2_stan_feature_manifest.csv", index=False
    )
    pd.DataFrame({"block_index": range(1, len(block_levels) + 1), "block_50km_id": block_levels}).to_csv(
        TABLE_DIR / "v2_stan_block_index.csv", index=False
    )
    pd.DataFrame({"year_index": range(1, len(year_levels) + 1), "year": year_levels}).to_csv(
        TABLE_DIR / "v2_stan_year_index.csv", index=False
    )
    run_script = write_run_script(stan_file.resolve(), data_file.resolve())

    summary = {
        "status": "stan_model_and_data_prepared_mcmc_not_run",
        "stan_file": str(stan_file.relative_to(PROJECT)),
        "data_file": str(data_file.relative_to(PROJECT)),
        "run_script": str(run_script.relative_to(PROJECT)),
        "cmdstan_root_exists": CMDSTAN_ROOT.exists(),
        "make_exists": MAKE_EXE.exists(),
        "gpp_dir_exists": GPP_DIR.exists(),
        "train_rows": int(len(train)),
        "features": FEATURES,
        "block_50km_levels": len(block_levels),
        "year_levels": year_levels,
        "mcmc_plan": "4 chains, 500 warmup, 500 sampling iterations, adapt_delta=0.95",
    }
    write_json(AUDIT_DIR / "HIERARCHICAL_STAN_PREP_QA.json", summary)
    md = "# Hierarchical Stan Prep QA\n\n"
    md += f"- Status: {summary['status']}\n"
    md += f"- Train rows: {summary['train_rows']}\n"
    md += f"- Features: {len(FEATURES)}\n"
    md += f"- 50 km blocks: {summary['block_50km_levels']}\n"
    md += f"- Years: `{summary['year_levels']}`\n"
    md += f"- CmdStan root exists: {summary['cmdstan_root_exists']}\n"
    md += f"- Rtools make exists: {summary['make_exists']}\n"
    md += f"- Run script: `{summary['run_script']}`\n\n"
    md += "No posterior quantities are reported until CmdStan MCMC chains complete and diagnostics are checked.\n"
    write_text(AUDIT_DIR / "HIERARCHICAL_STAN_PREP_QA.md", md)
    print(f"[done] {stan_file}")
    print(f"[done] {data_file}")
    print(f"[done] {run_script}")


if __name__ == "__main__":
    main()
