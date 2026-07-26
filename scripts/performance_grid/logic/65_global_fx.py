PARAMS_TAB_H = 26
PARAMS_TAB_GAP = 2
GLOBAL_FX_ROW_HDR = 22
GLOBAL_FX_ROW_BODY = 148
GLOBAL_FX_MAX = 8
GLOBAL_FX_TAG = '__perf_global_fx__'

_GLOBAL_FX = []
_GLOBAL_FX_BY_SCENE = {}
_GLOBAL_FX_SCENE = None  # scene index the live _GLOBAL_FX list belongs to
_PARAMS_TAB = 'layer'
_GLOBAL_FX_GUARD = {'wiring': False, 'ensure': False}


def _program_out_expr():
    r = _root()
    if r is not None and r.op('global_fx_out') is not None:
        return "op('global_fx_out')"
    return "op('chain_out')"


def _sync_program_out_route():
    _route_program_out_to(_program_out_expr())


def _params_tab():
    return _PARAMS_TAB if _PARAMS_TAB in ('layer', 'global') else 'layer'


def set_params_tab(name):
    global _PARAMS_TAB
    name = str(name or 'layer').strip().lower()
    if name not in ('layer', 'global'):
        return
    if _PARAMS_TAB == name:
        return
    _PARAMS_TAB = name
    _apply_params_tab_visibility()
    try:
        sync_map_control_context()
    except Exception:
        pass
    try:
        r = _root()
        if r is not None:
            r.store('params_tab', name)
    except Exception:
        pass


def _restore_params_tab():
    global _PARAMS_TAB
    try:
        r = _root()
        if r is not None:
            stored = str(r.fetch('params_tab', 'layer') or 'layer').strip().lower()
            if stored in ('layer', 'global'):
                _PARAMS_TAB = stored
    except Exception:
        pass


def _global_fx_comp():
    r = _root()
    return r.op('global_fx') if r else None


def _global_fx_slots_parent():
    g = _global_fx_comp()
    return g.op('slots') if g else None


def _clone_global_fx_entry(entry):
    clone = dict(entry or {})
    clone['par_state'] = [dict(rec) for rec in entry.get('par_state') or []]
    return clone


def _clone_global_fx_list(effects):
    return [_clone_global_fx_entry(entry) for entry in (effects or [])]


def _global_fx_scene_list(scene=None):
    scene = int(_active_scene() if scene is None else scene)
    if scene not in _GLOBAL_FX_BY_SCENE:
        _GLOBAL_FX_BY_SCENE[scene] = []
    return _GLOBAL_FX_BY_SCENE[scene]


def _remember_active_global_fx_scene(scene=None):
    """Persist the live dial bank into a scene-owned deep copy."""
    global _GLOBAL_FX, _GLOBAL_FX_SCENE
    if scene is None:
        scene = _GLOBAL_FX_SCENE if _GLOBAL_FX_SCENE is not None else _active_scene()
    scene = int(scene)
    for entry in _GLOBAL_FX:
        fx_id = int(entry.get('id', 0))
        records = _snapshot_global_fx_params(fx_id)
        if records:
            entry['par_state'] = records
    _GLOBAL_FX_BY_SCENE[scene] = _clone_global_fx_list(_GLOBAL_FX)
    if _GLOBAL_FX_SCENE == scene:
        _GLOBAL_FX = _GLOBAL_FX_BY_SCENE[scene]


def _bind_global_fx_to_scene(scene=None):
    """Point the live list at the selected scene's stored FX bank."""
    global _GLOBAL_FX, _GLOBAL_FX_SCENE
    scene = int(_active_scene() if scene is None else scene)
    if _GLOBAL_FX_SCENE is not None and _GLOBAL_FX_SCENE != scene:
        _remember_active_global_fx_scene(_GLOBAL_FX_SCENE)
    elif _GLOBAL_FX_SCENE is None and _GLOBAL_FX:
        lst = _global_fx_scene_list(scene)
        if not lst:
            _GLOBAL_FX_BY_SCENE[scene] = _clone_global_fx_list(_GLOBAL_FX)
    _GLOBAL_FX = _global_fx_scene_list(scene)
    _GLOBAL_FX_SCENE = scene
    return _GLOBAL_FX


def _clear_global_fx_runtime():
    slots = _global_fx_slots_parent()
    if slots is not None:
        for child in list(slots.children):
            try:
                child.destroy()
            except Exception:
                pass


def _repair_global_fx_scene_aliases():
    """Break shared list references left by older builds."""
    seen = {}
    for scene in sorted(_GLOBAL_FX_BY_SCENE.keys()):
        effects = _GLOBAL_FX_BY_SCENE.get(scene)
        if effects is None:
            continue
        key = id(effects)
        if key in seen:
            _GLOBAL_FX_BY_SCENE[int(scene)] = _clone_global_fx_list(effects)
        else:
            seen[key] = int(scene)


def _activate_global_fx_scene(scene=None, remember_current=True, remember_scene=None):
    """Build only the selected scene's Global FX chain."""
    global _GLOBAL_FX, _GLOBAL_FX_SCENE
    target = int(_active_scene() if scene is None else scene)
    if remember_current:
        src = remember_scene
        if src is None:
            src = _GLOBAL_FX_SCENE if _GLOBAL_FX_SCENE is not None else _active_scene()
        src = int(src)
        if src != target or _GLOBAL_FX_SCENE is not None:
            _remember_active_global_fx_scene(src)
    _repair_global_fx_scene_aliases()
    _GLOBAL_FX = _global_fx_scene_list(target)
    _GLOBAL_FX_SCENE = target
    _clear_global_fx_runtime()
    _ensure_global_fx_network()
    for entry in _GLOBAL_FX:
        fx_id = int(entry.get('id', 0))
        _wire_global_fx_tox(fx_id, entry.get('path', ''), force_reload=True)
        _set_global_fx_bypass(fx_id, entry.get('bypass'))
        _restore_global_fx_params(fx_id, entry.get('par_state') or [])
    _wire_global_fx_chain()
    _refresh_global_fx_ui()


def _copy_global_fx_scene(src, dst):
    src, dst = int(src), int(dst)
    if _GLOBAL_FX_SCENE is not None:
        _remember_active_global_fx_scene(_GLOBAL_FX_SCENE)
    copied = _clone_global_fx_list(_global_fx_scene_list(src))
    _GLOBAL_FX_BY_SCENE[dst] = copied


def _delete_global_fx_scene(removed):
    global _GLOBAL_FX_SCENE
    removed = int(removed)
    if _GLOBAL_FX_SCENE is not None:
        _remember_active_global_fx_scene(_GLOBAL_FX_SCENE)
    remapped = {}
    for scene, effects in _GLOBAL_FX_BY_SCENE.items():
        scene = int(scene)
        if scene == removed:
            continue
        remapped[scene - 1 if scene > removed else scene] = effects
    _GLOBAL_FX_BY_SCENE.clear()
    _GLOBAL_FX_BY_SCENE.update(remapped)
    if _GLOBAL_FX_SCENE is not None:
        if _GLOBAL_FX_SCENE == removed:
            _GLOBAL_FX_SCENE = None
        elif _GLOBAL_FX_SCENE > removed:
            _GLOBAL_FX_SCENE -= 1


def _remap_global_fx_scenes(old_to_new):
    global _GLOBAL_FX_SCENE
    if _GLOBAL_FX_SCENE is not None:
        _remember_active_global_fx_scene(_GLOBAL_FX_SCENE)
    remapped = {}
    for old_scene, new_scene in old_to_new.items():
        if int(old_scene) in _GLOBAL_FX_BY_SCENE:
            remapped[int(new_scene)] = _GLOBAL_FX_BY_SCENE[int(old_scene)]
    _GLOBAL_FX_BY_SCENE.clear()
    _GLOBAL_FX_BY_SCENE.update(remapped)
    if _GLOBAL_FX_SCENE is not None and _GLOBAL_FX_SCENE in old_to_new:
        _GLOBAL_FX_SCENE = int(old_to_new[_GLOBAL_FX_SCENE])


def _next_global_fx_id():
    r = _root()
    n = 1
    if r is not None:
        try:
            n = max(1, int(r.fetch('global_fx_next_id', 1)))
        except Exception:
            n = 1
    used = {int(e.get('id', 0)) for e in _GLOBAL_FX}
    while n in used:
        n += 1
    if r is not None:
        try:
            r.store('global_fx_next_id', n + 1)
        except Exception:
            pass
    return n


def _global_fx_entry(fx_id):
    fx_id = int(fx_id)
    for entry in _GLOBAL_FX:
        if int(entry.get('id', -1)) == fx_id:
            return entry
    return None


def _global_fx_index(fx_id):
    fx_id = int(fx_id)
    for i, entry in enumerate(_GLOBAL_FX):
        if int(entry.get('id', -1)) == fx_id:
            return i
    return -1


def _global_fx_label(path):
    path = _norm_asset_path(path or '')
    if not path:
        return 'Effect'
    base = os.path.basename(path)
    if base.lower().endswith('.tox'):
        base = base[:-4]
    return base or 'Effect'


def _ensure_global_fx_out():
    """Create global_fx_out passthrough; does not touch program_sel (see _sync_program_out_route)."""
    r = _root()
    if r is None:
        return None
    out = r.op('global_fx_out')
    if out is None:
        try:
            out = r.create('selectTOP', 'global_fx_out')
            _bind_canvas_res(out)
        except Exception:
            return None
    if not _GLOBAL_FX:
        _set_top_expr(out, "op('chain_out')")
    return out


def _build_global_fx_slot(slots, fx_id):
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
    bypass = slot.create('switchTOP', 'bypass')
    _set_par(bypass, 'index', 0)
    in_sel.outputConnectors[0].connect(bypass.inputConnectors[0])
    tox_pick.outputConnectors[0].connect(bypass.inputConnectors[1])
    out = slot.create('outTOP', 'out1')
    bypass.outputConnectors[0].connect(out.inputConnectors[0])
    return slot


def _ensure_global_fx_network():
    if _GLOBAL_FX_GUARD['ensure']:
        return _global_fx_comp()
    _GLOBAL_FX_GUARD['ensure'] = True
    try:
        r = _root()
        if r is None:
            return None
        g = _global_fx_comp()
        if g is None:
            try:
                g = r.create('baseCOMP', 'global_fx')
                g.nodeX = 900
                g.nodeY = -400
            except Exception:
                return None
        slots = g.op('slots')
        if slots is None:
            try:
                slots = g.create('baseCOMP', 'slots')
            except Exception:
                return None
        for entry in _GLOBAL_FX:
            fx_id = int(entry.get('id', 0))
            if fx_id <= 0:
                continue
            name = 'fx_{:04d}'.format(fx_id)
            if slots.op(name) is None:
                _build_global_fx_slot(slots, fx_id)
        _ensure_global_fx_out()
        return g
    finally:
        _GLOBAL_FX_GUARD['ensure'] = False


def _global_fx_slot_comp(fx_id):
    slots = _global_fx_slots_parent()
    if slots is None:
        return None
    return slots.op('fx_{:04d}'.format(int(fx_id)))


def _set_global_fx_bypass(fx_id, bypass):
    entry = _global_fx_entry(fx_id)
    if entry is None:
        return
    entry['bypass'] = bool(bypass)
    slot = _global_fx_slot_comp(fx_id)
    sw = slot.op('bypass') if slot else None
    if sw is not None:
        try:
            # Input 0 is dry/in_sel; input 1 is the effect output.
            sw.par.index = 0 if entry['bypass'] else 1
        except Exception:
            pass
    _refresh_global_fx_row(fx_id)


def _toggle_global_fx_expanded(fx_id):
    entry = _global_fx_entry(fx_id)
    if entry is None:
        return
    entry['expanded'] = not bool(entry.get('expanded'))
    _layout_global_fx_rows()
    _refresh_global_fx_row(fx_id)


def _feed_global_fx_tox(slot):
    t = slot.op('tox') if slot else None
    if t is None:
        return
    _protect_generic_tox_resolution(t)
    _ensure_generic_tox_input_adapter(t)
    _heal_effect_tox(t, reload_external=False)
    feed_expr = "op('../in_sel')"
    for name in ('select_video_in', 'select_in', 'video_sel'):
        sel = t.op(name)
        if sel is not None:
            try:
                sel.par.top.expr = feed_expr
                sel.par.top.mode = ParMode.EXPRESS
                _configure_tox_feed_select(sel, 100)
            except Exception:
                pass
    if _is_generic_top_fx_tox(t):
        in_top = t.op('in1')
        if in_top is not None:
            try:
                in_top.par.top.expr = feed_expr
                in_top.par.top.mode = ParMode.EXPRESS
            except Exception:
                pass
    _apply_tox_render_scale(t)


def _refresh_global_fx_canvas_feed():
    """Re-feed global FX TOXs after canvas resolution changes."""
    if _GLOBAL_FX_GUARD.get('wiring'):
        return
    try:
        if not _GLOBAL_FX:
            return
        _ensure_global_fx_network()
        for entry in _GLOBAL_FX:
            slot = _global_fx_slot_comp(int(entry.get('id', 0)))
            if slot is not None:
                _feed_global_fx_tox(slot)
    except Exception:
        pass


def _wire_global_fx_tox(fx_id, path, force_reload=False):
    slot = _global_fx_slot_comp(fx_id)
    if slot is None:
        return False
    t = slot.op('tox')
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
    _feed_global_fx_tox(slot)
    try:
        bypass = slot.op('bypass')
        tox_pick = slot.op('tox_pick')
        if tox_pick is not None:
            _set_par(tox_pick, 'top', expr="op('tox/out1')")
        if bypass is not None:
            entry = _global_fx_entry(fx_id)
            bypass.par.index = 0 if entry and entry.get('bypass') else 1
    except Exception:
        pass
    return True


def _wire_global_fx_chain():
    if _GLOBAL_FX_GUARD['wiring']:
        return
    _GLOBAL_FX_GUARD['wiring'] = True
    try:
        r = _root()
        if r is None:
            return
        if not _GLOBAL_FX:
            out = _ensure_global_fx_out()
            if out is not None:
                _set_top_expr(out, "op('chain_out')")
            _sync_program_out_route()
            return
        _ensure_global_fx_network()
        chain_expr = "op('chain_out')"
        chain = r.op('chain_out')
        if chain is not None:
            chain_expr = "op('{}')".format(chain.path.replace('\\', '/'))
        prev_expr = chain_expr
        for entry in _GLOBAL_FX:
            fx_id = int(entry.get('id', 0))
            slot = _global_fx_slot_comp(fx_id)
            if slot is None:
                continue
            in_sel = slot.op('in_sel')
            if in_sel is not None:
                _set_top_expr(in_sel, prev_expr)
            _wire_global_fx_tox(fx_id, entry.get('path', ''), force_reload=False)
            out1 = slot.op('out1')
            if out1 is not None:
                prev_expr = "op('{}')".format(out1.path.replace('\\', '/'))
        out = r.op('global_fx_out')
        if out is not None:
            _set_top_expr(out, prev_expr)
        _sync_program_out_route()
    finally:
        _GLOBAL_FX_GUARD['wiring'] = False


def add_global_fx(path, index=None):
    path = _norm_asset_path(path or '')
    if not path or not path.lower().endswith('.tox'):
        return None
    _bind_global_fx_to_scene()
    if len(_GLOBAL_FX) >= GLOBAL_FX_MAX:
        print('Global FX: max {} effects'.format(GLOBAL_FX_MAX))
        return None
    fx_id = _next_global_fx_id()
    entry = {
        'id': fx_id,
        'path': _store_asset_path(path),
        'label': _global_fx_label(path),
        'bypass': False,
        'expanded': False,
        'par_state': [],
    }
    if index is None:
        _GLOBAL_FX.insert(0, entry)
    elif index < 0 or index > len(_GLOBAL_FX):
        _GLOBAL_FX.append(entry)
    else:
        _GLOBAL_FX.insert(int(index), entry)
    _ensure_global_fx_network()
    _wire_global_fx_tox(fx_id, path, force_reload=True)
    _wire_global_fx_chain()
    _refresh_global_fx_ui()
    set_params_tab('global')
    return fx_id


def remove_global_fx(fx_id):
    idx = _global_fx_index(fx_id)
    if idx < 0:
        return False
    entry = _GLOBAL_FX.pop(idx)
    fx_id = int(entry.get('id', 0))
    try:
        purge_map_control_bindings_for_global_fx(fx_id)
    except Exception:
        pass
    slot = _global_fx_slot_comp(fx_id)
    if slot is not None:
        try:
            slot.destroy()
        except Exception:
            pass
    ui = _root().op('ui') if _root() else None
    if ui is not None:
        row = ui.op('global_fx_panel')
        if row is not None:
            old = row.op('gfx_row_{:04d}'.format(int(entry.get('id', 0))))
            if old is not None:
                try:
                    old.destroy()
                except Exception:
                    pass
    _wire_global_fx_chain()
    _refresh_global_fx_ui()
    return True


def reload_global_fx(fx_id):
    """Reload one global effect from disk."""
    fx_id = int(fx_id)
    entry = _global_fx_entry(fx_id)
    path = str(entry.get('path', '') if entry else '').strip()
    if not path:
        print('No global effect to reload')
        return False
    par_state = _snapshot_global_fx_params(fx_id) or list(entry.get('par_state') or [])
    _wire_global_fx_tox(fx_id, path, force_reload=True)
    _restore_global_fx_params(fx_id, par_state)
    entry['par_state'] = par_state
    _wire_global_fx_chain()
    _refresh_global_fx_ui()
    print('Reloaded global effect {}'.format(_label(path)))
    return True


def relink_global_fx(fx_id, new_path=None):
    """Point a global effect at a moved/renamed .tox, then reload (keeps pars)."""
    fx_id = int(fx_id)
    entry = _global_fx_entry(fx_id)
    old_path = str(entry.get('path', '') if entry else '').strip()
    if not old_path:
        print('No global effect to relink')
        return False
    if not new_path:
        new_path = _pick_asset_file('Relink Global Effect TOX', ['tox'], old_path)
    new_path = _norm_asset_path(new_path)
    if not new_path:
        return False
    if not os.path.isfile(new_path) or not new_path.lower().endswith('.tox'):
        print('Relink: need a .tox file ->', new_path)
        return False
    par_state = _snapshot_global_fx_params(fx_id) or list(entry.get('par_state') or [])
    entry['path'] = _store_asset_path(new_path)
    entry['label'] = _global_fx_label(new_path)
    _wire_global_fx_tox(fx_id, new_path, force_reload=True)
    _restore_global_fx_params(fx_id, par_state)
    entry['par_state'] = par_state
    _wire_global_fx_chain()
    _refresh_global_fx_ui()
    print('Relinked global effect -> {}'.format(_label(new_path)))
    return True


def edit_tox_global_fx(fx_id):
    """Open a global effect .tox for editing."""
    fx_id = int(fx_id)
    entry = _global_fx_entry(fx_id)
    path = str(entry.get('path', '') if entry else '').strip()
    if not path:
        print('No .tox file found for global effect')
        return False
    slot = _global_fx_slot_comp(fx_id)
    tox = slot.op('tox') if slot else None
    tox_path = _resolve_tox_edit_path(path, tox)
    if not tox_path:
        print('No .tox file found for global effect')
        return False
    return open_tox_for_edit(tox_path)


def get_fx_clipboard():
    return dict(_FX_CLIPBOARD)


def _set_fx_clipboard(path, label='', bypass=False, expanded=False, par_state=None):
    _FX_CLIPBOARD.update({
        'path': _store_asset_path(path or ''),
        'label': str(label or ''),
        'bypass': bool(bypass),
        'expanded': bool(expanded),
        'par_state': [dict(rec) for rec in par_state or []],
    })
    return bool(_FX_CLIPBOARD.get('path'))


def copy_global_fx(fx_id):
    entry = _global_fx_entry(fx_id)
    if entry is None:
        return False
    records = _snapshot_global_fx_params(fx_id) or list(entry.get('par_state') or [])
    return _set_fx_clipboard(
        entry.get('path'), entry.get('label'), entry.get('bypass'),
        entry.get('expanded'), records)


def cut_global_fx(fx_id):
    if not copy_global_fx(fx_id):
        return False
    return remove_global_fx(fx_id)


def paste_global_fx(before_id=None):
    path = _FX_CLIPBOARD.get('path', '')
    if not path or len(_GLOBAL_FX) >= GLOBAL_FX_MAX:
        return None
    index = _global_fx_index(before_id) if before_id is not None else -1
    if before_id is not None and index < 0:
        index = None
    fx_id = add_global_fx(path, index=index)
    entry = _global_fx_entry(fx_id) if fx_id is not None else None
    if entry is None:
        return None
    entry['label'] = str(_FX_CLIPBOARD.get('label') or _global_fx_label(path))
    entry['expanded'] = bool(_FX_CLIPBOARD.get('expanded', False))
    _set_global_fx_bypass(fx_id, _FX_CLIPBOARD.get('bypass', False))
    records = list(_FX_CLIPBOARD.get('par_state') or [])
    entry['par_state'] = records
    _restore_global_fx_params(fx_id, records)
    _refresh_global_fx_ui()
    return fx_id


def move_global_fx(src_id, dst_id):
    si = _global_fx_index(src_id)
    di = _global_fx_index(dst_id)
    if si < 0 or di < 0 or si == di:
        return False
    for current in _GLOBAL_FX:
        fx_id = int(current.get('id', 0))
        current['par_state'] = (
            _snapshot_global_fx_params(fx_id) or list(current.get('par_state') or []))
    entry = _GLOBAL_FX.pop(si)
    # Keep the target's original index so two effects can swap order.
    _GLOBAL_FX.insert(di, entry)
    _wire_global_fx_chain()
    for current in _GLOBAL_FX:
        _restore_global_fx_params(current.get('id'), current.get('par_state') or [])
    _refresh_global_fx_ui()
    return True


def clear_global_fx(all_scenes=False):
    global _GLOBAL_FX, _GLOBAL_FX_SCENE
    _bind_global_fx_to_scene()
    ids = [int(e.get('id', 0)) for e in _GLOBAL_FX]
    _GLOBAL_FX[:] = []
    if all_scenes:
        _GLOBAL_FX_BY_SCENE.clear()
        _GLOBAL_FX_SCENE = None
        _GLOBAL_FX = []
    purge_paths = []
    for fx_id in ids:
        purge_paths.extend(_map_control_paths_for_global_fx(fx_id))
    try:
        purge_map_control_bindings_for_ops(purge_paths)
    except Exception:
        pass
    for fx_id in ids:
        slot = _global_fx_slot_comp(fx_id)
        if slot is not None:
            tox = slot.op('tox')
            if tox is not None:
                try:
                    _clear_map_out_binds_on_target(tox, 'tox')
                except Exception:
                    pass
    for fx_id in ids:
        slot = _global_fx_slot_comp(fx_id)
        if slot is not None:
            try:
                slot.destroy()
            except Exception:
                pass
    ui = _root().op('ui') if _root() else None
    panel = ui.op('global_fx_panel') if ui else None
    if panel is not None:
        for ch in list(panel.children):
            if ch.name.startswith('gfx_row_'):
                try:
                    ch.destroy()
                except Exception:
                    pass
    _wire_global_fx_chain()
    _refresh_global_fx_ui()


def _snapshot_global_fx_params(fx_id):
    slot = _global_fx_slot_comp(fx_id)
    target = slot.op('tox') if slot else None
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
        try:
            bind_expr = str(par.bindExpr or '').strip()
            if bind_expr:
                rec['bindExpr'] = bind_expr
        except Exception:
            pass
        records.append(rec)
    return records


def _restore_global_fx_params(fx_id, records):
    if not records:
        return 0
    slot = _global_fx_slot_comp(fx_id)
    target = slot.op('tox') if slot else None
    if target is None:
        return 0
    return _restore_op_params(target, records)


def _restore_op_params(target, records):
    restored = 0
    for rec in records:
        try:
            par = getattr(target.par, rec.get('name', ''))
        except Exception:
            continue
        try:
            if rec.get('bindExpr'):
                par.bindExpr = rec['bindExpr']
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
            if 'val' in rec:
                par.val = rec['val']
                restored += 1
        except Exception:
            pass
    return restored


def export_global_fx_state():
    if _GLOBAL_FX_SCENE is not None:
        _remember_active_global_fx_scene(_GLOBAL_FX_SCENE)
    else:
        _remember_active_global_fx_scene()
    rows = []
    active = int(_active_scene())
    for scene, effects in _GLOBAL_FX_BY_SCENE.items():
        for entry in effects:
            fx_id = int(entry.get('id', 0))
            records = list(entry.get('par_state') or [])
            if int(scene) == active:
                records = _snapshot_global_fx_params(fx_id) or records
            rows.append({
                'scene': int(scene),
                'id': fx_id,
                'path': _rel_or_abs_path(entry.get('path', '')),
                'label': str(entry.get('label', '')),
                'bypass': bool(entry.get('bypass')),
                'expanded': bool(entry.get('expanded')),
                'par_state': records,
            })
    return rows


def import_global_fx_state(rows):
    global _GLOBAL_FX, _GLOBAL_FX_SCENE
    clear_global_fx(all_scenes=True)
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        path = _resolve_stored_asset_path(str(row.get('path', '')).strip())
        if not path:
            continue
        # Legacy shared Global FX state belongs to whichever scene was active.
        scene = int(row.get('scene', _active_scene()))
        fx_id = int(row.get('id', 0)) or _next_global_fx_id()
        entry = {
            'id': fx_id,
            'path': _store_asset_path(path),
            'label': str(row.get('label', '') or _global_fx_label(path)),
            'bypass': bool(row.get('bypass')),
            'expanded': bool(row.get('expanded', False)),
            'par_state': list(row.get('par_state') or []),
        }
        _global_fx_scene_list(scene).append(entry)
    _activate_global_fx_scene(_active_scene(), remember_current=False)


def _params_tab_button_width():
    """Half-width tab tiles; side edges align with FX / Map Controller panels."""
    return max(60, (int(_cell_panel_w()) - PARAMS_TAB_GAP) // 2)


def _apply_params_tab_style(btn, active):
    if btn is None:
        return
    try:
        btn.par.bgalpha = SCENE_CONTROL_TILE_ALPHA
        btn.par.bgcolorr, btn.par.bgcolorg, btn.par.bgcolorb = SCENE_BTN_TILE_BG
    except Exception:
        pass
    txt = btn.op('label_text')
    if txt is None:
        return
    try:
        if active:
            txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = SCENE_ACTIVE_TEXT
        else:
            txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = SCENE_IDLE_TEXT
        txt.cook(force=True)
    except Exception:
        pass


def _create_params_tab_button(parent, name, label):
    btn = parent.op(name)
    if btn is None:
        btn = parent.create('containerCOMP', name)
    try:
        btn.par.w = _params_tab_button_width()
        btn.par.h = PARAMS_TAB_H
        btn.par.hmode = 'fixed'
        btn.par.vmode = 'fixed'
        btn.par.drop = 'dropno'
        btn.par.drag = 'dragno'
    except Exception:
        pass
    txt = btn.op('label_text')
    if txt is None:
        txt = btn.create('textTOP', 'label_text')
    _style_scene_tile_text(txt, label)
    try:
        txt.par.resolutionw = max(60, int(btn.par.w.eval()))
        txt.par.resolutionh = PARAMS_TAB_H
        txt.par.clickthrough = True
    except Exception:
        pass
    _apply_scene_tile_top(btn, txt)
    return btn


def _ensure_params_column_tabs():
    r = _root()
    ui = r.op('ui') if r else None
    if ui is None:
        return None
    bar = ui.op('params_tab_bar')
    if bar is None:
        bar = ui.create('containerCOMP', 'params_tab_bar')
    try:
        bar.par.w = _cell_panel_w()
        bar.par.h = PARAMS_TAB_H
        bar.par.hmode = 'fixed'
        bar.par.vmode = 'fixed'
        bar.par.align = 'none'
        bar.par.display = True
        bar.par.enable = True
        bar.par.clipping = False
    except Exception:
        pass
    _create_params_tab_button(bar, 'params_tab_layer', 'Cell')
    _create_params_tab_button(bar, 'params_tab_global', 'Global')
    _restore_params_tab()
    _apply_params_tab_visibility()
    return bar


def _apply_params_tab_visibility():
    r = _root()
    ui = r.op('ui') if r else None
    if ui is None:
        return
    tab = _params_tab()
    layer_btn = ui.op('params_tab_bar/params_tab_layer') if ui.op('params_tab_bar') else None
    global_btn = ui.op('params_tab_bar/params_tab_global') if ui.op('params_tab_bar') else None
    _apply_params_tab_style(layer_btn, tab == 'layer')
    _apply_params_tab_style(global_btn, tab == 'global')
    panel = ui.op('cell_params')
    gfx = ui.op('global_fx_panel')
    lfx = ui.op('layer_fx_panel')
    selected_type = ''
    selected_path = ''
    try:
        layer = int(float(r.par.Selectedlayer.eval()))
        col = int(float(r.par.Selectedcol.eval()))
        selected_type, selected_path = _get(layer, col)
    except Exception:
        pass
    show_layer_fx = tab == 'layer' and (selected_type == 'tox' or not selected_path)
    show_plain_cell = tab == 'layer' and bool(selected_path) and selected_type != 'tox'
    if panel is not None:
        try:
            panel.par.display = show_plain_cell
            panel.par.enable = show_plain_cell
        except Exception:
            pass
    if lfx is not None:
        try:
            lfx.par.display = show_layer_fx
            lfx.par.enable = show_layer_fx
        except Exception:
            pass
    if gfx is not None:
        try:
            gfx.par.display = tab == 'global'
            gfx.par.enable = tab == 'global'
        except Exception:
            pass
    map_sec = ui.op('map_control_section')
    if map_sec is not None:
        try:
            map_sec.par.display = True
            map_sec.par.enable = True
        except Exception:
            pass


def _wire_global_fx_dragdrop(comp):
    if comp is None:
        return
    r = _root()
    cb = _ensure_global_fx_dragdrop_dat()
    if cb is None:
        return
    try:
        comp.par.drop = 'usecallbacks'
        comp.par.drag = 'dragparent'
        comp.par.dragdropcallbacks = cb
    except Exception:
        pass


def _ensure_global_fx_dragdrop_dat():
    r = _root()
    if r is None:
        return None
    cb = r.op('global_fx_dragdrop')
    if cb is None:
        try:
            cb = r.create('textDAT', 'global_fx_dragdrop')
            cb.par.language = 'python'
        except Exception:
            return None
    try:
        cb.text = GLOBAL_FX_DRAGDROP
    except NameError:
        pass
    return cb


FX_HDR_DRAG_W = 24
FX_HDR_BYPASS_W = 28
FX_HDR_EXPAND_W = 22
FX_HDR_CHIP_PAD = 2
FX_HDR_TITLE_PAD = 2
FX_HDR_TITLE_TEXT_OFFSET_X = -14
FX_HDR_TITLE_RES_MARGIN = 40
FX_ACCORDION_ICON_SCALE = 0.62


def _fx_accordion_title_width(width=None):
    """Match Map Controller header title raster width."""
    return max(80, int(width or _cell_panel_w()) - FX_HDR_TITLE_RES_MARGIN)


def _fx_accordion_right_slots(width):
    """Fixed columns from the right edge: drag, expand, bypass."""
    edge = int(width) - FX_HDR_CHIP_PAD
    drag_x = edge - FX_HDR_DRAG_W
    edge = drag_x - FX_HDR_CHIP_PAD
    expand_x = edge - FX_HDR_EXPAND_W
    edge = expand_x - FX_HDR_CHIP_PAD
    bypass_x = edge - FX_HDR_BYPASS_W
    title_right = bypass_x - FX_HDR_CHIP_PAD
    return {
        'drag': drag_x,
        'expand': expand_x,
        'bypass': bypass_x,
        'title_right': title_right,
    }


def _fx_accordion_control(hdr, kind):
    if hdr is None:
        return None
    prefixes = {
        'drag': ('gfx_drag_', 'lfx_drag_'),
        'expand': ('gfx_expand_', 'lfx_expand_'),
        'bypass': ('gfx_bypass_', 'lfx_bypass_'),
    }.get(kind, ())
    for ch in hdr.children:
        if not ch.isCOMP:
            continue
        name = getattr(ch, 'name', '')
        for prefix in prefixes:
            if name.startswith(prefix):
                return ch
    return None


def _header_direct_child(hdr, name):
    if hdr is None:
        return None
    for ch in hdr.children:
        if getattr(ch, 'name', '') == name:
            return ch
    return None


def _position_fx_accordion_header_controls(hdr, width=None, row_h=None):
    """Title on the left; bypass, expand, drag handle on fixed right-side columns."""
    if hdr is None:
        return
    width = max(80, int(width or _cell_panel_w()))
    row_h = int(row_h or GLOBAL_FX_ROW_HDR)
    chip_h = row_h - 4
    chip_y = FX_HDR_CHIP_PAD
    slots = _fx_accordion_right_slots(width)
    drag = _fx_accordion_control(hdr, 'drag')
    expand = _fx_accordion_control(hdr, 'expand')
    bypass = _fx_accordion_control(hdr, 'bypass')
    if bypass is not None:
        try:
            bypass.par.w = FX_HDR_BYPASS_W
            bypass.par.h = chip_h
            bypass.par.x = slots['bypass']
            bypass.par.y = chip_y
            bypass.par.display = True
            bypass.par.enable = True
            bypass.par.layoutorder = 10
        except Exception:
            pass
    if expand is not None:
        try:
            expand.par.w = FX_HDR_EXPAND_W
            expand.par.h = chip_h
            expand.par.x = slots['expand']
            expand.par.y = chip_y
            expand.par.display = True
            expand.par.enable = True
            expand.par.layoutorder = 11
        except Exception:
            pass
    if drag is not None:
        try:
            drag.par.w = FX_HDR_DRAG_W
            drag.par.h = chip_h
            drag.par.x = slots['drag']
            drag.par.y = chip_y
            drag.par.display = True
            drag.par.enable = True
            drag.par.layoutorder = 12
        except Exception:
            pass
    title = hdr.op('title_text')
    if title is not None:
        title_w = _fx_accordion_title_width(width)
        try:
            title.par.resolutionw = title_w
            title.par.resolutionh = row_h
            title.par.positionx = FX_HDR_TITLE_PAD
            title.par.alignx = 'left'
            title.par.aligny = 'center'
            title.par.textoffsetx = FX_HDR_TITLE_TEXT_OFFSET_X
            title.par.textoffsety = 0
            title.cook(force=True)
        except Exception:
            pass


def _apply_fx_row_header_visual(hdr, title, width=None, row_h=None):
    """Draw accordion title on the header bar (containerCOMP needs par.top set)."""
    if hdr is None or title is None:
        return
    width = max(80, int(width or _cell_panel_w()))
    row_h = int(row_h or GLOBAL_FX_ROW_HDR)
    try:
        hdr.par.w = width
        hdr.par.h = row_h
        hdr.par.top = title
        hdr.par.topfill = 'best'
    except Exception:
        pass
    _position_fx_accordion_header_controls(hdr, width=width, row_h=row_h)


def _sync_fx_accordion_header(hdr, row_h=None, width=None):
    """Apply current accordion header layout (title offset, control positions)."""
    if hdr is None:
        return
    row_h = int(row_h or GLOBAL_FX_ROW_HDR)
    width = max(80, int(width or _cell_panel_w()))
    title = hdr.op('title_text')
    if title is None:
        _position_fx_accordion_header_controls(hdr, width=width, row_h=row_h)
        return
    _apply_fx_row_header_visual(hdr, title, width=width, row_h=row_h)


def _heal_fx_accordion_headers_in_panel(panel, row_prefix, row_h, repair_drag=None):
    """Re-layout every accordion header row in a Cell/Global FX panel."""
    if panel is None:
        return
    width = max(80, int(_cell_panel_w()))
    for row in panel.children:
        if not getattr(row, 'name', '').startswith(row_prefix):
            continue
        hdr = None
        for ch in row.children:
            if ch.isCOMP and 'row_hdr_' in ch.name:
                hdr = ch
                break
        if repair_drag is not None:
            try:
                repair_drag(row, hdr)
            except Exception:
                pass
        _sync_fx_accordion_header(hdr, row_h=row_h, width=width)


def _apply_fx_chip_visual(btn, txt, row_h=None):
    if btn is None or txt is None:
        return
    chip_h = int(row_h or GLOBAL_FX_ROW_HDR) - 4
    try:
        btn.par.top = txt
        btn.par.topfill = 'best'
        txt.par.resolutionh = chip_h
        txt.cook(force=True)
    except Exception:
        pass


def _fx_accordion_icon_tile_size(btn=None, row_h=None):
    chip_h = int(row_h or GLOBAL_FX_ROW_HDR) - 4
    chip_w = FX_HDR_EXPAND_W
    if btn is not None:
        try:
            chip_w = max(8, int(btn.par.w))
            chip_h = max(8, int(btn.par.h))
        except Exception:
            pass
    return chip_w, chip_h


def _configure_fx_accordion_icon_fit(fit, tile_w, tile_h):
    scale = max(0.2, min(1.0, float(FX_ACCORDION_ICON_SCALE)))
    if fit is None:
        return
    try:
        fit.par.outputresolution = 'custom'
        fit.par.resolutionw = max(8, int(tile_w))
        fit.par.resolutionh = max(8, int(tile_h))
        fit.par.resmult = False
        fit.par.fit = 'fitbest'
        fit.par.justifyh = 'center'
        fit.par.justifyv = 'center'
        fit.par.filtertype = 'linear'
        fit.par.punit = 'fraction'
        fit.par.px = 0.5
        fit.par.py = 0.5
        fit.par.tx = 0
        fit.par.ty = 0
        fit.par.sx = scale
        fit.par.sy = scale
        fit.par.bgcolorr = 0.0
        fit.par.bgcolorg = 0.0
        fit.par.bgcolorb = 0.0
        for pname in ('bgalpha', 'bgcolora'):
            try:
                getattr(fit.par, pname).val = 0.0
            except Exception:
                pass
    except Exception:
        pass


def _apply_fx_accordion_expand_icon_fallback(expand_btn, expanded, row_h=None):
    if expand_btn is None:
        return False
    row_h = int(row_h or GLOBAL_FX_ROW_HDR)
    etxt = expand_btn.op('label_text')
    if etxt is None:
        etxt = expand_btn.create('textTOP', 'label_text')
    try:
        etxt.par.text = 'v' if expanded else '^'
        etxt.par.font = TD_FONT
        etxt.par.fontsizex = TD_FONT_SIZE_SMALL
        etxt.par.fontsizey = TD_FONT_SIZE_SMALL
        etxt.par.resolutionw = FX_HDR_EXPAND_W
        etxt.par.resolutionh = row_h - 4
        etxt.par.bgalpha = 0.0
        etxt.par.fontcolorr, etxt.par.fontcolorg, etxt.par.fontcolorb = UI_TEXT_SECONDARY
        etxt.par.alignx = 'center'
        etxt.par.aligny = 'center'
        etxt.par.clickthrough = True
        etxt.par.display = True
    except Exception:
        pass
    _apply_fx_chip_visual(expand_btn, etxt, row_h)
    return True


def _set_fx_accordion_icon_transform(xform, expanded):
    """Closed: vertical flip (up). Open: default PNG (down)."""
    if xform is None:
        return
    try:
        xform.par.punit = 'fraction'
        xform.par.px = 0.5
        xform.par.py = 0.5
        xform.par.sx = 1.0
        xform.par.sy = 1.0 if expanded else -1.0
    except Exception:
        pass
    for name in ('rz', 'rotate'):
        try:
            getattr(xform.par, name).val = 0.0
        except Exception:
            pass
    try:
        xform.cook(force=True)
    except Exception:
        pass


def _sync_fx_accordion_expand_icon(expand_btn, expanded, row_h=None):
    """Accordion chevron from assets/accord.png; rotated when collapsed."""
    if expand_btn is None:
        return False
    row_h = int(row_h or GLOBAL_FX_ROW_HDR)
    path = _accordion_icon_path()
    if not path:
        return _apply_fx_accordion_expand_icon_fallback(expand_btn, expanded, row_h)
    chip_w, chip_h = _fx_accordion_icon_tile_size(expand_btn, row_h)
    etxt = expand_btn.op('label_text')
    if etxt is not None:
        try:
            etxt.par.text = ''
            etxt.par.display = False
        except Exception:
            pass
    src = expand_btn.op('icon_src')
    if src is not None and src.opType != 'moviefileinTOP':
        try:
            src.destroy()
        except Exception:
            pass
        src = None
    try:
        if src is None:
            src = expand_btn.create('moviefileinTOP', 'icon_src')
        _set_par_safe(src, 'outputresolution', 'useinput')
        _set_par_safe(src, 'play', True)
        src.par.file = path.replace('\\', '/')
        try:
            src.par.reloadpulse.pulse()
        except Exception:
            pass
        if not _top_has_image(src):
            return _apply_fx_accordion_expand_icon_fallback(expand_btn, expanded, row_h)
    except Exception:
        return _apply_fx_accordion_expand_icon_fallback(expand_btn, expanded, row_h)
    xform = expand_btn.op('icon_xform')
    if xform is None:
        try:
            xform = expand_btn.create('transformTOP', 'icon_xform')
        except Exception:
            xform = None
    if xform is not None:
        _set_fx_accordion_icon_transform(xform, expanded)
    fit = expand_btn.op('icon_fit')
    if fit is None:
        try:
            fit = expand_btn.create('fitTOP', 'icon_fit')
        except Exception:
            fit = None
    if fit is not None:
        _configure_fx_accordion_icon_fit(fit, chip_w, chip_h)
        nodes = [src]
        if xform is not None:
            nodes.append(xform)
        nodes.append(fit)
        _connect_top_chain(nodes)
    try:
        if fit is not None:
            expand_btn.par.top = fit.path
            expand_btn.par.topfill = 'best'
        expand_btn.par.clickthrough = True
    except Exception:
        return _apply_fx_accordion_expand_icon_fallback(expand_btn, expanded, row_h)
    return True


def _create_fx_accordion_drag_handle(hdr, drag_name, row_h=None, wire_dragdrop=None, width=None):
    """Create or repair a drag handle on an accordion header."""
    if hdr is None or not drag_name:
        return None
    row_h = int(row_h or GLOBAL_FX_ROW_HDR)
    width = max(80, int(width or _cell_panel_w()))
    chip_h = row_h - 4
    drag = _header_direct_child(hdr, drag_name)
    if drag is None:
        drag = hdr.create('containerCOMP', drag_name)
    try:
        drag.par.w = FX_HDR_DRAG_W
        drag.par.h = chip_h
        drag.par.y = FX_HDR_CHIP_PAD
        drag.par.drag = 'usecallbacks'
        drag.par.drop = 'dropno'
        drag.par.clickthrough = False
        drag.par.display = True
        drag.par.enable = True
        drag.par.layoutorder = 12
    except Exception:
        pass
    if wire_dragdrop is not None:
        wire_dragdrop(drag)
        wire_dragdrop(hdr)
    try:
        drag.par.drag = 'usecallbacks'
        drag.par.drop = 'dropno'
    except Exception:
        pass
    drag_text = drag.op('label_text')
    if drag_text is None:
        drag_text = drag.create('textTOP', 'label_text')
    try:
        drag_text.par.text = '|||'
        drag_text.par.font = TD_FONT
        drag_text.par.fontsizex = TD_FONT_SIZE_SMALL
        drag_text.par.fontsizey = TD_FONT_SIZE_SMALL
        drag_text.par.resolutionw = FX_HDR_DRAG_W
        drag_text.par.resolutionh = chip_h
        drag_text.par.bgalpha = 0.35
        drag_text.par.fontcolorr, drag_text.par.fontcolorg, drag_text.par.fontcolorb = UI_TEXT_PRIMARY
        drag_text.par.alignx = 'center'
        drag_text.par.aligny = 'center'
        drag_text.par.positionx = 0
        drag_text.par.positiony = 1
        drag_text.par.clickthrough = True
    except Exception:
        pass
    _apply_fx_chip_visual(drag, drag_text, row_h)
    _position_fx_accordion_header_controls(hdr, width=width, row_h=row_h)
    return drag


def _ensure_global_fx_panel():
    r = _root()
    ui = r.op('ui') if r else None
    if ui is None:
        return None
    panel = ui.op('global_fx_panel')
    if panel is None:
        panel = ui.create('containerCOMP', 'global_fx_panel')
    try:
        panel.par.w = _cell_panel_w()
        panel.par.hmode = 'fixed'
        panel.par.vmode = 'fixed'
        panel.par.align = 'none'
        panel.par.clipping = True
        panel.par.display = False
        panel.par.enable = False
        panel.par.bgcolorr, panel.par.bgcolorg, panel.par.bgcolorb = TD_BG_MAIN
        panel.par.bgalpha = 1.0
    except Exception:
        pass
    hint = panel.op('global_fx_hint')
    if hint is None:
        hint = panel.create('textTOP', 'global_fx_hint')
    try:
        hint.par.text = 'Drop .tox effects here'
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
    _wire_global_fx_dragdrop(panel)
    return panel


def _create_global_fx_row_header(parent, fx_id, label, bypass, expanded=True):
    hdr = parent.create('containerCOMP', 'gfx_row_hdr_{:04d}'.format(fx_id))
    try:
        hdr.par.h = GLOBAL_FX_ROW_HDR
        hdr.par.hmode = 'fixed'
        hdr.par.vmode = 'fixed'
        hdr.par.align = 'left'
        hdr.par.bgcolorr, hdr.par.bgcolorg, hdr.par.bgcolorb = UI_NAME_BAR_BG
        hdr.par.bgalpha = 1.0
        hdr.par.drag = 'dragno'
        hdr.par.drop = 'usecallbacks'
    except Exception:
        pass
    _wire_global_fx_dragdrop(hdr)
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
        title.par.resolutionh = GLOBAL_FX_ROW_HDR
        title.par.bgalpha = 0.0
        title.par.fontcolorr, title.par.fontcolorg, title.par.fontcolorb = UI_TEXT_PRIMARY
        title.par.alignx = 'left'
        title.par.aligny = 'center'
        title.par.positionx = FX_HDR_TITLE_PAD
        title.par.textoffsetx = FX_HDR_TITLE_TEXT_OFFSET_X
        title.par.clickthrough = True
    except Exception:
        pass
    bypass_btn = hdr.create('containerCOMP', 'gfx_bypass_{:04d}'.format(fx_id))
    try:
        bypass_btn.par.w = FX_HDR_BYPASS_W
        bypass_btn.par.h = GLOBAL_FX_ROW_HDR - 4
        bypass_btn.par.y = FX_HDR_CHIP_PAD
        bypass_btn.par.hmode = 'fixed'
        bypass_btn.par.vmode = 'fixed'
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
        btxt.par.resolutionh = GLOBAL_FX_ROW_HDR - 4
        btxt.par.bgalpha = 0.15 if bypass else 0.0
        btxt.par.fontcolorr, btxt.par.fontcolorg, btxt.par.fontcolorb = UI_TEXT_SECONDARY
        btxt.par.alignx = 'center'
        btxt.par.aligny = 'center'
        btxt.par.clickthrough = True
    except Exception:
        pass
    _apply_fx_chip_visual(bypass_btn, btxt, GLOBAL_FX_ROW_HDR)
    expand_btn = hdr.create('containerCOMP', 'gfx_expand_{:04d}'.format(fx_id))
    try:
        expand_btn.par.w = FX_HDR_EXPAND_W
        expand_btn.par.h = GLOBAL_FX_ROW_HDR - 4
        expand_btn.par.y = FX_HDR_CHIP_PAD
        expand_btn.par.hmode = 'fixed'
        expand_btn.par.vmode = 'fixed'
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
    _sync_fx_accordion_expand_icon(expand_btn, expanded, GLOBAL_FX_ROW_HDR)
    _create_fx_accordion_drag_handle(
        hdr, 'gfx_drag_{:04d}'.format(fx_id), GLOBAL_FX_ROW_HDR, _wire_global_fx_dragdrop)
    _apply_fx_row_header_visual(hdr, title, row_h=GLOBAL_FX_ROW_HDR)
    return hdr


def _ensure_global_fx_row(fx_id):
    panel = _ensure_global_fx_panel()
    if panel is None:
        return None
    name = 'gfx_row_{:04d}'.format(int(fx_id))
    row = panel.op(name)
    entry = _global_fx_entry(fx_id)
    if entry is None:
        if row is not None:
            try:
                row.destroy()
            except Exception:
                pass
        return None
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
    _wire_global_fx_dragdrop(row)
    hdr = row.op('gfx_row_hdr_{:04d}'.format(fx_id))
    if hdr is None:
        hdr = _create_global_fx_row_header(
            row, fx_id, entry.get('label', 'Effect'),
            entry.get('bypass'), entry.get('expanded'))
    else:
        try:
            hdr.par.clickthrough = False
        except Exception:
            pass
        t = hdr.op('title_text')
        if t is not None:
            try:
                t.par.text = str(entry.get('label', 'Effect'))
            except Exception:
                pass
        b = hdr.op('gfx_bypass_{:04d}'.format(fx_id))
        if b is not None:
            try:
                b.par.clickthrough = True
            except Exception:
                pass
            bt = b.op('label_text')
            if bt is not None:
                try:
                    bt.par.text = 'BYP' if entry.get('bypass') else ''
                    bt.par.bgalpha = 0.15 if entry.get('bypass') else 0.0
                except Exception:
                    pass
        e = hdr.op('gfx_expand_{:04d}'.format(fx_id))
        if e is not None:
            try:
                e.par.clickthrough = True
            except Exception:
                pass
            _sync_fx_accordion_expand_icon(
                e, bool(entry.get('expanded')), GLOBAL_FX_ROW_HDR)
    slot = _global_fx_slot_comp(fx_id)
    target = slot.op('tox') if slot else None
    if target is not None:
        _heal_logo_overlay_imagefile_par(target)
    params = row.op('gfx_params')
    if params is None:
        params = row.create('parameterCOMP', 'gfx_params')
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
        params.par.display = bool(entry.get('expanded'))
        params.par.enable = bool(entry.get('expanded'))
        params.par.builtin = True
        params.par.custom = True
        params.par.drag = 'dragno'
        params.par.drop = 'dropno'
        params.par.mousewheel = True
    except Exception:
        pass
    try:
        params.par.op.mode = 'constant'
        if target is not None:
            params.par.op.val = target.path
        else:
            params.par.op.val = ''
    except Exception:
        pass
    hdr = row.op('gfx_row_hdr_{:04d}'.format(fx_id))
    if hdr is not None:
        _create_fx_accordion_drag_handle(
            hdr, 'gfx_drag_{:04d}'.format(fx_id), GLOBAL_FX_ROW_HDR, _wire_global_fx_dragdrop)
    _sync_fx_accordion_header(hdr, row_h=GLOBAL_FX_ROW_HDR)
    return row


def _layout_global_fx_rows(content_h=None):
    panel = _ensure_global_fx_panel()
    if panel is None:
        return
    if content_h is None:
        try:
            content_h = int(panel.par.h.eval())
        except Exception:
            content_h = 300
    hint = panel.op('global_fx_hint')
    hint_h = 20
    if hint is not None:
        try:
            hint.par.x = 0
            hint.par.y = 0
            hint.par.w = _cell_panel_w()
            hint.par.h = hint_h
        except Exception:
            pass
    expanded_count = sum(1 for entry in _GLOBAL_FX if bool(entry.get('expanded')))
    available_body_h = max(
        0, int(content_h) - hint_h - (GLOBAL_FX_ROW_HDR * len(_GLOBAL_FX)))
    expanded_body_h = max(80, int(available_body_h / max(1, expanded_count)))
    y = int(content_h)
    for entry in _GLOBAL_FX:
        fx_id = int(entry.get('id', 0))
        row = _ensure_global_fx_row(fx_id)
        if row is None:
            continue
        expanded = bool(entry.get('expanded'))
        body_h = expanded_body_h if expanded else 0
        row_h = GLOBAL_FX_ROW_HDR + body_h
        y -= row_h
        try:
            row.par.x = 0
            row.par.y = y
            row.par.w = _cell_panel_w()
            row.par.h = row_h
            row.par.hmode = 'fixed'
            row.par.vmode = 'fixed'
        except Exception:
            pass
        hdr = row.op('gfx_row_hdr_{:04d}'.format(fx_id))
        if hdr is not None:
            try:
                hdr.par.x = 0
                hdr.par.y = body_h
                hdr.par.w = _cell_panel_w()
                t = hdr.op('title_text')
                if t is not None:
                    _apply_fx_row_header_visual(hdr, t, row_h=GLOBAL_FX_ROW_HDR)
            except Exception:
                pass
        params = row.op('gfx_params')
        if params is not None:
            try:
                params.par.x = 0
                params.par.y = 0
                params.par.w = _cell_panel_w()
                params.par.h = body_h
                params.par.display = expanded
                params.par.enable = expanded
            except Exception:
                pass


def _refresh_global_fx_row(fx_id):
    _ensure_global_fx_row(fx_id)
    _layout_global_fx_rows()


def _refresh_global_fx_ui():
    _ensure_params_column_tabs()
    panel = _ensure_global_fx_panel()
    if panel is None:
        return
    existing = {ch.name for ch in panel.children if ch.name.startswith('gfx_row_')}
    wanted = {'gfx_row_{:04d}'.format(int(e.get('id', 0))) for e in _GLOBAL_FX}
    for name in existing - wanted:
        old = panel.op(name)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass
    for entry in _GLOBAL_FX:
        _ensure_global_fx_row(int(entry.get('id', 0)))
    _layout_global_fx_rows()
    _heal_fx_accordion_headers_in_panel(panel, 'gfx_row_', GLOBAL_FX_ROW_HDR)
    _apply_params_tab_visibility()
    _refresh_panel_exec_panels()


def _layout_params_column(bottom_h):
    """Position tab bar + layer/global panels in the middle column."""
    r = _root()
    ui = r.op('ui') if r else None
    if ui is None:
        return
    _ensure_params_column_tabs()
    _ensure_global_fx_panel()
    _ensure_layer_fx_panel()
    _ensure_map_control_section()
    content_h = max(80, int(bottom_h) - PARAMS_TAB_H)
    map_h = _map_control_section_height()
    lfx_h = max(80, content_h - map_h)
    bar = ui.op('params_tab_bar')
    panel = ui.op('cell_params')
    gfx = ui.op('global_fx_panel')
    if bar is not None:
        try:
            bar.par.x = UI_PANEL_X
            bar.par.y = bottom_h - PARAMS_TAB_H
            bar.par.w = _cell_panel_w()
            bar.par.h = PARAMS_TAB_H
            tab_w = _params_tab_button_width()
            layer_btn = bar.op('params_tab_layer')
            global_btn = bar.op('params_tab_global')
            if layer_btn is not None:
                layer_btn.par.x = 0
                layer_btn.par.y = 0
                layer_btn.par.w = tab_w
                layer_btn.par.h = PARAMS_TAB_H
            if global_btn is not None:
                global_btn.par.x = tab_w + PARAMS_TAB_GAP
                global_btn.par.y = 0
                global_btn.par.w = tab_w
                global_btn.par.h = PARAMS_TAB_H
        except Exception:
            pass
    for comp in (panel, gfx):
        if comp is None:
            continue
        try:
            comp.par.x = UI_PANEL_X
            comp.par.y = map_h
            comp.par.w = _cell_panel_w()
            comp.par.h = lfx_h
            comp.par.hmode = 'fixed'
            comp.par.vmode = 'fixed'
            comp.par.align = 'none'
        except Exception:
            pass
    lfx = ui.op('layer_fx_panel') if ui else None
    if lfx is not None:
        try:
            lfx.par.x = UI_PANEL_X
            lfx.par.y = map_h
            lfx.par.w = _cell_panel_w()
            lfx.par.h = lfx_h
            lfx.par.hmode = 'fixed'
            lfx.par.vmode = 'fixed'
            lfx.par.align = 'none'
        except Exception:
            pass
    _layout_layer_fx_panel(lfx_h)
    _layout_global_fx_rows(lfx_h)
    _layout_map_control_section(map_h, bottom_y=0)
    _apply_params_tab_visibility()
