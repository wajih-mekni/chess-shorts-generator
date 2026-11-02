# Final composition in output pixels. Board internals retain one logical coordinate
# system so pieces, arrows, highlights and animation distances scale together.
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
TOP_SAFE_AREA = 150
BOTTOM_SAFE_AREA = 280
BOARD_SIZE = 960
FRAME_PADDING = 30
BOARD_FRAME_SIZE = BOARD_SIZE + 2 * FRAME_PADDING
FRAME_X = (CANVAS_WIDTH - BOARD_FRAME_SIZE) / 2
FRAME_Y = TOP_SAFE_AREA
BOARD_X = FRAME_X + FRAME_PADDING
BOARD_Y = FRAME_Y + FRAME_PADDING
BOARD_LOGICAL_SIZE = 1080
BOARD_SCALE = BOARD_SIZE / BOARD_LOGICAL_SIZE
MEME_WIDTH = 980
MEME_X = (CANVAS_WIDTH - MEME_WIDTH) / 2
MEME_Y = FRAME_Y + BOARD_FRAME_SIZE + 30
MEME_HEIGHT = CANVAS_HEIGHT - BOTTOM_SAFE_AREA - MEME_Y
RIGHT_UI_SAFE_AREA = 150
# Contain preserves faces/text for any source aspect ratio without guessing a crop.
MEME_FIT = "contain"

# Meme-free portrait viewport, in output pixels. Keep the complete board visible
# at the wide shot; K/L still intentionally frame a local neighborhood.
FULL_BOARD_MAX_SIZE = 960
FULL_VIEWPORT_SIDE_MARGIN = 24
FULL_VIEWPORT_TOP_MARGIN = 140
FULL_VIEWPORT_BOTTOM_MARGIN = 140
FULL_BOARD_SAFE_MARGIN = 112  # Board edge to viewport: kicks, rotation and glow.
FULL_CAMERA_EFFECT_MARGIN = 32  # Extra inset for focused K/L neighborhoods.

# Oversized square inside a tall viewport. These do not affect the safe layout.
CROP_BOARD_SIZE = 1440
CROP_VIEWPORT_SIDE_MARGIN = 0
CROP_VIEWPORT_TOP_MARGIN = 60
CROP_VIEWPORT_BOTTOM_MARGIN = 60
CROP_CAMERA_EFFECT_MARGIN = 24


def layout_config(meme_mode="fixed", layout_mode="safe"):
    """Resolve output geometry without changing the shared logical board space."""
    if layout_mode not in ("safe", "crop"):
        raise ValueError(f"Unsupported layout mode: {layout_mode!r}; expected 'safe' or 'crop'")
    values = {name: value for name, value in globals().items() if name.isupper()}
    values.update(VIEWPORT_WIDTH=BOARD_FRAME_SIZE, VIEWPORT_HEIGHT=BOARD_FRAME_SIZE,
                  BOARD_OFFSET_X=FRAME_PADDING, BOARD_OFFSET_Y=FRAME_PADDING,
                  CAMERA_EFFECT_MARGIN=0)
    if meme_mode == "fixed":
        return values
    if meme_mode != "off":
        raise ValueError(f"Unsupported meme mode: {meme_mode!r}")
    if layout_mode == "crop":
        width = CANVAS_WIDTH - 2 * CROP_VIEWPORT_SIDE_MARGIN
        height = CANVAS_HEIGHT - CROP_VIEWPORT_TOP_MARGIN - CROP_VIEWPORT_BOTTOM_MARGIN
        if (CROP_BOARD_SIZE <= 0 or min(CROP_VIEWPORT_SIDE_MARGIN,
                CROP_VIEWPORT_TOP_MARGIN, CROP_VIEWPORT_BOTTOM_MARGIN,
                CROP_CAMERA_EFFECT_MARGIN) < 0 or
                min(width, height) <= 2 * CROP_CAMERA_EFFECT_MARGIN):
            raise ValueError("Crop layout requires positive board and camera framing area")
        offset_x, offset_y = (width - CROP_BOARD_SIZE) / 2, (height - CROP_BOARD_SIZE) / 2
        values.update(VIEWPORT_WIDTH=width, VIEWPORT_HEIGHT=height,
                      FRAME_X=CROP_VIEWPORT_SIDE_MARGIN, FRAME_Y=CROP_VIEWPORT_TOP_MARGIN,
                      BOARD_SIZE=CROP_BOARD_SIZE, BOARD_SCALE=CROP_BOARD_SIZE / BOARD_LOGICAL_SIZE,
                      BOARD_OFFSET_X=offset_x, BOARD_OFFSET_Y=offset_y,
                      BOARD_X=CROP_VIEWPORT_SIDE_MARGIN + offset_x,
                      BOARD_Y=CROP_VIEWPORT_TOP_MARGIN + offset_y,
                      CAMERA_EFFECT_MARGIN=CROP_CAMERA_EFFECT_MARGIN)
        return values
    width = CANVAS_WIDTH - 2 * FULL_VIEWPORT_SIDE_MARGIN
    height = CANVAS_HEIGHT - FULL_VIEWPORT_TOP_MARGIN - FULL_VIEWPORT_BOTTOM_MARGIN
    size = min(FULL_BOARD_MAX_SIZE, width - 2 * FULL_BOARD_SAFE_MARGIN,
               height - 2 * FULL_BOARD_SAFE_MARGIN)
    if size <= 0 or min(FULL_VIEWPORT_SIDE_MARGIN, FULL_VIEWPORT_TOP_MARGIN,
                        FULL_VIEWPORT_BOTTOM_MARGIN, FULL_BOARD_SAFE_MARGIN,
                        FULL_CAMERA_EFFECT_MARGIN) < 0:
        raise ValueError("Full-board layout margins must leave a positive board area")
    if 2 * FULL_CAMERA_EFFECT_MARGIN >= min(width, height):
        raise ValueError("Full-board camera effect margin leaves no framing area")
    offset_x, offset_y = (width - size) / 2, (height - size) / 2
    values.update(VIEWPORT_WIDTH=width, VIEWPORT_HEIGHT=height,
                  FRAME_X=FULL_VIEWPORT_SIDE_MARGIN, FRAME_Y=FULL_VIEWPORT_TOP_MARGIN,
                  BOARD_SIZE=size, BOARD_SCALE=size / BOARD_LOGICAL_SIZE,
                  BOARD_OFFSET_X=offset_x, BOARD_OFFSET_Y=offset_y,
                  BOARD_X=FULL_VIEWPORT_SIDE_MARGIN + offset_x,
                  BOARD_Y=FULL_VIEWPORT_TOP_MARGIN + offset_y,
                  CAMERA_EFFECT_MARGIN=FULL_CAMERA_EFFECT_MARGIN)
    return values

