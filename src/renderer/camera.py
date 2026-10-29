"""Camera profiles: milliseconds, degrees, local square widths and logical pixels.

REFERENCE transition durations come from grid-spacing measurements in the supplied
video (see docs/reference-motion-analysis.md). Amplitudes below are tuned
design choices for our square viewport, not recovered source keyframes.
"""
from math import cos, prod, radians, sin


CAMERA_ENABLED = True
CAMERA_WIDE_ZOOM = 1.0
CAMERA_MEDIUM_ZOOM = 2.05
CAMERA_CLOSE_ZOOM = 3.15
CAMERA_MEDIUM_REGION = 4.0  # Local square widths, independent of move distance.
CAMERA_CLOSE_REGION = 2.5
CAMERA_MEDIUM_ROTATION = 0.8
CAMERA_CLOSE_ROTATION = 2.0
CAMERA_MEDIUM_DURATION = 300
CAMERA_CLOSE_DURATION = 240
CAMERA_WIDE_DURATION = 380
BRILLIANT_PRE_HOLD = 120
BRILLIANT_POST_HOLD = 180
CAMERA_EASING = "cubic-bezier(0.22, 0.61, 0.36, 1)"
CAMERA_MAX_TRANSLATION = 1300
CAMERA_MAX_ZOOM = 3.4
CAMERA_MAX_ROTATION = 3.0
CAMERA_OVERSCAN = 1550

# Preserve the original directed shots in LEGACY. A profile changes the camera
# only; the current aggressive piece motion presets remain untouched.
REFERENCE_CAMERA_MEDIUM_DURATION = 300  # Chosen tactical reframe, tunable.
REFERENCE_CAMERA_CLOSE_DURATION = 400  # Measured close push: about 400 ms.
REFERENCE_CAMERA_WIDE_DURATION = 450  # Measured pull range: about 400–500 ms.
REFERENCE_CAMERA_MEDIUM_ROTATION = 0.35  # Chosen; stable reference grids are upright.
REFERENCE_CAMERA_CLOSE_ROTATION = 0.6

# Independent transient tracks; reframe stays restrained, impacts/heroes punch. Translation
# is screen-relative in board logical pixels, outside the persistent camera zoom.
CAMERA_REFRAME_SETTLE_DURATION = 120
CAMERA_REFRAME_TRANSLATION = 7.0
CAMERA_REFRAME_ZOOM = 0.010  # Added to 1.0, never to the persistent shot target.
CAMERA_REFRAME_ROTATION = 0.16
CAMERA_REFRAME_PEAK = 0.82  # Fraction of the persistent transition duration.
CAMERA_REFRAME_REBOUND = 0.20

CAMERA_IMPACT_DURATION = 190
CAMERA_IMPACT_TRANSLATION = 18.0
CAMERA_IMPACT_ZOOM = 0.045
CAMERA_IMPACT_ROTATION = 1.15
CAMERA_IMPACT_REBOUND = 0.62
CAMERA_IMPACT_SETTLE = 0.22
CAMERA_IMPACT_PEAK_AT = 0.18
CAMERA_IMPACT_REBOUND_AT = 0.44
CAMERA_IMPACT_SETTLE_AT = 0.72

CAMERA_HERO_TRANSLATION = 12.0
CAMERA_HERO_ZOOM = 0.050
CAMERA_HERO_ROTATION = 0.80
CAMERA_HERO_DRIFT_PERIOD = 640
CAMERA_HERO_PULSE_PERIOD = 500  # Approximate observed pulse rhythm; not music sync.
CAMERA_HERO_SAMPLE_INTERVAL = 32


def _transient_config(enabled, viewport_size):
    tracks = dict(
        reframe=dict(translation=CAMERA_REFRAME_TRANSLATION, zoom=CAMERA_REFRAME_ZOOM,
                     rotation=CAMERA_REFRAME_ROTATION,
                     settleDuration=CAMERA_REFRAME_SETTLE_DURATION,
                     peak=CAMERA_REFRAME_PEAK, rebound=CAMERA_REFRAME_REBOUND),
        impact=dict(translation=CAMERA_IMPACT_TRANSLATION, zoom=CAMERA_IMPACT_ZOOM,
                    rotation=CAMERA_IMPACT_ROTATION, duration=CAMERA_IMPACT_DURATION,
                    rebound=CAMERA_IMPACT_REBOUND, settle=CAMERA_IMPACT_SETTLE,
                    peakAt=CAMERA_IMPACT_PEAK_AT, reboundAt=CAMERA_IMPACT_REBOUND_AT,
                    settleAt=CAMERA_IMPACT_SETTLE_AT),
        hero=dict(translation=CAMERA_HERO_TRANSLATION, zoom=CAMERA_HERO_ZOOM,
                  rotation=CAMERA_HERO_ROTATION, driftPeriod=CAMERA_HERO_DRIFT_PERIOD,
                  pulsePeriod=CAMERA_HERO_PULSE_PERIOD,
                  sampleInterval=CAMERA_HERO_SAMPLE_INTERVAL),
    )
    # Any simultaneous track combination stays inside this conservative envelope.
    # Rotating a square increases its axis-aligned extent by cos(a) + sin(a).
    scale = prod(1 + abs(track["zoom"]) for track in tracks.values())
    angle = radians(sum(abs(track["rotation"]) for track in tracks.values()))
    rotated_extent = cos(angle) + sin(angle)
    # Inner translations are also rotated/scaled by outer owners.
    translation = sum(abs(track["translation"]) for track in tracks.values()) * scale * rotated_extent
    safe_half = (viewport_size / 2 - translation) / (scale * rotated_extent)
    return dict(enabled=enabled, easing=CAMERA_EASING,
                framingMargin=viewport_size / 2 - safe_half if enabled else 0,
                **tracks)


def camera_config(enabled=None, profile="REFERENCE"):
    from .layout import BOARD_FRAME_SIZE, BOARD_SCALE
    if profile not in {"LEGACY", "REFERENCE"}:
        raise ValueError(f"Unknown camera profile: {profile}")
    enabled = CAMERA_ENABLED if enabled is None else enabled
    reference = profile == "REFERENCE"
    medium_duration = REFERENCE_CAMERA_MEDIUM_DURATION if reference else CAMERA_MEDIUM_DURATION
    close_duration = REFERENCE_CAMERA_CLOSE_DURATION if reference else CAMERA_CLOSE_DURATION
    wide_duration = REFERENCE_CAMERA_WIDE_DURATION if reference else CAMERA_WIDE_DURATION
    medium_rotation = REFERENCE_CAMERA_MEDIUM_ROTATION if reference else CAMERA_MEDIUM_ROTATION
    close_rotation = REFERENCE_CAMERA_CLOSE_ROTATION if reference else CAMERA_CLOSE_ROTATION
    viewport_size = BOARD_FRAME_SIZE / BOARD_SCALE
    return dict(enabled=enabled, profile=profile,
                duration=medium_duration, wideDuration=wide_duration,
                brilliantPreHold=BRILLIANT_PRE_HOLD, brilliantPostHold=BRILLIANT_POST_HOLD,
                easing=CAMERA_EASING,
                wideZoom=CAMERA_WIDE_ZOOM,
                shots={"K": dict(zoom=CAMERA_MEDIUM_ZOOM, region=CAMERA_MEDIUM_REGION,
                                 duration=medium_duration, rotation=medium_rotation),
                       "L": dict(zoom=CAMERA_CLOSE_ZOOM, region=CAMERA_CLOSE_REGION,
                                 duration=close_duration, rotation=close_rotation)},
                transient=_transient_config(bool(enabled and reference), viewport_size),
                viewportSize=viewport_size,
                maxTranslation=CAMERA_MAX_TRANSLATION, maxZoom=CAMERA_MAX_ZOOM,
                maxRotation=CAMERA_MAX_ROTATION)
