# TouchDesigner exec helpers — sys.path, package cache bust, fresh DAT assembly.
from __future__ import annotations

import os
import sys


_SETTINGS_PATHS = ('/settings',)


def _resolve_td_op(td_op=None):
    """Return TouchDesigner's op(); must be passed in when called from imported modules."""
    if td_op is not None:
        return td_op
    try:
        return op  # noqa: F821 — TouchDesigner Textport / DAT
    except NameError:
        pass
    try:
        import __main__ as main
        o = getattr(main, 'op', None)
        if o is not None:
            return o
    except Exception:
        pass
    raise RuntimeError(
        'TouchDesigner op() is not available. '
        'Run this in the TouchDesigner Textport (not system Python — no "python >>>" prompt). '
        'Dialog: Dialogs → Textport and DATs, or press Alt+T.'
    )


def _resolve_settings_op(td_op=None):
    td_op = _resolve_td_op(td_op)
    for path in _SETTINGS_PATHS:
        try:
            settings = td_op(path)
            if settings is not None:
                return settings
        except Exception:
            pass
    return None


def _td_exec_ns(td_op=None, extra=None):
    """Namespace for exec(build_simple_grid.py) inside TouchDesigner."""
    ns = dict(extra or {})
    ns['op'] = _resolve_td_op(td_op)
    for name in ('me', 'parent', 'root', 'ParMode', 'absTime', 'run', 'ui', 'tdu', 'app'):
        if name in ns:
            continue
        try:
            ns[name] = eval(name)
        except Exception:
            pass
    return ns


SONOMIKA_SCRIPTS_STORE_KEY = 'sonomika_scripts_dir'


def _is_scripts_dir(path: str | None) -> bool:
    if not path:
        return False
    return os.path.isdir(os.path.join(os.path.normpath(path), 'performance_grid'))


def _walk_up_scripts_dir(start_dir: str | None, max_levels: int = 8) -> str | None:
    d = os.path.normpath(str(start_dir or ''))
    if not d or not os.path.isdir(d):
        return None
    for _ in range(max_levels):
        scripts = os.path.join(d, 'scripts')
        if _is_scripts_dir(scripts):
            return os.path.normpath(scripts)
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def fetch_stored_scripts_dir(td_op=None) -> str | None:
    try:
        td = _resolve_td_op(td_op)
        stored = str(td('/').fetch(SONOMIKA_SCRIPTS_STORE_KEY, '') or '').strip()
        if _is_scripts_dir(stored):
            return os.path.normpath(stored)
    except Exception:
        pass
    return None


def remember_scripts_dir(scripts_dir: str | None, td_op=None) -> None:
    if not _is_scripts_dir(scripts_dir):
        return
    try:
        td = _resolve_td_op(td_op)
        td('/').store(
            SONOMIKA_SCRIPTS_STORE_KEY,
            os.path.normpath(str(scripts_dir)).replace('\\', '/'),
        )
    except Exception:
        pass


def discover_scripts_dir(builder_path: str | None = None, td_op=None) -> str | None:
    """Directory containing performance_grid/ (for sys.path)."""
    stored = fetch_stored_scripts_dir(td_op=td_op)
    if stored:
        return stored
    if builder_path:
        builder_path = os.path.normpath(builder_path)
        scripts_dir = os.path.dirname(builder_path)
        if _is_scripts_dir(scripts_dir):
            remember_scripts_dir(scripts_dir, td_op=td_op)
            return scripts_dir
        alt = os.path.normpath(os.path.join(scripts_dir, '..', 'SonomikaTD', 'scripts'))
        if _is_scripts_dir(alt):
            remember_scripts_dir(alt, td_op=td_op)
            return alt
    env = os.environ.get('SONOMIKA_TD_ROOT', '').strip()
    if env:
        p = os.path.normpath(os.path.join(env, 'scripts'))
        if _is_scripts_dir(p):
            remember_scripts_dir(p, td_op=td_op)
            return p
    try:
        td = _resolve_td_op(td_op)
        proj = td('/').project
        pf = str(getattr(proj, 'folder', '') or '').strip()
        toe = str(getattr(proj, 'file', '') or getattr(proj, 'savePath', '') or '').strip()
    except Exception:
        pf = ''
        toe = ''
    candidates: list[str] = []
    if pf:
        candidates.extend([
            os.path.join(pf, 'scripts'),
            os.path.join(pf, 'SonomikaTD', 'scripts'),
        ])
        walked = _walk_up_scripts_dir(pf)
        if walked:
            candidates.append(walked)
    if toe:
        toe_dir = os.path.dirname(toe)
        candidates.extend([
            os.path.join(toe_dir, 'scripts'),
            os.path.join(toe_dir, 'SonomikaTD', 'scripts'),
            os.path.join(os.path.dirname(toe_dir), 'SonomikaTD', 'scripts'),
        ])
        walked = _walk_up_scripts_dir(toe_dir)
        if walked:
            candidates.append(walked)
    seen: set[str] = set()
    for p in candidates:
        p = os.path.normpath(p)
        if p in seen:
            continue
        seen.add(p)
        if _is_scripts_dir(p):
            remember_scripts_dir(p, td_op=td_op)
            return p
    pkg = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.normpath(os.path.join(pkg, '..'))
    if _is_scripts_dir(scripts_dir):
        remember_scripts_dir(scripts_dir, td_op=td_op)
        return scripts_dir
    return None


def _ensure_scripts_on_path(scripts_dir: str | None) -> str | None:
    if not scripts_dir or not os.path.isdir(scripts_dir):
        return None
    scripts_dir = os.path.normpath(scripts_dir)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    return scripts_dir


def invalidate_performance_grid_modules():
    for key in list(sys.modules.keys()):
        if key == 'performance_grid' or key.startswith('performance_grid.'):
            del sys.modules[key]


def discover_performance_mode_path(td_op=None, preferred=None):
    """Resolve live performance_mode COMP path in the current project."""
    td_op = _resolve_td_op(td_op)
    if preferred:
        try:
            if td_op(preferred) is not None:
                return preferred
        except Exception:
            pass
    for path in ('/project1/performance_mode', '/performance_mode'):
        try:
            if td_op(path) is not None:
                return path
        except Exception:
            pass
    try:
        parent = td_op('/project1')
        if parent is None:
            parent = td_op('/')
        if parent is not None:
            pm = parent.op('performance_mode')
            if pm is not None:
                return pm.path
    except Exception:
        pass
    return preferred or '/project1/performance_mode'


def inject_td_op_into_performance_grid(td_op=None):
    """Give modular chunks the TouchDesigner + builder globals the monolith had."""
    td_op = _resolve_td_op(td_op)
    shared = {'op': td_op, 'os': os, 'sys': sys}
    try:
        from performance_grid import constants_builder as constants
        for name, value in constants.__dict__.items():
            if name.isupper() or name in ('ROOT',):
                shared[name] = value
    except Exception:
        pass
    try:
        from performance_grid import assemble
        for name in ('LOGIC', 'PANEL_EXEC', 'LEGACY_DROP', 'CELL_DRAGDROP', 'GLOBAL_FX_DRAGDROP', 'CELL_FX_DRAGDROP', 'MAP_CONTROL_DRAGDROP', 'SCENE_DRAGDROP', 'AUTO_REPAIR'):
            if hasattr(assemble, name):
                shared[name] = getattr(assemble, name)
        if all(name in shared for name in ('DEFAULT_SET_NAME', 'SETS_SUBDIR')):
            shared['SETTINGS_PAREXEC'] = assemble.assemble_settings_parexec(
                default_set_name=shared['DEFAULT_SET_NAME'],
                sets_subdir=shared['SETS_SUBDIR'],
            )
    except Exception:
        pass
    for mod_name in (
        'performance_grid.builder.helpers_layout',
        'performance_grid.builder.helpers_ui',
        'performance_grid.builder.helpers_settings',
    ):
        try:
            mod = sys.modules.get(mod_name)
            if mod is None:
                continue
            for name, value in mod.__dict__.items():
                if name.startswith('_') and callable(value):
                    shared[name] = value
        except Exception:
            pass
    for mod in list(sys.modules.values()):
        name = getattr(mod, '__name__', '') or ''
        if name == 'performance_grid' or name.startswith('performance_grid.'):
            mod.__dict__.update(shared)
    return td_op


def exec_builder_script(path: str, td_op=None) -> dict:
    """Run build_simple_grid.py with sys.path + fresh performance_grid import."""
    path = os.path.normpath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    td_op = _resolve_td_op(td_op)
    scripts_dir = discover_scripts_dir(path, td_op=td_op)
    _ensure_scripts_on_path(scripts_dir)
    invalidate_performance_grid_modules()
    ns = _td_exec_ns(td_op=td_op)
    ns['__file__'] = path
    ns['__name__'] = '__main__'
    with open(path, encoding='utf-8') as fh:
        code = fh.read()
    exec(compile(code, path, 'exec'), ns)
    inject_td_op_into_performance_grid(td_op=td_op)
    return ns


def _set_dat_text(dat, text, language='python'):
    if dat is None or not text:
        return
    try:
        # Word-wrap inserts newlines into long source lines and breaks Python.
        if hasattr(dat.par, 'wordwrap'):
            try:
                dat.par.wordwrap = 'off'
            except Exception:
                try:
                    dat.par.wordwrap = False
                except Exception:
                    pass
        dat.text = text
        if language:
            dat.par.language = language
    except Exception:
        pass


def _grid_dragdrop_dat(grid, td_op):
    if grid is None:
        return None
    cb = grid.op('cell_dragdrop')
    if cb is None:
        try:
            cb = grid.create('textDAT', 'cell_dragdrop')
        except Exception:
            cb = None
    return cb


def apply_dat_scripts_to_network(root, scripts, td_op=None):
    """Write all assembled DAT scripts into performance_mode + settings COMP."""
    td_op = _resolve_td_op(td_op)
    if root is None or not scripts:
        return False
    logic = root.op('logic')
    if logic is None:
        return False
    _set_dat_text(logic, scripts.get('logic'))
    try:
        logic.par.extension = 'module'
    except Exception:
        pass
    panel_exec = root.op('panel_exec')
    if panel_exec is not None:
        _set_dat_text(panel_exec, scripts.get('panel_exec'))
        for pname, val in (
            ('panelvalue', 'lselect rselect u v insidev mousev scrollu scrollx wheel'),
            ('offtoon', True),
            ('ontooff', True),
            ('valuechange', True),
            ('whileon', True),
            ('active', True),
        ):
            try:
                getattr(panel_exec.par, pname).val = val
            except Exception:
                pass
    legacy = root.op('legacy_drop')
    _set_dat_text(legacy, scripts.get('legacy_drop'))
    ui = root.op('ui')
    bar = ui.op('scene_bar') if ui is not None else None
    if bar is not None and scripts.get('scene_dragdrop'):
        cb = bar.op('scene_dragdrop')
        if cb is None:
            try:
                cb = bar.create('textDAT', 'scene_dragdrop')
            except Exception:
                cb = None
        _set_dat_text(cb, scripts.get('scene_dragdrop'))
    stack = ui.op('grid_stack') if ui is not None else None
    grid = stack.op('grid') if stack is not None else None
    if grid is not None and scripts.get('cell_dragdrop'):
        _set_dat_text(_grid_dragdrop_dat(grid, td_op), scripts.get('cell_dragdrop'))
    if scripts.get('global_fx_dragdrop'):
        cb = root.op('global_fx_dragdrop')
        if cb is None:
            try:
                cb = root.create('textDAT', 'global_fx_dragdrop')
                cb.par.language = 'python'
            except Exception:
                cb = None
        _set_dat_text(cb, scripts.get('global_fx_dragdrop'))
    if scripts.get('cell_fx_dragdrop'):
        cb = root.op('cell_fx_dragdrop')
        if cb is None:
            try:
                cb = root.create('textDAT', 'cell_fx_dragdrop')
                cb.par.language = 'python'
            except Exception:
                cb = None
        _set_dat_text(cb, scripts.get('cell_fx_dragdrop'))
    if scripts.get('map_control_dragdrop'):
        cb = root.op('map_control_dragdrop')
        if cb is None:
            try:
                cb = root.create('textDAT', 'map_control_dragdrop')
                cb.par.language = 'python'
            except Exception:
                cb = None
        _set_dat_text(cb, scripts.get('map_control_dragdrop'))
    if scripts.get('map_control_parexec'):
        pe = root.op('map_control_parexec')
        if pe is None:
            try:
                pe = root.create('parameterexecuteDAT', 'map_control_parexec')
            except Exception:
                pe = None
        if pe is not None:
            _set_dat_text(pe, scripts.get('map_control_parexec'))
            try:
                pe.par.active = True
                pe.par.valuechange = True
                pe.par.modechange = True
                pe.par.expressionchange = True
            except Exception:
                pass
    auto = root.op('auto_repair')
    if auto is not None:
        _set_dat_text(auto, scripts.get('auto_repair'))
        try:
            auto.par.active = True
            auto.par.framestart = True
        except Exception:
            pass
    settings = _resolve_settings_op(td_op)
    if settings is not None:
        if scripts.get('settings_parexec'):
            sp = settings.op('settings_parexec') or settings.op('parexec')
            _set_dat_text(sp, scripts.get('settings_parexec'), language=None)
            if sp is not None:
                try:
                    sp.par.active = True
                    sp.par.valuechange = True
                except Exception:
                    pass
        for key, name in (
            ('pulse_frame_exec', 'pulse_frame_exec'),
            ('osc_callbacks', 'osc_callbacks'),
            ('midi_callbacks', 'midi_callbacks'),
            ('midi_table_exec', 'midi_table_exec'),
        ):
            text = scripts.get(key)
            if not text:
                continue
            dat = settings.op(name)
            if dat is None:
                try:
                    op_type = 'executeDAT' if name == 'pulse_frame_exec' else (
                        'datexecuteDAT' if name == 'midi_table_exec' else 'textDAT'
                    )
                    dat = settings.create(op_type, name)
                except Exception:
                    dat = None
            _set_dat_text(dat, text)
            if name == 'pulse_frame_exec' and dat is not None:
                try:
                    dat.par.active = True
                    dat.par.framestart = True
                    dat.par.frameend = False
                except Exception:
                    pass
        try:
            from performance_grid.builder.helpers_settings import _wire_settings_parexec
            _wire_settings_parexec(settings)
        except Exception:
            pass
    return True


def patch_dat_scripts_from_disk(comp_path=None, td_op=None):
    """Write assembled logic/panel_exec/etc. into performance_mode (no builder exec)."""
    td_op = _resolve_td_op(td_op)
    comp_path = discover_performance_mode_path(td_op, comp_path)
    root = td_op(comp_path)
    if root is None:
        print('patch_scripts: performance_mode not found at', comp_path)
        return False
    logic = root.op('logic')
    if logic is None:
        print('patch_scripts: no logic DAT under', comp_path)
        return False
    fx_state = {'cell': [], 'global': []}
    map_state = []
    try:
        old_module = logic.module
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
        print('patch_scripts: FX snapshot failed:', exc)
    try:
        import json
        if map_state:
            root.store('map_control_reload_json', json.dumps(map_state or []))
    except Exception:
        pass
    try:
        scripts = fresh_dat_scripts(td_op=td_op)
    except Exception as exc:
        print('patch_scripts: assemble failed:', exc)
        return False
    if not apply_dat_scripts_to_network(root, scripts, td_op=td_op):
        return False
    try:
        new_module = logic.module
        if fx_state['cell'] and hasattr(new_module, 'import_cell_fx_state'):
            new_module.import_cell_fx_state(fx_state['cell'])
        if fx_state['global'] and hasattr(new_module, 'import_global_fx_state'):
            new_module.import_global_fx_state(fx_state['global'])
        if hasattr(new_module, 'import_map_control_state'):
            rows = list(map_state or [])
            if not rows:
                try:
                    import json
                    raw = str(root.fetch('map_control_reload_json', '') or '').strip()
                    if raw:
                        rows = json.loads(raw)
                except Exception:
                    rows = []
            new_module.import_map_control_state(rows)
    except Exception as exc:
        print('patch_scripts: state restore failed:', exc)
    try:
        logic.module.onInit(full=False)
    except TypeError:
        try:
            logic.module.onInit()
        except Exception as exc:
            print('patch_scripts: onInit failed:', exc)
    except Exception as exc:
        print('patch_scripts: onInit failed:', exc)
    try:
        new_module = logic.module
        if hasattr(new_module, '_update_cell_params_ui'):
            new_module._update_cell_params_ui()
        if hasattr(new_module, '_refresh_global_fx_ui'):
            new_module._refresh_global_fx_ui()
        if hasattr(new_module, '_refresh_map_control_layout_only'):
            new_module._refresh_map_control_layout_only()
        elif hasattr(new_module, 'refresh_map_control_ui'):
            new_module.refresh_map_control_ui()
        if hasattr(new_module, 'repair_map_dial_binds'):
            new_module.repair_map_dial_binds()
    except Exception as exc:
        print('patch_scripts: UI refresh failed:', exc)
    try:
        new_module = logic.module
        if hasattr(new_module, 'configure_osc_input'):
            new_module.configure_osc_input()
    except Exception as exc:
        print('patch_scripts: configure_osc_input failed:', exc)
    try:
        new_module = logic.module
        if hasattr(new_module, 'configure_midi_input'):
            new_module.configure_midi_input()
    except Exception as exc:
        print('patch_scripts: configure_midi_input failed:', exc)
    scripts_dir = discover_scripts_dir(td_op=td_op)
    remember_scripts_dir(scripts_dir, td_op=td_op)
    print('patch_scripts OK:', comp_path)
    return True


def fresh_dat_scripts(td_op=None):
    """Read modular sources from disk (not cached LOGIC constants)."""
    scripts_dir = discover_scripts_dir(td_op=td_op)
    _ensure_scripts_on_path(scripts_dir)
    invalidate_performance_grid_modules()
    from performance_grid.assemble import (
        assemble_logic,
        assemble_settings_parexec,
        read_embedded,
    )
    from performance_grid.constants_builder import DEFAULT_SET_NAME, SETS_SUBDIR

    return {
        'logic': assemble_logic(),
        'panel_exec': read_embedded('panel_exec.py'),
        'legacy_drop': read_embedded('legacy_drop.py'),
        'cell_dragdrop': read_embedded('cell_dragdrop.py'),
        'global_fx_dragdrop': read_embedded('global_fx_dragdrop.py'),
        'cell_fx_dragdrop': read_embedded('cell_fx_dragdrop.py'),
        'map_control_dragdrop': read_embedded('map_control_dragdrop.py'),
        'map_control_parexec': read_embedded('map_control_parexec.py'),
        'scene_dragdrop': read_embedded('scene_dragdrop.py'),
        'auto_repair': read_embedded('auto_repair.py'),
        'pulse_frame_exec': read_embedded('pulse_frame_exec.py'),
        'osc_callbacks': read_embedded('osc_callbacks.py'),
        'midi_callbacks': read_embedded('midi_callbacks.py'),
        'midi_table_exec': read_embedded('midi_table_exec.py'),
        'settings_parexec': assemble_settings_parexec(
            default_set_name=DEFAULT_SET_NAME,
            sets_subdir=SETS_SUBDIR,
        ),
    }
