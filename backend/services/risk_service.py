from __future__ import annotations

from typing import Any


def determine_severity(rainfall: float, water_level: float) -> str:
    if rainfall >= 100 or water_level >= 90:
        return "CRITICAL"
    if rainfall >= 80 or water_level >= 70:
        return "HIGH"
    if rainfall >= 40 or water_level >= 40:
        return "MEDIUM"
    return "LOW"


def calculate_probability(rainfall: float, water_level: float, severity: str) -> float:
    combined = rainfall + water_level

    if severity == "LOW":
        probability = min(0.25 + (combined / 600), 0.39)
    elif severity == "MEDIUM":
        probability = min(0.45 + (combined / 300), 0.69)
    elif severity == "HIGH":
        probability = min(0.70 + (combined / 240), 0.89)
    else:
        probability = min(0.86 + (combined / 220), 0.99)

    return round(probability, 2)


def calculate_risk(environment: dict[str, Any]) -> dict[str, Any]:
    rainfall = float(environment.get("rainfall", 0))
    observed_water_level = float(environment.get("water_level", 0))
    forecast = str(environment.get("forecast", "normal")).lower()
    forecast_adjustment = {"watch": 5.0, "moderate": 5.0, "heavy": 10.0, "extreme": 20.0}.get(forecast, 0.0)
    drainage_capacity = environment.get("drainage_capacity")
    drainage_blockage = environment.get("drainage_blockage")
    drainage_adjustment = 0.0
    if drainage_capacity is not None or drainage_blockage is not None:
        capacity = 100.0 if drainage_capacity is None else float(drainage_capacity)
        blockage = 0.0 if drainage_blockage is None else float(drainage_blockage)
        drainage_adjustment = max(0.0, (100.0 - capacity) * 0.15 + blockage * 0.15)
    water_level = min(100.0, observed_water_level + drainage_adjustment + forecast_adjustment)
    location = environment.get("location", "Unknown Location")
    severity = determine_severity(rainfall, water_level)

    return {
        "risk_type": "waterlogging",
        "severity": severity,
        "probability": calculate_probability(rainfall, water_level, severity),
        "location": location,
        "observed_water_level": observed_water_level,
        "effective_water_level": round(water_level, 1),
        "drainage_adjustment": round(drainage_adjustment, 1),
        "forecast_adjustment": forecast_adjustment,
    }
