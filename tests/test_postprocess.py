import pandas as pd
import pytest

from scripts.postprocess import add_interference_metrics, validate_frame


def frame(case_id: str, cm: float, mbase: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "case_id": case_id,
                "wind_angle": 45,
                "spacing_ratio": None if case_id.startswith("BASE") else 0.5,
                "row_id": 1,
                "Cd": 0.1,
                "Cl": 0.2,
                "Cm": cm,
                "Fx": 1.0,
                "Fy": 2.0,
                "Fz": 3.0,
                "Mx": 4.0,
                "My": 5.0,
                "Mz": 6.0,
                "Mbase": mbase,
            }
        ]
    )


def test_interference_metrics():
    obstacle = frame("OBS_S050_A045", 0.4, 12.0)
    baseline = frame("BASE_A045", 0.2, 10.0)
    validate_frame(obstacle, __file__)
    result = add_interference_metrics(obstacle, baseline)
    assert result.loc[0, "IF_M"] == pytest.approx(2.0)
    assert result.loc[0, "K_M"] == pytest.approx(1.2)

