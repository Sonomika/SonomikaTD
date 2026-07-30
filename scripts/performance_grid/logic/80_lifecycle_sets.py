def _script_reload_paths():
    """Canonical builder first; SonomikaTD package copy last (may be stale)."""
    paths = []
    scripts_dir = _discover_scripts_dir()
    if scripts_dir:
        paths.append(os.path.join(scripts_dir, 'build_simple_grid.py'))
    env = os.environ.get('SONOMIKA_TD_ROOT', '').strip()
    if env:
        paths.append(os.path.join(env, 'scripts', 'build_simple_grid.py'))
    r = _root()
    if r is not None:
        try:
            pf = r.project.folder
            paths.append(os.path.join(pf, 'scripts', 'build_simple_grid.py'))
            paths.append(os.path.join(pf, 'SonomikaTD', 'scripts', 'build_simple_grid.py'))
        except Exception:
            pass
    pkg = _package_root()
    if pkg:
        paths.append(os.path.join(pkg, 'scripts', 'build_simple_grid.py'))
        paths.append(os.path.join(pkg, 'SonomikaTD', 'scripts', 'build_simple_grid.py'))
    seen = set()
    out = []
    for p in paths:
        p = os.path.normpath(p).replace('\\', '/')
        if p in seen or not os.path.isfile(p):
            continue
        seen.add(p)
        out.append(p)
    return out


def _effects_folder():
    candidates = []
    try:
        pf = project.folder
        candidates.append(os.path.join(pf, 'tox'))
        candidates.append(os.path.join(pf, 'SonomikaTD', 'tox'))
    except Exception:
        pass
    pkg = _package_root()
    if pkg:
        candidates.append(os.path.join(pkg, 'tox'))
    for folder in candidates:
        try:
            folder = os.path.normpath(folder)
            if os.path.isdir(folder):
                return folder.replace('\\', '/')
        except Exception:
            pass
    folder = os.path.normpath(candidates[0] if candidates else os.path.join('tox'))
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        pass
    return folder.replace('\\', '/')


def open_effects_folder():
    folder = _effects_folder()
    try:
        ui.viewFile(folder)
        return True
    except Exception:
        pass
    try:
        import os as _os
        if hasattr(_os, 'startfile'):
            _os.startfile(folder.replace('/', '\\'))
            return True
    except Exception:
        pass
    try:
        import subprocess
        import sys
        opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
        subprocess.Popen([opener, folder])
        return True
    except Exception as exc:
        print('Open effects folder failed:', folder, exc)
        return False


def _td_exec_ns():
    ns = {'op': op}
    try:
        ns['me'] = me
        ns['parent'] = parent
        ns['ParMode'] = ParMode
    except Exception:
        pass
    return ns


def _purge_performance_grid_modules():
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


def _exec_builder_script(path):
    import os
    path = os.path.normpath(path)
    scripts_dir = _ensure_scripts_path(_discover_scripts_dir_from_builder(path))
    try:
        from performance_grid.td_runtime import exec_builder_script
        return exec_builder_script(path, td_op=op)
    except Exception:
        _ensure_scripts_path(scripts_dir)
        _purge_performance_grid_modules()
        ns = _td_exec_ns()
        ns['__file__'] = path
        ns['__name__'] = '__main__'
        with open(path, encoding='utf-8') as fh:
            code = fh.read()
        exec(compile(code, path, 'exec'), ns)
        return ns


def reload_scripts(comp_path=None):
    """Reload build_simple_grid.py from disk (safe patch; rebuild only if broken)."""
    comp_path = comp_path or (_root().path if _root() is not None else '/project1/performance_mode')
    for path in _script_reload_paths():
        try:
            ns = _exec_builder_script(path)
            reload_fn = ns.get('reload_performance_scripts')
            if reload_fn is not None and reload_fn(comp_path):
                return True
        except Exception as exc:
            import traceback
            print('Reload failed:', path, exc)
            traceback.print_exc()
    print('reload_scripts: build_simple_grid.py not found')
    return False


def normalize_asset_paths():
    """Migrate clip_matrix and FX paths to project.folder-relative form."""
    changed = False
    tbl = _table()
    if tbl is not None:
        for i in range(1, tbl.numRows):
            path = str(tbl[i, 'path']).strip()
            if not path:
                continue
            stored = _store_asset_path(path)
            if stored and stored != path:
                tbl[i, 'path'] = stored
                changed = True
    for fx_list in _CELL_FX.values():
        for entry in fx_list:
            path = str(entry.get('path', '') or '').strip()
            if not path:
                continue
            stored = _store_asset_path(path)
            if stored and stored != path:
                entry['path'] = stored
                changed = True
    for effects in _GLOBAL_FX_BY_SCENE.values():
        for entry in effects:
            path = str(entry.get('path', '') or '').strip()
            if not path:
                continue
            stored = _store_asset_path(path)
            if stored and stored != path:
                entry['path'] = stored
                changed = True
    for entry in _GLOBAL_FX:
        path = str(entry.get('path', '') or '').strip()
        if not path:
            continue
        stored = _store_asset_path(path)
        if stored and stored != path:
            entry['path'] = stored
            changed = True
    return changed


def normalize_set_file_paths():
    """Migrate Savefile/Openfile to paths relative to project.folder."""
    s = _settings()
    if s is None:
        return False
    changed = False
    for pname in ('Savefile', 'Openfile'):
        try:
            raw = str(getattr(s.par, pname).eval()).strip()
            rel = _rel_set_path(raw)
            if rel and rel != raw:
                getattr(s.par, pname).val = rel
                changed = True
        except Exception:
            pass
    return changed


def _ensure_rec_normalization_settings():
    """Migrate Rec normalization controls in-place during script-button reload."""
    settings = _settings()
    if settings is None:
        return False
    rec_page = None
    try:
        rec_page = next(
            page for page in settings.customPages if page.name == 'Rec')
    except Exception:
        pass
    if rec_page is None:
        try:
            rec_page = settings.appendCustomPage('Rec')
        except Exception:
            return False
    try:
        normalize_audio = settings.par.Normalizerecordingaudio
    except AttributeError:
        normalize_audio = rec_page.appendToggle(
            'Normalizerecordingaudio',
            label='Normalize Audio After Recording',
        )
        normalize_audio.default = False
        normalize_audio.val = False
    try:
        normalize_audio.label = 'Normalize Audio After Recording'
        normalize_audio.order = 5
    except Exception:
        pass
    try:
        loudness = settings.par.Recordingloudness
    except AttributeError:
        loudness = rec_page.appendMenu(
            'Recordingloudness',
            label='Normalization Loudness',
        )
        loudness.default = 'safe'
        loudness.val = 'safe'
    try:
        loudness.label = 'Normalization Loudness'
        loudness.menuNames = ['safe', 'loud']
        loudness.menuLabels = ['Safe (-14 LUFS)', 'Loud (-10 LUFS)']
        loudness.order = 6
    except Exception:
        pass
    try:
        settings.par.Togglerecording.order = 7
        settings.par.Recordingstatus.order = 8
    except Exception:
        pass
    return True


def post_reload_heal():
    """Run after script reload: repair tabs, re-wire inputs, refresh settings UI."""
    heal_fade_tab()
    heal_perf_tab()
    heal_canvas_tab()
    try:
        from performance_grid.builder.helpers_settings import heal_reload_scripts_button
        heal_reload_scripts_button()
    except Exception:
        pass
    _ensure_rec_normalization_settings()
    try:
        clear_embedded_dat_cache(('osc_callbacks.py', 'midi_callbacks.py', 'midi_table_exec.py'))
    except Exception:
        pass
    try:
        configure_osc_input()
    except Exception:
        pass
    try:
        configure_midi_input()
    except Exception:
        pass
    try:
        configure_pulse_engine(reset_sync=False)
    except Exception:
        pass
    try:
        configure_audio_analysis()
    except Exception:
        pass
    try:
        reconcile_orphan_map_binds()
    except Exception:
        pass
    try:
        repair_map_dial_binds()
    except Exception:
        pass
    try:
        _wire_global_fx_chain()
        _ensure_params_column_tabs()
        _refresh_global_fx_ui()
        _refresh_layer_fx_ui()
        _refresh_map_control_layout_only()
    except Exception:
        pass
    try:
        _apply_audio_device()
    except Exception:
        pass
    try:
        restore_root_settings_layout(reposition=False)
    except Exception as exc:
        print('restore_root_settings_layout:', exc)
    try:
        normalize_asset_paths()
    except Exception:
        pass
    try:
        normalize_set_file_paths()
    except Exception:
        pass
    try:
        _refresh_settings_params_panel()
    except Exception as exc:
        print('refresh_settings_panel:', exc)


def heal_perf_tab(settings=None):
    """Repair Perf tab menu labels (All Cell Render Scale, etc.)."""
    settings = settings or _settings()
    if settings is None:
        return False

    def _inline_heal():
        specs = (
            ('Allrenderscale', 'All Cell Render Scale',
             ['100', '75', '67', '50', '25'], ['100%', '75%', '67%', '50%', '25%'], '100'),
            ('Fxrowrenderscale', 'FX render scale',
             ['100', '75', '67', '50', '25'], ['100%', '75%', '67%', '50%', '25%'], '75'),
            ('Thumbfps', 'Thumbnail FPS',
             ['60', '30', '15', '5', '1', '0'], ['Full', '30 FPS', '15 FPS', '5 FPS', '1 FPS', 'Off'], '5'),
            ('Thumbquality', 'Thumbnail Quality',
             ['100', '75', '50', '25'], ['Full', '75%', '50%', '25%'], '75'),
            ('Toxcookmode', 'Disable TOX Cooking',
             ['html', 'live', 'all'], ['Non-HTML', 'Not Active', 'Off'], 'html'),
        )
        for name, label, names, labels, default in specs:
            try:
                p = getattr(settings.par, name)
            except Exception:
                continue
            _apply_menu_options(p, names, labels)
            try:
                p.label = label
                if str(p.eval()) not in [str(n) for n in names]:
                    p.val = default
            except Exception:
                pass
        return True

    import sys
    for key in list(sys.modules.keys()):
        if key == 'performance_grid' or key.startswith('performance_grid.'):
            del sys.modules[key]
    try:
        from performance_grid.builder.helpers_settings import heal_perf_tab as _heal
        return _heal(settings)
    except Exception as exc:
        print('heal_perf_tab (builder):', exc)
        return _inline_heal()


def heal_canvas_tab(settings=None):
    """Repair Canvas Preset menu (1920x1080, etc.)."""
    settings = settings or _settings()
    if settings is None:
        return False

    def _inline_heal():
        _sync_canvas_preset_menu(settings)
        try:
            settings.par.Canvaspreset.label = 'Canvas Preset'
        except Exception:
            pass
        return True

    import sys
    for key in list(sys.modules.keys()):
        if key == 'performance_grid' or key.startswith('performance_grid.'):
            del sys.modules[key]
    try:
        from performance_grid.builder.helpers_settings import heal_canvas_tab as _heal
        return _heal(settings)
    except Exception as exc:
        print('heal_canvas_tab (builder):', exc)
        return _inline_heal()


def heal_fade_tab(settings=None):
    """Repair Fade tab pars (master Fade + Cells / Column toggles)."""
    settings = settings or _settings()
    if settings is None:
        return False
    # Release .toe files may not ship the performance_grid Python package.
    # Existing embedded Fade parameters can be healed without importing it.
    found = False
    for name, label in (
        ('Fadeactive', 'Fade'),
        ('Cellcrossfade', 'Cells'),
        ('Columncrossfade', 'Column'),
        ('Columncrossfadedur', 'Duration'),
    ):
        try:
            getattr(settings.par, name).label = label
            found = True
        except Exception:
            pass
    if found:
        return True
    try:
        from performance_grid.builder.helpers_settings import heal_fade_tab as _heal
        return _heal(settings)
    except Exception:
        return False


def reset_fade_defaults_for_new_set():
    """New set: Fade off; Cells and Column crossfade options ready."""
    settings = _settings()
    if settings is None:
        return False
    changed = False
    for name, value in (
        ('Fadeactive', False),
        ('Cellcrossfade', True),
        ('Columncrossfade', True),
    ):
        try:
            getattr(settings.par, name).val = value
            changed = True
        except Exception:
            pass
    if changed:
        return True
    try:
        from performance_grid.builder.helpers_settings import reset_fade_defaults_for_new_set as _reset
        return _reset(settings)
    except Exception:
        return False


_NEW_SET_TAB_DEFAULTS_KEY = 'new_set_all_tabs_defaults'
_NEW_SET_DEFAULT_PAGES = {
    'Canvas', 'OSC', 'GrdOSC', 'Pulse', 'Audio', 'Midi', 'Fade', 'Perf',
}
_NEW_SET_DYNAMIC_PARS = {
    'Midireceived', 'OscLastaddress', 'Gridosclastaddress',
}


def _new_set_par_is_dynamic(name):
    name = str(name)
    low = name.lower()
    if low in {item.lower() for item in _NEW_SET_DYNAMIC_PARS}:
        return True
    if low.startswith('audioout'):
        return True
    if low.startswith('osc') and low.endswith('value'):
        return True
    if low.startswith('pulse') and low.endswith('value'):
        return True
    return False


def capture_new_set_tab_defaults(settings=None):
    """Capture current editable values across all functional Settings tabs."""
    settings = settings or _settings()
    if settings is None:
        return 0
    snapshot = {}
    for page in settings.customPages:
        if str(page.name) not in _NEW_SET_DEFAULT_PAGES:
            continue
        for par in page.pars:
            if _new_set_par_is_dynamic(par.name):
                continue
            try:
                if str(par.mode) != str(ParMode.CONSTANT):
                    continue
                if 'pulse' in str(par.style).lower():
                    continue
                if bool(par.readOnly):
                    continue
            except Exception:
                pass
            try:
                snapshot[str(par.name)] = par.eval()
            except Exception:
                pass
    try:
        settings.store(_NEW_SET_TAB_DEFAULTS_KEY, snapshot, search=False)
    except Exception:
        return 0
    return len(snapshot)


def apply_new_set_tab_defaults(settings=None):
    """Apply the saved all-tab snapshot after legacy New Set resets."""
    settings = settings or _settings()
    if settings is None:
        return 0
    try:
        snapshot = settings.fetch(_NEW_SET_TAB_DEFAULTS_KEY, {}, search=False)
    except Exception:
        snapshot = {}
    if not isinstance(snapshot, dict) or not snapshot:
        return 0
    applied = 0
    parexec = settings.op('settings_parexec') or settings.op('parexec')
    parexec_was_active = None
    try:
        if parexec is not None:
            parexec_was_active = bool(parexec.par.active.eval())
            parexec.par.active = False
        for name, value in snapshot.items():
            if _new_set_par_is_dynamic(name):
                continue
            try:
                par = getattr(settings.par, str(name))
                if str(par.mode) != str(ParMode.CONSTANT):
                    continue
                if 'pulse' in str(par.style).lower():
                    continue
                par.default = value
                if par.eval() != value:
                    par.val = value
                    applied += 1
            except Exception:
                pass
    finally:
        if parexec is not None and parexec_was_active is not None:
            try:
                parexec.par.active = parexec_was_active
            except Exception:
                pass
    callbacks = (
        lambda: apply_canvas_size(),
        lambda: configure_osc_input(),
        lambda: configure_midi_input(),
        lambda: configure_pulse_engine(reset_sync=True),
        lambda: (_sync_audio_active(), _apply_audio_device()),
    )
    for index, callback in enumerate(callbacks, start=1):
        try:
            if not _defer_run(callback, delayFrames=index * 2, fromOP=_root()):
                callback()
        except Exception:
            pass
    return applied


def onInit(full=True):
    """full=False: UI/schema repairs only (script reload must not reset the grid)."""
    heal_fade_tab()
    heal_perf_tab()
    heal_canvas_tab()
    try:
        from performance_grid.builder.helpers_settings import heal_reload_scripts_button
        heal_reload_scripts_button()
    except Exception:
        pass
    _ensure_rec_normalization_settings()
    _ensure_matrix_schema()
    _ensure_comp_schema()
    _ensure_scene_bar()
    _ensure_program_preview()
    repair_ui_drops()
    repair_cell_labels()
    r = _root()
    if r is not None:
        try:
            _set_num_cols(int(float(r.par.Numcols.eval())))
        except Exception:
            _set_num_cols(NUM_COLS)
        if not _SCENE_GRID_DIMS:
            try:
                _set_scene_grid_dims(_active_scene(), _num_layers(), _num_cols())
            except Exception:
                pass
        _ensure_column_xfade_nodes(r)
        _ensure_grid_stack(r)
        _ensure_max_layers(r)
    apply_layer_opacities()
    apply_canvas_size()
    _ensure_root_output()
    configure_osc_input()
    configure_midi_input()
    configure_pulse_engine(reset_sync=True)
    configure_audio_analysis()
    try:
        _wire_global_fx_chain()
        _ensure_params_column_tabs()
        _refresh_global_fx_ui()
        _refresh_layer_fx_ui()
        _refresh_map_control_layout_only()
    except Exception:
        pass
    if full:
        try:
            tidy_root_network_view(layout=True)
        except Exception as exc:
            print('tidy_root_network_view:', exc)
    else:
        try:
            restore_root_settings_layout(reposition=False)
        except Exception as exc:
            print('restore_root_settings_layout:', exc)
    try:
        _refresh_settings_params_panel()
    except Exception as exc:
        print('refresh_settings_panel:', exc)
    if not full:
        _refresh_scene_bar()
        _refresh_ui()
        return
    dedupe_grid_assets()
    _refresh_ui()
    try:
        r = _root()
        col = int(float(r.par.Activecolumn.eval())) or 1
        r.par.Activecolumn = col
        trigger_column(col)
    except Exception:
        pass


def _auto_heal_active_column():
    """Lightweight re-wire for current composition."""
    r = _root()
    if r is None:
        return
    for sl, sc in _composition_deps():
        slot = _slot(sl, sc)
        if slot is None:
            continue
        ctype, path = _get(sl, sc)
        if not path or not _valid_clip_type(ctype):
            continue
        if ctype == 'video':
            _wire_video(slot, path, play=global_transport_playing())
        else:
            _wire_tox(slot, path, sl, sc)
            _wire_tox_chain_feed(slot, sl)
        if sl < _base_layer():
            _wire_upstream(slot, sl)
    if not _COLUMN_XFADE.get('active'):
        _route_composition_out()


def _migrate_column_clips(col):
    """No-op: clips stay on the row where they were dropped."""
    return False


def _resolve_tox_external_path(comp):
    if comp is None:
        return None
    try:
        rel = str(comp.par.externaltox.eval()).strip()
        if not rel:
            return None
        rel = rel.replace('\\\\', '/')
        if os.path.isabs(rel) and os.path.isfile(rel):
            return rel
        full = os.path.normpath(os.path.join(project.folder, rel)).replace('\\\\', '/')
        if os.path.isfile(full):
            return full
    except Exception:
        pass
    return None


def _adopt_column_contents(col, fx_layer=None):
    """No-op: clip_matrix is the only source of cell content."""
    return False


def link_manual_setup(col=None, fx_layer=None):
    """Re-wire the column from clip_matrix (video/tox cells only)."""
    r = _root()
    if r is None:
        return None
    if col is None:
        col = int(float(r.par.Activecolumn.eval())) or 1
    trigger_column(int(col))
    return int(col)


def repair_all_columns():
    """Ensure pass-through wiring + FX resolution on every column."""
    for col in range(1, _num_cols() + 1):
        for layer in range(1, _num_layers() + 1):
            _ensure_slot_chain(_slot(layer, col), layer)
        _rebuild_column_chain(col)
    _layout_perform_ui()
    _ensure_root_output()


def repair_column(col=None):
    """Re-wire FX chain for a column."""
    r = _root()
    if r is None:
        return
    if col is None:
        col = int(float(r.par.Activecolumn.eval())) or 1
    col = int(col)
    _rebuild_column_chain(col)
    _refresh_ui()
    _layout_perform_ui()
    return col


SETS_VERSION = 1
SET_DIR_REL = 'sets'
DEFAULT_SET_FILENAME = 'performance_set.json'


def _sets_folder():
    """Absolute path to sets/ beside the .toe (project.folder/sets)."""
    try:
        pf = str(project.folder or '').strip()
        if pf:
            folder = os.path.join(pf, SET_DIR_REL)
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception:
                pass
            return os.path.normpath(folder).replace('\\', '/')
    except Exception:
        pass
    try:
        from performance_grid.paths import sonomika_sets_dir
        return sonomika_sets_dir()
    except Exception:
        pass
    return SET_DIR_REL


def _set_rel_path_for_name(name):
    return '{}/{}.json'.format(SET_DIR_REL, _sanitize_set_name(name))


def _rel_set_path(path):
    """Store set paths relative to project.folder (for Savefile/Openfile)."""
    path = str(path or '').strip().replace('\\', '/')
    if not path:
        return ''
    if not os.path.isabs(path) and not (len(path) > 1 and path[1] == ':'):
        return path.lstrip('./')
    return _rel_or_abs_path(path)


def _default_set_rel_path():
    return '{}/{}'.format(SET_DIR_REL, DEFAULT_SET_FILENAME)


def _sanitize_set_name(name):
    name = str(name or 'default').strip()
    if not name:
        name = 'default'
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, '_')
    return name


def _set_path_for_name(name):
    return _set_rel_path_for_name(name)


def _path_for_set_file(path):
    path = os.path.normpath(str(path).strip()).replace('\\', '/')
    if not path:
        return ''
    if os.path.isfile(path):
        return path
    if not path.lower().endswith('.json'):
        path = path + '.json'
    if os.path.isfile(path):
        return path
    return ''


def _resolve_stored_asset_path(path):
    """Resolve a set clip path. Keep the original when missing so UI can show 'missing'."""
    path = str(path or '').strip().replace('\\', '/')
    if not path:
        return ''
    resolved = _norm_asset_path(path)
    if resolved and os.path.isfile(resolved):
        return resolved
    # File gone — keep the stored path so the cell stays assigned and labels
    # can show "missing" instead of silently dropping the clip on set open.
    return path


def _resolve_set_path(path):
    path = str(path or '').strip().replace('\\', '/')
    if not path:
        return ''
    if os.path.isabs(path) and os.path.isfile(path):
        return path
    try:
        full = os.path.normpath(os.path.join(project.folder, path)).replace('\\', '/')
        if os.path.isfile(full):
            return full
    except Exception:
        pass
    try:
        in_sets = os.path.normpath(os.path.join(_sets_folder(), os.path.basename(path))).replace('\\', '/')
        if os.path.isfile(in_sets):
            return in_sets
    except Exception:
        pass
    return _path_for_set_file(path)


def _abs_set_path(path):
    """Resolve Savefile/Openfile to an absolute path for read/write."""
    path = str(path or '').strip().replace('\\', '/')
    if not path:
        return ''
    if os.path.isabs(path) or (len(path) > 1 and path[1] == ':'):
        return os.path.normpath(path).replace('\\', '/')
    try:
        return os.path.normpath(os.path.join(project.folder, path)).replace('\\', '/')
    except Exception:
        return path


def _osc_settings_pars_for_set():
    return [n for n in _osc_page_par_order() if not n.startswith('Osclast')]


def _grid_osc_settings_pars_for_set():
    return [n for n in _grid_osc_page_par_order() if n != 'Gridosclastaddress']


def _pulse_settings_pars_for_set():
    return [n for n in _pulse_page_par_order() if not n.endswith('value')]


def _export_settings_par_block(s, names):
    out = {}
    if s is None:
        return out
    for name in names:
        try:
            out[name] = getattr(s.par, name).eval()
        except Exception:
            pass
    return out


def _apply_settings_par_block(s, data):
    if s is None or not isinstance(data, dict):
        return False
    applied = False
    for name, val in data.items():
        try:
            getattr(s.par, name).val = val
            applied = True
        except Exception:
            pass
    return applied


def _export_set_engine_settings(s):
    if s is None:
        return {}
    audio = _export_settings_par_block(s, _audio_settings_pars_for_set())
    bands = _export_audio_band_storage(s)
    if bands:
        audio['_band_storage'] = bands
    return {
        'osc': _export_settings_par_block(s, _osc_settings_pars_for_set()),
        'grid_osc': _export_settings_par_block(s, _grid_osc_settings_pars_for_set()),
        'pulse': _export_settings_par_block(s, _pulse_settings_pars_for_set()),
        'audio': audio,
    }


def _restore_set_engine_settings(state):
    s = _settings()
    if s is None or not isinstance(state, dict):
        return False
    restored = False
    for key in ('osc', 'grid_osc', 'pulse', 'audio'):
        block = state.get(key)
        if key == 'pulse' and isinstance(block, dict) and 'Pulseusetempo' in block:
            try:
                if 'Pulsecustombpm' not in block:
                    block['Pulsecustombpm'] = not bool(block['Pulseusetempo'])
            except Exception:
                pass
            try:
                del block['Pulseusetempo']
            except Exception:
                pass
        if isinstance(block, dict) and block:
            if key == 'audio':
                band_data = block.get('_band_storage')
                par_block = {k: v for k, v in block.items() if k != '_band_storage'}
                if par_block and _apply_settings_par_block(s, par_block):
                    restored = True
                if band_data and _apply_audio_band_storage(s, band_data):
                    restored = True
                continue
            if _apply_settings_par_block(s, block):
                restored = True
    if not restored:
        return False
    try:
        configure_osc_input()
    except Exception:
        pass
    try:
        configure_pulse_engine(reset_sync=True)
    except Exception:
        pass
    try:
        configure_audio_analysis()
    except Exception:
        pass
    return True


def _export_grid_state():
    r = _root()
    if r is None:
        return None
    try:
        _remember_scene_grid_dims(_active_scene())
    except Exception:
        pass
    try:
        _cache_scene_cell_params(_active_scene())
    except Exception:
        pass
    tbl = _table()
    if tbl is None:
        return None
    clips = []
    for i in range(1, tbl.numRows):
        path = str(tbl[i, 'path']).strip()
        if not path:
            continue
        scene = int(float(tbl[i, 'scene']))
        layer = int(float(tbl[i, 'layer']))
        col = int(float(tbl[i, 'col']))
        clip_type = str(tbl[i, 'type'])
        par_state = []
        try:
            if scene == _active_scene():
                par_state = _snapshot_cell_params(layer, col, clip_type)
            else:
                cached = (_SCENE_PARAM_STATE.get(scene, {}) or {}).get((layer, col), {}) or {}
                par_state = list(cached.get('records') or [])
        except Exception:
            par_state = []
        clips.append({
            'scene': scene,
            'layer': layer,
            'col': col,
            'type': clip_type,
            'path': _rel_or_abs_path(path),
            'label': str(tbl[i, 'label']),
            'render_scale': _cell_render_scale(
                layer,
                col,
                scene=scene,
            ),
            'update_rate': _cell_update_rate(
                layer,
                col,
                scene=scene,
            ),
            'frozen': _cell_frozen(
                layer,
                col,
                scene=scene,
            ),
            'par_state': par_state,
        })
    composition = []
    tbl = _comp_table()
    if tbl is not None:
        for i in range(1, tbl.numRows):
            composition.append({
                'scene': int(float(tbl[i, 'scene'])),
                'layer': int(float(tbl[i, 'layer'])),
                'src_col': int(float(tbl[i, 'src_col'])),
            })
    state = {
        'version': SETS_VERSION,
        'clips': clips,
        'composition': composition,
        'num_scenes': _num_scenes(),
        'active_scene': _active_scene(),
        'num_layers': _num_layers(),
        'num_cols': _num_cols(),
        'scene_grid_dims': dict(_SCENE_GRID_DIMS),
        'active_column': int(float(r.par.Activecolumn.eval())) or 1,
        'active_layer': int(float(r.par.Activelayer.eval())) or 1,
        'selected_layer': int(float(r.par.Selectedlayer.eval())) or 1,
        'selected_col': int(float(r.par.Selectedcol.eval())) or 1,
        'layer_opacity': [layer_opacity(layer) for layer in range(1, MAX_LAYERS + 1)],
    }
    try:
        state['cell_fx'] = export_cell_fx_state()
    except Exception:
        state['cell_fx'] = []
    try:
        state['global_fx'] = export_global_fx_state()
    except Exception:
        state['global_fx'] = []
    try:
        state['map_control'] = export_map_control_state()
    except Exception:
        state['map_control'] = []
    s = _settings()
    if s is not None:
        try:
            state['canvas'] = {
                'width': int(float(s.par.Canvaswidth.eval())),
                'height': int(float(s.par.Canvasheight.eval())),
                'preset': str(s.par.Canvaspreset.eval()),
                'background': list(_canvas_bg_rgb(s)),
            }
            saved_dims = _saved_canvas_dims(s)
            if saved_dims is not None:
                state['canvas']['saved_width'] = int(saved_dims[0])
                state['canvas']['saved_height'] = int(saved_dims[1])
        except Exception:
            pass
        try:
            state['performance'] = {
                'all_render_scale': str(s.par.Allrenderscale.eval()),
                'fx_row_render_scale': str(s.par.Fxrowrenderscale.eval()),
                'thumbnail_fps': str(s.par.Thumbfps.eval()),
                'thumbnail_quality': str(s.par.Thumbquality.eval()),
                'tox_cook_mode': str(s.par.Toxcookmode.eval()),
            }
        except Exception:
            pass
        try:
            state.update(_export_set_engine_settings(s))
        except Exception:
            pass
    return state


def _clear_grid_state():
    _clear_video_prime_cache()
    tbl = _table()
    if tbl is not None:
        for i in range(1, tbl.numRows):
            tbl[i, 'type'] = ''
            tbl[i, 'path'] = ''
            tbl[i, 'label'] = ''
            try:
                tbl[i, 'render_scale'] = '100'
            except Exception:
                pass
            try:
                tbl[i, 'update_rate'] = '1'
                tbl[i, 'frozen'] = '0'
            except Exception:
                pass
    slots = _root().op('slots') if _root() is not None else None
    if slots is not None:
        for layer_comp in list(slots.children):
            if not getattr(layer_comp, 'isCOMP', False):
                continue
            try:
                layer = int(str(layer_comp.name).split('_')[-1])
            except Exception:
                continue
            for slot in list(layer_comp.children):
                if not getattr(slot, 'isCOMP', False) or not str(slot.name).startswith('col_'):
                    continue
                try:
                    col = int(str(slot.name).split('_')[-1])
                except Exception:
                    continue
                # A genuinely new set must not serialize loaded networks from
                # the previous set. Rebuild each TOX shell instead of merely
                # blanking externaltox, which leaves old children in the .toe.
                _reset_slot_media(layer, col, hard=True)
                _reset_cell_preview(layer, col)


def _reset_new_set_runtime_routing():
    """Clear transient crossfade/program routing so a blank set starts from black."""
    r = _root()
    if r is None:
        return
    try:
        _COLUMN_XFADE.clear()
        _COLUMN_XFADE.update({'active': False, 'from_col': 1, 'to_col': 1, 't0': 0.0, 'dur': 1.0})
    except Exception:
        pass
    try:
        _LAST_LIVE_SLOT_COLS.clear()
        _LAST_UI_LIVE_CELLS.clear()
    except Exception:
        pass
    for node_name in ('chain_prev', 'chain_next'):
        node = r.op(node_name)
        black = r.op('slots/layer_1/black') or r.op('chain_out')
        if node is not None and black is not None:
            try:
                _set_top_expr(node, "op('{}')".format(black.path.replace('\\', '/')))
            except Exception:
                pass
    cross = r.op('column_xfade')
    if cross is not None:
        try:
            cross.par.cross = 1.0
        except Exception:
            pass
    for layer in range(1, MAX_LAYERS + 1):
        try:
            _set_layer_src_col(layer, 1, scene=1)
        except Exception:
            pass
    try:
        _route_composition_out()
        _route_program_out_to(_program_out_expr())
        _cook_composition_output()
    except Exception:
        pass


def _unique_new_set_name(base='untitled'):
    folder = _sets_folder()
    name = _sanitize_set_name(base)
    path = os.path.join(folder, name + '.json').replace('\\', '/')
    if not os.path.isfile(path):
        return name
    for n in range(2, 1000):
        name = _sanitize_set_name('{}_{}'.format(base, n))
        path = os.path.join(folder, name + '.json').replace('\\', '/')
        if not os.path.isfile(path):
            return name
    return _sanitize_set_name('{}_{}'.format(base, int(_now_seconds())))


def new_performance_set(set_name=None):
    """Blank performance set: clear all grid cells (all scenes). Does not write JSON until Save."""
    r = _root()
    if r is None:
        print('New set: performance_mode not found')
        return False
    # Never carry developer probe payloads into a fresh set or release .toe.
    # These historical keys can contain tens of megabytes of sampled values.
    for key in ('old_live_probe', 'live_probe2', 'tmp_bind_test'):
        try:
            r.unstore(key)
        except Exception:
            pass
    _clear_grid_state()
    try:
        clear_global_fx(all_scenes=True)
    except Exception:
        pass
    try:
        clear_map_control_state()
    except Exception:
        pass
    try:
        _CELL_FX.clear()
    except Exception:
        pass
    try:
        reset_pulse_defaults_for_new_set()
    except Exception:
        pass
    try:
        reset_audio_defaults_for_new_set()
    except Exception:
        pass
    try:
        reset_midi_defaults_for_new_set()
    except Exception:
        pass
    try:
        apply_new_set_tab_defaults()
    except Exception:
        pass
    # Fade is the one forced New Set default. Apply it after the saved
    # all-tab snapshot so a previously captured Fade=On value cannot win.
    try:
        reset_fade_defaults_for_new_set()
    except Exception:
        pass
    tbl_comp = _comp_table()
    if tbl_comp is not None:
        for i in range(tbl_comp.numRows - 1, 0, -1):
            tbl_comp.deleteRow(i)
    _reset_new_set_runtime_routing()
    _CLIPBOARD['type'] = ''
    _CLIPBOARD['path'] = ''
    _CLIPBOARD['source_layer'] = None
    _CLIPBOARD['source_col'] = None
    _CLIPBOARD['is_cut'] = False
    _CLIPBOARD['par_state'] = []
    _CLIPBOARD['render_scale'] = 100
    _CLIPBOARD['update_rate'] = 1
    _CLIPBOARD['frozen'] = False
    _COLUMN_CLIPBOARD['source_col'] = None
    _COLUMN_CLIPBOARD['cells'] = []
    _SCENE_GRID_DIMS.clear()
    _SCENE_PARAM_STATE.clear()
    _CELL_PAR_LAST_GOOD.clear()
    _set_scene_grid_dims(1, DEFAULT_LAYERS, 30)
    try:
        _set_num_layers(DEFAULT_LAYERS)
        _set_num_cols(30)
        r.par.Numscenes = DEFAULT_SCENES
        r.par.Activescene = 1
        r.par.Activecolumn = 1
        r.par.Selectedcol = 1
        r.par.Activelayer = 1
        r.par.Selectedlayer = DEFAULT_LAYERS
        for pname in ('Activelayer', 'Selectedlayer'):
            p = getattr(r.par, pname, None)
            if p is not None:
                p.normMax = MAX_LAYERS
    except Exception:
        pass
    for col in range(1, _num_cols() + 1):
        _rebuild_column_chain(col)
    switch_scene(1)
    col = 1
    trigger_column(col)
    try:
        _reset_empty_grid_previews()
        _refresh_ui(full=True)
    except Exception:
        pass
    if set_name is None:
        set_name = _unique_new_set_name()
    else:
        set_name = _sanitize_set_name(set_name)
    path = _set_path_for_name(set_name)
    _settings_set_file_pars(path)
    repair_cell_labels()
    _update_cell_params_ui(_base_layer(), col)
    try:
        _refresh_settings_params_panel()
    except Exception:
        pass
    print('New set "{}" — grid cleared (Save to write {})'.format(set_name, path))
    return True


def _default_set_path():
    return os.path.join(_sets_folder(), DEFAULT_SET_FILENAME).replace('\\', '/')


def _settings_set_file_pars(path):
    """Write relative set path into Savefile + Openfile."""
    rel = _rel_set_path(path)
    if not rel:
        return
    s = _settings()
    if s is None:
        return
    try:
        s.par.Savefile = rel
        s.par.Openfile = rel
    except Exception:
        pass


def _normalize_set_path(path):
    path = (str(path).strip() if path else '') or _default_set_rel_path()
    path = _resolve_set_path(path) or _abs_set_path(path)
    if not path.lower().endswith('.json'):
        path = path + '.json'
    return path


def _pick_set_file(title, settings_par):
    """File picker; writes path into settings Savefile or Openfile."""
    folder = _sets_folder()
    try:
        path = ui.chooseFile(title=title, fileTypes=['json'], start=folder)
    except Exception as exc:
        print('File picker error:', exc)
        path = None
    if not path:
        return ''
    path = _normalize_set_path(path)
    try:
        s = _settings()
        if s is not None and settings_par:
            setattr(s.par, settings_par, _rel_set_path(path))
    except Exception:
        pass
    return path


def save_performance_set(set_name=None, path=None):
    """Save current grid clip layout atomically to Save File."""
    state = _export_grid_state()
    if state is None:
        print('Save set: performance_mode not ready')
        return ''
    s = _settings()
    raw = str(path).strip() if path else ''
    if not raw and s is not None:
        try:
            raw = str(s.par.Savefile.eval()).strip()
        except Exception:
            pass
    if not raw and set_name:
        raw = _set_rel_path_for_name(set_name)
    if not raw:
        path = _pick_set_file('Save performance set', 'Savefile')
        if not path:
            print('Save set: enter Save File or pick a file')
            return ''
    else:
        path = _normalize_set_path(raw)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass
    temp_path = ''
    try:
        import tempfile
        folder = os.path.dirname(path) or '.'
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=folder,
            prefix='.sonomika_set_',
            suffix='.tmp',
            delete=False,
        ) as fh:
            temp_path = fh.name
            json.dump(state, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_path, path)
        temp_path = ''
        _settings_set_file_pars(path)
        print('Saved set ->', _rel_set_path(path))
        return path
    except Exception as exc:
        print('Save set failed:', exc)
        return ''
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except Exception:
                pass


def load_performance_set(path=None):
    """Restore grid clip layout from Open File."""
    r = _root()
    if r is None:
        print('Open set: performance_mode not found')
        return False
    raw = str(path).strip() if path else ''
    if not raw:
        s = _settings()
        if s is not None:
            try:
                raw = str(s.par.Openfile.eval()).strip()
            except Exception:
                pass
    if not raw:
        path = _pick_set_file('Open performance set', 'Openfile')
        if not path:
            print('Open set: set Open File or pick a file')
            return False
    else:
        path = _normalize_set_path(raw)
    if not os.path.isfile(path):
        print('Open set: file not found ->', path)
        return False
    try:
        with open(path, encoding='utf-8') as fh:
            state = json.load(fh)
    except Exception as exc:
        print('Open set: invalid JSON', exc)
        return False
    if not isinstance(state, dict):
        print('Open set: bad file format')
        return False

    # Validate scene metadata before mutating any live settings or grid state.
    try:
        ns = max(
            MIN_SCENES,
            min(MAX_SCENES, int(state.get('num_scenes', DEFAULT_SCENES))),
        )
        active_scene = max(1, min(ns, int(state.get('active_scene', 1))))
    except (TypeError, ValueError, OverflowError) as exc:
        print('Open set: invalid scene metadata', exc)
        return False

    canvas = state.get('canvas') or {}
    s = _settings()
    if s is not None and canvas:
        try:
            if 'saved_width' in canvas:
                s.store('saved_canvas_width', int(canvas['saved_width']))
            if 'saved_height' in canvas:
                s.store('saved_canvas_height', int(canvas['saved_height']))
            for name in ('Savedcanvaswidth', 'Savedcanvasheight'):
                try:
                    getattr(s.par, name).destroy()
                except Exception:
                    pass
            _sync_canvas_preset_menu(s)
            preset_names = _canvas_preset_names(s)
            if 'preset' in canvas and str(canvas['preset']) in preset_names:
                s.par.Canvaspreset = str(canvas['preset'])
            if 'width' in canvas:
                s.par.Canvaswidth = int(canvas['width'])
            if 'height' in canvas:
                s.par.Canvasheight = int(canvas['height'])
            bg = canvas.get('background')
            if isinstance(bg, (list, tuple)) and len(bg) >= 3:
                try:
                    s.par.Canvasbg = (
                        max(0.0, min(1.0, float(bg[0]))),
                        max(0.0, min(1.0, float(bg[1]))),
                        max(0.0, min(1.0, float(bg[2]))),
                    )
                except Exception:
                    pass
        except Exception:
            pass
    perf = state.get('performance') or {}
    if s is not None and perf:
        try:
            if 'all_render_scale' in perf:
                s.par.Allrenderscale = str(perf['all_render_scale'])
            if 'fx_row_render_scale' in perf:
                s.par.Fxrowrenderscale = str(perf['fx_row_render_scale'])
            if 'thumbnail_fps' in perf:
                s.par.Thumbfps = str(perf['thumbnail_fps'])
            if 'thumbnail_quality' in perf:
                s.par.Thumbquality = str(perf['thumbnail_quality'])
            if 'tox_cook_mode' in perf:
                s.par.Toxcookmode = str(perf['tox_cook_mode'])
        except Exception:
            pass
    try:
        _restore_set_engine_settings(state)
    except Exception:
        pass

    try:
        r.par.Numscenes = ns
    except Exception:
        pass
    _SCENE_GRID_DIMS.clear()
    _SCENE_PARAM_STATE.clear()
    _CELL_PAR_LAST_GOOD.clear()
    raw_dims = state.get('scene_grid_dims') or state.get('scene_dims') or {}
    if isinstance(raw_dims, dict):
        for key, dims in raw_dims.items():
            if not isinstance(dims, dict):
                continue
            try:
                _set_scene_grid_dims(
                    int(key),
                    dims.get('num_layers', DEFAULT_LAYERS),
                    dims.get('num_cols', 30),
                )
            except Exception:
                pass
    for scene in range(1, ns + 1):
        if str(scene) not in _SCENE_GRID_DIMS:
            if scene == active_scene:
                _set_scene_grid_dims(
                    scene,
                    state.get('num_layers', DEFAULT_LAYERS),
                    state.get('num_cols', 30),
                )
            else:
                _set_scene_grid_dims(scene, DEFAULT_LAYERS, 30)
    _apply_scene_grid_dims(active_scene)

    _clear_grid_state()
    tbl_comp = _comp_table()
    if tbl_comp is not None:
        for i in range(tbl_comp.numRows - 1, 0, -1):
            tbl_comp.deleteRow(i)
    touched_cols = set()
    for row in state.get('clips') or []:
        try:
            scene = int(row.get('scene', 1))
            layer = int(row.get('layer', 1))
            col = int(row.get('col', 1))
            ctype = str(row.get('type', '')).strip().lower()
            fpath = _resolve_stored_asset_path(row.get('path', ''))
            if not ctype or not fpath or ctype not in VALID_CLIP_TYPES:
                continue
            if layer < 1 or layer > _scene_num_layers(scene) or col < 1 or col > _scene_num_cols(scene):
                continue
            _set(layer, col, ctype, fpath, scene=scene)
            _set_cell_render_scale(layer, col, row.get('render_scale', 100), scene=scene)
            _set_cell_update_rate(layer, col, row.get('update_rate', 1), scene=scene)
            _set_cell_frozen(layer, col, row.get('frozen', False), scene=scene)
            par_state = list(row.get('par_state') or [])
            if par_state:
                try:
                    cached = _SCENE_PARAM_STATE.setdefault(scene, {})
                    entry = {
                        'type': ctype,
                        'path': _norm_asset_path(fpath),
                        'records': par_state,
                    }
                    cached[(layer, col)] = entry
                    _CELL_PAR_LAST_GOOD[(int(scene), int(layer), int(col))] = {
                        'type': ctype,
                        'path': _norm_asset_path(fpath),
                        'records': [dict(rec) for rec in par_state],
                    }
                except Exception:
                    pass
                if scene == active_scene:
                    try:
                        _restore_cell_params(layer, col, ctype, par_state)
                        _schedule_cell_par_restore(layer, col, ctype, par_state)
                    except Exception:
                        pass
            try:
                tbl = _table()
                idx = _find(tbl, layer, col, scene=scene)
                if idx is not None:
                    label = str(row.get('label', '')).strip()
                    if _is_bad_display_name(label):
                        label = _file_display_name(fpath, ctype)
                    if not _is_bad_display_name(label):
                        tbl[idx, 'label'] = label
            except Exception:
                pass
            if scene == active_scene:
                touched_cols.add(col)
        except Exception:
            continue
    try:
        import_cell_fx_state(state.get('cell_fx') or [])
    except Exception:
        pass
    try:
        import_global_fx_state(state.get('global_fx') or [])
    except Exception:
        pass
    try:
        import_map_control_state(state.get('map_control') or [])
    except Exception:
        pass

    try:
        r.par.Activescene = max(1, min(_num_scenes(), active_scene))
    except Exception:
        pass
    try:
        r.par.Activecolumn = max(1, min(_num_cols(), int(state.get('active_column', 1))))
        r.par.Selectedcol = max(1, min(_num_cols(), int(state.get('selected_col', r.par.Activecolumn))))
        r.par.Activelayer = max(1, min(_num_layers(), int(state.get('active_layer', 1))))
        r.par.Selectedlayer = max(1, min(_num_layers(), int(state.get('selected_layer', r.par.Activelayer))))
    except Exception:
        pass

    for i, value in enumerate(state.get('layer_opacity') or [], start=1):
        if i > MAX_LAYERS:
            break
        try:
            set_layer_opacity(i, value, paint_ui=False, all_slots=True)
        except Exception:
            pass

    for row in state.get('composition') or state.get('chains') or []:
        try:
            scene = int(row.get('scene', 1))
            if scene != active_scene:
                continue
            if 'src_col' in row:
                _set_layer_src_col(int(row['layer']), int(row['src_col']), scene=scene)
            elif 'src_layer' in row and 'src_col' in row:
                _set_layer_src_col(int(row['layer']), int(row['src_col']), scene=scene)
        except Exception:
            continue
    switch_scene(active_scene)
    col = int(float(r.par.Activecolumn.eval())) or 1
    layer = int(float(r.par.Selectedlayer.eval())) or _base_layer()
    trigger_column(col)
    try:
        warm_html_tox_cells(force=True)
    except Exception:
        pass
    # Full grid label/thumb pass so off-screen missing assets show "missing".
    try:
        _refresh_ui(full=True)
    except Exception:
        pass
    _update_cell_params_ui(layer, col)
    try:
        refresh_map_control_ui()
    except Exception:
        pass
    _settings_set_file_pars(path)
    print('Opened set ->', _rel_set_path(path))
    return True
