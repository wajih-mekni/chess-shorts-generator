"""Stage 3 recipes. Milliseconds, degrees, and fractions of a logical square.

The 200 ms inversion / 130 ms hang follows the 31.50–31.83 s reference
window. Finish/settle and deformation amplitudes are tunable interpretations;
the source's last quarter-turn is partly hidden by bloom. No reactions here.
"""
CHOREOGRAPHY_PROFILE = "LEGACY"  # Opt into REFERENCE for type-based ordinary travel.
LIFT_DURATION = 420
KNIGHT_DURATION = 500
SWEEP_DURATION = 480
TRAVEL_PEAK_AT = 0.40
TRAVEL_ARRIVAL_AT = 0.82
TRAVEL_PEAK_PROGRESS = 0.40
TRAVEL_OVERSHOOT = 0.08
TRAVEL_OVERSHOOT_DISTANCE_LIMIT = 0.08
TRAVEL_EASING = "cubic-bezier(0.22, 0.61, 0.36, 1)"
LAUNCH_EASING = "cubic-bezier(0.42, 0, 0.58, 1)"
SETTLE_EASING = "cubic-bezier(0.22, 0.61, 0.36, 1)"
LIFT_HEIGHT = 0.18
LIFT_SCALE = 1.10
LIFT_ROTATION = 6
KNIGHT_HEIGHT = 0.55
KNIGHT_SCALE = 1.18
KNIGHT_ROTATION = 12
BISHOP_SWEEP_WIDTH = 0.22
BISHOP_SWEEP_HEIGHT = 0.10
BISHOP_SWEEP_SCALE = 1.10
BISHOP_SWEEP_ROTATION = 22
SPIN_LAUNCH_DURATION = 200
SPIN_HANG_DURATION = 130
SPIN_FINISH_DURATION = 150
SPIN_SETTLE_DURATION = 90
SPIN_HANG_PROGRESS = 0.42
SPIN_LAUNCH_EASING = "cubic-bezier(0.16, 0.8, 0.3, 1)"
SPIN_FINISH_EASING = "cubic-bezier(0.55, 0, 1, 0.45)"
SPIN_LIFT = 0.22
SPIN_SCALE = 1.14
SPIN_OVERSHOOT_ANGLE = 8
ROOK_LIFT = 0.28
ROOK_SCALE = 1.20
ROOK_OVERSHOOT_ANGLE = 12
QUEEN_LIFT = 0.22
QUEEN_SCALE = 1.16
QUEEN_SWEEP = 0.10
BISHOP_SPIN_LIFT = 0.18
BISHOP_SPIN_SCALE = 1.12
BISHOP_SPIN_SWEEP = 0.15
ARRIVAL_SCALE_REMAINDER = 0.20
ARRIVAL_ROTATION_REBOUND = 0.15


def choreography_config(profile=CHOREOGRAPHY_PROFILE):
    if profile not in {"LEGACY", "REFERENCE"}:
        raise ValueError(f"Unknown choreography profile: {profile}")
    common = dict(overshoot=TRAVEL_OVERSHOOT, distanceLimit=TRAVEL_OVERSHOOT_DISTANCE_LIMIT,
                  easing=TRAVEL_EASING, launchEasing=LAUNCH_EASING,
                  settleEasing=SETTLE_EASING, peakAt=TRAVEL_PEAK_AT,
                  arrivalAt=TRAVEL_ARRIVAL_AT, peakProgress=TRAVEL_PEAK_PROGRESS,
                  arrivalScale=ARRIVAL_SCALE_REMAINDER,
                  rotationRebound=ARRIVAL_ROTATION_REBOUND, sweep=0, direction=1)
    lift = dict(common, kind="lift", duration=LIFT_DURATION,
                lift=LIFT_HEIGHT, scale=LIFT_SCALE, rotation=LIFT_ROTATION)
    spin = dict(common, kind="spin", launch=SPIN_LAUNCH_DURATION, hang=SPIN_HANG_DURATION,
                finish=SPIN_FINISH_DURATION, settle=SPIN_SETTLE_DURATION,
                duration=sum((SPIN_LAUNCH_DURATION, SPIN_HANG_DURATION,
                              SPIN_FINISH_DURATION, SPIN_SETTLE_DURATION)),
                hangProgress=SPIN_HANG_PROGRESS, launchEasing=SPIN_LAUNCH_EASING,
                finishEasing=SPIN_FINISH_EASING, lift=SPIN_LIFT, scale=SPIN_SCALE,
                rotation=SPIN_OVERSHOOT_ANGLE)
    presets = {
        "LIFT_MOVE": lift,
        "KNIGHT_JUMP": dict(lift, duration=KNIGHT_DURATION, lift=KNIGHT_HEIGHT,
                            scale=KNIGHT_SCALE, rotation=KNIGHT_ROTATION),
        "BISHOP_SWEEP": dict(lift, duration=SWEEP_DURATION, lift=BISHOP_SWEEP_HEIGHT,
                             sweep=BISHOP_SWEEP_WIDTH, scale=BISHOP_SWEEP_SCALE,
                             rotation=BISHOP_SWEEP_ROTATION),
        "SPIN_WITH_HANG": spin,
        "ROOK_FLIP": dict(spin, lift=ROOK_LIFT, scale=ROOK_SCALE, rotation=ROOK_OVERSHOOT_ANGLE),
        "QUEEN_SPIN": dict(spin, lift=QUEEN_LIFT, scale=QUEEN_SCALE,
                           sweep=QUEEN_SWEEP, direction=-1),
        "BISHOP_SPIN": dict(spin, lift=BISHOP_SPIN_LIFT, scale=BISHOP_SPIN_SCALE,
                            sweep=BISHOP_SPIN_SWEEP),
    }
    for name, preset in presets.items():
        if preset["duration"] <= 0 or not 0 < preset["peakAt"] < preset["arrivalAt"] < 1:
            raise ValueError(f"Invalid choreography timing: {name}")
        if preset["kind"] == "spin" and any(preset[key] <= 0 for key in ("launch", "hang", "finish", "settle")):
            raise ValueError(f"Spin phases must be positive: {name}")
    return dict(profile=profile, presets=presets,
                ordinary={"pawn": "LIFT_MOVE", "king": "LIFT_MOVE", "rook": "LIFT_MOVE",
                          "queen": "LIFT_MOVE", "bishop": "BISHOP_SWEEP", "knight": "KNIGHT_JUMP"})
