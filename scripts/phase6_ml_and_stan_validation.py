import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


PHASE3 = PROJECT / "data/processed/phase3"
PHASE4 = PROJECT / "data/processed/phase4"
PHASE6 = PROJECT / "data/processed/phase6"
STAN_DIR = PROJECT / "stan"
TABLE_DIR = PROJECT / "outputs/tables"
FIG_DIR = PROJECT / "outputs/figures/phase6"

RANDOM_SEED = 20260701
TRAIN_YEARS = [2017, 2018, 2019, 2020, 2021]
TEST_YEARS = [2022, 2023]
LABEL = "exogenous_fire_exposure"

COLORS = {
    "paper": "#fbfaf6",
    "text": "#24292c",
    "axis": "#596168",
    "grid": "#d8d5cd",
    "accent": "#005f73",
    "compare": "#c27a15",
    "forest": "#3d6b35",
    "steel": "#4f6d7a",
    "muted": "#8b8378",
}

RAW_FEATURES = [
    "gridmet_vpd_p95",
    "gridmet_erc_p95",
    "gridmet_bi_p95",
    "gridmet_vs_p95",
    "gridmet_fm100_p05",
    "gridmet_fm1000_p05",
    "gridmet_rmin_p05",
    "gridmet_pr_sum",
    "dem_elevation_m",
    "landfire_canopy_cover_pct",
    "landfire_canopy_height_m",
    "landfire_canopy_base_height_m",
    "landfire_canopy_bulk_density",
]

SELECTED_PHYSICS_CORE = RAW_FEATURES + [
    "phys_dryness_index",
    "phys_fuel_structure_index",
    "phys_dryness_x_fuel",
]

ML_MODELS = {
    "ml_logistic_l2": make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, solver="lbfgs", random_state=RANDOM_SEED),
    ),
    "ml_random_forest_balanced": RandomForestClassifier(
        n_estimators=450,
        min_samples_leaf=12,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=RANDOM_SEED,
    ),
    "ml_extra_trees_balanced": ExtraTreesClassifier(
        n_estimators=450,
        min_samples_leaf=12,
        class_weight="balanced",
        n_jobs=-1,
        random_state=RANDOM_SEED,
    ),
    "ml_hist_gradient_boosting": HistGradientBoostingClassifier(
        max_iter=260,
        learning_rate=0.035,
        max_leaf_nodes=24,
        l2_regularization=0.05,
        random_state=RANDOM_SEED,
    ),
}


def ensure_dirs():
    PHASE6.mkdir(parents=True, exist_ok=True)
    STAN_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_model_table():
    parquet = PHASE3 / "segment_year_model_table.parquet"
    if parquet.exists():
        df = pd.read_parquet(parquet)
    else:
        df = pd.read_csv(PHASE3 / "segment_year_model_table.csv")
    return df.sort_values(["segment_id", "year"]).reset_index(drop=True)


def add_physics_features(df, train_mask):
    df = df.copy()
    med = df.loc[train_mask, RAW_FEATURES].median(numeric_only=True)
    for col in RAW_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(med[col])

    scaler = StandardScaler()
    z_all = pd.DataFrame(scaler.fit(df.loc[train_mask, RAW_FEATURES]).transform(df[RAW_FEATURES]), columns=RAW_FEATURES, index=df.index)
    df["phys_dryness_index"] = z_all[
        ["gridmet_vpd_p95", "gridmet_erc_p95", "gridmet_bi_p95", "gridmet_vs_p95"]
    ].mean(axis=1) - z_all[["gridmet_fm100_p05", "gridmet_fm1000_p05", "gridmet_rmin_p05", "gridmet_pr_sum"]].mean(axis=1)
    df["phys_fuel_structure_index"] = z_all[
        ["landfire_canopy_cover_pct", "landfire_canopy_height_m", "landfire_canopy_bulk_density"]
    ].mean(axis=1)
    df["phys_dryness_x_fuel"] = df["phys_dryness_index"] * df["phys_fuel_structure_index"]
    return df, med.to_dict()


def prepare_feature_matrix(df, train_mask):
    work = df[SELECTED_PHYSICS_CORE].copy()
    for col in SELECTED_PHYSICS_CORE:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    med = work.loc[train_mask].median(numeric_only=True)
    work = work.fillna(med)
    return work, med.to_dict()


def top_decile_capture(y, score):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    k = max(1, int(np.ceil(0.10 * len(score))))
    chosen = np.argsort(score)[-k:]
    positives = int(y.sum())
    return {
        "top10_k": int(k),
        "top10_capture_rate": float(y[chosen].sum() / positives) if positives else np.nan,
        "top10_positive_rate": float(y[chosen].mean()),
    }


def segment_top_decile_capture(pred):
    seg = (
        pred.groupby("segment_id", as_index=False)
        .agg(score=("probability", "mean"), positives=(LABEL, "sum"))
        .sort_values("score", ascending=False)
    )
    k = max(1, int(np.ceil(0.10 * len(seg))))
    chosen = seg.head(k)
    positives = float(seg["positives"].sum())
    return {
        "segment_top10_k": int(k),
        "segment_top10_capture_rate": float(chosen["positives"].sum() / positives) if positives else np.nan,
        "segment_top10_positive_rate": float(chosen["positives"].sum() / max(1, len(chosen))),
    }


def evaluate_prediction(model_id, label, pred):
    y = pred[LABEL].to_numpy(dtype=int)
    p = pred["probability"].to_numpy(dtype=float)
    row_top = top_decile_capture(y, p)
    seg_top = segment_top_decile_capture(pred)
    out = {
        "model_id": model_id,
        "label": label,
        "test_rows": int(len(pred)),
        "test_positive_rows": int(y.sum()),
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
    }
    out.update(row_top)
    out.update(seg_top)
    return out


def load_phase4_comparators(test_keys):
    phase4_path = PHASE4 / "phase4_segment_year_predictions.parquet"
    comp = pd.read_parquet(phase4_path)
    comp = comp.merge(test_keys, on=["segment_id", "year"], how="inner")
    comparators = []
    specs = [
        ("deterministic_calibrated", "Deterministic calibrated score", "deterministic_calibrated_prob"),
        ("bayesian_laplace", "Bayesian Laplace posterior mean", "bayesian_posterior_predictive_mean"),
    ]
    for model_id, label, col in specs:
        pred = comp[["segment_id", "year", LABEL, col]].rename(columns={col: "probability"})
        pred["model_id"] = model_id
        pred["model_label"] = label
        comparators.append(pred)
    return comparators


def fit_ml_models(df, features, train_mask, test_mask):
    X_train = features.loc[train_mask].to_numpy(dtype="float64")
    y_train = df.loc[train_mask, LABEL].to_numpy(dtype=int)
    X_test = features.loc[test_mask].to_numpy(dtype="float64")
    base = df.loc[test_mask, ["segment_id", "year", LABEL]].reset_index(drop=True)

    predictions = []
    for model_id, model in ML_MODELS.items():
        model.fit(X_train, y_train)
        probability = model.predict_proba(X_test)[:, 1]
        pred = base.copy()
        pred["probability"] = probability
        pred["model_id"] = model_id
        pred["model_label"] = model_id.replace("_", " ")
        predictions.append(pred)
    return predictions


def write_stan_model():
    stan_path = STAN_DIR / "exogenous_logistic_selected_core.stan"
    stan_path.write_text(
        """data {
  int<lower=1> N;
  int<lower=1> K;
  matrix[N, K] X;
  array[N] int<lower=0, upper=1> y;
  int<lower=1> N_new;
  matrix[N_new, K] X_new;
}
parameters {
  real alpha;
  vector[K] beta;
}
model {
  alpha ~ normal(0, 5);
  beta ~ normal(0, 2);
  y ~ bernoulli_logit(alpha + X * beta);
}
generated quantities {
  vector[N_new] p_new;
  for (n in 1:N_new) {
    p_new[n] = inv_logit(alpha + X_new[n] * beta);
  }
}
""",
        encoding="utf-8",
    )
    return stan_path


def write_stan_runner():
    runner_path = PROJECT / "scripts/phase6_run_stan_mcmc.py"
    if runner_path.exists():
        return runner_path
    runner_path.write_text(
        """import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

try:
    from cmdstanpy import CmdStanModel
except ImportError as exc:
    raise SystemExit(
        "cmdstanpy is not installed in this project runtime. "
        "Install cmdstanpy and CmdStan, then rerun this script."
    ) from exc


def main():
    stan_file = PROJECT / "stan/exogenous_logistic_selected_core.stan"
    data_file = PROJECT / "data/processed/phase6/stan_selected_core_data.json"
    out_dir = PROJECT / "data/processed/phase6/stan_mcmc"
    out_dir.mkdir(parents=True, exist_ok=True)
    model = CmdStanModel(stan_file=str(stan_file))
    fit = model.sample(
        data=str(data_file),
        chains=4,
        parallel_chains=4,
        iter_warmup=1000,
        iter_sampling=1000,
        seed=20260701,
        output_dir=str(out_dir),
    )
    fit.save_csvfiles(dir=str(out_dir))
    print(fit.diagnose())
    print(fit.summary().head(30))


if __name__ == "__main__":
    main()
""",
        encoding="utf-8",
    )
    return runner_path


def write_stan_data(features, df, train_mask, test_mask):
    scaler = StandardScaler()
    X_train = scaler.fit_transform(features.loc[train_mask])
    X_test = scaler.transform(features.loc[test_mask])
    y_train = df.loc[train_mask, LABEL].astype(int).to_numpy()
    y_test = df.loc[test_mask, LABEL].astype(int).to_numpy()

    data = {
        "N": int(X_train.shape[0]),
        "K": int(X_train.shape[1]),
        "X": X_train.tolist(),
        "y": y_train.tolist(),
        "N_new": int(X_test.shape[0]),
        "X_new": X_test.tolist(),
    }
    data_path = PHASE6 / "stan_selected_core_data.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")

    meta = {
        "label": LABEL,
        "train_years": TRAIN_YEARS,
        "test_years": TEST_YEARS,
        "features": SELECTED_PHYSICS_CORE,
        "train_rows": int(X_train.shape[0]),
        "test_rows": int(X_test.shape[0]),
        "train_positive_rows": int(y_train.sum()),
        "test_positive_rows": int(y_test.sum()),
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "test_keys_path": str(PHASE6 / "phase6_stan_test_keys.csv"),
    }
    meta_path = PHASE6 / "stan_selected_core_metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    df.loc[test_mask, ["segment_id", "year", LABEL]].to_csv(PHASE6 / "phase6_stan_test_keys.csv", index=False)
    return data_path, meta_path


def save_outputs(predictions, metrics):
    pred_df = pd.concat(predictions, ignore_index=True)
    metrics_df = pd.DataFrame(metrics).sort_values(["pr_auc", "top10_capture_rate"], ascending=False)

    pred_df.to_parquet(PHASE6 / "phase6_ml_and_comparator_predictions.parquet", index=False)
    pred_df.to_csv(PHASE6 / "phase6_ml_and_comparator_predictions.csv", index=False)
    metrics_df.to_parquet(PHASE6 / "phase6_model_comparison_metrics.parquet", index=False)
    metrics_df.to_csv(PHASE6 / "phase6_model_comparison_metrics.csv", index=False)

    report = {
        "method": "Temporal-holdout validation with deterministic, Bayesian Laplace, and machine-learning baselines; Stan MCMC input package prepared.",
        "label": LABEL,
        "train_years": TRAIN_YEARS,
        "test_years": TEST_YEARS,
        "features": SELECTED_PHYSICS_CORE,
        "metrics": metrics_df.to_dict(orient="records"),
        "outputs": {
            "metrics_csv": str(PHASE6 / "phase6_model_comparison_metrics.csv"),
            "predictions_parquet": str(PHASE6 / "phase6_ml_and_comparator_predictions.parquet"),
            "stan_model": str(STAN_DIR / "exogenous_logistic_selected_core.stan"),
            "stan_data": str(PHASE6 / "stan_selected_core_data.json"),
            "stan_runner": str(PROJECT / "scripts/phase6_run_stan_mcmc.py"),
        },
    }
    (TABLE_DIR / "phase6_ml_stan_validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return pred_df, metrics_df


def style_axis(ax):
    ax.set_facecolor(COLORS["paper"])
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.7, alpha=0.75)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(COLORS["grid"])
    ax.spines["bottom"].set_color(COLORS["grid"])
    ax.tick_params(colors=COLORS["axis"], labelsize=8)
    ax.title.set_color(COLORS["text"])
    ax.xaxis.label.set_color(COLORS["axis"])
    ax.yaxis.label.set_color(COLORS["axis"])


def plot_metrics(metrics_df):
    plot_df = metrics_df.copy()
    label_map = {
        "bayesian_laplace": "Bayesian\nLaplace",
        "deterministic_calibrated": "Deterministic\ncalibrated",
        "ml_logistic_l2": "ML logistic",
        "ml_random_forest_balanced": "Random\nforest",
        "ml_extra_trees_balanced": "Extra\ntrees",
        "ml_hist_gradient_boosting": "Gradient\nboosting",
    }
    order = [
        "deterministic_calibrated",
        "bayesian_laplace",
        "ml_logistic_l2",
        "ml_random_forest_balanced",
        "ml_extra_trees_balanced",
        "ml_hist_gradient_boosting",
    ]
    plot_df["display"] = plot_df["model_id"].map(label_map)
    plot_df["order"] = plot_df["model_id"].map({m: i for i, m in enumerate(order)})
    plot_df = plot_df.sort_values("order")
    palette = {
        "deterministic_calibrated": COLORS["compare"],
        "bayesian_laplace": COLORS["accent"],
        "ml_logistic_l2": COLORS["muted"],
        "ml_random_forest_balanced": COLORS["forest"],
        "ml_extra_trees_balanced": COLORS["steel"],
        "ml_hist_gradient_boosting": "#7a6a2f",
    }

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), facecolor=COLORS["paper"], constrained_layout=True)
    specs = [
        ("roc_auc", "ROC-AUC", "Higher is better"),
        ("pr_auc", "PR-AUC", "Sensitive to rare exposure positives"),
        ("top10_capture_rate", "Row top-10% capture", "Decision triage concentration"),
    ]
    for ax, (metric, title, subtitle) in zip(axes, specs):
        colors = [palette[m] for m in plot_df["model_id"]]
        ax.bar(plot_df["display"], plot_df[metric], color=colors, width=0.68)
        style_axis(ax)
        ax.set_title(title, fontsize=10, loc="left", pad=12)
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=8, color=COLORS["axis"], va="bottom")
        ax.set_ylabel(title)
        ax.tick_params(axis="x", rotation=18)
        for tick in ax.get_xticklabels():
            tick.set_ha("right")
        ymax = max(plot_df[metric].max() * 1.18, 0.05)
        ax.set_ylim(0, ymax)
        for i, val in enumerate(plot_df[metric]):
            ax.text(i, val + ymax * 0.025, f"{val:.3f}", ha="center", va="bottom", fontsize=7, color=COLORS["text"])
    fig.suptitle("Temporal holdout validation: deterministic, Bayesian, and ML baselines", fontsize=11, color=COLORS["text"])
    out = FIG_DIR / "phase6_model_comparison_metrics.png"
    fig.savefig(out, dpi=300, facecolor=COLORS["paper"])
    plt.close(fig)


def plot_calibration(pred_df):
    bins = np.linspace(0, max(0.12, pred_df["probability"].quantile(0.995)), 12)
    rows = []
    for model_id, g in pred_df.groupby("model_id"):
        cuts = pd.cut(g["probability"], bins=bins, include_lowest=True)
        cal = g.groupby(cuts, observed=True).agg(predicted=("probability", "mean"), observed=(LABEL, "mean"), n=(LABEL, "size"))
        cal["model_id"] = model_id
        rows.append(cal.reset_index(drop=True))
    cal_df = pd.concat(rows, ignore_index=True)
    keep = ["deterministic_calibrated", "bayesian_laplace", "ml_hist_gradient_boosting", "ml_random_forest_balanced"]
    colors = {
        "deterministic_calibrated": COLORS["compare"],
        "bayesian_laplace": COLORS["accent"],
        "ml_hist_gradient_boosting": "#7a6a2f",
        "ml_random_forest_balanced": COLORS["forest"],
    }
    labels = {
        "deterministic_calibrated": "Deterministic calibrated",
        "bayesian_laplace": "Bayesian Laplace",
        "ml_hist_gradient_boosting": "Gradient boosting",
        "ml_random_forest_balanced": "Random forest",
    }
    fig, ax = plt.subplots(figsize=(7.2, 5.0), facecolor=COLORS["paper"], constrained_layout=True)
    for model_id in keep:
        g = cal_df[(cal_df["model_id"] == model_id) & (cal_df["n"] >= 20)]
        ax.plot(g["predicted"], g["observed"], marker="o", linewidth=1.6, markersize=4, color=colors[model_id], label=labels[model_id])
    hi = max(cal_df["predicted"].max(), cal_df["observed"].max()) * 1.05
    ax.plot([0, hi], [0, hi], color=COLORS["grid"], linewidth=1.1, linestyle="--", label="Ideal")
    style_axis(ax)
    ax.set_xlim(0, hi)
    ax.set_ylim(0, hi)
    ax.set_xlabel("Mean predicted exposure probability")
    ax.set_ylabel("Observed exposure frequency")
    ax.set_title("Calibration check for rare external exposure", fontsize=10.5, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper left", handlelength=2.0)
    out = FIG_DIR / "phase6_calibration_check.png"
    fig.savefig(out, dpi=300, facecolor=COLORS["paper"])
    plt.close(fig)


def main():
    ensure_dirs()
    df = load_model_table()
    train_mask = df["year"].isin(TRAIN_YEARS).to_numpy()
    test_mask = df["year"].isin(TEST_YEARS).to_numpy()
    df, raw_medians = add_physics_features(df, train_mask)
    features, feature_medians = prepare_feature_matrix(df, train_mask)

    test_keys = df.loc[test_mask, ["segment_id", "year"]].copy()
    predictions = load_phase4_comparators(test_keys)
    predictions.extend(fit_ml_models(df, features, train_mask, test_mask))
    metrics = [evaluate_prediction(pred["model_id"].iloc[0], pred["model_label"].iloc[0], pred) for pred in predictions]

    pred_df, metrics_df = save_outputs(predictions, metrics)
    stan_model = write_stan_model()
    stan_runner = write_stan_runner()
    stan_data, stan_meta = write_stan_data(features, df, train_mask, test_mask)
    plot_metrics(metrics_df)
    plot_calibration(pred_df)

    env = {}
    for pkg in ["cmdstanpy", "stan", "pystan", "pymc"]:
        try:
            __import__(pkg)
            env[pkg] = True
        except Exception:
            env[pkg] = False

    run_report = {
        "metrics": str(PHASE6 / "phase6_model_comparison_metrics.csv"),
        "predictions": str(PHASE6 / "phase6_ml_and_comparator_predictions.parquet"),
        "stan_model": str(stan_model),
        "stan_data": str(stan_data),
        "stan_metadata": str(stan_meta),
        "stan_runner": str(stan_runner),
        "bayesian_runtime_available": env,
        "raw_feature_medians": raw_medians,
        "selected_feature_medians": feature_medians,
    }
    (PHASE6 / "phase6_run_manifest.json").write_text(json.dumps(run_report, indent=2), encoding="utf-8")
    print(json.dumps(run_report, indent=2))
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
