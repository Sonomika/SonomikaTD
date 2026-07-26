# Run in TouchDesigner Textport only (Alt+T). Prompt is >>> not python >>>.
#
#   exec(open(r'...\SonomikaTD\scripts\reload_performance.py', encoding='utf-8').read())
#   restore_settings_buttons()

import os
import sys

_THIS = None
try:
    _THIS = os.path.dirname(os.path.abspath(__file__))
except NameError:
    pass

if _THIS and _THIS not in sys.path:
    sys.path.insert(0, _THIS)

# TouchDesigner keeps old performance_grid modules in sys.modules — clear before import.
for _key in list(sys.modules.keys()):
    if _key == 'performance_grid' or _key.startswith('performance_grid.'):
        del sys.modules[_key]

from performance_grid.td_runtime import (
    _resolve_td_op,
    discover_performance_mode_path,
    discover_scripts_dir,
    exec_builder_script,
    inject_td_op_into_performance_grid,
    invalidate_performance_grid_modules,
    patch_dat_scripts_from_disk,
)
from performance_grid.paths import script_entry_paths

if not _THIS:
    try:
        _THIS = discover_scripts_dir(td_op=_resolve_td_op())
    except RuntimeError:
        _THIS = discover_scripts_dir()
    if _THIS and _THIS not in sys.path:
        sys.path.insert(0, _THIS)


def _logic_module_ok(td_op, comp_path):
    try:
        root = td_op(comp_path)
        logic = root.op('logic') if root is not None else None
        if logic is None:
            return False
        return hasattr(logic, 'module') and logic.module is not None
    except Exception:
        return False


def reload_now(comp_path=None, td_op=None):
    td_op = _resolve_td_op(td_op)
    invalidate_performance_grid_modules()
    inject_td_op_into_performance_grid(td_op=td_op)
    comp_path = discover_performance_mode_path(td_op, comp_path)
    if not _logic_module_ok(td_op, comp_path):
        print('Reload: logic DAT has errors — patching scripts from disk...')
        if patch_dat_scripts_from_disk(comp_path=comp_path, td_op=td_op):
            print('reload_now OK: patched scripts from disk')
            return 'patched'
    pf = None
    try:
        root = td_op(comp_path)
        if root is not None:
            pf = root.project.folder
    except Exception:
        pass
    ordered = script_entry_paths(pf)
    if not ordered:
        print('reload_now: build_simple_grid.py not found on disk')
        if patch_dat_scripts_from_disk(comp_path=comp_path, td_op=td_op):
            print('reload_now OK: patched scripts from disk')
            return 'patched'
        return None
    from performance_grid.builder.api import _apply_reload_from_builder_ns

    last_exc = None
    for path in ordered:
        try:
            ns = exec_builder_script(path, td_op=td_op)
            result = _apply_reload_from_builder_ns(ns, comp_path, path)
            if result:
                pm = td_op(discover_performance_mode_path(td_op, comp_path))
                ui = pm.op('ui') if pm is not None else None
                perform = td_op('/perform')
                if ui is not None and perform is not None:
                    try:
                        perform.par.winop = ui.path
                        perform.par.interact = True
                        perform.par.drawwindow = True
                    except Exception:
                        pass
                print('reload_now OK:', result)
                return result
        except Exception as exc:
            last_exc = exc
            import traceback
            print('reload_now failed:', path, exc)
            traceback.print_exc()
    print('Reload: builder failed — patching scripts from disk...')
    if patch_dat_scripts_from_disk(comp_path=comp_path, td_op=td_op):
        print('reload_now OK: patched scripts from disk')
        return 'patched'
    if last_exc:
        print('reload_now: all paths failed — see traceback above')
    else:
        print('reload_now: no builder found')
    return None


def patch_scripts_only(comp_path=None, td_op=None):
    """Fix script errors without running build_simple_grid (updates logic DAT from disk)."""
    td_op = _resolve_td_op(td_op)
    invalidate_performance_grid_modules()
    inject_td_op_into_performance_grid(td_op=td_op)
    return patch_dat_scripts_from_disk(comp_path=comp_path, td_op=td_op)


def _refresh_settings_panel(td_op, settings):
    pm = td_op('/project1/performance_mode')
    if pm is None:
        return
    logic = pm.op('logic')
    ui = pm.op('ui')
    panel = ui.op('settings_params') if ui is not None else None
    if logic is None or not hasattr(logic, 'module'):
        return
    mod = logic.module
    if panel is not None and hasattr(mod, '_configure_settings_params_panel'):
        mod._configure_settings_params_panel(panel)
    if panel is not None and hasattr(mod, '_settings_panel_w'):
        try:
            panel.par.w = mod._settings_panel_w()
        except Exception:
            pass
    if hasattr(mod, '_wire_settings_parexec'):
        try:
            from performance_grid.builder.helpers_settings import _wire_settings_parexec
            _wire_settings_parexec(settings)
        except Exception:
            pass
    if hasattr(mod, '_layout_perform_ui'):
        try:
            mod._layout_perform_ui()
        except Exception:
            pass


def restore_sets_buttons():
    """Recreate Sets tab: Save File, Open File, New Set, Save, Open (TouchDesigner Textport only)."""
    td_op = _resolve_td_op()
    invalidate_performance_grid_modules()
    inject_td_op_into_performance_grid(td_op=td_op)
    from performance_grid.builder.helpers_settings import (
        _build_settings,
        _ensure_sets_page_controls,
        _wire_settings_parexec,
    )

    settings = td_op('/settings')
    if settings is None:
        pm = td_op('/project1/performance_mode')
        _build_settings(pm)
        settings = td_op('/settings')
    if settings is None:
        print('restore_sets_buttons: /settings not found')
        return False
    _ensure_sets_page_controls(settings)
    _wire_settings_parexec(settings)
    _refresh_settings_panel(td_op, settings)
    print('Sets buttons restored on', settings.path)
    print('Sets tab: Save File, Open File, New Set, Save, Open (gray buttons may say Pulse)')
    return True


def restore_maintenance_button():
    """Recreate Maintenance → Reload Scripts on /settings (TouchDesigner Textport only)."""
    td_op = _resolve_td_op()
    invalidate_performance_grid_modules()
    inject_td_op_into_performance_grid(td_op=td_op)
    from performance_grid.builder.helpers_ui import _ensure_reload_scripts_maintenance
    from performance_grid.builder.helpers_settings import _build_settings, _wire_settings_parexec

    settings = td_op('/settings')
    if settings is None:
        pm = td_op('/project1/performance_mode')
        _build_settings(pm)
        settings = td_op('/settings')
    if settings is None:
        print('restore_maintenance_button: /settings not found')
        return False
    _ensure_reload_scripts_maintenance(settings)
    _wire_settings_parexec(settings)
    _refresh_settings_panel(td_op, settings)
    print('Maintenance button restored on', settings.path)
    print('Open Perform → Settings panel → Maintenance tab (gray button may say Pulse)')
    return True


def restore_audio_devices():
    """Rebuild Audio input-device dropdown on /settings (TouchDesigner Textport only)."""
    td_op = _resolve_td_op()
    invalidate_performance_grid_modules()
    inject_td_op_into_performance_grid(td_op=td_op)
    patch_scripts_only(td_op=td_op)
    pm = td_op('/project1/performance_mode')
    logic = pm.op('logic') if pm is not None else None
    if logic is None or not hasattr(logic, 'module'):
        print('restore_audio_devices: performance_mode logic not found')
        return False
    mod = logic.module
    if not hasattr(mod, 'configure_audio_analysis'):
        print('restore_audio_devices: configure_audio_analysis missing')
        return False
    mod.configure_audio_analysis()
    if hasattr(mod, '_apply_audio_device'):
        mod._apply_audio_device()
    settings = td_op('/settings')
    try:
        from performance_grid.builder.helpers_settings import _wire_settings_parexec
        _wire_settings_parexec(settings)
    except Exception:
        pass
    _refresh_settings_panel(td_op, settings)
    print('Audio tab rebuilt — Settings → Audio: Input Device dropdown')
    return True


def restore_midi_menus():
    """Rebuild Midi device/template dropdowns on /settings (TouchDesigner Textport only)."""
    td_op = _resolve_td_op()
    invalidate_performance_grid_modules()
    inject_td_op_into_performance_grid(td_op=td_op)
    patch_scripts_only(td_op=td_op)
    pm = td_op('/project1/performance_mode')
    logic = pm.op('logic') if pm is not None else None
    if logic is None or not hasattr(logic, 'module'):
        print('restore_midi_menus: performance_mode logic not found')
        return False
    mod = logic.module
    if hasattr(mod, '_ensure_midi_tab_pars'):
        mod._ensure_midi_tab_pars()
    if not hasattr(mod, 'configure_midi_input'):
        print('restore_midi_menus: configure_midi_input missing')
        return False
    mod.configure_midi_input()
    settings = td_op('/settings')
    try:
        from performance_grid.builder.helpers_settings import _wire_settings_parexec
        _wire_settings_parexec(settings)
    except Exception:
        pass
    _refresh_settings_panel(td_op, settings)
    print('Midi tab rebuilt — Settings → Midi: MIDI Device and Template dropdowns')
    return True


def remove_spout_output():
    """Remove legacy Settings → Output Spout controls and old senders."""
    td_op = _resolve_td_op()
    invalidate_performance_grid_modules()
    inject_td_op_into_performance_grid(td_op=td_op)
    patch_scripts_only(td_op=td_op)
    from performance_grid.builder.helpers_settings import _remove_legacy_spout_output

    settings = td_op('/settings')
    _remove_legacy_spout_output(settings)
    _refresh_settings_panel(td_op, settings)
    print('Legacy Spout settings removed — /SonomikaTD is left untouched')
    return True


def configure_out1_spout():
    """Feed /out1 into /SonomikaTD Spout sender (TouchDesigner Textport only)."""
    td_op = _resolve_td_op()
    invalidate_performance_grid_modules()
    inject_td_op_into_performance_grid(td_op=td_op)
    patch_scripts_only(td_op=td_op)
    from performance_grid.builder.helpers_settings import _ensure_out1_spout_output

    sender = _ensure_out1_spout_output()
    if sender is None:
        print('configure_out1_spout: could not create /SonomikaTD sender')
        return False
    print('Spout configured: /out1 -> /SonomikaTD')
    return True


def configure_perform_spout():
    """Compatibility alias: current Spout sender uses /out1."""
    return configure_out1_spout()


def restore_settings_buttons():
    """Restore Sets + Maintenance + Midi/Audio menus on /settings."""
    ok_sets = restore_sets_buttons()
    ok_maint = restore_maintenance_button()
    ok_midi = restore_midi_menus()
    ok_audio = restore_audio_devices()
    try:
        from performance_grid.builder.helpers_settings import _ensure_out1_spout_output
        _ensure_out1_spout_output()
    except Exception:
        pass
    return ok_sets and ok_maint and ok_midi and ok_audio


try:
    reload_now()
except RuntimeError as exc:
    print(exc)
