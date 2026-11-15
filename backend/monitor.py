import json
from pathlib import Path
from statistics import mean
from datetime import datetime, timezone

FIELDS = {
    "heart": ("Resting heart rate", "bpm", 20, 250, 10),
    "systolic": ("Systolic pressure", "mmHg", 50, 260, 15),
    "diastolic": ("Diastolic pressure", "mmHg", 25, 160, 10),
    "temperature": ("Body temperature", "°C", 30, 44, 0.8),
    "oxygen": ("Oxygen saturation", "%", 50, 100, 3),
    "sleep": ("Sleep duration", "h", 0, 24, 1.5),
    "mood": ("Mood", "/10", 0, 10, 3),
    "stress": ("Stress", "/10", 0, 10, 3),
    "fatigue": ("Fatigue", "/10", 0, 10, 3),
    "exercise": ("Exercise", "min", 0, 1440, 30),
}
THRESHOLDS = {key: value[4] for key, value in FIELDS.items()}
config = Path(__file__).with_name("thresholds.json")
if config.exists():
    THRESHOLDS.update(json.loads(config.read_text(encoding="utf-8-sig")))


def summarize(baseline, history, now=None):
    now = now or datetime.now(timezone.utc)
    latest = history[-1] if history else {}
    alerts, metrics = [], {}
    for key, (label, unit, minimum, maximum, _) in FIELDS.items():
        value = latest.get(key)
        delta = round(value - baseline[key], 2) if value is not None and baseline[key] is not None else None
        values = [row[key] for row in history[-7:] if row.get(key) is not None]
        trend = round(mean(values[-3:]) - mean(values[:-3]), 2) if len(values) >= 4 else None
        metrics[key] = dict(label=label, unit=unit, minimum=minimum, maximum=maximum, value=value, baseline=baseline[key],
                            delta=delta, trend=trend, samples=len(values))
        if value is None:
            alerts.append(dict(code=key+"_missing", level="Data gap", message=f"{label} was not recorded."))
        elif delta is not None and abs(delta) >= THRESHOLDS[key]:
            alerts.append(dict(code=key+"_baseline", level="Monitor",
                               message=f"{label} is {delta:+g} {unit} from personal baseline. Demo threshold: {THRESHOLDS[key]:g} {unit}."))
    if latest and (now - datetime.fromisoformat(latest["timestamp"])).total_seconds() > 36 * 3600:
        alerts.append(dict(code="stale", level="Data gap", message="The latest check-in is more than 36 hours old."))
    if (metrics["heart"]["delta"] or 0) >= THRESHOLDS["heart"] and latest.get("symptoms", "").strip():
        alerts.insert(0, dict(code="heart_symptoms", level="Crew review",
                             message="Resting heart rate is above its demo threshold and symptoms were reported. Flag for crew medical review."))
    if (metrics["sleep"]["delta"] or 0) <= -THRESHOLDS["sleep"] and (metrics["fatigue"]["delta"] or 0) >= THRESHOLDS["fatigue"]:
        alerts.insert(0, dict(code="sleep_fatigue", level="Crew review",
                             message="Sleep is below baseline and fatigue is elevated. Flag the combination for crew review."))
    return dict(metrics=metrics, alerts=alerts)

