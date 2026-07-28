def _root():
    return parent()


def _num_layers():
    r = _root()
    if r is None:
        return DEFAULT_LAYERS
    try:
        n = int(float(r.par.Numlayers.eval()))
    except Exception:
        n = DEFAULT_LAYERS
    return max(MIN_LAYERS, min(MAX_LAYERS, n))


def _base_layer():
    return _num_layers()


def _table():
    tbl = _root().op('clip_matrix')
    _ensure_matrix_schema(tbl)
    return tbl


def _comp_table():
    """Per-layer column cell that feeds the live composition."""
    r = _root()
    if r is None:
        return None
    tbl = r.op('comp_matrix') or r.op('chain_matrix')
    if tbl is None:
        tbl = r.create('tableDAT', 'comp_matrix')
    else:
        try:
            tbl.name = 'comp_matrix'
        except Exception:
            pass
    _ensure_comp_schema(tbl)
    return tbl


def _ensure_comp_schema(tbl=None):
    if tbl is None:
        tbl = _root().op('comp_matrix') if _root() else None
        if tbl is None:
            tbl = _root().op('chain_matrix') if _root() else None
    if tbl is None:
        return
    if tbl.numRows < 1:
        tbl.appendRow(['scene', 'layer', 'src_col'])
        return
    try:
        headers = [str(tbl[0, c]) for c in range(tbl.numCols)]
    except Exception:
        return
    if headers == ['scene', 'layer', 'src_col']:
        return
    tbl.clear()
    tbl.appendRow(['scene', 'layer', 'src_col'])


def _active_column():
    r = _root()
    try:
        return max(1, min(_num_cols(), int(float(r.par.Activecolumn.eval())) or 1))
    except Exception:
        return 1


def _find_comp(layer, scene=None):
    scene = _active_scene() if scene is None else int(scene)
    tbl = _comp_table()
    if tbl is None:
        return None
    layer = int(layer)
    for i in range(1, tbl.numRows):
        if int(tbl[i, 'scene']) == scene and int(tbl[i, 'layer']) == layer:
            return i
    return None


def _get_layer_src_col(layer, scene=None):
    """Which column this layer reads from in the live composition."""
    layer = int(layer)
    idx = _find_comp(layer, scene=scene)
    if idx is not None:
        return int(_comp_table()[idx, 'src_col'])
    return _active_column()


def _set_layer_src_col(layer, col, scene=None):
    layer, col = int(layer), int(col)
    scene = _active_scene() if scene is None else int(scene)
    tbl = _comp_table()
    if tbl is None:
        return
    row = [scene, layer, col]
    idx = _find_comp(layer, scene=scene)
    if idx is None:
        tbl.appendRow(row)
    else:
        for j, v in enumerate(row):
            tbl[idx, j] = v


def _clear_layer_src_col(layer, scene=None):
    tbl = _comp_table()
    if tbl is None:
        return
    idx = _find_comp(layer, scene=scene)
    if idx is not None:
        tbl.deleteRow(idx)


def _is_composition_cell(layer, col, scene=None):
    return int(col) == _get_layer_src_col(layer, scene=scene)


def _col_used_in_composition(col, scene=None):
    col = int(col)
    for layer in range(1, _num_layers() + 1):
        if _get_layer_src_col(layer, scene=scene) == col:
            return True
    return False


def _refresh_composition_for_cols(cols):
    """Update live playback for columns already in the mix; do not change active column."""
    try:
        need = {int(c) for c in cols if c is not None}
    except Exception:
        need = set()
    if not need or not any(_col_used_in_composition(c) for c in need):
        return
    _rebuild_composition()
    _refresh_ui()


def composition_assign_layer_cell(layer, col, toggle=False):
    """Assign this layer row to play the clip in (layer, col). Shift+click toggles off."""
    layer, col = int(layer), int(col)
    set_params_tab('layer')
    r = _root()
    if r is not None:
        try:
            r.par.Activelayer = layer
            r.par.Selectedlayer = layer
            r.par.Selectedcol = col
        except Exception:
            pass
    try:
        sync_map_control_context(r)
    except Exception:
        pass
    def _apply():
        cur = _get_layer_src_col(layer)
        if toggle and cur == col:
            _clear_layer_src_col(layer)
        else:
            _set_layer_src_col(layer, col)
        _rebuild_composition()
    from_col = _get_layer_src_col(layer)
    if toggle and from_col == col:
        _apply()
    elif (not toggle) and from_col == col:
        if global_transport_playing():
            _resume_live_transport_slots()
    elif _cell_xfade_enabled() and _xfade_allowed() and from_col != col:
        _begin_layer_col_xfade(layer, from_col, col, _apply)
    else:
        _apply()
    if not _grid_osc_routing_active():
        _refresh_ui()
        _update_cell_params_ui(layer, col)
        _open_output()
    print('{} -> col {}'.format(_layer_label(layer), col))


def _prime_column_before_switch(col, frames=0):
    """Wake the incoming column off-air without blocking the switch callback."""
    col = int(col)
    for layer in range(_num_layers(), 0, -1):
        try:
            _wake_cell_media_for_pending_xfade(layer, col)
        except Exception:
            pass
    if int(frames) <= 0:
        return
    for _ in range(int(frames)):
        for layer in range(_num_layers(), 0, -1):
            slot = _slot(layer, col)
            if slot is None:
                continue
            for name in ('tox', 'tox_fit', 'tox_pick', 'video', 'video_fit', 'pick', 'out1'):
                node = slot.op(name)
                if node is None:
                    continue
                try:
                    node.cook(force=True)
                except Exception:
                    pass


def _column_is_video_only(col):
    """Return True when every loaded cell in a non-empty column is video."""
    found = False
    for layer in range(1, _num_layers() + 1):
        ctype, path = _cell_content(layer, int(col))
        if not path:
            continue
        found = True
        if ctype != 'video':
            return False
    return found


def composition_select_column(col, previous_col=None):
    """All layers use this column, including explicit video-only crossfades."""
    col = int(col)
    try:
        prev_sig = tuple(_get_layer_src_col(layer) for layer in range(1, _num_layers() + 1))
    except Exception:
        prev_sig = ()
    try:
        light_param_focus = _cell_param_focus_mode() in ('off', 'double', 'delayed')
    except Exception:
        light_param_focus = False
    if all(int(_get_layer_src_col(layer)) == col for layer in range(1, _num_layers() + 1)):
        r = _root()
        if r is not None:
            try:
                r.par.Activecolumn = col
                r.par.Selectedcol = col
            except Exception:
                pass
        if global_transport_playing():
            _resume_live_transport_slots()
        if light_param_focus:
            try:
                _defer_midi_grid_selection_repaint(prev_sig)
            except Exception:
                pass
        return
    r = _root()
    prev_col = int(previous_col) if previous_col is not None else _get_layer_src_col(1)
    if _COLUMN_XFADE.get('active'):
        try:
            prev_col = int(_COLUMN_XFADE.get('to_col', prev_col))
            _finish_column_xfade(prev_col, _COLUMN_XFADE.get('from_col', prev_col))
        except Exception:
            pass
    if r is not None:
        try:
            r.par.Selectedcol = col
        except Exception:
            pass
    def _apply():
        if r is not None:
            try:
                r.par.Activecolumn = col
                r.par.Selectedcol = col
            except Exception:
                pass
        for layer in range(1, _num_layers() + 1):
            _set_layer_src_col(layer, col)
        _rebuild_composition()
        # The fade starter is deferred until incoming media is ready. Refresh
        # after applying the new composition so every row ring moves together.
        try:
            _refresh_ui(cols=(prev_col, col))
        except Exception:
            pass
    if _column_xfade_enabled() and _xfade_allowed():
        _schedule_column_xfade_when_ready(col, prev_col, _apply)
    else:
        _apply()
    if not _grid_osc_routing_active() and not light_param_focus:
        _refresh_ui()
        _open_output()
    elif light_param_focus:
        try:
            _defer_midi_grid_selection_repaint(prev_sig)
        except Exception:
            pass
    print('All layers -> col {}{}'.format(
        col,
        ' (video-only fade)' if _column_is_video_only(prev_col) and _column_is_video_only(col) else '',
    ))


def composition_reset_layer(layer):
    _clear_layer_src_col(int(layer))
    _rebuild_composition()
    _refresh_ui()
    print('{} reset to col {}'.format(_layer_label(layer), _get_layer_src_col(layer)))


def composition_reset_all(scene=None):
    tbl = _comp_table()
    if tbl is None or tbl.numRows < 2:
        return
    scene = _active_scene() if scene is None else int(scene)
    for i in range(tbl.numRows - 1, 0, -1):
        if int(tbl[i, 'scene']) == scene:
            tbl.deleteRow(i)
    col = _active_column()
    for layer in range(1, _num_layers() + 1):
        _set_layer_src_col(layer, col)
    _rebuild_composition()
    _refresh_ui()
    print('Composition reset — all layers col {}'.format(col))


def _composition_deps(scene=None):
    """All (layer, col) slots that must cook for the current composition."""
    deps = set()
    for layer in range(1, _num_layers() + 1):
        deps.add((layer, _get_layer_src_col(layer, scene=scene)))
    if _COLUMN_XFADE.get('active'):
        if _COLUMN_XFADE.get('mode') == 'layer_col':
            try:
                layer = int(_COLUMN_XFADE.get('layer', 0))
                deps.add((layer, int(_COLUMN_XFADE.get('from_col', 1))))
                deps.add((layer, int(_COLUMN_XFADE.get('to_col', 1))))
            except Exception:
                pass
        elif _COLUMN_XFADE.get('mode') == 'column_layers':
            for layer, (fc, tc) in _column_layers_fade_map().items():
                deps.add((int(layer), int(fc)))
                deps.add((int(layer), int(tc)))
        else:
            from_sig = tuple(_COLUMN_XFADE.get('from_sig') or ())
            to_sig = tuple(_COLUMN_XFADE.get('to_sig') or ())
            if from_sig:
                wire_from = _column_xfade_outgoing_sig(from_sig, to_sig)
                for layer, col in enumerate(wire_from, start=1):
                    try:
                        deps.add((layer, int(col)))
                    except Exception:
                        pass
            if to_sig:
                for layer, col in enumerate(to_sig, start=1):
                    try:
                        deps.add((layer, int(col)))
                    except Exception:
                        pass
    return deps


def _ensure_matrix_schema(tbl=None):
    if tbl is None:
        tbl = _root().op('clip_matrix') if _root() else None
    if tbl is None or tbl.numRows < 1:
        return
    try:
        headers = [str(tbl[0, c]) for c in range(tbl.numCols)]
    except Exception:
        return
    if 'scene' in headers:
        pass
    elif headers and headers[0] == 'layer':
        tbl.insertCol(0)
        tbl[0, 0] = 'scene'
        for i in range(1, tbl.numRows):
            tbl[i, 0] = 1
    elif tbl.numCols >= 5:
        tbl.insertCol(0)
        tbl[0, 0] = 'scene'
        for i in range(1, tbl.numRows):
            tbl[i, 0] = 1
    try:
        headers = [str(tbl[0, c]) for c in range(tbl.numCols)]
    except Exception:
        return
    if 'render_scale' not in headers:
        try:
            tbl.appendCol(['render_scale'] + ['100'] * max(0, tbl.numRows - 1))
        except Exception:
            try:
                tbl.appendCol()
                tbl[0, tbl.numCols - 1] = 'render_scale'
                for i in range(1, tbl.numRows):
                    tbl[i, tbl.numCols - 1] = '100'
            except Exception:
                pass
    try:
        headers = [str(tbl[0, c]) for c in range(tbl.numCols)]
    except Exception:
        return
    for col_name, default in (('update_rate', '1'), ('frozen', '0')):
        if col_name in headers:
            continue
        try:
            tbl.appendCol([col_name] + [default] * max(0, tbl.numRows - 1))
        except Exception:
            try:
                tbl.appendCol()
                tbl[0, tbl.numCols - 1] = col_name
                for i in range(1, tbl.numRows):
                    tbl[i, tbl.numCols - 1] = default
            except Exception:
                pass


def _num_scenes():
    r = _root()
    if r is None:
        return DEFAULT_SCENES
    try:
        n = int(float(r.par.Numscenes.eval()))
    except Exception:
        n = DEFAULT_SCENES
    return max(MIN_SCENES, min(MAX_SCENES, n))


def _active_scene():
    r = _root()
    if r is None:
        return 1
    try:
        s = int(float(r.par.Activescene.eval()))
    except Exception:
        s = 1
    return max(1, min(_num_scenes(), s))


def _slot(layer, col):
    return _root().op('slots/layer_{}/col_{}'.format(layer, col))


def _layer(layer):
    return _root().op('slots/layer_{}'.format(layer))


def _label(path):
    return os.path.basename(path) if path else ''


def _file_display_name(path, clip_type=None):
    """Basename of the asset file (not parent folders like Derivative)."""
    path = str(path or '').strip().replace('\\', '/')
    if not path:
        return ''
    path = _resolve_display_asset_path(path, clip_type)
    name = os.path.basename(path)
    if not name:
        return ''
    if str(clip_type or '').lower() == 'tox' and name.lower().endswith('.tox'):
        name = name[:-4]
    return name


def _is_bad_display_name(name):
    n = str(name or '').strip().lower()
    if not n:
        return True
    if n == 'missing':
        return True
    bad_exact = ('touchdesigner', 'touchengine', 'samples', 'sample', 'map', 'tox', 'video')
    if n in bad_exact:
        return True
    return 'derivative' in n


def _matrix_cell_label(layer, col):
    tbl = _table()
    if tbl is None:
        return ''
    idx = _find(tbl, int(layer), int(col))
    if idx is None:
        return ''
    try:
        label = str(tbl[idx, 'label']).strip()
    except Exception:
        return ''
    return label if not _is_bad_display_name(label) else ''


def _resolve_display_asset_path(path, clip_type=None):
    path = str(path or '').strip().strip('"').replace('\\', '/')
    if not path:
        return ''
    if os.path.isfile(path):
        return path
    if os.path.isdir(path):
        clip_type = str(clip_type or '').strip().lower()
        exts = {'.tox'} if clip_type == 'tox' else VIDEO_EXTS
        try:
            names = sorted(os.listdir(path))
        except Exception:
            names = []
        for name in names:
            full = os.path.join(path, name).replace('\\', '/')
            if os.path.isfile(full) and os.path.splitext(name)[1].lower() in exts:
                return full
        return path
    base, ext = os.path.splitext(path)
    if ext:
        return path
    parent = os.path.dirname(path)
    stem = os.path.basename(path)
    if parent and os.path.isdir(parent):
        try:
            names = sorted(os.listdir(parent))
        except Exception:
            names = []
        for name in names:
            if not name.lower().startswith(stem.lower()):
                continue
            full = os.path.join(parent, name).replace('\\', '/')
            if os.path.isfile(full):
                return full
    return path


def _asset_file_missing(path, clip_type=None):
    """True when a stored clip path no longer resolves to a readable file."""
    raw = str(path or '').strip()
    if not raw:
        return False
    norm = _norm_asset_path(raw)
    if norm and os.path.isfile(norm):
        return False
    resolved = _resolve_display_asset_path(norm or raw, clip_type)
    return not (resolved and os.path.isfile(resolved))


def _live_cell_display_name(layer, col, clip_type):
    slot = _slot(layer, col)
    if slot is None:
        return ''
    clip_type = str(clip_type or '').strip().lower()
    paths = []
    if clip_type == 'video':
        v = slot.op('video')
        if v is not None:
            try:
                paths.append(str(v.par.file.eval()).strip())
            except Exception:
                pass
    elif clip_type == 'tox':
        try:
            paths.append(_slot_tox_path(slot))
        except Exception:
            pass
        t = slot.op('tox')
        if t is not None:
            try:
                paths.append(str(t.par.externaltox.eval()).strip())
            except Exception:
                pass
    for p in paths:
        name = _file_display_name(p, clip_type)
        if not _is_bad_display_name(name):
            return name
    return ''


def _clip_display_name(clip_type, path):
    """Short name stored in clip_matrix label column."""
    name = _file_display_name(path, clip_type)
    return name[:40] if name else chr(183)


def _cell_display_name(layer, col):
    """Name strip above cell thumbnail — always the loaded file, not folder/type."""
    layer, col = int(layer), int(col)
    ctype, path = _get(layer, col)
    if not path:
        return chr(183)
    if _asset_file_missing(path, ctype):
        name = _file_display_name(path, ctype)
        return name[:40] if name else 'missing'
    name = _matrix_cell_label(layer, col)
    if _is_bad_display_name(name):
        name = _file_display_name(path, ctype)
    if _is_bad_display_name(name):
        name = _live_cell_display_name(layer, col, ctype)
    if _is_bad_display_name(name):
        name = chr(183)
    return name[:40]


def _find(tbl, layer, col, scene=None):
    scene = _active_scene() if scene is None else int(scene)
    for i in range(1, tbl.numRows):
        if (int(tbl[i, 'scene']) == scene and
                int(tbl[i, 'layer']) == layer and
                int(tbl[i, 'col']) == col):
            return i
    return None


def _get(layer, col):
    tbl = _table()
    if tbl is None:
        return '', ''
    idx = _find(tbl, layer, col)
    if idx is None:
        return '', ''
    return str(tbl[idx, 'type']), str(tbl[idx, 'path'])


def _clamp_cell_render_scale(value):
    try:
        scale = int(round(float(value)))
    except Exception:
        scale = 100
    allowed = (25, 50, 67, 75, 100)
    return min(allowed, key=lambda candidate: abs(candidate - scale))


def _clamp_cell_update_rate(value):
    try:
        rate = int(round(float(value)))
    except Exception:
        rate = 1
    allowed = (1, 2, 3, 4)
    return min(allowed, key=lambda candidate: abs(candidate - rate))


def _cell_render_scale(layer, col, scene=None):
    tbl = _table()
    if tbl is None:
        return 100
    idx = _find(tbl, int(layer), int(col), scene=scene)
    if idx is None:
        return 100
    try:
        return _clamp_cell_render_scale(tbl[idx, 'render_scale'])
    except Exception:
        return 100


def _fx_row_render_scale_default():
    try:
        s = _settings()
        if s is not None and hasattr(s.par, 'Fxrowrenderscale'):
            return _clamp_cell_render_scale(s.par.Fxrowrenderscale.eval())
    except Exception:
        pass
    return 100


def _set_cell_render_scale(layer, col, scale, scene=None):
    tbl = _table()
    if tbl is None:
        return 100
    idx = _find(tbl, int(layer), int(col), scene=scene)
    scale = _clamp_cell_render_scale(scale)
    if idx is not None:
        try:
            tbl[idx, 'render_scale'] = str(scale)
        except Exception:
            pass
    return scale


def _cell_update_rate(layer, col, scene=None):
    tbl = _table()
    if tbl is None:
        return 1
    idx = _find(tbl, int(layer), int(col), scene=scene)
    if idx is None:
        return 1
    try:
        return _clamp_cell_update_rate(tbl[idx, 'update_rate'])
    except Exception:
        return 1


def _set_cell_update_rate(layer, col, rate, scene=None):
    tbl = _table()
    if tbl is None:
        return 1
    idx = _find(tbl, int(layer), int(col), scene=scene)
    rate = _clamp_cell_update_rate(rate)
    if idx is not None:
        try:
            tbl[idx, 'update_rate'] = str(rate)
        except Exception:
            pass
    return rate


def _cell_frozen(layer, col, scene=None):
    tbl = _table()
    if tbl is None:
        return False
    idx = _find(tbl, int(layer), int(col), scene=scene)
    if idx is None:
        return False
    try:
        value = str(tbl[idx, 'frozen']).strip().lower()
        return value in ('1', 'true', 'yes', 'on')
    except Exception:
        return False


def _set_cell_frozen(layer, col, frozen, scene=None):
    tbl = _table()
    if tbl is None:
        return False
    idx = _find(tbl, int(layer), int(col), scene=scene)
    frozen = bool(frozen)
    if idx is not None:
        try:
            tbl[idx, 'frozen'] = '1' if frozen else '0'
        except Exception:
            pass
    return frozen


def _set(layer, col, clip_type, path, scene=None):
    tbl = _table()
    scene = _active_scene() if scene is None else int(scene)
    idx = _find(tbl, layer, col, scene=scene)
    scale = _cell_render_scale(layer, col, scene=scene) if idx is not None else 100
    previous_path = ''
    if idx is not None:
        try:
            previous_path = str(tbl[idx, 'path']).strip()
        except Exception:
            previous_path = ''
    is_new_cell = idx is None or not previous_path
    if is_new_cell and str(clip_type or '').strip().lower() == 'tox':
        try:
            if int(layer) < int(_scene_num_layers(scene)):
                scale = _fx_row_render_scale_default()
        except Exception:
            pass
    update_rate = _cell_update_rate(layer, col, scene=scene) if idx is not None else 1
    frozen = _cell_frozen(layer, col, scene=scene) if idx is not None else False
    if path:
        path = _store_asset_path(path)
        if not _valid_clip_type(clip_type):
            return
    row = [
        scene, layer, col, clip_type, path, _clip_display_name(clip_type, path),
        str(scale), str(update_rate), '1' if frozen else '0',
    ]
    if idx is None:
        tbl.appendRow(row)
    else:
        for j, v in enumerate(row):
            tbl[idx, j] = v


def _norm_asset_path(path):
    if not path:
        return ''
    path = str(path).strip().strip('"').replace('\\', '/')
    if not path:
        return ''
    if not os.path.isabs(path) and not (len(path) > 1 and path[1] == ':'):
        try:
            full = os.path.normpath(os.path.join(project.folder, path)).replace('\\', '/')
            if os.path.isfile(full):
                path = full
        except Exception:
            pass
    try:
        p = os.path.normpath(path).replace('\\', '/')
        if os.path.isfile(p):
            p = os.path.normcase(os.path.realpath(p)).replace('\\', '/')
        return p
    except Exception:
        return path


def _rel_or_abs_path(path):
    """Store asset paths relative to project.folder when possible."""
    path = _norm_asset_path(path)
    if not path:
        return ''
    if not os.path.isabs(path) and not (len(path) > 1 and path[1] == ':'):
        return path.lstrip('./')
    try:
        rel = os.path.relpath(path, project.folder).replace('\\', '/')
        if not rel.startswith('..'):
            return rel
    except Exception:
        pass
    return path


def _store_asset_path(path):
    """Persist clip/FX paths relative to project.folder when possible."""
    return _rel_or_abs_path(path)


def _pick_asset_file(title, file_types, hint_path=''):
    """File picker; opens near hint_path when that folder still exists."""
    start = project.folder
    try:
        hint = _norm_asset_path(hint_path) if hint_path else ''
        parent = os.path.dirname(hint) if hint else ''
        while parent:
            if os.path.isdir(parent):
                start = parent
                break
            nxt = os.path.dirname(parent)
            if nxt == parent:
                break
            parent = nxt
    except Exception:
        pass
    types = []
    for t in file_types or ():
        s = str(t).strip().lstrip('.')
        if s and s not in types:
            types.append(s)
    path = None
    try:
        path = ui.chooseFile(
            title=title,
            fileTypes=types or None,
            load=True,
            start=start,
        )
    except Exception as exc:
        print('File picker error:', exc)
        path = None
    return _norm_asset_path(path) if path else ''


def _find_asset_cells(clip_type, path, skip=(), scene=None):
    norm = _norm_asset_path(path)
    if not norm or not clip_type:
        return []
    skip = set((int(a), int(b)) for a, b in skip)
    scene = _active_scene() if scene is None else int(scene)
    hits = []
    tbl = _table()
    if tbl is None:
        return hits
    for i in range(1, tbl.numRows):
        if int(tbl[i, 'scene']) != scene:
            continue
        t = str(tbl[i, 'type'])
        p = _norm_asset_path(str(tbl[i, 'path']))
        if t == clip_type and p and p == norm:
            layer = int(tbl[i, 'layer'])
            col = int(tbl[i, 'col'])
            if (layer, col) not in skip:
                hits.append((layer, col))
    return hits


def _evict_duplicate_assets(clip_type, path, keep_layer, keep_col, skip=()):
    """Clear other cells using the same asset. TOX clips may repeat across cells."""
    if str(clip_type or '').strip().lower() == 'tox':
        return set()
    skip_set = set((int(a), int(b)) for a, b in skip)
    skip_set.add((int(keep_layer), int(keep_col)))
    cols = set()
    for layer, col in _find_asset_cells(clip_type, path):
        if (layer, col) in skip_set:
            continue
        clear_cell(layer, col)
        cols.add(col)
        print('Removed duplicate {} from row {} col {}'.format(_label(path), layer, col))
    return cols


def dedupe_grid_assets():
    """Keep one grid cell per unique video asset; TOX may repeat across cells."""
    seen = {}
    cleared_cols = set()
    for col in range(1, _num_cols() + 1):
        for layer in range(1, _num_layers() + 1):
            ctype, path = _get(layer, col)
            if not path:
                continue
            if str(ctype).strip().lower() == 'tox':
                continue
            key = (ctype, _norm_asset_path(path))
            if key in seen:
                clear_cell(layer, col)
                cleared_cols.add(col)
                print('Removed duplicate {} from row {} col {}'.format(_label(path), layer, col))
            else:
                seen[key] = (layer, col)
    for c in cleared_cols:
        _rebuild_column_chain(c)
    if cleared_cols:
        _refresh_ui()
    return len(cleared_cols)
