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
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler


PHASE3 = PROJECT / "data/processed/phase3"
PHASE5 = PROJECT / "data/processed/phase5"
TABLE_DIR = PROJECT / "outputs/tables"
FIG_DIR = PROJECT / "outputs/figures/phase5"

RANDOM_SEED = 20260701
POSTERIOR_DRAWS = 1000
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
    "muted": "#6d7f86",
}

GEOMETRY_TERRAIN = [
    "length_m",
    "kv_sort",
    "mid_lon",
    "mid_lat",
    "dem_elevation_m",
]

LANDFIRE_STATIC = [
    "landfire_fbfm40",
    "landfire_canopy_cover_pct",
    "landfire_canopy_height_m",
    "landfire_canopy_base_height_m",
    "landfire_canopy_bulk_density",
]

GRIDMET_DYNAMIC = [
    "gridmet_fm100_p05",
    "gridmet_fm100_mean",
    "gridmet_fm1000_p05",
    "gridmet_fm1000_mean",
    "gridmet_vpd_p95",
    "gridmet_vpd_mean",
    "gridmet_erc_p95",
    "gridmet_erc_mean",
    "gridmet_bi_p95",
    "gridmet_bi_mean",
    "gridmet_vs_p95",
    "gridmet_vs_mean",
    "gridmet_rmin_p05",
    "gridmet_rmin_mean",
    "gridmet_pr_sum",
    "gridmet_pr_p95",
]

PHYSICS_ENGINEERED = [
    "phys_dryness_index",
    "phys_fuel_structure_index",
    "phys_dryness_x_fuel",
]

SELECTED_PHYSICS_CORE = [
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
] + PHYSICS_ENGINEERED

MODEL_SPECS = [
    {
        "model_id": "M0_geometry_terrain",
        "label": "M0 geometry + terrain",
        "features": GEOMETRY_TERRAIN,
    },
    {
        "model_id": "M1_static_fuel",
        "label": "M1 + LANDFIRE fuel",
        "features": GEOMETRY_TERRAIN + LANDFIRE_STATIC,
    },
    {
        "model_id": "M2_dynamic_weather",
        "label": "M2 + gridMET weather",
        "features": GEOMETRY_TERRAIN + GRIDMET_DYNAMIC,
    },
    {
        "model_id": "M3_static_dynamic",
        "label": "M3 fuel + weather",
        "features": GEOMETRY_TERRAIN + LANDFIRE_STATIC + GRIDMET_DYNAMIC,
    },
    {
        "model_id": "M4_physics_interaction",
        "label": "M4 physics interaction",
        "features": GEOMETRY_TERRAIN + LANDFIRE_STATIC + GRIDMET_DYNAMIC + PHYSICS_ENGINEERED,
    },
    {
        "model_id": "M5_selected_physics_core",
        "label": "M5 selected physics core",
        "features": SELECTED_PHYSICS_CORE,
    },
]


def ensure_dirs():
    PHASE5.mkdir(parents=True, exist_ok=True)
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
    raw = GRIDMET_DYNAMIC + LANDFIRE_STATIC + ["dem_elevation_m"]
    med = df.loc[train_mask, raw].median(numeric_only=True)
    for col in raw:
        df[col] = df[col].fillna(med[col])
    scaler = StandardScaler()
    z = pd.DataFrame(
        scaler.fit_transform(df.loc[train_mask, raw]),
        columns=raw,
        index=df.index[train_mask],
    )
    z_all = pd.DataFrame(scaler.transform(df[raw]), columns=raw, index=df.index)
    df["phys_dryness_index"] = z_all[
        ["gridmet_vpd_p95", "gridmet_erc_p95", "gridmet_bi_p95", "gridmet_vs_p95"]
    ].mean(axis=1) - z_all[["gridmet_fm100_p05", "gridmet_fm1000_p05", "gridmet_rmin_p05", "gridmet_pr_sum"]].mean(axis=1)
    df["phys_fuel_structure_index"] = z_all[
        ["landfire_canopy_cover_pct", "landfire_canopy_height_m", "landfire_canopy_bulk_density"]
    ].mean(axis=1)
    df["phys_dryness_x_fuel"] = df["phys_dryness_index"] * df["phys_fuel_structure_index"]
    return df


def prepare_matrix(df, train_mask, features):
    work = df[features].copy()
    for col in features:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    med = work.loc[train_mask].median(numeric_only=True)
    work = work.fillna(med)
    scaler = StandardScaler()
    X_train = scaler.fit_transform(work.loc[train_mask])
    X_all = scaler.transform(work)
    return X_train, X_all


def add_intercept(X):
    return np.column_stack([np.ones(X.shape[0]), X])


def fit_laplace_logit(X, y, prior_sd=2.0, intercept_prior_sd=5.0):
    X1 = add_intercept(X)
    y = y.astype(float)
    prior_prec = np.full(X1.shape[1], 1.0 / (prior_sd * prior_sd))
    prior_prec[0] = 1.0 / (intercept_prior_sd * intercept_prior_sd)

    def objective(beta):
        p = expit(X1 @ beta)
        eps = 1e-12
        neg_ll = -np.sum(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps))
        return neg_ll + 0.5 * np.sum(prior_prec * beta * beta)

    def gradient(beta):
        p = expit(X1 @ beta)
        return X1.T @ (p - y) + prior_prec * beta

    result = minimize(
        objective,
        np.zeros(X1.shape[1]),
        jac=gradient,
        method="L-BFGS-B",
        options={"maxiter": 1500, "ftol": 1e-9},
    )
    if not result.success:
        raise RuntimeError(result.message)
    beta = result.x
    p = expit(X1 @ beta)
    w = p * (1 - p)
    hessian = X1.T @ (X1 * w[:, None]) + np.diag(prior_prec)
    cov = np.linalg.pinv(hessian)
    return beta, cov, result.fun


def posterior_predictive_mean(X, beta, cov, draws, seed_offset=0):
    rng = np.random.default_rng(RANDOM_SEED + seed_offset)
    beta_draws = rng.multivariate_normal(beta, cov + np.eye(len(beta)) * 1e-8, size=draws)
    X1 = add_intercept(X)
    acc = np.zeros(X.shape[0], dtype="float64")
    chunk = 250
    for start in range(0, draws, chunk):
        draw = beta_draws[start : start + chunk]
        acc += expit(X1 @ draw.T).sum(axis=1)
    return acc / draws


def segment_top10_capture(df, score_col, test_mask):
    test = df.loc[test_mask, ["segment_id", LABEL, score_col]].copy()
    seg = test.groupby("segment_id", as_index=False).agg(
        observed=(LABEL, "sum"),
        score=(score_col, "mean"),
    )
    k = int(np.ceil(0.10 * len(seg)))
    selected = seg.nlargest(k, "score")
    positives = test[LABEL].sum()
    return {
        "segment_top10_k": k,
        "segment_top10_capture_rate": float(selected["observed"].sum() / max(positives, 1)),
        "segment_top10_positive_rate": float((selected["observed"] > 0).mean()),
    }


def evaluate(df, score_col, test_mask):
    y = df.loc[test_mask, LABEL].to_numpy()
    score = df.loc[test_mask, score_col].to_numpy()
    cutoff = np.quantile(score, 0.90)
    selected = score >= cutoff
    metrics = {
        "roc_auc": float(roc_auc_score(y, score)),
        "pr_auc": float(average_precision_score(y, score)),
        "brier": float(brier_score_loss(y, score)),
        "row_top10_capture_rate": float(y[selected].sum() / max(y.sum(), 1)),
        "row_top10_positive_rate": float(y[selected].mean()),
    }
    metrics.update(segment_top10_capture(df, score_col, test_mask))
    return metrics


def run_ablation(df):
    train_mask = df["year"].isin(TRAIN_YEARS).to_numpy()
    test_mask = df["year"].isin(TEST_YEARS).to_numpy()
    y_train = df.loc[train_mask, LABEL].to_numpy()
    all_predictions = df[["segment_id", "year", LABEL]].copy()
    metrics = []
    coef_rows = []
    for idx, spec in enumerate(MODEL_SPECS):
        print(f"[fit] {spec['model_id']}")
        X_train, X_all = prepare_matrix(df, train_mask, spec["features"])
        beta, cov, objective = fit_laplace_logit(X_train, y_train)
        pred = posterior_predictive_mean(X_all, beta, cov, POSTERIOR_DRAWS, seed_offset=idx)
        pred_col = f"pred_{spec['model_id']}"
        all_predictions[pred_col] = pred
        row = {
            "model_id": spec["model_id"],
            "label": spec["label"],
            "n_features": len(spec["features"]),
            "train_rows": int(train_mask.sum()),
            "train_positive_rows": int(y_train.sum()),
            "test_rows": int(test_mask.sum()),
            "test_positive_rows": int(df.loc[test_mask, LABEL].sum()),
            "objective": float(objective),
        }
        row.update(evaluate(all_predictions, pred_col, test_mask))
        metrics.append(row)
        for term, mean, sd in zip(["intercept"] + spec["features"], beta, np.sqrt(np.diag(cov))):
            coef_rows.append(
                {
                    "model_id": spec["model_id"],
                    "term": term,
                    "posterior_mean": float(mean),
                    "posterior_sd": float(sd),
                    "ci95_low": float(mean - 1.96 * sd),
                    "ci95_high": float(mean + 1.96 * sd),
                }
            )
    return pd.DataFrame(metrics), all_predictions, pd.DataFrame(coef_rows)


def style_ax(ax):
    ax.set_facecolor(COLORS["paper"])
    ax.grid(True, axis="y", color=COLORS["grid"], linewidth=0.45, alpha=0.75)
    ax.tick_params(labelsize=7, colors=COLORS["axis"], length=2.5, width=0.5)
    for spine in ax.spines.values():
        spine.set_color("#4f565c")
        spine.set_linewidth(0.55)


def make_metric_figure(metrics):
    fig, axes = plt.subplots(1, 4, figsize=(12.0, 3.7), dpi=300)
    fig.patch.set_facecolor(COLORS["paper"])
    panels = [
        ("ROC-AUC", "roc_auc"),
        ("PR-AUC", "pr_auc"),
        ("Row top-10% capture", "row_top10_capture_rate"),
        ("Segment top-10% capture", "segment_top10_capture_rate"),
    ]
    x = np.arange(len(metrics))
    labels = [model_id.split("_")[0] for model_id in metrics["model_id"]]
    bar_colors = [COLORS["muted"]] * len(metrics)
    bar_colors[-1] = COLORS["accent"]
    for ax, (title, col) in zip(axes, panels):
        bars = ax.bar(x, metrics[col], color=bar_colors, alpha=0.9, width=0.68)
        ax.set_xticks(x, labels, rotation=0)
        ax.set_title(title, fontsize=9, color=COLORS["text"], pad=7)
        ymax = max(metrics[col].max() * 1.20, 0.01)
        ax.set_ylim(0, ymax)
        for bar, value in zip(bars, metrics[col]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + ymax * 0.02,
                f"{value:.3f}",
                ha="center",
                va="bottom",
                fontsize=6.3,
                color=COLORS["text"],
            )
        style_ax(ax)
        ax.grid(axis="x", visible=False)
    fig.suptitle("Phase 5 ablation: public-data modules improve exposure ranking", fontsize=11, color=COLORS["text"])
    fig.text(
        0.5,
        0.01,
        "Temporal holdout uses 2022-2023. M0 geometry/terrain; M1 adds LANDFIRE; M2 adds gridMET; M3 combines fuel/weather; M4 adds all interactions; M5 is selected physics core.",
        ha="center",
        va="bottom",
        fontsize=7.1,
        color=COLORS["axis"],
    )
    fig.subplots_adjust(left=0.045, right=0.995, top=0.77, bottom=0.34, wspace=0.36)
    out = FIG_DIR / "phase5_ablation_validation_metrics.png"
    fig.savefig(out, bbox_inches="tight", facecolor=COLORS["paper"])
    plt.close(fig)
    return out


def make_brier_figure(metrics):
    fig, ax = plt.subplots(figsize=(6.8, 3.8), dpi=300)
    fig.patch.set_facecolor(COLORS["paper"])
    x = np.arange(len(metrics))
    labels = [model_id.split("_")[0] for model_id in metrics["model_id"]]
    ax.plot(x, metrics["brier"], marker="o", color=COLORS["compare"], linewidth=1.6, markersize=4.5)
    ax.scatter([x[-1]], [metrics["brier"].iloc[-1]], color=COLORS["accent"], s=28, zorder=5)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Brier score", fontsize=8, color=COLORS["axis"])
    ax.set_title("Brier score across ablations", fontsize=10, color=COLORS["text"], pad=7)
    style_ax(ax)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    out = FIG_DIR / "phase5_ablation_brier_scores.png"
    fig.savefig(out, bbox_inches="tight", facecolor=COLORS["paper"])
    plt.close(fig)
    return out


def write_outputs(metrics, predictions, coefficients):
    metrics_csv = PHASE5 / "phase5_ablation_metrics.csv"
    metrics_parquet = PHASE5 / "phase5_ablation_metrics.parquet"
    pred_parquet = PHASE5 / "phase5_ablation_predictions.parquet"
    coef_csv = PHASE5 / "phase5_ablation_coefficients.csv"
    metrics.to_csv(metrics_csv, index=False)
    metrics.to_parquet(metrics_parquet, index=False)
    predictions.to_parquet(pred_parquet, index=False)
    coefficients.to_csv(coef_csv, index=False)
    report = {
        "method": "Bayesian logistic ablation with Laplace posterior predictive mean",
        "label": LABEL,
        "train_years": TRAIN_YEARS,
        "test_years": TEST_YEARS,
        "posterior_draws_per_model": POSTERIOR_DRAWS,
        "models": MODEL_SPECS,
        "outputs": {
            "metrics_csv": str(metrics_csv),
            "metrics_parquet": str(metrics_parquet),
            "predictions_parquet": str(pred_parquet),
            "coefficients_csv": str(coef_csv),
        },
    }
    report_path = TABLE_DIR / "phase5_ablation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


def main():
    ensure_dirs()
    df = load_model_table()
    train_mask = df["year"].isin(TRAIN_YEARS).to_numpy()
    df = add_physics_features(df, train_mask)
    metrics, predictions, coefficients = run_ablation(df)
    report_path = write_outputs(metrics, predictions, coefficients)
    fig1 = make_metric_figure(metrics)
    fig2 = make_brier_figure(metrics)
    print(metrics.to_string(index=False))
    print(f"[report] {report_path}")
    print(f"[figure] {fig1}")
    print(f"[figure] {fig2}")


if __name__ == "__main__":
    main()
