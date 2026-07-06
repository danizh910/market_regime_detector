import numpy as np
import pandas as pd

from market_regime_hmm.features import FEATURE_COLUMNS, engineer_features


def test_engineer_features_creates_expected_columns():
    dates = pd.bdate_range("2020-01-01", periods=180)
    close = 100 * np.exp(np.linspace(0, 0.25, len(dates)))
    prices = pd.DataFrame({"close": close}, index=dates)

    features = engineer_features(prices)

    assert set(FEATURE_COLUMNS).issubset(features.columns)
    assert not features[FEATURE_COLUMNS].isna().any().any()
    assert (features["realized_vol_short"] >= 0).all()
