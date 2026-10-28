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

