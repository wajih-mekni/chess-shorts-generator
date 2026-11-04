"""Compose the static scene and inline runtime into a portable HTML preview."""
import json
from math import hypot, isfinite
from html import escape
from pathlib import Path
from string import Template
from . import layout
from .piece_memes import configure_piece_memes
from .motion import movement_presets
from .camera import camera_config, CAMERA_OVERSCAN
from .timing import TIMING_PROFILE, timing_config
from .choreography import CHOREOGRAPHY_PROFILE, choreography_config
from .reactions import REACTION_PROFILE, reaction_config
from .lighting import LIGHTING_PROFILE, lighting_config
from .directing import directing_config
from urllib.parse import quote

ASSETS = Path(__file__).parent
RUNTIME_ORDER = ("board", "camera", "camera_impulses", "motion", "choreography", "pieces",
                 "reactions", "effects", "lighting_plan", "particles", "lighting",
                 "media", "audio", "piece_memes", "director", "scheduler", "timeline")


def render_scene(scene, *, meme_mode="fixed", layout_mode="safe", meme_path=None, meme_volume=0.25,
                 meme_comment_text=None, music_path=None, music_volume=0.8,
                 movement_preset="NORMAL_MOVE", camera_enabled=None,
                 timing_profile=None, choreography_profile=None,
                 reaction_profile=None, lighting_profile=None, directing_profile='LEGACY',
                 brilliant_mode='standard', aggressive_config=None, very_aggressive_config=None, initial_delay=0.0,
                 piece_meme_mode="off", piece_memes=None, initial_piece_memes=None):
    scene, piece_meme_config = configure_piece_memes(scene, piece_meme_mode, piece_memes, initial_piece_memes)
    if (isinstance(initial_delay, bool) or not isinstance(initial_delay, (int, float))
            or not isfinite(initial_delay) or not 0 <= initial_delay <= 2_147_483.647):
        raise ValueError('initial_delay must be finite, non-negative seconds within the browser timer limit')
    if meme_mode not in ("fixed", "off"):
        raise ValueError(f"Unsupported meme mode: {meme_mode!r}; expected 'fixed' or 'off'")
    directing = directing_config(directing_profile, brilliant_mode=brilliant_mode, aggressive=aggressive_config,
                                 very_aggressive=very_aggressive_config)
    def profile(value, legacy):
        return value if value is not None else ('REFERENCE' if directing['enabled'] else legacy)
    timing_profile = profile(timing_profile, TIMING_PROFILE)
    choreography_profile = profile(choreography_profile, CHOREOGRAPHY_PROFILE)
    reaction_profile = profile(reaction_profile, REACTION_PROFILE)
    lighting_profile = profile(lighting_profile, LIGHTING_PROFILE)
    presets = movement_presets()
    if movement_preset not in presets:
        raise ValueError(f"Unknown movement preset: {movement_preset}")
    choreography = choreography_config(choreography_profile)
    reactions = reaction_config(reaction_profile)
    lighting = lighting_config(lighting_profile)
    for event in scene.get("timeline", []):
        move = event.get("move", {})
        if move.get('brilliant_mode', 'standard') not in {'standard', 'aggressive', 'very_aggressive'}:
            raise ValueError('Unknown per-move brilliant mode')
        if 'director_tier' in move and move['director_tier'] not in directing['tiers']:
            raise ValueError(f"Unknown director tier: {move['director_tier']}")
        name = move.get("effect_preset", lighting["defaultPreset"])
        if name != "NONE" and name not in lighting["presets"]:
            raise ValueError(f"Unknown effect preset: {name}")
        palette = move.get("effect_palette", lighting["defaultPalette"])
        if palette not in lighting["palettes"]:
            raise ValueError(f"Unknown effect palette: {palette}")
        for key in ("choreography_preset", "rook_choreography_preset"):
            name = event.get("move", {}).get(key)
            if name and name != "LEGACY" and name not in choreography["presets"]:
                raise ValueError(f"Unknown choreography preset: {name}")
        for channel in ("capture", "king"):
            name = event.get("move", {}).get(channel + "_reaction")
            if name is not None and name != "NONE":
                if name not in reactions["presets"] or reactions["presets"][name]["kind"] != channel:
                    raise ValueError(f"Invalid {channel} reaction: {name}")
    meme_video = (
        f'<video id="memeVideo" src="{escape(meme_path, quote=True)}" '
        'preload="auto" loop playsinline></video>'
        if meme_path else ""
    )

    meme_comment = (
        f'<div class="meme-comment">{escape(meme_comment_text)}</div>'
        if meme_comment_text else ""
    )
    meme_layer = (
        '<div class="reaction-area">\n'
        f'        {meme_video}\n'
        f'        {meme_comment}\n'
        '    </div>'
        if meme_mode == "fixed" else ""
    )

    music_audio = (
        f'<audio id="backgroundMusic" src="{escape(music_path, quote=True)}" '
        'preload="auto" loop></audio>'
        if music_path else ""
    )


    values = layout.layout_config(meme_mode, layout_mode)
    # Use the inscribed safe square for the existing destination camera solver.
    # Portrait height provides extra effect room, never an unsafe horizontal zoom.
    camera_viewport = ((min(values['VIEWPORT_WIDTH'], values['VIEWPORT_HEIGHT']) -
                        2 * values['CAMERA_EFFECT_MARGIN']) / values['BOARD_SCALE'])
    theme = lighting['theme']
    board_image = '../assets/board.svg'
    if lighting['enabled']:
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8">'
               '<defs><pattern id="squares" width="2" height="2" patternUnits="userSpaceOnUse">'
               f'<rect width="2" height="2" fill="{theme["light"]}"/>'
               f'<path d="M1 0h1v1H1zM0 1h1v1H0z" fill="{theme["dark"]}"/>'
               '</pattern></defs><rect width="8" height="8" fill="url(#squares)"/></svg>')
        board_image = 'data:image/svg+xml,' + quote(svg)
    values.update(board_image=board_image,
                  theme_class='lighting-reference' if lighting['enabled'] else '',
                  LIGHT_CANVAS=theme['canvas'], LIGHT_BACKING=theme['backing'])
    # A rotation-invariant backing on the outer rocking track covers even tall
    # portrait viewports. Only the outer track translates this backing; inner
    # shot/impact transforms cannot move it. Scale is always >= 1 on this owner.
    radius = hypot(values['VIEWPORT_WIDTH'], values['VIEWPORT_HEIGHT']) / (2 * values['BOARD_SCALE'])
    shake = directing['aggressive']['shakeTranslation']
    aggressive_overscan = max(0, radius - values['BOARD_LOGICAL_SIZE'] / 2) + hypot(shake, shake) + 1
    values.update(AGGRESSIVE_OVERSCAN=aggressive_overscan)
    values.update(CAMERA_OVERSCAN=CAMERA_OVERSCAN, SQUARE_SIZE=layout.BOARD_LOGICAL_SIZE / 8,
                  CAPTION_RIGHT=max(24, layout.MEME_X + layout.MEME_WIDTH -
                                    (layout.CANVAS_WIDTH - layout.RIGHT_UI_SAFE_AREA)),
                  meme_layer=meme_layer, music_audio=music_audio)
    data = {"scene": scene,
            "pieceMemeConfig": piece_meme_config,
            "playbackConfig": {"initialDelayMs": initial_delay * 1000},
            "directingConfig": directing,
            "cameraConfig": camera_config(camera_enabled, timing_profile,
                                          viewport_size=camera_viewport,
                                          aggressive=directing["aggressive"]),
            "timingConfig": timing_config(timing_profile),
            "choreographyConfig": choreography,
            "reactionConfig": reactions,
            "lightingConfig": lighting,
            "motion": {"presets": presets, "defaultPreset": movement_preset},
            "media": {"memeVolume": meme_volume, "musicVolume": music_volume},
            "layout": {"squareSize": layout.BOARD_LOGICAL_SIZE / 8,
                       "labelRight": (layout.CANVAS_WIDTH - layout.RIGHT_UI_SAFE_AREA -
                                      values['BOARD_X']) / values['BOARD_SCALE']}}
    if meme_mode == 'off' and layout_mode == 'crop':
        data['cameraConfig']['cropWide'] = True
    # Escape '<' so user content cannot terminate the inline script element.
    runtime = "\n".join("const " + name + " = " + json.dumps(value).replace("<", "\\u003c") + ";"
                        for name, value in data.items())
    runtime += """
const initialPieces = scene.pieces;
const moves = scene.moves;
const timeline = scene.timeline;
const hasMemeTriggers = timeline.some(event =>
    event.type === "meme" || event.move?.start_meme);
"""
    runtime += "\n" + "\n".join((ASSETS / (name + ".js")).read_text() for name in RUNTIME_ORDER)
    runtime += "\ncamera.reset();\ncameraMotion.reset();\ncreatePieces();\n"
    runtime += "if (pieceMemeConfig.initial) pieceMemeSystem.prepare().then(()=>pieceMemeSystem.initialize()).catch(console.error);\n"
    values["runtime"] = runtime
    # Keep scene.css valid standalone CSS; inject computed layout as custom properties.
    pixel_properties = (
        "CANVAS_WIDTH", "CANVAS_HEIGHT", "FRAME_X", "FRAME_Y",
        "VIEWPORT_WIDTH", "VIEWPORT_HEIGHT", "BOARD_OFFSET_X", "BOARD_OFFSET_Y",
        "BOARD_LOGICAL_SIZE", "CAMERA_OVERSCAN", "AGGRESSIVE_OVERSCAN", "SQUARE_SIZE",
        "MEME_X", "MEME_Y", "MEME_WIDTH", "MEME_HEIGHT", "CAPTION_RIGHT",
    )
    css_properties = {
        "--" + key.lower().replace("_", "-"): f"{values[key]}px"
        for key in pixel_properties
    }
    css_properties.update({"--board-scale": str(values["BOARD_SCALE"]),
                           "--meme-fit": values["MEME_FIT"]})
    layout_styles = ":root {\n" + "".join(
        f"    {key}: {value};\n" for key, value in css_properties.items()) + "}\n"
    values["styles"] = (layout_styles + (ASSETS / "scene.css").read_text() +
                        Template((ASSETS / "lighting.css").read_text()).substitute(values))
    return Template((ASSETS / "scene.html").read_text()).substitute(values)
