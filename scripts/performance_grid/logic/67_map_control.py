MAP_DIAL_COUNT = 8
MAP_DIAL_COLS = 8
MAP_CONTROL_ROW_HDR = 22
MAP_DIAL_GAP = 4
MAP_CONTROL_BODY_PAD = 6
MAP_DIAL_PAD = 4
MAP_DIAL_INDEX_H = 12
MAP_DIAL_BIND_VALUE_H = 11
MAP_DIAL_RANGE_H = 11
MAP_DIAL_RANGE_GAP = 2
MAP_DIAL_BIND_LABEL_FONT = max(6, TD_FONT_SIZE_SMALL - 1)
MAP_DIAL_BIND_EMPTY_LABEL = 'Drop\nParameter'
MAP_DIAL_BIND_LABEL_INDEX_GAP = 3
MAP_DIAL_BIND_LABEL_RANGE_GAP = 5
MAP_DIAL_BIND_LABEL_PAD_TOP = 5
MAP_DIAL_BIND_LABEL_PAD_BOTTOM = 2
MAP_DIAL_BIND_LABEL_LINES = 3
MAP_DIAL_BIND_LABEL_LINE_GAP = 1
MAP_DIAL_BIND_LABEL_LINE1_WIDTH_SCALE = 0.55
MAP_DIAL_BIND_LABEL_LINE2_WIDTH_SCALE = 0.42  # looser fit → more chars on row 2
MAP_DIAL_BIND_LABEL_GLYPH_SCALE = 0.62  # avg glyph width / font size (texture fit)
MAP_DIAL_BIND_LABEL_TEX_PAD = 6
MAP_DIAL_BIND_LABEL_LINE_H = MAP_DIAL_BIND_LABEL_FONT + 3
MAP_DIAL_BIND_LABEL_H = (
    MAP_DIAL_BIND_LABEL_LINE_H * MAP_DIAL_BIND_LABEL_LINES
    + MAP_DIAL_BIND_LABEL_LINE_GAP * (MAP_DIAL_BIND_LABEL_LINES - 1)
    + MAP_DIAL_BIND_LABEL_PAD_TOP + MAP_DIAL_BIND_LABEL_PAD_BOTTOM
)
MAP_DIAL_ROW_GAP = 3
MAP_DIAL_BIND_H = (
    MAP_DIAL_BIND_LABEL_H + MAP_DIAL_BIND_LABEL_RANGE_GAP
    + MAP_DIAL_RANGE_H + MAP_DIAL_ROW_GAP
    + MAP_DIAL_BIND_VALUE_H
)
MAP_DIAL_BIND_GAP = MAP_DIAL_ROW_GAP
MAP_DIAL_FADER_H = 68
MAP_DEFAULT_MIN = 0.0
MAP_DEFAULT_MAX = 1.0
MAP_RANGE_LIMIT = 100000.0
MAP_DIAL_H = (
    MAP_DIAL_PAD
    + MAP_DIAL_INDEX_H
    + MAP_DIAL_BIND_LABEL_INDEX_GAP
    + MAP_DIAL_BIND_H
    + MAP_DIAL_ROW_GAP
    + MAP_DIAL_FADER_H
    + MAP_DIAL_PAD
)


def _map_dial_layout_metrics(panel_w=None):
    """Fit dial cells to the params column width."""
    if panel_w is None:
        panel_w = _cell_panel_w()
    cols = MAP_DIAL_COLS
    inner_w = max(160, int(panel_w) - MAP_CONTROL_BODY_PAD * 2)
    dial_w = max(48, int((inner_w - MAP_DIAL_GAP * (cols - 1)) // cols))
    body_h = MAP_CONTROL_BODY_PAD * 2 + MAP_DIAL_H
    return dial_w, MAP_DIAL_H, body_h


def _map_dial_label_width(dial_w=None):
    """Usable bind-label width inside a dial cell (matches layout inner_w)."""
    if dial_w is None:
        dial_w, _, _ = _map_dial_layout_metrics()
    return max(24, int(dial_w) - MAP_DIAL_PAD * 2)


MAP_DIAL_W = 112  # default; overridden at layout time
MAP_CONTROL_BODY_H = MAP_CONTROL_BODY_PAD * 2 + MAP_DIAL_H
MAP_CONTROLLER_PAGE = 'Map Controller'
MAP_CONTROLLER_PAGE_LEGACY = 'Map Control'

_CELL_MAP_BY_KEY = {}
_GLOBAL_MAP_BY_SCENE = {}
_MAP_ACTIVE_CONTEXT = None
_MAP_SWITCH_GUARD = False
_MAP_DIAL_MIDI_BLOCK = set()
_MAP_DIAL_MIDI_SYNCED = set()
_MAP_DIAL_MIDI_LAST = {}
_MAP_DIAL_MIDI_PAINT_PENDING = set()
_MAP_DIAL_MIDI_WRITE = set()
_MAP_DIAL_DRAG_ACTIVE = set()
MAP_DIAL_MIDI_REARM_DELTA = 0.35
MAP_DIAL_INTERACTIVE_EPS = 1.0 / 1024.0
MAP_CONTROL_RELOAD_JSON_KEY = 'map_control_reload_json'


def _default_map_dial_state():
    return {
        'value': 0.0,
        'min': MAP_DEFAULT_MIN,
        'max': MAP_DEFAULT_MAX,
        'bind_expr': '',
        'target_expr': '',
        'driver_expr': '',
    }


_PULSE_DRIVER_VALUE_SUFFIX = 'value'
_AUDIO_MAP_DRIVER_NAMES = frozenset({
    'Audiooutkick',
    'Audioouthit',
    'Audiooutpeakhit',
})


def _pulse_slot_from_par_name(name):
    name = str(name or '')
    if not name.lower().startswith('pulse') or not name.lower().endswith(_PULSE_DRIVER_VALUE_SUFFIX):
        return None
    mid = name[5:-5]
    if not mid.isdigit():
        return None
    try:
        return int(mid)
    except Exception:
        return None


def _audio_driver_from_par_name(name):
    """Settings Audio Out Peak/Low/High/Kick/Hit (0-1) can drive Map*value like Pulse*value."""
    name = str(name or '')
    if name in _AUDIO_MAP_DRIVER_NAMES:
        return name
    return None


def _is_settings_owner(owner):
    if owner is None:
        return False
    settings = _settings_op()
    if settings is not None and owner == settings:
        return True
    try:
        return str(owner.path).replace('\\', '/').rstrip('/').endswith('/settings')
    except Exception:
        return False


def _is_map_driver_par(par):
    """Settings pulse/audio value pars drive Map*value (inbound), not Map*out."""
    if par is None:
        return False
    name = getattr(par, 'name', '')
    if _pulse_slot_from_par_name(name) is None and _audio_driver_from_par_name(name) is None:
        return False
    return _is_settings_owner(getattr(par, 'owner', None))


def _is_map_driver_expr(expr):
    expr = str(expr or '').strip()
    if not expr:
        return False
    low = expr.lower()
    if 'settings' not in low and '.par.pulse' not in low and '.par.audioout' not in low:
        return False
    tail = expr.rsplit('.par.', 1)[-1] if '.par.' in expr else expr
    return (
        _pulse_slot_from_par_name(tail) is not None
        or _audio_driver_from_par_name(tail) is not None
    )


def _pulse_slot_from_driver_expr(expr):
    if not expr:
        return None
    tail = str(expr).rsplit('.par.', 1)[-1] if '.par.' in str(expr) else str(expr)
    return _pulse_slot_from_par_name(tail)


def _current_map_context(r=None):
    if r is None:
        r = _root()
    tab = _params_tab()
    scene = int(_active_scene())
    if tab == 'global':
        return ('global', scene)
    layer = col = 1
    if r is not None:
        try:
            layer = int(float(r.par.Selectedlayer.eval()))
            col = int(float(r.par.Selectedcol.eval()))
        except Exception:
            pass
    return ('cell', scene, layer, col)


def _map_control_scope_label(r=None):
    ctx = _current_map_context(r)
    if ctx[0] == 'global':
        return 'Map Controller (Global)'
    return 'Map Controller (Cell)'


def _map_snapshot_target_expr(index, r=None):
    """Effect/cell param bound to Map*out — never a pulse driver par."""
    if r is None:
        r = _root()
    if r is None:
        return ''
    target = _recalled_map_bind_target(index, r)
    if target is not None and not _is_map_driver_par(target):
        return _absolute_bind_expr(target)
    expr = _map_bind_expr(index, r)
    if expr and not _is_map_driver_expr(expr):
        return expr
    return ''


def _snapshot_map_dial(index, r=None):
    if r is None:
        r = _root()
    target_expr = _map_snapshot_target_expr(index, r)
    driver_expr = _map_value_driver_expr(index, r)
    bind_expr = _map_bind_expr(index, r)
    if bind_expr and _is_map_driver_expr(bind_expr) and target_expr:
        bind_expr = target_expr
    lo, hi = _map_dial_range(index, r)
    return {
        'value': map_dial_norm(index, r),
        'min': lo,
        'max': hi,
        'bind_expr': bind_expr,
        'target_expr': target_expr,
        'driver_expr': driver_expr,
    }


def _snapshot_map_control_state(r=None):
    return {
        idx: _snapshot_map_dial(idx, r)
        for idx in range(1, MAP_DIAL_COUNT + 1)
    }


def _detach_map_dial(index, r=None, ctx=None):
    if r is None:
        r = _root()
    bound = _recalled_map_bind_target(index, r)
    if bound is None:
        bound = _resolve_bind_target(index, r)
    if bound is None and ctx is not None:
        st = (_stored_map_control_state(ctx) or {}).get(int(index)) or {}
        for key in ('target_expr', 'bind_expr'):
            expr = str(st.get(key, '') or '').strip()
            if not expr or _is_map_driver_expr(expr):
                continue
            try:
                bound = eval(expr, {'op': op})
            except Exception:
                bound = None
            if bound is not None and not _is_map_driver_par(bound):
                break
    if bound is not None and _target_bound_to_map_dial(index, bound, r):
        try:
            current = float(bound.eval())
            bound.mode = ParMode.CONSTANT
            bound.bindExpr = ''
            bound.expr = ''
            bound.val = current
        except Exception:
            pass
    elif bound is not None and not _is_map_driver_par(bound):
        try:
            if bound.mode == ParMode.BIND and is_map_out_bind_expr(
                    _par_bind_expression(bound)):
                current = float(bound.eval())
                bound.mode = ParMode.CONSTANT
                bound.bindExpr = ''
                bound.expr = ''
                bound.val = current
        except Exception:
            pass


_MAP_BIND_LOCK_KEY = 'map_bind_lock'


def _map_bind_lock_active(r=None):
    if r is None:
        r = _root()
    if r is None:
        return False
    try:
        return int(r.fetch(_MAP_BIND_LOCK_KEY, 0)) > 0
    except Exception:
        return False


def _map_bind_lock_begin(r=None):
    if r is None:
        r = _root()
    if r is None:
        return
    try:
        r.store(_MAP_BIND_LOCK_KEY, int(r.fetch(_MAP_BIND_LOCK_KEY, 0)) + 1)
    except Exception:
        pass


def _map_bind_lock_end(r=None):
    if r is None:
        r = _root()
    if r is None:
        return
    try:
        n = int(r.fetch(_MAP_BIND_LOCK_KEY, 0)) - 1
        if n <= 0:
            r.unstore(_MAP_BIND_LOCK_KEY)
        else:
            r.store(_MAP_BIND_LOCK_KEY, n)
    except Exception:
        pass


def _resolve_map_bind_target_par(master_par):
    if master_par is None:
        return None
    abs_expr = _absolute_bind_expr(master_par)
    if abs_expr:
        try:
            return eval(abs_expr, {'op': op})
        except Exception:
            pass
    return master_par


def _map_stored_range_is_default(lo, hi):
    try:
        lo = float(lo)
        hi = float(hi)
    except Exception:
        return True
    return lo == MAP_DEFAULT_MIN and hi == MAP_DEFAULT_MAX


def _resolve_map_dial_bind_target(target_expr, outbound_expr):
    for expr in (target_expr, outbound_expr):
        expr = str(expr or '').strip()
        if not expr or _is_map_driver_expr(expr):
            continue
        try:
            target = eval(expr, {'op': op})
        except Exception:
            target = None
        if target is not None and not _is_map_driver_par(target):
            return target
    return None


def _apply_map_dial_state(index, state, r=None, rebind=True, clear_bind=False):
    if r is None:
        r = _root()
    if r is None:
        return
    if clear_bind:
        _clear_map_dial_live_storage(index, r)
    state = dict(state or _default_map_dial_state())
    _ensure_map_control_pars(r)
    driver_expr = str(state.get('driver_expr', '') or '').strip()
    bind_expr = str(state.get('bind_expr', '') or '').strip()
    if not driver_expr and _is_map_driver_expr(bind_expr):
        driver_expr = bind_expr
    target_expr = str(state.get('target_expr', '') or '').strip()
    if target_expr and _is_map_driver_expr(target_expr):
        target_expr = ''
    outbound_expr = bind_expr
    if outbound_expr and _is_map_driver_expr(outbound_expr):
        outbound_expr = target_expr
    norm = max(0.0, min(1.0, float(state.get('value', 0.0))))
    st_lo = float(state.get('min', MAP_DEFAULT_MIN))
    st_hi = float(state.get('max', MAP_DEFAULT_MAX))
    rebind_expr = target_expr
    if not rebind_expr and outbound_expr and not _is_map_driver_expr(outbound_expr):
        rebind_expr = outbound_expr
    target = None
    if rebind and rebind_expr:
        target = _resolve_map_dial_bind_target(target_expr, outbound_expr)
    range_from_target = (
        target is not None
        and not _is_map_driver_par(target)
        and _map_stored_range_is_default(st_lo, st_hi)
    )
    if range_from_target:
        _apply_map_range_from_target(index, target, r, force=True)
        norm = _map_dial_norm_from_scaled(
            _read_map_bind_target_value(target), index, r)
    else:
        try:
            getattr(r.par, _map_min_par_name(index)).val = _clamp_map_range_value(
                st_lo)
            getattr(r.par, _map_max_par_name(index)).val = _clamp_map_range_value(
                st_hi)
        except Exception:
            pass
    _set_map_bind_outbound(index, outbound_expr, r)
    _set_map_driver_storage(index, driver_expr, r)
    if driver_expr:
        _ensure_map_value_driver_bind(index, driver_expr, r)
    else:
        _set_map_dial_norm(index, norm, r, force_cook=bool(rebind and rebind_expr))
    if not target_expr and not outbound_expr and not driver_expr:
        try:
            r.unstore(_map_range_seed_key(index))
        except Exception:
            pass
    if rebind and rebind_expr:
        if target is None:
            target = _resolve_map_dial_bind_target(target_expr, outbound_expr)
        if target is not None and not _is_map_driver_par(target):
            _remember_map_bind_target(index, target, r)
            _clear_duplicate_map_out_binds(index, keep_target=target, r=r)
            _ensure_target_map_bind(index, target, r, force=rebind)
            abs_expr = _absolute_bind_expr(target)
            if abs_expr:
                try:
                    r.store(_map_range_seed_key(index), abs_expr)
                except Exception:
                    pass
            if rebind:
                _heal_map_dial_output_chain(index, r)
                if int(index) not in _MAP_DIAL_DRAG_ACTIVE:
                    _sync_map_dial_norm_from_bound_target(index, r, force=True)
            return
        if rebind_expr and not _is_map_driver_expr(rebind_expr):
            keep_expr = outbound_expr or target_expr or rebind_expr
            _set_map_bind_outbound(index, keep_expr, r)
            try:
                r.store(_map_target_store_key(index), target_expr or keep_expr)
            except Exception:
                pass
            if target is None:
                target = _resolve_map_dial_bind_target(target_expr, outbound_expr)
            if target is None:
                try:
                    target = eval(keep_expr, {'op': op})
                except Exception:
                    target = None
            if target is not None and not _is_map_driver_par(target):
                _remember_map_bind_target(index, target, r)
                _heal_map_dial_output_chain(index, r)
                if int(index) not in _MAP_DIAL_DRAG_ACTIVE:
                    _sync_map_dial_norm_from_bound_target(index, r, force=True)
            return
    if clear_bind or (not rebind and not rebind_expr and not driver_expr):
        try:
            r.unstore(_map_target_store_key(index))
        except Exception:
            pass


def _stored_map_control_state(ctx):
    if not ctx:
        return {}
    if ctx[0] == 'global':
        return _normalize_map_dial_store(
            dict(_GLOBAL_MAP_BY_SCENE.get(int(ctx[1]), {}) or {}))
    return _normalize_map_dial_store(dict(
        _CELL_MAP_BY_KEY.get((int(ctx[1]), int(ctx[2]), int(ctx[3])), {}) or {}))


def _stored_map_dial_state(ctx, index):
    stored = _stored_map_control_state(ctx)
    idx = int(index)
    return stored.get(idx) or stored.get(str(idx)) or {}


def _persist_map_context(ctx, r=None):
    """Write the live dial bank into a cell/global store without detaching."""
    if r is None:
        r = _root()
    if r is None or not ctx:
        return False
    state = _normalize_map_dial_store(_snapshot_map_control_state(r))
    if ctx[0] == 'global':
        _GLOBAL_MAP_BY_SCENE[int(ctx[1])] = state
    else:
        _CELL_MAP_BY_KEY[(int(ctx[1]), int(ctx[2]), int(ctx[3]))] = state
    return True


def _commit_map_control_state(ctx=None, r=None):
    global _MAP_SWITCH_GUARD
    if _MAP_SWITCH_GUARD:
        return False
    if r is None:
        r = _root()
    if r is None:
        return False
    ctx = ctx or _MAP_ACTIVE_CONTEXT
    if ctx is None:
        return False
    _persist_map_context(ctx, r)
    for idx in range(1, MAP_DIAL_COUNT + 1):
        _detach_map_dial(idx, r)
    _clear_all_map_dial_live_storage(r)
    return True


def _restore_map_control_state(ctx, r=None):
    global _MAP_SWITCH_GUARD
    if r is None:
        r = _root()
    if r is None or ctx is None:
        return False
    if _map_bind_lock_active(r):
        return False
    _MAP_SWITCH_GUARD = True
    try:
        _clear_all_map_dial_live_storage(r)
        stored = _stored_map_control_state(ctx)
        for idx in range(1, MAP_DIAL_COUNT + 1):
            st = stored.get(idx)
            if st is None:
                _apply_map_dial_state(
                    idx, _default_map_dial_state(), r,
                    rebind=False, clear_bind=True)
                continue
            _apply_map_dial_state(idx, st, r)
    finally:
        _MAP_SWITCH_GUARD = False
    clear_map_dial_midi_sync()
    try:
        _reconcile_map_dial_live_binds(r)
    except Exception:
        pass
    try:
        refresh_map_control_display(r, paint=False)
    except Exception:
        pass
    return True


def _reconcile_map_dial_live_binds(r=None):
    """Re-wire Map*out binds after context restore (labels can outlive detached targets)."""
    if r is None:
        r = _root()
    if r is None:
        return False
    ctx = _MAP_ACTIVE_CONTEXT or _current_map_context(r)
    stored = _stored_map_control_state(ctx)
    ok = False
    for idx in range(1, MAP_DIAL_COUNT + 1):
        st = stored.get(idx) or {}
        pending_expr = str(
            st.get('target_expr', '') or st.get('bind_expr', '') or ''
        ).strip()
        if pending_expr and not _is_map_driver_expr(pending_expr):
            if not _is_map_bind_active(idx, r):
                _set_map_bind_outbound(idx, pending_expr, r)
                try:
                    r.store(_map_target_store_key(idx), pending_expr)
                except Exception:
                    pass
        if not _is_map_bind_active(idx, r):
            continue
        target = _resolve_bind_target(idx, r)
        if target is None or _is_map_driver_par(target):
            continue
        _clear_duplicate_map_out_binds(idx, keep_target=target, r=r)
        if _ensure_target_map_bind(idx, target, r, force=True):
            ok = True
    return ok


def _save_active_map_control_state(r=None):
    """Persist the live dial bank into the active cell/global map store."""
    global _MAP_ACTIVE_CONTEXT
    if r is None:
        r = _root()
    if r is None:
        return False
    ctx = _MAP_ACTIVE_CONTEXT or _current_map_context(r)
    _MAP_ACTIVE_CONTEXT = ctx
    if not _persist_map_context(ctx, r):
        return False
    try:
        _persist_map_control_reload_snapshot(_map_control_rows_for_persist(r), r)
    except Exception:
        pass
    return True


def _map_control_rows_for_persist(r=None):
    """Serialize in-memory map banks for COMP op-storage reload snapshot."""
    if r is None:
        r = _root()
    if r is None:
        return []
    _snapshot_live_context_to_store(r)
    rows = []
    for (scene, layer, col), dials in _CELL_MAP_BY_KEY.items():
        norm = _normalize_map_dial_store(dials)
        if not norm:
            continue
        rows.append({
            'scope': 'cell',
            'scene': int(scene),
            'layer': int(layer),
            'col': int(col),
            'dials': norm,
        })
    for scene, dials in _GLOBAL_MAP_BY_SCENE.items():
        norm = _normalize_map_dial_store(dials)
        if not norm:
            continue
        rows.append({
            'scope': 'global',
            'scene': int(scene),
            'dials': norm,
        })
    return rows


def _detach_stored_context_map_binds(ctx, r=None):
    """Release every Map*out bind recorded in a cell/global bank."""
    if r is None:
        r = _root()
    if r is None or ctx is None:
        return
    for idx in range(1, MAP_DIAL_COUNT + 1):
        _detach_map_dial(idx, r, ctx=ctx)
    stored = _stored_map_control_state(ctx) or {}
    for st in stored.values():
        for key in ('target_expr', 'bind_expr'):
            expr = str((st or {}).get(key, '') or '').strip()
            if not expr or _is_map_driver_expr(expr):
                continue
            try:
                bound = eval(expr, {'op': op})
            except Exception:
                continue
            if bound is None or _is_map_driver_par(bound):
                continue
            try:
                if bound.mode != ParMode.BIND:
                    continue
                if not is_map_out_bind_expr(_par_bind_expression(bound)):
                    continue
                current = float(bound.eval())
                bound.mode = ParMode.CONSTANT
                bound.bindExpr = ''
                bound.expr = ''
                bound.val = current
            except Exception:
                pass


def _switch_map_control_context(r=None):
    global _MAP_ACTIVE_CONTEXT
    ctx = _current_map_context(r)
    if _MAP_ACTIVE_CONTEXT is None:
        _MAP_ACTIVE_CONTEXT = ctx
        _restore_map_control_state(ctx, r)
        _update_map_control_header_label(r)
        return False
    if ctx == _MAP_ACTIVE_CONTEXT:
        return False
    leaving_ctx = _MAP_ACTIVE_CONTEXT
    _persist_map_context(leaving_ctx, r)
    _detach_stored_context_map_binds(leaving_ctx, r)
    _clear_all_map_dial_live_storage(r)
    _MAP_ACTIVE_CONTEXT = ctx
    _restore_map_control_state(ctx, r)
    _update_map_control_header_label(r)
    return True


def sync_map_control_context(r=None):
    if r is None:
        r = _root()
    if _map_bind_lock_active(r):
        return False
    first_init = _MAP_ACTIVE_CONTEXT is None
    switched = _switch_map_control_context(r)
    if switched or first_init:
        repair_map_dial_binds(r)
        try:
            _prime_all_map_dials_for_midi(r)
        except Exception:
            pass
        if switched:
            ctx = _MAP_ACTIVE_CONTEXT or _current_map_context(r)
            if ctx and ctx[0] == 'cell':
                try:
                    schedule_cell_map_bind_repair(
                        int(ctx[2]), int(ctx[3]), scene=int(ctx[1]), r=r)
                except Exception:
                    pass
    else:
        for idx in range(1, MAP_DIAL_COUNT + 1):
            if not _is_map_bind_active(idx, r):
                continue
            try:
                norm = float(_map_value_par(idx, r).eval())
            except Exception:
                norm = None
            if not _map_bind_chain_is_live(idx, r, norm=norm):
                _heal_map_dial_output_chain(idx, r)
                if norm is not None:
                    _sync_map_dial_bound_target(idx, norm, r)
    if switched or first_init:
        refresh_map_control_display(r)
    elif not global_transport_playing():
        refresh_map_control_display(r, light=True)
    return switched or first_init


def _ensure_map_live_context_for_midi(r=None, scope=None):
    """Align the live dial bank with UI selection before MIDI writes."""
    if r is None:
        r = _root()
    if r is None:
        return False
    scope = str(scope or '').strip().lower()
    if scope == 'global':
        return False
    if _MAP_ACTIVE_CONTEXT == _current_map_context(r):
        return False
    try:
        sync_map_control_context(r)
    except Exception:
        pass
    return True


def _maybe_migrate_legacy_map_control(r=None):
    if r is None:
        r = _root()
    if r is None:
        return
    try:
        if int(r.fetch('map_control_scoped_v1', 0)):
            return
    except Exception:
        pass
    ctx = _current_map_context(r)
    state = _snapshot_map_control_state(r)
    has_data = False
    for st in state.values():
        if str(st.get('bind_expr', '') or '').strip():
            has_data = True
            break
        if str(st.get('target_expr', '') or '').strip():
            has_data = True
            break
        if abs(float(st.get('value', 0.0))) > 0.001:
            has_data = True
            break
        if float(st.get('min', MAP_DEFAULT_MIN)) != MAP_DEFAULT_MIN:
            has_data = True
            break
        if float(st.get('max', MAP_DEFAULT_MAX)) != MAP_DEFAULT_MAX:
            has_data = True
            break
    if has_data:
        if ctx[0] == 'global':
            _GLOBAL_MAP_BY_SCENE[int(ctx[1])] = state
        else:
            _CELL_MAP_BY_KEY[(int(ctx[1]), int(ctx[2]), int(ctx[3]))] = state
    try:
        r.store('map_control_scoped_v1', 1)
    except Exception:
        pass


def _normalize_map_dial_store(dials):
    out = {}
    if not isinstance(dials, dict):
        return out
    for key, val in dials.items():
        try:
            idx = int(key)
        except Exception:
            continue
        if 1 <= idx <= MAP_DIAL_COUNT and isinstance(val, dict):
            out[idx] = dict(val)
    return out


def snapshot_cell_map_control(layer, col, scene=None):
    """Snapshot per-cell Map Controller dial bank (values, ranges, binds)."""
    scene = int(_active_scene() if scene is None else scene)
    layer, col = int(layer), int(col)
    ctx = ('cell', scene, layer, col)
    if _MAP_ACTIVE_CONTEXT == ctx:
        return _normalize_map_dial_store(_snapshot_map_control_state())
    stored = _CELL_MAP_BY_KEY.get((scene, layer, col))
    if stored:
        return _normalize_map_dial_store(stored)
    if _current_map_context() == ctx:
        return _normalize_map_dial_store(_snapshot_map_control_state())
    return {}


def _remap_map_bind_text(text, src_layer, src_col, dst_layer, dst_col):
    text = str(text or '').replace('\\', '/')
    if not text:
        return ''
    src_layer, src_col = int(src_layer), int(src_col)
    dst_layer, dst_col = int(dst_layer), int(dst_col)
    if src_layer == dst_layer and src_col == dst_col:
        return text
    old = 'layer_{}/col_{}'.format(src_layer, src_col)
    new = 'layer_{}/col_{}'.format(dst_layer, dst_col)
    return text.replace(old, new)


def _remap_map_dial_state_paths(dials, src_layer, src_col, dst_layer, dst_col):
    out = {}
    for idx, st in (_normalize_map_dial_store(dials) or {}).items():
        st = dict(st or {})
        for key in ('target_expr', 'bind_expr'):
            if key in st:
                st[key] = _remap_map_bind_text(
                    st.get(key), src_layer, src_col, dst_layer, dst_col)
        out[idx] = st
    return out


def restore_cell_map_control(layer, col, dials, src_layer=None, src_col=None, scene=None):
    """Restore a copied cell map bank; rebinds target paths to the destination cell."""
    global _MAP_ACTIVE_CONTEXT
    r = _root()
    scene = int(_active_scene() if scene is None else scene)
    layer, col = int(layer), int(col)
    remap_src_layer = int(layer if src_layer is None else src_layer)
    remap_src_col = int(col if src_col is None else src_col)
    mapped = _remap_map_dial_state_paths(
        dials, remap_src_layer, remap_src_col, layer, col)
    _CELL_MAP_BY_KEY[(scene, layer, col)] = mapped
    return True


def activate_cell_map_control(layer, col, scene=None, r=None, force=False):
    """Select a cell and apply its stored Map Controller bank to the live dials."""
    if r is None:
        r = _root()
    if r is None:
        return False
    layer, col = int(layer), int(col)
    scene = int(_active_scene() if scene is None else scene)
    try:
        r.par.Selectedlayer = layer
        r.par.Selectedcol = col
    except Exception:
        pass
    ctx = ('cell', scene, layer, col)
    if force and _MAP_ACTIVE_CONTEXT == ctx:
        _restore_map_control_state(ctx, r)
        try:
            repair_map_dial_binds(r)
        except Exception:
            pass
        for idx in range(1, MAP_DIAL_COUNT + 1):
            _paint_map_dial(idx, r=r)
        _update_map_control_header_label(r)
        return True
    sync_map_control_context(r)
    _update_map_control_header_label(r)
    return True


def schedule_cell_map_bind_repair(layer, col, scene=None, r=None):
    """Re-apply map binds after async TOX load (externaltox pulse)."""
    if r is None:
        r = _root()
    if r is None:
        return False
    layer, col = int(layer), int(col)
    scene = int(_active_scene() if scene is None else scene)

    def _repair():
        try:
            if _MAP_DIAL_DRAG_ACTIVE:
                return
            cur = _current_map_context(r)
            if cur != ('cell', scene, layer, col):
                return
            repair_map_dial_binds(r)
            try:
                _prime_all_map_dials_for_midi(r)
            except Exception:
                pass
            for idx in range(1, MAP_DIAL_COUNT + 1):
                _paint_map_dial(idx, r=r)
        except Exception:
            pass

    for delay in (0, 1, 4, 12, 30):
        _defer_run(_repair, delayFrames=int(delay), fromOP=r)
    return True


def clear_cell_map_control_store(layer, col, scene=None):
    """Drop stored Map Controller state for an empty/cleared grid cell."""
    global _MAP_SWITCH_GUARD
    scene = int(_active_scene() if scene is None else scene)
    layer, col = int(layer), int(col)
    _CELL_MAP_BY_KEY.pop((scene, layer, col), None)
    ctx = ('cell', scene, layer, col)
    if _MAP_ACTIVE_CONTEXT != ctx and _current_map_context() != ctx:
        return False
    _MAP_SWITCH_GUARD = True
    try:
        for idx in range(1, MAP_DIAL_COUNT + 1):
            _apply_map_dial_state(idx, _default_map_dial_state(), rebind=False)
    finally:
        _MAP_SWITCH_GUARD = False
    for idx in range(1, MAP_DIAL_COUNT + 1):
        _paint_map_dial(idx)
    return True


def _persist_map_control_reload_snapshot(rows, r=None):
    """Store map dial banks on the COMP so script reload can restore them."""
    import json
    if r is None:
        r = _root()
    if r is None:
        return False
    try:
        r.store(MAP_CONTROL_RELOAD_JSON_KEY, json.dumps(rows or []))
        return True
    except Exception:
        return False


def _load_map_control_reload_snapshot(r=None):
    import json
    if r is None:
        r = _root()
    if r is None:
        return []
    try:
        raw = str(r.fetch(MAP_CONTROL_RELOAD_JSON_KEY, '') or '').strip()
        if raw:
            rows = json.loads(raw)
            if isinstance(rows, list):
                return rows
    except Exception:
        pass
    return []


def _snapshot_live_context_to_store(r=None):
    """Persist the live dial bank for the active context without detaching targets."""
    global _MAP_ACTIVE_CONTEXT
    if r is None:
        r = _root()
    if r is None:
        return False
    ctx = _MAP_ACTIVE_CONTEXT or _current_map_context(r)
    if not ctx:
        return False
    _MAP_ACTIVE_CONTEXT = ctx
    return _persist_map_context(ctx, r)


def _snapshot_live_op_storage_dials(r=None):
    """Read live map dial binds from COMP op storage (survives script reload)."""
    if r is None:
        r = _root()
    if r is None:
        return {}
    state = {}
    for idx in range(1, MAP_DIAL_COUNT + 1):
        bind = str(r.fetch(_map_outbound_store_key(idx), '') or '').strip()
        target = str(r.fetch(_map_target_store_key(idx), '') or '').strip()
        if not bind and not target:
            bind_par = _map_bind_par(idx, r)
            if bind_par is not None:
                try:
                    if bind_par.mode == ParMode.BIND:
                        bind = str(getattr(bind_par, 'bindExpr', '') or '').strip()
                except Exception:
                    pass
        if not bind and not target:
            resolved = _resolve_bind_target(idx, r)
            if resolved is not None:
                target = _absolute_bind_expr(resolved)
                bind = target
        if not bind and not target:
            continue
        st = _default_map_dial_state()
        st['bind_expr'] = bind
        st['target_expr'] = target or bind
        try:
            st['value'] = float(getattr(r.par, _map_value_par_name(idx)).eval())
        except Exception:
            pass
        try:
            st['min'] = float(getattr(r.par, _map_min_par_name(idx)).eval())
            st['max'] = float(getattr(r.par, _map_max_par_name(idx)).eval())
        except Exception:
            pass
        state[idx] = st
    return _normalize_map_dial_store(state)


def _map_control_rows_from_live_op_storage(r=None):
    """Build a reload row for the active map context from live COMP storage."""
    if r is None:
        r = _root()
    if r is None:
        return []
    dials = _snapshot_live_op_storage_dials(r)
    if not dials:
        return []
    ctx = _current_map_context(r)
    if not ctx:
        return []
    if ctx[0] == 'global':
        return [{
            'scope': 'global',
            'scene': int(ctx[1]),
            'dials': dials,
        }]
    return [{
        'scope': 'cell',
        'scene': int(ctx[1]),
        'layer': int(ctx[2]),
        'col': int(ctx[3]),
        'dials': dials,
    }]


def _merge_map_control_rows(primary, fallback):
    """Merge map reload rows; primary wins, fallback fills missing cell/global banks."""
    merged = {}
    order = []
    for row in list(primary or []) + list(fallback or []):
        if not isinstance(row, dict):
            continue
        scope = str(row.get('scope', 'cell') or 'cell').strip().lower()
        scene = int(row.get('scene', 1))
        if scope == 'global':
            key = ('global', scene)
        else:
            key = ('cell', scene, int(row.get('layer', 1)), int(row.get('col', 1)))
        if key not in merged:
            order.append(key)
            merged[key] = dict(row)
            merged[key]['dials'] = _normalize_map_dial_store(row.get('dials'))
            continue
        dials = dict(merged[key].get('dials') or {})
        for idx, st in _normalize_map_dial_store(row.get('dials')).items():
            if idx not in dials or str((st or {}).get('bind_expr', '') or '').strip():
                dials[idx] = dict(st or {})
        merged[key]['dials'] = dials
    return [merged[key] for key in order]


def _rehydrate_map_store_from_op_storage(r=None):
    """Rebuild per-cell map store from op storage after script reload."""
    if r is None:
        r = _root()
    if r is None:
        return False
    ctx = _current_map_context(r)
    normalized = _snapshot_live_op_storage_dials(r)
    if not normalized:
        return False
    if ctx[0] == 'global':
        merged = dict(_GLOBAL_MAP_BY_SCENE.get(int(ctx[1]), {}) or {})
        merged.update(normalized)
        _GLOBAL_MAP_BY_SCENE[int(ctx[1])] = merged
    else:
        key = (int(ctx[1]), int(ctx[2]), int(ctx[3]))
        merged = dict(_CELL_MAP_BY_KEY.get(key, {}) or {})
        merged.update(normalized)
        _CELL_MAP_BY_KEY[key] = merged
    return True


def export_map_control_state(r=None):
    if r is None:
        r = _root()
    if r is None:
        return []
    rows = _map_control_rows_for_persist(r)
    rows = _merge_map_control_rows(rows, _map_control_rows_from_live_op_storage(r))
    _persist_map_control_reload_snapshot(rows, r)
    return rows


def import_map_control_state(rows, r=None):
    global _MAP_ACTIVE_CONTEXT
    if r is None:
        r = _root()
    rows = list(rows or [])
    if not rows:
        rows = _load_map_control_reload_snapshot(r)
    _CELL_MAP_BY_KEY.clear()
    _GLOBAL_MAP_BY_SCENE.clear()
    loaded = False
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        dials = _normalize_map_dial_store(row.get('dials'))
        if not dials:
            continue
        scope = str(row.get('scope', 'cell') or 'cell').strip().lower()
        scene = int(row.get('scene', _active_scene()))
        if scope == 'global':
            _GLOBAL_MAP_BY_SCENE[scene] = dials
        else:
            _CELL_MAP_BY_KEY[(scene, int(row.get('layer', 1)), int(row.get('col', 1)))] = dials
        loaded = True
    if not loaded and r is not None:
        _rehydrate_map_store_from_op_storage(r)
    if r is not None:
        _clear_all_map_dial_live_storage(r)
    _MAP_ACTIVE_CONTEXT = None
    clear_map_dial_midi_sync()
    sync_map_control_context(r)
    repair_map_dial_binds(r)


def restore_map_dial_binds_after_reload(r=None):
    """Reload-safe restore of map dial binds from COMP storage snapshot."""
    rows = _load_map_control_reload_snapshot(r)
    if rows:
        import_map_control_state(rows, r=r)
        return True
    if _rehydrate_map_store_from_op_storage(r):
        global _MAP_ACTIVE_CONTEXT
        _MAP_ACTIVE_CONTEXT = None
        sync_map_control_context(r)
        repair_map_dial_binds(r)
        return True
    return False


def _detach_all_map_control_targets(r=None):
    if r is None:
        r = _root()
    for idx in range(1, MAP_DIAL_COUNT + 1):
        _detach_map_dial(idx, r)
    for dials in list(_CELL_MAP_BY_KEY.values()) + list(_GLOBAL_MAP_BY_SCENE.values()):
        for idx, st in (dials or {}).items():
            try:
                dial_idx = int(idx)
            except Exception:
                continue
            if not (1 <= dial_idx <= MAP_DIAL_COUNT):
                continue
            target_expr = str((st or {}).get('target_expr', '') or '').strip()
            if not target_expr:
                continue
            try:
                target = eval(target_expr, {'op': op})
            except Exception:
                continue
            if target is None:
                continue
            try:
                if _target_bound_to_map_dial(dial_idx, target, r):
                    target.mode = ParMode.CONSTANT
                    target.bindExpr = ''
            except Exception:
                pass


def clear_map_control_state(r=None):
    """Reset all per-cell/global map dial banks and live dial parameters."""
    global _MAP_ACTIVE_CONTEXT
    if r is None:
        r = _root()
    if r is None:
        return False
    _detach_all_map_control_targets(r)
    _CELL_MAP_BY_KEY.clear()
    _GLOBAL_MAP_BY_SCENE.clear()
    _MAP_ACTIVE_CONTEXT = None
    _MAP_SWITCH_GUARD = True
    try:
        for idx in range(1, MAP_DIAL_COUNT + 1):
            _apply_map_dial_state(
                idx, _default_map_dial_state(), r, rebind=False, clear_bind=True)
    finally:
        _MAP_SWITCH_GUARD = False
    try:
        refresh_map_control_ui()
    except Exception:
        sync_map_control_context(r)
    return True


_MAP_PURGE_GUARD = False


def _map_dial_state_has_bind(st):
    st = st or {}
    if str(st.get('bind_expr', '') or '').strip():
        return True
    if str(st.get('target_expr', '') or '').strip():
        return True
    return bool(str(st.get('driver_expr', '') or '').strip())


def _map_control_paths_from_comp(comp):
    paths = []
    if comp is None:
        return paths
    try:
        paths.append(str(comp.path).replace('\\', '/'))
    except Exception:
        pass
    try:
        tox = comp.op('tox')
        if tox is not None:
            paths.append(str(tox.path).replace('\\', '/'))
    except Exception:
        pass
    return paths


def _clear_map_out_binds_for_op_paths(op_paths, r=None):
    """Drop Map*out binds on any clip/FX tox whose operator path is being removed."""
    if not op_paths:
        return 0
    cleared = 0
    for layer in range(1, _num_layers() + 1):
        for col in range(1, _num_cols() + 1):
            slot = _slot(layer, col)
            if slot is None:
                continue
            tox = slot.op('tox')
            if tox is not None and _op_path_matches(tox.path, op_paths):
                cleared += _clear_map_out_binds_on_target(tox, 'tox')
            for entry in _cell_fx_list(layer, col):
                fx_slot = _cell_fx_slot_comp(slot, entry.get('id'))
                if fx_slot is None:
                    continue
                fx_tox = fx_slot.op('tox')
                if fx_tox is None:
                    continue
                if (
                    _op_path_matches(fx_slot.path, op_paths)
                    or _op_path_matches(fx_tox.path, op_paths)
                ):
                    cleared += _clear_map_out_binds_on_target(fx_tox, 'tox')
    slots = _global_fx_slots_parent()
    if slots is not None:
        for ch in slots.children:
            try:
                fx_tox = ch.op('tox')
                if fx_tox is None:
                    continue
                if (
                    _op_path_matches(ch.path, op_paths)
                    or _op_path_matches(fx_tox.path, op_paths)
                ):
                    cleared += _clear_map_out_binds_on_target(fx_tox, 'tox')
            except Exception:
                pass
    return cleared


def _map_control_paths_for_cell_fx(slot, fx_id):
    """Operator paths for a stacked cell FX row (live or already destroyed)."""
    paths = []
    if slot is None or not fx_id:
        return paths
    fx_id = int(fx_id)
    fx_slot = _cell_fx_slot_comp(slot, fx_id)
    if fx_slot is not None:
        return _map_control_paths_from_comp(fx_slot)
    base = str(slot.path).replace('\\', '/').rstrip('/')
    name = 'fx_{:04d}'.format(fx_id)
    paths.append('{}/cell_fx/slots/{}'.format(base, name))
    paths.append('{}/cell_fx/slots/{}/tox'.format(base, name))
    return paths


def _map_control_paths_for_global_fx(fx_id):
    """Operator paths for a global FX row (live or already destroyed)."""
    paths = []
    if not fx_id:
        return paths
    fx_id = int(fx_id)
    slot = _global_fx_slot_comp(fx_id)
    if slot is not None:
        return _map_control_paths_from_comp(slot)
    slots = _global_fx_slots_parent()
    if slots is not None:
        base = str(slots.path).replace('\\', '/').rstrip('/')
        name = 'fx_{:04d}'.format(fx_id)
        paths.append('{}/{}'.format(base, name))
        paths.append('{}/{}/tox'.format(base, name))
    return paths


def _op_path_matches(path, op_paths):
    path = str(path or '').replace('\\', '/').rstrip('/')
    if not path or not op_paths:
        return False
    for raw in op_paths:
        candidate = str(raw or '').replace('\\', '/').rstrip('/')
        if not candidate:
            continue
        if path == candidate or path.startswith(candidate + '/'):
            return True
    return False


def _map_expr_references_op_path(expr, op_paths):
    expr = str(expr or '').replace('\\', '/')
    if not expr or not op_paths:
        return False
    for raw in op_paths:
        path = str(raw or '').replace('\\', '/').rstrip('/')
        if path and path in expr:
            return True
    return False


def _par_references_removed_ops(par, op_paths, r=None):
    if par is None or not op_paths:
        return False
    owner = getattr(par, 'owner', None)
    if owner is not None and _op_path_matches(owner.path, op_paths):
        return True
    bind_expr = _par_bind_expression(par)
    if bind_expr and _map_expr_references_op_path(bind_expr, op_paths):
        return True
    try:
        if par.mode == ParMode.BIND:
            master = getattr(par, 'bindMaster', None)
            if master is not None and master is not par:
                return _par_references_removed_ops(master, op_paths, r)
    except Exception:
        pass
    return False


def _expr_references_removed_ops(expr, op_paths, r=None):
    if _map_expr_references_op_path(expr, op_paths):
        return True
    expr = str(expr or '').strip()
    if not expr:
        return False
    if r is None:
        r = _root()
    if expr.startswith('par:') or expr.startswith('param:'):
        if r is None:
            return False
        try:
            par = _resolve_cell_par_bind(expr, r)
        except Exception:
            par = None
        if par is None:
            return False
        return _par_references_removed_ops(par, op_paths, r)
    try:
        resolved = eval(expr, {'op': op})
        if _par_references_removed_ops(resolved, op_paths, r):
            return True
    except Exception:
        pass
    return False


def _map_dial_state_references_ops(state, op_paths, r=None):
    state = state or {}
    for key in ('bind_expr', 'target_expr', 'driver_expr'):
        if _expr_references_removed_ops(state.get(key), op_paths, r):
            return True
    return False


def _map_bind_targets_removed_ops(index, op_paths, r=None):
    if r is None:
        r = _root()
    if r is None or not op_paths:
        return False
    index = int(index)
    for expr in (
        _map_bind_expr(index, r),
        _map_snapshot_target_expr(index, r),
        str(r.fetch(_map_outbound_store_key(index), '') or '').strip(),
        str(r.fetch(_map_target_store_key(index), '') or '').strip(),
        str(r.fetch(_map_driver_store_key(index), '') or '').strip(),
    ):
        if _expr_references_removed_ops(expr, op_paths, r):
            return True
    target = _resolve_bind_target(index, r)
    if _par_references_removed_ops(target, op_paths, r):
        return True
    for store in list(_CELL_MAP_BY_KEY.values()) + list(_GLOBAL_MAP_BY_SCENE.values()):
        st = (store or {}).get(index) or (store or {}).get(str(index))
        if _map_dial_state_references_ops(st, op_paths, r):
            return True
    return False


def _clear_map_dial_assignment(index, r=None):
    """Fully drop one map dial bind (live storage, labels, and target links)."""
    global _MAP_SWITCH_GUARD
    if r is None:
        r = _root()
    if r is None:
        return False
    _detach_map_dial(index, r)
    _MAP_SWITCH_GUARD = True
    try:
        _apply_map_dial_state(
            index, _default_map_dial_state(), r,
            rebind=False, clear_bind=True)
    finally:
        _MAP_SWITCH_GUARD = False
    try:
        r.unstore(_map_target_store_key(index))
        r.unstore(_map_range_seed_key(index))
    except Exception:
        pass
    return True


def _purge_selected_cell_pars_for_ops(op_paths, r=None):
    """Remove Selected Cell mirror parameters that bound to deleted operators."""
    if r is None:
        r = _root()
    if r is None or not op_paths:
        return False
    try:
        page = _get_selected_cell_page(r)
    except Exception:
        return False
    if page is None:
        return False
    changed = False
    for par in list(r.customPars):
        try:
            if par.page != page.name:
                continue
            if par.name == 'Cellinfo':
                continue
            if _par_references_removed_ops(par, op_paths, r):
                par.destroy()
                changed = True
        except Exception:
            pass
    return changed


def _scrub_map_dial_store(dials, op_paths, r=None):
    touched = False
    if not isinstance(dials, dict):
        return False
    for idx in list(dials.keys()):
        st = dials.get(idx)
        if _map_dial_state_references_ops(st, op_paths, r):
            dials[idx] = dict(_default_map_dial_state())
            touched = True
    return touched


def purge_map_control_bindings_for_cell_fx(layer, col, fx_id, scene=None):
    """Remove map dial assignments targeting one stacked cell FX row."""
    layer, col, fx_id = int(layer), int(col), int(fx_id)
    slot = _slot(layer, col)
    paths = _map_control_paths_for_cell_fx(slot, fx_id)
    fx_slot = _cell_fx_slot_comp(slot, fx_id) if slot is not None else None
    if fx_slot is not None:
        tox = fx_slot.op('tox')
        if tox is not None:
            _clear_map_out_binds_on_target(tox, 'tox')
    return purge_map_control_bindings_for_ops(paths)


def purge_map_control_bindings_for_ops(op_paths, r=None):
    """Drop map dial binds that target parameters on deleted effect operators."""
    global _MAP_PURGE_GUARD
    if r is None:
        r = _root()
    paths = []
    for raw in (op_paths if isinstance(op_paths, (list, tuple, set)) else [op_paths]):
        if not raw:
            continue
        path = str(raw).replace('\\', '/').rstrip('/')
        if path and path not in paths:
            paths.append(path)
    if not paths or r is None:
        return False

    changed = False
    _MAP_PURGE_GUARD = True
    try:
        try:
            _snapshot_live_context_to_store(r)
        except Exception:
            pass

        if _clear_map_out_binds_for_op_paths(paths, r):
            changed = True

        for dials in list(_CELL_MAP_BY_KEY.values()):
            if _scrub_map_dial_store(dials, paths, r):
                changed = True
        for dials in list(_GLOBAL_MAP_BY_SCENE.values()):
            if _scrub_map_dial_store(dials, paths, r):
                changed = True

        try:
            if _purge_selected_cell_pars_for_ops(paths, r):
                changed = True
        except Exception:
            pass

        for idx in range(1, MAP_DIAL_COUNT + 1):
            if not _map_bind_targets_removed_ops(idx, paths, r):
                continue
            _clear_map_dial_assignment(idx, r)
            changed = True

        ctx = _MAP_ACTIVE_CONTEXT
        if ctx is not None:
            stored = _normalize_map_dial_store(_stored_map_control_state(ctx))
            for idx in range(1, MAP_DIAL_COUNT + 1):
                st = stored.get(idx)
                if st and _map_dial_state_references_ops(st, paths, r):
                    stored[idx] = dict(_default_map_dial_state())
                    changed = True
            _persist_stored_map_dial_state(ctx, stored)
            _restore_map_control_state(ctx, r)
        elif changed:
            sync_map_control_context(r)

        try:
            if _prune_stale_map_dial_assignments(r):
                changed = True
        except Exception:
            pass

        if changed:
            try:
                _save_active_map_control_state(r)
            except Exception:
                pass
            try:
                _persist_map_control_reload_snapshot(
                    _map_control_rows_for_persist(r), r)
            except Exception:
                pass
    finally:
        _MAP_PURGE_GUARD = False

    if changed:
        for idx in range(1, MAP_DIAL_COUNT + 1):
            _paint_map_dial(idx, r=r)
    return changed


def purge_map_control_bindings_for_global_fx(fx_id):
    """Remove map dial assignments targeting one global FX row."""
    fx_id = int(fx_id)
    slot = _global_fx_slot_comp(fx_id)
    if slot is not None:
        tox = slot.op('tox')
        if tox is not None:
            _clear_map_out_binds_on_target(tox, 'tox')
    return purge_map_control_bindings_for_ops(_map_control_paths_for_global_fx(fx_id))


def purge_map_control_bindings_for_cell(layer, col, scene=None):
    """Remove map binds targeting any tox in a grid cell (source + stacked FX)."""
    paths = []
    slot = _slot(layer, col)
    if slot is not None:
        paths.extend(_map_control_paths_from_comp(slot.op('tox')))
        for entry in _cell_fx_list(layer, col, scene):
            paths.extend(_map_control_paths_for_cell_fx(slot, entry.get('id')))
    return purge_map_control_bindings_for_ops(paths)


def _update_map_control_header_label(r=None):
    ui = _root().op('ui') if _root() else None
    if ui is None:
        return
    section = ui.op('map_control_section')
    if section is None:
        return
    hdr = section.op('map_control_hdr')
    if hdr is None:
        return
    title = hdr.op('title_text')
    if title is None:
        return
    try:
        title.par.text = _map_control_scope_label(r)
        title.cook(force=True)
    except Exception:
        pass


def _map_dial_body(section=None):
    if section is None:
        ui = _root().op('ui') if _root() else None
        section = ui.op('map_control_section') if ui else None
    return section.op('map_control_dials') if section else None


def _map_dial_comp(index, section=None):
    body = _map_dial_body(section)
    if body is None:
        return None
    return body.op('map_dial_{}'.format(int(index)))


def _map_dial_knob_from_owner(owner):
    p = owner
    for _ in range(8):
        if p is None:
            break
        name = getattr(p, 'name', '')
        if name.startswith('map_dial_') and name.endswith('_knob'):
            return p
        try:
            p = p.parent()
        except Exception:
            break
    return None


def _map_control_page(r=None):
    if r is None:
        r = _root()
    if r is None:
        return None
    page = None
    for pg in r.customPages:
        if pg.name in (MAP_CONTROLLER_PAGE, MAP_CONTROLLER_PAGE_LEGACY):
            page = pg
            break
    if page is None:
        page = r.appendCustomPage(MAP_CONTROLLER_PAGE)
    try:
        if page.name != MAP_CONTROLLER_PAGE:
            page.name = MAP_CONTROLLER_PAGE
    except Exception:
        pass
    return page


def _map_value_par_name(index):
    return 'Map{}value'.format(int(index))


def _map_bind_par_name(index):
    return 'Map{}bind'.format(int(index))


def _map_min_par_name(index):
    return 'Map{}min'.format(int(index))


def _map_max_par_name(index):
    return 'Map{}max'.format(int(index))


def _map_output_par_name(index):
    return 'Map{}out'.format(int(index))


def _map_output_internal_expr(index):
    v = _map_value_par_name(index)
    mn = _map_min_par_name(index)
    mx = _map_max_par_name(index)
    return (
        "me.par.{mn} + me.par.{v} * (me.par.{mx} - me.par.{mn})"
    ).format(mn=mn, v=v, mx=mx)


def _map_output_bind_expr(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return ''
    return "op('{}').par.{}".format(
        r.path.replace('\\', '/'), _map_output_par_name(index))


def _map_range_par(index, r=None, which='min'):
    if r is None:
        r = _root()
    if r is None:
        return None
    name = _map_min_par_name(index) if which == 'min' else _map_max_par_name(index)
    try:
        return getattr(r.par, name)
    except AttributeError:
        return None


def _ensure_map_range_par(page, r, idx, which, default):
    name = _map_min_par_name(idx) if which == 'min' else _map_max_par_name(idx)
    label = '{} Min'.format(int(idx)) if which == 'min' else '{} Max'.format(int(idx))
    try:
        return getattr(r.par, name)
    except AttributeError:
        pass
    p = page.appendFloat(name, label=label)
    p.default = default
    p.val = default
    p.min = -MAP_RANGE_LIMIT
    p.max = MAP_RANGE_LIMIT
    p.normMin = -MAP_RANGE_LIMIT
    p.normMax = MAP_RANGE_LIMIT
    p.clampMin = False
    p.clampMax = False
    return p


def _clamp_map_range_value(value):
    return max(-MAP_RANGE_LIMIT, min(MAP_RANGE_LIMIT, float(value)))


def _map_dial_range(index, r=None):
    if r is None:
        r = _root()
    lo = MAP_DEFAULT_MIN
    hi = MAP_DEFAULT_MAX
    if r is not None:
        try:
            lo = _clamp_map_range_value(getattr(r.par, _map_min_par_name(index)).eval())
        except Exception:
            pass
        try:
            hi = _clamp_map_range_value(getattr(r.par, _map_max_par_name(index)).eval())
        except Exception:
            pass
    if hi <= lo:
        hi = lo + 1.0
    return lo, hi


def _format_map_number(value):
    v = float(value)
    if abs(v - round(v)) < 0.001:
        return '{:.0f}'.format(v)
    if abs(v) >= 100.0:
        return '{:.1f}'.format(v)
    return '{:.2f}'.format(v)


def _map_dial_range_text(index, r=None):
    lo, hi = _map_dial_range(index, r)
    return '{} – {}'.format(_format_map_number(lo), _format_map_number(hi))


def _map_dial_scaled_from_norm(norm, index, r=None):
    lo, hi = _map_dial_range(index, r)
    return lo + max(0.0, min(1.0, float(norm))) * (hi - lo)


def _map_dial_norm_from_scaled(value, index, r=None):
    lo, hi = _map_dial_range(index, r)
    span = hi - lo
    if span <= 0.0:
        return 0.0
    return max(0.0, min(1.0, (float(value) - lo) / span))


def _map_scaled_bind_expr(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return ''
    rp = r.path.replace('\\', '/')
    v = _map_value_par_name(index)
    mn = _map_min_par_name(index)
    mx = _map_max_par_name(index)
    return (
        "op('{r}').par.{mn} + op('{r}').par.{v} * "
        "(op('{r}').par.{mx} - op('{r}').par.{mn})"
    ).format(r=rp, v=v, mn=mn, mx=mx)


def _target_bound_to_map_dial(index, target, r=None):
    if target is None:
        return False
    value_par = _map_value_par(index, r)
    out_par = _map_output_par(index, r)
    try:
        if target.mode == ParMode.BIND:
            master = getattr(target, 'bindMaster', None)
            if master is not None and master in (value_par, out_par):
                return True
    except Exception:
        pass
    expr = _par_bind_expression(target)
    if not expr:
        return False
    for candidate in (
        _map_expr_for_value_par(index, r),
        _map_output_bind_expr(index, r),
        _map_scaled_bind_expr(index, r),
    ):
        if expr == candidate:
            return True
    return False


def _map_range_seed_key(index):
    return 'map_dial_range_seed_{}'.format(int(index))


def _par_norm_absolute_scale(par):
    """When min/max match normMin/normMax scaled by K, return full eval maximum K."""
    if par is None:
        return None
    try:
        norm_lo = float(par.normMin)
        norm_hi = float(par.normMax)
        abs_lo = float(par.min)
        abs_hi = float(par.max)
    except Exception:
        return None
    norm_span = norm_hi - norm_lo
    if norm_span <= 0.0 or norm_span > 1.001 or norm_lo < 0.0001:
        return None
    scale_lo = abs_lo / norm_lo
    scale_hi = abs_hi / norm_hi
    if scale_lo <= 0.0 or scale_hi <= 0.0:
        return None
    ref = max(scale_lo, scale_hi, 1.0)
    if abs(scale_lo - scale_hi) > max(0.01, 0.01 * ref):
        return None
    return scale_hi


def _absolute_to_par_val(par, absolute):
    """Convert a map/MIDI absolute value into the target par's normalized .val."""
    if par is None:
        return absolute
    slider_lo, slider_hi = _param_slider_range(par)
    try:
        norm_lo = float(par.normMin)
        norm_hi = float(par.normMax)
    except Exception:
        return absolute
    span = slider_hi - slider_lo
    norm_span = norm_hi - norm_lo
    if span <= 0.0 or norm_span <= 0.0:
        return absolute
    t = max(0.0, min(1.0, (float(absolute) - slider_lo) / span))
    return norm_lo + t * norm_span


def _param_slider_range(par):
    """Read the target parameter's usable value range for map dial scaling."""
    if par is None:
        return MAP_DEFAULT_MIN, MAP_DEFAULT_MAX
    norm_lo = norm_hi = None
    abs_lo = abs_hi = None
    try:
        norm_lo = float(par.normMin)
        norm_hi = float(par.normMax)
    except Exception:
        pass
    try:
        abs_lo = float(par.min)
        abs_hi = float(par.max)
    except Exception:
        pass
    norm_span = None
    abs_span = None
    if norm_lo is not None and norm_hi is not None and norm_hi > norm_lo:
        norm_span = norm_hi - norm_lo
    if abs_lo is not None and abs_hi is not None and abs_hi > abs_lo:
        abs_span = abs_hi - abs_lo
    full_scale = _par_norm_absolute_scale(par)
    if full_scale is not None:
        return 0.0, full_scale
    if norm_span is not None and abs_span is not None:
        # Norm 0-1 UI driving a wider absolute range (e.g. Glitch Speed 0-20).
        if norm_span <= 1.001 and abs_span > norm_span + 0.001:
            return abs_lo, abs_hi
    # Standard 0-1 performance parameters (opacity, mix, etc.) — dial travels 0-1
    # even when the TOX par has tighter normMin/normMax metadata (e.g. 0.3-0.97).
    if norm_span is not None and norm_lo >= 0.0 and norm_hi <= 1.001:
        return MAP_DEFAULT_MIN, MAP_DEFAULT_MAX
    if (
        abs_span is not None and abs_span <= 1.001
        and abs_lo is not None and abs_hi is not None
        and abs_lo >= 0.0 and abs_hi <= 1.001
    ):
        return MAP_DEFAULT_MIN, MAP_DEFAULT_MAX
    if norm_span is not None and norm_span > 1.001:
        return norm_lo, norm_hi
    if norm_span is not None:
        return norm_lo, norm_hi
    if abs_span is not None:
        return abs_lo, abs_hi
    return MAP_DEFAULT_MIN, MAP_DEFAULT_MAX


def _read_target_par_value(par):
    """Read a bind target's current value in map-dial slider units."""
    if par is None:
        return 0.0
    eval_v = val_v = None
    try:
        eval_v = float(par.eval())
    except Exception:
        pass
    try:
        val_v = float(par.val)
    except Exception:
        pass
    if eval_v is None and val_v is None:
        return 0.0
    if eval_v is None:
        raw = val_v
    elif val_v is None:
        raw = eval_v
    else:
        # Prefer eval (display value). Some pars (e.g. Logo Opacity) keep val=0 while eval=1.
        if abs(eval_v - val_v) > 0.0001:
            raw = eval_v
        else:
            raw = eval_v

    slider_lo, slider_hi = _param_slider_range(par)
    span = slider_hi - slider_lo
    if span <= 0.0:
        return raw
    if slider_lo <= raw <= slider_hi:
        return raw

    try:
        norm_lo = float(par.normMin)
        norm_hi = float(par.normMax)
        abs_lo = float(par.min)
        abs_hi = float(par.max)
        norm_span = norm_hi - norm_lo
        abs_span = abs_hi - abs_lo
    except Exception:
        return raw

    if 0.0 <= raw <= 1.001:
        if norm_span <= 1.001 and abs_span > norm_span + 0.001:
            return abs_lo + raw * abs_span
        if norm_span > 1.001:
            return norm_lo + raw * norm_span
        if span > 1.001:
            return slider_lo + raw * span

    return raw


def _cook_map_bind_target_owner(target):
    """One-shot cook so bound clip/TOX pars read correctly while transport is stopped."""
    owner = getattr(target, 'owner', None)
    if owner is None:
        return
    try:
        if bool(getattr(owner, 'allowCooking', True)):
            return
    except Exception:
        pass
    try:
        owner.cook(force=True)
    except Exception:
        pass


def _read_map_bind_target_value(target):
    if target is None:
        return 0.0
    _cook_map_bind_target_owner(target)
    return _read_target_par_value(target)


def _sync_map_dial_norm_from_bound_target(index, r=None, force=False):
    """Align Map*value with a bound parameter (for paused transport / cell restore)."""
    idx = int(index)
    if idx in _MAP_DIAL_DRAG_ACTIVE:
        return None
    if r is None:
        r = _root()
    if r is None or not _is_map_bind_active(idx, r):
        return None
    target = _resolve_bind_target(idx, r)
    if target is None or _is_map_driver_par(target):
        return None
    norm = _map_dial_norm_from_scaled(
        _read_map_bind_target_value(target), idx, r)
    if not force:
        try:
            current = float(_map_value_par(idx, r).eval())
            if abs(current - norm) < MAP_DIAL_INTERACTIVE_EPS:
                return norm
        except Exception:
            pass
    _set_map_dial_norm(idx, norm, r, force=True)
    return norm


def refresh_map_control_display(r=None, paint=True, light=False):
    """Sync dial positions from bound parameters and repaint (works while paused)."""
    if r is None:
        r = _root()
    if r is None:
        return False
    for idx in range(1, MAP_DIAL_COUNT + 1):
        _sync_map_dial_norm_from_bound_target(idx, r)
        if paint:
            _paint_map_dial(idx, r=r, light=light)
    return True


def _set_map_dial_norm(index, norm, r=None, force_cook=False, from_midi=False, force=False):
    """Write normalized dial position (0-1). Optional cook only when wiring binds."""
    if r is None:
        r = _root()
    if r is None:
        return False
    norm = max(0.0, min(1.0, float(norm)))
    try:
        value_par = getattr(r.par, _map_value_par_name(index))
    except AttributeError:
        return False
    endpoint = norm <= 0.0 or norm >= 1.0
    try:
        if not force and not endpoint and abs(float(value_par.val) - norm) < (1.0 / 127.0):
            return True
    except Exception:
        pass
    try:
        if value_par.mode != ParMode.CONSTANT:
            value_par.mode = ParMode.CONSTANT
            value_par.expr = ''
            value_par.bindExpr = ''
    except Exception:
        pass
    try:
        value_par.val = norm
    except Exception:
        return False
    if force_cook:
        _heal_map_dial_output_chain(index, r)
    return True


def _set_map_dial_norm_from_target(index, target, r=None):
    if r is None:
        r = _root()
    if r is None or target is None:
        return False
    if _target_bound_to_map_dial(index, target, r):
        return False
    return _set_map_dial_norm(
        index, _map_dial_norm_from_scaled(_read_target_par_value(target), index, r), r)


def _apply_map_range_from_target(index, target, r=None, force=False):
    if r is None:
        r = _root()
    if r is None or target is None:
        return False
    expr = _absolute_bind_expr(target)
    seed_key = _map_range_seed_key(index)
    lo, hi = _param_slider_range(target)
    if not force and expr:
        try:
            if str(r.fetch(seed_key, '') or '') == expr:
                # Same bind target — keep dial min/max (e.g. restored per-cell bank).
                return False
        except Exception:
            pass
    try:
        getattr(r.par, _map_min_par_name(index)).val = _clamp_map_range_value(lo)
        getattr(r.par, _map_max_par_name(index)).val = _clamp_map_range_value(hi)
    except Exception:
        return False
    if expr:
        try:
            r.store(seed_key, expr)
        except Exception:
            pass
    return True


def _map_output_par(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return None
    try:
        return getattr(r.par, _map_output_par_name(index))
    except AttributeError:
        return None


def _ensure_map_output_par(page, r, idx):
    name = _map_output_par_name(idx)
    try:
        par = getattr(r.par, name)
    except AttributeError:
        par = page.appendFloat(name, label='{} Out'.format(int(idx)))
        par.default = 0.0
        par.val = 0.0
        par.min = -MAP_RANGE_LIMIT
        par.max = MAP_RANGE_LIMIT
        par.normMin = -MAP_RANGE_LIMIT
        par.normMax = MAP_RANGE_LIMIT
        par.clampMin = False
        par.clampMax = False
    expr = _map_output_internal_expr(idx)
    try:
        if str(getattr(par, 'expr', '') or '').strip() != expr:
            par.expr = expr
        if par.mode != ParMode.EXPRESSION:
            par.mode = ParMode.EXPRESSION
    except Exception:
        try:
            par.mode = ParMode.EXPRESSION
            par.expr = expr
        except Exception:
            pass
    try:
        par.enable = False
    except Exception:
        pass
    return par


def _map_output_is_live(index, r=None):
    """True when Map*out expression tracks Map*value (not a stale CONSTANT)."""
    if r is None:
        r = _root()
    if r is None:
        return False
    out_par = _map_output_par(index, r)
    value_par = _map_value_par(index, r)
    if out_par is None or value_par is None:
        return False
    try:
        if out_par.mode != ParMode.EXPRESSION:
            return False
        expected_expr = _map_output_internal_expr(index)
        if str(getattr(out_par, 'expr', '') or '').strip() != expected_expr:
            return False
        norm = max(0.0, min(1.0, float(value_par.eval())))
        expected_val = _map_dial_scaled_from_norm(norm, index, r)
        actual_val = float(out_par.eval())
        tol = max(0.001, abs(expected_val) * 0.01 + 0.001)
        return abs(expected_val - actual_val) <= tol
    except Exception:
        return False


def _heal_map_output_par(index, r=None):
    """Restore Map*out expression mode — TD can leave a stale CONSTANT .val."""
    if r is None:
        r = _root()
    if r is None:
        return False
    _ensure_map_control_pars(r)
    out_par = _map_output_par(index, r)
    if out_par is None:
        return False
    expected = _map_output_internal_expr(index)
    try:
        out_par.expr = expected
        out_par.mode = ParMode.EXPRESSION
        try:
            out_par.enable = False
        except Exception:
            pass
    except Exception:
        return False
    return True


def _ensure_map_output_expr(index, r=None, force=False):
    """Keep Map*out in expression mode so outbound binds stay live."""
    if not force and _map_output_is_live(index, r):
        return True
    return _heal_map_output_par(index, r)


def _map_bind_chain_is_live(index, r=None, norm=None):
    """True when Map*out and the bound target both track Map*value."""
    if not _map_output_is_live(index, r):
        return False
    if not _is_map_bind_active(index, r):
        return True
    target = _resolve_bind_target(index, r)
    if target is None or _is_map_driver_par(target):
        return False
    if not _target_bound_to_map_dial(index, target, r):
        return False
    if norm is None:
        try:
            norm = float(_map_value_par(index, r).eval())
        except Exception:
            return False
    expected = _map_dial_scaled_from_norm(norm, index, r)
    try:
        actual = float(target.eval())
    except Exception:
        return False
    tol = max(0.001, abs(expected) * 0.01 + 0.001)
    return abs(expected - actual) <= tol


def _map_dial_target_tolerance(expected):
    return max(0.001, abs(float(expected)) * 0.01 + 0.001)


def _sync_map_dial_bound_target(index, norm, r=None):
    """Keep the bound clip/FX parameter in sync while dragging a map dial."""
    if r is None:
        r = _root()
    if r is None or not _is_map_bind_active(index, r):
        return False
    if _map_bind_chain_is_live(index, r, norm=norm):
        return True
    if not _map_output_is_live(index, r):
        _heal_map_output_par(index, r)
    target = _resolve_bind_target(index, r)
    if target is None or _is_map_driver_par(target):
        return False
    expected = _map_dial_scaled_from_norm(norm, index, r)
    par_val = _absolute_to_par_val(target, expected)
    tol = _map_dial_target_tolerance(expected)
    try:
        if abs(float(target.eval()) - expected) <= tol:
            return True
    except Exception:
        pass
    out_expr = _map_output_bind_expr(index, r)
    try:
        target.mode = ParMode.CONSTANT
        target.bindExpr = ''
        target.expr = ''
        target.val = par_val
        if out_expr:
            target.mode = ParMode.BIND
            target.bindExpr = out_expr
        return True
    except Exception:
        return False


def _heal_map_dial_output_chain(index, r=None):
    """Repair Map*out and re-apply the outbound bind after UI / cell refresh."""
    if r is None:
        r = _root()
    if r is None:
        return False
    _heal_map_output_par(index, r)
    if not _is_map_bind_active(index, r):
        return _map_output_is_live(index, r)
    target = _resolve_bind_target(index, r)
    if target is not None and not _is_map_driver_par(target):
        _ensure_target_map_bind(index, target, r, force=True)
    try:
        norm = float(_map_value_par(index, r).eval())
    except Exception:
        norm = None
    return _map_bind_chain_is_live(index, r, norm=norm)


def _map_bind_target_matches_context(index, r=None):
    """True when the bound parameter belongs to the active map cell context."""
    ctx = _MAP_ACTIVE_CONTEXT or _current_map_context(r)
    if not ctx or ctx[0] != 'cell':
        return True
    if r is None:
        r = _root()
    target = _resolve_bind_target(index, r)
    if target is None:
        return True
    try:
        owner = target.owner
        if owner is None:
            return True
        layer, col = _slot_layer_col_from_path(owner.path)
        if layer is None:
            return True
        return int(layer) == int(ctx[2]) and int(col) == int(ctx[3])
    except Exception:
        return True


def _prime_map_dial_midi_chain(index, norm, r=None):
    """Ensure Map*out bind chain is live for MIDI (no-op when already healthy)."""
    idx = int(index)
    if r is None:
        r = _root()
    if r is None:
        return False
    if (
        _map_bind_chain_is_live(idx, r, norm=norm)
        and _map_bind_target_matches_context(idx, r)
    ):
        return True
    if not _is_map_bind_active(idx, r):
        ctx = _MAP_ACTIVE_CONTEXT or _current_map_context(r)
        st = (_stored_map_control_state(ctx) or {}).get(idx) or {}
        expr = str(st.get('target_expr') or st.get('bind_expr') or '').strip()
        if not expr or _is_map_driver_expr(expr):
            return False
        _set_map_bind_outbound(idx, expr, r)
        try:
            r.store(_map_target_store_key(idx), expr)
        except Exception:
            pass
    _heal_map_dial_output_chain(idx, r)
    if not _map_bind_chain_is_live(idx, r, norm=norm):
        _sync_map_dial_bound_target(idx, norm, r)
    return _map_bind_chain_is_live(idx, r, norm=norm)


def _prime_all_map_dials_for_midi(r=None):
    """Wire all stored dial binds after a cell/context switch so MIDI works immediately."""
    if r is None:
        r = _root()
    if r is None:
        return False
    for idx in range(1, MAP_DIAL_COUNT + 1):
        try:
            norm = float(_map_value_par(idx, r).eval())
        except Exception:
            norm = 0.0
        _prime_map_dial_midi_chain(idx, norm, r)
    return True


def _ensure_target_map_bind(index, target=None, r=None, force=False):
    """Bind the target parameter to Map*out via bindExpr (one-way)."""
    if r is None:
        r = _root()
    if r is None:
        return False
    _ensure_map_output_expr(index, r, force=force)
    if target is None:
        target = _resolve_bind_target(index, r)
    if target is None:
        return False
    _clear_duplicate_map_out_binds(index, keep_target=target, r=r)
    out_expr = _map_output_bind_expr(index, r)
    if not out_expr:
        return False
    if not force:
        try:
            if (
                target.mode == ParMode.BIND
                and _par_bind_expression(target) == out_expr
                and _target_bound_to_map_dial(index, target, r)
            ):
                return True
        except Exception:
            pass
    try:
        target.mode = ParMode.BIND
        target.bindExpr = out_expr
    except Exception:
        return False
    return True


def _apply_map_dial_scaled_bind(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return False
    if not _is_map_bind_active(index, r):
        return False
    return _ensure_target_map_bind(index, r=r)


def on_map_dial_range_change(index, r=None):
    if _MAP_SWITCH_GUARD:
        return False
    if r is None:
        r = _root()
    if r is None:
        return False
    if _map_bind_lock_active(r):
        return False
    _apply_map_dial_scaled_bind(index, r)
    _paint_map_dial(index, r=r)
    return True


def set_map_dial_range_boundary(index, which, value, r=None):
    if r is None:
        r = _root()
    par = _map_range_par(index, r, which)
    if par is None:
        return False
    try:
        par.val = _clamp_map_range_value(value)
    except Exception:
        return False
    return on_map_dial_range_change(index, r)


def _map_dialog_ok(info):
    if info is None:
        return False
    try:
        if int(info.get('buttonNum', 0) or 0) == 1:
            return True
    except Exception:
        pass
    return str(info.get('button', '') or '').strip().upper() in ('OK', '1')


def _apply_map_dial_range_text(index, text, r=None):
    text = str(text or '').strip().replace(';', ',')
    parts = [p.strip() for p in text.split(',') if p.strip()]
    if len(parts) < 2:
        parts = [p for p in text.split() if p]
    if len(parts) < 2:
        return False
    try:
        new_lo = float(parts[0])
        new_hi = float(parts[1])
    except ValueError:
        return False
    set_map_dial_range_boundary(index, 'min', new_lo, r)
    set_map_dial_range_boundary(index, 'max', new_hi, r)
    return True


def edit_map_dial_range_dialog(index, r=None):
    return _edit_map_dial_range_dialog_prompt(index, r)


def _edit_map_dial_range_dialog_prompt(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return False
    _ensure_map_control_pars(r)
    lo, hi = _map_dial_range(index, r)
    default = '{}, {}'.format(_format_map_number(lo), _format_map_number(hi))
    idx = int(index)

    def _on_dialog(info):
        try:
            if not _map_dialog_ok(info):
                return
            text = info.get('enteredText', '')
            if not _apply_map_dial_range_text(idx, text, r):
                print('Map range: could not parse "{}"'.format(text))
        except Exception as exc:
            print('Map range apply failed:', exc)

    try:
        op.TDResources.PopDialog.OpenDefault(
            text='Enter minimum and maximum, comma separated (e.g. 0, 10):',
            title='Dial {} — Min / Max'.format(idx),
            buttons=['OK', 'Cancel'],
            callback=_on_dialog,
            textEntry=default,
            escButton=2,
            enterButton=1,
            escOnClickAway=True,
        )
        return True
    except Exception as exc:
        print('Map range dialog failed:', exc)
        return False


def edit_map_dial_range_field(index, which, r=None):
    return _edit_map_dial_range_field_prompt(index, which, r)


def _edit_map_dial_range_field_prompt(index, which, r=None):
    if r is None:
        r = _root()
    if r is None:
        return False
    _ensure_map_control_pars(r)
    lo, hi = _map_dial_range(index, r)
    current = lo if which == 'min' else hi
    label = 'Minimum' if which == 'min' else 'Maximum'
    idx = int(index)
    which = str(which or '').strip().lower()

    def _on_dialog(info):
        try:
            if not _map_dialog_ok(info):
                return
            text = str(info.get('enteredText', '') or '').strip()
            if not text:
                return
            val = float(text)
            set_map_dial_range_boundary(idx, which, val, r)
        except ValueError:
            print('Map range: invalid number "{}"'.format(info.get('enteredText', '')))
        except Exception as exc:
            print('Map range apply failed:', exc)

    try:
        op.TDResources.PopDialog.OpenDefault(
            text='Type {} value:'.format(label.lower()),
            title='Dial {} — {}'.format(idx, label),
            buttons=['OK', 'Cancel'],
            callback=_on_dialog,
            textEntry=_format_map_number(current),
            escButton=2,
            enterButton=1,
            escOnClickAway=True,
        )
        return True
    except Exception as exc:
        print('Map range edit failed:', exc)
        return False


def nudge_map_dial_range_field(index, which, delta, r=None):
    if r is None:
        r = _root()
    par = _map_range_par(index, r, which)
    if par is None:
        return False
    try:
        current = float(par.eval())
    except Exception:
        current = MAP_DEFAULT_MIN if which == 'min' else MAP_DEFAULT_MAX
    return set_map_dial_range_boundary(index, which, current + float(delta), r)


def adjust_map_dial_range_field(index, which, wheel, fine=False, r=None):
    if not wheel:
        return False
    step = _map_dial_range_step(index, fine=fine, r=r)
    return nudge_map_dial_range_field(index, which, step if wheel > 0 else -step, r)


def _map_dial_range_step(index, fine=False, r=None):
    lo, hi = _map_dial_range(index, r)
    span = max(0.0, hi - lo)
    if fine:
        if span <= 1.0:
            return 0.01
        if span <= 10.0:
            return 0.1
        return 1.0
    if span <= 1.0:
        return 0.1
    if span <= 10.0:
        return 1.0
    return max(1.0, span / 20.0)


def _normalize_map_bind_par(par, idx, r):
    if par is None or r is None:
        return
    try:
        if par.mode == ParMode.BIND:
            legacy = str(getattr(par, 'bindExpr', '') or '').strip()
            if legacy and legacy.lower() != 'none':
                try:
                    eval(legacy, {'op': op})
                    r.store(_map_outbound_store_key(idx), legacy)
                except Exception:
                    pass
            par.mode = ParMode.CONSTANT
            par.bindExpr = ''
    except Exception:
        pass


def _ensure_map_bind_par(page, r, idx):
    """Hidden bind reference par — outbound path stored in op storage, not BIND mode."""
    bname = _map_bind_par_name(idx)
    try:
        par = getattr(r.par, bname)
        if par.style == 'Str':
            old_expr = str(par.eval()).strip()
            try:
                par.destroy()
            except Exception:
                pass
            par = page.appendFloat(bname, label='Bind')
            par.default = 0.0
            par.val = 0.0
            par.min = 0.0
            par.max = 1.0
            par.normMin = 0.0
            par.normMax = 1.0
            if old_expr:
                r.store(_map_outbound_store_key(idx), old_expr)
        _normalize_map_bind_par(par, idx, r)
        return par
    except AttributeError:
        pass
    p = page.appendFloat(bname, label='Bind')
    p.default = 0.0
    p.val = 0.0
    p.min = 0.0
    p.max = 1.0
    p.normMin = 0.0
    p.normMax = 1.0
    p.clampMin = True
    p.clampMax = True
    try:
        p.readOnly = True
    except Exception:
        pass
    _normalize_map_bind_par(p, idx, r)
    return p


def _ensure_map_control_pars(r=None):
    if r is None:
        r = _root()
    if r is None:
        return False
    page = _map_control_page(r)
    for idx in range(1, MAP_DIAL_COUNT + 1):
        vname = _map_value_par_name(idx)
        try:
            par = getattr(r.par, vname)
            try:
                par.label = str(int(idx))
            except Exception:
                pass
        except AttributeError:
            p = page.appendFloat(vname, label=str(int(idx)))
            p.default = 0.0
            p.val = 0.0
            p.min = 0.0
            p.max = 1.0
            p.normMin = 0.0
            p.normMax = 1.0
            p.clampMin = True
            p.clampMax = True
        _ensure_map_range_par(page, r, idx, 'min', MAP_DEFAULT_MIN)
        _ensure_map_range_par(page, r, idx, 'max', MAP_DEFAULT_MAX)
        _ensure_map_output_par(page, r, idx)
        _ensure_map_bind_par(page, r, idx)
    return True


def _map_bind_expr(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return ''
    try:
        expr = str(r.fetch(_map_outbound_store_key(index), '') or '').strip()
        if expr:
            return expr
    except Exception:
        pass
    bind_par = _map_bind_par(index, r)
    if bind_par is None:
        return ''
    try:
        if bind_par.mode == ParMode.BIND:
            expr = str(getattr(bind_par, 'bindExpr', '') or '').strip()
            if expr and expr.lower() != 'none':
                _set_map_bind_outbound(index, expr, r)
                return expr
    except Exception:
        pass
    return ''


def _map_bind_target_resolves(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return False
    if _map_value_has_driver_bind(index, r):
        return True
    outbound = ''
    try:
        outbound = str(r.fetch(_map_outbound_store_key(index), '') or '').strip()
    except Exception:
        pass
    if not outbound:
        outbound = str(_map_bind_expr(index, r) or '').strip()
    if outbound and not _is_map_driver_expr(outbound):
        if outbound.startswith('par:') or outbound.startswith('param:'):
            try:
                return _resolve_cell_par_bind(outbound, r) is not None
            except Exception:
                return False
        try:
            eval(outbound, {'op': op})
            return True
        except Exception:
            return False
    target = _resolve_bind_target(index, r)
    if target is None:
        return False
    try:
        owner = getattr(target, 'owner', None)
        if owner is None:
            return False
        try:
            if hasattr(owner, 'valid') and not owner.valid:
                return False
        except Exception:
            pass
        return True
    except Exception:
        return False


def _prune_stale_map_dial_assignments(r=None):
    """Clear map dial labels/storage when the bound operator no longer exists."""
    if _MAP_SWITCH_GUARD:
        return False
    if r is None:
        r = _root()
    if r is None:
        return False
    ctx = _MAP_ACTIVE_CONTEXT
    stored = _stored_map_control_state(ctx) if ctx else {}
    changed = False
    for idx in range(1, MAP_DIAL_COUNT + 1):
        if _map_value_has_driver_bind(idx, r):
            continue
        st = stored.get(idx) or {}
        pending_expr = str(
            st.get('target_expr', '') or st.get('bind_expr', '') or ''
        ).strip()
        if pending_expr and not _is_map_driver_expr(pending_expr):
            continue
        expr = str(
            _map_snapshot_target_expr(idx, r) or _map_bind_expr(idx, r) or ''
        ).strip()
        if not expr or _is_map_driver_expr(expr):
            continue
        if _map_bind_target_resolves(idx, r):
            continue
        _clear_map_dial_assignment(idx, r)
        changed = True
    return changed


def _is_map_bind_active(index, r=None):
    if _map_value_has_driver_bind(index, r):
        return True
    expr = str(
        _map_snapshot_target_expr(index, r) or _map_bind_expr(index, r) or ''
    ).strip()
    if not expr:
        return False
    if _is_map_driver_expr(expr):
        return True
    return _map_bind_target_resolves(index, r)


def _map_bind_par(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return None
    try:
        return getattr(r.par, _map_bind_par_name(index))
    except AttributeError:
        return None


def _map_target_store_key(index):
    return 'map_dial_target_{}'.format(int(index))


def _map_outbound_store_key(index):
    return 'map_dial_outbound_{}'.format(int(index))


def _map_driver_store_key(index):
    return 'map_dial_driver_{}'.format(int(index))


def _clear_map_dial_live_storage(index, r=None):
    """Drop shared COMP op-storage keys for one dial (scope-neutral)."""
    if r is None:
        r = _root()
    if r is None:
        return
    for key in (
            _map_outbound_store_key(index),
            _map_target_store_key(index),
            _map_driver_store_key(index),
            _map_range_seed_key(index)):
        try:
            r.unstore(key)
        except Exception:
            pass


def _clear_all_map_dial_live_storage(r=None):
    for idx in range(1, MAP_DIAL_COUNT + 1):
        _clear_map_dial_live_storage(idx, r)


def _remember_map_bind_target(index, master_par, r=None):
    if r is None:
        r = _root()
    if r is None or master_par is None:
        return
    owner = getattr(master_par, 'owner', None)
    if owner is None:
        return
    expr = "op('{}').par.{}".format(
        owner.path.replace('\\', '/'), master_par.name)
    try:
        r.store(_map_target_store_key(index), expr)
    except Exception:
        pass


def _recalled_map_bind_target(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return None
    try:
        expr = str(r.fetch(_map_target_store_key(index), '') or '').strip()
    except Exception:
        expr = ''
    if expr:
        try:
            return eval(expr, {'op': op})
        except Exception:
            pass
    return _resolve_bound_par(index, r)


def _set_map_bind_outbound(index, outbound, r=None):
    if r is None:
        r = _root()
    if r is None:
        return False
    outbound = str(outbound or '').strip()
    if outbound and _is_map_driver_expr(outbound):
        outbound = ''
    store_key = _map_outbound_store_key(index)
    try:
        if outbound:
            r.store(store_key, outbound)
        else:
            r.unstore(store_key)
    except Exception:
        pass
    bind_par = _map_bind_par(index, r)
    if bind_par is not None:
        try:
            bind_par.mode = ParMode.CONSTANT
            bind_par.bindExpr = ''
        except Exception:
            pass
    return True


def _map_driver_expr(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return ''
    try:
        expr = str(r.fetch(_map_driver_store_key(index), '') or '').strip()
        if expr and _is_map_driver_expr(expr):
            return expr
    except Exception:
        pass
    return ''


def _set_map_driver_storage(index, driver_expr, r=None):
    if r is None:
        r = _root()
    if r is None:
        return False
    driver_expr = str(driver_expr or '').strip()
    store_key = _map_driver_store_key(index)
    try:
        if driver_expr and _is_map_driver_expr(driver_expr):
            r.store(store_key, driver_expr)
        else:
            r.unstore(store_key)
    except Exception:
        pass
    return True


def _map_value_driver_expr(index, r=None):
    """Pulse (etc.) expression bound inbound on Map*value."""
    stored = _map_driver_expr(index, r)
    if stored:
        return stored
    value_par = _map_value_par(index, r)
    if value_par is None:
        return ''
    try:
        if value_par.mode == ParMode.BIND:
            expr = str(getattr(value_par, 'bindExpr', '') or '').strip()
            if expr and _is_map_driver_expr(expr):
                return expr
            master = getattr(value_par, 'bindMaster', None)
            if master is not None and _is_map_driver_par(master):
                return _absolute_bind_expr(master)
    except Exception:
        pass
    return ''


def _map_value_has_driver_bind(index, r=None):
    return bool(_map_value_driver_expr(index, r))


def _ensure_map_value_driver_bind(index, driver_expr, r=None):
    """Wire Map*value to follow a pulse driver (inbound bind)."""
    if r is None:
        r = _root()
    if r is None:
        return False
    driver_expr = str(driver_expr or '').strip()
    if not driver_expr or not _is_map_driver_expr(driver_expr):
        return False
    _ensure_map_control_pars(r)
    value_par = _map_value_par(index, r)
    if value_par is None:
        return False
    wrong_target = _recalled_map_bind_target(index, r)
    if wrong_target is not None and _is_map_driver_par(wrong_target):
        try:
            if _target_bound_to_map_dial(index, wrong_target, r):
                wrong_target.mode = ParMode.CONSTANT
                wrong_target.bindExpr = ''
        except Exception:
            pass
    try:
        if (
            value_par.mode == ParMode.BIND
            and str(getattr(value_par, 'bindExpr', '') or '').strip() == driver_expr
        ):
            _set_map_driver_storage(index, driver_expr, r)
            return True
        value_par.mode = ParMode.BIND
        value_par.bindExpr = _sanitize_bind_expr(driver_expr)
    except Exception:
        return False
    _set_map_driver_storage(index, driver_expr, r)
    return True


def _clear_map_value_driver_bind(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return False
    _set_map_driver_storage(index, '', r)
    value_par = _map_value_par(index, r)
    if value_par is None:
        return True
    try:
        if value_par.mode != ParMode.BIND:
            return True
        expr = str(getattr(value_par, 'bindExpr', '') or '').strip()
        master = getattr(value_par, 'bindMaster', None)
        if _is_map_driver_expr(expr) or _is_map_driver_par(master):
            value_par.mode = ParMode.CONSTANT
            value_par.bindExpr = ''
    except Exception:
        pass
    return True


def map_dial_parexec_should_skip(index):
    """Skip parexec save/paint feedback while MIDI or mouse drag is driving Map*value."""
    idx = int(index)
    return idx in _MAP_DIAL_MIDI_WRITE or idx in _MAP_DIAL_DRAG_ACTIVE


def sync_map_value_driver_from_par(index, r=None):
    """Persist Map*value inbound pulse binds into the scoped dial bank."""
    if _MAP_SWITCH_GUARD:
        return False
    if map_dial_parexec_should_skip(index):
        return False
    if r is None:
        r = _root()
    if r is None:
        return False
    driver = _map_value_driver_expr(index, r)
    if driver:
        _set_map_driver_storage(index, driver, r)
    else:
        try:
            r.unstore(_map_driver_store_key(index))
        except Exception:
            pass
    _save_active_map_control_state(r)
    return bool(driver)


def _resolve_cell_par_bind(expr, r=None):
    """Resolve par:L3_col1:Size style references to a live parameter."""
    if r is None:
        r = _root()
    if r is None:
        return None
    spec = _parse_midi_param_target(expr)
    if not spec or spec.get('kind') != 'cell':
        return None
    layer = spec.get('layer')
    col = spec.get('col')
    if layer is None:
        try:
            layer = int(float(r.par.Selectedlayer.eval()))
        except Exception:
            return None
    if col is None:
        try:
            col = int(float(r.par.Selectedcol.eval()))
        except Exception:
            return None
    target = _cell_param_target(layer, col)
    return _find_par_on_op(target, spec.get('par'))


def _absolute_bind_expr(master_par):
    """Absolute op('path').par.Name bind, null-safe when the master OP is briefly missing."""
    owner = getattr(master_par, 'owner', None)
    if owner is None:
        return ''
    path = owner.path.replace('\\', '/')
    name = master_par.name
    return _null_safe_bind_expr(path, name)


def _null_safe_bind_expr(op_path, par_name):
    """BindExpr that won't throw AttributeError if the master OP is missing."""
    path = str(op_path or '').replace('\\', '/').strip()
    name = str(par_name or '').strip()
    if not path or not name:
        return ''
    path = path.replace("'", "\\'")
    # me.curPar = this follower parameter (TD) — holds last value while master is gone.
    return (
        "op('{path}').par.{name} if op('{path}') is not None else me.curPar"
    ).format(path=path, name=name)


def _sanitize_bind_expr(expr):
    """Rewrite bare op('…').par.Name binds so missing OPs don't error Settings."""
    import re
    text = str(expr or '').strip()
    if not text:
        return text
    if ' if op(' in text or 'me.curPar' in text:
        return text
    m = re.match(
        r"^op\('([^']+)'\)\.par\.([A-Za-z_][A-Za-z0-9_]*)$",
        text,
    )
    if not m:
        return text
    return _null_safe_bind_expr(m.group(1), m.group(2))


def heal_unsafe_parameter_binds(r=None):
    """Rewrite bare op().par binds under slots (and map dials) to null-safe form."""
    if r is None:
        r = _root()
    if r is None:
        return 0
    fixed = 0

    def _heal_par(par):
        nonlocal fixed
        if par is None:
            return
        try:
            if par.mode != ParMode.BIND:
                return
            raw = str(getattr(par, 'bindExpr', '') or '').strip()
            safe = _sanitize_bind_expr(raw)
            if safe and safe != raw:
                par.bindExpr = safe
                fixed += 1
        except Exception:
            pass

    slots = r.op('slots')
    if slots is not None:
        for layer_comp in list(slots.children):
            if not getattr(layer_comp, 'isCOMP', False):
                continue
            for slot in list(layer_comp.children):
                if not getattr(slot, 'isCOMP', False):
                    continue
                for name in ('tox', 'video'):
                    node = slot.op(name)
                    if node is None:
                        continue
                    try:
                        for par in node.customPars:
                            _heal_par(par)
                    except Exception:
                        pass
                    try:
                        for child in node.children:
                            if not getattr(child, 'isCOMP', False):
                                continue
                            for par in getattr(child, 'customPars', []):
                                _heal_par(par)
                    except Exception:
                        pass
    try:
        _ensure_map_control_pars(r)
        for idx in range(1, MAP_DIAL_COUNT + 1):
            _heal_par(_map_value_par(idx, r))
            _heal_par(_map_bind_par(idx, r))
    except Exception:
        pass
    return fixed


def _resolve_bind_target(index, r=None):
    """Resolve the effect parameter bound to Map*out (not pulse drivers)."""
    if r is None:
        r = _root()
    if r is None:
        return None
    bind_par = _map_bind_par(index, r)
    if bind_par is not None:
        try:
            if bind_par.mode == ParMode.BIND:
                master = getattr(bind_par, 'bindMaster', None)
                if master is not None and not _is_map_driver_par(master):
                    return master
        except Exception:
            pass
    try:
        target_expr = str(r.fetch(_map_target_store_key(index), '') or '').strip()
    except Exception:
        target_expr = ''
    if target_expr and not _is_map_driver_expr(target_expr):
        if target_expr.startswith('par:') or target_expr.startswith('param:'):
            resolved = _resolve_cell_par_bind(target_expr, r)
            if resolved is not None and not _is_map_driver_par(resolved):
                return resolved
        try:
            resolved = r.evalExpression(target_expr)
            if resolved is not None and not _is_map_driver_par(resolved):
                return resolved
        except Exception:
            pass
        try:
            resolved = eval(target_expr, {'op': op})
            if resolved is not None and not _is_map_driver_par(resolved):
                return resolved
        except Exception:
            pass
    expr = _map_bind_expr(index, r)
    if not expr or _is_map_driver_expr(expr):
        return None
    if expr.startswith('par:') or expr.startswith('param:'):
        resolved = _resolve_cell_par_bind(expr, r)
        if resolved is not None and not _is_map_driver_par(resolved):
            return resolved
        return None
    try:
        resolved = r.evalExpression(expr)
        if resolved is not None and not _is_map_driver_par(resolved):
            return resolved
    except Exception:
        pass
    try:
        resolved = eval(expr, {'op': op})
        if resolved is not None and not _is_map_driver_par(resolved):
            return resolved
    except Exception:
        pass
    return None


def _resolve_bound_par(index, r=None):
    return _resolve_bind_target(index, r)


def _map_value_par(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return None
    try:
        return getattr(r.par, _map_value_par_name(index))
    except AttributeError:
        return None


def _par_bind_expression(par):
    if par is None:
        return ''
    try:
        if par.mode == ParMode.BIND:
            expr = str(getattr(par, 'bindExpr', '') or '').strip()
            if expr:
                return expr
    except Exception:
        pass
    try:
        master = getattr(par, 'bindMaster', None)
        if master is not None:
            owner = getattr(master, 'owner', None)
            if owner is not None:
                return "op('{}').par.{}".format(
                    owner.path.replace('\\', '/'), master.name)
    except Exception:
        pass
    return ''


def _map_dial_bind_expression(index, r=None):
    expr = _map_bind_expr(index, r)
    if expr:
        return expr
    return _par_bind_expression(_map_value_par(index, r))


def _bind_label_lines(display):
    return [ln.strip() for ln in str(display or '').split('\n') if str(ln).strip()]


def _fit_bind_label_font_size(display, dial_w=None):
    """Shrink font when a line cannot fit the dial cell width."""
    dial_w = max(24, int(dial_w or 54))
    lines = _bind_label_lines(display)
    if not lines:
        return MAP_DIAL_BIND_LABEL_FONT
    max_chars = max(len(ln) for ln in lines)
    font = MAP_DIAL_BIND_LABEL_FONT
    min_font = max(6, int(round(MAP_DIAL_BIND_LABEL_FONT * 0.65)))
    usable = max(14, dial_w - 4)
    while font > min_font:
        if max_chars * font * MAP_DIAL_BIND_LABEL_GLYPH_SCALE <= usable:
            break
        font -= 1
    return font


def _map_bind_label_texture_width(display, dial_w=None, font=None):
    """Render label text into a wide enough texture; container topfill scales it down."""
    dial_w = max(24, int(dial_w or 54))
    font = MAP_DIAL_BIND_LABEL_FONT if font is None else int(font)
    lines = _bind_label_lines(display)
    if not lines:
        return dial_w
    max_chars = max(len(ln) for ln in lines)
    needed = int(max_chars * float(font) * MAP_DIAL_BIND_LABEL_GLYPH_SCALE)
    needed += MAP_DIAL_BIND_LABEL_TEX_PAD
    return max(dial_w, needed)


def _bind_label_chars_per_line(dial_w=None, line=1):
    w = max(24, int(dial_w or 54))
    scale = (
        MAP_DIAL_BIND_LABEL_LINE1_WIDTH_SCALE
        if int(line) <= 1 else MAP_DIAL_BIND_LABEL_LINE2_WIDTH_SCALE)
    return max(4, int(w / max(4.0, MAP_DIAL_BIND_LABEL_FONT * scale)))


def _bind_label_line_char_limit(dial_w, line_index):
    if int(line_index) <= 0:
        return _bind_label_chars_per_line(dial_w, line=1)
    return _bind_label_chars_per_line(dial_w, line=2)


def _split_camel_case_token(token):
    if not token:
        return []
    parts = []
    start = 0
    n = len(token)
    for i in range(1, n):
        prev, cur = token[i - 1], token[i]
        if prev.islower() and cur.isupper():
            parts.append(token[start:i])
            start = i
        elif prev.isupper() and cur.isupper() and i + 1 < n and token[i + 1].islower():
            parts.append(token[start:i])
            start = i
    parts.append(token[start:])
    return [p for p in parts if p]


def _bind_label_words(text):
    """Split a parameter label into display words (spaces, underscores, camelCase)."""
    text = str(text or '').strip()
    if not text:
        return []
    words = []
    for chunk in text.replace('_', ' ').split():
        parts = _split_camel_case_token(chunk)
        words.extend(parts if len(parts) > 1 else [chunk])
    return words


def _wrap_bind_label_display(text, dial_w=None, max_lines=None):
    """One word per line; never break inside a word."""
    text = str(text or '').strip()
    if not text:
        return ''
    if max_lines is None:
        max_lines = MAP_DIAL_BIND_LABEL_LINES
    per_line1 = _bind_label_chars_per_line(dial_w, line=1)
    per_line2 = _bind_label_chars_per_line(dial_w, line=2)

    if '\n' in text:
        lines = [ln.strip() for ln in text.split('\n') if ln.strip()][:max_lines]
        return '\n'.join(
            _fit_bind_label_display(ln, _bind_label_line_char_limit(dial_w, i))
            for i, ln in enumerate(lines))

    words = _bind_label_words(text)
    if not words:
        return ''
    if len(words) == 1:
        return _fit_bind_label_display(words[0], max(per_line1, per_line2))
    if max_lines <= 1:
        return _fit_bind_label_display(words[0], per_line1)

    if len(words) > max_lines:
        head = words[:max_lines - 1]
        tail = ' '.join(words[max_lines - 1:])
        words = head + [tail]

    lines = []
    for i, word in enumerate(words):
        limit = _bind_label_line_char_limit(dial_w, i)
        lines.append(_fit_bind_label_display(word, limit))
    return '\n'.join(lines)


def _fit_bind_label_display(text, max_chars):
    """Truncate long parameter labels at the end (left-aligned row)."""
    text = str(text or '').strip()
    if not text:
        return ''
    if len(text) <= max_chars:
        return text
    return text[: max(1, max_chars - 3)] + '...'


def _fit_bind_display(text, max_chars):
    text = str(text or '').strip()
    if not text:
        return ''
    if len(text) <= max_chars:
        return text
    if '.par.' in text:
        head, tail = text.rsplit('.par.', 1)
        if len(tail) + 6 < max_chars:
            keep = max(4, max_chars - len(tail) - 6)
            return head[:keep] + "').par." + tail
    return text[: max(0, max_chars - 3)] + '...'


def _map_bind_param_display(par):
    if par is None:
        return ''
    try:
        label = str(getattr(par, 'label', '') or '').strip()
        if label:
            return label
    except Exception:
        pass
    try:
        return str(getattr(par, 'name', '') or '').strip()
    except Exception:
        return ''


def _map_dial_link_label_text(index, dial_w=None, r=None):
    if not _is_map_bind_active(index, r):
        return MAP_DIAL_BIND_EMPTY_LABEL
    target = _resolve_bind_target(index, r)
    if target is not None:
        text = _map_bind_param_display(target)
        if text:
            return text
    return _bind_label(_map_bind_expr(index, r))


def _map_dial_value_text(value):
    return _format_map_number(value)


def _map_dial_readout(index, value, dial_w=None, r=None):
    expr = _map_dial_bind_expression(index, r)
    if expr:
        max_chars = max(10, int((dial_w or 54) // 3))
        return _fit_bind_display(expr, max_chars), True
    return _map_dial_value_text(value), False


def _map_expr_for_value_par(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return ''
    return "op('{}').par.{}".format(
        r.path.replace('\\', '/'), _map_value_par_name(index))


def _native_bind_label(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return ''
    try:
        par = getattr(r.par, _map_value_par_name(index))
        master = getattr(par, 'bindMaster', None)
        if master is not None:
            return _map_bind_param_display(master)
    except Exception:
        pass
    return ''


def _bind_label(expr, r=None):
    expr = str(expr or '').strip()
    if not expr:
        return MAP_DIAL_BIND_EMPTY_LABEL
    if expr.startswith('par:') or expr.startswith('param:'):
        if r is None:
            r = _root()
        if r is not None:
            try:
                par = _resolve_cell_par_bind(expr, r)
                text = _map_bind_param_display(par)
                if text:
                    return text
            except Exception:
                pass
    if '.par.' in expr:
        try:
            if r is None:
                r = _root()
            if r is not None:
                par = r.evalExpression(expr)
                text = _map_bind_param_display(par)
                if text:
                    return text
        except Exception:
            pass
        try:
            _, tail = expr.rsplit('.par.', 1)
            return tail
        except Exception:
            pass
    if len(expr) > 28:
        return expr[:25] + '...'
    return expr


def _map_context_for_scope(scope, r=None):
    """Resolve cell/global map bank for scoped MIDI (None = active tab)."""
    scope = str(scope or '').strip().lower()
    if scope in ('', 'active', 'current'):
        return _current_map_context(r)
    scene = int(_active_scene())
    if scope == 'global':
        return ('global', scene)
    if scope in ('cell', 'layer'):
        layer = col = 1
        if r is None:
            r = _root()
        if r is not None:
            try:
                layer = int(float(r.par.Selectedlayer.eval()))
                col = int(float(r.par.Selectedcol.eval()))
            except Exception:
                pass
        return ('cell', scene, layer, col)
    return _current_map_context(r)


def _persist_stored_map_dial_state(ctx, stored):
    if not ctx:
        return
    stored = _normalize_map_dial_store(stored)
    if ctx[0] == 'global':
        _GLOBAL_MAP_BY_SCENE[int(ctx[1])] = stored
    else:
        _CELL_MAP_BY_KEY[(int(ctx[1]), int(ctx[2]), int(ctx[3]))] = stored


def _push_stored_map_dial_output(index, state, r=None):
    """Drive a stored bind target without switching the live map bank."""
    state = dict(state or {})
    target_expr = str(state.get('target_expr', '') or '').strip()
    outbound = str(state.get('bind_expr', '') or '').strip()
    if outbound and _is_map_driver_expr(outbound):
        outbound = target_expr
    if not outbound or _is_map_driver_expr(outbound):
        outbound = target_expr
    if not outbound or _is_map_driver_expr(outbound):
        return False
    try:
        target = eval(outbound, {'op': op})
    except Exception:
        return False
    if target is None or _is_map_driver_par(target):
        return False
    norm = max(0.0, min(1.0, float(state.get('value', 0.0))))
    lo = _clamp_map_range_value(state.get('min', MAP_DEFAULT_MIN))
    hi = _clamp_map_range_value(state.get('max', MAP_DEFAULT_MAX))
    span = hi - lo if hi > lo else 1.0
    scaled = lo + norm * span
    try:
        target.val = _absolute_to_par_val(target, scaled)
        return True
    except Exception:
        return False


def map_dial_norm_scoped(index, scope=None, r=None):
    """Normalized dial position for active or stored cell/global bank."""
    ctx = _map_context_for_scope(scope, r)
    live = _MAP_ACTIVE_CONTEXT or _current_map_context(r)
    if scope in (None, '', 'active', 'current') or ctx == live:
        return map_dial_norm(index, r)
    stored = _stored_map_control_state(ctx)
    st = stored.get(int(index)) or _default_map_dial_state()
    return max(0.0, min(1.0, float(st.get('value', 0.0))))


def map_dial_norm(index, r=None):
    """Normalized dial position (0–1)."""
    if r is None:
        r = _root()
    if r is None:
        return 0.0
    try:
        par = getattr(r.par, _map_value_par_name(index))
        try:
            return max(0.0, min(1.0, float(par.val)))
        except Exception:
            return max(0.0, min(1.0, float(par.eval())))
    except Exception:
        pass
    bound = _resolve_bound_par(index, r)
    if bound is not None:
        try:
            return _map_dial_norm_from_scaled(float(bound.eval()), index, r)
        except Exception:
            pass
    return 0.0


def map_dial_value(index, r=None):
    """Scaled dial output between Map*min and Map*max."""
    return _map_dial_scaled_from_norm(map_dial_norm(index, r), index, r)


def block_map_dial_midi(index):
    _MAP_DIAL_MIDI_BLOCK.add(int(index))


def unblock_map_dial_midi(index):
    _MAP_DIAL_MIDI_BLOCK.discard(int(index))
    clear_map_dial_midi_sync(index)


def clear_map_dial_midi_blocks():
    _MAP_DIAL_MIDI_BLOCK.clear()


def clear_map_dial_midi_sync(index=None):
    """Reset relative MIDI tracking so knobs pick up without jumping."""
    if index is None:
        _MAP_DIAL_MIDI_SYNCED.clear()
        _MAP_DIAL_MIDI_LAST.clear()
        _MAP_DIAL_MIDI_PAINT_PENDING.clear()
    else:
        idx = int(index)
        _MAP_DIAL_MIDI_SYNCED.discard(idx)
        _MAP_DIAL_MIDI_LAST.pop(idx, None)
        _MAP_DIAL_MIDI_PAINT_PENDING.discard(idx)


def map_dial_midi_blocked(index):
    return int(index) in _MAP_DIAL_MIDI_BLOCK


def _map_dial_target_follows_map_out(index, r=None):
    """True when the bind target listens to Map*out (expression + BIND chain)."""
    if r is None:
        r = _root()
    if r is None or not _is_map_bind_active(index, r):
        return False
    target = _resolve_bind_target(index, r)
    if target is None or _is_map_driver_par(target):
        return False
    return _target_bound_to_map_dial(index, target, r)


def _schedule_map_dial_midi_paint(index, r=None):
    """Coalesce map dial repaints to one per frame during MIDI streams."""
    idx = int(index)
    if idx in _MAP_DIAL_MIDI_PAINT_PENDING:
        return
    if r is None:
        r = _root()
    if r is None:
        return
    _MAP_DIAL_MIDI_PAINT_PENDING.add(idx)

    def _paint():
        _MAP_DIAL_MIDI_PAINT_PENDING.discard(idx)
        try:
            _paint_map_dial(idx, r=r, light=True)
        except Exception:
            pass

    if not _defer_run(_paint, delayFrames=0, fromOP=r):
        _MAP_DIAL_MIDI_PAINT_PENDING.discard(idx)
        _paint()


def apply_map_dial_midi(index, midi_cc, r=None, light=True, out_min=0.0, out_max=1.0):
    """Drive a map dial from MIDI (absolute CC position, like layer opacity)."""
    if map_dial_midi_blocked(index):
        return True
    try:
        cc = max(0.0, min(127.0, float(midi_cc)))
    except Exception:
        cc = 0.0
    lo = float(out_min)
    hi = float(out_max)
    span = hi - lo
    if span <= 0.0:
        span = 1.0
        lo = 0.0
    norm = max(0.0, min(1.0, lo + (cc / 127.0) * span))
    return set_map_dial_value(index, norm, r=r, light=light, paint=False, from_midi=True)


def set_map_dial_value_scoped(
    index, value, scope=None, r=None, light=False, paint=True, from_midi=False,
):
    """Set a map dial in the active, cell, or global bank."""
    if r is None:
        r = _root()
    if r is None:
        return False
    scope_key = str(scope or '').strip().lower()
    if from_midi and scope_key != 'global':
        _ensure_map_live_context_for_midi(r, scope=scope_key)
    ctx = _map_context_for_scope(scope, r)
    live = _MAP_ACTIVE_CONTEXT or _current_map_context(r)
    norm = max(0.0, min(1.0, float(value)))
    if scope_key in ('', 'active', 'current') or ctx == live:
        return set_map_dial_value(
            index, norm, r=r, light=light, paint=paint, from_midi=from_midi,
        )
    stored = dict(_stored_map_control_state(ctx))
    st = dict(stored.get(int(index)) or _default_map_dial_state())
    endpoint = norm <= 0.0 or norm >= 1.0
    try:
        if not endpoint and abs(float(st.get('value', 0.0)) - norm) < (1.0 / 127.0):
            return True
    except Exception:
        pass
    st['value'] = norm
    stored[int(index)] = st
    _persist_stored_map_dial_state(ctx, stored)
    if not from_midi:
        _push_stored_map_dial_output(index, st, r)
    else:
        lo = _clamp_map_range_value(st.get('min', MAP_DEFAULT_MIN))
        hi = _clamp_map_range_value(st.get('max', MAP_DEFAULT_MAX))
        span = hi - lo if hi > lo else 1.0
        scaled = lo + norm * span
        try:
            target = eval(str(st.get('bind_expr', '') or '').strip(), {'op': op})
            if target is not None:
                target.val = _absolute_to_par_val(target, scaled)
        except Exception:
            pass
    return True


def set_map_dial_value(index, value, r=None, light=False, paint=True, from_midi=False):
    if from_midi and map_dial_midi_blocked(index):
        return True
    if r is None:
        r = _root()
    if r is None:
        return False
    if from_midi:
        _ensure_map_live_context_for_midi(r)
    try:
        getattr(r.par, _map_value_par_name(1))
    except AttributeError:
        _ensure_map_control_pars(r)
    if not from_midi and _map_value_has_driver_bind(index, r):
        _clear_map_value_driver_bind(index, r)
    idx = int(index)
    norm = max(0.0, min(1.0, float(value)))
    endpoint = norm <= 0.0 or norm >= 1.0
    bind_active = _is_map_bind_active(idx, r)

    if from_midi:
        _MAP_DIAL_MIDI_WRITE.add(idx)
        try:
            try:
                current = float(getattr(r.par, _map_value_par_name(idx)).eval())
                if not endpoint and abs(current - norm) < (1.0 / 127.0):
                    if paint:
                        _schedule_map_dial_midi_paint(idx, r)
                    return True
            except Exception:
                pass
            if not _map_output_is_live(idx, r):
                _heal_map_output_par(idx, r)
            if not _set_map_dial_norm(idx, norm, r, from_midi=True, force=True):
                return False
            _prime_map_dial_midi_chain(idx, norm, r)
            if paint:
                _schedule_map_dial_midi_paint(idx, r)
            return True
        finally:
            _MAP_DIAL_MIDI_WRITE.discard(idx)

    if not from_midi:
        try:
            current = float(getattr(r.par, _map_value_par_name(idx)).eval())
            if not endpoint and abs(current - norm) < (1.0 / 127.0):
                if paint:
                    _paint_map_dial(idx, r=r, light=light)
                return True
        except Exception:
            pass
    if bind_active:
        _heal_map_dial_output_chain(idx, r)
    if not _set_map_dial_norm(idx, norm, r, from_midi=from_midi, force=from_midi):
        return False
    if bind_active:
        target = _resolve_bind_target(idx, r)
        if target is not None and not _is_map_driver_par(target):
            if not _target_bound_to_map_dial(idx, target, r):
                _ensure_target_map_bind(idx, target, r, force=True)
        _sync_map_dial_bound_target(idx, norm, r)
    if not from_midi:
        _save_active_map_control_state(r)
    if paint:
        if from_midi:
            _schedule_map_dial_midi_paint(idx, r)
        else:
            _paint_map_dial(idx, r=r, light=light)
    return True


def set_map_dial_value_interactive(index, value, r=None, light=True):
    """Fast mouse-drag path for Map Controller dials.

    Dragging should feel like MIDI: update the bound output immediately, coalesce
    UI painting, and defer the saved scoped-state snapshot until mouse-up.
    """
    if r is None:
        r = _root()
    if r is None:
        return False
    idx = int(index)
    _MAP_DIAL_DRAG_ACTIVE.add(idx)
    try:
        getattr(r.par, _map_value_par_name(1))
    except AttributeError:
        _ensure_map_control_pars(r)
    if _map_value_has_driver_bind(index, r):
        _clear_map_value_driver_bind(index, r)
    norm = max(0.0, min(1.0, float(value)))
    endpoint = norm <= 0.0 or norm >= 1.0
    try:
        current = float(getattr(r.par, _map_value_par_name(index)).eval())
        if not endpoint and abs(current - norm) < MAP_DIAL_INTERACTIVE_EPS:
            return True
    except Exception:
        pass

    bind_active = _is_map_bind_active(index, r)
    if bind_active:
        _heal_map_dial_output_chain(index, r)
    if not _set_map_dial_norm(index, norm, r, from_midi=True, force=True):
        return False
    if bind_active:
        target = _resolve_bind_target(index, r)
        if target is not None and not _is_map_driver_par(target):
            if not _target_bound_to_map_dial(index, target, r):
                _ensure_target_map_bind(index, target, r, force=True)
        _sync_map_dial_bound_target(index, norm, r)
    if light:
        _schedule_map_dial_midi_paint(index, r)
    return True


def commit_map_dial_drag(index, r=None):
    """Persist a Map Controller dial after an interactive mouse drag."""
    idx = int(index)
    _MAP_DIAL_DRAG_ACTIVE.discard(idx)
    if r is None:
        r = _root()
    if r is None:
        return False
    try:
        norm = float(getattr(r.par, _map_value_par_name(index)).eval())
        if _is_map_bind_active(index, r) and not _map_bind_chain_is_live(index, r, norm=norm):
            _sync_map_dial_bound_target(index, norm, r)
    except Exception:
        pass
    _save_active_map_control_state(r)
    clear_map_dial_midi_sync(index)
    _paint_map_dial(index, r=r)
    return True


def bind_map_dial(index, master_par, r=None):
    if r is None:
        r = _root()
    if r is None or master_par is None:
        return False
    try:
        if _MAP_ACTIVE_CONTEXT != _current_map_context(r):
            sync_map_control_context(r)
    except Exception:
        pass
    live_par = _resolve_map_bind_target_par(master_par)
    if live_par is None:
        return False
    abs_expr = _absolute_bind_expr(live_par)
    if not abs_expr:
        return False
    _ensure_map_control_pars(r)
    _clear_duplicate_map_out_binds(index, keep_target=live_par, r=r)
    existing_driver = _map_value_driver_expr(index, r)
    existing_target_expr = _map_snapshot_target_expr(index, r)
    scaled_seed = _read_target_par_value(live_par)
    _detach_map_dial(index, r)
    _set_map_bind_outbound(index, '', r)
    _map_bind_lock_begin(r)
    global _MAP_SWITCH_GUARD
    _MAP_SWITCH_GUARD = True
    try:
        if _is_map_driver_par(live_par):
            slot = _pulse_slot_from_par_name(live_par.name)
            if slot is not None:
                lo, hi = _pulse_slot_min_max(slot)
            else:
                lo, hi = MAP_DEFAULT_MIN, MAP_DEFAULT_MAX
            try:
                norm = max(0.0, min(1.0, float(live_par.eval())))
            except Exception:
                norm = _map_dial_norm_from_scaled(scaled_seed, index, r)
            state = {
                'value': norm,
                'min': lo,
                'max': hi,
                'bind_expr': existing_target_expr or abs_expr,
                'target_expr': existing_target_expr,
                'driver_expr': abs_expr,
            }
            _apply_map_dial_state(index, state, r, rebind=True)
        else:
            _apply_map_range_from_target(index, live_par, r, force=True)
            lo, hi = _map_dial_range(index, r)
            norm = _map_dial_norm_from_scaled(scaled_seed, index, r)
            state = {
                'value': norm,
                'min': lo,
                'max': hi,
                'bind_expr': abs_expr,
                'target_expr': abs_expr,
                'driver_expr': existing_driver,
            }
            _apply_map_dial_state(index, state, r, rebind=True)
    finally:
        _MAP_SWITCH_GUARD = False
        _map_bind_lock_end(r)
    clear_map_dial_midi_sync(index)
    _save_active_map_control_state(r)
    _paint_map_dial(index, r=r)
    try:
        owner = getattr(live_par, 'owner', None)
        bind_layer, bind_col = _slot_layer_col_from_path(
            getattr(owner, 'path', '') if owner is not None else '')
        if bind_layer is not None:
            _heal_column_video_after_fx_map_bind(bind_layer, bind_col, r)
    except Exception:
        pass
    return True


def clear_map_dial_bind(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return False
    bound = _recalled_map_bind_target(index, r)
    _set_map_bind_outbound(index, '', r)
    _clear_map_value_driver_bind(index, r)
    if bound is not None:
        try:
            if _target_bound_to_map_dial(index, bound, r):
                bound.mode = ParMode.CONSTANT
                bound.bindExpr = ''
                bound.val = float(map_dial_value(index, r))
        except Exception:
            pass
    try:
        r.unstore(_map_target_store_key(index))
        r.unstore(_map_range_seed_key(index))
    except Exception:
        pass
    _save_active_map_control_state(r)
    _paint_map_dial(index, r=r)
    return True


def sync_map_dial_bind_from_par(index, r=None):
    """Keep outbound target bind in sync after native TD bind UI edits."""
    if _MAP_SWITCH_GUARD:
        return False
    if r is None:
        r = _root()
    if r is None:
        return False
    if _map_bind_lock_active(r):
        return False
    guard_key = 'map_sync_guard_{}'.format(int(index))
    try:
        if int(r.fetch(guard_key, 0)):
            return False
        r.store(guard_key, 1)
    except Exception:
        pass
    try:
        return _sync_map_dial_bind_from_par_impl(index, r)
    finally:
        try:
            r.unstore(guard_key)
        except Exception:
            pass


def _sync_map_dial_bind_from_par_impl(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return False
    if _map_bind_lock_active(r):
        return False
    if not _is_map_bind_active(index, r):
        return False
    outbound = _map_bind_expr(index, r)
    target = _resolve_bind_target(index, r)
    if target is None:
        _paint_map_dial(index, r=r)
        return False
    _remember_map_bind_target(index, target, r)
    abs_expr = _absolute_bind_expr(target)
    if abs_expr and abs_expr != outbound and not _is_map_driver_expr(abs_expr):
        _set_map_bind_outbound(index, abs_expr, r)
    _apply_map_range_from_target(index, target, r)
    if not _target_bound_to_map_dial(index, target, r):
        if not _map_value_has_driver_bind(index, r):
            seed_val = _read_target_par_value(target)
            _set_map_dial_norm(
                index, _map_dial_norm_from_scaled(seed_val, index, r), r)
    if _is_map_driver_par(target):
        _paint_map_dial(index, r=r)
        _save_active_map_control_state(r)
        return True
    _ensure_target_map_bind(index, target, r, force=True)
    _paint_map_dial(index, r=r)
    _save_active_map_control_state(r)
    return True


def _map_dial_index_from_output_bind_expr(bind_expr):
    expr = str(bind_expr or '')
    for idx in range(MAP_DIAL_COUNT, 0, -1):
        token = 'Map{}out'.format(idx)
        if token in expr:
            return idx
    return None


def is_map_out_bind_expr(expr):
    """True when a bind expression targets a Map Controller dial output par."""
    return _map_dial_index_from_output_bind_expr(expr) is not None


def _clear_map_out_binds_on_target(target, clip_type=None):
    """Drop Map*out binds on a clip parameter owner (video / tox COMP)."""
    if target is None:
        return 0
    cleared = 0
    for par in _copyable_cell_params(target, clip_type):
        try:
            if par.mode != ParMode.BIND:
                continue
        except Exception:
            continue
        if not is_map_out_bind_expr(_par_bind_expression(par)):
            continue
        try:
            par.mode = ParMode.CONSTANT
            par.bindExpr = ''
            cleared += 1
        except Exception:
            pass
    return cleared


def _par_bound_to_map_dial_index(par, r=None):
    """Return 1…8 when par is bound to Map*Nout, else None."""
    return _map_dial_index_from_output_bind_expr(_par_bind_expression(par))


def _slot_layer_col_from_path(path):
    path = str(path or '').replace('\\', '/')
    if '/slots/layer_' not in path:
        return None, None
    try:
        chunk = path.split('/slots/layer_', 1)[1]
        layer_s, rest = chunk.split('/', 1)
        layer = int(layer_s)
        col = int(rest.split('/', 1)[0].replace('col_', ''))
        return layer, col
    except Exception:
        return None, None


def _clear_duplicate_map_out_binds(index, keep_target=None, r=None):
    """One map dial may only drive one parameter — drop stale binds on other cells."""
    index = int(index)
    cleared = 0
    for layer in range(1, _num_layers() + 1):
        for col in range(1, _num_cols() + 1):
            ctype, path = _get(layer, col)
            if not path or not _valid_clip_type(ctype):
                continue
            owners = []
            target = _cell_param_target(layer, col, ctype)
            if target is not None:
                owners.append((ctype, target))
            slot = _slot(layer, col)
            if slot is not None:
                try:
                    for entry in _cell_fx_list(layer, col):
                        fx_slot = _cell_fx_slot_comp(slot, entry.get('id'))
                        if fx_slot is not None:
                            tox = fx_slot.op('tox')
                            if tox is not None:
                                owners.append(('tox', tox))
                except Exception:
                    pass
            for owner_ctype, owner in owners:
                for par in _copyable_cell_params(owner, owner_ctype):
                    if keep_target is not None and par is keep_target:
                        continue
                    try:
                        if par.mode != ParMode.BIND:
                            continue
                    except Exception:
                        continue
                    if _par_bound_to_map_dial_index(par, r) != index:
                        continue
                    try:
                        current = float(par.eval())
                        par.mode = ParMode.CONSTANT
                        par.bindExpr = ''
                        par.val = current
                        cleared += 1
                    except Exception:
                        pass
    return cleared


def _heal_column_video_after_fx_map_bind(bind_layer, bind_col, r=None):
    """Rewire the base-row video when an FX map bind left Movie File In stuck."""
    try:
        bind_layer = int(bind_layer)
        bind_col = int(bind_col)
        if bind_layer >= int(_base_layer()):
            return False
    except Exception:
        return False
    base = int(_base_layer())
    col = int(bind_col)
    ctype, path = _get(base, col)
    if str(ctype or '').strip().lower() != 'video' or not path:
        return False
    slot = _slot(base, col)
    if slot is None:
        return False
    try:
        _clear_video_prime_cache(base, col)
        playing = global_transport_playing() and _video_slot_should_play(base, col)
        _wire_video(slot, path, play=playing, resume=True, force_reload=True)
        return True
    except Exception:
        return False


def clear_cell_map_out_param_binds(layer, col, clip_type=None, scene=None):
    """Remove Map*out binds from a grid cell's clip parameters."""
    layer, col = int(layer), int(col)
    if clip_type is None:
        clip_type, _ = _cell_content(layer, col)
    target = _cell_param_target(layer, col, clip_type)
    cleared = _clear_map_out_binds_on_target(target, clip_type)
    slot = _slot(layer, col)
    if slot is not None:
        for entry in _cell_fx_list(layer, col, scene):
            fx_slot = _cell_fx_slot_comp(slot, entry.get('id'))
            if fx_slot is not None:
                cleared += _clear_map_out_binds_on_target(fx_slot.op('tox'), 'tox')
    return cleared


def _map_dial_has_stored_bind(index, r=None):
    if r is None:
        r = _root()
    if r is None:
        return False
    if str(_map_bind_expr(index, r) or '').strip():
        return True
    try:
        if str(r.fetch(_map_outbound_store_key(index), '') or '').strip():
            return True
        if str(r.fetch(_map_target_store_key(index), '') or '').strip():
            return True
    except Exception:
        pass
    return False


def reconcile_orphan_map_binds(r=None):
    """Adopt Map*out binds left on the selected cell's params without a dial entry."""
    if _MAP_PURGE_GUARD:
        return False
    if r is None:
        r = _root()
    if r is None:
        return False
    if _params_tab() == 'global':
        return False
    try:
        sel_layer = int(float(r.par.Selectedlayer.eval()))
        sel_col = int(float(r.par.Selectedcol.eval()))
    except Exception:
        return False
    _ensure_map_control_pars(r)
    changed = False
    seen = set()
    scene = int(_active_scene())
    for sl, sc in ((sel_layer, sel_col),):
        ctype, path = _get(sl, sc)
        target = None
        if path and _valid_clip_type(ctype):
            target = _cell_param_target(sl, sc, ctype)
        slot = _slot(sl, sc)
        if target is None and slot is not None:
            target = slot.op('tox')
            if target is not None:
                ctype = 'tox'
        bind_targets = []
        if target is not None:
            bind_targets.append((target, ctype or 'tox'))
        if slot is not None:
            for entry in _cell_fx_list(sl, sc):
                fx_slot = _cell_fx_slot_comp(slot, entry.get('id'))
                if fx_slot is None:
                    continue
                fx_tox = fx_slot.op('tox')
                if fx_tox is not None:
                    bind_targets.append((fx_tox, 'tox'))
        for target, tctype in bind_targets:
            for par in _copyable_cell_params(target, tctype):
                try:
                    if par.mode != ParMode.BIND:
                        continue
                except Exception:
                    continue
                bind_expr = _par_bind_expression(par)
                idx = _map_dial_index_from_output_bind_expr(bind_expr)
                if idx is None or idx in seen:
                    continue
                seen.add(idx)
                bank = _CELL_MAP_BY_KEY.get((scene, int(sl), int(sc)), {})
                bank_st = bank.get(idx) or bank.get(str(idx))
                if bank_st is not None and not _map_dial_state_has_bind(bank_st):
                    try:
                        par.mode = ParMode.CONSTANT
                        par.bindExpr = ''
                        changed = True
                    except Exception:
                        pass
                    continue
                if _map_dial_has_stored_bind(idx, r):
                    continue
                abs_expr = _absolute_bind_expr(par)
                if not abs_expr:
                    continue
                _remember_map_bind_target(idx, par, r)
                _set_map_bind_outbound(idx, abs_expr, r)
                _apply_map_range_from_target(idx, par, r, force=True)
                _clear_duplicate_map_out_binds(idx, keep_target=par, r=r)
                try:
                    seed = float(par.val)
                except Exception:
                    seed = 0.0
                try:
                    if abs(float(par.eval()) - seed) < 0.0001:
                        seed = _read_target_par_value(par)
                except Exception:
                    pass
                _set_map_dial_norm(
                    idx, _map_dial_norm_from_scaled(seed, idx, r), r, force_cook=True)
                _ensure_target_map_bind(idx, par, r, force=True)
                changed = True
    return changed


def repair_map_dial_binds(r=None):
    """Re-sync all map dial outbound links (fixes relative-path native binds)."""
    if r is None:
        r = _root()
    if r is None:
        return False
    try:
        _prune_stale_map_dial_assignments(r)
    except Exception:
        pass
    _ensure_map_control_pars(r)
    for idx in range(1, MAP_DIAL_COUNT + 1):
        if _is_map_bind_active(idx, r):
            _heal_map_output_par(idx, r)
            target = _resolve_bind_target(idx, r)
            if target is not None and not _is_map_driver_par(target):
                lo, hi = _map_dial_range(idx, r)
                force = _map_stored_range_is_default(lo, hi)
                if _apply_map_range_from_target(idx, target, r, force=force):
                    if force:
                        try:
                            cur_norm = float(_map_value_par(idx, r).eval())
                        except Exception:
                            cur_norm = 0.0
                        if cur_norm < 0.0001:
                            _set_map_dial_norm(
                                idx,
                                _map_dial_norm_from_scaled(
                                    _read_target_par_value(target), idx, r),
                                r, force_cook=True)
    try:
        reconcile_orphan_map_binds(r)
    except Exception:
        pass
    ok = False
    for idx in range(1, MAP_DIAL_COUNT + 1):
        bind_par = _map_bind_par(idx, r)
        _normalize_map_bind_par(bind_par, idx, r)
        driver = _map_driver_expr(idx, r) or _map_value_driver_expr(idx, r)
        if driver:
            if _ensure_map_value_driver_bind(idx, driver, r):
                ok = True
        if _map_bind_expr(idx, r) or _map_snapshot_target_expr(idx, r):
            if sync_map_dial_bind_from_par(idx, r):
                ok = True
        elif _apply_map_dial_scaled_bind(idx, r):
            ok = True
        if _is_map_bind_active(idx, r):
            try:
                norm = float(_map_value_par(idx, r).eval())
            except Exception:
                norm = None
            if norm is not None and not _map_bind_chain_is_live(idx, r, norm=norm):
                if _sync_map_dial_bound_target(idx, norm, r):
                    ok = True
        _paint_map_dial(idx, r)
    return ok


def open_map_dial_menu(index, r=None):
    """Right-click anywhere on a map dial — edit range, optionally clear bind."""
    if _is_map_bind_active(index, r):
        def _menu_choice(info):
            choice = info.get('item', '')
            if choice == 'Edit Min / Max...':
                _edit_map_dial_range_dialog_prompt(index, r)
            elif choice == 'Clear Bind':
                clear_map_dial_bind(index, r)

        try:
            op.TDResources.PopMenu.Open(
                items=['Edit Min / Max...', 'Clear Bind'],
                callback=_menu_choice,
            )
        except Exception as exc:
            print('Map dial menu error:', exc)
            return False
        return True
    return _edit_map_dial_range_dialog_prompt(index, r)


def open_map_dial_bind_menu(index, r=None):
    """Legacy alias — opens the map dial right-click menu."""
    return open_map_dial_menu(index, r)


def _map_control_expanded(r=None):
    if r is None:
        r = _root()
    if r is None:
        return True
    try:
        return bool(int(float(r.fetch('map_control_expanded', 1))))
    except Exception:
        return True


def set_map_control_expanded(expanded, r=None):
    if r is None:
        r = _root()
    if r is None:
        return False
    try:
        r.store('map_control_expanded', 1 if expanded else 0)
    except Exception:
        pass
    if not expanded:
        _save_active_map_control_state(r)
    _layout_map_control_section()
    if expanded:
        global _MAP_ACTIVE_CONTEXT
        ctx = _MAP_ACTIVE_CONTEXT or _current_map_context(r)
        if ctx is not None:
            if _MAP_ACTIVE_CONTEXT is None:
                _MAP_ACTIVE_CONTEXT = ctx
            _restore_map_control_state(ctx, r)
        repair_map_dial_binds(r)
        for idx in range(1, MAP_DIAL_COUNT + 1):
            _paint_map_dial(idx, r=r)
    return True


def toggle_map_control_expanded(r=None):
    return set_map_control_expanded(not _map_control_expanded(r), r)


def _map_control_section_height(r=None):
    if not _map_control_expanded(r):
        return MAP_CONTROL_ROW_HDR
    _, _, body_h = _map_dial_layout_metrics()
    return MAP_CONTROL_ROW_HDR + body_h


def _wire_map_control_dragdrop(comp):
    if comp is None:
        return
    cb = _ensure_map_control_dragdrop_dat()
    if cb is None:
        return
    try:
        comp.par.drop = 'usecallbacks'
        comp.par.drag = 'dragno'
        comp.par.dragdropcallbacks = cb
    except Exception:
        pass


def _ensure_map_control_dragdrop_dat():
    r = _root()
    if r is None:
        return None
    cb = r.op('map_control_dragdrop')
    if cb is None:
        try:
            cb = r.create('textDAT', 'map_control_dragdrop')
            cb.par.language = 'python'
        except Exception:
            return None
    try:
        cb.text = MAP_CONTROL_DRAGDROP
    except NameError:
        pass
    return cb


def _apply_map_bind_label_text_style(txt, text, w, fg=None, is_bind=False):
    if txt is None:
        return
    fg = fg or UI_TEXT_SECONDARY
    display = str(text or '')
    w = max(24, int(w))
    if display and display != MAP_DIAL_BIND_EMPTY_LABEL:
        display = _wrap_bind_label_display(display, dial_w=w)
    font = MAP_DIAL_BIND_LABEL_FONT
    tex_w = w
    try:
        txt.par.text = display
        txt.par.font = TD_FONT
        txt.par.fontsizex = font
        txt.par.fontsizey = font
        txt.par.resolutionw = tex_w
        txt.par.resolutionh = MAP_DIAL_BIND_LABEL_H
        # Manual \n line breaks only — wordwrap re-clips row 2 inside narrow dials.
        txt.par.wordwrap = False
        txt.par.linespacing = MAP_DIAL_BIND_LABEL_LINE_GAP
        txt.par.linespacingunit = 'pixels'
        txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = fg
        txt.par.alignx = 'center'
        txt.par.aligny = 'top'
        txt.par.positionx = 0
        txt.par.positiony = MAP_DIAL_BIND_LABEL_PAD_TOP
        txt.par.clickthrough = True
        txt.cook(force=True)
    except Exception:
        pass


def _style_map_bind_label(comp, txt, w, h, text, bg_alpha=0.0, fg=None):
    if comp is None or txt is None:
        return
    fg = fg or UI_TEXT_SECONDARY
    try:
        comp.par.w = w
        comp.par.h = h
        comp.par.top = txt
        comp.par.topfill = 'width'
        comp.par.clipping = True
        txt.par.bgalpha = bg_alpha
        _apply_map_bind_label_text_style(txt, text, w, fg=fg)
    except Exception:
        pass


def _style_map_chip(comp, txt, w, h, text, bg_alpha=0.35, fg=None, font_size=None):
    if comp is None or txt is None:
        return
    fg = fg or UI_TEXT_PRIMARY
    fs = TD_FONT_SIZE_SMALL if font_size is None else int(font_size)
    try:
        comp.par.w = w
        comp.par.h = h
        comp.par.top = txt
        comp.par.topfill = 'best'
        txt.par.text = str(text)
        txt.par.font = TD_FONT
        txt.par.fontsizex = fs
        txt.par.fontsizey = fs
        txt.par.resolutionw = w
        txt.par.resolutionh = h
        txt.par.bgalpha = bg_alpha
        txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = fg
        txt.par.alignx = 'center'
        txt.par.aligny = 'center'
        txt.par.clickthrough = True
        txt.cook(force=True)
    except Exception:
        pass


def _paint_map_dial_fader(knob, norm, display_value=None, cook_text=True):
    if knob is None:
        return
    try:
        fw = int(knob.par.w.eval())
        fh = int(knob.par.h.eval())
    except Exception:
        return
    fw, inner_h, pad = _opacity_slider_inner_size(fh, fw)
    layout = _opacity_track_layout(fw, inner_h, norm, pad=pad)
    for comp_name, key in (
        ('map_knob_groove', 'groove'),
        ('map_knob_fill', 'fill'),
        ('map_knob_thumb', 'thumb'),
    ):
        comp = knob.op(comp_name)
        if comp is None:
            continue
        x, y, w, h = layout[key]
        try:
            comp.par.x = int(x)
            comp.par.y = int(y)
            comp.par.w = int(max(1, w))
            comp.par.h = int(max(1, h)) if key == 'thumb' else int(h)
            comp.par.display = key != 'fill' or h > 0
            if key == 'thumb':
                comp.par.display = True
            comp.cook(force=True)
        except Exception:
            pass
    txt = knob.op('label_text')
    if txt is not None:
        try:
            show = display_value if display_value is not None else norm
            txt.par.text = _format_map_number(show)
            txt.par.resolutionw = max(24, fw)
            txt.par.resolutionh = max(10, min(14, fh // 3))
            txt.par.font = TD_FONT
            txt.par.fontsizex = TD_FONT_SIZE_SMALL
            txt.par.fontsizey = TD_FONT_SIZE_SMALL
            txt.par.bgalpha = 0.0
            txt.par.clickthrough = True
            txt.par.alignx = 'center'
            txt.par.aligny = 'center'
            txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = UI_TEXT_PRIMARY
            if cook_text:
                txt.cook(force=True)
            knob.par.top = txt
            knob.par.topfill = 'best'
        except Exception:
            pass
    try:
        knob.cook(force=True)
    except Exception:
        pass


def _ensure_map_control_parexec(r=None):
    if r is None:
        r = _root()
    if r is None:
        return None
    pe = r.op('map_control_parexec')
    if pe is None:
        pe = r.create('parameterexecuteDAT', 'map_control_parexec')
    try:
        pe.par.op = r
        pe.par.pars = ' '.join(
            name
            for i in range(1, MAP_DIAL_COUNT + 1)
            for name in (
                _map_value_par_name(i),
                _map_bind_par_name(i),
                _map_min_par_name(i),
                _map_max_par_name(i),
            )
        )
        pe.par.valuechange = True
        pe.par.modechange = True
        pe.par.expressionchange = True
        pe.par.active = True
    except Exception:
        pass
    try:
        text = _read_embedded_dat('map_control_parexec.py')
        if text:
            pe.text = text
    except Exception:
        pass
    return pe


def _ensure_map_dial_range_fields(dial, index, r=None, dial_w=None):
    """Min / max value chips — right-click to type, wheel to nudge."""
    if dial is None:
        return None
    if dial_w is None:
        dial_w, _, _ = _map_dial_layout_metrics()
    pad = MAP_DIAL_PAD
    bw = max(32, int(dial_w) - pad * 2)
    half_w = max(18, (bw - MAP_DIAL_RANGE_GAP) // 2)

    range_name = 'map_dial_{}_bind_range'.format(int(index))
    range_box = dial.op(range_name)
    if range_box is None:
        range_box = dial.create('containerCOMP', range_name)
    for stale in ('range_text', 'min_field', 'max_field'):
        old = range_box.op(stale)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass
    try:
        range_box.par.w = bw
        range_box.par.h = MAP_DIAL_RANGE_H
        range_box.par.hmode = 'fixed'
        range_box.par.vmode = 'fixed'
        range_box.par.align = 'none'
        range_box.par.clipping = True
        range_box.par.clickthrough = True
        range_box.par.bgcolorr, range_box.par.bgcolorg, range_box.par.bgcolorb = TD_BG_INPUT
        range_box.par.bgalpha = 0.0
    except Exception:
        pass

    for which, x_off in (('min', 0), ('max', half_w + MAP_DIAL_RANGE_GAP)):
        cname = 'map_dial_{}_range_{}'.format(int(index), which)
        chip = range_box.op(cname)
        if chip is not None and chip.opType != 'containerCOMP':
            try:
                chip.destroy()
            except Exception:
                pass
            chip = None
        if chip is None:
            chip = range_box.create('containerCOMP', cname)
        try:
            chip.par.x = int(x_off)
            chip.par.y = 0
            chip.par.w = half_w
            chip.par.h = MAP_DIAL_RANGE_H
            chip.par.hmode = 'fixed'
            chip.par.vmode = 'fixed'
            chip.par.align = 'none'
            chip.par.clipping = True
            chip.par.clickthrough = False
            chip.par.mousewheel = True
            chip.par.bgcolorr, chip.par.bgcolorg, chip.par.bgcolorb = TD_BG_INPUT
            chip.par.bgalpha = 1.0
        except Exception:
            pass
        txt = chip.op('value_text')
        if txt is None:
            txt = chip.create('textTOP', 'value_text')
        default = _format_map_number(MAP_DEFAULT_MIN if which == 'min' else MAP_DEFAULT_MAX)
        _style_map_chip(
            chip, txt, half_w, MAP_DIAL_RANGE_H, default,
            bg_alpha=0.0, fg=UI_TEXT_SECONDARY,
        )
        try:
            txt.par.clickthrough = False
        except Exception:
            pass
    return range_box


def _ensure_map_dial_bind_panel(dial, index, r=None, dial_w=None):
    """Value + linked parameter name; drag parameters onto either row."""
    if dial is None:
        return None
    if r is None:
        r = _root()
    if dial_w is None:
        dial_w, _, _ = _map_dial_layout_metrics()
    pad = MAP_DIAL_PAD
    bw = max(32, int(dial_w) - pad * 2)

    for stale_name in (
        'map_dial_{}_bind'.format(int(index)),
        'map_dial_{}_bind_name'.format(int(index)),
        'map_dial_{}_bindpar'.format(int(index)),
        'bind_par',
    ):
        old = dial.op(stale_name)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass

    val_name = 'map_dial_{}_bind_value'.format(int(index))
    val_box = dial.op(val_name)
    if val_box is None:
        val_box = dial.create('containerCOMP', val_name)
    try:
        val_box.par.w = bw
        val_box.par.h = MAP_DIAL_BIND_VALUE_H
        val_box.par.hmode = 'fixed'
        val_box.par.vmode = 'fixed'
        val_box.par.align = 'none'
        val_box.par.clipping = True
        val_box.par.clickthrough = False
        val_box.par.bgcolorr, val_box.par.bgcolorg, val_box.par.bgcolorb = TD_BG_INPUT
        val_box.par.bgalpha = 1.0
    except Exception:
        pass
    val_txt = val_box.op('value_text')
    if val_txt is None:
        val_txt = val_box.create('textTOP', 'value_text')
    _style_map_chip(
        val_box, val_txt, bw, MAP_DIAL_BIND_VALUE_H, '0.00',
        bg_alpha=0.0, fg=UI_TEXT_PRIMARY,
    )
    _wire_map_control_dragdrop(val_box)
    _ensure_map_dial_range_fields(dial, index, r=r, dial_w=dial_w)

    label_name = 'map_dial_{}_bind_label'.format(int(index))
    label_box = dial.op(label_name)
    if label_box is None:
        label_box = dial.create('containerCOMP', label_name)
    try:
        label_box.par.w = bw
        label_box.par.h = MAP_DIAL_BIND_LABEL_H
        label_box.par.hmode = 'fixed'
        label_box.par.vmode = 'fixed'
        label_box.par.align = 'none'
        label_box.par.clipping = False
        label_box.par.clickthrough = False
        label_box.par.bgcolorr, label_box.par.bgcolorg, label_box.par.bgcolorb = TD_BG_INPUT
        label_box.par.bgalpha = 1.0
    except Exception:
        pass
    label_txt = label_box.op('link_text')
    if label_txt is None:
        label_txt = label_box.create('textTOP', 'link_text')
    _style_map_bind_label(
        label_box, label_txt, bw, MAP_DIAL_BIND_LABEL_H, MAP_DIAL_BIND_EMPTY_LABEL,
        bg_alpha=0.0, fg=UI_TEXT_SECONDARY,
    )
    _wire_map_control_dragdrop(label_box)
    return label_box


def _layout_map_dial_internals(index, dial_w=None, dial_h=None):
    """Stack fader on top; value, range, bind label underneath; index at bottom."""
    dial = _map_dial_comp(index)
    if dial is None:
        return
    if dial_w is None or dial_h is None:
        dial_w, dial_h, _ = _map_dial_layout_metrics()
    pad = MAP_DIAL_PAD
    inner_w = max(32, int(dial_w) - pad * 2)
    index_y = MAP_DIAL_PAD
    label_y = index_y + MAP_DIAL_INDEX_H + MAP_DIAL_BIND_LABEL_INDEX_GAP
    range_y = label_y + MAP_DIAL_BIND_LABEL_H + MAP_DIAL_BIND_LABEL_RANGE_GAP
    value_y = range_y + MAP_DIAL_RANGE_H + MAP_DIAL_ROW_GAP
    fader_y = value_y + MAP_DIAL_BIND_VALUE_H + MAP_DIAL_ROW_GAP
    fader_h = MAP_DIAL_FADER_H
    try:
        dial.par.w = int(dial_w)
        dial.par.h = int(dial_h)
        dial.par.clipping = True
        dial.par.align = 'none'
        dial.par.clickthrough = True
    except Exception:
        pass
    idx_txt = dial.op('index_text')
    if idx_txt is not None:
        try:
            idx_txt.par.text = str(int(index))
            idx_txt.par.resolutionw = 12
            idx_txt.par.resolutionh = MAP_DIAL_INDEX_H
            idx_txt.par.positionx = 1
            idx_txt.par.positiony = 1
            idx_txt.par.x = pad
            idx_txt.par.y = index_y
        except Exception:
            pass
    val_box = dial.op('map_dial_{}_bind_value'.format(int(index)))
    range_box = dial.op('map_dial_{}_bind_range'.format(int(index)))
    label_box = dial.op('map_dial_{}_bind_label'.format(int(index)))
    if val_box is not None:
        try:
            val_box.par.x = pad
            val_box.par.y = value_y
            val_box.par.w = inner_w
            val_box.par.h = MAP_DIAL_BIND_VALUE_H
        except Exception:
            pass
        txt = val_box.op('value_text')
        if txt is not None:
            try:
                val_box.par.top = txt
                val_box.par.topfill = 'best'
                txt.par.resolutionw = max(24, int(inner_w))
                txt.par.resolutionh = MAP_DIAL_BIND_VALUE_H
            except Exception:
                pass
    if range_box is not None:
        half_w = max(18, (inner_w - MAP_DIAL_RANGE_GAP) // 2)
        try:
            range_box.par.x = pad
            range_box.par.y = range_y
            range_box.par.w = inner_w
            range_box.par.h = MAP_DIAL_RANGE_H
        except Exception:
            pass
        for which, x_off in (('min', 0), ('max', half_w + MAP_DIAL_RANGE_GAP)):
            chip = range_box.op('map_dial_{}_range_{}'.format(int(index), which))
            if chip is None:
                continue
            try:
                chip.par.x = int(x_off)
                chip.par.y = 0
                chip.par.w = half_w
                chip.par.h = MAP_DIAL_RANGE_H
            except Exception:
                pass
            txt = chip.op('value_text')
            if txt is not None:
                try:
                    chip.par.top = txt
                    chip.par.topfill = 'best'
                    txt.par.resolutionw = max(18, int(half_w))
                    txt.par.resolutionh = MAP_DIAL_RANGE_H
                except Exception:
                    pass
    if label_box is not None:
        try:
            label_box.par.x = pad
            label_box.par.y = label_y
            label_box.par.w = inner_w
            label_box.par.h = MAP_DIAL_BIND_LABEL_H
        except Exception:
            pass
        txt = label_box.op('link_text')
        if txt is not None:
            try:
                label_box.par.top = txt
                label_box.par.topfill = 'width'
                label_box.par.clipping = True
                r = _root()
                link_text = _map_dial_link_label_text(index, dial_w=inner_w, r=r)
                is_bind = _is_map_bind_active(index, r)
                if is_bind:
                    fg = TD_BIND_EXPR
                else:
                    fg = UI_TEXT_SECONDARY
                _apply_map_bind_label_text_style(
                    txt, link_text, inner_w, fg=fg, is_bind=is_bind)
            except Exception:
                pass
    knob = dial.op('map_dial_{}_knob'.format(int(index)))
    if knob is not None:
        try:
            knob.par.x = pad
            knob.par.y = fader_y
            knob.par.w = inner_w
            knob.par.h = fader_h
        except Exception:
            pass


def _upgrade_map_dial_knob(knob):
    if knob is None:
        return
    try:
        knob.par.top = ''
        knob.par.clickthrough = False
        knob.par.cursor = 'ns-resize'
        knob.par.bgcolorr, knob.par.bgcolorg, knob.par.bgcolorb = TD_SLIDER_TRACK
        knob.par.bgalpha = 0.12
        knob.par.hmode = 'fixed'
        knob.par.vmode = 'fixed'
        knob.par.align = 'none'
    except Exception:
        pass
    for name, rgb in (
        ('map_knob_groove', TD_SLIDER_GROOVE),
        ('map_knob_fill', TD_SLIDER_FILL),
        ('map_knob_thumb', TD_SLIDER_THUMB),
    ):
        comp = knob.op(name)
        if comp is None:
            comp = knob.create('containerCOMP', name)
        _style_opacity_slider_part(comp, rgb, alpha=1.0, clickthrough=True)
    txt = knob.op('label_text')
    if txt is None:
        txt = knob.create('textTOP', 'label_text')
    try:
        txt.par.clickthrough = True
        txt.par.bgalpha = 0.0
        txt.par.alignx = 'center'
        txt.par.aligny = 'center'
        txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = UI_TEXT_PRIMARY
    except Exception:
        pass
    _wire_map_control_dragdrop(knob)


def _paint_map_dial(index, r=None, light=False):
    dial = _map_dial_comp(index)
    if dial is None:
        return
    if int(index) in _MAP_DIAL_MIDI_WRITE:
        return
    if r is None:
        r = _root()
    if (
        r is not None
        and int(index) not in _MAP_DIAL_DRAG_ACTIVE
        and not map_dial_midi_blocked(index)
        and not global_transport_playing()
    ):
        _sync_map_dial_norm_from_bound_target(index, r)
    try:
        norm = max(0.0, min(1.0, float(getattr(r.par, _map_value_par_name(index)).eval())))
    except Exception:
        norm = map_dial_norm(index, r)
    scaled = _map_dial_scaled_from_norm(norm, index, r)
    try:
        dial_w = int(dial.par.w.eval())
    except Exception:
        dial_w = None
    if not dial_w or dial_w < 32:
        dial_w, _, _ = _map_dial_layout_metrics()
    label_w = _map_dial_label_width(dial_w)
    value_text = _map_dial_value_text(scaled)
    knob = dial.op('map_dial_{}_knob'.format(int(index)))
    if knob is not None:
        _paint_map_dial_fader(knob, norm, scaled, cook_text=not light)
    val_box = dial.op('map_dial_{}_bind_value'.format(int(index)))
    if val_box is not None:
        txt = val_box.op('value_text')
        if txt is not None:
            try:
                txt.par.text = value_text
                if light:
                    txt.cook(force=True)
                else:
                    txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = UI_TEXT_PRIMARY
                    txt.par.fontsizex = TD_FONT_SIZE_SMALL
                    txt.par.fontsizey = TD_FONT_SIZE_SMALL
                    val_box.par.bgcolorr, val_box.par.bgcolorg, val_box.par.bgcolorb = TD_BG_INPUT
                    txt.cook(force=True)
            except Exception:
                pass
    lo, hi = _map_dial_range(index, r)
    min_text = _format_map_number(lo)
    max_text = _format_map_number(hi)
    link_text = _map_dial_link_label_text(index, dial_w=label_w, r=r)
    is_bind = _is_map_bind_active(index, r)
    label_box = dial.op('map_dial_{}_bind_label'.format(int(index)))
    if label_box is not None:
        txt = label_box.op('link_text')
        if txt is not None:
            try:
                if is_bind:
                    fg = TD_BIND_EXPR
                    label_box.par.bgcolorr, label_box.par.bgcolorg, label_box.par.bgcolorb = TD_BIND_BG
                else:
                    fg = UI_TEXT_SECONDARY
                    label_box.par.bgcolorr, label_box.par.bgcolorg, label_box.par.bgcolorb = TD_BG_INPUT
                _apply_map_bind_label_text_style(
                    txt, link_text, label_w, fg=fg, is_bind=is_bind)
            except Exception:
                pass
    if light:
        return
    range_box = dial.op('map_dial_{}_bind_range'.format(int(index)))
    if range_box is not None:
        for which, text in (('min', min_text), ('max', max_text)):
            chip = range_box.op('map_dial_{}_range_{}'.format(int(index), which))
            if chip is None:
                continue
            txt = chip.op('value_text')
            if txt is None:
                continue
            try:
                txt.par.text = text
                txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = UI_TEXT_SECONDARY
                txt.par.fontsizex = TD_FONT_SIZE_SMALL
                txt.par.fontsizey = TD_FONT_SIZE_SMALL
                txt.cook(force=True)
            except Exception:
                pass


def _ensure_map_dial(parent, index):
    name = 'map_dial_{}'.format(int(index))
    dial = parent.op(name)
    if dial is None:
        dial = parent.create('containerCOMP', name)
    try:
        dial.par.w = MAP_DIAL_W
        dial.par.h = MAP_DIAL_H
        dial.par.align = 'none'
        dial.par.clipping = True
        dial.par.clickthrough = True
        dial.par.bgcolorr, dial.par.bgcolorg, dial.par.bgcolorb = 0, 0, 0
        dial.par.bgalpha = 0.0
    except Exception:
        pass
    idx_txt = dial.op('index_text')
    if idx_txt is None:
        idx_txt = dial.create('textTOP', 'index_text')
    try:
        idx_txt.par.text = str(int(index))
        idx_txt.par.font = TD_FONT
        idx_txt.par.fontsizex = TD_FONT_SIZE_SMALL
        idx_txt.par.fontsizey = TD_FONT_SIZE_SMALL
        idx_txt.par.resolutionw = 14
        idx_txt.par.resolutionh = MAP_DIAL_INDEX_H
        idx_txt.par.bgalpha = 0.0
        idx_txt.par.fontcolorr, idx_txt.par.fontcolorg, idx_txt.par.fontcolorb = UI_TEXT_SECONDARY
        idx_txt.par.alignx = 'left'
        idx_txt.par.aligny = 'center'
        idx_txt.par.positionx = 2
        idx_txt.par.clickthrough = True
    except Exception:
        pass
    knob_name = 'map_dial_{}_knob'.format(int(index))
    knob = dial.op(knob_name)
    if knob is None:
        knob = dial.create('containerCOMP', knob_name)
    _upgrade_map_dial_knob(knob)
    _ensure_map_dial_bind_panel(dial, index, r=_root())
    _layout_map_dial_internals(index)
    return dial


def _ensure_map_control_section():
    r = _root()
    ui = r.op('ui') if r else None
    if ui is None:
        return None
    _ensure_map_control_pars(r)
    section = ui.op('map_control_section')
    if section is None:
        section = ui.create('containerCOMP', 'map_control_section')
    for stale in ('map_control_params', 'map_control_sliders'):
        old = section.op(stale)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                try:
                    old.par.display = False
                    old.par.enable = False
                except Exception:
                    pass
    try:
        section.par.w = panel_w
        section.par.align = 'none'
        section.par.clipping = True
        section.par.bgcolorr, section.par.bgcolorg, section.par.bgcolorb = TD_BG_MAIN
        section.par.bgalpha = 1.0
    except Exception:
        pass
    hdr = section.op('map_control_hdr')
    if hdr is None:
        hdr = section.create('containerCOMP', 'map_control_hdr')
    try:
        hdr.par.h = MAP_CONTROL_ROW_HDR
        hdr.par.hmode = 'fixed'
        hdr.par.vmode = 'fixed'
        hdr.par.bgcolorr, hdr.par.bgcolorg, hdr.par.bgcolorb = UI_NAME_BAR_BG
        hdr.par.bgalpha = 1.0
        hdr.par.drag = 'dragno'
        hdr.par.drop = 'dropno'
        hdr.par.clickthrough = False
    except Exception:
        pass
    title = hdr.op('title_text')
    if title is None:
        title = hdr.create('textTOP', 'title_text')
    try:
        title.par.text = _map_control_scope_label(r)
        title.par.font = TD_FONT
        title.par.fontsizex = TD_FONT_SIZE
        title.par.fontsizey = TD_FONT_SIZE
        title.par.resolutionw = _fx_accordion_title_width(panel_w)
        title.par.resolutionh = MAP_CONTROL_ROW_HDR
        title.par.bgalpha = 0.0
        title.par.fontcolorr, title.par.fontcolorg, title.par.fontcolorb = UI_TEXT_PRIMARY
        title.par.alignx = 'left'
        title.par.aligny = 'center'
        title.par.positionx = FX_HDR_TITLE_PAD
        title.par.textoffsetx = FX_HDR_TITLE_TEXT_OFFSET_X
        title.par.clickthrough = True
        hdr.par.top = title
        hdr.par.topfill = 'best'
    except Exception:
        pass
    expand = hdr.op('map_control_expand')
    if expand is None:
        expand = hdr.create('containerCOMP', 'map_control_expand')
    try:
        expand.par.w = FX_HDR_EXPAND_W
        expand.par.h = MAP_CONTROL_ROW_HDR - 4
        expand.par.x = max(80, int(panel_w) - FX_HDR_EXPAND_W - 2)
        expand.par.y = 2
        expand.par.clickthrough = True
    except Exception:
        pass
    etxt = expand.op('label_text')
    if etxt is None:
        etxt = expand.create('textTOP', 'label_text')
    try:
        etxt.par.clickthrough = True
    except Exception:
        pass
    _sync_fx_accordion_expand_icon(expand, _map_control_expanded(r), MAP_CONTROL_ROW_HDR)
    body = section.op('map_control_dials')
    if body is None:
        body = section.create('containerCOMP', 'map_control_dials')
    try:
        body.par.align = 'none'
        body.par.clipping = True
        body.par.bgcolorr, body.par.bgcolorg, body.par.bgcolorb = TD_BG_MAIN
        body.par.bgalpha = 1.0
    except Exception:
        pass
    for idx in range(1, MAP_DIAL_COUNT + 1):
        _ensure_map_dial(body, idx)
    return section


def _layout_map_control_section(total_h=None, bottom_y=0):
    ui = _root().op('ui') if _root() else None
    if ui is None:
        return
    section = _ensure_map_control_section()
    if section is None:
        return
    expanded = _map_control_expanded()
    dial_w, dial_h, body_h_default = _map_dial_layout_metrics()
    body_h = body_h_default if expanded else 0
    section_h = MAP_CONTROL_ROW_HDR + body_h
    if total_h is not None:
        section_h = int(total_h)
        body_h = max(0, section_h - MAP_CONTROL_ROW_HDR)
    panel_w = _cell_panel_w()
    try:
        section.par.x = UI_PANEL_X
        section.par.y = int(bottom_y)
        section.par.w = panel_w
        section.par.h = section_h
        section.par.hmode = 'fixed'
        section.par.vmode = 'fixed'
    except Exception:
        pass
    hdr = section.op('map_control_hdr')
    if hdr is not None:
        try:
            hdr.par.x = 0
            hdr.par.y = body_h
            hdr.par.w = panel_w
            hdr.par.h = MAP_CONTROL_ROW_HDR
        except Exception:
            pass
    expand = section.op('map_control_hdr/map_control_expand')
    if expand is not None:
        _sync_fx_accordion_expand_icon(expand, expanded, MAP_CONTROL_ROW_HDR)
    body = section.op('map_control_dials')
    if body is not None:
        try:
            body.par.x = 0
            body.par.y = 0
            body.par.w = panel_w
            body.par.h = body_h
            body.par.display = expanded and body_h > 0
            body.par.enable = expanded and body_h > 0
        except Exception:
            pass
        if expanded and body_h > 0:
            dial_y = max(0, body_h - MAP_CONTROL_BODY_PAD - dial_h)
            for idx in range(1, MAP_DIAL_COUNT + 1):
                dial = body.op('map_dial_{}'.format(idx))
                if dial is None:
                    continue
                col = idx - 1
                x = MAP_CONTROL_BODY_PAD + col * (dial_w + MAP_DIAL_GAP)
                try:
                    dial.par.x = x
                    dial.par.y = dial_y
                    dial.par.display = True
                    dial.par.enable = True
                except Exception:
                    pass
                _layout_map_dial_internals(idx, dial_w=dial_w, dial_h=dial_h)


def map_dial_value_from_panel(panel, owner, index=None):
    knob = _map_dial_knob_from_owner(owner)
    if knob is None:
        v = _read_panel_v(panel)
        return None if v is None else max(0.0, min(1.0, float(v)))
    # Always map against the full knob track (clicks on thumb/groove children included).
    v = None
    try:
        kp = knob.panel
        for name in ('insidev', 'v', 'mousev'):
            try:
                val = float(getattr(kp, name))
                if 0.0 <= val <= 1.0:
                    v = val
                    break
            except Exception:
                pass
    except Exception:
        pass
    if v is None:
        v = _read_panel_v(panel)
    if v is None:
        return None
    try:
        fader_h = float(knob.par.h.eval())
        fader_w = float(knob.par.w.eval())
    except Exception:
        return None
    if fader_h <= 0:
        return None
    fw, inner_h, pad = _opacity_slider_inner_size(int(fader_h), int(fader_w))
    track_rel = float(v) * fader_h - pad
    return max(0.0, min(1.0, track_rel / max(1.0, float(inner_h))))


def _map_dial_index_from_comp(comp):
    p = comp
    for _ in range(8):
        if p is None:
            break
        name = getattr(p, 'name', '')
        if name.startswith('map_dial_'):
            parts = name.split('_')
            if len(parts) >= 3 and parts[2].isdigit():
                return int(parts[2])
            if name.startswith('map_dial_') and name.endswith('_knob'):
                try:
                    return int(name.replace('map_dial_', '').replace('_knob', ''))
                except Exception:
                    pass
            if name.startswith('map_dial_') and name.endswith('_bind_value'):
                try:
                    return int(name.replace('map_dial_', '').replace('_bind_value', ''))
                except Exception:
                    pass
            if name.startswith('map_dial_') and name.endswith('_range_min'):
                try:
                    return int(name.replace('map_dial_', '').replace('_range_min', ''))
                except Exception:
                    pass
            if name.startswith('map_dial_') and name.endswith('_range_max'):
                try:
                    return int(name.replace('map_dial_', '').replace('_range_max', ''))
                except Exception:
                    pass
            if name.startswith('map_dial_') and name.endswith('_bind_label'):
                try:
                    return int(name.replace('map_dial_', '').replace('_bind_label', ''))
                except Exception:
                    pass
            if name.startswith('map_dial_') and name.endswith('_bind') and not name.endswith('_bind_value'):
                try:
                    return int(name.replace('map_dial_', '').replace('_bind', ''))
                except Exception:
                    pass
        try:
            p = p.parent()
        except Exception:
            break
    return None


def _refresh_map_control_layout_only(r=None):
    """Rebuild map UI chrome without swapping dial banks (safe during script reload)."""
    _ensure_map_control_section()
    _ensure_map_control_parexec()
    _layout_map_control_section()
    _update_map_control_header_label(r)
    _refresh_panel_exec_panels()


def refresh_map_control_ui():
    _refresh_map_control_layout_only()
    _maybe_migrate_legacy_map_control()
    sync_map_control_context()
    repair_map_dial_binds()
