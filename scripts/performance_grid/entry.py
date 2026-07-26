# Performance grid — modular entry (imported by build_simple_grid.py).
from performance_grid.constants_builder import *  # noqa: F401,F403
from performance_grid.paths import ROOT, SCRIPTS_DIR, package_root, script_entry_paths
from performance_grid.td_runtime import _td_exec_ns
from performance_grid.assemble import (
    LOGIC,
    PANEL_EXEC,
    LEGACY_DROP,
    CELL_DRAGDROP,
    SCENE_DRAGDROP,
    AUTO_REPAIR,
    assemble_logic,
    assemble_settings_parexec,
    read_embedded,
)

SETTINGS_PAREXEC = assemble_settings_parexec(
    default_set_name=DEFAULT_SET_NAME,
    sets_subdir=SETS_SUBDIR,
)

from performance_grid.builder import *  # noqa: F401,F403
