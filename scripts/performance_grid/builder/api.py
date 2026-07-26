import json
import os
import tempfile

from performance_grid.assemble import (
    AUTO_REPAIR,
    CELL_DRAGDROP,
    GLOBAL_FX_DRAGDROP,
    CELL_FX_DRAGDROP,
    MAP_CONTROL_DRAGDROP,
    LEGACY_DROP,
    LOGIC,
    MIDI_CALLBACKS,
    MIDI_TABLE_EXEC,
    OSC_CALLBACKS,
    PANEL_EXEC,
    PULSE_FRAME_EXEC,
    SCENE_DRAGDROP,
)
from performance_grid.constants_builder import *  # noqa: F401,F403
from performance_grid.paths import script_entry_paths
from performance_grid.td_runtime import (
    _resolve_td_op,
    apply_dat_scripts_to_network,
    discover_performance_mode_path,
    exec_builder_script,
    fresh_dat_scripts,
    inject_td_op_into_performance_grid,
)
from performance_grid.builder.helpers_layout import (
    _build_scene_bar,
    _collect_panel_paths,
    _ensure_column_xfade_nodes,
    _ensure_grid_custom_pars,
    _ensure_scenes_par,
    _wire_scene_bar_dragdrop,
)
from performance_grid.builder.helpers_settings import _build_settings
from performance_grid.builder.helpers_ui import (
    _ensure_grid_columns,
    _heal_perform_window,
    _performance_mode_patchable,
    _performance_mode_ready,
    _performance_mode_ui_grid,
    _set_par,
    _setup_grid_dragdrop,
)
from performance_grid.builder.build_network import build_simple_grid

# DEFAULT_COMP, LOGIC, _td_exec_ns, etc. come from performance_grid.builder package.


def _par_eval(node, name, default=None):
    try:
        return getattr(node.par, name).eval()
    except Exception:
        return default


def _table_cell(tbl, row, col, default=''):
    try:
        return str(tbl[row, col])
    except Exception:
        return default


def _bad_display_label(label):
    label = str(label or '').strip().lower()
    if not label:
        return True
    if label in ('touchdesigner', 'touchengine', 'samples', 'sample', 'map', 'tox', 'video'):
        return True
    return 'derivative' in label


def _display_label_from_path(path, clip_type='', existing=''):
    if not _bad_display_label(existing):
        return str(existing).strip()
    path = str(path or '').strip().strip('"').replace('\\', '/')
    name = os.path.basename(path.rstrip('/'))
    if str(clip_type or '').strip().lower() == 'tox' and name.lower().endswith('.tox'):
        name = name[:-4]
    return name if not _bad_display_label(name) else ''


def _snapshot_par_assignments(root):
    """Preserve user expressions/binds on loaded clip/tox parameters across rebuilds."""
    if root is None:
        return []
    out = []
    slots = root.op('slots')
    if slots is None:
        return out
    try:
        layers = [c for c in slots.children if c.name.startswith('layer_')]
    except Exception:
        layers = []
    for layer in layers:
        try:
            cells = [c for c in layer.children if c.name.startswith('col_')]
        except Exception:
            cells = []
        for cell in cells:
            for target_name in ('tox', 'video'):
                target = cell.op(target_name)
                if target is None:
                    continue
                try:
                    pars = list(target.customPars)
                except Exception:
                    pars = []
                try:
                    # Include a few built-in video params too, but avoid file/externaltox paths.
                    for pname in ('speed', 'index', 'play'):
                        try:
                            p = getattr(target.par, pname)
                            if p not in pars:
                                pars.append(p)
                        except Exception:
                            pass
                except Exception:
                    pass
                skip_names = frozenset((
                    'externaltox', 'enableexternaltox', 'enableexternaltoxpulse',
                    'reloadcustom', 'reloadbuiltin',
                ))
                for par in pars:
                    name = par.name
                    if name in skip_names:
                        continue
                    rec = {'owner': target.path, 'name': name}
                    keep = False
                    try:
                        expr = str(par.expr or '').strip()
                    except Exception:
                        expr = ''
                    if expr:
                        rec['expr'] = expr
                        keep = True
                    try:
                        bind_expr = str(par.bindExpr or '').strip()
                    except Exception:
                        bind_expr = ''
                    if bind_expr:
                        rec['bindExpr'] = bind_expr
                        keep = True
                    if keep:
                        out.append(rec)
                        continue
                    try:
                        rec['val'] = par.eval()
                        out.append(rec)
                    except Exception:
                        try:
                            rec['val'] = par.val
                            out.append(rec)
                        except Exception:
                            pass
    return out


def _restore_par_assignments(assignments):
    if not assignments:
        return 0
    restored = 0
    try:
        from td import ParMode as _TDParMode
    except Exception:
        _TDParMode = globals().get('ParMode', None)
    for rec in assignments:
        try:
            owner = op(rec.get('owner', ''))
            if owner is None:
                continue
            par = getattr(owner.par, rec.get('name', ''))
        except Exception:
            continue
        try:
            if rec.get('bindExpr'):
                par.bindExpr = rec['bindExpr']
                if _TDParMode is not None and hasattr(_TDParMode, 'BIND'):
                    par.mode = _TDParMode.BIND
                restored += 1
                continue
        except Exception:
            pass
        try:
            if rec.get('expr'):
                par.expr = rec['expr']
                if _TDParMode is not None:
                    if hasattr(_TDParMode, 'EXPRESSION'):
                        par.mode = _TDParMode.EXPRESSION
                    elif hasattr(_TDParMode, 'EXPRESS'):
                        par.mode = _TDParMode.EXPRESS
                restored += 1
                continue
        except Exception:
            pass
        try:
            if 'val' in rec:
                par.val = rec['val']
                if _TDParMode is not None and hasattr(_TDParMode, 'CONSTANT'):
                    par.mode = _TDParMode.CONSTANT
                restored += 1
        except Exception:
            pass
    return restored


def _node_position_record(node, key):
    try:
        rec = {
            'key': key,
            'x': float(node.nodeX),
            'y': float(node.nodeY),
        }
        try:
            rec['w'] = float(node.nodeWidth)
        except Exception:
            pass
        try:
            rec['h'] = float(node.nodeHeight)
        except Exception:
            pass
        return rec
    except Exception:
        return None


def _walk_children(node):
    try:
        children = list(node.children)
    except Exception:
        children = []
    for child in children:
        yield child
        for desc in _walk_children(child):
            yield desc


def _snapshot_node_positions(root):
    """Preserve network editor layout across destructive rebuilds."""
    out = []
    if root is not None:
        root_path = root.path.rstrip('/')
        rec = _node_position_record(root, '.')
        if rec is not None:
            out.append(rec)
        for node in _walk_children(root):
            try:
                rel = node.path[len(root_path):].lstrip('/')
                rec = _node_position_record(node, rel)
                if rec is not None:
                    out.append(rec)
            except Exception:
                pass
    for path in (
        SETTINGS_COMP,
        PROGRAM_PICK_COMP,
        '/out1', '/output_window',
    ):
        try:
            node = op(path)
            if node is not None:
                rec = _node_position_record(node, path)
                if rec is not None:
                    out.append(rec)
        except Exception:
            pass
    return out


def _restore_node_positions(root, positions):
    if root is None or not positions:
        return 0
    restored = 0
    for rec in positions:
        key = rec.get('key', '')
        try:
            if key == '.':
                node = root
            elif str(key).startswith('/'):
                node = op(key)
            else:
                node = root.op(key)
            if node is None:
                continue
            node.nodeX = rec.get('x', node.nodeX)
            node.nodeY = rec.get('y', node.nodeY)
            if 'w' in rec:
                try:
                    node.nodeWidth = rec['w']
                except Exception:
                    pass
            if 'h' in rec:
                try:
                    node.nodeHeight = rec['h']
                except Exception:
                    pass
            restored += 1
        except Exception:
            pass
    return restored


def _snapshot_matrix_state(root):
    """Best-effort set snapshot before a forced rebuild destroys performance_mode."""
    if root is None:
        return None
    par_assignments = _snapshot_par_assignments(root)
    node_positions = _snapshot_node_positions(root)
    logic = root.op('logic')
    if logic is not None and hasattr(logic, 'module'):
        try:
            mod = logic.module
            if hasattr(mod, '_export_grid_state'):
                state = mod._export_grid_state()
                if state is not None:
                    state['_par_assignments'] = par_assignments
                    state['_node_positions'] = node_positions
                    return state
        except Exception:
            pass

    tbl = root.op('clip_matrix')
    if tbl is None:
        return None
    clips = []
    try:
        for i in range(1, tbl.numRows):
            path = _table_cell(tbl, i, 'path').strip()
            ctype = _table_cell(tbl, i, 'type').strip()
            if not path or not ctype:
                continue
            clips.append({
                'scene': int(float(_table_cell(tbl, i, 'scene', '1') or 1)),
                'layer': int(float(_table_cell(tbl, i, 'layer', '1') or 1)),
                'col': int(float(_table_cell(tbl, i, 'col', '1') or 1)),
                'type': ctype,
                'path': path,
                'label': _display_label_from_path(path, ctype, _table_cell(tbl, i, 'label')),
                'render_scale': int(float(_table_cell(tbl, i, 'render_scale', '100') or 100)),
                'update_rate': int(float(_table_cell(tbl, i, 'update_rate', '1') or 1)),
                'frozen': str(_table_cell(tbl, i, 'frozen', '0')).strip().lower() in ('1', 'true', 'yes', 'on'),
            })
    except Exception:
        pass

    composition = []
    ctbl = root.op('comp_matrix') or root.op('chain_matrix')
    if ctbl is not None:
        try:
            for i in range(1, ctbl.numRows):
                composition.append({
                    'scene': int(float(_table_cell(ctbl, i, 'scene', '1') or 1)),
                    'layer': int(float(_table_cell(ctbl, i, 'layer', '1') or 1)),
                    'src_col': int(float(_table_cell(ctbl, i, 'src_col', '1') or 1)),
                })
        except Exception:
            pass

    state = {
        'version': SETS_VERSION,
        'clips': clips,
        'composition': composition,
        'num_scenes': int(float(_par_eval(root, 'Numscenes', DEFAULT_SCENES) or DEFAULT_SCENES)),
        'active_scene': int(float(_par_eval(root, 'Activescene', 1) or 1)),
        'num_layers': int(float(_par_eval(root, 'Numlayers', DEFAULT_LAYERS) or DEFAULT_LAYERS)),
        'num_cols': int(float(_par_eval(root, 'Numcols', NUM_COLS) or NUM_COLS)),
        'active_column': int(float(_par_eval(root, 'Activecolumn', 1) or 1)),
        'active_layer': int(float(_par_eval(root, 'Activelayer', 1) or 1)),
        'selected_layer': int(float(_par_eval(root, 'Selectedlayer', DEFAULT_LAYERS) or DEFAULT_LAYERS)),
        'selected_col': int(float(_par_eval(root, 'Selectedcol', 1) or 1)),
    }

    settings = op(SETTINGS_COMP)
    if settings is not None:
        try:
            state['canvas'] = {
                'width': int(float(settings.par.Canvaswidth.eval())),
                'height': int(float(settings.par.Canvasheight.eval())),
                'preset': str(settings.par.Canvaspreset.eval()),
                'background': list(
                    tuple(settings.par.Canvasbg.eval())[:3]
                    if hasattr(settings.par, 'Canvasbg')
                    else (
                        float(settings.par.Canvasbgr.eval()),
                        float(settings.par.Canvasbgg.eval()),
                        float(settings.par.Canvasbgb.eval()),
                    )
                ),
            }
        except Exception:
            pass
        state['_settings'] = {}
        for pname in ('Savefile', 'Openfile'):
            try:
                state['_settings'][pname] = str(getattr(settings.par, pname).eval())
            except Exception:
                pass
    state['_par_assignments'] = par_assignments
    state['_node_positions'] = node_positions
    return state if clips or composition else None


def _restore_matrix_state(comp_path, state):
    if not state:
        return False
    root = op(comp_path)
    logic = root.op('logic') if root is not None else None
    if logic is None or not hasattr(logic, 'module'):
        return False
    mod = logic.module
    if not hasattr(mod, 'load_performance_set'):
        return False
    fd, path = tempfile.mkstemp(prefix='sonomika_reload_restore_', suffix='.json')
    os.close(fd)
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(state, fh, indent=2)
        if not mod.load_performance_set(path):
            return False
        restored = _restore_par_assignments(state.get('_par_assignments') or [])
        root = op(comp_path)
        restored_positions = _restore_node_positions(root, state.get('_node_positions') or [])
        settings_state = state.get('_settings') or {}
        settings = op(SETTINGS_COMP)
        if settings is not None:
            for pname, value in settings_state.items():
                try:
                    getattr(settings.par, pname).val = value
                except Exception:
                    pass
        print('Reload: restored current set after rebuild')
        if restored:
            print('Reload: restored {} parameter assignment(s)'.format(restored))
        if restored_positions:
            print('Reload: restored {} node position(s)'.format(restored_positions))
        return True
    except Exception as exc:
        print('Reload: restore current set failed:', exc)
        return False
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


def link_performance_column(col=None, comp_path=None, fx_layer=None):
    """Re-wire active column from clip_matrix (video/tox cells)."""
    comp_path = comp_path or DEFAULT_COMP
    logic = op(comp_path + '/logic')
    if logic is None:
        print('Not found:', comp_path)
        return False
    logic.text = LOGIC
    logic.par.language = 'python'
    logic.par.extension = 'module'
    return logic.module.link_manual_setup(col, fx_layer)


def load_tox_to_cell(layer, col, path=None, comp_path=None):
    """Load a .tox into a grid cell without drag-drop (Textport fallback)."""
    comp_path = comp_path or DEFAULT_COMP
    path = path or os.path.join(ROOT, 'tox', 'touchengine', 'strobe_slices.tox')
    path = os.path.normpath(path).replace('\\', '/')
    if not os.path.isfile(path):
        print('File not found:', path)
        return False
    logic = op(comp_path + '/logic')
    if logic is None:
        print('No logic at', comp_path)
        return False
    logic.module.load_cell(int(layer), int(col), 'tox', path)
    return True


def _repair_panel_exec(root):
    panel_exec = root.op('panel_exec')
    if panel_exec is None:
        return
    panel_exec.text = PANEL_EXEC
    _set_par(panel_exec, 'panelvalue', 'lselect rselect u v insidev mousev scrollu scrollx wheel')
    _set_par(panel_exec, 'offtoon', True)
    _set_par(panel_exec, 'ontooff', True)
    _set_par(panel_exec, 'valuechange', True)
    _set_par(panel_exec, 'whileon', True)
    _set_par(panel_exec, 'active', True)
    paths = _collect_panel_paths(root)
    if paths:
        try:
            panel_exec.par.panels = ' '.join(paths)
            panel_exec.par.select = True
        except Exception:
            pass


def patch_performance_scripts(comp_path=None):
    """Light reload: refresh DAT scripts only — no rebuild, no onInit, grid preserved."""
    comp_path = comp_path or DEFAULT_COMP
    root = op(comp_path)
    if not _performance_mode_patchable(root):
        return False
    fx_state = {'cell': [], 'global': []}
    map_state = []
    try:
        old_module = root.op('logic').module
        if hasattr(old_module, 'export_cell_fx_state'):
            fx_state['cell'] = old_module.export_cell_fx_state()
        if hasattr(old_module, 'export_global_fx_state'):
            fx_state['global'] = old_module.export_global_fx_state()
        if hasattr(old_module, 'export_map_control_state'):
            map_state = old_module.export_map_control_state()
        if not map_state and hasattr(old_module, '_map_control_rows_from_live_op_storage'):
            map_state = old_module._map_control_rows_from_live_op_storage(root)
        if not map_state:
            try:
                import json
                raw = str(root.fetch('map_control_reload_json', '') or '').strip()
                if raw and raw != '[]':
                    map_state = json.loads(raw)
            except Exception:
                pass
    except Exception as exc:
        print('patch_performance_scripts: FX snapshot failed:', exc)
    try:
        import json
        if map_state:
            root.store('map_control_reload_json', json.dumps(map_state or []))
    except Exception:
        pass
    try:
        td_op = _resolve_td_op()
        inject_td_op_into_performance_grid(td_op=td_op)
        scripts = fresh_dat_scripts(td_op=td_op)
    except Exception as exc:
        print('patch_performance_scripts: assemble failed:', exc)
        scripts = {
            'logic': LOGIC,
            'panel_exec': PANEL_EXEC,
            'legacy_drop': LEGACY_DROP,
            'cell_dragdrop': CELL_DRAGDROP,
            'global_fx_dragdrop': GLOBAL_FX_DRAGDROP,
            'cell_fx_dragdrop': CELL_FX_DRAGDROP,
            'map_control_dragdrop': MAP_CONTROL_DRAGDROP,
            'scene_dragdrop': SCENE_DRAGDROP,
            'auto_repair': AUTO_REPAIR,
            'pulse_frame_exec': PULSE_FRAME_EXEC,
            'osc_callbacks': OSC_CALLBACKS,
            'midi_callbacks': MIDI_CALLBACKS,
            'midi_table_exec': MIDI_TABLE_EXEC,
            'settings_parexec': None,
        }
    apply_dat_scripts_to_network(root, scripts, td_op=_resolve_td_op())
    ui = root.op('ui')
    bar = ui.op('scene_bar') if ui is not None else None
    if bar is not None:
        _wire_scene_bar_dragdrop(bar)
    if _performance_mode_ready(root):
        _ensure_column_xfade_nodes(root)
        _repair_panel_exec(root)
    logic = root.op('logic')
    if logic is not None and hasattr(logic, 'module'):
        mod = logic.module
        try:
            if fx_state['cell'] and hasattr(mod, 'import_cell_fx_state'):
                mod.import_cell_fx_state(fx_state['cell'])
            if fx_state['global'] and hasattr(mod, 'import_global_fx_state'):
                mod.import_global_fx_state(fx_state['global'])
            if hasattr(mod, 'import_map_control_state'):
                rows = list(map_state or [])
                if not rows:
                    try:
                        import json
                        raw = str(root.fetch('map_control_reload_json', '') or '').strip()
                        if raw:
                            rows = json.loads(raw)
                    except Exception:
                        rows = []
                mod.import_map_control_state(rows)
        except Exception as exc:
            print('patch_performance_scripts: state restore failed:', exc)
        try:
            mod.onInit(full=False)
        except TypeError:
            try:
                mod.onInit()
            except Exception:
                pass
        except Exception:
            pass
        try:
            if hasattr(mod, '_update_cell_params_ui'):
                mod._update_cell_params_ui()
            if hasattr(mod, '_refresh_global_fx_ui'):
                mod._refresh_global_fx_ui()
            if hasattr(mod, '_refresh_map_control_layout_only'):
                mod._refresh_map_control_layout_only()
            elif hasattr(mod, 'refresh_map_control_ui'):
                mod.refresh_map_control_ui()
            if hasattr(mod, 'repair_map_dial_binds'):
                mod.repair_map_dial_binds()
        except Exception as exc:
            print('patch_performance_scripts: UI refresh failed:', exc)
        if hasattr(mod, 'post_reload_heal'):
            try:
                mod.post_reload_heal()
            except Exception:
                pass
    return True


def _apply_reload_from_builder_ns(ns, comp_path, builder_path):
    """Patch scripts; rebuild performance_mode first when logic DAT is missing."""
    td_op = _resolve_td_op()
    inject_td_op_into_performance_grid(td_op=td_op)
    comp_path = discover_performance_mode_path(td_op, comp_path)
    patchable_fn = _performance_mode_patchable
    patch_fn = ns.get('patch_performance_scripts')
    build_fn = ns.get('build_simple_grid') or build_simple_grid
    heal_fn = _heal_perform_window
    settings_fn = _build_settings

    root = td_op(comp_path)
    patchable = patchable_fn(root) if root and patchable_fn else False
    restore_state = None

    if root is None:
        if build_fn is None:
            print('performance_mode missing — build_simple_grid not available')
            return None
        print('Reload: creating performance_mode...')
        build_fn(comp_path=comp_path, open_perform=True)
    elif not patchable:
        if build_fn is None:
            print(
                'Reload: performance_mode at {} has no logic DAT — cannot rebuild'.format(
                    comp_path
                )
            )
            return None
        restore_state = _snapshot_matrix_state(root)
        if restore_state:
            print('Reload: captured current set before rebuild')
        print('Reload: performance_mode incomplete (no logic) — rebuilding...')
        build_fn(comp_path=comp_path, open_perform=True)

    root = td_op(comp_path)
    if root is None:
        print('Reload: performance_mode still missing after build')
        return None
    if patch_fn is None:
        print('Reload: patch_performance_scripts missing from builder')
        return None
    if not patch_fn(comp_path):
        print('Reload: could not patch performance_mode scripts')
        return None
    if heal_fn is not None:
        heal_fn(comp_path)
    if settings_fn is not None:
        try:
            settings_fn(td_op(comp_path))
        except Exception:
            pass
    try:
        from performance_grid.td_runtime import invalidate_performance_grid_modules
        invalidate_performance_grid_modules()
    except Exception:
        pass
    root = td_op(comp_path)
    logic = root.op('logic') if root is not None else None
    if logic is not None and hasattr(logic, 'module'):
        mod = logic.module
        if hasattr(mod, 'configure_audio_analysis'):
            try:
                mod.configure_audio_analysis()
                if hasattr(mod, '_apply_audio_device'):
                    mod._apply_audio_device()
            except Exception:
                pass
    if restore_state:
        _restore_matrix_state(comp_path, restore_state)
    print('Reloaded from', builder_path.replace('\\', '/'))
    return builder_path.replace('\\', '/')


def reload_performance_scripts(comp_path=None):
    """Reload builder from disk (rebuild if needed, then patch DAT scripts)."""
    td_op = _resolve_td_op()
    inject_td_op_into_performance_grid(td_op=td_op)
    comp_path = discover_performance_mode_path(td_op, comp_path or DEFAULT_COMP)
    project_folder = None
    root = td_op(comp_path)
    if root is not None:
        try:
            project_folder = root.project.folder
        except Exception:
            pass
    ordered = script_entry_paths(project_folder)
    if not ordered:
        print('reload_performance_scripts: build_simple_grid.py not found on disk')
        print('  Set SONOMIKA_TD_ROOT to your TouchDesigner repo folder, then retry')
        return None
    last_exc = None
    for path in ordered:
        try:
            ns = exec_builder_script(path, td_op=td_op)
            return _apply_reload_from_builder_ns(ns, comp_path, path)
        except Exception as exc:
            last_exc = exc
            import traceback
            print('Reload error:', path, exc)
            traceback.print_exc()
    if last_exc is not None:
        print('reload_performance_scripts: all builder paths failed')
    else:
        print('reload_performance_scripts: build_simple_grid.py not found')
    return None


def repair_performance_drops(comp_path=None, allow_rebuild=False):
    """Patch grid for drag-reposition between cells + Explorer file drops."""
    comp_path = comp_path or DEFAULT_COMP
    root = op(comp_path)
    if root is None:
        print('Not found:', comp_path)
        return False
    if not _performance_mode_ready(root):
        if allow_rebuild:
            print('performance_mode incomplete — rebuilding with Perform UI...')
            build_simple_grid(comp_path=comp_path, open_perform=True)
            _heal_perform_window(comp_path)
            return True
        print('performance_mode incomplete — run build_simple_grid(open_perform=True)')
        _heal_perform_window(comp_path)
        return False
    _build_settings(root)
    _ensure_column_xfade_nodes(root)
    drop_cb = root.op('drop_callbacks')
    if drop_cb is not None:
        try:
            drop_cb.destroy()
        except Exception:
            pass
    ui = root.op('ui')
    grid = _performance_mode_ui_grid(ui) if ui is not None else None
    legacy = root.op('legacy_drop')
    if legacy is not None:
        legacy.text = LEGACY_DROP
        legacy.par.language = 'python'
    if grid is not None:
        _setup_grid_dragdrop(grid)
        _ensure_grid_columns(root)
    _ensure_grid_custom_pars(root)
    _ensure_scenes_par(root)
    ui = root.op('ui')
    bar, _paths = _build_scene_bar(ui, root)
    if bar is not None:
        _wire_scene_bar_dragdrop(bar)
    _repair_panel_exec(root)
    logic = root.op('logic')
    if logic is not None:
        logic.text = LOGIC
        logic.par.language = 'python'
        logic.par.extension = 'module'
    if logic is not None and hasattr(logic.module, '_ensure_grid_stack'):
        logic.module._ensure_grid_stack(root)
    if logic is not None and hasattr(logic.module, '_ensure_max_layers'):
        logic.module._ensure_max_layers(root)
    if logic is not None and hasattr(logic.module, 'repair_ui_drops'):
        logic.module.repair_ui_drops()
    if logic is not None and hasattr(logic.module, 'repair_cell_labels'):
        logic.module.repair_cell_labels()
    if logic is not None and hasattr(logic.module, 'repair_all_columns'):
        try:
            logic.module.repair_all_columns()
        except Exception:
            pass
    if logic is not None and hasattr(logic.module, 'dedupe_grid_assets'):
        try:
            logic.module.dedupe_grid_assets()
        except Exception:
            pass
    auto = root.op('auto_repair')
    if auto is None:
        auto = root.create('executeDAT', 'auto_repair')
        auto.text = AUTO_REPAIR
        auto.par.active = True
        auto.par.start = True
        auto.par.framestart = True
    else:
        auto.text = AUTO_REPAIR
    if logic is not None and hasattr(logic.module, 'onInit'):
        try:
            logic.module.onInit(full=False)
        except TypeError:
            try:
                logic.module.onInit()
            except Exception:
                pass
        except Exception:
            pass
    else:
        print('Grid cells accept drag-reposition and Explorer drops')
    _heal_perform_window(comp_path)
    return True


def main(open_perform=False):
    diag_mcp()
    result = build_simple_grid(open_perform=open_perform)
    print('Built simple grid -> {}'.format(result['tox']))
    print('Program out:', result['program_out'])
    return result


if __name__ == '__main__':
    main(open_perform=True)
