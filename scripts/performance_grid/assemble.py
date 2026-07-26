"""Assemble TouchDesigner DAT source text from modular files."""
from __future__ import annotations

import os

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))

LOGIC_PARTS = [
    'ui_theme.py',
    'logic/00_bootstrap.py',
    'logic/10_matrix.py',
    'logic/20_canvas_media.py',
    'logic/30_cells.py',
    'logic/14_transport_bpm.py',
    'logic/15_brand.py',
    'logic/16_perf_readouts.py',
    'logic/17_osc_mapping.py',
    'logic/19_pulse_osc.py',
    'logic/21_audio_analysis.py',
    'logic/18_layer_opacity.py',
    'logic/40_grid_rows.py',
    'logic/50_cell_ui.py',
    'logic/60_composition.py',
    'logic/65_global_fx.py',
    'logic/66_cell_fx.py',
    'logic/67_map_control.py',
    'logic/70_params_layout.py',
    'logic/80_lifecycle_sets.py',
]


def _read(rel_path: str) -> str:
    path = os.path.join(_PKG_DIR, rel_path.replace('/', os.sep))
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def _unwrap_dat_source(text: str) -> str:
    """Strip `NAME = r'''` wrappers left from monolith extraction."""
    first = text.find("r'''")
    if first >= 0:
        text = text[first + 4:]
    last = text.rfind("'''")
    if last >= 0:
        text = text[:last]
    if text.startswith('\n'):
        text = text[1:]
    return text


def read_embedded(name: str) -> str:
    return _unwrap_dat_source(_read(os.path.join('embedded', name)))


def assemble_logic() -> str:
    chunks = [_read(p).rstrip() for p in LOGIC_PARTS]
    return '\n\n'.join(chunks) + '\n'


def assemble_settings_parexec(
    default_set_name: str = 'performance_set',
    sets_subdir: str = 'sets',
) -> str:
    """Settings DAT script needs set-name constants in its namespace."""
    preamble = (
        'DEFAULT_SET_NAME = {0!r}\n'
        'SETS_SUBDIR = {1!r}\n\n'
    ).format(default_set_name, sets_subdir)
    return preamble + read_embedded('settings_parexec.py')


LOGIC = assemble_logic()
PANEL_EXEC = read_embedded('panel_exec.py')
LEGACY_DROP = read_embedded('legacy_drop.py')
CELL_DRAGDROP = read_embedded('cell_dragdrop.py')
GLOBAL_FX_DRAGDROP = read_embedded('global_fx_dragdrop.py')
CELL_FX_DRAGDROP = read_embedded('cell_fx_dragdrop.py')
MAP_CONTROL_DRAGDROP = read_embedded('map_control_dragdrop.py')
SCENE_DRAGDROP = read_embedded('scene_dragdrop.py')
AUTO_REPAIR = read_embedded('auto_repair.py')
PULSE_FRAME_EXEC = read_embedded('pulse_frame_exec.py')
OSC_CALLBACKS = read_embedded('osc_callbacks.py')
MIDI_CALLBACKS = read_embedded('midi_callbacks.py')
MIDI_TABLE_EXEC = read_embedded('midi_table_exec.py')
