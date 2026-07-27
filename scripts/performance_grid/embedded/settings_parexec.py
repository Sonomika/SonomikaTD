SETTINGS_PAREXEC = r'''def _td_ns():
    ns = {'op': op}
    for n in ('me', 'parent', 'ParMode'):
        try:
            ns[n] = eval(n)
        except Exception:
            pass
    return ns

def _settings():
    for path in ('/settings',):
        try:
            s = op(path)
            if s is not None:
                return s
        except Exception:
            pass
    return None

_SONOMIKA_SCRIPTS_STORE_KEY = 'sonomika_scripts_dir'
_OSC_SYNCING = False

def _is_scripts_dir(path):
    import os
    if not path:
        return False
    return os.path.isdir(os.path.join(os.path.normpath(str(path)), 'performance_grid'))

def _walk_up_scripts_dir(start_dir, max_levels=8):
    import os
    d = os.path.normpath(str(start_dir or ''))
    if not d or not os.path.isdir(d):
        return None
    for _ in range(max_levels):
        scripts = os.path.join(d, 'scripts')
        if _is_scripts_dir(scripts):
            return os.path.normpath(scripts).replace('\\', '/')
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None

def _remember_scripts_dir(scripts_dir):
    if not _is_scripts_dir(scripts_dir):
        return
    import os
    try:
        op('/').store(
            _SONOMIKA_SCRIPTS_STORE_KEY,
            os.path.normpath(str(scripts_dir)).replace('\\', '/'),
        )
    except Exception:
        pass

def _discover_scripts_dir():
    import os
    try:
        stored = str(op('/').fetch(_SONOMIKA_SCRIPTS_STORE_KEY, '') or '').strip()
        if _is_scripts_dir(stored):
            return os.path.normpath(stored).replace('\\', '/')
    except Exception:
        pass
    candidates = []
    env = os.environ.get('SONOMIKA_TD_ROOT', '').strip()
    if env:
        candidates.append(os.path.join(env, 'scripts'))
    try:
        proj = op('/').project
        pf = str(proj.folder or '').strip()
        if pf:
            candidates.extend([
                os.path.join(pf, 'scripts'),
                os.path.join(pf, 'SonomikaTD', 'scripts'),
                _walk_up_scripts_dir(pf),
            ])
        toe = str(getattr(proj, 'file', '') or getattr(proj, 'savePath', '') or '').strip()
        if toe:
            toe_dir = os.path.dirname(toe)
            candidates.extend([
                os.path.join(toe_dir, 'scripts'),
                os.path.join(toe_dir, 'SonomikaTD', 'scripts'),
                os.path.join(os.path.dirname(toe_dir), 'SonomikaTD', 'scripts'),
                _walk_up_scripts_dir(toe_dir),
            ])
    except Exception:
        pass
    seen = set()
    for scripts_dir in candidates:
        if not scripts_dir:
            continue
        scripts_dir = os.path.normpath(scripts_dir).replace('\\', '/')
        if scripts_dir in seen:
            continue
        seen.add(scripts_dir)
        if _is_scripts_dir(scripts_dir):
            _remember_scripts_dir(scripts_dir)
            return scripts_dir
    return None


def _reload_paths():
    import os
    paths = []
    scripts_dir = _discover_scripts_dir()
    if scripts_dir:
        paths.append(os.path.join(scripts_dir, 'build_simple_grid.py'))
    env = os.environ.get('SONOMIKA_TD_ROOT', '').strip()
    if env:
        paths.append(os.path.join(env, 'scripts', 'build_simple_grid.py'))
    try:
        pf = op('/').project.folder.replace('\\', '/')
        paths.append(os.path.join(pf, 'SonomikaTD', 'scripts', 'build_simple_grid.py'))
        paths.append(os.path.join(pf, 'scripts', 'build_simple_grid.py'))
    except Exception:
        pass
    seen = set()
    out = []
    for p in paths:
        p = os.path.normpath(p).replace('\\', '/')
        if p in seen or not os.path.isfile(p):
            continue
        seen.add(p)
        out.append(p)
    return out

def _purge_performance_grid():
    import sys
    for key in list(sys.modules.keys()):
        if key == 'performance_grid' or key.startswith('performance_grid.'):
            del sys.modules[key]

def _ensure_scripts_path(scripts_dir):
    import os
    import sys
    if scripts_dir and os.path.isdir(scripts_dir):
        scripts_dir = os.path.normpath(scripts_dir)
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        return scripts_dir
    return None

def _discover_scripts_dir_from_builder(builder_path):
    import os
    builder_path = os.path.normpath(builder_path)
    scripts_dir = os.path.dirname(builder_path)
    if os.path.isdir(os.path.join(scripts_dir, 'performance_grid')):
        return scripts_dir
    alt = os.path.normpath(os.path.join(scripts_dir, '..', 'SonomikaTD', 'scripts'))
    if os.path.isdir(os.path.join(alt, 'performance_grid')):
        return alt
    return scripts_dir

def _exec_builder(path):
    import os
    path = os.path.normpath(path)
    _ensure_scripts_path(_discover_scripts_dir_from_builder(path))
    _purge_performance_grid()
    ns = _td_ns()
    ns['__file__'] = path
    ns['__name__'] = '__main__'
    with open(path, encoding='utf-8') as fh:
        code = fh.read()
    exec(compile(code, path, 'exec'), ns)
    return ns

def _patch_dat_scripts_from_disk(comp='/project1/performance_mode'):
    """Patch logic/settings DATs from disk — works when in-network logic is broken."""
    import os
    import sys
    scripts_dir = _discover_scripts_dir()
    if not scripts_dir:
        try:
            pf = op('/').project.folder
        except Exception:
            pf = '(unknown)'
        print('Reload patch: scripts/performance_grid not found on disk')
        print('  project.folder =', pf)
        print('  Set SONOMIKA_TD_ROOT to your SonomikaTD folder, or save the .toe next to scripts/')
        return False
    scripts_dir = os.path.normpath(scripts_dir)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    _purge_performance_grid()
    try:
        from performance_grid.td_runtime import patch_dat_scripts_from_disk
        ok = bool(patch_dat_scripts_from_disk(comp_path=comp, td_op=op))
        if ok:
            _remember_scripts_dir(scripts_dir)
        return ok
    except Exception as exc:
        import traceback
        print('Reload patch failed:', exc)
        traceback.print_exc()
        return False


def _reload_from_disk():
    comp = '/project1/performance_mode'
    import os
    if _patch_dat_scripts_from_disk(comp):
        print('Reload OK (patch_dat_scripts_from_disk)')
        return True
    for builder_path in _reload_paths():
        reload_path = os.path.join(os.path.dirname(builder_path), 'reload_performance.py')
        reload_path = os.path.normpath(reload_path).replace('\\', '/')
        if not os.path.isfile(reload_path):
            continue
        try:
            ns = _td_ns()
            ns['__file__'] = reload_path
            with open(reload_path, encoding='utf-8') as fh:
                code = fh.read()
            exec(compile(code, reload_path, 'exec'), ns)
            print('Reload OK:', reload_path)
            _post_reload_heal()
            return True
        except Exception as exc:
            import traceback
            print('Reload script failed:', reload_path, exc)
            traceback.print_exc()
    pm = op(comp)
    if pm is not None:
        logic = pm.op('logic')
        if logic is not None and hasattr(logic, 'module'):
            mod = logic.module
            if hasattr(mod, '_package_root') and hasattr(mod, 'reload_scripts'):
                try:
                    if mod.reload_scripts(comp):
                        print('Reload OK (logic.reload_scripts)')
                        _post_reload_heal()
                        return True
                except Exception as exc:
                    print('Reload via logic failed:', exc)
            elif hasattr(mod, 'reload_scripts'):
                print('Reload: skipping stale logic.reload_scripts (patch from disk first)')
    for path in _reload_paths():
        try:
            ns = _exec_builder(path)
            fn = ns.get('reload_performance_scripts')
            if fn is None:
                continue
            result = fn(comp)
            if result:
                print('Reload OK:', path)
                _post_reload_heal()
                return True
            print('Reload: patch returned false for', path)
        except Exception as exc:
            import traceback
            print('Reload failed:', path, exc)
            traceback.print_exc()
    print('Reload: no builder script worked — run build_simple_grid from Textport')
    return False

def _pm_logic():
    pm = op('/project1/performance_mode')
    return pm.op('logic').module if pm else None


def _post_reload_heal():
    logic = _pm_logic()
    if logic is None:
        return
    if hasattr(logic, 'post_reload_heal'):
        try:
            logic.post_reload_heal()
            return
        except Exception as exc:
            print('post_reload_heal:', exc)
    if hasattr(logic, '_ensure_midi_tab_pars'):
        try:
            logic._ensure_midi_tab_pars()
        except Exception:
            pass
    if hasattr(logic, 'configure_midi_input'):
        try:
            logic.configure_midi_input()
        except Exception:
            pass
    if hasattr(logic, 'configure_pulse_engine'):
        try:
            logic.configure_pulse_engine()
        except Exception:
            pass
    if hasattr(logic, 'heal_fade_tab'):
        try:
            logic.heal_fade_tab()
        except Exception:
            pass
    if hasattr(logic, 'configure_audio_analysis'):
        try:
            logic.configure_audio_analysis()
        except Exception:
            pass
    if hasattr(logic, '_apply_audio_device'):
        try:
            logic._apply_audio_device()
        except Exception:
            pass
    try:
        s = _settings()
        if s is not None:
            from performance_grid.builder.helpers_ui import _ensure_reload_scripts_maintenance
            _ensure_reload_scripts_maintenance(s)
    except Exception:
        pass
    pm = op('/project1/performance_mode')
    ui = pm.op('ui') if pm is not None else None
    panel = ui.op('settings_params') if ui is not None else None
    if panel is not None and hasattr(logic, '_configure_settings_params_panel'):
        try:
            logic._configure_settings_params_panel(panel)
        except Exception:
            pass


def _purge_performance_grid_modules():
    import sys
    for key in list(sys.modules.keys()):
        if key == 'performance_grid' or key.startswith('performance_grid.'):
            del sys.modules[key]


def _sync_osc_ip(source_name):
    global _OSC_SYNCING
    if _OSC_SYNCING:
        return
    s = _settings()
    if s is None:
        return
    try:
        ip = str(getattr(s.par, source_name).eval()).strip()
    except Exception:
        return
    _OSC_SYNCING = True
    try:
        for name in ('Oscip', 'Gridoscip'):
            if name == source_name:
                continue
            try:
                target = getattr(s.par, name)
                if str(target.eval()).strip() != ip:
                    target.val = ip
            except Exception:
                pass
    finally:
        _OSC_SYNCING = False


def _sync_osc_port(source_name):
    global _OSC_SYNCING
    if _OSC_SYNCING:
        return
    s = _settings()
    if s is None:
        return
    try:
        port = max(1, min(65535, int(float(getattr(s.par, source_name).eval()))))
    except Exception:
        return
    _OSC_SYNCING = True
    try:
        for name in ('Oscport', 'Gridoscport'):
            if name == source_name:
                continue
            try:
                target = getattr(s.par, name)
                current = max(1, min(65535, int(float(target.eval()))))
                if current != port:
                    target.val = port
            except Exception:
                pass
    finally:
        _OSC_SYNCING = False


def onValueChange(par, prev):
    logic = _pm_logic()
    if logic is None:
        return
    if par.name in ('Canvaspreset', 'Canvaswidth', 'Canvasheight', 'Canvasbg', 'Canvasbgr', 'Canvasbgg', 'Canvasbgb'):
        if hasattr(logic, '_apply_canvas_settings_change'):
            logic._apply_canvas_settings_change(str(par.name), par)
        elif par.name == 'Canvaspreset':
            logic.apply_canvas_preset(str(par.eval()))
        else:
            logic.apply_canvas_size()
    elif par.name == 'Allrenderscale':
        if hasattr(logic, 'apply_all_cell_render_scale'):
            logic.apply_all_cell_render_scale(str(par.eval()))
    elif par.name == 'Fxrowrenderscale':
        if hasattr(logic, 'apply_fx_row_render_scale'):
            logic.apply_fx_row_render_scale(str(par.eval()))
    elif par.name == 'Toxcookmode':
        if hasattr(logic, '_sync_layer_slot_pause_states'):
            logic._sync_layer_slot_pause_states(force_full=True)
    elif par.name in ('Oscip', 'Gridoscip'):
        _sync_osc_ip(str(par.name))
        if hasattr(logic, 'configure_osc_input'):
            logic.configure_osc_input()
        if hasattr(logic, 'refresh_pulse_osc_out'):
            logic.refresh_pulse_osc_out()
    elif par.name in ('Oscport', 'Gridoscport'):
        _sync_osc_port(str(par.name))
        if hasattr(logic, 'configure_osc_input'):
            logic.configure_osc_input()
        if hasattr(logic, 'refresh_pulse_osc_out'):
            logic.refresh_pulse_osc_out()
    elif par.name in (
        'Oscactive', 'Oscport', 'Oscip',
        'Gridoscactive', 'Gridoscport', 'Gridoscip', 'Gridoscprefix',
    ):
        if hasattr(logic, 'configure_osc_input'):
            logic.configure_osc_input()
    elif par.name == 'Mididevice':
        if hasattr(logic, '_midi_menu_refresh_active') and logic._midi_menu_refresh_active():
            return
        if hasattr(logic, 'configure_midi_input'):
            logic.configure_midi_input()
    elif par.name == 'Miditemplate':
        if hasattr(logic, '_midi_menu_refresh_active') and logic._midi_menu_refresh_active():
            return
        if hasattr(logic, 'apply_midi_template'):
            logic.apply_midi_template()
    elif par.name == 'Miditakeovermode':
        if hasattr(logic, '_midi_menu_refresh_active') and logic._midi_menu_refresh_active():
            return
        if hasattr(logic, 'clear_midi_takeover_sync'):
            logic.clear_midi_takeover_sync()
    elif str(par.name).startswith('Pulse'):
        if hasattr(logic, '_apply_pulse_settings_change'):
            logic._apply_pulse_settings_change(str(par.name))
        elif par.name == 'Pulseactive':
            if hasattr(logic, '_reset_pulse_sync'):
                logic._reset_pulse_sync()
            if bool(par.eval()) and hasattr(logic, '_ensure_pulse_master_slot'):
                logic._ensure_pulse_master_slot()
            if hasattr(logic, 'update_pulse_engine'):
                logic.update_pulse_engine()
        elif hasattr(logic, '_reset_pulse_sync'):
            logic._reset_pulse_sync()
            if hasattr(logic, 'update_pulse_engine'):
                logic.update_pulse_engine()
    elif par.name == 'Audioactive':
        if hasattr(logic, 'on_audio_active_changed'):
            logic.on_audio_active_changed()
        elif hasattr(logic, '_sync_audio_active'):
            logic._sync_audio_active()
            if hasattr(logic, '_sync_audio_spectrum_for_settings_tab'):
                logic._sync_audio_spectrum_for_settings_tab(force=True)
    elif par.name == 'Audiodeviceindex':
        if hasattr(logic, '_apply_audio_device'):
            logic._apply_audio_device()
    elif par.name in (
        'Audiothresholdlow', 'Audiothresholdhigh', 'Audiothresholdpeak',
    ):
        # Histogram drag writes these every pixel — skip heavy rebuilds mid-drag.
        dragging = False
        try:
            dragging = bool(logic._AUDIO_HIST_DRAG.get('writing_thresh')) or (
                hasattr(logic, '_audio_threshold_drag_active')
                and logic._audio_threshold_drag_active()
            )
        except Exception:
            dragging = False
        if not dragging:
            if hasattr(logic, '_sync_audio_hz_display_pars'):
                logic._sync_audio_hz_display_pars()
            if hasattr(logic, '_update_audio_readouts'):
                logic._update_audio_readouts()
    elif par.name in (
        'Audioreverselow', 'Audioreversehigh', 'Audioreversepeak',
    ):
        # Out expressions already depend on these toggles — only refresh meter UI.
        if hasattr(logic, '_sync_audio_trigger_reverse_ui'):
            logic._sync_audio_trigger_reverse_ui()

def onPulse(par):
    if par is None or par.name is None:
        return
    name = str(par.name)
    if name == 'Reloadscripts':
        _reload_from_disk()
        logic = _pm_logic()
        if logic is not None:
            try:
                if hasattr(logic, 'restore_map_dial_binds_after_reload'):
                    logic.restore_map_dial_binds_after_reload()
                elif hasattr(logic, 'repair_map_dial_binds'):
                    logic.repair_map_dial_binds()
                if hasattr(logic, 'sync_map_control_context'):
                    logic.sync_map_control_context()
                for idx in range(1, 9):
                    if hasattr(logic, '_paint_map_dial'):
                        logic._paint_map_dial(idx)
            except Exception:
                pass
            try:
                logic.repair_cell_labels()
                logic._refresh_ui()
            except Exception:
                pass
        return
    logic = _pm_logic()
    if logic is None:
        return
    if name == 'Takescreenshot':
        if hasattr(logic, 'take_program_screenshot'):
            logic.take_program_screenshot()
    elif name == 'Togglerecording':
        if hasattr(logic, 'toggle_screen_recording'):
            logic.toggle_screen_recording()
    elif name == 'Savecanvassize':
        if hasattr(logic, 'save_canvas_size'):
            logic.save_canvas_size()
    elif name == 'Saveset':
        if hasattr(logic, 'save_performance_set'):
            s = _settings()
            logic.save_performance_set(path=str(s.par.Savefile.eval()).strip())
    elif name == 'Openset':
        if hasattr(logic, 'load_performance_set'):
            s = _settings()
            logic.load_performance_set(str(s.par.Openfile.eval()).strip())
    elif name == 'Newset':
        if hasattr(logic, 'new_performance_set'):
            logic.new_performance_set()
        if hasattr(logic, '_refresh_settings_params_panel'):
            logic._refresh_settings_params_panel()
    elif name == 'Midirefreshtemplates':
        if hasattr(logic, '_pin_settings_tab'):
            logic._pin_settings_tab('Midi')
        if hasattr(logic, 'refresh_midi_template_list'):
            logic.refresh_midi_template_list()
    elif name == 'Audiorefresh':
        if hasattr(logic, '_pin_settings_tab'):
            logic._pin_settings_tab('Audio')
        if hasattr(logic, 'refresh_audio_input'):
            logic.refresh_audio_input()
'''
