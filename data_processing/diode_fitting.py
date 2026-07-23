"""Robust single-diode-model fitting for measured I-V curves.

The public function in this module accepts the units used by the application
(mV and mA), while the model and optimizer use SI units internally.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.special import wrightomega


MINIMUM_FIT_POINTS = 8


def single_diode_current(voltage, iph, i0, diode_voltage, rs, rp):
    """Return single-diode-model current for ``voltage`` (all in SI units).

    The model is

        I = Iph - I0 * (exp((V + I*Rs) / a) - 1)
            - (V + I*Rs) / Rp

    where ``a`` is the effective diode voltage (n * Ns * kT/q).  The explicit
    Lambert-W solution is evaluated via Wright omega in log space.  This avoids
    overflow in the exponential during nonlinear optimization.
    """

    voltage = np.asarray(voltage, dtype=float)
    conductance_factor = 1.0 + rs / rp
    log_argument = (
        math.log(rs)
        + math.log(i0)
        - math.log(diode_voltage * conductance_factor)
        + (rs * (iph + i0) + voltage)
        / (diode_voltage * conductance_factor)
    )
    diode_term = (diode_voltage / rs) * wrightomega(log_argument)
    linear_term = (iph + i0 - voltage / rp) / conductance_factor
    return linear_term - diode_term


def _local_slope(x, y, center, point_count):
    """Estimate a local slope robustly with the median of pairwise slopes."""

    nearest = np.argsort(np.abs(x - center))[:point_count]
    local_x = x[nearest]
    local_y = y[nearest]
    slopes = []
    for first in range(len(local_x) - 1):
        delta_x = local_x[first + 1 :] - local_x[first]
        delta_y = local_y[first + 1 :] - local_y[first]
        usable = np.abs(delta_x) > np.finfo(float).eps
        slopes.extend((delta_y[usable] / delta_x[usable]).tolist())
    if not slopes:
        return math.nan
    return float(np.median(slopes))


def _clip_inside(value, lower, upper):
    """Clip an initial value strictly inside optimizer bounds."""

    margin = 1e-6
    return float(np.clip(value, lower * (1.0 + margin), upper * (1.0 - margin)))


def _current_orientation(voltage, current):
    """Return the multiplier that maps measured current to PV convention.

    The normal application importer reverses the instrument current, while
    other sources may already use positive short-circuit current.  A
    single-diode curve has more current at its low-voltage end than at its
    high-voltage end, so voltage-tail medians provide a noise-resistant way to
    recognize either convention.
    """

    tail_size = min(len(voltage), max(3, int(math.ceil(len(voltage) * 0.1))))
    voltage_order = np.argsort(voltage)
    low_voltage_current = float(np.median(current[voltage_order[:tail_size]]))
    high_voltage_current = float(np.median(current[voltage_order[-tail_size:]]))
    return 1.0 if low_voltage_current >= high_voltage_current else -1.0


def _initial_values_and_bounds(voltage, current):
    """Build slope-based starting values and data-scaled physical bounds."""

    # Keep the slope windows genuinely local.  A broad percentage of a steep
    # diode curve biases both endpoint slopes heavily; 4% (with eight points as
    # a noise-resistant minimum) stays close to the respective axis.
    point_count = min(len(voltage), max(8, int(math.ceil(len(voltage) * 0.04))))
    current_vs_voltage = _local_slope(voltage, current, 0.0, point_count)
    voltage_vs_current = _local_slope(current, voltage, 0.0, point_count)

    voltage_span = float(np.ptp(voltage))
    current_span = float(np.ptp(current))
    current_scale = max(
        current_span,
        float(np.percentile(np.abs(current), 90)),
        1e-9,
    )
    voltage_scale = max(
        voltage_span,
        float(np.percentile(np.abs(voltage), 90)),
        1e-6,
    )
    resistance_scale = voltage_scale / current_scale

    # The intercepts are evaluated from local robust slopes.  They are more
    # stable than choosing the single samples closest to the axes.
    near_voltage_zero = np.argsort(np.abs(voltage))[:point_count]
    if np.isfinite(current_vs_voltage):
        isc_samples = current[near_voltage_zero] - (
            current_vs_voltage * voltage[near_voltage_zero]
        )
        isc = float(np.median(isc_samples))
    else:
        isc = float(current[np.argmin(np.abs(voltage))])

    near_current_zero = np.argsort(np.abs(current))[:point_count]
    if np.isfinite(voltage_vs_current):
        voc_samples = voltage[near_current_zero] - (
            voltage_vs_current * current[near_current_zero]
        )
        voc = float(np.median(voc_samples))
    else:
        voc = float(voltage[np.argmin(np.abs(current))])

    rp_from_slope = (
        -1.0 / current_vs_voltage
        if np.isfinite(current_vs_voltage) and current_vs_voltage < 0.0
        else resistance_scale * 10.0
    )
    rs_from_slope = (
        -voltage_vs_current
        if np.isfinite(voltage_vs_current) and voltage_vs_current < 0.0
        else resistance_scale * 0.05
    )

    iph_lower = max(current_scale * 1e-4, 1e-12)
    iph_upper = max(current_scale * 20.0, abs(isc) * 10.0, iph_lower * 100.0)
    i0_lower = max(current_scale * 1e-15, 1e-18)
    i0_upper = max(current_scale * 2.0, i0_lower * 1e6)
    diode_voltage_lower = max(voltage_scale * 1e-4, 1e-5)
    diode_voltage_upper = max(voltage_scale * 2.0, 0.05)
    rs_lower = max(resistance_scale * 1e-9, 1e-12)
    rs_upper = max(resistance_scale * 100.0, rs_from_slope * 100.0, 1e-3)
    rp_lower = max(resistance_scale * 1e-3, 1e-6)
    rp_upper = max(resistance_scale * 1e6, rp_from_slope * 100.0, 1e3)

    iph_initial = _clip_inside(max(isc, current_scale), iph_lower, iph_upper)
    rp_initial = _clip_inside(rp_from_slope, rp_lower, rp_upper)
    rs_initial = _clip_inside(rs_from_slope, rs_lower, rs_upper)
    diode_voltage_initial = _clip_inside(
        max(abs(voc) / 20.0, voltage_scale / 40.0),
        diode_voltage_lower,
        diode_voltage_upper,
    )

    exponent = np.clip(abs(voc) / diode_voltage_initial, 0.0, 700.0)
    diode_numerator = max(iph_initial - max(voc, 0.0) / rp_initial, i0_lower)
    i0_initial = diode_numerator / max(float(np.expm1(exponent)), 1.0)
    i0_initial = _clip_inside(i0_initial, i0_lower, i0_upper)

    initial = np.array(
        [iph_initial, i0_initial, diode_voltage_initial, rs_initial, rp_initial]
    )
    lower = np.array(
        [iph_lower, i0_lower, diode_voltage_lower, rs_lower, rp_lower]
    )
    upper = np.array(
        [iph_upper, i0_upper, diode_voltage_upper, rs_upper, rp_upper]
    )
    slope_estimates = {
        "rs_ohm": float(rs_initial),
        "rp_ohm": float(rp_initial),
    }
    return initial, lower, upper, current_scale, slope_estimates


def _failure(message):
    return {
        "success": False,
        "message": message,
        "rs_ohm": None,
        "rp_kohm": None,
        "voltage_mv": [],
        "current_ma": [],
    }


def fit_single_diode(dataframe):
    """Robustly fit one measured dataset and return JSON-serializable results."""

    required_columns = {"Voltage [mV]", "Current [mA]"}
    if not isinstance(dataframe, pd.DataFrame) or not required_columns.issubset(
        dataframe.columns
    ):
        return _failure("Spannungs- oder Stromspalte fehlt.")

    voltage = pd.to_numeric(dataframe["Voltage [mV]"], errors="coerce").to_numpy(
        dtype=float
    )
    current = pd.to_numeric(dataframe["Current [mA]"], errors="coerce").to_numpy(
        dtype=float
    )
    finite = np.isfinite(voltage) & np.isfinite(current)
    voltage = voltage[finite] / 1000.0
    current = current[finite] / 1000.0

    if len(voltage) < MINIMUM_FIT_POINTS:
        return _failure(
            f"Mindestens {MINIMUM_FIT_POINTS} gültige Messpunkte werden benötigt."
        )
    if np.ptp(voltage) <= 0.0 or np.ptp(current) <= 0.0:
        return _failure("Die Messdaten haben keinen ausreichenden Wertebereich.")

    order = np.argsort(voltage)
    voltage = voltage[order]
    current = current[order]
    current_orientation = _current_orientation(voltage, current)
    current = current_orientation * current

    try:
        initial, lower, upper, current_scale, slopes = _initial_values_and_bounds(
            voltage, current
        )

        def residuals(log_parameters):
            parameters = np.exp(log_parameters)
            predicted = single_diode_current(voltage, *parameters)
            if not np.all(np.isfinite(predicted)):
                return np.full_like(current, 1e6)
            return (predicted - current) / current_scale

        # A pilot fit gets close to the nonlinear curve.  Its residual MAD then
        # gives a noise estimate that is not inflated by the curve's shape.
        pilot = least_squares(
            residuals,
            np.log(initial),
            bounds=(np.log(lower), np.log(upper)),
            loss="soft_l1",
            f_scale=0.05,
            x_scale="jac",
            max_nfev=1200,
        )
        pilot_residuals = residuals(pilot.x)
        median_residual = np.median(pilot_residuals)
        robust_sigma = 1.4826 * np.median(
            np.abs(pilot_residuals - median_residual)
        )
        robust_scale = float(np.clip(1.5 * robust_sigma, 0.0005, 0.05))

        result = least_squares(
            residuals,
            pilot.x,
            bounds=(np.log(lower), np.log(upper)),
            loss="soft_l1",
            f_scale=robust_scale,
            x_scale="jac",
            max_nfev=1500,
        )
        parameters = np.exp(result.x)
        fitted_at_measurements = single_diode_current(voltage, *parameters)
        if not result.success or not np.all(np.isfinite(fitted_at_measurements)):
            return _failure("Die nichtlineare Anpassung ist nicht konvergiert.")

        rmse = float(np.sqrt(np.mean((fitted_at_measurements - current) ** 2)))
        if rmse / current_scale > 0.1:
            return _failure(
                "Die Messkurve kann durch das Ein-Dioden-Modell nicht "
                "ausreichend beschrieben werden."
            )

        curve_voltage = np.linspace(float(voltage.min()), float(voltage.max()), 300)
        curve_current = single_diode_current(curve_voltage, *parameters)
        if not np.all(np.isfinite(curve_current)):
            return _failure("Die angepasste Kennlinie konnte nicht berechnet werden.")

        iph, i0, diode_voltage, rs, rp = parameters
        return {
            "success": True,
            "message": "Anpassung erfolgreich.",
            "rs_ohm": float(rs),
            "rp_kohm": float(rp / 1000.0),
            "iph_a": float(iph),
            "i0_a": float(i0),
            "diode_voltage_v": float(diode_voltage),
            "rmse_ma": float(rmse * 1000.0),
            "initial_rs_ohm": slopes["rs_ohm"],
            "initial_rp_kohm": slopes["rp_ohm"] / 1000.0,
            "current_orientation": int(current_orientation),
            "voltage_mv": (curve_voltage * 1000.0).tolist(),
            "current_ma": (current_orientation * curve_current * 1000.0).tolist(),
        }
    except (ArithmeticError, FloatingPointError, ValueError):
        return _failure("Die Messdaten konnten nicht stabil angepasst werden.")
