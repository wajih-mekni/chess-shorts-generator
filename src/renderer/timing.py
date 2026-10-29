"""Move scheduling in milliseconds; piece durations remain owned by motion.py.

REFERENCE overlaps camera travel with the unchanged piece preset. LEGACY keeps
the previous camera-then-piece ordering. Authored pauses are never shortened or
extended to match a recipe: the demo explicitly requests its measured hero hold.
"""

TIMING_PROFILE = "REFERENCE"
CAMERA_LEAD_NORMAL = 0
CAMERA_LEAD_CLOSE = 60
CAMERA_LEAD_HERO = 120
# Approximate 27.35–30.85 s / 31.50–35.05 s entrance + hold measurements.
# A recommended authored pause, not an automatic override of SAN (Xs) timing.
REFERENCE_HERO_HOLD = 2800


def timing_config(profile=TIMING_PROFILE):
    if profile not in {"REFERENCE", "LEGACY"}:
        raise ValueError(f"Unknown timing profile: {profile}")
    return dict(profile=profile, serialCamera=profile == "LEGACY",
                cameraLeadNormal=CAMERA_LEAD_NORMAL,
                cameraLeadClose=CAMERA_LEAD_CLOSE,
                cameraLeadHero=CAMERA_LEAD_HERO)
