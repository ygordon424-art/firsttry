import pandas as pd
import pytest

from scripts.structural_mapping import map_loads


def test_explicit_structural_mapping():
    loads = pd.DataFrame([{"Fx": 10.0, "My": 3.0}])
    model = {
        "horizontal_force_axis": "Fx",
        "overturning_moment_axis": "My",
        "load_height": 2.0,
        "column_spacing": 1.0,
        "brace_angle_degrees": 60.0,
    }
    mapped = map_loads(loads, model)
    assert mapped.loc[0, "M_base"] == pytest.approx(23.0)
    assert mapped.loc[0, "T_anchor"] == pytest.approx(23.0)
    assert mapped.loc[0, "N_brace"] == pytest.approx(20.0)

