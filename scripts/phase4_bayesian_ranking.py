import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEPS = PROJECT / ".python_deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler


PHASE1 = PROJECT / "data/processed/phase1"
PHASE3 = PROJECT / "data/processed/phase3"
PHASE4 = PROJECT / "data/processed/phase4"
TABLE_DIR = PROJECT / "outputs/tables"
FIG_DIR = PROJECT / "outputs/figures/phase4"

RANDOM_SEED = 20260701
POSTERIOR_DRAWS = 1500
TRAIN_YEARS = [2017, 2018, 2019, 2020, 2021]
TEST_YEARS = [2022, 2023]
LABEL = "exogenous_fire_exposure"

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

MODEL_FEATURES = RAW_FEATURES + [
    "phys_dryness_index",
    "phys_fuel_structure_index",
    "phys_dryness_x_fuel",
]

COLORS = {
    "paper": "#fbfaf6",
    "text": "#24292c",
    "axis": "#596168",
    "grid": "#d8d5cd",
    "accent": "#005f73",
    "compare": "#c27a15",
    "quiet": "#d9d6ce",
}


def ensure_dirs():
    PHASE4.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_model_table():
    parquet = PHASE3 / "segment_year_model_table.parquet"
    if parquet.exists():
        df = pd.read_parquet(parquet)
    else:
        df = pd.read_csv(PHASE3 / "segment_year_model_table.csv")
    return df.sort_values(["segment_id", "year"]).reset_index(drop=True)


def add_engineered_features(df, train_mask):
    df = df.copy()
    medians = df.loc[train_mask, RAW_FEATURES].median(numeric_only=True)
    for col in RAW_FEATURES:
        df[col] = df[col].fillna(medians[col])

    scaler = StandardScaler()
    z = pd.DataFrame(
        scaler.fit_transform(df.loc[train_mask, RAW_FEATURES]),
        columns=RAW_FEATURES,
        index=df.index[train_mask],
    )
    z_all = pd.DataFrame(
        scaler.transform(df[RAW_FEATURES]),
        columns=RAW_FEATURES,
        index=df.index,
    )

    df["phys_dryness_index"] = z_all[
        ["gridmet_vpd_p95", "gridmet_erc_p95", "gridmet_bi_p95", "gridmet_vs_p95"]
    ].mean(axis=1) - z_all[["gridmet_fm100_p05", "gridmet_fm1000_p05", "gridmet_rmin_p05", "gridmet_pr_sum"]].mean(axis=1)
    df["phys_fuel_structure_index"] = z_all[
        ["landfire_canopy_cover_pct", "landfire_canopy_height_m", "landfire_canopy_bulk_density"]
    ].mean(axis=1)
    df["phys_dryness_x_fuel"] = df["phys_dryness_index"] * df["phys_fuel_structure_index"]

    deterministic_raw = (
        0.56 * df["phys_dryness_index"]
        + 0.30 * df["phys_fuel_structure_index"]
        + 0.14 * z_all["dem_elevation_m"]
    )
    lo, hi = deterministic_raw.loc[train_mask].quantile([0.01, 0.99])
    df["deterministic_risk_score"] = ((deterministic_raw - lo) / (hi - lo)).clip(0, 1)

    model_scaler = StandardScaler()
    X_train = model_scaler.fit_transform(df.loc[train_mask, MODEL_FEATURES])
    X_all = model_scaler.transform(df[MODEL_FEATURES])
    return df, X_train, X_all, medians.to_dict()


def add_intercept(X):
    return np.column_stack([np.ones(X.shape[0]), X])


def fit_laplace_logit(X, y, prior_sd=2.0, intercept_prior_sd=5.0):
    X1 = add_intercept(X)
    y = y.astype(float)
    prior_prec = np.full(X1.shape[1], 1.0 / (prior_sd * prior_sd))
    prior_prec[0] = 1.0 / (intercept_prior_sd * intercept_prior_sd)

    def objective(beta):
        eta = X1 @ beta
        p = expit(eta)
        eps = 1e-12
        neg_ll = -np.sum(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps))
        penalty = 0.5 * np.sum(prior_prec * beta * beta)
        return neg_ll + penalty

    def gradient(beta):
        eta = X1 @ beta
        p = expit(eta)
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
    return beta, cov, result


def posterior_draws(beta, cov, n_draws):
    rng = np.random.default_rng(RANDOM_SEED)
    jitter = np.eye(len(beta)) * 1e-8
    return rng.multivariate_normal(beta, cov + jitter, size=n_draws)


def calibrate_deterministic_probability(df, train_mask):
    score = df["deterministic_risk_score"].to_numpy(dtype="float64")
    y = df[LABEL].to_numpy(dtype="float64")
    X = np.column_stack([np.ones(train_mask.sum()), score[train_mask]])
    y_train = y[train_mask]
    prior_prec = np.array([1.0 / 25.0, 1.0 / 4.0])

    def objective(beta):
        p = expit(X @ beta)
        eps = 1e-12
        return -np.sum(y_train * np.log(p + eps) + (1 - y_train) * np.log(1 - p + eps)) + 0.5 * np.sum(
            prior_prec * beta * beta
        )

    def gradient(beta):
        p = expit(X @ beta)
        return X.T @ (p - y_train) + prior_prec * beta

    result = minimize(objective, np.zeros(2), jac=gradient, method="L-BFGS-B")
    if not result.success:
        raise RuntimeError(result.message)
    X_all = np.column_stack([np.ones(len(df)), score])
    return expit(X_all @ result.x), result.x


def summarize_segment_posterior(df, X_all, beta_draws, tau):
    X1 = add_intercept(X_all)
    segments = df["segment_id"].drop_duplicates().to_numpy()
    segment_codes = pd.Categorical(df["segment_id"], categories=segments).codes
    n_segments = len(segments)
    draw_segment_p = np.empty((len(beta_draws), n_segments), dtype="float32")
    for draw_idx, beta in enumerate(beta_draws):
        p = expit(X1 @ beta)
        sums = np.bincount(segment_codes, weights=p, minlength=n_segments)
        counts = np.bincount(segment_codes, minlength=n_segments)
        draw_segment_p[draw_idx] = sums / counts
    top_k = int(np.ceil(0.10 * n_segments))
    rank_top = np.zeros_like(draw_segment_p, dtype=bool)
    for draw_idx in range(draw_segment_p.shape[0]):
        top_idx = np.argpartition(-draw_segment_p[draw_idx], top_k - 1)[:top_k]
        rank_top[draw_idx, top_idx] = True
    summary = pd.DataFrame(
        {
            "segment_id": segments,
            "posterior_mean_exposure_prob": draw_segment_p.mean(axis=0),
            "posterior_sd_exposure_prob": draw_segment_p.std(axis=0),
            "p_exposure_gt_threshold": (draw_segment_p > tau).mean(axis=0),
            "p_rank_top10": rank_top.mean(axis=0),
        }
    )
    return summary, draw_segment_p


def predictive_mean(X, beta_draws, chunk=250):
    X1 = add_intercept(X)
    acc = np.zeros(X1.shape[0], dtype="float64")
    for start in range(0, len(beta_draws), chunk):
        draws = beta_draws[start : start + chunk]
        acc += expit(X1 @ draws.T).sum(axis=1)
    return acc / len(beta_draws)


def metrics_for_holdout(df, y_prob, deterministic_prob):
    test = df["year"].isin(TEST_YEARS).to_numpy()
    y = df.loc[test, LABEL].to_numpy()
    bayes = y_prob[test]
    det = df.loc[test, "deterministic_risk_score"].to_numpy()
    det_prob = deterministic_prob[test]
    out = {
        "test_years": TEST_YEARS,
        "test_rows": int(test.sum()),
        "test_positive_rows": int(y.sum()),
        "bayesian_roc_auc": float(roc_auc_score(y, bayes)),
        "bayesian_pr_auc": float(average_precision_score(y, bayes)),
        "bayesian_brier": float(brier_score_loss(y, bayes)),
        "deterministic_roc_auc": float(roc_auc_score(y, det)),
        "deterministic_pr_auc": float(average_precision_score(y, det)),
        "deterministic_raw_score_brier": float(brier_score_loss(y, det)),
        "deterministic_calibrated_brier": float(brier_score_loss(y, det_prob)),
    }
    for name, score in {"bayesian": bayes, "deterministic": det}.items():
        cutoff = np.quantile(score, 0.90)
        selected = score >= cutoff
        out[f"{name}_top10_capture_rate"] = float(y[selected].sum() / max(y.sum(), 1))
        out[f"{name}_top10_positive_rate"] = float(y[selected].mean())
    return out


def write_outputs(df, segment_summary, y_prob, deterministic_prob, metrics, tau):
    observed = (
        df.groupby("segment_id", as_index=False)[LABEL]
        .sum()
        .rename(columns={LABEL: "observed_exogenous_exposure_years"})
    )
    det = (
        df.groupby("segment_id", as_index=False)["deterministic_risk_score"]
        .mean()
        .rename(columns={"deterministic_risk_score": "deterministic_segment_score"})
    )
    coords = df[["segment_id", "mid_lon", "mid_lat"]].drop_duplicates("segment_id")
    static_cols = [
        "segment_id",
        "dem_elevation_m",
        "landfire_fbfm40",
        "landfire_canopy_cover_pct",
        "landfire_canopy_height_m",
        "landfire_canopy_base_height_m",
        "landfire_canopy_bulk_density",
    ]
    static = df[static_cols].drop_duplicates("segment_id")
    segment_summary = (
        segment_summary.merge(det, on="segment_id", how="left")
        .merge(observed, on="segment_id", how="left")
        .merge(coords, on="segment_id", how="left")
        .merge(static, on="segment_id", how="left")
    )
    segment_summary["deterministic_rank_percentile"] = segment_summary["deterministic_segment_score"].rank(pct=True)
    segment_summary["posterior_mean_rank_percentile"] = segment_summary["posterior_mean_exposure_prob"].rank(pct=True)
    segment_summary["decision_threshold_tau"] = tau
    segment_summary["posterior_top10_by_mean"] = (
        segment_summary["posterior_mean_rank_percentile"] >= 0.90
    ).astype(int)
    segment_summary["deterministic_top10"] = (segment_summary["deterministic_rank_percentile"] >= 0.90).astype(int)

    row_pred = df[["segment_id", "year", LABEL, "deterministic_risk_score"]].copy()
    row_pred["deterministic_calibrated_prob"] = deterministic_prob
    row_pred["bayesian_posterior_predictive_mean"] = y_prob

    segment_csv = PHASE4 / "phase4_segment_posterior_decision_metrics.csv"
    segment_parquet = PHASE4 / "phase4_segment_posterior_decision_metrics.parquet"
    row_csv = PHASE4 / "phase4_segment_year_predictions.csv"
    row_parquet = PHASE4 / "phase4_segment_year_predictions.parquet"
    segment_summary.to_csv(segment_csv, index=False)
    segment_summary.to_parquet(segment_parquet, index=False)
    row_pred.to_csv(row_csv, index=False)
    row_pred.to_parquet(row_parquet, index=False)

    report = {
        "method": "Bayesian logistic regression with Laplace posterior approximation",
        "label": LABEL,
        "train_years": TRAIN_YEARS,
        "test_years": TEST_YEARS,
        "posterior_draws": POSTERIOR_DRAWS,
        "decision_threshold_tau": tau,
        "top_decile_k": int(np.ceil(0.10 * segment_summary.shape[0])),
        "features": MODEL_FEATURES,
        "metrics": metrics,
        "outputs": {
            "segment_csv": str(segment_csv),
            "segment_parquet": str(segment_parquet),
            "row_csv": str(row_csv),
            "row_parquet": str(row_parquet),
        },
    }
    report_path = TABLE_DIR / "phase4_bayesian_ranking_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return segment_summary, row_pred, report


def style_ax(ax):
    ax.set_facecolor(COLORS["paper"])
    ax.grid(True, color=COLORS["grid"], linewidth=0.45, alpha=0.7)
    ax.tick_params(labelsize=7, colors=COLORS["axis"], length=2.5, width=0.5)
    for spine in ax.spines.values():
        spine.set_color("#4f565c")
        spine.set_linewidth(0.55)


def make_rank_figure(segment_summary):
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.5), dpi=300)
    fig.patch.set_facecolor(COLORS["paper"])
    ax = axes[0]
    sc = ax.scatter(
        segment_summary["deterministic_rank_percentile"],
        segment_summary["p_rank_top10"],
        c=segment_summary["observed_exogenous_exposure_years"],
        cmap="YlGnBu",
        s=11,
        alpha=0.72,
        linewidth=0,
    )
    ax.axhline(0.5, color=COLORS["compare"], linewidth=0.8, linestyle="--")
    ax.axvline(0.9, color=COLORS["compare"], linewidth=0.8, linestyle="--")
    ax.set_xlabel("Deterministic rank percentile", fontsize=8, color=COLORS["axis"])
    ax.set_ylabel("Posterior P(rank in top 10%)", fontsize=8, color=COLORS["axis"])
    ax.set_title("Ranking uncertainty changes the decision set", fontsize=9.4, color=COLORS["text"])
    style_ax(ax)
    cb = fig.colorbar(sc, ax=ax, shrink=0.78)
    cb.set_label("Observed exposure years", fontsize=7, color=COLORS["axis"])
    cb.ax.tick_params(labelsize=6, colors=COLORS["axis"])

    ax = axes[1]
    ax.scatter(
        segment_summary["posterior_mean_exposure_prob"],
        segment_summary["p_exposure_gt_threshold"],
        c=segment_summary["p_rank_top10"],
        cmap="cividis",
        s=11,
        alpha=0.72,
        linewidth=0,
    )
    ax.set_xlabel("Posterior mean annual exposure probability", fontsize=8, color=COLORS["axis"])
    ax.set_ylabel("P(exposure > threshold)", fontsize=8, color=COLORS["axis"])
    ax.set_title("Exceedance probability is not a single score", fontsize=9.4, color=COLORS["text"])
    style_ax(ax)
    fig.suptitle("Deterministic score versus Bayesian posterior decision metrics", fontsize=11, color=COLORS["text"])
    fig.tight_layout(rect=(0, 0, 1, 0.93), w_pad=1.6)
    out = FIG_DIR / "phase4_deterministic_vs_bayesian_ranking.png"
    fig.savefig(out, bbox_inches="tight", facecolor=COLORS["paper"])
    plt.close(fig)
    return out


def make_decision_map(segment_summary):
    segments = gpd.read_file(PHASE1 / "segments_1km.gpkg")
    if segments.crs is None:
        segments = segments.set_crs("EPSG:4326")
    gdf = segments.to_crs("EPSG:3310").merge(segment_summary, on="segment_id", how="left")
    fig, axes = plt.subplots(1, 3, figsize=(11.3, 4.8), dpi=300)
    fig.patch.set_facecolor(COLORS["paper"])
    specs = [
        ("deterministic_segment_score", "Deterministic score", "Score", "cividis"),
        ("p_exposure_gt_threshold", "P(exposure > threshold)", "Probability", "YlGnBu"),
        ("p_rank_top10", "P(rank in top 10%)", "Probability", "YlGnBu"),
    ]
    for ax, (col, title, label, cmap) in zip(axes, specs):
        gdf.plot(
            ax=ax,
            column=col,
            cmap=cmap,
            linewidth=0.34,
            alpha=0.92,
            legend=True,
            legend_kwds={"label": label, "shrink": 0.68},
            missing_kwds={"color": COLORS["quiet"], "linewidth": 0.2},
        )
        ax.set_title(title, fontsize=9.2, color=COLORS["text"], pad=7)
        ax.set_axis_off()
        ax.set_facecolor(COLORS["paper"])
    fig.suptitle("Phase 4 decision outputs for external wildfire exposure ranking", fontsize=11, color=COLORS["text"], y=0.985)
    fig.text(
        0.5,
        0.026,
        "Bayesian panels summarize posterior draws from the segment-year external exposure model; transmission lines are receptor assets, not ignition sources.",
        ha="center",
        va="bottom",
        fontsize=7.1,
        color=COLORS["axis"],
    )
    fig.subplots_adjust(left=0.02, right=0.985, top=0.87, bottom=0.09, wspace=0.08)
    out = FIG_DIR / "phase4_decision_metric_maps.png"
    fig.savefig(out, bbox_inches="tight", facecolor=COLORS["paper"])
    plt.close(fig)
    return out


def make_validation_figure(metrics):
    fig, axes = plt.subplots(1, 4, figsize=(11.4, 3.3), dpi=300)
    fig.patch.set_facecolor(COLORS["paper"])
    panels = [
        ("ROC-AUC", metrics["bayesian_roc_auc"], metrics["deterministic_roc_auc"], True),
        ("PR-AUC", metrics["bayesian_pr_auc"], metrics["deterministic_pr_auc"], True),
        ("Top-10% capture", metrics["bayesian_top10_capture_rate"], metrics["deterministic_top10_capture_rate"], True),
        ("Brier score", metrics["bayesian_brier"], metrics["deterministic_calibrated_brier"], False),
    ]
    for ax, (title, bayes, det, higher_better) in zip(axes, panels):
        bars = ax.bar([0, 1], [det, bayes], color=[COLORS["compare"], COLORS["accent"]], width=0.62)
        ax.set_xticks([0, 1], ["Deterministic", "Bayesian"], rotation=22, ha="right")
        ax.set_title(title, fontsize=9, color=COLORS["text"], pad=7)
        ymax = max(det, bayes) * 1.22 if max(det, bayes) > 0 else 1
        ax.set_ylim(0, ymax)
        for bar, value in zip(bars, [det, bayes]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + ymax * 0.025,
                f"{value:.3f}",
                ha="center",
                va="bottom",
                fontsize=7,
                color=COLORS["text"],
            )
        style_ax(ax)
        ax.grid(axis="x", visible=False)
    fig.suptitle("Temporal holdout validation, 2022-2023", fontsize=11, color=COLORS["text"], y=0.99)
    fig.text(
        0.5,
        0.015,
        "Brier comparison uses calibrated deterministic probabilities; ranking metrics use the deterministic physics score directly.",
        ha="center",
        va="bottom",
        fontsize=7.0,
        color=COLORS["axis"],
    )
    fig.subplots_adjust(left=0.05, right=0.99, top=0.79, bottom=0.29, wspace=0.42)
    out = FIG_DIR / "phase4_temporal_holdout_validation.png"
    fig.savefig(out, bbox_inches="tight", facecolor=COLORS["paper"])
    plt.close(fig)
    return out


def main():
    ensure_dirs()
    df = load_model_table()
    train_mask = df["year"].isin(TRAIN_YEARS).to_numpy()
    df, X_train, X_all, medians = add_engineered_features(df, train_mask)
    y_train = df.loc[train_mask, LABEL].to_numpy()
    tau = float(y_train.mean())
    print(f"[fit] train rows={len(y_train)} positives={int(y_train.sum())} tau={tau:.6f}")
    beta, cov, result = fit_laplace_logit(X_train, y_train)
    print(f"[fit] converged objective={result.fun:.3f}")
    beta_draws = posterior_draws(beta, cov, POSTERIOR_DRAWS)
    y_prob = predictive_mean(X_all, beta_draws)
    deterministic_prob, det_calibration_beta = calibrate_deterministic_probability(df, train_mask)
    metrics = metrics_for_holdout(df, y_prob, deterministic_prob)
    segment_summary, _, report = write_outputs(
        df,
        summarize_segment_posterior(df, X_all, beta_draws, tau)[0],
        y_prob,
        deterministic_prob,
        metrics,
        tau,
    )
    rank_fig = make_rank_figure(segment_summary)
    map_fig = make_decision_map(segment_summary)
    validation_fig = make_validation_figure(metrics)
    coef = pd.DataFrame(
        {
            "term": ["intercept"] + MODEL_FEATURES,
            "posterior_mean": beta,
            "posterior_sd": np.sqrt(np.diag(cov)),
        }
    )
    coef["ci95_low"] = coef["posterior_mean"] - 1.96 * coef["posterior_sd"]
    coef["ci95_high"] = coef["posterior_mean"] + 1.96 * coef["posterior_sd"]
    coef.to_csv(PHASE4 / "phase4_laplace_logit_coefficients.csv", index=False)
    pd.DataFrame(
        {
            "term": ["intercept", "deterministic_risk_score"],
            "coefficient": det_calibration_beta,
        }
    ).to_csv(PHASE4 / "phase4_deterministic_calibration_coefficients.csv", index=False)
    print(json.dumps(report["metrics"], indent=2))
    print(f"[figure] {rank_fig}")
    print(f"[figure] {map_fig}")
    print(f"[figure] {validation_fig}")


if __name__ == "__main__":
    main()
