"""Stage 6 recipe selection and pacing; no animation implementation here."""
from copy import deepcopy
from math import isfinite

DIRECTING_PROFILE = 'AUTO'
# Optional overlay on HERO, never a replacement for its tuned base recipe.
AGGRESSIVE_HERO = dict(
    rotation=4.0,
    duration=200,
    oscillations=1,
    damping=8.0,
    zoom=.16,
    shakeTranslation=4.0,
    shakeCycles=2,
    impactStrength=2.5,
    lightingMultiplier=1.6,
    lightSizeMultiplier=1.35,
    particlesMultiplier=2.0
)

# 3 s total: 1.4 s inward, 0.2 s peak, 1.4 s outward. Rocking overlaps
# the return (2360 - 60 + 700 = 3000 ms).
# Absolute scale factors; these only affect ^VA's short spin phase.
VERY_AGGRESSIVE_HERO = dict(spinTurns=3, spinDuration=2000, spinDirection=1,
                            spinZoomIn=1.5, spinZoomHold=1.5, spinZoomRecoil=1.1,
                            spinZoomDuration=2500, spinPunchAt=800/2500, spinRecoilAt=1000/2500, spinOverlap=60,
                            spinSampleInterval=8, spinReturnWide=True, spinReturnWideAt=1000/2500)


def very_aggressive_recipe(aggressive, overrides=None):
    spin = dict(VERY_AGGRESSIVE_HERO)
    if overrides is not None:
        unknown = overrides.keys() - spin.keys()
        if unknown:
            raise ValueError(f'Unknown very aggressive parameters: {sorted(unknown)}')
        spin.update(overrides)
    bounds = dict(spinTurns=(1, 4), spinDuration=(200, 5000), spinZoomDuration=(200, 5000), spinDirection=(-1, 1),
                  spinZoomIn=(1, 2.5), spinZoomHold=(1, 2.5), spinZoomRecoil=(1, 1.5),
                  spinPunchAt=(.05, .49), spinRecoilAt=(.05, .85),
                  spinOverlap=(20, 150), spinSampleInterval=(2, 16), spinReturnWideAt=(0, .95))
    for key, (low, high) in bounds.items():
        value = spin[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not low <= value <= high:
            raise ValueError(f'Very aggressive {key} must be between {low} and {high}')
    if not isinstance(spin['spinReturnWide'], bool):
        raise ValueError('spinReturnWide must be True or False')
    if spin['spinTurns'] != int(spin['spinTurns']) or spin['spinDirection'] not in (-1, 1):
        raise ValueError('Spin needs whole turns and direction +1 or -1')
    if spin['spinOverlap'] >= min(spin['spinDuration'] / 2, aggressive['duration']):
        raise ValueError('Spin overlap must be shorter than the rocking phase and half the spin')
    if not spin['spinZoomIn'] >= spin['spinZoomHold'] >= spin['spinZoomRecoil']:
        raise ValueError('Spin zoom must decrease from punch to hold to recoil')
    return dict(aggressive, **spin)


def aggressive_recipe(overrides=None):
    recipe = dict(AGGRESSIVE_HERO)
    if overrides is not None:
        unknown = overrides.keys() - recipe.keys()
        if unknown:
            raise ValueError(f'Unknown aggressive parameters: {sorted(unknown)}')
        recipe.update(overrides)
    bounds = dict(rotation=(0, 20), duration=(100, 5000), oscillations=(1, 12),
                  damping=(.1, 8), zoom=(0, .4), shakeTranslation=(0, 60),
                  shakeCycles=(1, 30), impactStrength=(1, 4),
                  lightingMultiplier=(1, 3), lightSizeMultiplier=(1, 2),
                  particlesMultiplier=(1, 3))
    for key, (low, high) in bounds.items():
        value = recipe[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not low <= value <= high:
            raise ValueError(f'Aggressive {key} must be between {low} and {high}')
    return recipe

TIERS = {
    'NORMAL': dict(pause=.45, effect='LOCAL_ACCENT', impact=0),
    'TACTICAL': dict(pause=.53, effect='TACTICAL_ACCENT', impact=.25),
    'HERO': dict(pause=1.5, effect='HERO', impact=3),
}
NORMAL_CHOREOGRAPHY = dict(pawn='LIFT_MOVE', knight='KNIGHT_JUMP', bishop='BISHOP_SWEEP',
                          rook='LIFT_MOVE', queen='LIFT_MOVE', king='LIFT_MOVE')
STRONG_CHOREOGRAPHY = dict(NORMAL_CHOREOGRAPHY, bishop='BISHOP_SPIN', rook='ROOK_FLIP', queen='QUEEN_SPIN')
LONG_MOVE_SQUARES = 4
WIDE_HERO_MOVE_SQUARES = 5
KEEP_MEDIUM_RADIUS = 1.5

# One extensible alias registry: the parser has no piece-specific syntax branches.
CHOREOGRAPHY_ALIASES = {
    'lift': 'LIFT_MOVE', 'jump': 'KNIGHT_JUMP', 'sweep': 'BISHOP_SWEEP',
    'spin': 'SPIN_WITH_HANG', 'flip': 'ROOK_FLIP', 'rook-spin': 'ROOK_FLIP',
    'queen-spin': 'QUEEN_SPIN', 'bishop-spin': 'BISHOP_SPIN', 'legacy': 'LEGACY',
}


def directing_config(profile='LEGACY', *, brilliant_mode='standard', aggressive=None, very_aggressive=None):
    if profile not in {'AUTO','LEGACY'}:
        raise ValueError(f'Unknown directing profile: {profile}')
    if brilliant_mode not in {'standard', 'aggressive'}:
        raise ValueError(f'Unknown brilliant mode: {brilliant_mode}')
    aggressive = aggressive_recipe(aggressive)
    return dict(brilliantMode=brilliant_mode, aggressive=aggressive,
                veryAggressive=very_aggressive_recipe(aggressive, very_aggressive), profile=profile, enabled=profile=='AUTO', tiers=deepcopy(TIERS),
                ordinary=NORMAL_CHOREOGRAPHY, strong=STRONG_CHOREOGRAPHY,
                longMove=LONG_MOVE_SQUARES, wideHeroMove=WIDE_HERO_MOVE_SQUARES,
                keepMediumRadius=KEEP_MEDIUM_RADIUS)
