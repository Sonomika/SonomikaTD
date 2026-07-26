CELL_FX_ROW_HDR = 22
CELL_FX_ROW_BODY = 140
CELL_FX_MAX = 7
CELL_FX_TAG = '__perf_cell_fx__'

_CELL_FX = {}
_CELL_FX_GUARD = {'wiring': False}


def _cell_fx_key(layer, col, scene=None):
    return (int(_active_scene() if scene is None else scene), int(layer), int(col))


def _cell_fx_list(layer, col, scene=None):
    return list(_CELL_FX.get(_cell_fx_key(layer, col, scene), ()))


def cell_accepts_stacked_fx(layer, col, scene=None):
    """Stacked .tox effects are only valid on loaded effect (.tox) cells, not video."""
    ctype, src = _get(layer, col)
    return bool(src) and str(ctype).strip().lower() == 'tox'


def cell_accepts_tox_clip_load(layer, col):
    """Grid / browser .tox drops may load on empty or effect cells, not video cells."""
    ctype, src = _get(layer, col)
    if not src:
        return True
    return str(ctype).strip().lower() != 'video'


def _cell_accepts_tox_fx_drop(layer, col, scene=None):
    """True when dropping a .tox onto the Cell FX panel should be accepted."""
    ctype, src = _get(layer, col)
    if not src:
        return True
    return str(ctype).strip().lower() == 'tox'


def _slot_coords(slot):
    if slot is None:
        return None, None
    p = slot
    for _ in range(8):
        name = getattr(p, 'name', '')
        if name.startswith('col_'):
            try:
                col = int(name.split('_')[1])
            except Exception:
                return None, None
            parent = p.parent()
            if parent is not None and parent.name.startswith('layer_'):
                try:
                    return int(parent.name.split('_')[1]), col
                except Exception:
                    return None, None
        try:
            p = p.parent()
        except Exception:
            break
    return None, None


def _next_cell_fx_id(layer, col, scene=None):
    key = _cell_fx_key(layer, col, scene)
    used = {int(e.get('id', 0)) for e in _CELL_FX.get(key, ())}
    n = 1
    while n in used:
        n += 1
    return n


def _cell_fx_entry(layer, col, fx_id, scene=None):
    fx_id = int(fx_id)
    for entry in _cell_fx_list(layer, col, scene):
        if int(entry.get('id', -1)) == fx_id:
            return entry
    return None


def _cell_fx_index(layer, col, fx_id, scene=None):
    fx_id = int(fx_id)
    for i, entry in enumerate(_cell_fx_list(layer, col, scene)):
        if int(entry.get('id', -1)) == fx_id:
            return i
    return -1


def _cell_fx_label(path):
    path = _norm_asset_path(path or '')
    if not path:
        return 'Effect'
    base = os.path.basename(path)
    if base.lower().endswith('.tox'):
        base = base[:-4]
    return base or 'Effect'


def _build_cell_fx_slot(slots, fx_id):
    name = 'fx_{:04d}'.format(int(fx_id))
    slot = slots.create('baseCOMP', name)
    in_sel = slot.create('selectTOP', 'in_sel')
    _bind_canvas_res(in_sel)
    tox = slot.create('baseCOMP', 'tox')
    try:
        tox.par.enableexternaltox = True
    except Exception:
        pass
    tox_black = tox.create('constantTOP', 'black')
    _set_par(tox_black, 'colorr', expr=CANVAS_BG_R_EXPR)
    _set_par(tox_black, 'colorg', expr=CANVAS_BG_G_EXPR)
    _set_par(tox_black, 'colorb', expr=CANVAS_BG_B_EXPR)
    _set_par(tox_black, 'alpha', 1)
    _bind_canvas_res(tox_black)
    tox_out = tox.create('outTOP', 'out1')
    tox_black.outputConnectors[0].connect(tox_out.inputConnectors[0])
    tox_pick = slot.create('selectTOP', 'tox_pick')
    _set_par(tox_pick, 'outputresolution', 'useinput')
    _set_par(tox_pick, 'top', expr="op('tox/out1')")
    canvas_fit = slot.create('fitTOP', 'canvas_fit')
    _configure_tox_fit(canvas_fit)
    bypass = slot.create('switchTOP', 'bypass')
    _set_par(bypass, 'index', 0)
    in_sel.outputConnectors[0].connect(bypass.inputConnectors[0])
    tox_pick.outputConnectors[0].connect(canvas_fit.inputConnectors[0])
    canvas_fit.outputConnectors[0].connect(bypass.inputConnectors[1])
    out = slot.create('outTOP', 'out1')
    bypass.outputConnectors[0].connect(out.inputConnectors[0])
    return slot


def _ensure_cell_fx_canvas_fit(fx_slot):
    if fx_slot is None:
        return None
    tox_pick = fx_slot.op('tox_pick')
    bypass = fx_slot.op('bypass')
    if tox_pick is None or bypass is None:
        return None
    fit = fx_slot.op('canvas_fit')
    if fit is None:
        fit = fx_slot.create('fitTOP', 'canvas_fit')
    _configure_tox_fit(fit)
    try:
        _disconnect_input(fit.inputConnectors[0])
        tox_pick.outputConnectors[0].connect(fit.inputConnectors[0])
        _disconnect_input(bypass.inputConnectors[1])
        fit.outputConnectors[0].connect(bypass.inputConnectors[1])
    except Exception:
        pass
    return fit


def _ensure_slot_cell_fx_network(slot, layer, col):
    if slot is None:
        return None
    chain = slot.op('cell_fx')
    if chain is None:
        try:
            chain = slot.create('baseCOMP', 'cell_fx')
        except Exception:
            return None
    slots = chain.op('slots')
    if slots is None:
        try:
            slots = chain.create('baseCOMP', 'slots')
        except Exception:
            return None
    for entry in _cell_fx_list(layer, col):
        fx_id = int(entry.get('id', 0))
        if fx_id <= 0:
            continue
        name = 'fx_{:04d}'.format(fx_id)
        if slots.op(name) is None:
            _build_cell_fx_slot(slots, fx_id)
        _ensure_cell_fx_canvas_fit(slots.op(name))
    out = slot.op('cell_fx_out')
    if out is None:
        try:
            out = slot.create('selectTOP', 'cell_fx_out')
            _bind_canvas_res(out)
        except Exception:
            return chain
    return chain


def _cell_fx_slot_comp(slot, fx_id):
    chain = slot.op('cell_fx') if slot else None
    slots = chain.op('slots') if chain else None
    if slots is None:
        return None
    return slots.op('fx_{:04d}'.format(int(fx_id)))


def _set_cell_fx_animation_paused(layer, col, paused=True):
    slot = _slot(layer, col)
    for entry in _cell_fx_list(layer, col):
        fx_slot = _cell_fx_slot_comp(slot, entry.get('id'))
        if fx_slot is not None:
            _set_tox_animation_paused(fx_slot.op('tox'), paused)


def _feed_cell_fx_tox(fx_slot):
    t = fx_slot.op('tox') if fx_slot else None
    if t is None:
        return
    _protect_generic_tox_resolution(t)
    _ensure_generic_tox_input_adapter(t)
    feed_expr = "op('../in_sel')"
    for name in ('select_video_in', 'select_in', 'video_sel'):
        sel = t.op(name)
        if sel is not None:
            try:
                sel.par.top.expr = feed_expr
                sel.par.top.mode = ParMode.EXPRESS
                _lock_stacked_cell_fx_feed(sel, _stacked_cell_fx_scale(t))
            except Exception:
                pass
    _heal_effect_tox(t, reload_external=False)
    _apply_tox_render_scale(t)


def _wire_cell_fx_tox(slot, layer, col, fx_id, path, force_reload=False):
    fx_slot = _cell_fx_slot_comp(slot, fx_id)
    if fx_slot is None:
        return False
    t = fx_slot.op('tox')
    if t is None:
        return False
    path_norm = _norm_asset_path(path)
    load_path = _tox_load_path(path)
    prev = ''
    try:
        prev = _norm_asset_path(str(t.par.externaltox.eval()).strip())
    except Exception:
        pass
    already = prev == path_norm and bool(path_norm)
    t.allowCooking = True
    if force_reload or not already:
        try:
            t.par.externaltox = load_path
            t.par.enableexternaltoxpulse.pulse()
        except Exception:
            pass
        _heal_effect_tox(t, reload_external=True)
    else:
        _heal_effect_tox(t, reload_external=False)
    _feed_cell_fx_tox(fx_slot)
    if force_reload:
        _schedule_effect_resolution_repair(layer, col)
    entry = _cell_fx_entry(layer, col, fx_id)
    try:
        sw = fx_slot.op('bypass')
        if sw is not None and entry is not None:
            # Input 0 is dry/in_sel; input 1 is the effect output.
            sw.par.index = 0 if entry.get('bypass') else 1
    except Exception:
        pass
    return True


def _connect_slot_content_to_level(slot, layer=None):
    """Route pick (via optional cell_fx_out) into layer_opacity."""
    if slot is None:
        return
    level = slot.op('layer_opacity')
    if level is None:
        _ensure_slot_layer_blend(slot, layer)
        level = slot.op('layer_opacity')
    if level is None:
        return
    fx_out = slot.op('cell_fx_out')
    pick = slot.op('pick')
    src = fx_out if fx_out is not None else pick
    if src is None:
        return
    try:
        _disconnect_input(level.inputConnectors[0])
    except Exception:
        pass
    try:
        src.outputConnectors[0].connect(level.inputConnectors[0])
    except Exception:
        pass


def _wire_slot_cell_fx_chain(layer, col, slot=None):
    if _CELL_FX_GUARD['wiring']:
        return
    _CELL_FX_GUARD['wiring'] = True
    try:
        layer, col = int(layer), int(col)
        slot = slot or _slot(layer, col)
        if slot is None:
            return
        pick = slot.op('pick')
        pick_expr = (
            "op('{}')".format(pick.path.replace('\\', '/'))
            if pick is not None else "op('pick')"
        )
        effects = _cell_fx_list(layer, col)
        if not cell_accepts_stacked_fx(layer, col):
            effects = []
        if not effects:
            stale_chain = slot.op('cell_fx')
            if stale_chain is not None:
                try:
                    stale_chain.destroy()
                except Exception:
                    pass
            out = slot.op('cell_fx_out')
            if out is not None:
                _set_top_expr(out, pick_expr)
            _connect_slot_content_to_level(slot, layer)
            return
        _ensure_slot_cell_fx_network(slot, layer, col)
        prev_expr = pick_expr
        for entry in effects:
            fx_id = int(entry.get('id', 0))
            fx_slot = _cell_fx_slot_comp(slot, fx_id)
            if fx_slot is None:
                continue
            in_sel = fx_slot.op('in_sel')
            if in_sel is not None:
                _set_top_expr(in_sel, prev_expr)
                try:
                    _configure_scaled_top_res(in_sel, _cell_render_scale(layer, col))
                except Exception:
                    pass
            _wire_cell_fx_tox(slot, layer, col, fx_id, entry.get('path', ''), force_reload=False)
            out1 = fx_slot.op('out1')
            if out1 is not None:
                prev_expr = "op('{}')".format(out1.path.replace('\\', '/'))
        out = slot.op('cell_fx_out')
        if out is not None:
            _set_top_expr(out, prev_expr)
        _connect_slot_content_to_level(slot, layer)
    finally:
        _CELL_FX_GUARD['wiring'] = False


def add_cell_fx(layer, col, path, index=None, scene=None):
    layer, col = int(layer), int(col)
    path = _norm_asset_path(path or '')
    if not path or not path.lower().endswith('.tox'):
        return None
    ctype, src = _get(layer, col)
    if not src:
        load_cell(layer, col, 'tox', path)
        _refresh_layer_fx_ui(layer, col)
        return None
    if not cell_accepts_stacked_fx(layer, col, scene):
        if str(ctype).strip().lower() == 'video':
            print('Cell FX: video cells cannot contain stacked effects')
        else:
            print('Cell FX: only effect (.tox) cells can contain stacked effects')
        return None
    key = _cell_fx_key(layer, col, scene)
    fx_list = list(_CELL_FX.get(key, ()))
    if len(fx_list) >= CELL_FX_MAX:
        print('Cell FX: max {} stacked effects per cell ({} including source)'.format(
            CELL_FX_MAX, CELL_FX_MAX + 1))
        return None
    fx_id = _next_cell_fx_id(layer, col, scene)
    entry = {
        'id': fx_id,
        'path': _store_asset_path(path),
        'label': _cell_fx_label(path),
        'bypass': False,
        'expanded': False,
        'par_state': [],
    }
    if index is None or index < 0 or index > len(fx_list):
        fx_list.append(entry)
    else:
        fx_list.insert(int(index), entry)
    _CELL_FX[key] = fx_list
    slot = _slot(layer, col)
    _ensure_slot_cell_fx_network(slot, layer, col)
    _wire_cell_fx_tox(slot, layer, col, fx_id, path, force_reload=True)
    _wire_slot_cell_fx_chain(layer, col, slot)
    _refresh_layer_fx_ui(layer, col)
    set_params_tab('layer')
    return fx_id


def promote_cell_fx_to_source(layer, col, scene=None):
    """Replace source TOX with the first stacked cell FX; keep any others."""
    layer, col = int(layer), int(col)
    key = _cell_fx_key(layer, col, scene)
    fx_list = list(_CELL_FX.get(key, ()))
    if not fx_list:
        return False
    entry = fx_list.pop(0)
    _CELL_FX[key] = fx_list
    path = str(entry.get('path', '') or '')
    records = list(entry.get('par_state') or [])
    fx_id = int(entry.get('id', 0))
    slot = _slot(layer, col)
    if slot is not None and fx_id > 0:
        fx_slot = _cell_fx_slot_comp(slot, fx_id)
        if fx_slot is not None:
            try:
                purge_map_control_bindings_for_cell_fx(layer, col, fx_id, scene)
            except Exception:
                pass
            try:
                fx_slot.destroy()
            except Exception:
                pass
    if not path:
        _wire_slot_cell_fx_chain(layer, col, slot)
        _refresh_layer_fx_ui(layer, col)
        return False
    load_cell(layer, col, 'tox', path, par_state=records)
    _refresh_layer_fx_ui(layer, col)
    return True


def delete_cell_fx_source(layer, col, scene=None):
    """Delete source row only — promote stacked FX instead of clearing the cell."""
    if _cell_fx_list(layer, col, scene):
        return promote_cell_fx_to_source(layer, col, scene)
    delete_cell(layer, col)
    return True


def remove_cell_fx(layer, col, fx_id, scene=None):
    layer, col, fx_id = int(layer), int(col), int(fx_id)
    key = _cell_fx_key(layer, col, scene)
    fx_list = list(_CELL_FX.get(key, ()))
    idx = _cell_fx_index(layer, col, fx_id, scene)
    if idx < 0:
        return False
    entry = fx_list.pop(idx)
    _CELL_FX[key] = fx_list
    slot = _slot(layer, col)
    if slot is not None:
        fx_slot = _cell_fx_slot_comp(slot, entry.get('id'))
        try:
            purge_map_control_bindings_for_cell_fx(layer, col, entry.get('id'), scene)
        except Exception:
            pass
        if fx_slot is not None:
            try:
                fx_slot.destroy()
            except Exception:
                pass
    _wire_slot_cell_fx_chain(layer, col, slot)
    _refresh_layer_fx_ui(layer, col)
    return True


def reload_cell_fx(layer, col, row_id):
    """Reload source clip or stacked effect from disk."""
    layer, col = int(layer), int(col)
    if str(row_id) == 'source' or int(row_id) == 0:
        return reload_cell(layer, col)
    fx_id = int(row_id)
    entry = _cell_fx_entry(layer, col, fx_id)
    path = str(entry.get('path', '') if entry else '').strip()
    if not path:
        print('No effect to reload at row {} col {}'.format(layer, col))
        return False
    slot = _slot(layer, col)
    if slot is None:
        return False
    par_state = _snapshot_cell_fx_params(layer, col, fx_id) or list(entry.get('par_state') or [])
    _wire_cell_fx_tox(slot, layer, col, fx_id, path, force_reload=True)
    fx_slot = _cell_fx_slot_comp(slot, fx_id)
    _restore_cell_fx_params(fx_slot.op('tox') if fx_slot else None, par_state)
    entry['par_state'] = par_state
    _wire_slot_cell_fx_chain(layer, col, slot)
    if _is_composition_cell(layer, col) or _get_layer_src_col(layer) == col:
        _refresh_composition_for_cols([col])
    _refresh_layer_fx_ui(layer, col)
    print('Reloaded {} row {} col {}'.format(_label(path), layer, col))
    return True


def relink_cell_fx(layer, col, row_id, new_path=None):
    """Point source or stacked cell FX at a moved/renamed .tox, then reload."""
    layer, col = int(layer), int(col)
    if str(row_id) == 'source' or int(row_id) == 0:
        return relink_cell(layer, col, new_path=new_path)
    fx_id = int(row_id)
    entry = _cell_fx_entry(layer, col, fx_id)
    old_path = str(entry.get('path', '') if entry else '').strip()
    if not old_path:
        print('No effect to relink at row {} col {}'.format(layer, col))
        return False
    if not new_path:
        new_path = _pick_asset_file('Relink Effect TOX', ['tox'], old_path)
    new_path = _norm_asset_path(new_path)
    if not new_path:
        return False
    if not os.path.isfile(new_path) or not new_path.lower().endswith('.tox'):
        print('Relink: need a .tox file ->', new_path)
        return False
    slot = _slot(layer, col)
    if slot is None:
        return False
    par_state = _snapshot_cell_fx_params(layer, col, fx_id) or list(entry.get('par_state') or [])
    entry['path'] = _store_asset_path(new_path)
    entry['label'] = _cell_fx_label(new_path)
    _wire_cell_fx_tox(slot, layer, col, fx_id, new_path, force_reload=True)
    fx_slot = _cell_fx_slot_comp(slot, fx_id)
    _restore_cell_fx_params(fx_slot.op('tox') if fx_slot else None, par_state)
    entry['par_state'] = par_state
    _wire_slot_cell_fx_chain(layer, col, slot)
    if _is_composition_cell(layer, col) or _get_layer_src_col(layer) == col:
        _refresh_composition_for_cols([col])
    _refresh_layer_fx_ui(layer, col)
    print('Relinked effect row {} col {} -> {}'.format(layer, col, _label(new_path)))
    return True


def edit_tox_cell_fx(layer, col, row_id):
    """Open the source or stacked effect .tox for editing."""
    layer, col = int(layer), int(col)
    if str(row_id) == 'source' or int(row_id) == 0:
        return edit_tox_cell(layer, col)
    fx_id = int(row_id)
    entry = _cell_fx_entry(layer, col, fx_id)
    path = str(entry.get('path', '') if entry else '').strip()
    if not path:
        print('No .tox file found for row {} col {}'.format(layer, col))
        return False
    slot = _slot(layer, col)
    fx_slot = _cell_fx_slot_comp(slot, fx_id) if slot else None
    tox = fx_slot.op('tox') if fx_slot else None
    tox_path = _resolve_tox_edit_path(path, tox)
    if not tox_path:
        print('No .tox file found for row {} col {}'.format(layer, col))
        return False
    return open_tox_for_edit(tox_path)


def copy_cell_fx(layer, col, row_id):
    layer, col = int(layer), int(col)
    if str(row_id) == 'source' or int(row_id) == 0:
        ctype, path = _get(layer, col)
        if ctype != 'tox' or not path:
            return False
        return _set_fx_clipboard(
            path, _cell_display_name(layer, col), False, _source_row_expanded(),
            _snapshot_cell_params(layer, col, 'tox'))
    fx_id = int(row_id)
    entry = _cell_fx_entry(layer, col, fx_id)
    if entry is None:
        return False
    records = _snapshot_cell_fx_params(layer, col, fx_id) or list(entry.get('par_state') or [])
    return _set_fx_clipboard(
        entry.get('path'), entry.get('label'), entry.get('bypass'),
        entry.get('expanded'), records)


def cut_cell_fx(layer, col, row_id):
    if not copy_cell_fx(layer, col, row_id):
        return False
    if str(row_id) == 'source' or int(row_id) == 0:
        if _cell_fx_list(layer, col):
            return promote_cell_fx_to_source(layer, col)
        delete_cell(layer, col)
        return True
    return remove_cell_fx(layer, col, int(row_id))


def paste_cell_fx(layer, col, before_id=None):
    layer, col = int(layer), int(col)
    path = _FX_CLIPBOARD.get('path', '')
    if not path:
        return None
    ctype, src = _get(layer, col)
    records = list(_FX_CLIPBOARD.get('par_state') or [])
    if not src:
        load_cell(layer, col, 'tox', path, par_state=records)
        return 'source'
    if not cell_accepts_stacked_fx(layer, col) or len(_cell_fx_list(layer, col)) >= CELL_FX_MAX:
        return None
    index = _cell_fx_index(layer, col, before_id) if before_id not in (None, 'source') else None
    if index is not None and index < 0:
        index = None
    fx_id = add_cell_fx(layer, col, path, index=index)
    entry = _cell_fx_entry(layer, col, fx_id) if fx_id is not None else None
    if entry is None:
        return None
    entry['label'] = str(_FX_CLIPBOARD.get('label') or _cell_fx_label(path))
    entry['expanded'] = bool(_FX_CLIPBOARD.get('expanded', False))
    _set_cell_fx_bypass(layer, col, fx_id, _FX_CLIPBOARD.get('bypass', False))
    entry['par_state'] = records
    slot = _slot(layer, col)
    fx_slot = _cell_fx_slot_comp(slot, fx_id) if slot else None
    _restore_cell_fx_params(fx_slot.op('tox') if fx_slot else None, records)
    _refresh_layer_fx_ui(layer, col)
    return fx_id


def move_cell_fx(layer, col, src_id, dst_id, scene=None):
    layer, col = int(layer), int(col)
    si = _cell_fx_index(layer, col, src_id, scene)
    di = _cell_fx_index(layer, col, dst_id, scene)
    if si < 0 or di < 0 or si == di:
        return False
    key = _cell_fx_key(layer, col, scene)
    fx_list = list(_CELL_FX.get(key, ()))
    for current in fx_list:
        fx_id = int(current.get('id', 0))
        current['par_state'] = (
            _snapshot_cell_fx_params(layer, col, fx_id, scene)
            or list(current.get('par_state') or []))
    entry = fx_list.pop(si)
    # Insert at the target's original position. Decrementing di here makes a
    # two-effect list impossible to reorder when dragging the first onto second.
    fx_list.insert(di, entry)
    _CELL_FX[key] = fx_list
    _wire_slot_cell_fx_chain(layer, col)
    slot = _slot(layer, col)
    for current in fx_list:
        fx_slot = _cell_fx_slot_comp(slot, current.get('id')) if slot else None
        _restore_cell_fx_params(
            fx_slot.op('tox') if fx_slot else None, current.get('par_state') or [])
    _refresh_layer_fx_ui(layer, col)
    return True


def swap_cell_fx_with_source(layer, col, fx_id):
    """Swap the source TOX with one stacked FX while preserving parameters."""
    layer, col, fx_id = int(layer), int(col), int(fx_id)
    entry = _cell_fx_entry(layer, col, fx_id)
    ctype, source_path = _get(layer, col)
    if entry is None or ctype != 'tox' or not source_path:
        return False
    slot = _slot(layer, col)
    if slot is None:
        return False
    source_state = _snapshot_cell_params(layer, col, 'tox')
    stacked_state = _snapshot_cell_fx_params(layer, col, fx_id)
    stacked_path = entry.get('path', '')
    _set(layer, col, 'tox', stacked_path)
    _wire_tox(slot, stacked_path, layer, col, force_reload=True)
    entry['path'] = source_path
    entry['label'] = _cell_fx_label(source_path)
    _wire_cell_fx_tox(slot, layer, col, fx_id, source_path, force_reload=True)
    _wire_slot_cell_fx_chain(layer, col, slot)
    _restore_cell_params(layer, col, 'tox', stacked_state)
    _schedule_cell_par_restore(layer, col, 'tox', stacked_state)
    entry['par_state'] = source_state
    fx_slot = _cell_fx_slot_comp(slot, fx_id)
    _restore_cell_fx_params(fx_slot.op('tox') if fx_slot else None, source_state)
    _refresh_cell_display(layer, col)
    _refresh_layer_fx_ui(layer, col)
    return True


def clear_cell_fx(layer, col, scene=None):
    key = _cell_fx_key(layer, col, scene)
    fx_list = list(_CELL_FX.get(key, ()))
    _CELL_FX[key] = []
    slot = _slot(layer, col)
    purge_paths = []
    if slot is not None:
        for entry in fx_list:
            purge_paths.extend(
                _map_control_paths_for_cell_fx(slot, entry.get('id')))
    try:
        purge_map_control_bindings_for_ops(purge_paths)
    except Exception:
        pass
    if slot is not None:
        for entry in fx_list:
            fx_slot = _cell_fx_slot_comp(slot, entry.get('id'))
            if fx_slot is not None:
                try:
                    fx_slot.destroy()
                except Exception:
                    pass
        chain = slot.op('cell_fx')
        if chain is not None:
            try:
                chain.destroy()
            except Exception:
                pass
        out = slot.op('cell_fx_out')
        if out is not None:
            try:
                out.destroy()
            except Exception:
                pass
    _wire_slot_cell_fx_chain(layer, col, slot)
    _refresh_layer_fx_ui(layer, col)


def _set_cell_fx_bypass(layer, col, fx_id, bypass):
    entry = _cell_fx_entry(layer, col, fx_id)
    if entry is None:
        return
    entry['bypass'] = bool(bypass)
    slot = _slot(layer, col)
    fx_slot = _cell_fx_slot_comp(slot, fx_id) if slot else None
    sw = fx_slot.op('bypass') if fx_slot else None
    if sw is not None:
        try:
            sw.par.index = 0 if entry['bypass'] else 1
        except Exception:
            pass
    _refresh_layer_fx_row(layer, col, fx_id)


def _toggle_cell_fx_expanded(layer, col, row_id):
    layer, col = int(layer), int(col)
    if str(row_id) == 'source' or int(row_id) == 0:
        r = _root()
        if r is not None:
            expanded = not bool(r.fetch('lfx_source_expanded', True))
            r.store('lfx_source_expanded', expanded)
        _layout_layer_fx_rows()
        return
    entry = _cell_fx_entry(layer, col, row_id)
    if entry is None:
        return
    entry['expanded'] = not bool(entry.get('expanded'))
    _layout_layer_fx_rows()
    _refresh_layer_fx_row(layer, col, row_id)


def _source_row_expanded():
    try:
        r = _root()
        if r is None:
            return True
        return bool(r.fetch('lfx_source_expanded', True))
    except Exception:
        return True


def export_cell_fx_state():
    rows = []
    for (scene, layer, col), effects in _CELL_FX.items():
        for entry in effects:
            fx_id = int(entry.get('id', 0))
            rows.append({
                'scene': int(scene),
                'layer': int(layer),
                'col': int(col),
                'id': fx_id,
                'path': _rel_or_abs_path(entry.get('path', '')),
                'label': str(entry.get('label', '')),
                'bypass': bool(entry.get('bypass')),
                'expanded': bool(entry.get('expanded')),
                'par_state': _snapshot_cell_fx_params(layer, col, fx_id, scene),
            })
    return rows


def _snapshot_cell_fx_params(layer, col, fx_id, scene=None):
    slot = _slot(layer, col, scene=scene) if False else _slot(layer, col)
    fx_slot = _cell_fx_slot_comp(slot, fx_id)
    target = fx_slot.op('tox') if fx_slot else None
    if target is None:
        return []
    records = []
    for par in _copyable_cell_params(target, 'tox'):
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
        records.append(rec)
    return records


def snapshot_cell_fx(layer, col, scene=None):
    """Return a portable snapshot of the stacked effects on one cell."""
    active = int(_active_scene())
    target_scene = int(active if scene is None else scene)
    rows = []
    for entry in _cell_fx_list(layer, col, target_scene):
        fx_id = int(entry.get('id', 0))
        records = list(entry.get('par_state') or [])
        if target_scene == active:
            live_records = _snapshot_cell_fx_params(layer, col, fx_id, target_scene)
            if live_records:
                records = live_records
        rows.append({
            'path': _rel_or_abs_path(entry.get('path', '')),
            'label': str(entry.get('label', '')),
            'bypass': bool(entry.get('bypass')),
            'expanded': bool(entry.get('expanded')),
            'par_state': records,
        })
    return rows


def _restore_cell_fx_params(target, records):
    if target is None:
        return
    for rec in records or []:
        try:
            par = getattr(target.par, rec.get('name', ''))
            if rec.get('expr'):
                par.expr = rec['expr']
            elif 'val' in rec:
                par.val = rec['val']
        except Exception:
            pass


def restore_cell_fx(layer, col, rows, scene=None):
    """Replace one cell's stacked effects from a portable snapshot."""
    layer, col = int(layer), int(col)
    active = int(_active_scene())
    target_scene = int(active if scene is None else scene)
    clear_cell_fx(layer, col, target_scene)
    tbl = _table()
    idx = _find(tbl, layer, col, scene=target_scene) if tbl is not None else None
    ctype = str(tbl[idx, 'type']) if idx is not None else ''
    src = str(tbl[idx, 'path']) if idx is not None else ''
    if ctype != 'tox' or not src:
        return False
    key = _cell_fx_key(layer, col, target_scene)
    effects = []
    for row in list(rows or [])[:CELL_FX_MAX]:
        if not isinstance(row, dict):
            continue
        path = _resolve_stored_asset_path(str(row.get('path', '')).strip())
        if not path:
            continue
        effects.append({
            'id': len(effects) + 1,
            'path': _store_asset_path(path),
            'label': str(row.get('label', '') or _cell_fx_label(path)),
            'bypass': bool(row.get('bypass')),
            'expanded': bool(row.get('expanded', False)),
            'par_state': list(row.get('par_state') or []),
        })
    _CELL_FX[key] = effects
    if target_scene != active:
        return bool(effects)
    slot = _slot(layer, col)
    _ensure_slot_cell_fx_network(slot, layer, col)
    for entry in effects:
        fx_id = int(entry.get('id', 0))
        _wire_cell_fx_tox(slot, layer, col, fx_id, entry.get('path', ''), force_reload=True)
        fx_slot = _cell_fx_slot_comp(slot, fx_id)
        _restore_cell_fx_params(fx_slot.op('tox') if fx_slot else None, entry.get('par_state'))
    _wire_slot_cell_fx_chain(layer, col, slot)
    _refresh_layer_fx_ui(layer, col)
    return bool(effects)


def import_cell_fx_state(rows):
    _CELL_FX.clear()
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        path = _resolve_stored_asset_path(str(row.get('path', '')).strip())
        if not path:
            continue
        scene = int(row.get('scene', 1))
        layer = int(row.get('layer', 1))
        col = int(row.get('col', 1))
        tbl = _table()
        idx = _find(tbl, layer, col, scene=scene) if tbl is not None else None
        ctype = str(tbl[idx, 'type']) if idx is not None else ''
        src = str(tbl[idx, 'path']) if idx is not None else ''
        if ctype != 'tox' or not src:
            continue
        key = _cell_fx_key(layer, col, scene)
        fx_list = list(_CELL_FX.get(key, ()))
        if len(fx_list) >= CELL_FX_MAX:
            continue
        fx_id = int(row.get('id', 0)) or _next_cell_fx_id(layer, col, scene)
        fx_list.append({
            'id': fx_id,
            'path': _store_asset_path(path),
            'label': str(row.get('label', '') or _cell_fx_label(path)),
            'bypass': bool(row.get('bypass')),
            'expanded': bool(row.get('expanded', False)),
            'par_state': list(row.get('par_state') or []),
        })
        _CELL_FX[key] = fx_list
    for (scene, layer, col), effects in list(_CELL_FX.items()):
        if scene != _active_scene():
            continue
        slot = _slot(layer, col)
        _ensure_slot_cell_fx_network(slot, layer, col)
        for entry in effects:
            fx_id = int(entry.get('id', 0))
            _wire_cell_fx_tox(slot, layer, col, fx_id, entry.get('path', ''), force_reload=True)
            records = entry.get('par_state') or []
            if records:
                fx_slot = _cell_fx_slot_comp(slot, fx_id)
                target = fx_slot.op('tox') if fx_slot else None
                _restore_cell_fx_params(target, records)
        _wire_slot_cell_fx_chain(layer, col, slot)


def _wire_cell_fx_dragdrop(comp):
    if comp is None:
        return
    cb = _ensure_cell_fx_dragdrop_dat()
    if cb is None:
        return
    try:
        comp.par.drop = 'usecallbacks'
        comp.par.drag = 'dragparent'
        comp.par.dragdropcallbacks = cb
    except Exception:
        pass


def _ensure_cell_fx_dragdrop_dat():
    r = _root()
    if r is None:
        return None
    cb = r.op('cell_fx_dragdrop')
    if cb is None:
        try:
            cb = r.create('textDAT', 'cell_fx_dragdrop')
            cb.par.language = 'python'
        except Exception:
            return None
    try:
        cb.text = CELL_FX_DRAGDROP
    except NameError:
        pass
    return cb


def _ensure_layer_fx_panel():
    r = _root()
    ui = r.op('ui') if r else None
    if ui is None:
        return None
    panel = ui.op('layer_fx_panel')
    if panel is None:
        panel = ui.create('containerCOMP', 'layer_fx_panel')
    try:
        panel.par.w = _cell_panel_w()
        panel.par.hmode = 'fixed'
        panel.par.vmode = 'fixed'
        panel.par.align = 'none'
        panel.par.clipping = True
        panel.par.display = True
        panel.par.enable = True
        panel.par.bgcolorr, panel.par.bgcolorg, panel.par.bgcolorb = TD_BG_MAIN
        panel.par.bgalpha = 1.0
    except Exception:
        pass
    hint = panel.op('layer_fx_hint')
    if hint is None:
        hint = panel.create('textTOP', 'layer_fx_hint')
    try:
        hint.par.text = 'Drop a .tox effect here'
        hint.par.font = TD_FONT
        hint.par.fontsizex = TD_FONT_SIZE_SMALL
        hint.par.fontsizey = TD_FONT_SIZE_SMALL
        hint.par.resolutionw = max(200, int(_cell_panel_w()))
        hint.par.resolutionh = 18
        hint.par.bgalpha = 0.0
        hint.par.fontcolorr, hint.par.fontcolorg, hint.par.fontcolorb = UI_TEXT_SECONDARY
        hint.par.alignx = 'center'
        hint.par.aligny = 'center'
        hint.par.clickthrough = True
    except Exception:
        pass
    _wire_cell_fx_dragdrop(panel)
    return panel


def _layer_fx_row_header(row):
    if row is None:
        return None
    for ch in row.children:
        if ch.isCOMP and 'row_hdr_' in ch.name:
            return ch
    return None


def _ensure_cell_fx_header_drag(row, hdr, sfx):
    """Keep one drag handle on the header for cell FX rows (source + stacked)."""
    if hdr is None:
        return None
    drag_name = 'lfx_drag_{}'.format(sfx)
    if row is not None:
        stray = row.op(drag_name)
        if stray is not None and stray.parent() != hdr:
            try:
                stray.destroy()
            except Exception:
                pass
    return _create_fx_accordion_drag_handle(
        hdr, drag_name, CELL_FX_ROW_HDR, _wire_cell_fx_dragdrop)


def _repair_cell_fx_accordion_drag(row, hdr):
    if row is None or not row.name.startswith('lfx_row_'):
        return
    sfx = row.name[len('lfx_row_'):]
    if hdr is None:
        hdr = _layer_fx_row_header(row)
    _ensure_cell_fx_header_drag(row, hdr, sfx)


def _create_layer_fx_row_header(parent, row_id, label, bypass=None, draggable=True):
    sfx = 'source' if row_id == 'source' else '{:04d}'.format(int(row_id))
    hdr = parent.create('containerCOMP', 'lfx_row_hdr_{}'.format(sfx))
    try:
        hdr.par.h = CELL_FX_ROW_HDR
        hdr.par.hmode = 'fixed'
        hdr.par.vmode = 'fixed'
        hdr.par.align = 'left'
        hdr.par.bgcolorr, hdr.par.bgcolorg, hdr.par.bgcolorb = UI_NAME_BAR_BG
        hdr.par.bgalpha = 1.0
        hdr.par.drag = 'dragno'
        hdr.par.drop = 'usecallbacks' if draggable else 'dropno'
    except Exception:
        pass
    if draggable:
        _wire_cell_fx_dragdrop(hdr)
        try:
            hdr.par.clickthrough = False
        except Exception:
            pass
    title = hdr.create('textTOP', 'title_text')
    try:
        title.par.text = str(label)
        title.par.font = TD_FONT
        title.par.fontsizex = TD_FONT_SIZE
        title.par.fontsizey = TD_FONT_SIZE
        title.par.resolutionw = _fx_accordion_title_width()
        title.par.resolutionh = CELL_FX_ROW_HDR
        title.par.bgalpha = 0.0
        title.par.fontcolorr, title.par.fontcolorg, title.par.fontcolorb = UI_TEXT_PRIMARY
        title.par.alignx = 'left'
        title.par.aligny = 'center'
        title.par.positionx = FX_HDR_TITLE_PAD
        title.par.textoffsetx = FX_HDR_TITLE_TEXT_OFFSET_X
        title.par.clickthrough = True
    except Exception:
        pass
    if row_id != 'source':
        bypass_btn = hdr.create('containerCOMP', 'lfx_bypass_{:04d}'.format(int(row_id)))
        try:
            bypass_btn.par.w = FX_HDR_BYPASS_W
            bypass_btn.par.h = CELL_FX_ROW_HDR - 4
            bypass_btn.par.y = FX_HDR_CHIP_PAD
            bypass_btn.par.drag = 'dragno'
            bypass_btn.par.drop = 'dropno'
            bypass_btn.par.clickthrough = True
        except Exception:
            pass
        btxt = bypass_btn.create('textTOP', 'label_text')
        try:
            btxt.par.text = 'BYP' if bypass else ''
            btxt.par.font = TD_FONT
            btxt.par.fontsizex = TD_FONT_SIZE_SMALL
            btxt.par.fontsizey = TD_FONT_SIZE_SMALL
            btxt.par.resolutionw = 28
            btxt.par.resolutionh = CELL_FX_ROW_HDR - 4
            btxt.par.bgalpha = 0.15 if bypass else 0.0
            btxt.par.fontcolorr, btxt.par.fontcolorg, btxt.par.fontcolorb = UI_TEXT_SECONDARY
            btxt.par.alignx = 'center'
            btxt.par.aligny = 'center'
            btxt.par.clickthrough = True
        except Exception:
            pass
        _apply_fx_chip_visual(bypass_btn, btxt, CELL_FX_ROW_HDR)
    expand_id = row_id if row_id != 'source' else 'source'
    expand_btn = hdr.create('containerCOMP', 'lfx_expand_{}'.format(
        expand_id if expand_id == 'source' else '{:04d}'.format(int(expand_id))))
    try:
        expand_btn.par.w = FX_HDR_EXPAND_W
        expand_btn.par.h = CELL_FX_ROW_HDR - 4
        expand_btn.par.y = FX_HDR_CHIP_PAD
        expand_btn.par.drag = 'dragno'
        expand_btn.par.drop = 'dropno'
        expand_btn.par.clickthrough = True
    except Exception:
        pass
    etxt = expand_btn.create('textTOP', 'label_text')
    try:
        etxt.par.clickthrough = True
    except Exception:
        pass
    _sync_fx_accordion_expand_icon(expand_btn, True, CELL_FX_ROW_HDR)
    _ensure_cell_fx_header_drag(parent, hdr, sfx)
    _apply_fx_row_header_visual(hdr, title, row_h=CELL_FX_ROW_HDR)
    return hdr, expand_btn


def _ensure_layer_fx_row(layer, col, row_id, label, target, clip_type, bypass=None):
    panel = _ensure_layer_fx_panel()
    if panel is None:
        return None
    sfx = 'source' if row_id == 'source' else '{:04d}'.format(int(row_id))
    name = 'lfx_row_{}'.format(sfx)
    row = panel.op(name)
    if row is None:
        row = panel.create('containerCOMP', name)
    try:
        row.par.w = _cell_panel_w()
        row.par.align = 'left'
        row.par.clipping = True
        row.par.drop = 'usecallbacks'
        row.par.drag = 'dragno'
    except Exception:
        pass
    _wire_cell_fx_dragdrop(row)
    expanded = _source_row_expanded() if row_id == 'source' else bool(
        (_cell_fx_entry(layer, col, row_id) or {}).get('expanded'))
    hdr = row.op('lfx_row_hdr_{}'.format(sfx))
    if hdr is None:
        hdr, expand_btn = _create_layer_fx_row_header(
            row, row_id, label, bypass=bypass, draggable=(row_id != 'source'))
        _sync_fx_accordion_expand_icon(expand_btn, expanded, CELL_FX_ROW_HDR)
    else:
        try:
            hdr.par.clickthrough = False
        except Exception:
            pass
        t = hdr.op('title_text')
        if t is not None:
            try:
                t.par.text = str(label)
            except Exception:
                pass
        if row_id != 'source':
            b = hdr.op('lfx_bypass_{:04d}'.format(int(row_id)))
            if b is not None:
                try:
                    b.par.clickthrough = True
                except Exception:
                    pass
        e = hdr.op('lfx_expand_{}'.format(sfx))
        if e is not None:
            try:
                e.par.clickthrough = True
            except Exception:
                pass
            _sync_fx_accordion_expand_icon(e, expanded, CELL_FX_ROW_HDR)
    if target is not None and clip_type == 'tox':
        _heal_logo_overlay_imagefile_par(target)
    params = row.op('lfx_params')
    if params is None:
        params = row.create('parameterCOMP', 'lfx_params')
    try:
        params.par.header = True
        params.par.pagenames = True
        params.par.labels = True
        params.par.separators = True
        params.par.allowexpand = True
        params.par.pagescope = '*'
        params.par.parscope = '*'
        params.par.combinescopes = 'any'
        params.par.autoscroll = True
        params.par.display = expanded and target is not None
        params.par.enable = expanded and target is not None
        params.par.builtin = True
        params.par.custom = clip_type == 'tox' or bool(
            target is not None and getattr(target, 'customPars', None) and target.customPars)
        params.par.drag = 'dragno'
        params.par.drop = 'dropno'
        params.par.mousewheel = True
    except Exception:
        pass
    try:
        params.par.op.mode = 'constant'
        params.par.op.val = target.path if target is not None else ''
        if target is None:
            params.par.enable = False
            params.par.display = False
    except Exception:
        pass
    hdr = row.op('lfx_row_hdr_{}'.format(sfx))
    if hdr is None:
        hdr = _layer_fx_row_header(row)
    _ensure_cell_fx_header_drag(row, hdr, sfx)
    _sync_fx_accordion_header(hdr, row_h=CELL_FX_ROW_HDR)
    return row


def _layout_layer_fx_rows(content_h=None, layer=None, col=None):
    panel = _ensure_layer_fx_panel()
    if panel is None:
        return
    if content_h is None:
        try:
            content_h = int(panel.par.h.eval())
        except Exception:
            content_h = 300
    hint = panel.op('layer_fx_hint')
    hint_h = 20
    if hint is not None:
        try:
            hint.par.x = 0
            hint.par.y = 0
            hint.par.w = _cell_panel_w()
            hint.par.h = hint_h
        except Exception:
            pass
    for ch in list(panel.children):
        if ch.name.startswith('lfx_row_'):
            try:
                ch.par.y = -1000
            except Exception:
                pass
    r = _root()
    if r is None:
        return
    if layer is None or col is None:
        try:
            layer = int(float(r.par.Selectedlayer.eval()))
            col = int(float(r.par.Selectedcol.eval()))
        except Exception:
            return
    layer, col = int(layer), int(col)
    rows = []
    ctype, path = _get(layer, col)
    if hint is not None:
        try:
            hint.par.text = (
                'Effect cells can contain up to two effects'
                if path else 'Drop a .tox effect here')
        except Exception:
            pass
    if path:
        label = _cell_display_name(layer, col) or ('Video' if ctype == 'video' else 'Source')
        rows.append(('source', label, _cell_params_op(layer, col)[0], ctype, None))
    for entry in _cell_fx_list(layer, col):
        fx_id = int(entry.get('id', 0))
        slot = _slot(layer, col)
        fx_slot = _cell_fx_slot_comp(slot, fx_id) if slot else None
        target = fx_slot.op('tox') if fx_slot else None
        rows.append((fx_id, str(entry.get('label', 'Effect')), target, 'tox', entry.get('bypass')))
    expanded_count = sum(
        1 for row_id, _, _, _, _ in rows
        if (_source_row_expanded() if row_id == 'source' else bool(
            (_cell_fx_entry(layer, col, row_id) or {}).get('expanded')))
    )
    available_body_h = max(
        0, int(content_h) - hint_h - (CELL_FX_ROW_HDR * len(rows)))
    expanded_body_h = max(80, int(available_body_h / max(1, expanded_count)))
    y = int(content_h)
    for row_id, label, target, clip_type, bypass in rows:
        row = _ensure_layer_fx_row(layer, col, row_id, label, target, clip_type, bypass)
        if row is None:
            continue
        expanded = _source_row_expanded() if row_id == 'source' else bool(
            (_cell_fx_entry(layer, col, row_id) or {}).get('expanded'))
        body_h = expanded_body_h if expanded else 0
        row_h = CELL_FX_ROW_HDR + body_h
        y -= row_h
        try:
            row.par.x = 0
            row.par.y = y
            row.par.w = _cell_panel_w()
            row.par.h = row_h
            row.par.hmode = 'fixed'
            row.par.vmode = 'fixed'
            row.par.display = True
            row.par.enable = True
        except Exception:
            pass
        sfx = 'source' if row_id == 'source' else '{:04d}'.format(int(row_id))
        hdr = row.op('lfx_row_hdr_{}'.format(sfx))
        if hdr is not None:
            try:
                hdr.par.x = 0
                hdr.par.y = body_h
                hdr.par.w = _cell_panel_w()
                t = hdr.op('title_text')
                if t is not None:
                    _apply_fx_row_header_visual(hdr, t, row_h=CELL_FX_ROW_HDR)
            except Exception:
                pass
        params = row.op('lfx_params')
        if params is not None:
            try:
                params.par.x = 0
                params.par.y = 0
                params.par.w = _cell_panel_w()
                params.par.h = body_h
                params.par.display = expanded and target is not None
                params.par.enable = expanded and target is not None
            except Exception:
                pass


def _refresh_layer_fx_row(layer, col, row_id):
    _layout_layer_fx_rows(layer=layer, col=col)


def _refresh_layer_fx_ui(layer=None, col=None):
    r = _root()
    if r is None:
        return
    if layer is None or col is None:
        try:
            layer = int(float(r.par.Selectedlayer.eval()))
            col = int(float(r.par.Selectedcol.eval()))
        except Exception:
            return
    layer, col = int(layer), int(col)
    cell_change_log('layer_fx.start', 'L{} C{}'.format(layer, col))
    _wire_slot_cell_fx_chain(layer, col)
    cell_change_log('layer_fx.wired')
    panel = _ensure_layer_fx_panel()
    if panel is None:
        cell_change_log('layer_fx.no_panel')
        return
    wanted = {'lfx_row_source'}
    for entry in _cell_fx_list(layer, col):
        wanted.add('lfx_row_{:04d}'.format(int(entry.get('id', 0))))
    ctype, path = _get(layer, col)
    if not path:
        wanted = set(wanted) - {'lfx_row_source'}
    for ch in list(panel.children):
        if ch.name.startswith('lfx_row_') and ch.name not in wanted:
            try:
                ch.destroy()
            except Exception:
                pass

    def _sync_selected_cell_ui():
        cell_change_log('layer_fx.selected_cell_deferred')
        try:
            _sync_selected_cell_tab(layer, col, *_cell_params_op(layer, col))
            cell_change_log('layer_fx.selected_cell_done')
        except Exception as exc:
            cell_change_log('layer_fx.selected_cell.error', exc=exc)

    try:
        if not _defer_run(_sync_selected_cell_ui, delayFrames=1, fromOP=r):
            _sync_selected_cell_ui()
        else:
            cell_change_log('layer_fx.selected_cell_scheduled')
    except Exception as exc:
        cell_change_log('layer_fx.selected_cell_schedule.error', exc=exc)
        _sync_selected_cell_ui()

    _layout_layer_fx_rows(layer=layer, col=col)
    cell_change_log('layer_fx.layout_rows')
    _heal_fx_accordion_headers_in_panel(
        panel, 'lfx_row_', CELL_FX_ROW_HDR, repair_drag=_repair_cell_fx_accordion_drag)
    cell_change_log('layer_fx.heal_headers')
    _apply_params_tab_visibility()
    cell_change_log('layer_fx.tabs')
    _refresh_panel_exec_panels()
    cell_change_log('layer_fx.panel_exec')
    try:
        repair_map_dial_binds()
        cell_change_log('layer_fx.map_repair')
    except Exception as exc:
        cell_change_log('layer_fx.map_repair.error', exc=exc)
    cell_change_log('layer_fx.done')


def _layout_layer_fx_panel(content_h):
    panel = _ensure_layer_fx_panel()
    if panel is None:
        return
    try:
        panel.par.w = _cell_panel_w()
        panel.par.h = content_h
    except Exception:
        pass
    _layout_layer_fx_rows(content_h)
