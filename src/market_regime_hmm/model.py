from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class HMMSelectionResult:
    model: GaussianHMM
    scaler: StandardScaler
    selection_table: pd.DataFrame
    labels: np.ndarray
    log_likelihood: float


def _hmm_parameter_count(n_states: int, n_features: int, covariance_type: str) -> int:
    """Approximate parameter count for information criteria."""
    start_probabilities = n_states - 1
    transition_probabilities = n_states * (n_states - 1)
    means = n_states * n_features

    if covariance_type == "diag":
        covariances = n_states * n_features
    elif covariance_type == "full":
        covariances = n_states * n_features * (n_features + 1) // 2
    else:
        raise ValueError("Only 'diag' and 'full' covariance types are supported.")

    return start_probabilities + transition_probabilities + means + covariances


def fit_hmm_with_bic_selection(
    features: pd.DataFrame,
    feature_columns: list[str],
    state_candidates: range = range(2, 6),
    covariance_type: str = "diag",
    random_state: int = 42,
) -> HMMSelectionResult:
    """Fit candidate Gaussian HMMs and choose the state count with lowest BIC."""
    x = features[feature_columns].to_numpy()
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)

    rows: list[dict[str, float]] = []
    best_model: GaussianHMM | None = None
    best_bic = np.inf

    for n_states in state_candidates:
        model = GaussianHMM(
            n_components=n_states,
            covariance_type=covariance_type,
            n_iter=1000,
            tol=1e-4,
            min_covar=1e-4,
            random_state=random_state,
            implementation="log",
        )
        model.fit(x_scaled)
        log_likelihood = float(model.score(x_scaled))
        params = _hmm_parameter_count(n_states, len(feature_columns), covariance_type)
        aic = -2.0 * log_likelihood + 2.0 * params
        bic = -2.0 * log_likelihood + params * np.log(len(x_scaled))

        rows.append(
            {
                "n_states": n_states,
                "log_likelihood": log_likelihood,
                "n_parameters": params,
                "aic": aic,
                "bic": bic,
            }
        )

        if bic < best_bic:
            best_bic = bic
            best_model = model

    if best_model is None:
        raise RuntimeError("No HMM candidate was fitted.")

    labels = best_model.predict(x_scaled)
    selection_table = pd.DataFrame(rows).sort_values("n_states").reset_index(drop=True)
    return HMMSelectionResult(
        model=best_model,
        scaler=scaler,
        selection_table=selection_table,
        labels=labels,
        log_likelihood=float(best_model.score(x_scaled)),
    )


def predict_with_model(
    model: GaussianHMM,
    scaler: StandardScaler,
    features: pd.DataFrame,
    feature_columns: list[str],
) -> np.ndarray:
    """Predict HMM states for a feature matrix using a fitted scaler/model pair."""
    return model.predict(scaler.transform(features[feature_columns].to_numpy()))
