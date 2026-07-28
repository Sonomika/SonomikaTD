_DEFER_COMPOSITION_REBUILD = False
_COMPOSITION_RESTART_VIDEOS = False
_PENDING_CELL_XFADE = {'token': 0}
_PENDING_COLUMN_XFADE = {'token': 0}


def _xfade_allowed():
    """Crossfades need cooking frames; paused transport freezes run()/onFrameStart."""
    return bool(global_transport_playing())


def _cancel_pending_xfades():
    """Invalidate deferred cell/column fade starters."""
    try:
        _PENDING_CELL_XFADE['token'] = int(_PENDING_CELL_XFADE.get('token', 0)) + 1
    except Exception:
        _PENDING_CELL_XFADE['token'] = 1
    try:
        _PENDING_COLUMN_XFADE['token'] = int(_PENDING_COLUMN_XFADE.get('token', 0)) + 1
    except Exception:
        _PENDING_COLUMN_XFADE['token'] = 1


def _snap_xfades_for_pause():
    """Finish or drop fades so selection rings stay in sync while paused."""
    _cancel_pending_xfades()
    if not _COLUMN_XFADE.get('active'):
        return False
    try:
        to_col = int(_COLUMN_XFADE.get('to_col', 1))
        from_col = int(_COLUMN_XFADE.get('from_col', 1))
    except Exception:
        to_col, from_col = 1, 1
    try:
        _finish_column_xfade(to_col, from_col)
    except Exception:
        _COLUMN_XFADE['active'] = False
        _COLUMN_XFADE['stacks_wired'] = False
        _COLUMN_XFADE['keep_tick'] = 0
    try:
        _refresh_ui(full=True)
    except Exception:
        pass
    return True


def _request_composition_video_restart():
    """Cue live movies from frame 0 on the next composition rebuild."""
    global _COMPOSITION_RESTART_VIDEOS
    _COMPOSITION_RESTART_VIDEOS = True


def _composition_video_restart_requested():
    return bool(_COMPOSITION_RESTART_VIDEOS)


def _clear_composition_video_restart():
    global _COMPOSITION_RESTART_VIDEOS
    _COMPOSITION_RESTART_VIDEOS = False


def _route_composition_out():
    r = _root()
    if r is None:
        return
    if _COLUMN_XFADE.get('active'):
        if _COLUMN_XFADE.get('mode') in ('layer_col', 'column_layers'):
            expr = _layer_out_abs_expr(1)
            if expr:
                _set_top_expr(r.op('chain_out'), expr)
        return
    top_col = _get_layer_src_col(1)
    _set_top_expr(r.op('chain_out'), "op('slots/layer_1/col_{}/out1')".format(top_col))


def _refresh_layer_col_routing(layer):
    """Point chain/upstream at layer out1 so col_xfade is visible on program out."""
    layer = int(layer)
    for above in range(layer - 1, 0, -1):
        slot = _slot(above, _get_layer_src_col(above))
        if slot is not None:
            _wire_upstream(slot, above)
    _route_composition_out()


def _refresh_column_layers_routing(fade_layers):
    """Rewire upstream above every layer row that is crossfading cells."""
    for fade_layer in sorted(int(layer) for layer in fade_layers.keys()):
        for above in range(fade_layer - 1, 0, -1):
            slot = _slot(above, _get_layer_src_col(above))
            if slot is not None:
                _wire_upstream(slot, above)
    _route_composition_out()


def _route_prime_cols(
    xfade_column_layers=False,
    column_layer_fade=None,
    xfade_layer_col=False,
    fade_layer=0,
    fade_cols=(),
):
    """Slots that chain_out / col_xfade will sample on the next cook."""
    column_layer_fade = column_layer_fade or {}
    prime = {}
    for layer in range(1, _num_layers() + 1):
        cols = [_get_layer_src_col(layer)]
        if xfade_column_layers and int(layer) in column_layer_fade:
            fc, tc = column_layer_fade[int(layer)]
            cols = [fc, tc]
        elif xfade_layer_col and int(layer) == int(fade_layer):
            cols = list(fade_cols)
        prime[int(layer)] = [int(c) for c in cols]
    return prime


def _prime_route_slots(layer_cols):
    """Cook slot outputs at the correct render scale before chain_out retargets."""
    seen = set()
    for layer, cols in (layer_cols or {}).items():
        for sc in cols:
            key = (int(layer), int(sc))
            if key in seen:
                continue
            seen.add(key)
            slot = _slot(key[0], key[1])
            if slot is None:
                continue
            _apply_slot_canvas(slot)
            out = slot.op('out1')
            if out is not None:
                try:
                    out.cook(force=True)
                except Exception:
                    pass
    for layer, cols in (layer_cols or {}).items():
        if len(cols) < 2:
            continue
        layer_comp = _layer(int(layer))
        if layer_comp is None:
            continue
        for name in ('col_xfade', 'out1'):
            node = layer_comp.op(name)
            if node is None:
                continue
            try:
                node.cook(force=True)
            except Exception:
                pass


def _column_layers_fade_cols(layer):
    """(from_col, to_col) for a layer during column_layers crossfade, or None."""
    if _COLUMN_XFADE.get('mode') != 'column_layers':
        return None
    from_sig = tuple(_COLUMN_XFADE.get('from_sig') or ())
    to_sig = tuple(_COLUMN_XFADE.get('to_sig') or ())
    layer = int(layer)
    if len(from_sig) < layer or len(to_sig) < layer:
        return None
    fc = int(from_sig[layer - 1])
    tc = int(to_sig[layer - 1])
    if fc == tc:
        return None
    return fc, tc


def _sig_fade_map(from_sig, to_sig):
    """layer -> (from_col, to_col) for rows whose column assignment changes."""
    from_sig = tuple(from_sig or ())
    to_sig = tuple(to_sig or ())
    fade = {}
    for layer in range(1, min(len(from_sig), len(to_sig)) + 1):
        fc = int(from_sig[layer - 1])
        tc = int(to_sig[layer - 1])
        if fc != tc:
            fade[int(layer)] = (fc, tc)
    return fade


def _column_layers_fade_map():
    """layer -> (from_col, to_col) for every row that changes column."""
    if _COLUMN_XFADE.get('mode') != 'column_layers':
        return {}
    return _sig_fade_map(
        _COLUMN_XFADE.get('from_sig') or (),
        _COLUMN_XFADE.get('to_sig') or (),
    )


def _xfade_root_stack_active():
    """Full-column column_xfade (not per-layer col_xfade)."""
    return bool(
        _COLUMN_XFADE.get('active')
        and _COLUMN_XFADE.get('mode') not in ('layer_col', 'column_layers')
    )


def _column_xfade_video_enabled():
    """Column crossfades always blend video (per-row col_xfade path)."""
    return _column_xfade_enabled()


def _column_xfade_video_cut_active():
    """Column crossfade is on but video snaps to incoming (FX-only blend)."""
    return _xfade_root_stack_active() and not _column_xfade_video_enabled()


def _hybrid_xfade_prev_sig(from_sig, to_sig):
    """Outgoing stack with incoming video columns — FX crossfade, video cut."""
    from_sig = tuple(from_sig or ())
    to_sig = tuple(to_sig or ())
    if not from_sig or not to_sig:
        return from_sig
    out = list(from_sig)
    for layer in range(1, min(len(out), len(to_sig)) + 1):
        from_col = int(from_sig[layer - 1])
        to_col = int(to_sig[layer - 1])
        if from_col == to_col:
            continue
        ctype, path = _cell_content(layer, from_col)
        if path and str(ctype).strip().lower() == 'video':
            out[layer - 1] = to_col
    return tuple(out)


def _column_xfade_outgoing_sig(from_sig=None, to_sig=None):
    from_sig = tuple(
        from_sig if from_sig is not None else (_COLUMN_XFADE.get('from_sig') or ())
    )
    to_sig = tuple(
        to_sig if to_sig is not None else (_COLUMN_XFADE.get('to_sig') or ())
    )
    if not from_sig or _column_xfade_video_enabled():
        return from_sig
    return _hybrid_xfade_prev_sig(from_sig, to_sig)


def _xfade_video_cut_play_cols(layer):
    """Per-layer play columns when video snaps during column crossfade."""
    if not _column_xfade_video_cut_active():
        return None
    from_sig = tuple(_COLUMN_XFADE.get('from_sig') or ())
    to_sig = tuple(_COLUMN_XFADE.get('to_sig') or ())
    layer = int(layer)
    if len(from_sig) < layer or len(to_sig) < layer:
        return None
    from_col = int(from_sig[layer - 1])
    to_col = int(to_sig[layer - 1])
    if from_col == to_col:
        return {to_col}
    ctype_from, path_from = _cell_content(layer, from_col)
    ctype_to, path_to = _cell_content(layer, to_col)
    if (path_from and str(ctype_from).strip().lower() == 'video') or (
        path_to and str(ctype_to).strip().lower() == 'video'
    ):
        return {to_col}
    return {from_col, to_col}


def _sig_layer_matches(sig_a, sig_b, layer):
    layer = int(layer)
    if len(sig_a) < layer or len(sig_b) < layer:
        return False
    return int(sig_a[layer - 1]) == int(sig_b[layer - 1])


def _bind_root_column_xfade_selects(r=None):
    if r is None:
        r = _root()
    if r is None or not _xfade_root_stack_active():
        return
    from_sig = tuple(_COLUMN_XFADE.get('from_sig') or ())
    to_sig = tuple(_COLUMN_XFADE.get('to_sig') or ())
    wire_from = _column_xfade_outgoing_sig(from_sig, to_sig)
    prev = r.op('chain_prev')
    nxt = r.op('chain_next')
    cross = r.op('column_xfade')
    if prev is not None and wire_from:
        _set_top_expr(prev, _sig_layer1_out_expr(wire_from))
    if nxt is not None and to_sig:
        _set_top_expr(nxt, _sig_layer1_out_expr(to_sig))
    _rebind_xfade_top_resolution(prev, nxt, cross)


def _pause_outgoing_xfade_videos():
    """Stop decoding outgoing column videos during FX-only column crossfade."""
    if not _column_xfade_video_cut_active():
        return
    from_sig = tuple(_COLUMN_XFADE.get('from_sig') or ())
    to_sig = tuple(_COLUMN_XFADE.get('to_sig') or ())
    for layer in range(1, min(len(from_sig), len(to_sig)) + 1):
        from_col = int(from_sig[layer - 1])
        to_col = int(to_sig[layer - 1])
        if from_col == to_col:
            continue
        ctype, path = _cell_content(layer, from_col)
        if not path or str(ctype).strip().lower() != 'video':
            continue
        slot = _slot(layer, from_col)
        if slot is not None:
            _pause_slot(slot, on=False, clip_type='video')


def _wire_root_column_xfade_stacks(play=True, force=False, restart_videos=False):
    """Wire both outgoing/incoming column stacks for column_xfade (once per fade)."""
    if not _xfade_root_stack_active():
        return
    if not force and _COLUMN_XFADE.get('stacks_wired'):
        return
    from_sig = tuple(_COLUMN_XFADE.get('from_sig') or ())
    to_sig = tuple(_COLUMN_XFADE.get('to_sig') or ())
    wire_from = _column_xfade_outgoing_sig(from_sig, to_sig)
    if to_sig:
        _prep_signature_media(to_sig, restart_videos=restart_videos)
        _wire_signature_stack(
            to_sig, play=bool(play), restart_videos=restart_videos,
        )
    if wire_from and wire_from != to_sig:
        _prep_signature_media(wire_from, skip_layers_matching=to_sig)
        _wire_signature_stack(
            wire_from,
            play=bool(play),
            skip_layers_matching=to_sig,
            restart_videos=False,
        )
    elif wire_from and not to_sig:
        _prep_signature_media(wire_from)
        _wire_signature_stack(wire_from, play=bool(play), restart_videos=False)
    _COLUMN_XFADE['stacks_wired'] = True
    _bind_root_column_xfade_selects()
    _pause_outgoing_xfade_videos()


def _rebuild_composition():
    """Build live stack from per-layer column picks (e.g. Col1 L2+L3+L4 + Col2 L1)."""
    global _DEFER_COMPOSITION_REBUILD
    if _DEFER_COMPOSITION_REBUILD:
        return None
    r = _root()
    if r is None:
        return None
    restart_videos = _composition_video_restart_requested()
    _clear_composition_video_restart()
    xfade_root_stack = _xfade_root_stack_active()
    xfade_layer_col = (
        _COLUMN_XFADE.get('active')
        and _COLUMN_XFADE.get('mode') == 'layer_col'
    )
    xfade_column_layers = (
        _COLUMN_XFADE.get('active')
        and _COLUMN_XFADE.get('mode') == 'column_layers'
    )
    column_layer_fade = _column_layers_fade_map() if xfade_column_layers else {}
    fade_layer = int(_COLUMN_XFADE.get('layer', 0)) if xfade_layer_col else 0
    fade_cols = ()
    if xfade_layer_col:
        try:
            fade_cols = (
                int(_COLUMN_XFADE.get('from_col', 1)),
                int(_COLUMN_XFADE.get('to_col', 1)),
            )
        except Exception:
            fade_cols = ()

    for sl, sc in _composition_deps():
        _prep_cell_slot(sl, sc, play=global_transport_playing())

    if xfade_root_stack:
        _wire_root_column_xfade_stacks(
            play=global_transport_playing(),
            restart_videos=restart_videos,
        )
        _prime_route_slots(
            _route_prime_cols(
                xfade_column_layers=xfade_column_layers,
                column_layer_fade=column_layer_fade,
                xfade_layer_col=xfade_layer_col,
                fade_layer=fade_layer,
                fade_cols=fade_cols,
            )
        )
        chain_sel = r.op('chain_out')
        if chain_sel is not None:
            _route_composition_out()
        try:
            prog = r.op('program_sel')
            out = r.op('out1')
            if prog is not None:
                prog.cook(force=True)
            if out is not None:
                out.cook(force=True)
        except Exception:
            pass
        top = _slot(1, _get_layer_src_col(1))
        return top.op('out1') if top else None

    def _wire_layer_slot(layer, sc):
        slot = _slot(layer, sc)
        if slot is None:
            return
        _ensure_slot_chain(slot, layer)
        ctype, path = _get(layer, sc)
        if path and not _valid_clip_type(ctype):
            path = ''
        if not path:
            _route_slot_pass_only(slot)
            _wire_upstream(slot, layer)
            _pause_slot(slot, on=False, clip_type='')
            return
        slot_live = _video_slot_should_play(layer, sc)
        slot_play = global_transport_playing() and slot_live
        _pause_slot(
            slot,
            on=slot_play,
            keep_tox_cooking=_tox_cell_keep_cooking(layer, sc, ctype, path, slot_live, slot),
            clip_type=ctype,
        )
        if ctype == 'video':
            _wire_video(
                slot, path, play=slot_play,
                resume=bool(restart_videos and slot_live),
            )
            _route_slot_content(slot, 1, layer)
        else:
            _wire_tox(slot, path, layer, sc)
            _route_slot_content(slot, 2, layer)
        try:
            _wire_slot_cell_fx_chain(layer, sc, slot)
        except Exception:
            pass
        _wire_upstream(slot, layer)
        _apply_slot_canvas(slot)

    for layer in range(_num_layers(), 0, -1):
        cols = [_get_layer_src_col(layer)]
        if xfade_column_layers and int(layer) in column_layer_fade:
            fc, tc = column_layer_fade[int(layer)]
            cols = [fc, tc]
        elif xfade_layer_col and int(layer) == fade_layer:
            cols = list(fade_cols)
        seen = set()
        for sc in cols:
            sc = int(sc)
            if sc in seen:
                continue
            seen.add(sc)
            _wire_layer_slot(layer, sc)

    for layer in range(_num_layers() - 1, 0, -1):
        sc = _get_layer_src_col(layer)
        slot = _slot(layer, sc)
        if slot is None:
            continue
        ctype, path = _get(layer, sc)
        _wire_upstream(slot, layer)
        if path and ctype == 'tox':
            _wire_tox_chain_feed(slot, layer)

    for layer in range(_num_layers() - 1, 0, -1):
        sc = _get_layer_src_col(layer)
        slot = _slot(layer, sc)
        if slot is None:
            continue
        _wire_upstream(slot, layer)

    cook_cols = set(_get_layer_src_col(layer) for layer in range(1, _num_layers() + 1))
    for layer in range(1, _num_layers() + 1):
        if xfade_column_layers and int(layer) in column_layer_fade:
            continue
        if xfade_layer_col and int(layer) == int(_COLUMN_XFADE.get('layer', 0)):
            continue
        if xfade_root_stack:
            continue
        selected_col = _get_layer_src_col(layer)
        _set_layer_col(layer, selected_col)
        _restore_layer_col_switch(layer, selected_col)
    _prime_route_slots(
        _route_prime_cols(
            xfade_column_layers=xfade_column_layers,
            column_layer_fade=column_layer_fade,
            xfade_layer_col=xfade_layer_col,
            fade_layer=fade_layer,
            fade_cols=fade_cols,
        )
    )
    chain_sel = r.op('chain_out')
    if chain_sel is not None:
        _route_composition_out()
    try:
        prog = r.op('program_sel')
        out = r.op('out1')
        if prog is not None:
            prog.cook(force=True)
        if out is not None:
            out.cook(force=True)
    except Exception:
        pass
    if xfade_column_layers:
        for layer, (fc, tc) in column_layer_fade.items():
            _wire_layer_col_xfade(layer, fc, tc)
        _refresh_column_layers_routing(column_layer_fade)
    elif xfade_layer_col:
        _wire_layer_col_xfade(
            int(_COLUMN_XFADE.get('layer', 1)),
            int(_COLUMN_XFADE.get('from_col', 1)),
            int(_COLUMN_XFADE.get('to_col', 1)),
        )
        _refresh_layer_col_routing(int(_COLUMN_XFADE.get('layer', 1)))
    try:
        _ensure_layer_opacity_expr_bindings(_composition_deps())
    except Exception:
        pass
    top = _slot(1, _get_layer_src_col(1))
    return top.op('out1') if top else None


def _rebuild_column_chain(col, adopt=None):
    """Alias: set all layers to col, or rebuild current composition."""
    col = int(col)
    r = _root()
    if r is not None:
        try:
            ac = int(float(r.par.Activecolumn.eval())) or col
        except Exception:
            ac = col
        if col == ac:
            return _rebuild_composition()
    for layer in range(1, _num_layers() + 1):
        _set_layer_src_col(layer, col)
    return _rebuild_composition()


def _fade_master_enabled():
    s = _settings()
    if s is None:
        return False
    try:
        return bool(int(float(s.par.Fadeactive.eval())))
    except Exception:
        return False


def _cell_xfade_enabled():
    if not _fade_master_enabled():
        return False
    s = _settings()
    if s is None:
        return False
    try:
        return bool(int(float(s.par.Cellcrossfade.eval())))
    except Exception:
        return False


def _column_xfade_enabled():
    if not _fade_master_enabled():
        return False
    s = _settings()
    if s is None:
        return False
    try:
        return bool(int(float(s.par.Columncrossfade.eval())))
    except Exception:
        return False


def _column_xfade_duration():
    s = _settings()
    try:
        return max(0.05, float(s.par.Columncrossfadedur.eval()))
    except Exception:
        return 1.0


def _clip_xfade_enabled():
    """Legacy frame-freeze path disabled — use live signature/column fade."""
    return False


def _col_chain_expr(col):
    return _layer_out_abs_expr(1) or "op('slots/layer_1/col_{}/out1')".format(int(col))


def _ensure_column_xfade_nodes(r):
    """chain_prev + chain_next -> column_xfade for column crossfades."""
    if r is None:
        return None, None, None
    prev = r.op('chain_prev')
    nxt = r.op('chain_next')
    cross = r.op('column_xfade')
    if prev is None:
        prev = r.create('selectTOP', 'chain_prev')
    if nxt is None:
        nxt = r.create('selectTOP', 'chain_next')
    if cross is None:
        cross = r.create('crossTOP', 'column_xfade')
        try:
            prev.outputConnectors[0].connect(cross.inputConnectors[0])
            nxt.outputConnectors[0].connect(cross.inputConnectors[1])
        except Exception:
            pass
    for node in (prev, nxt, cross):
        _set_top_chain_res(node)
    return prev, nxt, cross


def _set_column_cook(col, on):
    for layer in range(1, _num_layers() + 1):
        ctype, path = _cell_content(layer, col)
        _pause_slot(
            _slot(layer, col),
            on=bool(on) and bool(path),
            keep_tox_cooking=(bool(on) and ctype == 'tox'),
            clip_type=ctype,
        )


def _keep_signature_slots_playing(sig, skip_layers_matching=None):
    if not sig or not global_transport_playing():
        return
    skip = tuple(skip_layers_matching or ())
    for layer, col in enumerate(sig, start=1):
        if skip and _sig_layer_matches(sig, skip, layer):
            continue
        slot = _slot(layer, col)
        if slot is None:
            continue
        try:
            slot.allowCooking = True
        except Exception:
            pass
        ctype, path = _get(layer, col)
        if not path:
            continue
        if ctype == 'video':
            v = slot.op('video')
            if v is not None:
                try:
                    _set_video_active(v, True)
                except Exception:
                    pass
        else:
            t = slot.op('tox')
            if t is not None:
                try:
                    t.allowCooking = True
                except Exception:
                    pass


def _keep_xfade_columns_playing():
    """Keep outgoing + incoming column movies advancing during crossfade."""
    if not _COLUMN_XFADE.get('active') or not global_transport_playing():
        return
    if _COLUMN_XFADE.get('mode') == 'layer_col':
        _keep_layer_col_xfade_playing(
            _COLUMN_XFADE.get('layer', 1),
            _COLUMN_XFADE.get('from_col', 1),
            _COLUMN_XFADE.get('to_col', 1),
        )
        return
    if _COLUMN_XFADE.get('mode') in ('clip', 'sig', 'column'):
        from_sig = tuple(_COLUMN_XFADE.get('from_sig') or ())
        to_sig = tuple(_COLUMN_XFADE.get('to_sig') or ())
        if from_sig or to_sig:
            wire_from = _column_xfade_outgoing_sig(from_sig, to_sig)
            if to_sig:
                _keep_signature_slots_playing(to_sig)
            if wire_from and wire_from != to_sig:
                _keep_signature_slots_playing(wire_from, skip_layers_matching=to_sig)
            return
    try:
        cols = (
            int(_COLUMN_XFADE.get('from_col', 1)),
            int(_COLUMN_XFADE.get('to_col', 1)),
        )
    except Exception:
        return
    for col in cols:
        for layer in range(1, _num_layers() + 1):
            slot = _slot(layer, col)
            if slot is None:
                continue
            try:
                slot.allowCooking = True
            except Exception:
                pass
            ctype, path = _get(layer, col)
            if not path:
                continue
            if ctype == 'video':
                v = slot.op('video')
                if v is None:
                    continue
                try:
                    _set_video_active(v, True)
                    v.cook(force=True)
                except Exception:
                    pass
            else:
                t = slot.op('tox')
                if t is not None:
                    try:
                        t.allowCooking = True
                    except Exception:
                        pass


def _route_chain_out(col=None):
    """Point program output at top of current composition."""
    _route_composition_out()


def _route_program_out_to(target_expr):
    r = _root()
    if r is None:
        return False
    return _set_top_expr(r.op('program_sel'), target_expr)


def _composition_signature():
    return tuple(_get_layer_src_col(layer) for layer in range(1, _num_layers() + 1))


def _ensure_clip_xfade_nodes(r):
    if r is None:
        return None, None
    hold = r.op('clip_fade_hold_select')
    cross = r.op('clip_fade')
    if hold is None:
        try:
            hold = r.create('selectTOP', 'clip_fade_hold_select')
        except Exception:
            return None, None
    if cross is None:
        try:
            cross = r.create('crossTOP', 'clip_fade')
        except Exception:
            return hold, None
    _set_top_chain_res(hold)
    _set_top_chain_res(cross)
    try:
        chain = r.op('chain_out')
        if chain is not None:
            _set_top_expr(hold, "op('chain_out')")
    except Exception:
        pass
    try:
        if hold is not None and not cross.inputConnectors[0].connections:
            hold.outputConnectors[0].connect(cross.inputConnectors[0])
        chain = r.op('chain_out')
        if chain is not None and len(cross.inputConnectors) > 1 and not cross.inputConnectors[1].connections:
            chain.outputConnectors[0].connect(cross.inputConnectors[1])
    except Exception:
        pass
    return hold, cross


def _sig_layer1_out_expr(sig):
    try:
        col = int(sig[0])
    except Exception:
        col = 1
    return "op('slots/layer_1/col_{}/out1')".format(col)


def _rebind_xfade_top_resolution(prev, nxt, cross):
    """Keep crossfade inputs locked to canvas size after expression changes."""
    for node in (prev, nxt, cross):
        _set_top_chain_res(node)


def _disconnect_top_input(top):
    if top is None:
        return
    try:
        inp = top.inputConnectors[0]
    except Exception:
        return
    try:
        for conn in list(inp.connections):
            conn.disconnect()
    except Exception:
        pass


def _ensure_layer_col_xfade(layer_comp):
    if layer_comp is None:
        return None
    try:
        cross = layer_comp.op('col_xfade') or layer_comp.create('crossTOP', 'col_xfade')
        sw_from = layer_comp.op('col_xfade_from_switch') or layer_comp.create(
            'switchTOP', 'col_xfade_from_switch'
        )
        sw_to = layer_comp.op('col_xfade_to_switch') or layer_comp.create(
            'switchTOP', 'col_xfade_to_switch'
        )
        for top in (cross, sw_from, sw_to):
            _set_top_chain_res(top)
        wiring_version = 2
        if int(cross.fetch('fixedFadeSwitchesWired', 0) or 0) != wiring_version:
            _disconnect_top_input(sw_from)
            _disconnect_top_input(sw_to)
            _disconnect_top_input(cross)
            sources = [layer_comp.op('black')] + [
                layer_comp.op('col_{}/out1'.format(c)) for c in range(1, _num_cols() + 1)
            ]
            for index, source in enumerate(sources):
                if source is None:
                    continue
                source.outputConnectors[0].connect(sw_from.inputConnectors[index])
                source.outputConnectors[0].connect(sw_to.inputConnectors[index])
            sw_from.outputConnectors[0].connect(cross.inputConnectors[0])
            sw_to.outputConnectors[0].connect(cross.inputConnectors[1])
            cross.store('fixedFadeSwitchesWired', wiring_version)
        return cross
    except Exception:
        return None


def _wire_layer_col_xfade(layer, from_col, to_col):
    """Fade by changing permanently wired Switch TOP indices only."""
    layer, from_col, to_col = int(layer), int(from_col), int(to_col)
    layer_comp = _layer(layer)
    if layer_comp is None:
        return False
    cross = _ensure_layer_col_xfade(layer_comp)
    out = layer_comp.op('out1')
    sw_from = layer_comp.op('col_xfade_from_switch')
    sw_to = layer_comp.op('col_xfade_to_switch')
    if cross is None or out is None or sw_from is None or sw_to is None:
        return False
    try:
        sw_from.par.index = from_col
        sw_to.par.index = to_col
        if len(out.inputs) < 1 or out.inputs[0] != cross:
            _disconnect_top_input(out)
            cross.outputConnectors[0].connect(out.inputConnectors[0])
    except Exception:
        return False
    return True


def _restore_layer_col_switch(layer, to_col):
    layer, to_col = int(layer), int(to_col)
    layer_comp = _layer(layer)
    if layer_comp is None:
        return
    cross = _ensure_layer_col_xfade(layer_comp)
    out = layer_comp.op('out1')
    sw_from = layer_comp.op('col_xfade_from_switch')
    sw_to = layer_comp.op('col_xfade_to_switch')
    if cross is not None and out is not None and sw_from is not None and sw_to is not None:
        try:
            sw_from.par.index = to_col
            sw_to.par.index = to_col
            cross.par.cross = 0.0
            if len(out.inputs) < 1 or out.inputs[0] != cross:
                _disconnect_top_input(out)
                cross.outputConnectors[0].connect(out.inputConnectors[0])
            return
        except Exception:
            pass


def _keep_layer_col_xfade_playing(layer, from_col, to_col):
    if not global_transport_playing():
        return
    layer = int(layer)
    for col in (int(from_col), int(to_col)):
        _prep_cell_slot(layer, col, play=True)
        slot = _slot(layer, col)
        if slot is None:
            continue
        ctype, path = _get(layer, col)
        if not path:
            continue
        if ctype == 'video':
            v = slot.op('video')
            if v is not None:
                try:
                    _set_video_active(v, True)
                    v.cook(force=True)
                except Exception:
                    pass


def _prime_layer_cell_before_switch(layer, col, frames=0):
    """Wake an incoming row/cell off-air without blocking the switch callback."""
    layer, col = int(layer), int(col)
    try:
        _prep_cell_slot(
            layer,
            col,
            play=True,
            restart_video=False,
        )
    except Exception:
        pass
    slot = _slot(layer, col)
    if slot is None:
        return
    if int(frames) <= 0:
        return
    for _ in range(int(frames)):
        for name in ('tox', 'tox_fit', 'tox_pick', 'video', 'video_fit', 'pick', 'out1'):
            node = slot.op(name)
            if node is None:
                continue
            try:
                node.cook(force=True)
            except Exception:
                pass


def _wake_cell_media_for_pending_xfade(layer, col):
    """Load/cook target media without changing slot routing or upstream chain."""
    layer, col = int(layer), int(col)
    slot = _slot(layer, col)
    if slot is None:
        return
    _ensure_slot_chain(slot, layer)
    ctype, path = _get(layer, col)
    if not path or not _valid_clip_type(ctype):
        return
    try:
        _pause_slot(
            slot,
            on=True,
            keep_tox_cooking=(ctype == 'tox'),
            clip_type=ctype,
        )
    except Exception:
        pass
    if ctype == 'video':
        try:
            _wire_video(slot, path, play=True, resume=False)
        except Exception:
            pass
        return
    if ctype == 'tox':
        try:
            _wire_tox(slot, path)
        except Exception:
            pass


def _cell_slot_ready_for_xfade(layer, col):
    layer, col = int(layer), int(col)
    slot = _slot(layer, col)
    if slot is None:
        return False
    ctype, path = _get(layer, col)
    if not path or not _valid_clip_type(ctype):
        return True
    try:
        if ctype == 'tox':
            t = slot.op('tox')
            if t is None:
                return False
            if _slot_tox_path(slot) != _norm_asset_path(path):
                return False
            out = slot.op('tox_pick') or slot.op('tox_fit') or t
        elif ctype == 'video':
            out = slot.op('video_fit') or slot.op('video')
        else:
            out = slot.op('out1') or slot.op('pick')
        if out is None:
            return False
        w = int(getattr(out, 'width', 0) or 0)
        h = int(getattr(out, 'height', 0) or 0)
        return w > 1 and h > 1
    except Exception:
        return False


def _schedule_layer_cell_xfade_when_ready(layer, from_col, to_col, apply_change, min_attempts=6, max_attempts=30):
    """Keep current program routed until the requested cell has a cooked output."""
    r = _root()
    layer, from_col, to_col = int(layer), int(from_col), int(to_col)
    _PENDING_CELL_XFADE['token'] = int(_PENDING_CELL_XFADE.get('token', 0)) + 1
    token = int(_PENDING_CELL_XFADE['token'])
    if not _cell_slot_ready_for_xfade(layer, to_col):
        _wake_cell_media_for_pending_xfade(layer, to_col)

    def _try_start(attempt=0):
        if token != int(_PENDING_CELL_XFADE.get('token', 0)):
            cell_change_log('trigger_cell.pending_cancelled', 'L{} C{}'.format(layer, to_col))
            return
        ready = _cell_slot_ready_for_xfade(layer, to_col)
        warmed = int(attempt) >= int(min_attempts)
        if (ready and warmed) or int(attempt) >= int(max_attempts):
            cell_change_log(
                'trigger_cell.begin_xfade',
                'ready={} warmed={} attempts={}'.format(bool(ready), bool(warmed), int(attempt)),
            )
            _begin_layer_col_xfade(layer, from_col, to_col, apply_change)
            try:
                _stabilize_logo_overlay_tox_instances(r)
                cell_change_log('trigger_cell.logo_stabilized_after_col_change')
            except Exception as exc:
                cell_change_log('trigger_cell.logo_stabilized_after_col_change.error', exc=exc)
            return
        if not ready:
            _wake_cell_media_for_pending_xfade(layer, to_col)
        if not _defer_run(lambda: _try_start(int(attempt) + 1), delayFrames=2, fromOP=r):
            _try_start(int(attempt) + 1)

    if not _defer_run(lambda: _try_start(0), delayFrames=2, fromOP=r):
        _try_start(0)


def _column_slots_ready_for_xfade(col):
    col = int(col)
    for layer in range(1, _num_layers() + 1):
        if not _cell_slot_ready_for_xfade(layer, col):
            return False
    return True


def _wake_column_media_for_pending_xfade(col):
    col = int(col)
    for layer in range(_num_layers(), 0, -1):
        _wake_cell_media_for_pending_xfade(layer, col)


def _schedule_column_xfade_when_ready(col, from_col, apply_change, min_attempts=6, max_attempts=30):
    """Keep current program routed until every target-column cell has a cooked output."""
    r = _root()
    col, from_col = int(col), int(from_col)
    _PENDING_COLUMN_XFADE['token'] = int(_PENDING_COLUMN_XFADE.get('token', 0)) + 1
    token = int(_PENDING_COLUMN_XFADE['token'])
    if not _column_slots_ready_for_xfade(col):
        _wake_column_media_for_pending_xfade(col)

    def _try_start(attempt=0):
        if token != int(_PENDING_COLUMN_XFADE.get('token', 0)):
            cell_change_log('trigger_column.pending_cancelled', 'C{}'.format(col))
            return
        ready = _column_slots_ready_for_xfade(col)
        warmed = int(attempt) >= int(min_attempts)
        if (ready and warmed) or int(attempt) >= int(max_attempts):
            cell_change_log(
                'trigger_column.begin_xfade',
                'ready={} warmed={} attempts={}'.format(bool(ready), bool(warmed), int(attempt)),
            )
            _begin_composition_xfade(apply_change)
            return
        if not ready:
            _wake_column_media_for_pending_xfade(col)
        if not _defer_run(lambda: _try_start(int(attempt) + 1), delayFrames=2, fromOP=r):
            _try_start(int(attempt) + 1)

    cell_change_log('trigger_column.pending_xfade', 'from={} to={}'.format(from_col, col))
    if not _defer_run(lambda: _try_start(0), delayFrames=2, fromOP=r):
        _try_start(0)


def _begin_layer_col_xfade(layer, from_col, to_col, apply_change):
    """Fade one layer row while cooking only its outgoing and incoming cells."""
    r = _root()
    if not _cell_xfade_enabled():
        apply_change()
        return False
    layer = int(layer)
    from_col = int(from_col)
    to_col = int(to_col)
    if from_col == to_col:
        apply_change()
        return False
    if not _wire_layer_col_xfade(layer, from_col, to_col):
        apply_change()
        return False
    try:
        cross = _layer(layer).op('col_xfade')
        if cross is not None:
            cross.par.cross = 0.0
    except Exception:
        pass
    _COLUMN_XFADE['active'] = True
    _COLUMN_XFADE['mode'] = 'layer_col'
    _COLUMN_XFADE['layer'] = layer
    _COLUMN_XFADE['from_col'] = from_col
    _COLUMN_XFADE['to_col'] = to_col
    _COLUMN_XFADE['from_sig'] = ()
    _COLUMN_XFADE['to_sig'] = ()
    _COLUMN_XFADE['t0'] = _now_seconds()
    _COLUMN_XFADE['dur'] = _column_xfade_duration()
    try:
        _stabilize_logo_overlay_tox_instances(r)
    except Exception:
        pass
    apply_change()
    _rebuild_composition()
    try:
        _stabilize_logo_overlay_tox_instances(r)
    except Exception:
        pass
    _route_program_out_to(_program_out_expr())
    _sync_layer_slot_pause_states(force_full=True)
    _sync_program_preview()
    return True


def _prep_signature_media(sig, skip_layers_matching=None, restart_videos=False):
    """Load/play every cell in a composition signature (outgoing + incoming clips)."""
    if not sig:
        return
    skip = tuple(skip_layers_matching or ())
    for layer, col in enumerate(sig, start=1):
        if skip and _sig_layer_matches(sig, skip, layer):
            continue
        try:
            _prep_cell_slot(
                layer, int(col),
                play=global_transport_playing(),
                restart_video=restart_videos,
            )
        except Exception:
            pass


def _wire_signature_stack(sig, play=True, skip_layers_matching=None, restart_videos=False):
    """Wire each layer's stack for sig without changing the composition table."""
    if not sig:
        return
    skip = tuple(skip_layers_matching or ())
    for layer in range(_num_layers(), 0, -1):
        if skip and _sig_layer_matches(sig, skip, layer):
            continue
        try:
            col = int(sig[layer - 1])
        except Exception:
            continue
        slot = _slot(layer, col)
        if slot is None:
            continue
        _ensure_slot_chain(slot, layer)
        ctype, path = _get(layer, col)
        if not path or not _valid_clip_type(ctype):
            _route_slot_pass_only(slot)
            _wire_upstream_for_sig(slot, layer, sig)
            _pause_slot(slot, on=False, clip_type='')
            continue
        slot_live = bool(play) and _video_slot_should_play(layer, col)
        should_play = slot_live and global_transport_playing()
        _pause_slot(
            slot,
            on=should_play,
            keep_tox_cooking=_tox_cell_keep_cooking(layer, col, ctype, path, slot_live, slot),
            clip_type=ctype,
        )
        if ctype == 'video':
            _wire_video(
                slot, path, play=should_play,
                resume=bool(restart_videos and slot_live),
            )
            _route_slot_content(slot, 1, layer)
        else:
            _wire_tox(slot, path, layer, col)
            _route_slot_content(slot, 2, layer)
        _wire_upstream_for_sig(slot, layer, sig)
        _apply_slot_canvas(slot)
    for layer in range(_num_layers() - 1, 0, -1):
        if skip and _sig_layer_matches(sig, skip, layer):
            continue
        try:
            col = int(sig[layer - 1])
        except Exception:
            continue
        slot = _slot(layer, col)
        if slot is None:
            continue
        ctype, path = _get(layer, col)
        _wire_upstream_for_sig(slot, layer, sig)
        if path and ctype == 'tox':
            _wire_tox_chain_feed(slot, layer)
            _apply_slot_canvas(slot)


def _mark_root_column_xfade_started():
    _COLUMN_XFADE['stacks_wired'] = False
    _COLUMN_XFADE['keep_tick'] = 0


def _keep_column_layers_playing():
    if not global_transport_playing():
        return
    for layer, (fc, tc) in _column_layers_fade_map().items():
        _keep_layer_col_xfade_playing(layer, fc, tc)


def _begin_column_layers_xfade(from_sig, apply_change):
    """Per-row col_xfade (same path as cell crossfade) when Fade Video is on."""
    global _DEFER_COMPOSITION_REBUILD
    r = _root()
    if r is None or not _column_xfade_enabled():
        apply_change()
        return False
    from_sig = tuple(from_sig or ())
    if not from_sig:
        apply_change()
        return False
    # Update composition table only — avoid one frame of the incoming column
    # before col_xfade is armed at cross=0 (same order as cell/layer_col fade).
    _DEFER_COMPOSITION_REBUILD = True
    try:
        apply_change()
    finally:
        _DEFER_COMPOSITION_REBUILD = False
    to_sig = tuple(_composition_signature())
    if from_sig == to_sig:
        _rebuild_composition()
        return False
    fade_map = _sig_fade_map(from_sig, to_sig)
    if not fade_map:
        _rebuild_composition()
        return False
    for layer, (fc, tc) in fade_map.items():
        if not _wire_layer_col_xfade(layer, fc, tc):
            _rebuild_composition()
            return False
        try:
            cross = _layer(layer).op('col_xfade')
            if cross is not None:
                cross.par.cross = 0.0
                cross.cook(force=True)
        except Exception:
            pass
    _mark_root_column_xfade_started()
    _COLUMN_XFADE['active'] = True
    _COLUMN_XFADE['mode'] = 'column_layers'
    _COLUMN_XFADE['from_sig'] = from_sig
    _COLUMN_XFADE['to_sig'] = to_sig
    _COLUMN_XFADE['from_col'] = from_sig[0] if from_sig else 1
    _COLUMN_XFADE['to_col'] = to_sig[0] if to_sig else 1
    _COLUMN_XFADE['t0'] = _now_seconds()
    _COLUMN_XFADE['dur'] = _column_xfade_duration()
    _rebuild_composition()
    _route_program_out_to(_program_out_expr())
    _sync_layer_slot_pause_states(force_full=True)
    _sync_program_preview()
    try:
        r.cook(force=True)
    except Exception:
        pass
    return True


def _begin_signature_xfade(apply_change, from_sig=None):
    """Live crossfade between two compositions; both clips keep playing."""
    r = _root()
    if r is None or not _column_xfade_enabled():
        apply_change()
        return False
    from_sig = tuple(from_sig or _composition_signature())
    if _column_xfade_video_enabled():
        return _begin_column_layers_xfade(from_sig, apply_change)
    prev, nxt, cross = _ensure_column_xfade_nodes(r)
    chain = r.op('chain_out')
    if prev is None or nxt is None or cross is None or chain is None:
        apply_change()
        return False
    try:
        if _COLUMN_XFADE.get('active'):
            _COLUMN_XFADE['active'] = False
        _mark_root_column_xfade_started()
        _COLUMN_XFADE['active'] = True
        _COLUMN_XFADE['mode'] = 'sig'
        _COLUMN_XFADE['from_sig'] = from_sig
        _COLUMN_XFADE['to_sig'] = ()
        _COLUMN_XFADE['from_col'] = from_sig[0] if from_sig else 1
        _COLUMN_XFADE['to_col'] = from_sig[0] if from_sig else 1
        _set_top_expr(prev, _sig_layer1_out_expr(from_sig))
        _set_top_expr(nxt, _sig_layer1_out_expr(from_sig))
        _rebind_xfade_top_resolution(prev, nxt, cross)
        cross.par.cross = 0.0
        cross.cook(force=True)
        if not _set_top_expr(chain, "op('column_xfade')"):
            _COLUMN_XFADE['active'] = False
            apply_change()
            return False
        if not _route_program_out_to("op('column_xfade')"):
            _COLUMN_XFADE['active'] = False
            apply_change()
            return False
    except Exception:
        _COLUMN_XFADE['active'] = False
        apply_change()
        return False
    apply_change()
    to_sig = tuple(_composition_signature())
    try:
        _COLUMN_XFADE['to_sig'] = to_sig
        _COLUMN_XFADE['to_col'] = to_sig[0] if to_sig else _COLUMN_XFADE['from_col']
        _COLUMN_XFADE['t0'] = _now_seconds()
        _COLUMN_XFADE['dur'] = _column_xfade_duration()
        _wire_root_column_xfade_stacks(play=True, force=True)
        _sync_layer_slot_pause_states(force_full=True)
        return True
    except Exception:
        _COLUMN_XFADE['active'] = False
        _route_program_out_to(_program_out_expr())
        return False


def _begin_clip_xfade(apply_change):
    return _begin_signature_xfade(apply_change)


def _begin_composition_xfade(apply_change):
    """Crossfade any composition change, including row/layer changes."""
    r = _root()
    if r is None or not _column_xfade_enabled():
        apply_change()
        return False
    prev_sig = _composition_signature()
    if prev_sig and len(set(prev_sig)) == 1:
        return _begin_column_layers_xfade(prev_sig, apply_change)
    if not prev_sig or len(set(prev_sig)) != 1:
        return _begin_signature_xfade(apply_change, prev_sig)
    prev, nxt, cross = _ensure_column_xfade_nodes(r)
    chain = r.op('chain_out')
    if prev is None or nxt is None or cross is None or chain is None:
        apply_change()
        return False
    try:
        if _COLUMN_XFADE.get('active'):
            _COLUMN_XFADE['active'] = False
        _set_top_expr(prev, _col_chain_expr(prev_sig[0]))
        _set_top_expr(nxt, _col_chain_expr(prev_sig[0]))
        cross.par.cross = 0.0
        cross.cook(force=True)
        if not _set_top_expr(chain, "op('column_xfade')"):
            _route_composition_out()
            apply_change()
            return False
        # Mark active before rebuilding so _route_composition_out() will not
        # briefly expose the new composition for one frame.
        _mark_root_column_xfade_started()
        _COLUMN_XFADE['active'] = True
        _COLUMN_XFADE['from_col'] = prev_sig[0] if prev_sig else 1
        _COLUMN_XFADE['to_col'] = prev_sig[0] if prev_sig else 1
        _COLUMN_XFADE['from_sig'] = prev_sig
        _COLUMN_XFADE['to_sig'] = ()
    except Exception:
        apply_change()
        return False
    apply_change()
    new_sig = _composition_signature()
    if new_sig == prev_sig:
        _COLUMN_XFADE['active'] = False
        _route_composition_out()
        return False
    if not new_sig or len(set(new_sig)) != 1:
        _COLUMN_XFADE['active'] = False
        _route_composition_out()
        return False
    try:
        _COLUMN_XFADE['from_col'] = prev_sig[0] if prev_sig else 1
        _COLUMN_XFADE['to_col'] = new_sig[0] if new_sig else 1
        _COLUMN_XFADE['from_sig'] = prev_sig
        _COLUMN_XFADE['to_sig'] = new_sig
        _COLUMN_XFADE['t0'] = _now_seconds()
        _COLUMN_XFADE['dur'] = _column_xfade_duration()
        _wire_root_column_xfade_stacks(play=True, force=True)
        _sync_layer_slot_pause_states(force_full=True)
        return True
    except Exception:
        _route_composition_out()
        return False


def _tick_column_xfade():
    if not _COLUMN_XFADE.get('active'):
        return
    r = _root()
    mode = _COLUMN_XFADE.get('mode', 'column')
    if mode == 'layer_col':
        layer = int(_COLUMN_XFADE.get('layer', 1))
        from_col = int(_COLUMN_XFADE.get('from_col', 1))
        to_col = int(_COLUMN_XFADE.get('to_col', 1))
        layer_comp = _layer(layer)
        cross = layer_comp.op('col_xfade') if layer_comp else None
        if cross is None:
            _finish_column_xfade(to_col, from_col)
            return
        dur = max(0.05, float(_COLUMN_XFADE.get('dur', 1.0)))
        try:
            t = (_now_seconds() - float(_COLUMN_XFADE.get('t0', 0.0))) / dur
        except Exception:
            t = 1.0
        if t >= 1.0:
            _finish_column_xfade(to_col, from_col)
            return
        try:
            cross.par.cross = t
        except Exception:
            pass
        return
    if mode == 'column_layers':
        dur = max(0.05, float(_COLUMN_XFADE.get('dur', 1.0)))
        try:
            t = (_now_seconds() - float(_COLUMN_XFADE.get('t0', 0.0))) / dur
        except Exception:
            t = 1.0
        if t >= 1.0:
            _finish_column_xfade(
                _COLUMN_XFADE.get('to_col', 1),
                _COLUMN_XFADE.get('from_col', 1),
            )
            return
        for layer, (fc, tc) in _column_layers_fade_map().items():
            layer_comp = _layer(layer)
            cross = layer_comp.op('col_xfade') if layer_comp else None
            if cross is None:
                continue
            try:
                cross.par.cross = t
            except Exception:
                pass
        keep_tick = int(_COLUMN_XFADE.get('keep_tick', 0)) + 1
        _COLUMN_XFADE['keep_tick'] = keep_tick
        if keep_tick % 30 == 0:
            _keep_column_layers_playing()
        return
    keep_tick = int(_COLUMN_XFADE.get('keep_tick', 0)) + 1
    _COLUMN_XFADE['keep_tick'] = keep_tick
    if keep_tick % 30 == 0:
        _keep_xfade_columns_playing()
    cross = r.op('column_xfade') if r else None
    if cross is None:
        _COLUMN_XFADE['active'] = False
        return
    dur = max(0.05, float(_COLUMN_XFADE.get('dur', 1.0)))
    try:
        t = (_now_seconds() - float(_COLUMN_XFADE.get('t0', 0.0))) / dur
    except Exception:
        t = 1.0
    if t >= 1.0:
        _finish_column_xfade(_COLUMN_XFADE.get('to_col', 1), _COLUMN_XFADE.get('from_col', 1))
        return
    try:
        cross.par.cross = t
    except Exception:
        pass


def _finish_column_xfade(to_col, from_col):
    mode = _COLUMN_XFADE.get('mode', 'column')
    _COLUMN_XFADE['active'] = False
    _COLUMN_XFADE['stacks_wired'] = False
    _COLUMN_XFADE['keep_tick'] = 0
    if mode == 'layer_col':
        layer = int(_COLUMN_XFADE.get('layer', 1))
        from_col = int(_COLUMN_XFADE.get('from_col', from_col))
        to_col = int(_COLUMN_XFADE.get('to_col', to_col))
        _restore_layer_col_switch(layer, to_col)
        _set_layer_col(layer, to_col)
        _rebuild_composition()
        _route_composition_out()
        _route_program_out_to(_program_out_expr())
        _sync_layer_slot_pause_states(force_full=True)
        _sync_program_preview()
        if from_col != to_col:
            _refresh_cell_selection_display(layer, from_col)
            _schedule_cell_preview_refresh(layer, from_col, delay_frames=12, force_video_prime=False)
        _refresh_cell_selection_display(layer, to_col)
        _schedule_cell_preview_refresh(layer, to_col, delay_frames=12, force_video_prime=False)
        return
    if mode == 'column_layers':
        to_sig = tuple(_COLUMN_XFADE.get('to_sig') or ())
        from_sig = tuple(_COLUMN_XFADE.get('from_sig') or ())
        for layer in range(1, min(len(from_sig), len(to_sig)) + 1):
            tc = int(to_sig[layer - 1])
            fc = int(from_sig[layer - 1])
            if fc != tc:
                _restore_layer_col_switch(layer, tc)
            _set_layer_col(layer, tc)
        _rebuild_composition()
        _route_composition_out()
        _route_program_out_to(_program_out_expr())
        _sync_layer_slot_pause_states(force_full=True)
        _sync_program_preview()
        return
    if mode == 'clip':
        r = _root()
        cross = r.op('clip_fade') if r else None
        if cross is not None:
            try:
                cross.par.cross = 1.0
            except Exception:
                pass
        try:
            hold = r.op('clip_fade_hold_select') if r else None
            if hold is not None:
                try:
                    hold.lock = False
                except Exception:
                    pass
                hold.allowCooking = True
        except Exception:
            pass
        _route_program_out_to(_program_out_expr())
        try:
            if r is not None:
                r.cook(force=True)
        except Exception:
            pass
        return
    to_col = int(to_col)
    from_col = int(from_col)
    r = _root()
    cross = r.op('column_xfade') if r else None
    if cross is not None:
        try:
            cross.par.cross = 1.0
        except Exception:
            pass
    if from_col != to_col:
        _set_column_cook(from_col, False)
    to_sig = _COLUMN_XFADE.get('to_sig')
    if to_sig:
        for layer, layer_col in enumerate(to_sig, start=1):
            _set_layer_src_col(layer, layer_col)
    else:
        for layer in range(1, _num_layers() + 1):
            _set_layer_src_col(layer, to_col)
    for layer in range(_num_layers(), 0, -1):
        _set_layer_col(layer, _get_layer_src_col(layer))
    _route_composition_out()
    _route_program_out_to(_program_out_expr())
    try:
        prog = r.op('program_sel')
        out = r.op('out1')
        if prog is not None:
            prog.cook(force=True)
        if out is not None:
            out.cook(force=True)
    except Exception:
        pass


def _prep_column_media(col):
    """Load/play a column chain for fade preview without changing live composition."""
    col = int(col)
    for layer in range(1, _num_layers() + 1):
        ctype, path = _get(layer, col)
        slot = _slot(layer, col)
        if slot is None:
            continue
        _ensure_slot_chain(slot, layer)
        if not path:
            _route_slot_pass_only(slot)
            _wire_upstream(slot, layer, src_layer=layer + 1, src_col=col)
            continue
        if ctype == 'video':
            _wire_video(slot, path, play=global_transport_playing())
            _route_slot_content(slot, 1, layer)
        else:
            _wire_tox(slot, path, layer, col)
            _route_slot_content(slot, 2, layer)
        _wire_upstream(slot, layer, src_layer=layer + 1, src_col=col)
    for layer in range(_num_layers() - 1, 0, -1):
        slot = _slot(layer, col)
        if slot is not None:
            _wire_upstream(slot, layer, src_layer=layer + 1, src_col=col)


def _begin_column_xfade(from_col, to_col):
    r = _root()
    if r is None:
        return
    from_col = int(from_col)
    to_col = int(to_col)
    if from_col == to_col:
        return
    prev, nxt, cross = _ensure_column_xfade_nodes(r)
    if cross is None:
        return
    _COLUMN_XFADE['active'] = True
    _COLUMN_XFADE['from_col'] = from_col
    _COLUMN_XFADE['to_col'] = to_col
    _prep_column_media(to_col)
    _prep_column_media(from_col)
    _set_column_cook(from_col, True)
    _set_column_cook(to_col, True)
    if not _set_top_expr(prev, _col_chain_expr(from_col)):
        return
    if not _set_top_expr(nxt, _col_chain_expr(to_col)):
        return
    chain = r.op('chain_out')
    if chain is None or not _set_top_expr(chain, "op('column_xfade')"):
        return
    try:
        cross.par.cross = 0.0
        cross.cook(force=True)
    except Exception:
        pass
    _COLUMN_XFADE['t0'] = _now_seconds()
    _COLUMN_XFADE['dur'] = _column_xfade_duration()
    _keep_xfade_columns_playing()
    try:
        r.cook(force=True)
    except Exception:
        pass


def _xfade_play_cols_for_layer(layer, active_col):
    play_cols = {int(active_col)}
    if not _COLUMN_XFADE.get('active'):
        return play_cols
    mode = _COLUMN_XFADE.get('mode', 'column')
    if mode == 'layer_col':
        if int(layer) == int(_COLUMN_XFADE.get('layer', 0)):
            try:
                play_cols.add(int(_COLUMN_XFADE.get('from_col', active_col)))
                play_cols.add(int(_COLUMN_XFADE.get('to_col', active_col)))
            except Exception:
                pass
        return play_cols
    if mode == 'column_layers':
        fade_cols = _column_layers_fade_cols(layer)
        if fade_cols is not None:
            play_cols.add(int(fade_cols[0]))
            play_cols.add(int(fade_cols[1]))
        return play_cols
    if mode in ('clip', 'sig', 'column'):
        cut_cols = _xfade_video_cut_play_cols(layer)
        if cut_cols is not None:
            return cut_cols
        used_sig = False
        for sig_name in ('from_sig', 'to_sig'):
            sig = _COLUMN_XFADE.get(sig_name) or ()
            if len(sig) >= layer:
                try:
                    play_cols.add(int(sig[layer - 1]))
                    used_sig = True
                except Exception:
                    pass
        if used_sig:
            return play_cols
        if mode in ('clip', 'sig'):
            return play_cols
    try:
        play_cols.add(int(_COLUMN_XFADE.get('from_col', active_col)))
        play_cols.add(int(_COLUMN_XFADE.get('to_col', active_col)))
    except Exception:
        pass
    return play_cols


def _set_layer_col(layer, col):
    global _LAST_LIVE_SLOT_COLS
    layer = int(layer)
    col = int(col)
    layer_comp = _layer(layer)
    if layer_comp is None:
        return
    sw = layer_comp.op('switch')
    if sw is not None:
        sw.par.index = col
    play_cols = _xfade_play_cols_for_layer(layer, col)
    if layer in _LAST_LIVE_SLOT_COLS:
        prev_cols = set(_LAST_LIVE_SLOT_COLS.get(layer, set()))
    else:
        prev_cols = set(range(1, _num_cols() + 1))
    update_cols = prev_cols | set(play_cols)
    for c in sorted(update_cols):
        if c < 1 or c > _num_cols():
            continue
        slot = layer_comp.op('col_{}'.format(c))
        ctype, path = _cell_content(layer, c)
        live = c in play_cols
        playing = global_transport_playing() and live and bool(path)
        _pause_slot(
            slot,
            on=playing,
            keep_tox_cooking=_tox_cell_keep_cooking(layer, c, ctype, path, live, slot),
            clip_type=ctype,
        )
    _LAST_LIVE_SLOT_COLS[layer] = set(play_cols)


def trigger_cell(layer, col):
    """Select one layer row to use this column cell (rest of composition unchanged)."""
    r = _root()
    if r is None:
        return
    layer, col = int(layer), int(col)
    cell_change_log('trigger_cell.start', 'L{} C{}'.format(layer, col))
    try:
        prev_selected_layer = int(float(r.par.Selectedlayer.eval()))
        prev_selected_col = int(float(r.par.Selectedcol.eval()))
    except Exception:
        prev_selected_layer = prev_selected_col = None
    cell_change_log('trigger_cell.prev', 'L{} C{}'.format(prev_selected_layer, prev_selected_col))
    from_col = _get_layer_src_col(layer)
    cell_change_log('trigger_cell.from_col', 'from={} target={}'.format(from_col, col))
    try:
        r.par.Activelayer = layer
        r.par.Selectedlayer = layer
        r.par.Selectedcol = col
        cell_change_log('trigger_cell.selection_set')
    except Exception as exc:
        cell_change_log('trigger_cell.selection_set.error', exc=exc)

    try:
        param_focus_mode = _cell_param_focus_mode()
        light_param_focus = param_focus_mode in ('off', 'double', 'delayed')
    except Exception:
        param_focus_mode = 'immediate'
        light_param_focus = False

    def _refresh_selected_cell_ui():
        if light_param_focus:
            cell_change_log('trigger_cell.ui_deferred.skip_light')
            return
        cell_change_log('trigger_cell.ui_deferred.start', 'L{} C{}'.format(layer, col))
        try:
            try:
                set_params_tab('layer')
                cell_change_log('trigger_cell.params_tab')
            except Exception as exc:
                cell_change_log('trigger_cell.params_tab.error', exc=exc)
            try:
                sync_map_control_context(r)
                cell_change_log('trigger_cell.map_ctx')
            except Exception as exc:
                cell_change_log('trigger_cell.map_ctx.error', exc=exc)
            _update_cell_params_ui(layer, col)
            try:
                _stabilize_logo_overlay_tox_instances(r)
                cell_change_log('trigger_cell.ui_logo_stabilized')
            except Exception as exc:
                cell_change_log('trigger_cell.ui_logo_stabilized.error', exc=exc)
            cell_change_log('trigger_cell.ui_deferred.done')
        except Exception as exc:
            cell_change_log('trigger_cell.ui_deferred.error', exc=exc)

    def _schedule_selected_cell_ui(delay=12):
        try:
            if not _defer_run(_refresh_selected_cell_ui, delayFrames=delay, fromOP=r):
                _refresh_selected_cell_ui()
            else:
                cell_change_log('trigger_cell.ui_scheduled')
        except Exception as exc:
            cell_change_log('trigger_cell.ui_schedule.error', exc=exc)
            _refresh_selected_cell_ui()

    def _apply_fade():
        cell_change_log('trigger_cell.xfade_apply')
        _set_layer_src_col(layer, col)
        # Pending fades apply after the click-time UI refresh. Repaint both
        # cells now that the live composition has actually moved.
        _refresh_cell_selection_display(layer, from_col)
        _refresh_cell_selection_display(layer, col)

    def _apply_direct():
        cell_change_log('trigger_cell.direct_apply')
        _set_layer_src_col(layer, col)
        _rebuild_composition()

    if from_col != col:
        if _cell_xfade_enabled() and _xfade_allowed():
            _target_type, target_path = _get(layer, col)
            if str(target_path or '').strip():
                cell_change_log('trigger_cell.pending_xfade', 'L{} C{}'.format(layer, col))
                _schedule_layer_cell_xfade_when_ready(layer, from_col, col, _apply_fade)
            else:
                cell_change_log('trigger_cell.empty_xfade', 'L{} C{}'.format(layer, col))
                _begin_layer_col_xfade(layer, from_col, col, _apply_fade)
        else:
            if _COLUMN_XFADE.get('active'):
                try:
                    _finish_column_xfade(
                        int(_COLUMN_XFADE.get('to_col', from_col)),
                        int(_COLUMN_XFADE.get('from_col', from_col)),
                    )
                except Exception:
                    pass
            _apply_direct()
            if not light_param_focus:
                try:
                    _stabilize_logo_overlay_tox_instances(r)
                    cell_change_log('trigger_cell.logo_stabilized_after_col_change')
                except Exception as exc:
                    cell_change_log('trigger_cell.logo_stabilized_after_col_change.error', exc=exc)
    else:
        cell_change_log('trigger_cell.same_col')
        if not light_param_focus:
            try:
                _stabilize_logo_overlay_tox_instances(r)
                cell_change_log('trigger_cell.logo_stabilized')
            except Exception as exc:
                cell_change_log('trigger_cell.logo_stabilized.error', exc=exc)

    if not light_param_focus:
        _schedule_selected_cell_ui(delay=12)
    elif param_focus_mode == 'delayed':
        try:
            _schedule_cell_params_ui(layer, col, delay_frames=18)
        except Exception:
            pass
    if from_col == col:
        if not light_param_focus:
            def _stabilize_logo_later():
                try:
                    _stabilize_logo_overlay_tox_instances(r)
                    cell_change_log('trigger_cell.logo_stabilized_later')
                except Exception as exc:
                    cell_change_log('trigger_cell.logo_stabilized_later.error', exc=exc)

            for _delay in (1, 2, 4):
                try:
                    _defer_run(_stabilize_logo_later, delayFrames=_delay, fromOP=r)
                except Exception:
                    pass
        if prev_selected_layer == layer and prev_selected_col == col:
            cell_change_log('trigger_cell.noop')
            return
        cell_change_log('trigger_cell.done_same_col')
        return
    if from_col != col:
        cell_change_log('trigger_cell.refresh_from', 'L{} C{}'.format(layer, from_col))
        _refresh_cell_selection_display(layer, from_col)
        if not light_param_focus:
            _schedule_cell_preview_refresh(layer, from_col, delay_frames=12, force_video_prime=False)
    cell_change_log('trigger_cell.refresh_to', 'L{} C{}'.format(layer, col))
    _refresh_cell_selection_display(layer, col)
    if not light_param_focus:
        _schedule_cell_preview_refresh(layer, col, delay_frames=12, force_video_prime=False)
        cell_change_log('trigger_cell.open_output')
        _open_output()
    cell_change_log('trigger_cell.done')


def trigger_column(col):
    r = _root()
    if r is None:
        return
    col = int(col)
    prev_col = int(_get_layer_src_col(1))
    if _COLUMN_XFADE.get('active'):
        prev_col = int(_COLUMN_XFADE.get('to_col', prev_col))
        _finish_column_xfade(prev_col, _COLUMN_XFADE.get('from_col', prev_col))
    composition_select_column(col, previous_col=prev_col)
    try:
        layer = int(float(r.par.Selectedlayer.eval()))
    except Exception:
        layer = _base_layer()
    _update_cell_params_ui(layer, col)
    return col
