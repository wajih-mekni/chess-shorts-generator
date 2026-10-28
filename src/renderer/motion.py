"""Piece motion tuning. Durations are milliseconds, rotation degrees,
overshoot a fraction of one square, blur logical board pixels.
"""
MOVE_DURATION = 700
MOVE_EASING = "cubic-bezier(0.22, 0.61, 0.36, 1)"

MOVE_SCALE_PEAK = 1.20
MOVE_ROTATION = 12.0
MOVE_OVERSHOOT = 0.12
MOVE_BLUR = 0.0


def movement_presets():
    normal = dict(duration=MOVE_DURATION, easing=MOVE_EASING,
                  scalePeak=MOVE_SCALE_PEAK, rotation=MOVE_ROTATION,
                  overshoot=MOVE_OVERSHOOT, blur=MOVE_BLUR)
    return {
        "NORMAL_MOVE": normal,
        "FAST_MOVE": {**normal, "duration": MOVE_DURATION * 0.65,
                      "scalePeak": 1 + (MOVE_SCALE_PEAK - 1) * 0.6,
                      "rotation": MOVE_ROTATION * 0.5,
                      "overshoot": MOVE_OVERSHOOT * 0.6},
        "DRAMATIC_MOVE": {**normal, "duration": MOVE_DURATION * 1.5,
                          "scalePeak": 1 + (MOVE_SCALE_PEAK - 1) * 1.3,
                          "rotation": MOVE_ROTATION * 1.5,
                          "overshoot": MOVE_OVERSHOOT * 1.5},
    }
