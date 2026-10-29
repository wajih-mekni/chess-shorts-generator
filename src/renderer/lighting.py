"""Stage 5 theme/effect vocabulary. Times in ms, geometry in logical squares.

Reference: recurring hero pulses roughly 500 ms; holds about 2.5–3 s.
Amplitudes are tunable interpretations, not recovered source keyframes.
"""
LIGHTING_PROFILE = 'LEGACY'
EFFECT_SEED = 271828
PULSE_PERIOD = 500
PULSE_SAMPLE_INTERVAL = 50
EFFECT_FADE_DURATION = 180
MAX_PARTICLES = 64
REFERENCE_THEME = dict(light='#e2e5e6', dark='#626a70', backing='#394148', canvas='#20272d')
ACCENT_PALETTES = {
    'CYAN': dict(color='#00eaff', core='#e4ffff'),
    'GREEN': dict(color='#45ff42', core='#f0ffe7'),
    'ORANGE': dict(color='#ff7818', core='#fff0cf'),
    'RED': dict(color='#ff2445', core='#ffe3e7'),
}

# Independent primitives: no writes to camera, actor or annotation transforms.
LIGHT_PRIMITIVES = {
    'SQUARE_GLOW': dict(space='under', shape='square', size=1, opacity=.32, duration=420, pulse=.18),
    'LOCAL_GLOW': dict(space='under', shape='glow', size=2.45, opacity=.78, duration=480, pulse=.22),
    'HERO_BLOOM': dict(space='under', shape='glow', size=4.2, opacity=1.0, duration=0, pulse=.50),
    'IMPACT_FLASH': dict(space='viewport', shape='flash', opacity=.55, duration=150, peak=.08),
    'BOARD_WASH': dict(space='viewport', shape='wash', opacity=.48, duration=0, pulse=.30, vignette=.32),
    'BADGE_RING': dict(space='over', shape='ring', size=.78, opacity=1.0, duration=0,
                       period=PULSE_PERIOD, endScale=3.15, border=.026),
}
PARTICLE_PRIMITIVES = {
    'CAPTURE_FRAGMENTS': dict(count=10, lifetime=420, size=[.035,.075], distance=[.3,.9],
                              spread=1, bias=.7, gravity=.25, rotation=220, opacity=.95),
    'ARRIVAL_SPARKS': dict(count=14, lifetime=360, size=[.025,.055], distance=[.45,1.45],
                          spread=1, bias=0, gravity=.1, rotation=70, opacity=.9),
    'AMBIENT_DUST': dict(count=4, lifetime=1000, period=PULSE_PERIOD, size=[.022,.040],
                        distance=[.08,.3], extent=2.5, spread=1, bias=0, gravity=-.12,
                        rotation=0, opacity=.8),
}
EFFECT_PRESETS = {
    'LOCAL_ACCENT': dict(contact=['SQUARE_GLOW'], capture=[], hold=[]),
    'TACTICAL_ACCENT': dict(contact=['LOCAL_GLOW','IMPACT_FLASH','ARRIVAL_SPARKS'],
                            capture=['CAPTURE_FRAGMENTS'], hold=[]),
    'HERO': dict(contact=['LOCAL_GLOW','IMPACT_FLASH','ARRIVAL_SPARKS'],
                 capture=['CAPTURE_FRAGMENTS'],
                 hold=['SQUARE_GLOW','HERO_BLOOM','BOARD_WASH','BADGE_RING','AMBIENT_DUST']),
}


def lighting_config(profile=LIGHTING_PROFILE):
    if profile not in {'LEGACY','REFERENCE'}:
        raise ValueError(f'Unknown lighting profile: {profile}')
    return dict(enabled=profile=='REFERENCE', profile=profile, seed=EFFECT_SEED,
                defaultPreset='LOCAL_ACCENT', defaultPalette='CYAN',
                theme=REFERENCE_THEME, palettes=ACCENT_PALETTES, presets=EFFECT_PRESETS,
                lights=LIGHT_PRIMITIVES, particles=PARTICLE_PRIMITIVES,
                pulsePeriod=PULSE_PERIOD, sampleInterval=PULSE_SAMPLE_INTERVAL,
                fadeDuration=EFFECT_FADE_DURATION, maxParticles=MAX_PARTICLES)
