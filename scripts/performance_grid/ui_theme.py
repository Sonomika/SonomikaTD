"""TouchDesigner native UI palette and typography (sRGB 0–1)."""
import sys


def _td_ui_font():
    """Match TD parameter UI: Segoe UI (Windows), Verdana (macOS)."""
    if sys.platform == 'darwin':
        return 'Verdana'
    return 'Segoe UI'


def _td_rgb(hex6):
    h = str(hex6).strip().lstrip('#')
    return (
        int(h[0:2], 16) / 255.0,
        int(h[2:4], 16) / 255.0,
        int(h[4:6], 16) / 255.0,
    )


# Typography (matches TD parameter dialogs)
TD_FONT = _td_ui_font()
TD_FONT_SIZE = 10
TD_FONT_SIZE_SMALL = 8

# Base grays from TD dark UI
TD_BG_MAIN = _td_rgb('2B2B2B')
TD_BG_HEADER = _td_rgb('1A1A1A')
TD_BG_INPUT = _td_rgb('464646')
TD_TEXT_ACTIVE = (1.0, 1.0, 1.0)
TD_TEXT_LABEL = _td_rgb('B3B3B3')
TD_SLIDER_TRACK = _td_rgb('111111')
TD_SLIDER_GROOVE = _td_rgb('1A1A1A')
TD_SLIDER_FILL = _td_rgb('666666')
TD_SLIDER_THUMB = _td_rgb('888888')

# Grid semantic aliases
GRID_FONT = TD_FONT
GRID_FONT_SIZE = TD_FONT_SIZE
CELL_NAME_FONT_SIZE = TD_FONT_SIZE_SMALL

EMPTY_CELL_R, EMPTY_CELL_G, EMPTY_CELL_B = TD_BG_INPUT
CELL_RING_CR, CELL_RING_CG, CELL_RING_CB = TD_TEXT_ACTIVE
CELL_RING_W = 2
CELL_RING_PAD = 3
CELL_RING_IDLE_CR, CELL_RING_IDLE_CG, CELL_RING_IDLE_CB = TD_SLIDER_THUMB
CELL_RING_IDLE_W = 1
CELL_BG_SELECTED_R, CELL_BG_SELECTED_G, CELL_BG_SELECTED_B = TD_BG_INPUT
CELL_BG_IDLE_R, CELL_BG_IDLE_G, CELL_BG_IDLE_B = TD_BG_INPUT
# Title strip: slightly darker than thumb/empty tile (#464646), lighter than main UI (#2B2B2B)
UI_NAME_BAR_BG = _td_rgb('383838')
SCENE_BTN_TILE_BG = TD_BG_INPUT
SCENE_CONTROL_TILE_ALPHA = 1.0
SCENE_CONTROL_BG_ALPHA = 0.0
SCENE_BAR_BG_ALPHA = 0.0
SCENE_BTN_TOPFILL = 'best'
UI_TEXT_PRIMARY = TD_TEXT_ACTIVE
UI_TEXT_SECONDARY = TD_TEXT_LABEL
TD_BIND_EXPR = _td_rgb('C8A8E8')
TD_BIND_BG = _td_rgb('3A2E4A')
UI_PREVIEW_BG = (0.0, 0.0, 0.0)

SCENE_ACTIVE_TEXT = TD_TEXT_ACTIVE
SCENE_IDLE_TEXT = TD_TEXT_LABEL
