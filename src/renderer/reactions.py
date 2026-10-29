"""Stage 4 reaction primitives: milliseconds, degrees and logical square fractions.

Reference victims retire in about 200 ms (35.20–35.40 / 39.20–39.40 s).
King anticipation/recovery is visible at 13.35–13.70 and 26.15–26.40 s.
Durations below adapt those ranges to our move clock; amplitudes are chosen.
"""
REACTION_PROFILE = "LEGACY"
CAPTURE_VISUAL_LAYER = 7  # Above moving pieces (6), below labels (10).
CAPTURE_LEAD_DURATION = 120  # Before the recipe's arrival cue, on its animation clock.
CAPTURE_DURATION = 240
CAPTURE_MIDPOINT = 0.35
CAPTURE_MID_SCALE = 0.75
CAPTURE_END_SCALE = 0.08
CAPTURE_MID_DISTANCE = 0.25
CAPTURE_MID_ROTATION = 0.40
CAPTURE_TUMBLE_DISTANCE = 0.35
CAPTURE_TUMBLE_ROTATION = 110
CAPTURE_KNOCKBACK_DISTANCE = 0.65
CAPTURE_KNOCKBACK_ROTATION = 28
CAPTURE_EASING = "cubic-bezier(0.42, 0, 1, 1)"
KING_LEAD_DURATION = 150
KING_ANTICIPATION_DURATION = 100
KING_RECOVERY_DURATION = 180
KING_TILT = 14
KING_SCALE = 1.12
KING_DISPLACEMENT = 0.08
KING_EASING = "cubic-bezier(0.22, 0.61, 0.36, 1)"


def reaction_config(profile=REACTION_PROFILE):
    if profile not in {"LEGACY", "REFERENCE"}:
        raise ValueError(f"Unknown reaction profile: {profile}")
    common = dict(kind="capture", lead=CAPTURE_LEAD_DURATION, duration=CAPTURE_DURATION,
                  midpoint=CAPTURE_MIDPOINT, midScale=CAPTURE_MID_SCALE,
                  endScale=CAPTURE_END_SCALE, midDistance=CAPTURE_MID_DISTANCE,
                  midRotation=CAPTURE_MID_ROTATION, easing=CAPTURE_EASING)
    return dict(profile=profile, captureVisualLayer=CAPTURE_VISUAL_LAYER,
                # Basic bindings, replaceable by a future director. No severity,
                # piece choreography, camera, color or tactical recipe decisions.
                defaults=dict(capture="CAPTURE_TUMBLE", king="KING_RECOIL"),
                presets={
                    "CAPTURE_SHRINK": dict(common, distance=0, rotation=0),
                    "CAPTURE_TUMBLE": dict(common, distance=CAPTURE_TUMBLE_DISTANCE,
                                           rotation=CAPTURE_TUMBLE_ROTATION),
                    "CAPTURE_KNOCKBACK": dict(common, distance=CAPTURE_KNOCKBACK_DISTANCE,
                                              rotation=CAPTURE_KNOCKBACK_ROTATION),
                    "KING_RECOIL": dict(kind="king", lead=KING_LEAD_DURATION,
                                        anticipation=KING_ANTICIPATION_DURATION,
                                        recovery=KING_RECOVERY_DURATION, rotation=KING_TILT,
                                        scale=KING_SCALE, distance=KING_DISPLACEMENT,
                                        easing=KING_EASING),
                })
