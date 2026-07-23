import json

import numpy as np
import pandas as pd
import pytest

from data_processing.diode_fitting import (
    MINIMUM_FIT_POINTS,
    fit_single_diode,
    single_diode_current,
)


def test_explicit_current_satisfies_implicit_single_diode_equation():
    voltage = np.linspace(-0.2, 0.8, 50)
    iph, i0, diode_voltage, rs, rp = 0.035, 2e-9, 0.045, 1.8, 1500.0

    current = single_diode_current(voltage, iph, i0, diode_voltage, rs, rp)
    junction_voltage = voltage + current * rs
    equation_residual = (
        current
        - iph
        + i0 * np.expm1(junction_voltage / diode_voltage)
        + junction_voltage / rp
    )

    assert np.max(np.abs(equation_residual)) < 1e-12


def test_robust_fit_recovers_resistances_with_outliers():
    rng = np.random.default_rng(11)
    voltage = np.linspace(-0.15, 0.75, 140)
    truth = {
        "iph": 0.035,
        "i0": 2e-9,
        "diode_voltage": 0.045,
        "rs": 1.8,
        "rp": 1500.0,
    }
    current = single_diode_current(voltage, *truth.values())
    current += rng.normal(0.0, 3.5e-5, len(voltage))
    current[[20, 75, 110]] += truth["iph"] * np.array([0.04, -0.06, 0.05])
    dataframe = pd.DataFrame(
        {
            "Voltage [mV]": voltage * 1000.0,
            "Current [mA]": current * 1000.0,
        }
    )

    result = fit_single_diode(dataframe)

    assert result["success"] is True
    assert result["rs_ohm"] == pytest.approx(truth["rs"], rel=0.05)
    assert result["rp_kohm"] == pytest.approx(truth["rp"] / 1000.0, rel=0.08)
    assert result["initial_rs_ohm"] > 0.0
    assert result["initial_rp_kohm"] > 0.0
    assert len(result["voltage_mv"]) == 300
    assert len(result["current_ma"]) == 300
    json.dumps(result)


def test_fit_preserves_the_application_current_orientation():
    voltage = np.linspace(-0.15, 0.75, 140)
    truth = (0.035, 2e-9, 0.045, 1.8, 1500.0)
    canonical_current = single_diode_current(voltage, *truth)
    dataframe = pd.DataFrame(
        {
            "Voltage [mV]": voltage * 1000.0,
            # The normal file parser intentionally produces this sign.
            "Current [mA]": -canonical_current * 1000.0,
        }
    )

    result = fit_single_diode(dataframe)

    assert result["success"] is True
    assert result["current_orientation"] == -1
    assert result["rs_ohm"] == pytest.approx(truth[3], rel=0.01)
    assert result["rp_kohm"] == pytest.approx(truth[4] / 1000.0, rel=0.01)
    fitted_at_measurements = np.interp(
        dataframe["Voltage [mV]"], result["voltage_mv"], result["current_ma"]
    )
    assert np.sqrt(
        np.mean((fitted_at_measurements - dataframe["Current [mA]"]) ** 2)
    ) < 0.01


def test_fit_fails_cleanly_for_too_few_points():
    dataframe = pd.DataFrame(
        {
            "Voltage [mV]": np.arange(MINIMUM_FIT_POINTS - 1),
            "Current [mA]": np.arange(MINIMUM_FIT_POINTS - 1),
        }
    )

    result = fit_single_diode(dataframe)

    assert result["success"] is False
    assert result["rs_ohm"] is None
    assert result["rp_kohm"] is None
    assert result["voltage_mv"] == []


def test_fit_fails_cleanly_when_required_column_is_missing():
    result = fit_single_diode(pd.DataFrame({"Voltage [mV]": [0.0] * 10}))

    assert result["success"] is False
    assert "fehlt" in result["message"]


def test_fit_rejects_curve_that_is_not_described_by_single_diode_model():
    voltage = np.linspace(-500.0, 1500.0, 120)
    current = 100.0 * np.sin(np.linspace(0.0, 4.0 * np.pi, len(voltage)))

    result = fit_single_diode(
        pd.DataFrame({"Voltage [mV]": voltage, "Current [mA]": current})
    )

    assert result["success"] is False
    assert "nicht ausreichend" in result["message"]
