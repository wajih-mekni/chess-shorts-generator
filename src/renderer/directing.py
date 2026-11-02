"""Stage 6 recipe selection and pacing; no animation implementation here."""
DIRECTING_PROFILE = 'AUTO'
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


def directing_config(profile='LEGACY'):
    if profile not in {'AUTO','LEGACY'}:
        raise ValueError(f'Unknown directing profile: {profile}')
    return dict(profile=profile, enabled=profile=='AUTO', tiers=TIERS,
                ordinary=NORMAL_CHOREOGRAPHY, strong=STRONG_CHOREOGRAPHY,
                longMove=LONG_MOVE_SQUARES, wideHeroMove=WIDE_HERO_MOVE_SQUARES,
                keepMediumRadius=KEEP_MEDIUM_RADIUS)
