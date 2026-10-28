"""Persistent directed shots: milliseconds, degrees, local region sizes, logical pixels."""
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


def camera_config(enabled=None):
    from .layout import BOARD_FRAME_SIZE, BOARD_SCALE
    return dict(enabled=CAMERA_ENABLED if enabled is None else enabled,
                duration=CAMERA_MEDIUM_DURATION, wideDuration=CAMERA_WIDE_DURATION,
                brilliantPreHold=BRILLIANT_PRE_HOLD, brilliantPostHold=BRILLIANT_POST_HOLD,
                easing=CAMERA_EASING,
                wideZoom=CAMERA_WIDE_ZOOM,
                shots={"K": dict(zoom=CAMERA_MEDIUM_ZOOM, region=CAMERA_MEDIUM_REGION, duration=CAMERA_MEDIUM_DURATION,
                                 rotation=CAMERA_MEDIUM_ROTATION),
                       "L": dict(zoom=CAMERA_CLOSE_ZOOM, region=CAMERA_CLOSE_REGION, duration=CAMERA_CLOSE_DURATION,
                                 rotation=CAMERA_CLOSE_ROTATION)},
                viewportSize=BOARD_FRAME_SIZE / BOARD_SCALE,
                maxTranslation=CAMERA_MAX_TRANSLATION, maxZoom=CAMERA_MAX_ZOOM,
                maxRotation=CAMERA_MAX_ROTATION)
