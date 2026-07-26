"""One-shot splitter: reads a monolithic build_simple_grid.py into modules.

Prefer editing logic/ and embedded/ directly. To re-run this tool, point MONOLITH
at a full single-file copy (not the thin shim in scripts/build_simple_grid.py).
"""
from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = HERE
# Full monolith backup (optional); default may be the thin shim — check size before run.
MONOLITH = os.environ.get(
    'PERF_GRID_MONOLITH',
    os.path.normpath(os.path.join(HERE, '..', '..', '..', 'scripts', 'build_simple_grid.py')),
)


def _read_lines():
    with open(MONOLITH, encoding='utf-8') as fh:
        return fh.read().splitlines(keepends=True)


def _slice(lines, start, end):
    """1-based inclusive line numbers."""
    return ''.join(lines[start - 1:end])


def _write(rel_path, content, strip_leading_blank=False):
    path = os.path.join(PKG, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if strip_leading_blank:
        content = content.lstrip('\n')
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(content)
    print('wrote', rel_path, len(content))


def main():
    if not os.path.isfile(MONOLITH):
        raise SystemExit('Monolith not found: ' + MONOLITH)
    lines = _read_lines()

    embedded = {
        'embedded/settings_parexec.py': (37, 171),
        'embedded/panel_exec.py': (226, 383),
        'embedded/legacy_drop.py': (385, 482),
        'embedded/cell_dragdrop.py': (484, 659),
        'embedded/auto_repair.py': (661, 681),
    }
    for rel, (a, b) in embedded.items():
        _write(rel, _slice(lines, a, b))

    logic_parts = [
        ('logic/00_bootstrap.py', 684, 786),
        ('logic/10_matrix.py', 787, 1174),
        ('logic/20_canvas_media.py', 1175, 1708),
        ('logic/30_cells.py', 1710, 2147),
        ('logic/40_grid_rows.py', 2149, 2566),
        ('logic/50_cell_ui.py', 2568, 3015),
        ('logic/60_composition.py', 3017, 3387),
        ('logic/70_params_layout.py', 3389, 4332),
        ('logic/80_lifecycle_sets.py', 4334, 4942),
    ]
    for rel, a, b in logic_parts:
        _write(rel, _slice(lines, a, b))

    builder_parts = [
        ('builder/helpers_layout.py', 4946, 5285),
        ('builder/helpers_ui.py', 5286, 5829),
        ('builder/helpers_settings.py', 5830, 6153),
        ('builder/build_network.py', 6155, 6357),
        ('builder/api.py', 6360, 6606),
    ]
    for rel, a, b in builder_parts:
        _write(rel, _slice(lines, a, b))

    _write('constants_builder.py', _slice(lines, 5, 35) + _slice(lines, 173, 224))
    _write('td_runtime.py', _slice(lines, 1, 17))


if __name__ == '__main__':
    main()
