import pytest

from scripts.compute_gci import compute


def test_gci_returns_positive_fraction():
    result = compute(phi1=1.0, phi2=1.04, phi3=1.12, h1=0.5, h2=1.0, h3=2.0)
    assert result["apparent_order"] == pytest.approx(1.0)
    assert result["gci_fine_fraction"] > 0


def test_gci_rejects_wrong_grid_order():
    with pytest.raises(ValueError):
        compute(1.0, 1.1, 1.2, 2.0, 1.0, 0.5)

