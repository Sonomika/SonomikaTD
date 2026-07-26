import os

from performance_grid.assemble import (
    AUTO_REPAIR, LEGACY_DROP, LOGIC, PANEL_EXEC,
    GLOBAL_FX_DRAGDROP, CELL_FX_DRAGDROP, MAP_CONTROL_DRAGDROP,
)
from performance_grid.constants_builder import *  # noqa: F401,F403
from performance_grid.builder.helpers_layout import (
    _build_scene_bar,
    _col_x,
    _ensure_column_xfade_nodes,
    _grid_content_w,
    _pin_scroll_label,
)
from performance_grid.builder.helpers_settings import (
    _build_settings,
    _project_parent,
    _safe_teardown,
    _setup_root_output,
)
from performance_grid.builder.helpers_ui import (
    _bind_canvas_res,
    _build_layer,
    _build_program_preview,
    _enable_cell_dragdrop,
    _make_cell,
    _pass_drop,
    _set_par,
    _setup_cell_params_panel,
    _setup_grid_dragdrop,
    _style_cell,
)


def build_simple_grid(comp_path=None, tox_path=None, open_perform=False):
    comp_path = comp_path or DEFAULT_COMP
    tox_path = tox_path or DEFAULT_TOX

    parent = _project_parent()
    if parent is None or parent.path == '/':
        raise RuntimeError('No project COMP found (expected /project1 or similar)')

    _safe_teardown(comp_path)

    root = parent.create('baseCOMP', 'performance_mode')
    root.nodeX = 0
    root.nodeY = 0

    _build_settings(root)

    matrix = root.create('tableDAT', 'clip_matrix')
    matrix.clear()
    matrix.appendRow(['scene', 'layer', 'col', 'type', 'path', 'label', 'render_scale', 'update_rate', 'frozen'])

    comp_matrix = root.create('tableDAT', 'comp_matrix')
    comp_matrix.clear()
    comp_matrix.appendRow(['scene', 'layer', 'src_col'])

    logic = root.create('textDAT', 'logic')
    logic.text = LOGIC
    logic.par.language = 'python'
    logic.par.extension = 'module'

    auto_repair = root.create('executeDAT', 'auto_repair')
    auto_repair.text = AUTO_REPAIR
    auto_repair.par.active = True
    auto_repair.par.start = True
    auto_repair.par.framestart = True

    panel_exec = root.create('panelexecuteDAT', 'panel_exec')
    panel_exec.text = PANEL_EXEC
    _set_par(panel_exec, 'panelvalue', 'lselect rselect u v insidev mousev scrollu scrollx wheel')
    _set_par(panel_exec, 'offtoon', True)
    _set_par(panel_exec, 'ontooff', True)
    _set_par(panel_exec, 'valuechange', True)
    _set_par(panel_exec, 'whileon', True)

    legacy_drop = root.create('textDAT', 'legacy_drop')
    legacy_drop.text = LEGACY_DROP
    legacy_drop.par.language = 'python'

    global_fx_drop = root.create('textDAT', 'global_fx_dragdrop')
    global_fx_drop.text = GLOBAL_FX_DRAGDROP
    global_fx_drop.par.language = 'python'

    cell_fx_drop = root.create('textDAT', 'cell_fx_dragdrop')
    cell_fx_drop.text = CELL_FX_DRAGDROP
    cell_fx_drop.par.language = 'python'

    map_control_drop = root.create('textDAT', 'map_control_dragdrop')
    map_control_drop.text = MAP_CONTROL_DRAGDROP
    map_control_drop.par.language = 'python'

    slots = root.create('baseCOMP', 'slots')
    for layer_idx in range(1, NUM_LAYERS + 1):
        _build_layer(slots, layer_idx)

    chain_out = root.create('selectTOP', 'chain_out')
    _bind_canvas_res(chain_out)
    _set_par(chain_out, 'top', expr="op('slots/layer_1/col_1/out1')")
    _ensure_column_xfade_nodes(root)

    global_fx_out = root.create('selectTOP', 'global_fx_out')
    _bind_canvas_res(global_fx_out)
    _set_par(global_fx_out, 'top', expr="op('chain_out')")

    program_sel = root.create('selectTOP', 'program_sel')
    _bind_canvas_res(program_sel)
    _set_par(program_sel, 'top', expr="op('global_fx_out')")

    program_out = root.create('outTOP', 'out1')
    _set_par(program_out, 'outputresolution', 'useinput')
    program_sel.outputConnectors[0].connect(program_out.inputConnectors[0])

    ui = root.create('containerCOMP', 'ui')
    _set_par(ui, 'x', 0)
    _set_par(ui, 'y', 0)
    _set_par(ui, 'align', 'none')
    _set_par(ui, 'bgcolorr', TD_BG_MAIN[0])
    _set_par(ui, 'bgcolorg', TD_BG_MAIN[1])
    _set_par(ui, 'bgcolorb', TD_BG_MAIN[2])
    _set_par(ui, 'bgalpha', 1.0)
    _pass_drop(ui)

    _build_program_preview(ui)
    scene_bar, scene_paths = _build_scene_bar(ui, root)

    stack = ui.create('containerCOMP', 'grid_stack')
    _set_par(stack, 'x', GRID_X0)
    _set_par(stack, 'w', UI_W - GRID_X0)
    _set_par(stack, 'align', 'none')
    _set_par(stack, 'phscrollbar', 'on' if _grid_content_w() > (UI_W - GRID_X0) + 2 else 'off')
    _set_par(stack, 'pvscrollbar', 'off')
    _pass_drop(stack)

    hdr = stack.create('containerCOMP', 'grid_header')
    _set_par(hdr, 'x', 0)
    _set_par(hdr, 'w', _grid_content_w())
    _set_par(hdr, 'h', GRID_HDR_H)
    _set_par(hdr, 'phscrollbar', 'off')
    _set_par(hdr, 'pvscrollbar', 'off')
    _pass_drop(hdr)

    grid = stack.create('containerCOMP', 'grid')
    _set_par(grid, 'x', 0)
    _set_par(grid, 'phscrollbar', 'off')
    _set_par(grid, 'pvscrollbar', 'off')
    _set_par(grid, 'align', 'none')
    _pass_drop(grid)
    _setup_grid_dragdrop(grid)
    corner = hdr.create('containerCOMP', 'corner')
    _make_cell(corner, ROW_LABEL_W, GRID_HDR_H, 'Layer', kind='header')
    _style_cell(corner, 'label')
    _pin_scroll_label(corner)
    _pass_drop(corner)

    cell_paths = []
    for c in range(1, NUM_COLS + 1):
        ch = hdr.create('containerCOMP', 'colhdr_{}'.format(c))
        _make_cell(ch, CELL_W, GRID_HDR_H, 'Col {}'.format(c), kind='header')
        _style_cell(ch, 'header')
        _set_par(ch, 'x', _col_x(c))
        _pass_drop(ch)
        cell_paths.append(ch.path)

    y = 0
    for layer in range(NUM_LAYERS, 0, -1):
        row = grid.create('containerCOMP', 'row_{}'.format(layer))
        _set_par(row, 'w', _grid_content_w())
        _set_par(row, 'h', CELL_H + 2)
        _set_par(row, 'y', y)
        _pass_drop(row)
        rl = row.create('containerCOMP', 'rowlabel')
        _make_cell(rl, ROW_LABEL_W, CELL_H - 2, 'L{}'.format(NUM_LAYERS - layer + 1), kind='header')
        _style_cell(rl, 'label')
        _pin_scroll_label(rl)
        _pass_drop(rl)
        cell_paths.append(rl.path)
        for c in range(1, NUM_COLS + 1):
            cell = row.create('containerCOMP', 'cell_{}_{}'.format(layer, c))
            _make_cell(cell, CELL_W, CELL_H)
            _set_par(cell, 'x', _col_x(c))
            _enable_cell_dragdrop(cell, grid, root.op('legacy_drop'))
            cell_paths.append(cell.path)
        y += CELL_H + 4

    _set_par(hdr, 'y', y)
    _set_par(grid, 'h', y)
    y += GRID_HDR_H + CELL_GAP + 4
    _set_par(stack, 'h', y)
    _setup_cell_params_panel(ui, y + 4)

    try:
        panel_exec.par.panels = ' '.join(scene_paths + [stack.path, grid.path] + cell_paths)
        panel_exec.par.select = True
    except Exception:
        pass

    page = root.appendCustomPage('Grid')
    for name, label, default, mn, mx, kind in [
        ('Numscenes', 'Scenes', DEFAULT_SCENES, MIN_SCENES, MAX_SCENES, 'int'),
        ('Activescene', 'Active Scene', 1, MIN_SCENES, MAX_SCENES, 'int'),
        ('Numlayers', 'Layers', DEFAULT_LAYERS, MIN_LAYERS, MAX_LAYERS, 'int'),
        ('Numcols', 'Columns', NUM_COLS, 1, 256, 'int'),
        ('Activelayer', 'Active Layer', 1, 1, MAX_LAYERS, 'int'),
        ('Activecolumn', 'Active Column', 1, 1, NUM_COLS, 'int'),
        ('Selectedlayer', 'Layer', 1, 1, MAX_LAYERS, 'int'),
        ('Selectedcol', 'Column', 1, 1, NUM_COLS, 'int'),
        ('Status', 'Status', 'Ready', 0, 0, 'str'),
    ]:
        if kind == 'int':
            p = page.appendInt(name, label=label)
            p.default = default
            p.min = mn
            p.max = mx
            p.val = default
        else:
            p = page.appendStr(name, label=label)
            p.val = default
    page.appendPulse('Windowopen', label='WINDOW OPEN')

    sel_page = root.appendCustomPage('Selected Cell')
    sel_info = sel_page.appendStr('Cellinfo', label='Selected')
    sel_info.val = '(click a grid cell)'
    try:
        sel_info.readOnly = True
    except Exception:
        pass

    parexec = root.create('parameterexecuteDAT', 'parexec')
    parexec.par.op = root
    parexec.par.pars = 'Windowopen'
    parexec.par.valuechange = False
    parexec.text = r'''def onPulse(par):
    if par.name == 'Windowopen':
        parent().op('logic').module._open_output()
'''

    _set_par(ui, 'w', UI_W)
    _set_par(ui, 'h', UI_H)
    root.par.opviewer = ui

    rout, win = _setup_root_output(program_out)

    if open_perform:
        perform = op('/perform')
        if perform is not None:
            perform.par.winop = ui.path
            perform.par.interact = True
            perform.par.drawwindow = True
            _set_par(perform, 'winw', UI_W)
            _set_par(perform, 'winh', UI_H)

    logic.module.onInit()

    os.makedirs(os.path.dirname(tox_path), exist_ok=True)
    root.save(tox_path)

    return {
        'comp': root.path,
        'tox': tox_path,
        'program_out': rout.path,
        'output_window': win.path,
    }
