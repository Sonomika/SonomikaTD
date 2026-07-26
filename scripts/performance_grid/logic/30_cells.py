def get_cell(layer, col):
    return _cell_content(int(layer), int(col))


def _cell_content(layer, col):
    """Active-scene clip from clip_matrix (video or tox only)."""
    layer, col = int(layer), int(col)
    ctype, path = _get(layer, col)
    if path and _valid_clip_type(ctype):
        return ctype, path
    return '', ''


def get_clipboard():
    return dict(_CLIPBOARD)


def get_column_clipboard():
    return dict(_COLUMN_CLIPBOARD)


def _cell_param_target(layer, col, clip_type=None):
    slot = _slot(layer, col)
    if slot is None:
        return None
    if clip_type is None:
        clip_type, _ = _cell_content(layer, col)
    if clip_type == 'tox':
        return slot.op('tox')
    if clip_type == 'video':
        return slot.op('video')
    return None


def reload_cell(layer, col):
    """Reload clip from disk (external TOX pulse or video file re-open)."""
    layer, col = int(layer), int(col)
    clip_type, path = _cell_content(layer, col)
    if not path or not _valid_clip_type(clip_type):
        print('No clip to reload at row {} col {}'.format(layer, col))
        return False
    slot = _slot(layer, col)
    if slot is None:
        return False
    playing = global_transport_playing()
    par_state = []
    if clip_type == 'tox':
        par_state = _best_cell_par_state(layer, col, clip_type, path)
        try:
            clear_cell_map_out_param_binds(layer, col, clip_type)
        except Exception:
            pass
        _wire_tox(slot, path, layer, col, force_reload=True)
        _schedule_cell_par_restore(layer, col, clip_type, par_state)
        try:
            schedule_cell_map_bind_repair(layer, col)
        except Exception:
            pass
    else:
        _clear_video_prime_cache(layer, col)
        _wire_video(slot, path, play=playing, resume=True, force_reload=True)
    if _is_composition_cell(layer, col) or _get_layer_src_col(layer) == col:
        _refresh_composition_for_cols([col])
    try:
        if _cell_frozen(layer, col):
            _recapture_cell_freeze(layer, col, clip_type)
    except Exception:
        pass
    _refresh_cell_display(layer, col, force_video_prime=(clip_type == 'video'))
    if clip_type == 'video':
        _prime_video_for_thumbnail(slot, layer, col, force=True)
        _schedule_cell_preview_refresh(layer, col, 4, force_video_prime=True)
    _update_cell_params_ui(layer, col)
    _sync_grid_ui()
    print('Reloaded {} row {} col {}'.format(_label(path), layer, col))
    return True


def relink_cell(layer, col, new_path=None):
    """Point a cell at a moved/renamed file, then reload (keeps pars + map binds)."""
    layer, col = int(layer), int(col)
    clip_type, old_path = _cell_content(layer, col)
    if not old_path or not _valid_clip_type(clip_type):
        print('No clip to relink at row {} col {}'.format(layer, col))
        return False
    # Capture session pars against the old path before the picker/wire.
    par_state = []
    if clip_type == 'tox':
        par_state = _best_cell_par_state(layer, col, clip_type, old_path)
    if not new_path:
        if clip_type == 'tox':
            title, types = 'Relink TOX', ['tox']
        else:
            title, types = 'Relink Video', [e.lstrip('.') for e in sorted(VIDEO_EXTS)]
        new_path = _pick_asset_file(title, types, old_path)
    new_path = _norm_asset_path(new_path)
    if not new_path:
        print('Relink cancelled')
        return False
    if not os.path.isfile(new_path):
        print('Relink: file not found ->', new_path)
        return False
    ext = os.path.splitext(new_path)[1].lower()
    if ext == '.tox':
        new_type = 'tox'
    elif ext in VIDEO_EXTS:
        new_type = 'video'
    else:
        print('Relink: unsupported file type', ext)
        return False
    slot = _slot(layer, col)
    if slot is None:
        return False
    _set(layer, col, new_type, new_path)
    playing = global_transport_playing()
    if new_type == 'tox':
        try:
            clear_cell_map_out_param_binds(layer, col, 'tox')
        except Exception:
            pass
        _wire_tox(slot, new_path, layer, col, force_reload=True)
        if clip_type == 'tox' and par_state:
            _schedule_cell_par_restore(layer, col, 'tox', par_state)
            try:
                _CELL_PAR_LAST_GOOD[(_active_scene(), layer, col)] = {
                    'type': 'tox',
                    'path': new_path,
                    'records': [dict(rec) for rec in par_state],
                }
            except Exception:
                pass
        try:
            schedule_cell_map_bind_repair(layer, col)
        except Exception:
            pass
    else:
        _clear_video_prime_cache(layer, col)
        _wire_video(slot, new_path, play=playing, resume=True, force_reload=True)
    if _is_composition_cell(layer, col) or _get_layer_src_col(layer) == col:
        _refresh_composition_for_cols([col])
    try:
        if _cell_frozen(layer, col):
            _recapture_cell_freeze(layer, col, new_type)
    except Exception:
        pass
    _refresh_cell_display(layer, col, force_video_prime=(new_type == 'video'))
    if new_type == 'video':
        _prime_video_for_thumbnail(slot, layer, col, force=True)
        _schedule_cell_preview_refresh(layer, col, 4, force_video_prime=True)
    _update_cell_params_ui(layer, col)
    _refresh_layer_fx_ui(layer, col)
    _sync_grid_ui()
    print('Relinked row {} col {} -> {} ({} pars)'.format(
        layer, col, _label(new_path), len(par_state) if new_type == 'tox' else 0))
    return True


def get_cell_render_scale(layer, col):
    return _cell_render_scale(int(layer), int(col))


def set_cell_render_scale(layer, col, scale):
    layer, col = int(layer), int(col)
    scale = _set_cell_render_scale(layer, col, scale)
    slot = _slot(layer, col)
    ctype, path = _cell_content(layer, col)
    if slot is not None:
        _apply_slot_canvas(slot)
        if path and _valid_clip_type(ctype):
            playing = global_transport_playing() and _video_slot_should_play(layer, col)
            if ctype == 'video':
                _wire_video(slot, path, play=playing, resume=True)
                _route_slot_content(slot, 1, layer)
                _prime_video_for_thumbnail(slot, layer, col, force=True)
            else:
                _wire_tox(slot, path, layer, col)
                _route_slot_content(slot, 2, layer)
            _wire_slot_cell_fx_chain(layer, col, slot)
        else:
            _route_slot_pass_only(slot)
    _refresh_composition_for_cols([col])
    _refresh_cell_display(layer, col, force_video_prime=(ctype == 'video'))
    _update_cell_params_ui(layer, col)
    print('Render scale row {} col {} -> {}%'.format(layer, col, scale))
    return scale


def apply_all_cell_render_scale(scale=None):
    scale = _clamp_cell_render_scale(scale if scale is not None else 100)
    tbl = _table()
    if tbl is None:
        return 0
    active_scene = _active_scene()
    active_cells = []
    total = 0
    for i in range(1, tbl.numRows):
        try:
            path = str(tbl[i, 'path']).strip()
            ctype = str(tbl[i, 'type']).strip().lower()
            if not path or not _valid_clip_type(ctype):
                continue
            scene = int(float(tbl[i, 'scene']))
            layer = int(float(tbl[i, 'layer']))
            col = int(float(tbl[i, 'col']))
            _set_cell_render_scale(layer, col, scale, scene=scene)
            total += 1
            if scene == active_scene:
                active_cells.append((layer, col, ctype, path))
        except Exception:
            continue
    touched_cols = set()
    playing = global_transport_playing()
    for layer, col, ctype, path in active_cells:
        slot = _slot(layer, col)
        if slot is None:
            continue
        _apply_slot_canvas(slot)
        if ctype == 'video':
            _wire_video(slot, path, play=(playing and _video_slot_should_play(layer, col)), resume=True)
            _route_slot_content(slot, 1, layer)
            _prime_video_for_thumbnail(slot, layer, col, force=True)
        elif ctype == 'tox':
            _wire_tox(slot, path, layer, col)
            _route_slot_content(slot, 2, layer)
        _wire_slot_cell_fx_chain(layer, col, slot)
        _refresh_cell_display(layer, col, force_video_prime=(ctype == 'video'))
        touched_cols.add(col)
    if touched_cols:
        _refresh_composition_for_cols(touched_cols)
    _sync_layer_slot_pause_states(force_full=True)
    print('All cell render scale -> {}% ({} cells)'.format(scale, total))
    return total


def apply_fx_row_render_scale(scale=None):
    scale = _clamp_cell_render_scale(scale if scale is not None else _fx_row_render_scale_default())
    tbl = _table()
    if tbl is None:
        return 0
    active_scene = _active_scene()
    active_cells = []
    total = 0
    for i in range(1, tbl.numRows):
        try:
            path = str(tbl[i, 'path']).strip()
            ctype = str(tbl[i, 'type']).strip().lower()
            if not path or ctype != 'tox':
                continue
            scene = int(float(tbl[i, 'scene']))
            layer = int(float(tbl[i, 'layer']))
            col = int(float(tbl[i, 'col']))
            if layer >= int(_scene_num_layers(scene)):
                continue
            _set_cell_render_scale(layer, col, scale, scene=scene)
            total += 1
            if scene == active_scene:
                active_cells.append((layer, col, ctype, path))
        except Exception:
            continue
    touched_cols = set()
    for layer, col, ctype, path in active_cells:
        slot = _slot(layer, col)
        if slot is None:
            continue
        _apply_slot_canvas(slot)
        _wire_tox(slot, path, layer, col)
        _route_slot_content(slot, 2, layer)
        _wire_slot_cell_fx_chain(layer, col, slot)
        _refresh_cell_display(layer, col)
        touched_cols.add(col)
    if touched_cols:
        _refresh_composition_for_cols(touched_cols)
    _sync_layer_slot_pause_states(force_full=True)
    print('FX row render scale -> {}% ({} cells)'.format(scale, total))
    return total


def get_cell_update_rate(layer, col):
    return _cell_update_rate(int(layer), int(col))


def set_cell_update_rate(layer, col, rate):
    layer, col = int(layer), int(col)
    rate = _set_cell_update_rate(layer, col, rate)
    _sync_layer_slot_pause_states(force_full=True)
    label = 'Full' if rate <= 1 else '1/{}'.format(rate)
    print('Update rate row {} col {} -> {}'.format(layer, col, label))
    return rate


def get_cell_frozen(layer, col):
    return _cell_frozen(int(layer), int(col))


def set_cell_frozen(layer, col, frozen=True):
    layer, col = int(layer), int(col)
    frozen = _set_cell_frozen(layer, col, frozen)
    slot = _slot(layer, col)
    ctype, path = _cell_content(layer, col)
    if slot is not None:
        if frozen:
            _route_slot_frozen(slot, True, ctype, capture=True)
            _set_cell_fx_animation_paused(layer, col, True)
        elif path and _valid_clip_type(ctype):
            _route_slot_frozen(slot, False, ctype, capture=False)
            playing = global_transport_playing() and _video_slot_should_play(layer, col)
            if ctype == 'video':
                _wire_video(slot, path, play=playing, resume=True)
                _route_slot_content(slot, 1, layer)
            else:
                _wire_tox(slot, path, layer, col)
                _route_slot_content(slot, 2, layer)
            _set_cell_fx_animation_paused(layer, col, False)
    _sync_layer_slot_pause_states(force_full=True)
    try:
        _refresh_cell_display(layer, col, force_video_prime=(ctype == 'video'))
    except Exception:
        pass
    print('{} row {} col {}'.format('Frozen' if frozen else 'Unfrozen', layer, col))
    return frozen


def toggle_cell_freeze(layer, col):
    return set_cell_frozen(layer, col, not get_cell_frozen(layer, col))


def _resolve_tox_edit_path(stored_path='', tox_comp=None):
    """Resolve a .tox file on disk from stored path and/or live component."""
    candidates = []
    try:
        live_path = _resolve_tox_external_path(tox_comp)
        if live_path:
            candidates.append(live_path)
    except Exception:
        pass
    raw = str(stored_path or '').strip().strip('"').replace('\\', '/')
    if raw:
        candidates.append(raw)
        try:
            candidates.append(os.path.join(project.folder, raw))
        except Exception:
            pass
        pkg = _package_root()
        if pkg:
            candidates.append(os.path.join(pkg, raw))
    seen = set()
    for candidate in candidates:
        candidate = str(candidate or '').strip().strip('"')
        if not candidate:
            continue
        full = os.path.normpath(candidate).replace('\\', '/')
        if full in seen:
            continue
        seen.add(full)
        if os.path.isfile(full) and full.lower().endswith('.tox'):
            return full
    return ''


def _resolve_cell_tox_edit_path(layer, col):
    """Resolve the original .tox file for opening in a separate TouchDesigner instance."""
    layer, col = int(layer), int(col)
    clip_type, path = _cell_content(layer, col)
    if clip_type != 'tox' or not path:
        return ''
    slot = _slot(layer, col)
    tox = slot.op('tox') if slot is not None else None
    return _resolve_tox_edit_path(path, tox)


def _touchdesigner_executable():
    try:
        import sys
        argv0 = str(sys.argv[0] if sys.argv else '').strip()
        if argv0 and os.path.isfile(argv0) and os.path.basename(argv0).lower().startswith('touchdesigner'):
            return os.path.normpath(argv0)
        exe = str(getattr(sys, 'executable', '') or '').strip()
        sibling = os.path.join(os.path.dirname(exe), 'TouchDesigner.exe') if exe else ''
        if sibling and os.path.isfile(sibling):
            return os.path.normpath(sibling)
    except Exception:
        pass
    return ''


def open_tox_for_edit(tox_path):
    """Open a .tox file in a separate TouchDesigner process (or OS default)."""
    tox_path = str(tox_path or '').strip()
    if not tox_path or not os.path.isfile(tox_path):
        return False
    try:
        import subprocess
        exe = _touchdesigner_executable()
        if exe and os.path.isfile(exe):
            proc = subprocess.Popen([exe, tox_path], cwd=os.path.dirname(tox_path) or None)
            try:
                proc.wait(timeout=2.0)
                if proc.returncode is not None:
                    os.startfile(tox_path)
            except Exception:
                pass
        else:
            os.startfile(tox_path)
        print('Opened TOX for editing:', tox_path)
        return True
    except Exception as exc:
        try:
            os.startfile(tox_path)
            print('Opened TOX for editing:', tox_path)
            return True
        except Exception:
            print('Edit TOX failed:', tox_path, exc)
            return False


def edit_tox_cell(layer, col):
    """Open the cell's original .tox in a separate TouchDesigner process."""
    layer, col = int(layer), int(col)
    tox_path = _resolve_cell_tox_edit_path(layer, col)
    if not tox_path:
        print('No .tox file found for row {} col {}'.format(layer, col))
        return False
    return open_tox_for_edit(tox_path)


def _copyable_cell_params(target, clip_type):
    if target is None:
        return []
    out = []
    if clip_type == 'tox':
        try:
            out.extend(list(target.customPars))
        except Exception:
            pass
    elif clip_type == 'video':
        for name in ('play', 'speed', 'index', 'textendright', 'trim'):
            try:
                out.append(getattr(target.par, name))
            except Exception:
                pass
    return out


def _snapshot_cell_params(layer, col, clip_type=None):
    clip_type = clip_type or _cell_content(layer, col)[0]
    target = _cell_param_target(layer, col, clip_type)
    records = []
    for par in _copyable_cell_params(target, clip_type):
        rec = {'name': par.name}
        try:
            rec['val'] = par.eval()
        except Exception:
            try:
                rec['val'] = par.val
            except Exception:
                pass
        try:
            expr = str(par.expr or '').strip()
            if expr:
                rec['expr'] = expr
        except Exception:
            pass
        try:
            bind_expr = str(par.bindExpr or '').strip()
            if bind_expr:
                rec['bindExpr'] = bind_expr
        except Exception:
            pass
        records.append(rec)
    return records


def _remember_cell_par_last_good(layer, col, clip_type=None, path=None, records=None):
    """Keep last known-good custom pars while the asset file still exists."""
    layer, col = int(layer), int(col)
    if clip_type is None or path is None:
        ctype, cpath = _cell_content(layer, col)
        clip_type = clip_type or ctype
        path = path if path is not None else cpath
    if not path or not _valid_clip_type(clip_type):
        return
    if _asset_file_missing(path, clip_type):
        return
    if records is None:
        records = _snapshot_cell_params(layer, col, clip_type)
    if not records:
        return
    _CELL_PAR_LAST_GOOD[(_active_scene(), layer, col)] = {
        'type': clip_type,
        'path': _norm_asset_path(path),
        'records': [dict(rec) for rec in records],
    }


def _best_cell_par_state(layer, col, clip_type, path):
    """Prefer last-good session pars over a live shell (missing/default reload)."""
    layer, col = int(layer), int(col)
    live = _snapshot_cell_params(layer, col, clip_type)
    key = (_active_scene(), layer, col)
    last = dict(_CELL_PAR_LAST_GOOD.get(key) or {})
    cached = dict((_SCENE_PARAM_STATE.get(_active_scene(), {}) or {}).get((layer, col), {}) or {})
    path_norm = _norm_asset_path(path)
    missing = _asset_file_missing(path, clip_type)

    def _usable(entry, allow_path_mismatch=False):
        if not entry or not entry.get('records'):
            return []
        if entry.get('type') and str(entry.get('type')) != str(clip_type):
            return []
        entry_path = _norm_asset_path(entry.get('path'))
        if entry_path and path_norm and entry_path != path_norm and not allow_path_mismatch:
            return []
        return list(entry.get('records') or [])

    last_recs = _usable(last, allow_path_mismatch=True)
    cache_recs = _usable(cached, allow_path_mismatch=True)
    if missing:
        # Don't trust a live shell after the file vanished — keep last-good or
        # fall through to empty so the new file's saved defaults can load.
        return last_recs or cache_recs
    if live:
        _remember_cell_par_last_good(layer, col, clip_type, path, live)
        # Prefer remembered session if live still looks like a thin/default shell.
        if last_recs and len(last_recs) > len(live):
            return last_recs
        return live
    return last_recs or cache_recs


def _restore_cell_params(layer, col, clip_type, records):
    if not records:
        return 0
    target = _cell_param_target(layer, col, clip_type)
    if target is None:
        return 0
    restored = 0
    for rec in records:
        try:
            par = getattr(target.par, rec.get('name', ''))
        except Exception:
            continue
        try:
            bind_expr = str(rec.get('bindExpr', '') or '').strip()
            if bind_expr:
                skip_map_bind = False
                try:
                    if is_map_out_bind_expr(bind_expr):
                        skip_map_bind = True
                except NameError:
                    pass
                if not skip_map_bind:
                    try:
                        bind_expr = _sanitize_bind_expr(bind_expr)
                    except Exception:
                        pass
                    par.bindExpr = bind_expr
                    try:
                        par.mode = ParMode.BIND
                    except Exception:
                        pass
                    restored += 1
                    continue
        except Exception:
            pass
        try:
            if rec.get('expr'):
                par.expr = rec['expr']
                try:
                    par.mode = ParMode.EXPRESS
                except Exception:
                    pass
                restored += 1
                continue
        except Exception:
            pass
        try:
            par.val = rec.get('val')
            try:
                par.mode = ParMode.CONSTANT
            except Exception:
                pass
            restored += 1
        except Exception:
            pass
    return restored


def _schedule_cell_par_restore(layer, col, clip_type, records):
    """Re-apply TOX settings after enableexternaltoxpulse (load is async)."""
    records = list(records or [])
    if clip_type != 'tox' or not records:
        return
    layer, col = int(layer), int(col)
    expected = {str(rec.get('name', '')) for rec in records if rec.get('name')}

    def _apply():
        target = _cell_param_target(layer, col, clip_type)
        if target is None:
            return
        try:
            live_names = {p.name for p in list(target.customPars)}
        except Exception:
            live_names = set()
        # External tox custom pages may not exist yet — later delays retry.
        if expected and live_names and not (expected & live_names):
            return
        n = _restore_cell_params(layer, col, clip_type, records)
        if n:
            try:
                ctype, path = _cell_content(layer, col)
                _remember_cell_par_last_good(layer, col, ctype, path, records)
            except Exception:
                pass
        _update_cell_params_ui(layer, col)

    root = _root()
    for delay in (1, 4, 12, 30, 60, 120):
        try:
            if root is not None:
                run(_apply, delayFrames=int(delay), fromOP=root)
            else:
                run(_apply, delayFrames=int(delay))
        except Exception:
            pass


def _cache_scene_cell_params(scene=None):
    """Remember live cell parameter edits before a scene rewire reloads slots."""
    scene = _active_scene() if scene is None else int(scene)
    tbl = _table()
    if tbl is None:
        return {}
    cached = {}
    for i in range(1, tbl.numRows):
        try:
            if int(tbl[i, 'scene']) != int(scene):
                continue
            layer = int(tbl[i, 'layer'])
            col = int(tbl[i, 'col'])
            clip_type = str(tbl[i, 'type'])
            path = str(tbl[i, 'path'])
        except Exception:
            continue
        if not path or not _valid_clip_type(clip_type):
            continue
        if _asset_file_missing(path, clip_type):
            # Keep prior last-good / scene cache; don't overwrite with empty shell.
            prior = (_SCENE_PARAM_STATE.get(int(scene), {}) or {}).get((layer, col))
            if prior:
                cached[(layer, col)] = dict(prior)
            last = _CELL_PAR_LAST_GOOD.get((int(scene), layer, col))
            if last and (layer, col) not in cached:
                cached[(layer, col)] = dict(last)
            continue
        records = _snapshot_cell_params(layer, col, clip_type)
        if records:
            entry = {
                'type': clip_type,
                'path': _norm_asset_path(path),
                'records': records,
            }
            cached[(layer, col)] = entry
            _CELL_PAR_LAST_GOOD[(int(scene), layer, col)] = {
                'type': clip_type,
                'path': _norm_asset_path(path),
                'records': [dict(rec) for rec in records],
            }
    _SCENE_PARAM_STATE[int(scene)] = cached
    return cached


def _restore_scene_cell_params(scene=None):
    """Restore cached per-scene cell parameters after scene slots are rebuilt."""
    scene = _active_scene() if scene is None else int(scene)
    cached = dict(_SCENE_PARAM_STATE.get(int(scene), {}) or {})
    if not cached:
        return 0
    restored = 0
    for (layer, col), rec in cached.items():
        try:
            layer, col = int(layer), int(col)
        except Exception:
            continue
        clip_type, path = _cell_content(layer, col)
        if clip_type != rec.get('type'):
            continue
        if _norm_asset_path(path) != _norm_asset_path(rec.get('path')):
            continue
        records = list(rec.get('records') or [])
        if not records:
            continue
        restored += _restore_cell_params(layer, col, clip_type, records)
        if clip_type == 'tox':
            _schedule_cell_par_restore(layer, col, clip_type, records)
    return restored


def _column_cells(col):
    col = int(col)
    cells = []
    for layer in range(1, _num_layers() + 1):
        clip_type, path = _cell_content(layer, col)
        if not path:
            continue
        cells.append({
            'layer': layer,
            'type': clip_type,
            'path': path,
            'par_state': _snapshot_cell_params(layer, col, clip_type),
            'cell_fx': snapshot_cell_fx(layer, col),
            'map_control': snapshot_cell_map_control(layer, col),
            'render_scale': _cell_render_scale(layer, col),
            'update_rate': _cell_update_rate(layer, col),
            'frozen': _cell_frozen(layer, col),
        })
    return cells


def column_has_clips(col):
    return bool(_column_cells(int(col)))


def copy_column(col):
    col = int(col)
    cells = _column_cells(col)
    if not cells:
        return False
    _COLUMN_CLIPBOARD['source_col'] = col
    _COLUMN_CLIPBOARD['cells'] = cells
    print('Copied column {} ({} clip{})'.format(col, len(cells), '' if len(cells) == 1 else 's'))
    return True


def paste_column(col):
    col = int(col)
    cells = list(_COLUMN_CLIPBOARD.get('cells') or [])
    if not cells:
        return False
    source_col = _COLUMN_CLIPBOARD.get('source_col')
    skip = []
    if source_col is not None:
        skip.extend((int(c['layer']), int(source_col)) for c in cells)
    seen = set(skip)
    for cell in cells:
        clip_type = cell.get('type', '')
        path = cell.get('path', '')
        if not path or not _valid_clip_type(clip_type):
            continue
        for hit in _find_asset_cells(clip_type, path):
            if hit not in seen:
                seen.add(hit)
                skip.append(hit)
    for layer in range(1, _num_layers() + 1):
        hit = (layer, col)
        if hit not in seen:
            seen.add(hit)
            skip.append(hit)
    source_layers = set(int(c['layer']) for c in cells)
    for layer in range(1, _num_layers() + 1):
        if layer not in source_layers:
            clear_cell(layer, col)
    for cell in cells:
        layer = int(cell['layer'])
        clip_type = cell.get('type', '')
        path = cell.get('path', '')
        if not path or not _valid_clip_type(clip_type):
            continue
        load_cell(
            layer, col, clip_type, path,
            skip_evict=skip,
            par_state=cell.get('par_state') or [],
        )
        if 'render_scale' in cell:
            set_cell_render_scale(layer, col, cell.get('render_scale', 100))
        if 'update_rate' in cell:
            set_cell_update_rate(layer, col, cell.get('update_rate', 1))
        if 'frozen' in cell:
            set_cell_frozen(layer, col, cell.get('frozen', False))
        restore_cell_fx(layer, col, cell.get('cell_fx') or [])
        map_control = cell.get('map_control') or {}
        if map_control:
            restore_cell_map_control(
                layer, col, map_control,
                src_layer=layer, src_col=int(source_col),
            )
    _refresh_composition_for_cols({col, source_col})
    _update_cell_params_ui()
    _sync_grid_ui()
    print('Pasted column {} -> column {}'.format(source_col, col))
    return True


def delete_column(col):
    col = int(col)
    for layer in range(1, _num_layers() + 1):
        clear_cell(layer, col)
    _refresh_composition_for_cols([col])
    _update_cell_params_ui()
    _sync_grid_ui()
    print('Deleted column {}'.format(col))
    return True


def _all_grid_coords():
    return [(layer, col) for layer in range(1, _num_layers() + 1) for col in range(1, _num_cols() + 1)]


def _num_cols():
    global NUM_COLS
    r = _root()
    if r is not None:
        try:
            count = max(1, int(float(r.par.Numcols.eval())))
            NUM_COLS = count
            return count
        except Exception:
            pass
    return max(1, int(NUM_COLS))


def _scene_grid_defaults():
    return {'num_layers': DEFAULT_LAYERS, 'num_cols': 30}


def _scene_grid_key(scene=None):
    if scene is None:
        scene = _active_scene()
    return str(max(1, int(scene)))


def _scene_grid_dims(scene=None):
    key = _scene_grid_key(scene)
    dims = _SCENE_GRID_DIMS.get(key)
    if not isinstance(dims, dict):
        dims = _scene_grid_defaults()
        _SCENE_GRID_DIMS[key] = dict(dims)
    return dims


def _scene_num_layers(scene=None):
    dims = _scene_grid_dims(scene)
    return max(MIN_LAYERS, min(MAX_LAYERS, int(dims.get('num_layers', DEFAULT_LAYERS))))


def _scene_num_cols(scene=None):
    dims = _scene_grid_dims(scene)
    return max(1, int(dims.get('num_cols', 30)))


def _remember_scene_grid_dims(scene=None):
    key = _scene_grid_key(scene)
    _SCENE_GRID_DIMS[key] = {
        'num_layers': _num_layers(),
        'num_cols': _num_cols(),
    }
    return _SCENE_GRID_DIMS[key]


def _set_num_layers(count):
    count = max(MIN_LAYERS, min(MAX_LAYERS, int(count)))
    r = _root()
    if r is None:
        return count
    try:
        r.par.Numlayers = count
    except Exception:
        pass
    for pname in ('Activelayer', 'Selectedlayer'):
        try:
            p = getattr(r.par, pname)
            p.max = count
            p.normMax = MAX_LAYERS
            p.val = max(1, min(count, int(float(p.eval()))))
        except Exception:
            pass
    return count


def _apply_scene_grid_dims(scene=None):
    dims = _scene_grid_dims(scene)
    _set_num_layers(dims.get('num_layers', DEFAULT_LAYERS))
    _set_num_cols(dims.get('num_cols', 30))
    r = _root()
    if r is not None:
        try:
            r.par.Activecolumn = max(1, min(_num_cols(), int(float(r.par.Activecolumn.eval()))))
            r.par.Selectedcol = max(1, min(_num_cols(), int(float(r.par.Selectedcol.eval()))))
            r.par.Activelayer = max(1, min(_num_layers(), int(float(r.par.Activelayer.eval()))))
            r.par.Selectedlayer = max(1, min(_num_layers(), int(float(r.par.Selectedlayer.eval()))))
        except Exception:
            pass
    return dims


def _set_scene_grid_dims(scene, num_layers=None, num_cols=None):
    key = _scene_grid_key(scene)
    dims = dict(_scene_grid_dims(scene))
    if num_layers is not None:
        dims['num_layers'] = max(MIN_LAYERS, min(MAX_LAYERS, int(num_layers)))
    if num_cols is not None:
        dims['num_cols'] = max(1, int(num_cols))
    _SCENE_GRID_DIMS[key] = dims
    return dims


def _set_num_cols(count):
    global NUM_COLS
    count = max(1, int(count))
    NUM_COLS = count
    r = _root()
    if r is not None:
        page = None
        for pg in r.customPages:
            if pg.name == 'Grid':
                page = pg
                break
        if page is None:
            page = r.appendCustomPage('Grid')
        try:
            p = r.par.Numcols
        except Exception:
            p = page.appendInt('Numcols', label='Columns')
            p.default = count
            p.min = 1
        try:
            p.max = max(count, 256)
            p.normMax = max(count, 256)
            try:
                p.mode = ParMode.CONSTANT
            except Exception:
                pass
            p.val = count
        except Exception:
            pass
        try:
            r.par.Numcols = count
        except Exception:
            pass
        for pname in ('Activecolumn', 'Selectedcol'):
            try:
                p = getattr(r.par, pname)
                p.max = count
                p.normMax = count
            except Exception:
                pass
        try:
            r.par.Status = '{} columns'.format(count)
        except Exception:
            pass
        try:
            _hide_columns_after(count)
        except Exception:
            pass
    return count


def _hide_columns_after(count):
    """Hide dynamic UI/slot operators beyond the active column count."""
    count = max(1, int(count))
    r = _root()
    if r is None:
        return
    hdr = _ui_grid_header(r)
    if hdr is not None:
        for ch in hdr.children:
            if ch.name.startswith('colhdr_'):
                try:
                    ch.par.display = int(ch.name.split('_')[1]) <= count
                except Exception:
                    pass
    grid = _ui_grid(r)
    if grid is not None:
        for row in grid.children:
            if not row.name.startswith('row_'):
                continue
            for cell in row.children:
                if cell.name.startswith('cell_'):
                    try:
                        cell.par.display = int(cell.name.split('_')[2]) <= count
                    except Exception:
                        pass
    slots = r.op('slots')
    if slots is not None:
        for layer_comp in slots.children:
            if not layer_comp.name.startswith('layer_'):
                continue
            for slot in layer_comp.children:
                if slot.name.startswith('col_'):
                    try:
                        slot.par.display = int(slot.name.split('_')[1]) <= count
                    except Exception:
                        pass


def reset_columns(count=30):
    """Reset active column count and relayout, without deleting existing hidden columns."""
    count = _set_num_cols(count)
    _set_scene_grid_dims(_active_scene(), num_cols=count)
    _force_grid_refresh()
    _defer_grid_refresh()
    print('Reset columns to {}'.format(count))
    return count


def _force_grid_refresh():
    """Relayout and cook scroll-related panels immediately."""
    try:
        _sync_grid_ui()
    except Exception:
        pass
    try:
        _refresh_ui()
    except Exception:
        pass
    try:
        _refresh_panel_exec_panels()
    except Exception:
        pass
    r = _root()
    if r is None:
        return
    ui = r.op('ui')
    stack = _ui_grid_stack(r)
    hdr = _ui_grid_header(r)
    grid = _ui_grid(r)
    try:
        if stack is not None and grid is not None:
            value = None
            for name in ('scrollu', 'scrollx', 'u'):
                try:
                    value = float(getattr(stack.panel, name))
                    break
                except Exception:
                    pass
            if value is not None:
                for name in ('scrollu', 'scrollx', 'u'):
                    try:
                        setattr(grid.panel, name, value)
                        break
                    except Exception:
                        pass
    except Exception:
        pass
    try:
        gutter = _ui_grid_gutter(r)
        rows = gutter.op('fixed_rows') if gutter is not None else None
        proxy = ui.op('grid_vscroll') if ui is not None else None
        source = proxy if proxy is not None else grid
        if rows is not None and source is not None:
            value = None
            for name in ('scrollv', 'scrolly', 'v'):
                try:
                    value = float(getattr(source.panel, name))
                    break
                except Exception:
                    pass
            if value is not None:
                if grid is not None:
                    for name in ('scrollv', 'scrolly', 'v'):
                        try:
                            setattr(grid.panel, name, value)
                            break
                        except Exception:
                            pass
                for name in ('scrollv', 'scrolly', 'v'):
                    try:
                        setattr(rows.panel, name, value)
                        break
                    except Exception:
                        pass
    except Exception:
        pass
    for node in (ui, stack, hdr, grid):
        try:
            if node is not None:
                node.cook(force=True)
        except Exception:
            pass


def _defer_grid_refresh(delay_frames=1):
    """Run the same refresh after PopMenu/panel callbacks finish."""
    def _cb():
        try:
            _force_grid_refresh()
        except Exception:
            pass
    try:
        run(_cb, delayFrames=max(1, int(delay_frames)), fromOP=_root())
    except Exception:
        try:
            run(_cb, delayFrames=max(1, int(delay_frames)))
        except Exception:
            pass


def _ensure_column_exists(col):
    col = int(col)
    r = _root()
    if r is None:
        return
    _ensure_grid_stack(r)
    grid = _ui_grid(r)
    hdr = _ui_grid_header(r)
    slots = r.op('slots')
    if hdr is not None and hdr.op('colhdr_{}'.format(col)) is None:
        ch = hdr.create('containerCOMP', 'colhdr_{}'.format(col))
        txt = ch.create('textTOP', 'label_text')
        _style_header_text(txt, CELL_W, GRID_HDR_H, 'Col {}'.format(col))
        _set_par(ch, 'top', txt)
        _set_par(ch, 'topfill', 'fit')
        try:
            ch.par.drop = 'dropno'
            ch.par.drag = 'dragno'
        except Exception:
            pass
    if hdr is not None:
        ch = hdr.op('colhdr_{}'.format(col))
        if ch is not None:
            try:
                ch.par.display = True
                ch.par.enable = True
            except Exception:
                pass
    if grid is not None:
        legacy = r.op('legacy_drop')
        for layer in range(1, _num_layers() + 1):
            row = grid.op('row_{}'.format(layer))
            if row is None:
                continue
            cell = row.op('cell_{}_{}'.format(layer, col))
            if cell is None:
                cell = row.create('containerCOMP', 'cell_{}_{}'.format(layer, col))
                _set_par(cell, 'w', CELL_W)
                _set_par(cell, 'h', CELL_H)
                _ensure_cell_layout(cell)
            try:
                cell.par.display = True
                cell.par.enable = True
            except Exception:
                pass
            _repair_cell_dragdrop(cell, grid, legacy)
    if slots is not None:
        for layer in range(1, MAX_LAYERS + 1):
            layer_comp = slots.op('layer_{}'.format(layer))
            if layer_comp is None:
                continue
            if layer_comp.op('col_{}'.format(col)) is None:
                out = _build_slot(layer_comp, col, layer)
                sw = layer_comp.op('switch')
                if sw is not None:
                    try:
                        out.outputConnectors[0].connect(sw.inputConnectors[col])
                    except Exception:
                        pass
            slot = layer_comp.op('col_{}'.format(col))
            if slot is not None:
                try:
                    slot.par.display = True
                except Exception:
                    pass


def _shift_composition_cols_on_insert(ref_col):
    ref_col = int(ref_col)
    scene = _active_scene()
    tbl = _comp_table()
    if tbl is not None:
        for i in range(1, tbl.numRows):
            try:
                if int(tbl[i, 'scene']) != scene:
                    continue
                src_col = int(tbl[i, 'src_col'])
                if src_col >= ref_col:
                    tbl[i, 'src_col'] = min(_num_cols(), src_col + 1)
            except Exception:
                pass
    r = _root()
    if r is not None:
        for pname in ('Activecolumn', 'Selectedcol'):
            try:
                p = getattr(r.par, pname)
                cur = int(float(p.eval()))
                if cur >= ref_col:
                    p.val = min(_num_cols(), cur + 1)
            except Exception:
                pass


def insert_column(col):
    """Insert empty column before col; grow column count and shift current-scene clips right."""
    col = int(col)
    current_cols = _num_cols()
    if col < 1 or col > current_cols:
        return False
    old_cols = current_cols
    _set_num_cols(old_cols + 1)
    new_cols = max(old_cols + 1, _num_cols())
    _set_num_cols(new_cols)
    _set_scene_grid_dims(_active_scene(), num_cols=new_cols)
    _ensure_column_exists(new_cols)
    snapshots = {}
    for c in range(col, old_cols + 1):
        snapshots[c] = _column_cells(c)
    for c in range(col, new_cols + 1):
        for layer in range(1, _num_layers() + 1):
            clear_cell(layer, c)
    skip = _all_grid_coords()
    for src_col in range(old_cols, col - 1, -1):
        dst_col = src_col + 1
        for cell in snapshots.get(src_col) or []:
            layer = int(cell['layer'])
            clip_type = cell.get('type', '')
            path = cell.get('path', '')
            if not path or not _valid_clip_type(clip_type):
                continue
            load_cell(
                layer, dst_col, clip_type, path,
                skip_evict=skip,
                par_state=cell.get('par_state') or [],
            )
            if 'render_scale' in cell:
                set_cell_render_scale(layer, dst_col, cell.get('render_scale', 100))
            if 'update_rate' in cell:
                set_cell_update_rate(layer, dst_col, cell.get('update_rate', 1))
            if 'frozen' in cell:
                set_cell_frozen(layer, dst_col, cell.get('frozen', False))
            restore_cell_fx(layer, dst_col, cell.get('cell_fx') or [])
    _shift_composition_cols_on_insert(col)
    _rebuild_composition()
    _cache_scene_cell_params(_active_scene())
    _force_grid_refresh()
    _defer_grid_refresh()
    _update_cell_params_ui()
    print('Inserted column before {} ({} columns)'.format(col, new_cols))
    return True


def copy_cell(layer, col):
    layer, col = int(layer), int(col)
    clip_type, path = _cell_content(layer, col)
    if not path:
        return False
    _CLIPBOARD['type'] = clip_type
    _CLIPBOARD['path'] = path
    _CLIPBOARD['source_layer'] = layer
    _CLIPBOARD['source_col'] = col
    _CLIPBOARD['is_cut'] = False
    _CLIPBOARD['par_state'] = _snapshot_cell_params(layer, col, clip_type)
    _CLIPBOARD['cell_fx'] = snapshot_cell_fx(layer, col)
    _CLIPBOARD['map_control'] = snapshot_cell_map_control(layer, col)
    _CLIPBOARD['render_scale'] = _cell_render_scale(layer, col)
    _CLIPBOARD['update_rate'] = _cell_update_rate(layer, col)
    _CLIPBOARD['frozen'] = _cell_frozen(layer, col)
    print('Copied {} from row {} col {}'.format(_label(path), layer, col))
    return True


def cut_cell(layer, col):
    """Copy to clipboard and mark for move on next paste (source cleared on paste)."""
    if not copy_cell(layer, col):
        return False
    _CLIPBOARD['is_cut'] = True
    print('Cut {} from row {} col {}'.format(_label(_CLIPBOARD['path']), layer, col))
    return True


def _paste_skip_evict(clip_type, path, is_cut, src_layer, src_col):
    """Cells to keep when loading a pasted clip (duplicate eviction)."""
    if is_cut:
        skip = []
        if src_layer is not None and src_col is not None:
            skip.append((int(src_layer), int(src_col)))
        return skip
    return list(_find_asset_cells(clip_type, path))


def paste_cell(layer, col):
    layer, col = int(layer), int(col)
    clip_type = _CLIPBOARD.get('type', '')
    path = _CLIPBOARD.get('path', '')
    if not path:
        return False
    is_cut = bool(_CLIPBOARD.get('is_cut'))
    src_layer = _CLIPBOARD.get('source_layer')
    src_col = _CLIPBOARD.get('source_col')
    par_state = list(_CLIPBOARD.get('par_state') or [])
    render_scale = _CLIPBOARD.get('render_scale', 100)
    update_rate = _CLIPBOARD.get('update_rate', 1)
    frozen = _CLIPBOARD.get('frozen', False)
    cell_fx = list(_CLIPBOARD.get('cell_fx') or [])
    map_control = dict(_CLIPBOARD.get('map_control') or {})
    skip = _paste_skip_evict(clip_type, path, is_cut, src_layer, src_col)
    load_cell(layer, col, clip_type, path, skip_evict=skip, par_state=par_state)
    set_cell_render_scale(layer, col, render_scale)
    set_cell_update_rate(layer, col, update_rate)
    set_cell_frozen(layer, col, frozen)
    restore_cell_fx(layer, col, cell_fx)
    if map_control:
        restore_cell_map_control(
            layer, col, map_control,
            src_layer=src_layer, src_col=src_col,
        )
        try:
            activate_cell_map_control(layer, col, force=True)
            if clip_type == 'tox':
                schedule_cell_map_bind_repair(layer, col)
        except Exception:
            pass
    if is_cut and src_layer is not None and src_col is not None:
        sl, sc = int(src_layer), int(src_col)
        if (sl, sc) != (layer, col):
            clear_cell(sl, sc)
        _CLIPBOARD['is_cut'] = False
        _CLIPBOARD['source_layer'] = None
        _CLIPBOARD['source_col'] = None
    cols = {col}
    if src_col is not None:
        cols.add(int(src_col))
    _refresh_composition_for_cols(cols)
    action = 'Moved' if is_cut else 'Pasted'
    print('{} {} -> row {} col {}'.format(action, _label(path), layer, col))
    _update_cell_params_ui(layer, col)
    _sync_grid_ui()
    return True


def delete_cell(layer, col):
    layer, col = int(layer), int(col)
    clear_cell(layer, col)
    _refresh_composition_for_cols([col])
    print('Deleted row {} col {}'.format(layer, col))
    r = _root()
    if r is not None:
        try:
            if int(float(r.par.Selectedlayer.eval())) == layer and int(float(r.par.Selectedcol.eval())) == col:
                _update_cell_params_ui(layer, col)
                _sync_grid_ui()
        except Exception:
            pass
    return True


def num_layers():
    return _num_layers()


def max_layers():
    return MAX_LAYERS


def min_layers():
    return MIN_LAYERS


def base_layer():
    return _base_layer()


def num_scenes():
    return _num_scenes()


def max_scenes():
    return MAX_SCENES


def min_scenes():
    return MIN_SCENES


def _shift_scene_grid_dims(removed):
    """Renumber stored per-scene grid sizes after a scene is deleted."""
    removed = int(removed)
    new_dims = {}
    for key, dims in list(_SCENE_GRID_DIMS.items()):
        try:
            s = int(key)
        except Exception:
            continue
        if s == removed:
            continue
        new_dims[str(s - 1 if s > removed else s)] = dict(dims)
    _SCENE_GRID_DIMS.clear()
    _SCENE_GRID_DIMS.update(new_dims)


def _purge_scene_from_table(tbl, removed):
    """Remove one scene and decrement higher scene indices in a tableDAT."""
    if tbl is None or tbl.numRows < 2:
        return
    removed = int(removed)
    for i in range(tbl.numRows - 1, 0, -1):
        try:
            s = int(tbl[i, 'scene'])
        except Exception:
            continue
        if s == removed:
            tbl.deleteRow(i)
        elif s > removed:
            tbl[i, 'scene'] = s - 1


def _copy_scene_data(src, dst):
    """Copy clip_matrix + comp_matrix rows from src scene to dst scene."""
    src, dst = int(src), int(dst)
    _ensure_matrix_schema()
    tbl = _table()
    if tbl is not None:
        for i in range(1, tbl.numRows):
            try:
                if int(tbl[i, 'scene']) != src:
                    continue
                layer = int(tbl[i, 'layer'])
                col = int(tbl[i, 'col'])
                ctype = str(tbl[i, 'type']).strip()
                path = str(tbl[i, 'path']).strip()
            except Exception:
                continue
            if path and _valid_clip_type(ctype):
                _set(layer, col, ctype, path, scene=dst)
                _set_cell_render_scale(layer, col, _cell_render_scale(layer, col, scene=src), scene=dst)
                _set_cell_update_rate(layer, col, _cell_update_rate(layer, col, scene=src), scene=dst)
                _set_cell_frozen(layer, col, _cell_frozen(layer, col, scene=src), scene=dst)
    comp = _comp_table()
    if comp is not None:
        for i in range(1, comp.numRows):
            try:
                if int(comp[i, 'scene']) != src:
                    continue
                layer = int(comp[i, 'layer'])
                src_col = int(comp[i, 'src_col'])
            except Exception:
                continue
            _set_layer_src_col(layer, src_col, scene=dst)


def duplicate_scene(scene):
    """Clone scene clips/composition into a new scene at the end."""
    r = _root()
    if r is None:
        return False
    scene = int(scene)
    n = _num_scenes()
    if scene < 1 or scene > n:
        return False
    if n >= MAX_SCENES:
        print('Max scenes ({}) reached'.format(MAX_SCENES))
        return False
    try:
        _remember_scene_grid_dims(scene)
    except Exception:
        pass
    src_dims = dict(_scene_grid_dims(scene))
    new_scene = n + 1
    _set_scene_grid_dims(new_scene, src_dims.get('num_layers'), src_dims.get('num_cols'))
    try:
        r.par.Numscenes = new_scene
        r.par.Activescene = new_scene
    except Exception:
        pass
    _copy_scene_data(scene, new_scene)
    try:
        _copy_global_fx_scene(scene, new_scene)
        _activate_global_fx_scene(new_scene, remember_current=False)
    except Exception:
        pass
    switch_scene(new_scene)
    print('Duplicated scene {} -> scene {}'.format(scene, new_scene))
    return True


def delete_scene(scene):
    """Remove a scene and renumber scenes/matrix rows."""
    r = _root()
    if r is None:
        return False
    scene = int(scene)
    n = _num_scenes()
    if n <= MIN_SCENES:
        print('At least {} scene required'.format(MIN_SCENES))
        return False
    if scene < 1 or scene > n:
        return False
    active = _active_scene()
    try:
        _remember_scene_grid_dims(active)
    except Exception:
        pass
    _purge_scene_from_table(_table(), scene)
    _purge_scene_from_table(_comp_table(), scene)
    _shift_scene_grid_dims(scene)
    try:
        _delete_global_fx_scene(scene)
    except Exception:
        pass
    new_n = n - 1
    if scene == active:
        new_active = max(1, scene - 1)
    elif scene < active:
        new_active = active - 1
    else:
        new_active = active
    try:
        r.par.Numscenes = new_n
        r.par.Activescene = max(1, min(new_n, new_active))
    except Exception:
        pass
    try:
        _activate_global_fx_scene(new_active, remember_current=False)
    except Exception:
        pass
    switch_scene(max(1, min(new_n, new_active)))
    print('Deleted scene {} ({} scenes)'.format(scene, new_n))
    return True


def _remap_scene_tables(old_to_new):
    """Rewrite scene column in clip_matrix + comp_matrix."""
    _ensure_matrix_schema()
    tbl = _table()
    if tbl is not None:
        for i in range(1, tbl.numRows):
            try:
                old = int(tbl[i, 'scene'])
                if old in old_to_new:
                    tbl[i, 'scene'] = old_to_new[old]
            except Exception:
                pass
    comp = _comp_table()
    if comp is not None:
        for i in range(1, comp.numRows):
            try:
                old = int(comp[i, 'scene'])
                if old in old_to_new:
                    comp[i, 'scene'] = old_to_new[old]
            except Exception:
                pass


def _remap_scene_grid_dims(old_to_new):
    new_dims = {}
    for old_s, new_s in old_to_new.items():
        key = str(old_s)
        if key in _SCENE_GRID_DIMS:
            new_dims[str(new_s)] = dict(_SCENE_GRID_DIMS[key])
    _SCENE_GRID_DIMS.clear()
    _SCENE_GRID_DIMS.update(new_dims)


def move_scene(from_scene, to_scene):
    """Drag-reorder: move from_scene to the slot before to_scene."""
    r = _root()
    if r is None:
        return False
    from_scene, to_scene = int(from_scene), int(to_scene)
    if from_scene == to_scene:
        return False
    n = _num_scenes()
    if from_scene < 1 or from_scene > n or to_scene < 1 or to_scene > n:
        return False
    order = list(range(1, n + 1))
    order.remove(from_scene)
    order.insert(order.index(to_scene), from_scene)
    old_to_new = {old: i + 1 for i, old in enumerate(order)}
    active = _active_scene()
    try:
        _remember_scene_grid_dims(active)
    except Exception:
        pass
    _remap_scene_tables(old_to_new)
    _remap_scene_grid_dims(old_to_new)
    try:
        _remap_global_fx_scenes(old_to_new)
    except Exception:
        pass
    new_active = old_to_new.get(active, active)
    try:
        r.par.Activescene = new_active
    except Exception:
        pass
    try:
        _activate_global_fx_scene(new_active, remember_current=False)
    except Exception:
        pass
    switch_scene(new_active)
    print('Scene {} is now scene {}'.format(from_scene, old_to_new[from_scene]))
    return True


def _repair_scene_dragdrop(btn, bar):
    """Enable drag-reorder on scene number tiles."""
    if btn is None or bar is None:
        return
    cb = bar.op('scene_dragdrop')
    if cb is None:
        return
    try:
        btn.par.builtindrop = False
        btn.par.clickthrough = False
        btn.par.drag = 'usecallbacks'
        btn.par.drop = 'usecallbacks'
        btn.par.dragdropcallbacks = cb
    except Exception:
        pass
    txt = btn.op('label_text')
    if txt is not None:
        try:
            txt.par.clickthrough = True
            txt.par.drop = 'dropparent'
            txt.par.drag = 'dragno'
        except Exception:
            pass


def _repair_scene_bar_dragdrop(bar):
    if bar is None:
        return
    for ch in bar.children:
        if not ch.isCOMP:
            continue
        if ch.name.startswith('scene_btn_'):
            _repair_scene_dragdrop(ch, bar)


def _style_transport_icon(txt, w, h, glyph, button_name=None):
    w = max(8, int(SCENE_BTN_W))
    h = max(8, int(SCENE_BTN_H))
    txt.par.text = glyph or ''
    txt.par.resolutionw = w
    txt.par.resolutionh = h
    txt.par.bgalpha = 0.0
    txt.par.alignx = 'center'
    txt.par.aligny = 'center'
    try:
        txt.par.fontautosize = 'off'
        txt.par.fontsizex = TRANSPORT_ICON_FONT_SIZE
        txt.par.fontsizey = TRANSPORT_ICON_FONT_SIZE
        txt.par.keepfontratio = True
        txt.par.fontcolorr = 1.0
        txt.par.fontcolorg = 1.0
        txt.par.fontcolorb = 1.0
        txt.par.textoffsetx = 0
        txt.par.textoffsety = 0
        if button_name == 'scene_play' or glyph == TRANSPORT_ICON_PLAY:
            txt.par.textoffsetx = 1
        for font_name in (TD_FONT, 'Segoe UI Symbol', 'Arial Unicode MS'):
            try:
                txt.par.font = font_name
                break
            except Exception:
                continue
    except Exception:
        _apply_grid_font(txt)
    try:
        txt.cook(force=True)
    except Exception:
        pass


def _transport_button_glyph(name):
    if name == 'scene_to_start':
        return TRANSPORT_ICON_TO_START
    if name == 'scene_play':
        return TRANSPORT_ICON_PLAY
    if name == 'scene_pause':
        return TRANSPORT_ICON_PAUSE
    return ''


def _style_scene_tile_text(txt, label=''):
    """Text sized to the square tile — avoids topfill stretch / squashed glyphs."""
    if txt is None:
        return
    w = max(8, int(SCENE_BTN_W))
    h = max(8, int(SCENE_BTN_H))
    try:
        txt.par.text = str(label)
        txt.par.resolutionw = w
        txt.par.resolutionh = h
        txt.par.font = TD_FONT
        txt.par.fontautosize = 'off'
        txt.par.fontsizex = GRID_FONT_SIZE
        txt.par.fontsizey = GRID_FONT_SIZE
        txt.par.keepfontratio = True
        txt.par.bgalpha = 0.0
        txt.par.alignx = 'center'
        txt.par.aligny = 'center'
        try:
            txt.par.textoffsetx = 0
            txt.par.textoffsety = 0
        except Exception:
            pass
        txt.cook(force=True)
    except Exception:
        pass


def _apply_scene_tile_top(btn, txt=None):
    """Letterbox tile content at native aspect (no squash)."""
    if btn is None:
        return
    try:
        if txt is not None:
            btn.par.top = txt
        btn.par.topfill = SCENE_BTN_TOPFILL
    except Exception:
        pass


def _apply_scene_control_bg(btn, is_active=False):
    """Tile behind play/pause and scene numbers; brighter when active."""
    if btn is None:
        return
    try:
        btn.par.bgalpha = SCENE_CONTROL_TILE_ALPHA
        if is_active:
            btn.par.bgcolorr, btn.par.bgcolorg, btn.par.bgcolorb = TD_SLIDER_FILL
        else:
            btn.par.bgcolorr, btn.par.bgcolorg, btn.par.bgcolorb = SCENE_BTN_TILE_BG
    except Exception:
        pass


def _apply_transport_btn_style(btn, is_active=False):
    """Transport tile: brighter panel bg when that control is active."""
    _apply_scene_control_bg(btn, is_active=bool(is_active))
    _apply_scene_tile_top(btn)


def _timeline_at_start(epsilon=0.75):
    t = None
    try:
        t = _td_timeline()
    except Exception:
        t = None
    if t is None:
        return False
    try:
        return abs(float(t.frame) - float(t.start)) <= float(epsilon)
    except Exception:
        try:
            return abs(float(t.frame) - 1.0) <= float(epsilon)
        except Exception:
            return False


def _active_transport_button_name():
    """Which transport control should read as selected."""
    if global_transport_playing():
        return 'scene_play'
    if _timeline_at_start():
        return 'scene_to_start'
    return 'scene_pause'


def _sync_transport_button_states(bar=None):
    """Highlight rewind / play / pause so the active transport state is obvious."""
    if bar is None:
        r = _root()
        bar = r.op('ui/scene_bar') if r else None
    if bar is None:
        return
    active = _active_transport_button_name()
    for name in SCENE_TRANSPORT_BUTTONS:
        btn = bar.op(name)
        if btn is None:
            continue
        _apply_transport_btn_style(btn, is_active=(name == active))


def _create_scene_transport_button(parent, name, label=None):
    btn = parent.op(name)
    if btn is None:
        btn = parent.create('containerCOMP', name)
    try:
        btn.par.w = SCENE_BTN_W
        btn.par.h = SCENE_BTN_H
        btn.par.hmode = 'fixed'
        btn.par.vmode = 'fixed'
        btn.par.drop = 'dropno'
        btn.par.drag = 'dragno'
    except Exception:
        pass
    txt = btn.op('label_text')
    if txt is None:
        txt = btn.create('textTOP', 'label_text')
    try:
        txt.par.clickthrough = True
    except Exception:
        pass
    if _wire_transport_button_icon(btn, name):
        _layout_transport_icon_view(btn)
    else:
        glyph = label if label else _transport_button_glyph(name)
        _style_transport_icon(txt, SCENE_BTN_W, SCENE_BTN_H, glyph, button_name=name)
        try:
            _apply_scene_tile_top(btn, txt)
            btn.par.clickthrough = False
        except Exception:
            pass
    _apply_transport_btn_style(btn, is_active=False)
    return btn


def _apply_scene_btn_style(btn, is_active):
    if btn is None:
        return
    _apply_scene_control_bg(btn, is_active=is_active)
    txt = btn.op('label_text')
    if txt is None:
        return
    try:
        if is_active:
            txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = SCENE_ACTIVE_TEXT
            txt.par.bgalpha = 0.0
        else:
            txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = SCENE_IDLE_TEXT
            txt.par.bgalpha = 0.0
        txt.cook(force=True)
    except Exception:
        pass


def _create_scene_button(parent, scene_idx):
    btn = parent.create('containerCOMP', 'scene_btn_{}'.format(scene_idx))
    try:
        btn.par.w = SCENE_BTN_W
        btn.par.h = SCENE_BTN_H
        btn.par.hmode = 'fixed'
        btn.par.vmode = 'fixed'
        btn.par.drop = 'dropno'
        btn.par.drag = 'dragno'
    except Exception:
        pass
    txt = btn.op('label_text')
    if txt is None:
        txt = btn.create('textTOP', 'label_text')
    _style_scene_tile_text(txt, str(scene_idx))
    try:
        txt.par.clickthrough = True
    except Exception:
        pass
    _apply_scene_tile_top(btn, txt)
    _apply_scene_btn_style(btn, scene_idx == _active_scene())
    bar = parent if getattr(parent, 'name', '') == 'scene_bar' else parent.op('scene_bar')
    _repair_scene_dragdrop(btn, bar if bar is not None else parent)
    return btn


def _create_scene_add_button(parent):
    btn = parent.create('containerCOMP', 'scene_add')
    try:
        btn.par.w = SCENE_BTN_W
        btn.par.h = SCENE_BTN_H
        btn.par.hmode = 'fixed'
        btn.par.vmode = 'fixed'
        btn.par.drop = 'dropno'
        btn.par.drag = 'dragno'
    except Exception:
        pass
    txt = btn.op('label_text')
    if txt is None:
        txt = btn.create('textTOP', 'label_text')
    _style_scene_tile_text(txt, '+')
    _apply_scene_tile_top(btn, txt)
    _apply_scene_control_bg(btn, is_active=False)
    return btn


EFFECTS_FOLDER_BTN_W = 168
EFFECTS_FOLDER_BTN_GAP = 12


def _style_scene_bar_label_button(txt, label, w, h):
    if txt is None:
        return
    w = max(32, int(w))
    h = max(8, int(h))
    try:
        txt.par.text = str(label)
        txt.par.resolutionw = w
        txt.par.resolutionh = h
        txt.par.font = TD_FONT
        txt.par.fontautosize = 'off'
        txt.par.fontsizex = GRID_FONT_SIZE
        txt.par.fontsizey = GRID_FONT_SIZE
        txt.par.keepfontratio = True
        txt.par.bgalpha = 0.0
        txt.par.alignx = 'center'
        txt.par.aligny = 'center'
        txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = SCENE_IDLE_TEXT
        txt.cook(force=True)
    except Exception:
        pass


def _ensure_open_effects_folder_button(bar):
    if bar is None:
        return None
    btn = bar.op('open_effects_folder')
    if btn is None:
        btn = bar.create('containerCOMP', 'open_effects_folder')
    try:
        btn.par.w = EFFECTS_FOLDER_BTN_W
        btn.par.h = SCENE_BTN_H
        btn.par.hmode = 'fixed'
        btn.par.vmode = 'fixed'
        btn.par.drop = 'dropno'
        btn.par.drag = 'dragno'
        btn.par.display = True
        btn.par.enable = True
        btn.par.clickthrough = False
    except Exception:
        pass
    txt = btn.op('label_text')
    if txt is None:
        txt = btn.create('textTOP', 'label_text')
    _style_scene_bar_label_button(txt, 'Open Effects Folder', EFFECTS_FOLDER_BTN_W, SCENE_BTN_H)
    try:
        txt.par.clickthrough = True
    except Exception:
        pass
    _apply_scene_tile_top(btn, txt)
    _apply_scene_control_bg(btn, is_active=False)
    return btn


def _layout_open_effects_folder_button(bar):
    if bar is None:
        return
    btn = _ensure_open_effects_folder_button(bar)
    if btn is None:
        return
    try:
        btn.par.x = max(0, _perf_readouts_x0() - EFFECTS_FOLDER_BTN_W - EFFECTS_FOLDER_BTN_GAP)
        btn.par.y = SCENE_BAR_CONTENT_Y
        btn.par.w = EFFECTS_FOLDER_BTN_W
        btn.par.h = SCENE_BTN_H
        btn.par.display = True
    except Exception:
        pass


def _ensure_scene_label(parent):
    label = parent.op('scene_label')
    if label is None:
        label = parent.create('containerCOMP', 'scene_label')
    try:
        label.par.w = 48
        label.par.h = SCENE_BTN_H
        label.par.hmode = 'fixed'
        label.par.vmode = 'fixed'
        label.par.drop = 'dropno'
        label.par.drag = 'dragno'
        label.par.clickthrough = True
        label.par.bgcolorr, label.par.bgcolorg, label.par.bgcolorb = 0, 0, 0
        label.par.bgalpha = 0
    except Exception:
        pass
    txt = label.op('label_text')
    if txt is None:
        txt = label.create('textTOP', 'label_text')
    try:
        txt.par.resolutionw = 48
        txt.par.resolutionh = SCENE_BTN_H
        txt.par.keepfontratio = True
    except Exception:
        pass
    _style_header_text(txt, 48, SCENE_BTN_H, 'Scene')
    try:
        txt.par.clickthrough = True
        label.par.top = txt
        label.par.topfill = SCENE_BTN_TOPFILL
    except Exception:
        pass
    return label


def _ensure_scene_bar():
    r = _root()
    ui = r.op('ui') if r else None
    if ui is None:
        return None
    bar = ui.op('scene_bar')
    if bar is None:
        bar = ui.create('containerCOMP', 'scene_bar')
        try:
            bar.par.x = 0
            bar.par.y = 0
            bar.par.w = UI_W
            bar.par.h = SCENE_BAR_H
            bar.par.hmode = 'fixed'
            bar.par.vmode = 'fixed'
            bar.par.align = 'none'
            bar.par.drop = 'dropno'
            bar.par.drag = 'dragno'
            bar.par.bgalpha = SCENE_BAR_BG_ALPHA
        except Exception:
            pass
    n = _num_scenes()
    for s in range(1, n + 1):
        btn = bar.op('scene_btn_{}'.format(s))
        if btn is None:
            _create_scene_button(bar, s)
    for s in range(n + 1, MAX_SCENES + 1):
        btn = bar.op('scene_btn_{}'.format(s))
        if btn is not None:
            try:
                btn.par.display = False
            except Exception:
                pass
    if bar.op('scene_add') is None:
        _create_scene_add_button(bar)
    for tname in SCENE_TRANSPORT_BUTTONS:
        if bar.op(tname) is None:
            _create_scene_transport_button(bar, tname)
    _ensure_scene_bpm(bar)
    _ensure_scene_label(bar)
    _ensure_scene_logo(bar)
    _ensure_open_effects_folder_button(bar)
    _ensure_perf_readouts(bar)
    try:
        _ensure_audio_toggle_button(bar)
    except Exception:
        pass
    _layout_scene_bar()
    try:
        bar.par.bgalpha = SCENE_BAR_BG_ALPHA
    except Exception:
        pass
    try:
        bar.par.y = UI_H - SCENE_BAR_H - SCENE_BAR_TOP_PAD
    except Exception:
        pass
    return bar


def _layout_scene_bar():
    r = _root()
    ui = r.op('ui') if r else None
    bar = ui.op('scene_bar') if ui else None
    if bar is None:
        return
    try:
        bar.par.display = True
        bar.par.x = 0
        bar.par.w = UI_W
        bar.par.h = SCENE_BAR_H
    except Exception:
        pass
    _layout_scene_logo(bar)
    x = _scene_bar_controls_x0()
    for name in SCENE_TRANSPORT_BUTTONS:
        btn = bar.op(name)
        if btn is None:
            continue
        try:
            btn.par.display = True
            btn.par.x = x
            btn.par.y = SCENE_BAR_CONTENT_Y
            btn.par.w = SCENE_BTN_W
            btn.par.h = SCENE_BTN_H
        except Exception:
            pass
        if not _wire_transport_button_icon(btn, name):
            txt = btn.op('label_text')
            if txt is not None:
                _style_transport_icon(txt, SCENE_BTN_W, SCENE_BTN_H, _transport_button_glyph(name), button_name=name)
            try:
                if txt is not None:
                    _apply_scene_tile_top(btn, txt)
            except Exception:
                pass
        else:
            _layout_transport_icon_view(btn)
        x += SCENE_BTN_W + 4
    _sync_transport_button_states(bar)
    try:
        bar.par.bgalpha = SCENE_BAR_BG_ALPHA
    except Exception:
        pass
    x = _layout_scene_bpm(bar, x)
    scene_label = _ensure_scene_label(bar)
    try:
        scene_label.par.display = True
        scene_label.par.x = x
        scene_label.par.y = SCENE_BAR_CONTENT_Y
        scene_label.par.w = 48
        scene_label.par.h = SCENE_BTN_H
    except Exception:
        pass
    txt = scene_label.op('label_text') if scene_label is not None else None
    if txt is not None:
        try:
            txt.par.resolutionw = 48
            txt.par.resolutionh = SCENE_BTN_H
            txt.par.keepfontratio = True
        except Exception:
            pass
        _style_header_text(txt, 48, SCENE_BTN_H, 'Scene')
        try:
            scene_label.par.topfill = SCENE_BTN_TOPFILL
        except Exception:
            pass
    x += 48 + 8
    active = _active_scene()
    n = _num_scenes()
    for s in range(1, n + 1):
        btn = bar.op('scene_btn_{}'.format(s))
        if btn is None:
            continue
        try:
            btn.par.display = True
            btn.par.x = x
            btn.par.y = SCENE_BAR_CONTENT_Y
            btn.par.w = SCENE_BTN_W
            btn.par.h = SCENE_BTN_H
        except Exception:
            pass
        txt = btn.op('label_text')
        if txt is not None:
            _style_scene_tile_text(txt, str(s))
            _apply_scene_tile_top(btn, txt)
        _apply_scene_btn_style(btn, s == active)
        x += SCENE_BTN_W + 4
    add = bar.op('scene_add')
    if add is not None:
        try:
            add.par.display = True
            add.par.x = x
            add.par.y = SCENE_BAR_CONTENT_Y
            add.par.w = SCENE_BTN_W
            add.par.h = SCENE_BTN_H
            _apply_scene_control_bg(add, is_active=False)
        except Exception:
            pass
        txt = add.op('label_text')
        if txt is not None:
            _style_scene_tile_text(txt, '+')
            _apply_scene_tile_top(add, txt)
    _layout_open_effects_folder_button(bar)
    _layout_perf_readouts(bar)
    _update_perf_readouts()


def _refresh_scene_bar():
    _ensure_scene_bar()
    _layout_scene_bar()
    r = _root()
    bar = r.op('ui/scene_bar') if r else None
    if bar is not None:
        _repair_scene_bar_dragdrop(bar)
    _refresh_panel_exec_panels()


def _rewire_scene_slots():
    """Sync slot chains to clip_matrix for the active scene (for thumbnails + playback)."""
    for layer in range(1, _num_layers() + 1):
        for col in range(1, _num_cols() + 1):
            slot = _slot(layer, col)
            if slot is None:
                continue
            _ensure_slot_chain(slot, layer)
            ctype, path = _get(layer, col)
            if not path or not _valid_clip_type(ctype):
                _reset_slot_media(layer, col)
                continue
            if ctype == 'video':
                _wire_video(slot, path, play=False)
            else:
                _wire_tox(slot, path, layer, col)


def switch_scene(scene_idx):
    r = _root()
    if r is None:
        return False
    prev_scene = None
    try:
        prev_scene = int(float(r.par.Activescene.eval()))
        _remember_scene_grid_dims(prev_scene)
    except Exception:
        pass
    if prev_scene is not None:
        _cache_scene_cell_params(prev_scene)
        try:
            _remember_active_global_fx_scene(prev_scene)
        except Exception:
            pass
    scene_idx = max(1, min(_num_scenes(), int(scene_idx)))
    try:
        r.par.Activescene = scene_idx
    except Exception:
        pass
    _apply_scene_grid_dims(scene_idx)
    col = 1
    try:
        col = int(float(r.par.Activecolumn.eval())) or 1
    except Exception:
        pass
    _rewire_scene_slots()
    _restore_scene_cell_params(scene_idx)
    _rebuild_composition()
    try:
        _activate_global_fx_scene(scene_idx, remember_current=False)
    except Exception:
        pass
    _refresh_scene_bar()
    _sync_grid_ui()
    try:
        layer = int(float(r.par.Selectedlayer.eval()))
        col = int(float(r.par.Selectedcol.eval()))
        _update_cell_params_ui(layer, col)
    except Exception:
        pass
    print('Scene {}'.format(scene_idx))
    return True


def _iter_loaded_cells():
    """Every grid cell with a loaded clip (for global transport)."""
    for layer in range(1, _num_layers() + 1):
        for col in range(1, _num_cols() + 1):
            ctype, path = _get(layer, col)
            if path and _valid_clip_type(ctype):
                yield int(layer), int(col), str(ctype)


def _current_frame_index():
    try:
        return int(absTime.frame)
    except Exception:
        pass
    try:
        t = _td_timeline()
        if t is not None:
            return int(t.frame)
    except Exception:
        pass
    return 0


def _cell_should_cook_now(layer, col, live, playing):
    if not live or not playing:
        return False
    ctype, path = _cell_content(layer, col)
    if not path or not _valid_clip_type(ctype):
        return False
    if _cell_frozen(layer, col):
        return False
    rate = _cell_update_rate(layer, col)
    if rate <= 1:
        return True
    return (_current_frame_index() % int(rate)) == 0


def _cell_video_should_play(layer, col, live, playing):
    """Movie decode must stay on while live+transport; independent of update-rate throttle."""
    if not live or not playing:
        return False
    ctype, path = _cell_content(layer, col)
    if not path or str(ctype).strip().lower() != 'video':
        return False
    if _cell_frozen(layer, col):
        return False
    return True


def _sync_layer_slot_pause_states(force_full=False):
    """Route live column slots; timeline play/pause is TouchDesigner project transport."""
    global _LAST_LIVE_SLOT_COLS
    playing = global_transport_playing()
    for layer in range(1, _num_layers() + 1):
        src_col = _get_layer_src_col(layer)
        play_cols = _xfade_play_cols_for_layer(layer, src_col)
        layer_comp = _layer(layer)
        if layer_comp is None:
            continue
        if force_full:
            prev_cols = set(range(1, _num_cols() + 1))
        elif int(layer) in _LAST_LIVE_SLOT_COLS:
            prev_cols = set(_LAST_LIVE_SLOT_COLS.get(int(layer), set()))
        else:
            prev_cols = set(range(1, _num_cols() + 1))
        update_cols = prev_cols | set(play_cols)
        for c in sorted(update_cols):
            if c < 1 or c > _num_cols():
                continue
            slot = layer_comp.op('col_{}'.format(c))
            live = c in play_cols
            if live and _cell_frozen(layer, c):
                ctype, _path = _cell_content(layer, c)
                _route_slot_frozen(slot, True, ctype, capture=False)
                continue
            should_cook = _cell_should_cook_now(layer, c, live, playing)
            video_play = _cell_video_should_play(layer, c, live, playing)
            v = slot.op('video') if slot else None
            ctype, _path = _cell_content(layer, c)
            keep_loaded_tox = _tox_cell_keep_cooking(layer, c, ctype, _path, live, slot)
            if v is not None and _video_timeline_locked(v):
                _set_video_active(v, video_play)
                t = slot.op('tox')
                if t is not None:
                    if _is_logo_overlay_tox(t):
                        _keep_logo_overlay_slot_cooking(slot)
                    else:
                        try:
                            t.allowCooking = bool(should_cook or keep_loaded_tox)
                        except Exception:
                            pass
            else:
                if ctype == 'video' and v is not None:
                    _set_video_active(v, video_play)
                    t = slot.op('tox')
                    if t is not None:
                        if _is_logo_overlay_tox(t):
                            _keep_logo_overlay_slot_cooking(slot)
                        else:
                            try:
                                t.allowCooking = bool(should_cook or keep_loaded_tox)
                            except Exception:
                                pass
                else:
                    _pause_slot(
                        slot,
                        on=should_cook,
                        keep_tox_cooking=keep_loaded_tox,
                        clip_type=ctype,
                    )
        _LAST_LIVE_SLOT_COLS[int(layer)] = set(play_cols)


def _tick_cell_performance_controls():
    if _xfade_root_stack_active():
        return
    _sync_layer_slot_pause_states()


def _resume_live_transport_slots():
    """Re-assert movie play on live composition slots after routing/rebuild churn."""
    if not global_transport_playing():
        return False
    touched = False
    seen = set()
    for layer in range(1, _num_layers() + 1):
        col = int(_get_layer_src_col(layer))
        if not _video_slot_should_play(layer, col):
            continue
        key = (int(layer), col)
        if key in seen:
            continue
        seen.add(key)
        ctype, path = _cell_content(layer, col)
        if str(ctype).strip().lower() != 'video' or not path:
            continue
        if _play_slot(layer, col, resume=True):
            touched = True
    _sync_layer_slot_pause_states(force_full=True)
    return touched


def _play_slot(layer, col, resume=False):
    layer, col = int(layer), int(col)
    slot = _slot(layer, col)
    if slot is None:
        return False
    ctype, path = _get(layer, col)
    if not path or not _valid_clip_type(ctype):
        return False
    _ensure_slot_chain(slot, layer)
    if ctype == 'video':
        _wire_video(slot, path, play=True, resume=resume)
    else:
        _wire_tox(slot, path, layer, col)
        _pause_slot(slot, on=True, keep_tox_cooking=True, clip_type='tox')
    pick = slot.op('pick')
    if pick is not None:
        pick.par.index = 1 if ctype == 'video' else 2
    return True


def play_column(col=None):
    """Start TouchDesigner project timeline; refresh live grid slots."""
    r = _root()
    if r is None:
        return False
    try:
        reconcile_orphan_map_binds()
    except Exception:
        pass
    _set_global_transport_playing(True)
    if col is not None:
        col = max(1, min(_num_cols(), int(col)))
        for layer in range(1, _num_layers() + 1):
            _play_slot(layer, col, resume=True)
    else:
        for layer, c, _ctype in _iter_loaded_cells():
            if _video_slot_should_play(layer, c):
                _play_slot(layer, c, resume=True)
    _sync_layer_slot_pause_states(force_full=True)
    try:
        if _grid_osc_active():
            def _after_grid_osc_play():
                if global_transport_playing():
                    _resume_live_transport_slots()
            _defer_run(_after_grid_osc_play, delayFrames=1)
    except Exception:
        pass
    print('Play (TouchDesigner timeline)')
    try:
        _sync_transport_button_states()
    except Exception:
        pass
    return True


def pause_column(col=None):
    """Pause TouchDesigner project timeline; keep live slots on current frame."""
    r = _root()
    if r is None:
        return False
    _set_global_transport_playing(False)
    try:
        _snap_xfades_for_pause()
    except Exception:
        pass
    _sync_layer_slot_pause_states(force_full=True)
    try:
        refresh_map_control_display()
    except Exception:
        pass
    print('Pause (TouchDesigner timeline)')
    try:
        _sync_transport_button_states()
    except Exception:
        pass
    return True


def add_scene():
    r = _root()
    if r is None:
        return False
    n = _num_scenes()
    if n >= MAX_SCENES:
        print('Max scenes ({}) reached'.format(MAX_SCENES))
        return False
    try:
        _remember_scene_grid_dims(_active_scene())
    except Exception:
        pass
    old_scene = int(_active_scene())
    try:
        _remember_active_global_fx_scene(old_scene)
    except Exception:
        pass
    _set_scene_grid_dims(n + 1, DEFAULT_LAYERS, 30)
    try:
        r.par.Numscenes = n + 1
        r.par.Activescene = n + 1
    except Exception:
        pass
    try:
        _activate_global_fx_scene(n + 1, remember_current=False)
    except Exception:
        pass
    _apply_scene_grid_dims(n + 1)
    for layer in range(1, MAX_LAYERS + 1):
        for c in range(1, _num_cols() + 1):
            _reset_slot_media(layer, c)
    _refresh_scene_bar()
    col = 1
    try:
        col = int(float(r.par.Activecolumn.eval())) or 1
    except Exception:
        pass
    _rebuild_column_chain(col, adopt=False)
    _sync_grid_ui()
    _update_cell_params_ui()
    print('Added scene {} ({} scenes)'.format(n + 1, n + 1))
    return True


def _transfer_cell(from_layer, from_col, to_layer, to_col, skip_evict=None):
    from_layer, from_col = int(from_layer), int(from_col)
    to_layer, to_col = int(to_layer), int(to_col)
    if from_layer == to_layer and from_col == to_col:
        return
    ct, path = _cell_content(from_layer, from_col)
    par_state = _snapshot_cell_params(from_layer, from_col, ct) if path else []
    render_scale = _cell_render_scale(from_layer, from_col) if path else 100
    update_rate = _cell_update_rate(from_layer, from_col) if path else 1
    frozen = _cell_frozen(from_layer, from_col) if path else False
    cell_fx = snapshot_cell_fx(from_layer, from_col) if path else []
    map_control = snapshot_cell_map_control(from_layer, from_col) if path else {}
    clear_cell(to_layer, to_col)
    if path:
        if skip_evict is None:
            skip = [(from_layer, from_col), (to_layer, to_col)]
        else:
            skip = list(skip_evict)
        load_cell(
            to_layer, to_col, ct, path,
            skip_evict=skip,
            par_state=par_state,
            auto_add_fx_row=False,
        )
        set_cell_render_scale(to_layer, to_col, render_scale)
        set_cell_update_rate(to_layer, to_col, update_rate)
        set_cell_frozen(to_layer, to_col, frozen)
        restore_cell_fx(to_layer, to_col, cell_fx)
        restore_cell_map_control(
            to_layer, to_col, map_control,
            src_layer=from_layer, src_col=from_col,
        )
    clear_cell(from_layer, from_col)
    if path:
        try:
            _finalize_cell_move_map_and_video(
                (from_layer, from_col),
                (to_layer, to_col),
                moved_type=ct,
                swapped=False,
            )
        except Exception:
            pass
