def _layer_col_xfade_layer():
    """Layer row currently crossfading between two column cells."""
    if not _COLUMN_XFADE.get('active') or _COLUMN_XFADE.get('mode') != 'layer_col':
        return 0
    try:
        return int(_COLUMN_XFADE.get('layer', 0))
    except Exception:
        return 0


def _layer_col_xfade_active_layers():
    """Layer rows using per-cell col_xfade (single cell or full column with video)."""
    if not _COLUMN_XFADE.get('active'):
        return set()
    mode = _COLUMN_XFADE.get('mode')
    if mode == 'layer_col':
        layer = _layer_col_xfade_layer()
        return {layer} if layer > 0 else set()
    if mode == 'column_layers':
        from_sig = tuple(_COLUMN_XFADE.get('from_sig') or ())
        to_sig = tuple(_COLUMN_XFADE.get('to_sig') or ())
        layers = set()
        for layer in range(1, min(len(from_sig), len(to_sig)) + 1):
            try:
                if int(from_sig[layer - 1]) != int(to_sig[layer - 1]):
                    layers.add(int(layer))
            except Exception:
                pass
        return layers
    return set()


def _layer_out_abs_expr(layer):
    r = _root()
    if r is None:
        return None
    out = r.op('slots/layer_{}/out1'.format(int(layer)))
    if out is None:
        return None
    return "op('{}')".format(out.path.replace('\\', '/'))


def _source_out_abs_expr(src_layer, col):
    if int(src_layer) in _layer_col_xfade_active_layers():
        return _layer_out_abs_expr(src_layer)
    r = _root()
    if r is None:
        return None
    out = r.op('slots/layer_{}/col_{}/out1'.format(src_layer, col))
    if out is None:
        return None
    return "op('{}')".format(out.path.replace('\\', '/'))


def _wire_upstream(slot, layer, src_layer=None, src_col=None):
    """Upstream = row below, using that row's assigned composition column."""
    if slot is None or layer >= _base_layer():
        return
    if src_layer is None or src_col is None:
        src_layer = layer + 1
        src_col = _get_layer_src_col(src_layer)
    up = slot.op('upstream') or slot.op('chain_src')
    expr = _source_out_abs_expr(src_layer, src_col)
    if up is None or not expr:
        return
    try:
        up.par.top.expr = expr
        up.par.top.mode = ParMode.EXPRESS
    except Exception:
        pass


def _wire_upstream_for_sig(slot, layer, sig):
    """Upstream wiring for a fixed composition signature (crossfade A/B stacks)."""
    if slot is None or layer >= _base_layer():
        return
    try:
        src_layer = int(layer) + 1
        src_col = int(sig[src_layer - 1])
    except Exception:
        return
    _wire_upstream(slot, layer, src_layer=src_layer, src_col=src_col)


CHAIN_W = 1920
CHAIN_H = 1080
CANVAS_PRESET_NAMES = ['1920x1080', '1080x1920', '1080x1080']
CANVAS_PRESETS = {
    '1920x1080': (1920, 1080),
    '1080x1920': (1080, 1920),
    '1080x1080': (1080, 1080),
}
VIDEO_FIT_MODE = 'fitoutside'
_COLUMN_XFADE = {'active': False, 'from_col': 1, 'to_col': 1, 't0': 0.0, 'dur': 1.0}


def _saved_canvas_dims(settings=None):
    s = settings if settings is not None else _settings()
    if s is None:
        return None
    try:
        w = int(float(s.fetch('saved_canvas_width', 0)))
        h = int(float(s.fetch('saved_canvas_height', 0)))
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    try:
        w = int(float(s.par.Savedcanvaswidth.eval()))
        h = int(float(s.par.Savedcanvasheight.eval()))
    except Exception:
        return None
    if w <= 0 or h <= 0:
        return None
    return w, h


def _canvas_preset_names(settings=None):
    names = list(CANVAS_PRESET_NAMES)
    custom_name = _saved_canvas_preset_name(settings)
    if custom_name is not None and custom_name not in names:
        names.append(custom_name)
    return names


def _saved_canvas_preset_name(settings=None):
    dims = _saved_canvas_dims(settings)
    if dims is None:
        return None
    return '{}x{}'.format(int(dims[0]), int(dims[1]))


def _sync_canvas_preset_menu(settings=None):
    s = settings if settings is not None else _settings()
    if s is None:
        return
    try:
        preset = s.par.Canvaspreset
    except Exception:
        return
    names = _canvas_preset_names(s)
    if not names:
        names = list(CANVAS_PRESET_NAMES)
    _apply_menu_options(preset, names, names)
    try:
        preset.label = 'Canvas Preset'
        preset.menuNames = list(names)
        preset.menuLabels = list(names)
    except Exception:
        pass


def _canvas_w():
    s = _settings()
    if s is None:
        return CHAIN_W
    try:
        return max(1, int(float(s.par.Canvaswidth.eval())))
    except Exception:
        return CHAIN_W


def _canvas_h():
    s = _settings()
    if s is None:
        return CHAIN_H
    try:
        return max(1, int(float(s.par.Canvasheight.eval())))
    except Exception:
        return CHAIN_H


def _canvas_w_expr():
    s = _settings()
    if s is None:
        return str(CHAIN_W)
    return "op('{}').par.Canvaswidth".format(s.path.replace('\\\\', '/'))


def _canvas_h_expr():
    s = _settings()
    if s is None:
        return str(CHAIN_H)
    return "op('{}').par.Canvasheight".format(s.path.replace('\\\\', '/'))


def _canvas_bg_rgb(settings=None):
    s = settings if settings is not None else _settings()
    if s is None:
        return DEFAULT_CANVAS_BG_R, DEFAULT_CANVAS_BG_G, DEFAULT_CANVAS_BG_B
    try:
        rgb = s.par.Canvasbg.eval()
        return (
            max(0.0, min(1.0, float(rgb[0]))),
            max(0.0, min(1.0, float(rgb[1]))),
            max(0.0, min(1.0, float(rgb[2]))),
        )
    except Exception:
        pass
    try:
        return (
            max(0.0, min(1.0, float(s.par.Canvasbgr.eval()))),
            max(0.0, min(1.0, float(s.par.Canvasbgg.eval()))),
            max(0.0, min(1.0, float(s.par.Canvasbgb.eval()))),
        )
    except Exception:
        return DEFAULT_CANVAS_BG_R, DEFAULT_CANVAS_BG_G, DEFAULT_CANVAS_BG_B


def _canvas_bg_expr(channel):
    s = _settings()
    if s is None:
        return '0'
    return "op('{}').par.Canvasbg{}".format(s.path.replace('\\\\', '/'), str(channel))


def _render_scale_value(scale):
    try:
        return _clamp_cell_render_scale(scale)
    except Exception:
        return 100


def _scaled_canvas_w_expr(scale):
    s = _settings()
    if s is None:
        return 'max(1, int({} * {} / 100.0))'.format(int(CHAIN_W), _render_scale_value(scale))
    return "max(1, int(float(op('{}').par.Canvaswidth.eval()) * {} / 100.0))".format(
        s.path.replace('\\\\', '/'),
        _render_scale_value(scale),
    )


def _scaled_canvas_h_expr(scale):
    s = _settings()
    if s is None:
        return 'max(1, int({} * {} / 100.0))'.format(int(CHAIN_H), _render_scale_value(scale))
    return "max(1, int(float(op('{}').par.Canvasheight.eval()) * {} / 100.0))".format(
        s.path.replace('\\\\', '/'),
        _render_scale_value(scale),
    )


def _scaled_canvas_w(scale):
    return max(1, int(_canvas_w() * _render_scale_value(scale) / 100.0))


def _scaled_canvas_h(scale):
    return max(1, int(_canvas_h() * _render_scale_value(scale) / 100.0))


def _slot_layer_col(slot):
    try:
        col = int(str(slot.name).split('_')[-1])
        layer = int(str(slot.parent().name).split('_')[-1])
        return layer, col
    except Exception:
        return None, None


def _slot_render_scale(slot=None, layer=None, col=None):
    if layer is None or col is None:
        layer, col = _slot_layer_col(slot)
    if layer is None or col is None:
        try:
            layer, col = _slot_coords(slot)
        except Exception:
            pass
    if layer is None or col is None:
        return 100
    return _cell_render_scale(int(layer), int(col))


def _set_canvas_black_constant(top):
    """Opaque canvas background at canvas resolution (empty program / preview letterbox)."""
    if top is None:
        return
    _set_top_chain_res(top)
    try:
        top.par.colorr.expr = _canvas_bg_expr('r')
        top.par.colorg.expr = _canvas_bg_expr('g')
        top.par.colorb.expr = _canvas_bg_expr('b')
        top.par.alpha = 1
    except Exception:
        pass


def _repair_opaque_black_sources():
    """Slot/layer empties were alpha 0 (transparent -> grey preview bars)."""
    r = _root()
    if r is None:
        return
    slots = r.op('slots')
    if slots is None:
        return
    for layer in range(1, MAX_LAYERS + 1):
        layer_comp = slots.op('layer_{}'.format(layer))
        if layer_comp is None:
            continue
        _set_canvas_black_constant(layer_comp.op('black'))
        for col in range(1, _num_cols() + 1):
            slot = layer_comp.op('col_{}'.format(col))
            if slot is not None:
                _set_canvas_black_constant(slot.op('empty'))


def _set_top_chain_res(top):
    if top is None:
        return
    w, h = _canvas_w(), _canvas_h()
    try:
        top.par.outputresolution = 'custom'
    except Exception:
        pass
    try:
        top.par.resolutionw.expr = _canvas_w_expr()
        top.par.resolutionw.mode = ParMode.EXPRESS
    except Exception:
        try:
            top.par.resolutionw = w
            top.par.resolutionw.mode = ParMode.CONSTANT
        except Exception:
            pass
    try:
        top.par.resolutionh.expr = _canvas_h_expr()
        top.par.resolutionh.mode = ParMode.EXPRESS
    except Exception:
        try:
            top.par.resolutionh = h
            top.par.resolutionh.mode = ParMode.CONSTANT
        except Exception:
            pass
    try:
        top.par.resmult = False
    except Exception:
        pass


def _sync_tox_canvas(tox_comp, layer=None, col=None):
    """Push canvas size into loaded effect TOX custom parameters."""
    if tox_comp is None:
        return
    # Logo overlays follow select_video_in resolution inside the TOX.
    if _is_logo_overlay_tox(tox_comp):
        return
    scale = _slot_render_scale(tox_comp.parent() if tox_comp is not None else None, layer, col)
    w, h = _scaled_canvas_w(scale), _scaled_canvas_h(scale)
    for pname, val in (('Canvaswidth', w), ('Canvasheight', h)):
        try:
            par = getattr(tox_comp.par, pname)
            par.val = val
            par.mode = ParMode.CONSTANT
        except Exception:
            pass


def _video_cover_source_size(video, scale=100):
    target_w, target_h = _scaled_canvas_w(scale), _scaled_canvas_h(scale)
    try:
        src_w = int(video.fetch('native_w', 0, search=False) or 0)
        src_h = int(video.fetch('native_h', 0, search=False) or 0)
    except Exception:
        src_w, src_h = 0, 0
    if src_w <= 0 or src_h <= 0:
        try:
            src_w, src_h = int(video.width), int(video.height)
        except Exception:
            src_w, src_h = target_w, target_h
    if src_w <= 0 or src_h <= 0:
        return target_w, target_h
    src_aspect = float(src_w) / float(max(1, src_h))
    target_aspect = float(target_w) / float(max(1, target_h))
    if src_aspect >= target_aspect:
        out_h = target_h
        out_w = int(round(out_h * src_aspect))
    else:
        out_w = target_w
        out_h = int(round(out_w / src_aspect))
    out_w = max(1, min(int(src_w), int(out_w)))
    out_h = max(1, min(int(src_h), int(out_h)))
    return out_w, out_h


def _configure_video_source(video, scale=100):
    """Movie source downsizes for low render scales while preserving source aspect."""
    if video is None:
        return
    scale = _render_scale_value(scale)
    try:
        current_file = str(video.par.file.eval())
    except Exception:
        current_file = ''
    try:
        stored_file = str(video.fetch('native_file', '', search=False) or '')
    except Exception:
        stored_file = ''
    if scale < 100 and current_file != stored_file:
        try:
            video.par.outputresolution = 'useinput'
            video.par.resmult = False
            video.cook(force=True)
            video.store('native_w', int(video.width), search=False)
            video.store('native_h', int(video.height), search=False)
            video.store('native_file', current_file, search=False)
        except Exception:
            pass
    try:
        if scale < 100:
            w, h = _video_cover_source_size(video, scale)
            video.par.outputresolution = 'custom'
            video.par.resolutionw = w
            video.par.resolutionw.mode = ParMode.CONSTANT
            video.par.resolutionh = h
            video.par.resolutionh.mode = ParMode.CONSTANT
        else:
            video.par.outputresolution = 'useinput'
        video.par.resmult = False
    except Exception:
        pass
    try:
        video.par.playmode = 'sequential'
    except Exception:
        pass


def _video_timeline_locked(video):
    if video is None:
        return False
    try:
        return str(video.par.playmode.eval()).strip().lower() == 'locked'
    except Exception:
        return False


def _set_video_active(video, on):
    """Per-slot playback: only live/crossfade cells should advance."""
    if video is None:
        return
    on = bool(on)
    try:
        video.par.playmode = 'sequential'
    except Exception:
        pass
    try:
        video.par.play = on
    except Exception:
        pass
    try:
        video.allowCooking = on
    except Exception:
        pass


def _configure_scaled_top_res(top, scale):
    if top is None:
        return
    scale = _render_scale_value(scale)
    w, h = _scaled_canvas_w(scale), _scaled_canvas_h(scale)
    try:
        top.par.outputresolution = 'custom'
    except Exception:
        pass
    try:
        top.par.resolutionw = w
        top.par.resolutionw.mode = ParMode.CONSTANT
    except Exception:
        pass
    try:
        top.par.resolutionh = h
        top.par.resolutionh.mode = ParMode.CONSTANT
    except Exception:
        pass
    try:
        top.par.resmult = False
    except Exception:
        pass


def _top_keeps_custom_resolution(top):
    try:
        return bool(top.fetch('sonomika_keep_custom_res', False, search=False))
    except Exception:
        return False


def _configure_video_fit(fit, scale=100):
    """Scale video to canvas size without distortion."""
    if fit is None:
        return
    _configure_scaled_top_res(fit, scale)
    try:
        fit.par.fit = VIDEO_FIT_MODE
    except Exception:
        pass


def _configure_tox_pick(tox_pick):
    """Reference TOX output at native resolution (no stretch)."""
    if tox_pick is None:
        return
    try:
        tox_pick.par.outputresolution = 'useinput'
        tox_pick.par.resmult = False
        tox_pick.par.top.expr = "op('tox/out1')"
        tox_pick.par.top.mode = ParMode.EXPRESS
    except Exception:
        pass


def _tox_feed_w_expr(scale=100):
    return _scaled_canvas_w_expr(scale)


def _tox_feed_h_expr(scale=100):
    return _scaled_canvas_h_expr(scale)


def _configure_tox_feed_select(sel, scale=100):
    """Downscale row-below feed before expensive effect TOXs, then upscale at tox_fit."""
    if sel is None:
        return
    scale = _render_scale_value(scale)
    _configure_scaled_top_res(sel, scale)
    try:
        for conn in list(sel.outputConnectors[0].connections):
            node = conn.owner
            if node is None or not str(getattr(node, 'OPType', '')).endswith('TOP'):
                continue
            if _top_keeps_custom_resolution(node):
                continue
            if node.OPType in ('fitTOP', 'resolutionTOP', 'selectTOP', 'nullTOP'):
                try:
                    node.par.outputresolution = 'useinput'
                    node.par.resmult = False
                except Exception:
                    pass
    except Exception:
        pass


def _tox_render_scale_from_comp(t):
    try:
        slot = t.parent()
    except Exception:
        slot = None
    return _slot_render_scale(slot)


def _is_stacked_cell_fx_tox(t):
    try:
        fx_slot = t.parent()
        slots = fx_slot.parent()
        return (
            str(fx_slot.name).startswith('fx_')
            and str(slots.name) == 'slots'
            and str(slots.parent().name) == 'cell_fx'
        )
    except Exception:
        return False


def _stacked_cell_fx_scale(t):
    try:
        layer, col = _slot_coords(t)
        if layer is not None and col is not None:
            return _cell_render_scale(layer, col)
    except Exception:
        pass
    return 100


def _lock_stacked_cell_fx_feed(sel, scale=100):
    """Feed a stacked TOX at the owning cell's scaled landscape size."""
    if sel is None:
        return
    try:
        sel.store('sonomika_keep_custom_res', True, search=False)
    except Exception:
        pass
    try:
        _configure_scaled_top_res(sel, scale)
    except Exception:
        pass


def _apply_tox_render_scale(t, layer=None, col=None):
    if t is None:
        return
    if _protect_video_source_tox_resolution(t):
        return
    scale = _slot_render_scale(t.parent(), layer, col)
    logo_protected_names = {
        'logo_file', 'logo_aspect_fit', 'logo_place', 'glitch_noise'
    } if _is_logo_overlay_tox(t) else set()
    if scale < 100:
        try:
            for child in t.children:
                if not str(getattr(child, 'OPType', '')).endswith('TOP'):
                    continue
                if child.name in logo_protected_names:
                    continue
                if _top_keeps_custom_resolution(child):
                    continue
                has_input = False
                try:
                    for connector in child.inputConnectors:
                        if connector.connections:
                            has_input = True
                            break
                except Exception:
                    has_input = True
                try:
                    if has_input:
                        child.par.outputresolution = 'useinput'
                        child.par.resmult = False
                    else:
                        _configure_scaled_top_res(child, scale)
                except Exception:
                    pass
        except Exception:
            pass
    else:
        try:
            for child in t.children:
                if child.name in logo_protected_names:
                    continue
                if _top_keeps_custom_resolution(child):
                    continue
                if str(getattr(child, 'OPType', '')).endswith('TOP'):
                    _set_top_chain_res(child)
        except Exception:
            pass
    for name in ('select_video_in', 'select_in', 'video_sel'):
        sel = t.op(name)
        if sel is not None:
            if _is_stacked_cell_fx_tox(t):
                _lock_stacked_cell_fx_feed(sel, _logo_overlay_feed_scale(t, _stacked_cell_fx_scale(t)))
            else:
                _configure_tox_feed_select(sel, _logo_overlay_feed_scale(t, scale))
    out = t.op('out1')
    if out is not None:
        if scale < 100:
            try:
                out.par.outputresolution = 'useinput'
                out.par.resmult = False
            except Exception:
                pass
        else:
            _set_top_chain_res(out)
    if logo_protected_names:
        _protect_logo_overlay_tox_resolution(t)


def _configure_tox_fit(fit):
    """Scale TOX to canvas like video — cover frame, trim sides, no squash."""
    if fit is None:
        return
    _set_top_chain_res(fit)
    try:
        fit.par.fit = VIDEO_FIT_MODE
    except Exception:
        pass


def _ensure_tox_fit(slot):
    """fitTOP between tox_pick and pick: same letterbox/crop as video_fit."""
    if slot is None:
        return None
    pick = slot.op('pick')
    tox_pick = slot.op('tox_pick')
    if pick is None or tox_pick is None:
        return None
    _configure_tox_pick(tox_pick)
    t = slot.op('tox')
    if _is_logo_overlay_tox(t):
        # Logo.tox already outputs a full-canvas transparent overlay and keeps
        # the logo aspect internally. The generic tox_fit cover/crop stage is
        # for normal content and stretches logo overlays horizontally.
        fit = slot.op('tox_fit')
        if fit is not None:
            try:
                ic = pick.inputConnectors[2]
                for conn in list(ic.connections):
                    if conn.owner == fit:
                        conn.disconnect()
            except Exception:
                pass
        try:
            if not pick.inputConnectors[2].connections or pick.inputConnectors[2].connections[0].owner != tox_pick:
                tox_pick.outputConnectors[0].connect(pick.inputConnectors[2])
        except Exception:
            pass
        return tox_pick
    fit = slot.op('tox_fit')
    if fit is None:
        fit = slot.create('fitTOP', 'tox_fit')
        try:
            fit.nodeX = tox_pick.nodeX + 140
            fit.nodeY = tox_pick.nodeY
        except Exception:
            pass
    _configure_tox_fit(fit)
    try:
        if not fit.inputConnectors[0].connections or fit.inputConnectors[0].connections[0].owner != tox_pick:
            tox_pick.outputConnectors[0].connect(fit.inputConnectors[0])
        if not pick.inputConnectors[2].connections or pick.inputConnectors[2].connections[0].owner != fit:
            fit.outputConnectors[0].connect(pick.inputConnectors[2])
    except Exception:
        pass
    return fit


def _keep_logo_overlay_slot_cooking(slot):
    """Keep native Logo.tox from collapsing to TD's fallback size between row cooks."""
    if slot is None:
        return False
    t = slot.op('tox')
    if not _is_logo_overlay_tox(t):
        return False
    try:
        slot.allowCooking = True
    except Exception:
        pass
    try:
        t.allowCooking = True
    except Exception:
        pass
    try:
        _protect_logo_overlay_tox_resolution(t)
    except Exception:
        pass
    try:
        slot.allowCooking = True
    except Exception:
        pass
    try:
        t.allowCooking = True
    except Exception:
        pass
    try:
        _ensure_tox_fit(slot)
    except Exception:
        pass
    for name in ('tox_pick', 'pick', 'layer_opacity', 'layer_over', 'out1'):
        node = slot.op(name)
        if node is None:
            continue
        try:
            node.allowCooking = True
        except Exception:
            pass
    for name in ('tox/out1', 'tox_pick', 'pick', 'layer_opacity', 'layer_over', 'out1'):
        node = slot.op(name)
        if node is None:
            continue
        try:
            node.cook(force=True)
        except Exception:
            pass
    return True


def _ensure_freeze_hold(slot, source=None):
    if slot is None:
        return None
    pick = slot.op('pick')
    if pick is None:
        return None
    hold = slot.op('freeze_hold')
    if hold is None:
        hold = slot.create('nullTOP', 'freeze_hold')
        try:
            hold.nodeX = pick.nodeX + 140
            hold.nodeY = pick.nodeY - 120
        except Exception:
            pass
    try:
        hold.par.outputresolution = 'useinput'
        hold.par.resmult = False
    except Exception:
        pass
    if source is not None:
        try:
            if not hold.inputConnectors[0].connections or hold.inputConnectors[0].connections[0].owner != source:
                source.outputConnectors[0].connect(hold.inputConnectors[0])
        except Exception:
            pass
    try:
        if len(pick.inputConnectors) >= 4:
            hold.outputConnectors[0].connect(pick.inputConnectors[3])
    except Exception:
        pass
    return hold


def _ensure_video_fit(slot):
    """fitTOP between movie and pick: cover canvas, preserve aspect."""
    if slot is None:
        return None
    video = slot.op('video')
    pick = slot.op('pick')
    if video is None or pick is None:
        return None
    layer, col = _slot_layer_col(slot)
    scale = _slot_render_scale(slot, layer, col)
    fit = slot.op('video_fit')
    if fit is None:
        fit = slot.create('fitTOP', 'video_fit')
        try:
            fit.nodeX = video.nodeX + 140
            fit.nodeY = video.nodeY
        except Exception:
            pass
    canvas_fit = slot.op('video_canvas_fit')
    if canvas_fit is None:
        canvas_fit = slot.create('fitTOP', 'video_canvas_fit')
        try:
            canvas_fit.nodeX = fit.nodeX + 140
            canvas_fit.nodeY = fit.nodeY
        except Exception:
            pass
    _configure_video_source(video, scale)
    _configure_video_fit(fit, scale)
    _configure_tox_fit(canvas_fit)
    try:
        if not fit.inputConnectors[0].connections or fit.inputConnectors[0].connections[0].owner != video:
            video.outputConnectors[0].connect(fit.inputConnectors[0])
        if not canvas_fit.inputConnectors[0].connections or canvas_fit.inputConnectors[0].connections[0].owner != fit:
            fit.outputConnectors[0].connect(canvas_fit.inputConnectors[0])
        if not pick.inputConnectors[1].connections or pick.inputConnectors[1].connections[0].owner != canvas_fit:
            canvas_fit.outputConnectors[0].connect(pick.inputConnectors[1])
    except Exception:
        pass
    _ensure_freeze_hold(slot)
    return canvas_fit


def _apply_slot_canvas(slot):
    if slot is None:
        return
    layer, col = _slot_layer_col(slot)
    scale = _slot_render_scale(slot, layer, col)
    for name in ('empty', 'upstream', 'chain_src', 'pass', 'pick', 'layer_opacity', 'layer_over', 'video_canvas_fit'):
        _set_top_chain_res(slot.op(name))
    _configure_video_fit(slot.op('video_fit'), scale)
    _configure_tox_pick(slot.op('tox_pick'))
    _ensure_video_fit(slot)
    _ensure_tox_fit(slot)
    _ensure_freeze_hold(slot)
    t = slot.op('tox')
    if t is not None:
        _sync_tox_canvas(t, layer, col)
        _heal_effect_tox(t)
        _apply_tox_render_scale(t, layer, col)


def _apply_canvas_settings_change(par_name, par=None):
    """Perform settings panel + /settings parexec — apply canvas size changes."""
    name = str(par_name or '').strip()
    if name == 'Canvaspreset':
        value = ''
        if par is not None:
            try:
                value = str(par.eval())
            except Exception:
                value = ''
        if not value:
            s = _settings()
            if s is not None:
                try:
                    value = str(s.par.Canvaspreset.eval())
                except Exception:
                    value = ''
        apply_canvas_preset(value)
        return True
    if name in ('Canvaswidth', 'Canvasheight', 'Canvasbg', 'Canvasbgr', 'Canvasbgg', 'Canvasbgb'):
        apply_canvas_size()
        return True
    return False


def apply_canvas_preset(preset_name):
    preset_name = str(preset_name or '').strip()
    if preset_name == _saved_canvas_preset_name():
        dims = _saved_canvas_dims()
        if dims is None:
            apply_canvas_size()
            return
        w, h = dims
        s = _settings()
        if s is not None:
            try:
                s.par.Canvaswidth = w
                s.par.Canvasheight = h
            except Exception:
                pass
        apply_canvas_size()
        return
    if preset_name not in CANVAS_PRESETS:
        apply_canvas_size()
        return
    w, h = CANVAS_PRESETS[preset_name]
    s = _settings()
    if s is not None:
        try:
            s.par.Canvaswidth = w
            s.par.Canvasheight = h
        except Exception:
            pass
    apply_canvas_size()


def save_canvas_size():
    """Store the current canvas dimensions as the reusable custom preset."""
    s = _settings()
    if s is None:
        return False
    w, h = _canvas_w(), _canvas_h()
    try:
        s.store('saved_canvas_width', int(w))
        s.store('saved_canvas_height', int(h))
        for name in ('Savedcanvaswidth', 'Savedcanvasheight'):
            try:
                getattr(s.par, name).destroy()
            except Exception:
                pass
    except Exception:
        return False
    _sync_canvas_preset_menu(s)
    try:
        saved_name = _saved_canvas_preset_name(s)
        if saved_name:
            s.par.Canvaspreset = saved_name
    except Exception:
        pass
    apply_canvas_size()
    return True


def apply_canvas_size():
    """Rebind all clip/slot TOP resolutions to settings canvas size."""
    r = _root()
    if r is None:
        return
    w, h = _canvas_w(), _canvas_h()
    slots = r.op('slots')
    if slots is not None:
        for layer in range(1, MAX_LAYERS + 1):
            layer_comp = slots.op('layer_{}'.format(layer))
            if layer_comp is None:
                continue
            _set_top_chain_res(layer_comp.op('black'))
            for col in range(1, _num_cols() + 1):
                _apply_slot_canvas(layer_comp.op('col_{}'.format(col)))
    for name in ('chain_out', 'chain_prev', 'chain_next', 'column_xfade', 'program_sel'):
        _set_top_chain_res(r.op(name))
    _ensure_column_xfade_nodes(r)
    _repair_opaque_black_sources()
    _sync_program_preview()
    _sync_root_output()
    _ensure_root_output()
    try:
        col = int(float(r.par.Activecolumn.eval())) or 1
    except Exception:
        col = 1
    _rebuild_column_chain(col)
    _sync_grid_ui()
    try:
        _refresh_global_fx_canvas_feed()
    except Exception:
        pass
    try:
        ui = r.op('ui')
        perform = op('/perform')
        if perform is not None and ui is not None:
            perform.par.winop = ui.path
            perform.par.interact = True
            perform.par.drawwindow = True
            perform.par.winw = UI_W
            perform.par.winh = UI_H
    except Exception:
        pass
    print('Canvas {}x{}'.format(w, h))


def _ensure_slot_chain(slot, layer):
    """Pass-through row below: upstream -> pass -> pick input 3."""
    if slot is None:
        return
    _ensure_video_fit(slot)
    if layer >= _base_layer():
        empty = slot.op('empty')
        pass_sel = slot.op('pass')
        if empty is not None and pass_sel is not None:
            try:
                pass_sel.par.top = empty
                pass_sel.par.top.mode = ParMode.CONSTANT
            except Exception:
                pass
            try:
                _ensure_slot_layer_blend(slot, layer)
            except Exception:
                pass
        return
    empty = slot.op('empty')
    pick = slot.op('pick')
    if empty is None or pick is None:
        return
    upstream = slot.op('upstream') or slot.op('chain_src')
    if upstream is None:
        upstream = slot.create('selectTOP', 'upstream')
        _set_top_chain_res(upstream)
        upstream.par.top = empty
    pass_sel = slot.op('pass')
    if pass_sel is None:
        pass_sel = slot.create('selectTOP', 'pass')
        _set_top_chain_res(pass_sel)
    try:
        pass_sel.par.top.expr = "op('upstream')"
        pass_sel.par.top.mode = ParMode.EXPRESS
    except Exception:
        pass
    try:
        _ensure_slot_layer_blend(slot, layer)
    except Exception:
        pass


def _heal_overlay_effect_tox(t):
    """Re-wire Pulse_Notes-style script overlay chains after external TOX load."""
    if t is None:
        return False
    out = t.op('out1')
    render = t.op('render_pulse_network')
    fit = t.op('fit_pulse_notes_overlay_fullframe')
    composite = t.op('composite_animation_overlay')
    video_in = t.op('select_video_in') or t.op('in1')
    if out is None or render is None or fit is None or composite is None:
        return False
    try:
        render.outputConnectors[0].connect(fit.inputConnectors[0])
        # Overlay-only: dots on composite in0, optional passthrough in1 on in1.
        # Slot layer_over composites this TOX over the row-below chain feed.
        fit.outputConnectors[0].connect(composite.inputConnectors[0])
        if video_in is not None:
            video_in.outputConnectors[0].connect(composite.inputConnectors[1])
        composite.outputConnectors[0].connect(out.inputConnectors[0])
        try:
            composite.par.operand = 'over'
        except Exception:
            pass
    except Exception:
        return False
    callbacks = t.op('pulse_network_callbacks')
    if callbacks is not None:
        try:
            render.par.callbacks.expr = "parent().op('pulse_network_callbacks')"
            render.par.callbacks.mode = ParMode.EXPRESS
        except Exception:
            pass
    frame_cook = t.op('pulse_frame_cook')
    if frame_cook is not None:
        try:
            frame_cook.par.active = True
            frame_cook.par.framestart = True
        except Exception:
            pass
    for node in (fit, composite, out):
        if node is not None:
            _set_top_chain_res(node)
    try:
        t.allowCooking = True
        for child in t.children:
            child.allowCooking = True
    except Exception:
        pass
    return True


def _schedule_effect_resolution_repair(layer, col):
    """Repair async-loaded source and stacked effect resolutions."""
    layer, col = int(layer), int(col)

    def _repair():
        slot = _slot(layer, col)
        if slot is None:
            return
        t = slot.op('tox')
        if t is not None:
            _heal_effect_tox(t)
        try:
            _wire_slot_cell_fx_chain(layer, col, slot)
        except Exception:
            pass

    for delay in (1, 4, 12, 30):
        try:
            run(_repair, delayFrames=delay, fromOP=_root())
        except Exception:
            try:
                run(_repair, delayFrames=delay)
            except Exception:
                pass


def _is_generic_top_fx_tox(t):
    """Shared TOX convention: plain in1 -> effect graph -> out1."""
    if t is None or t.op('out1') is None or t.op('in1') is None:
        return False
    if t.op('select_video_in') is not None or t.op('select_in') is not None or t.op('video_sel') is not None:
        return False
    try:
        return bool(t.op('in1').isTOP and t.op('out1').isTOP)
    except Exception:
        return False


def _ensure_generic_tox_input_adapter(t):
    """Adapt standard in1/out1 TOXs to Sonomika's row-below select feed."""
    if not _is_generic_top_fx_tox(t):
        return None
    in_top = t.op('in1')
    if in_top is None:
        return None
    sel = t.op('select_video_in')
    if sel is None:
        try:
            sel = t.create('selectTOP', 'select_video_in')
            sel.nodeX = in_top.nodeX
            sel.nodeY = in_top.nodeY - 120
        except Exception:
            return None
    try:
        sel.par.top.expr = "op('in1')"
        sel.par.top.mode = ParMode.EXPRESS
        sel.par.outputresolution = 'useinput'
        sel.par.resmult = False
    except Exception:
        pass

    targets = []
    try:
        for child in t.children:
            if child is sel:
                continue
            for index, connector in enumerate(child.inputConnectors):
                for conn in list(connector.connections):
                    if conn.owner == in_top:
                        targets.append((child, index))
    except Exception:
        targets = []
    for target, index in targets:
        try:
            sel.outputConnectors[0].connect(target.inputConnectors[index])
        except Exception:
            pass
    return sel


def _protect_generic_tox_resolution(t):
    """Preserve shared TOX internals; Sonomika fits the final out1 externally."""
    if not _is_generic_top_fx_tox(t):
        return False
    try:
        t.store('sonomika_generic_top_fx', True, search=False)
    except Exception:
        pass
    protected = False
    skip_names = {'in1', 'out1', 'select_video_in', 'select_in', 'video_sel'}
    try:
        children = list(t.children)
    except Exception:
        return False
    for child in children:
        try:
            if not child.isTOP or child.name in skip_names:
                continue
            child.store('sonomika_keep_custom_res', True)
            protected = True
        except Exception:
            pass
    return protected


def _is_video_source_tox(t):
    """TOX that captures/plays video directly (no row-below in1 effect chain)."""
    # Logo overlays use a Movie File In TOP for their embedded still image;
    # they are effects, not video-source TOXs. Treating them as video sources
    # periodically forces every internal TOP to useinput and causes flicker.
    if _is_logo_overlay_tox(t):
        return False
    if t is None or t.op('out1') is None:
        return False
    if t.op('in1') is not None:
        return False
    try:
        ext = str(t.par.externaltox.eval()).lower()
        if 'video_device' in ext:
            return True
    except Exception:
        pass
    try:
        for child in t.children:
            if not child.isTOP:
                continue
            optype = str(getattr(child, 'OPType', '')).lower()
            if optype in ('videodeviceintop', 'moviefileintop'):
                return True
    except Exception:
        pass
    return False


def _protect_video_source_tox_resolution(t):
    """Keep live camera / movie sources at native aspect; slot tox_fit scales to canvas."""
    if not _is_video_source_tox(t):
        return False
    try:
        t.store('sonomika_video_source_tox', True, search=False)
    except Exception:
        pass
    protected = False
    for child in t.children:
        try:
            if not child.isTOP:
                continue
            child.store('sonomika_keep_custom_res', True)
            child.par.outputresolution = 'useinput'
            child.par.resmult = False
            protected = True
        except Exception:
            pass
    return protected


def _protect_feedback_tox_resolution(t):
    """Keep feedback-style shared TOXs from being rewritten to canvas internals."""
    if t is None:
        return False
    try:
        children = list(t.children)
    except Exception:
        return False
    has_feedback = any('feedback' in str(getattr(child, 'OPType', '')).lower() for child in children)
    if not has_feedback:
        return False
    protected = False
    skip_names = {'in1', 'out1', 'select_video_in', 'select_in', 'video_sel'}
    for child in children:
        try:
            if not child.isTOP or child.name in skip_names:
                continue
            child.store('sonomika_keep_custom_res', True)
            protected = True
        except Exception:
            pass
    return protected


def _is_logo_overlay_tox(t):
    """True for the native Sonomika logo overlay effect."""
    if t is None:
        return False
    try:
        has_logo_nodes = bool(t.op('logo_file') and t.op('logo_place'))
    except Exception:
        has_logo_nodes = False
    if not has_logo_nodes:
        try:
            has_logo_nodes = bool(hasattr(t.par, 'Logoscale') and hasattr(t.par, 'Logoopacity'))
        except Exception:
            has_logo_nodes = False
    return bool(has_logo_nodes)


def _logo_overlay_feed_scale(t, scale):
    """Logo overlays are cheap and must keep stable full-canvas sizing."""
    return 100 if _is_logo_overlay_tox(t) else scale


_LOGO_PARAM_EXEC_TEXT = '''def onValueChange(par, prev):
    if par is None or par.name != 'Imagefile':
        return
    logo = parent().op('logo_file')
    if logo is None:
        return
    path = ''
    try:
        path = str(par.eval()).strip()
    except Exception:
        pass
    if not path:
        return
    try:
        logo.par.file = path
        logo.par.reloadpulse.pulse()
    except Exception:
        pass
'''


def _sync_logo_overlay_file_top(t, force_reload=False):
    """Push Imagefile onto logo_file — File custom pars do not EXPRESS to TOP file reliably."""
    if not _is_logo_overlay_tox(t):
        return False
    logo_file = t.op('logo_file')
    if logo_file is None:
        return False
    try:
        path = str(t.par.Imagefile.eval()).strip()
    except Exception:
        path = ''
    if not path:
        return False
    changed = False
    try:
        cur = str(logo_file.par.file.eval()).strip()
        if force_reload or cur != path:
            logo_file.par.file = path
            try:
                logo_file.par.file.mode = ParMode.CONSTANT
            except Exception:
                pass
            try:
                logo_file.par.reloadpulse.pulse()
            except Exception:
                pass
            changed = True
    except Exception:
        pass
    return changed


def _heal_logo_overlay_place_bindings(t):
    """Uniform logo scale (sx+sy) and aspect-safe fit — fixes horizontal squash."""
    if not _is_logo_overlay_tox(t):
        return False
    lp = t.op('logo_place')
    if lp is None:
        return False
    healed = False
    w_expr = _canvas_w_expr()
    h_expr = _canvas_h_expr()
    sx_expr = 'parent().par.Logoscale'
    bindings = (
        ('sx', sx_expr),
        ('sy', 'parent().par.Logoscale'),
        ('tx', 'parent().par.Positionx * 0.5'),
        ('ty', 'parent().par.Positiony * 0.5'),
    )
    for pn, expr in bindings:
        try:
            p = lp.par[pn]
            cur = str(p.expr or '').strip()
            if cur != expr or str(p.mode) != str(ParMode.EXPRESS):
                p.expr = expr
                p.mode = ParMode.EXPRESS
                healed = True
        except Exception:
            pass
    try:
        if str(lp.par.outputresolution.eval()) != 'useinput':
            lp.par.outputresolution = 'useinput'
            healed = True
    except Exception:
        pass
    try:
        if hasattr(lp.par, 'fit') and str(lp.par.fit.eval()) != 'fitbest':
            lp.par.fit = 'fitbest'
            healed = True
    except Exception:
        pass
    logo_fit = t.op('logo_aspect_fit')
    if logo_fit is not None:
        try:
            logo_fit.store('sonomika_keep_custom_res', True, search=False)
        except Exception:
            pass
        try:
            if str(logo_fit.par.fit.eval()) != 'fitbest':
                logo_fit.par.fit = 'fitbest'
                healed = True
        except Exception:
            pass
        for pn, expr in (('resolutionw', w_expr), ('resolutionh', h_expr)):
            try:
                p = logo_fit.par[pn]
                if str(p.expr or '').strip() != expr or str(p.mode) != str(ParMode.EXPRESS):
                    p.expr = expr
                    p.mode = ParMode.EXPRESS
                    healed = True
            except Exception:
                pass
        try:
            if str(logo_fit.par.outputresolution.eval()) != 'custom':
                logo_fit.par.outputresolution = 'custom'
                healed = True
        except Exception:
            pass
    try:
        if bool(lp.par.resmult.eval()):
            lp.par.resmult = False
            healed = True
    except Exception:
        pass
    logo_file = t.op('logo_file')
    if logo_file is not None:
        try:
            if str(logo_file.par.outputresolution.eval()) == 'useinput':
                logo_file.par.outputresolution = 'default'
                healed = True
        except Exception:
            pass
        try:
            if bool(logo_file.par.resmult.eval()):
                logo_file.par.resmult = False
                healed = True
        except Exception:
            pass
    return healed


def _heal_logo_overlay_imagefile_par(t):
    """Logo Imagefile must be a File par (browse +) with a working load path into logo_file."""
    if not _is_logo_overlay_tox(t):
        return False
    try:
        img = t.par.Imagefile
    except Exception:
        return False
    healed = False
    style = ''
    try:
        style = str(img.style)
    except Exception:
        pass
    old_val = ''
    try:
        old_val = str(img.eval()).strip()
    except Exception:
        pass
    page = None
    try:
        page = img.page
    except Exception:
        pass
    if style != 'File':
        try:
            img.destroy()
        except Exception:
            return False
        if page is None:
            for cp in t.customPages:
                if str(cp.name).lower() == 'logo':
                    page = cp
                    break
        if page is None:
            try:
                page = t.appendCustomPage('Logo')
            except Exception:
                return False
        try:
            page.appendFile('Imagefile', label='Image File')
        except Exception:
            return False
        if old_val:
            try:
                t.par.Imagefile = old_val
            except Exception:
                pass
        healed = True
    logo_file = t.op('logo_file')
    if logo_file is not None:
        want_bind = 'parent().par.Imagefile'
        try:
            fp = logo_file.par.file
            cur_bind = str(getattr(fp, 'bindExpr', '') or '').strip()
            bind_mode = getattr(ParMode, 'BIND', 3)
            if str(fp.mode) != str(bind_mode) or cur_bind != want_bind:
                fp.bindExpr = want_bind
                fp.mode = bind_mode
                healed = True
            elif str(fp.expr or '').strip() == want_bind and str(fp.mode) == str(ParMode.EXPRESS):
                # Legacy broken binding from Str→File migration.
                fp.bindExpr = want_bind
                fp.mode = bind_mode
                healed = True
        except Exception:
            pass
        if _sync_logo_overlay_file_top(t):
            healed = True
    pe = t.op('logo_param_exec')
    if pe is not None:
        want_text = _LOGO_PARAM_EXEC_TEXT.strip()
        try:
            if str(pe.text or '').strip() != want_text:
                pe.text = _LOGO_PARAM_EXEC_TEXT
                healed = True
            pe.par.op = t
            pe.par.active = True
            pe.par.valuechange = True
        except Exception:
            pass
    return healed


def _protect_logo_overlay_tox_resolution(t):
    """Keep logo overlay stable without overriding HUD-style expression resolutions."""
    if not _is_logo_overlay_tox(t):
        return False
    _heal_logo_overlay_imagefile_par(t)
    _heal_logo_overlay_place_bindings(t)
    try:
        t.allowCooking = True
    except Exception:
        pass
    try:
        slot = t.parent()
        if slot is not None:
            slot.allowCooking = True
    except Exception:
        pass
    logo_file = t.op('logo_file')
    if logo_file is not None:
        try:
            logo_file.par.outputresolution = 'default'
            logo_file.par.resmult = False
        except Exception:
            pass
    out = t.op('out1')
    if out is not None:
        try:
            out.par.outputresolution = 'useinput'
        except Exception:
            pass
        try:
            out.cook(force=True)
        except Exception:
            pass
    return True


def _stabilize_logo_overlay_tox_instances(root=None):
    """Re-lock loaded logo effects after focus/UI changes that may recook TOPs."""
    root = root or _root()
    if root is None:
        return 0
    seen = set()
    total = 0

    def _walk(node, depth=0):
        nonlocal total
        if node is None or depth > 24:
            return
        try:
            path = node.path
        except Exception:
            path = ''
        if path in seen:
            return
        seen.add(path)
        try:
            if _is_logo_overlay_tox(node):
                if _protect_logo_overlay_tox_resolution(node):
                    total += 1
        except Exception:
            pass
        try:
            children = list(node.children)
        except Exception:
            children = []
        for child in children:
            _walk(child, depth + 1)

    _walk(root)
    return total


def _heal_effect_tox(t, reload_external=False):
    """Re-wire effect chains after externaltox load (no reload pulse unless requested)."""
    if t is None:
        return
    _protect_generic_tox_resolution(t)
    _protect_video_source_tox_resolution(t)
    _ensure_generic_tox_input_adapter(t)
    _protect_feedback_tox_resolution(t)
    _protect_logo_overlay_tox_resolution(t)
    if _is_video_source_tox(t):
        return
    out = t.op('out1')
    healed = False
    for glsl_name in (
            'glsl_strobe_slices', 'glsl_chromatic_wave_slices', 'glsl_rotating_slices_3d',
            'hsv_glsl', 'glsl1', 'glsl'):
        glsl = t.op(glsl_name)
        if glsl is None or out is None:
            continue
        sel = t.op('select_video_in') or t.op('select_in')
        if sel is not None:
            try:
                sel.outputConnectors[0].connect(glsl.inputConnectors[0])
            except Exception:
                pass
            _configure_tox_feed_select(sel, _tox_render_scale_from_comp(t))
        try:
            glsl.outputConnectors[0].connect(out.inputConnectors[0])
        except Exception:
            pass
        for node in (glsl, out):
            _set_top_chain_res(node)
        _apply_tox_render_scale(t)
        if sel is not None:
            try:
                sel.cook(force=True)
                if reload_external and sel.width < 512:
                    t.par.enableexternaltoxpulse.pulse()
                    for node in (sel, glsl, out):
                        _set_top_chain_res(node)
                    _configure_tox_feed_select(sel, _tox_render_scale_from_comp(t))
                    sel.outputConnectors[0].connect(glsl.inputConnectors[0])
                    glsl.outputConnectors[0].connect(out.inputConnectors[0])
                    _apply_tox_render_scale(t)
            except Exception:
                pass
        healed = True
        break
    if not healed:
        _heal_overlay_effect_tox(t)


def _wire_tox_chain_feed(slot, layer):
    """Feed row-below composition cell into effect select."""
    if slot is None or layer >= _base_layer():
        return
    _wire_upstream(slot, layer)
    src_layer = layer + 1
    src_col = _get_layer_src_col(src_layer)
    feed_expr = _source_out_abs_expr(src_layer, src_col)
    if not feed_expr:
        return
    t = slot.op('tox')
    if t is None:
        return
    # Connect the live row-below frame before repairing effect internals.
    # HUD-style TOXs otherwise initialize from their portrait fallback size.
    for name in ('select_video_in', 'select_in', 'video_sel'):
        sel = t.op(name)
        if sel is not None:
            try:
                sel.par.top.expr = feed_expr
                sel.par.top.mode = ParMode.EXPRESS
                _configure_tox_feed_select(
                    sel,
                    _logo_overlay_feed_scale(t, _slot_render_scale(slot, layer, None)),
                )
                try:
                    sel.cook(force=True)
                except Exception:
                    pass
                _heal_effect_tox(t)
                _apply_tox_render_scale(t)
            except Exception:
                pass
            return
    _heal_effect_tox(t)


def _tox_load_path(path):
    return _store_asset_path(path)


def _slot_tox_path(slot):
    t = slot.op('tox') if slot is not None else None
    if t is None:
        return ''
    try:
        return _norm_asset_path(_resolve_tox_external_path(t) or '')
    except Exception:
        return ''


def _tox_cook_mode():
    s = _settings()
    try:
        mode = str(s.par.Toxcookmode.eval()).strip().lower()
    except Exception:
        mode = 'html'
    if mode in ('all', 'always'):
        return 'all'
    if mode in ('live', 'liveonly', 'off'):
        return 'live'
    return 'html'


def _tox_path_looks_html(path):
    low_path = str(path or '').replace('\\', '/').lower()
    return any(token in low_path for token in (
        'weather wave',
        'weather_wave',
        '_html',
        'html_',
        '_embed',
        'embed.',
        'embedded',
        '.html',
    ))


def _tox_comp_looks_html(t, path=''):
    if t is None:
        return False
    if _tox_path_looks_html(path):
        return True
    try:
        cached = t.fetch('sonomika_looks_html', None, search=False)
        if cached is not None:
            return bool(cached)
    except Exception:
        pass
    looks_html = False
    try:
        if t.op('web_render') is not None or t.op('html_page') is not None:
            looks_html = True
    except Exception:
        pass
    try:
        t.store('sonomika_looks_html', bool(looks_html), search=False)
    except Exception:
        pass
    return bool(looks_html)


def _warm_html_tox(slot, path='', layer=None, col=None, force=False):
    t = slot.op('tox') if slot is not None else None
    if t is None:
        return False
    looks_html = _tox_path_looks_html(path)
    if not looks_html:
        looks_html = _tox_comp_looks_html(t, path)
    if not looks_html:
        return False
    path_norm = _norm_asset_path(path)
    try:
        if (not force) and t.fetch('sonomika_html_warmed_path', '', search=False) == path_norm:
            try:
                t.allowCooking = True
            except Exception:
                pass
            web = t.op('web_render')
            if web is not None:
                try:
                    web.par.transparent = True
                except Exception:
                    pass
                try:
                    web.par.updatewhenloaded = True
                except Exception:
                    pass
                try:
                    web.par.alwayscook = True
                except Exception:
                    pass
            return True
    except Exception:
        pass
    try:
        t.store('sonomika_looks_html', True, search=False)
    except Exception:
        pass
    try:
        t.allowCooking = True
    except Exception:
        pass
    web = t.op('web_render')
    if web is not None:
        try:
            web.par.transparent = True
        except Exception:
            pass
        try:
            web.par.updatewhenloaded = True
        except Exception:
            pass
        try:
            web.par.alwayscook = True
        except Exception:
            pass
    for child_name in ('web_render', 'html_page', 'out1'):
        child = t.op(child_name)
        if child is None:
            continue
        try:
            child.allowCooking = True
        except Exception:
            pass
        try:
            child.cook(force=True)
        except Exception:
            pass
    try:
        t.cook(force=True)
    except Exception:
        pass
    try:
        t.store('sonomika_html_warmed_path', path_norm, search=False)
    except Exception:
        pass
    return True


def _cook_html_tox_slot_once(slot):
    if slot is None:
        return
    for rel in ('tox/web_render', 'tox/out1', 'tox_fit', 'tox_pick', 'pick', 'layer_opacity', 'out1'):
        node = slot.op(rel)
        if node is None:
            continue
        try:
            node.allowCooking = True
        except Exception:
            pass
        try:
            node.cook(force=True)
        except Exception:
            pass


def _prime_html_tox_slot(slot, frames=90):
    if slot is None:
        return
    frames = max(1, int(frames or 1))
    state_key = 'sonomika_html_prime_remaining'
    try:
        slot.store(state_key, frames, search=False)
    except Exception:
        pass

    def _tick():
        try:
            remaining = int(slot.fetch(state_key, 0, search=False) or 0)
        except Exception:
            remaining = 0
        if remaining <= 0:
            return
        _cook_html_tox_slot_once(slot)
        try:
            slot.store(state_key, remaining - 1, search=False)
        except Exception:
            pass
        if remaining > 1:
            try:
                _defer_run(_tick, delayFrames=1, fromOP=_root())
            except Exception:
                pass

    _tick()


def warm_html_tox_cells(force=False, prime_frames=90):
    warmed = []
    for layer in range(1, _num_layers() + 1):
        for col in range(1, _num_cols() + 1):
            ctype, path = _cell_content(layer, col)
            if str(ctype).strip().lower() != 'tox' or not path:
                continue
            slot = _slot(layer, col)
            try:
                if _warm_html_tox(slot, path, layer, col, force=force):
                    _prime_html_tox_slot(slot, frames=prime_frames)
                    warmed.append((int(layer), int(col)))
            except Exception as exc:
                print('HTML TOX warm failed row {} col {}: {}'.format(layer, col, exc))
    try:
        _sync_layer_slot_pause_states(force_full=True)
    except Exception:
        pass
    return warmed


def _tox_cell_keep_cooking(layer, col, ctype=None, path=None, live=False, slot=None):
    ctype = str(ctype if ctype is not None else _cell_content(layer, col)[0]).strip().lower()
    if ctype != 'tox':
        return False
    if path is None:
        path = _cell_content(layer, col)[1]
    if not str(path or '').strip():
        return False
    if _tox_path_looks_html(path):
        return True
    mode = _tox_cook_mode()
    if mode == 'all':
        return True
    if bool(live):
        return True
    if mode == 'live':
        return False
    if slot is None:
        slot = _slot(layer, col)
    t = slot.op('tox') if slot is not None else None
    return _tox_comp_looks_html(t, path)


def _wire_tox(slot, path, layer=None, col=None, force_reload=False):
    # Keep missing assignments in clip_matrix for relinking, but never ask
    # TouchDesigner to load an absent TOX. Otherwise the COMP can keep/show
    # stale contents from a previously loaded effect.
    if _asset_file_missing(path, 'tox'):
        if layer is not None and col is not None:
            _reset_slot_media(int(layer), int(col))
        else:
            t = slot.op('tox') if slot is not None else None
            if t is not None:
                try:
                    t.par.externaltox = ''
                except Exception:
                    pass
                t.allowCooking = False
        return False
    t = slot.op('tox')
    if t is None:
        return
    try:
        slot.unstore('sonomika_tox_replaces_upstream')
    except Exception:
        pass
    path_norm = _norm_asset_path(path)
    load_path = _tox_load_path(path)
    already = _slot_tox_path(slot) == path_norm and bool(path_norm)
    t.allowCooking = True
    if force_reload or not already:
        t.par.externaltox = load_path
        t.par.enableexternaltoxpulse.pulse()
        _heal_effect_tox(t, reload_external=True)
    else:
        _heal_effect_tox(t, reload_external=False)
    _wire_tox_pick(slot)
    _ensure_tox_fit(slot)
    _sync_tox_canvas(t, layer, col)
    _apply_tox_render_scale(t, layer, col)
    if layer is not None and col is not None and (force_reload or not already):
        _schedule_effect_resolution_repair(layer, col)
    try:
        if t.fetch('sonomika_generic_top_fx', False, search=False):
            slot.store('sonomika_tox_replaces_upstream', True, search=False)
    except Exception:
        pass
    if layer is not None:
        _wire_upstream(slot, layer)
        _wire_tox_chain_feed(slot, layer)
    v = slot.op('video')
    if v is not None:
        _set_video_active(v, False)


def _wire_video(slot, path, play=False, resume=False, force_reload=False):
    v = slot.op('video')
    if v is None:
        return False
    _ensure_video_fit(slot)
    path = _norm_asset_path(path) if path else ''
    prev = ''
    try:
        prev = _norm_asset_path(str(v.par.file.eval()).strip())
    except Exception:
        pass
    file_changed = bool(path) and (path != prev or force_reload)
    if file_changed:
        v.par.file = path
        try:
            v.par.reloadpulse.pulse()
        except Exception:
            pass
    _set_video_active(v, play)
    if not _video_timeline_locked(v) and (file_changed or resume or force_reload):
        try:
            # Cue/cook the new file even when inactive so thumbnails do not show
            # the Movie File In TOP's stale frame from the previous clip.
            if file_changed and not play:
                v.par.play = True
            v.par.cuepulse.pulse()
        except Exception:
            pass
        if file_changed:
            fit = slot.op('video_fit')
            for node in (v, fit):
                if node is None:
                    continue
                try:
                    node.cook(force=True)
                except Exception:
                    pass
            if not play:
                _set_video_active(v, False)
    pick = slot.op('pick')
    if pick is not None:
        pick.par.index = 1
    return file_changed


def _video_slot_should_play(layer, col):
    """True when this cell's movie should stay in play mode (live composition)."""
    layer, col = int(layer), int(col)
    if _COLUMN_XFADE.get('active'):
        try:
            mode = _COLUMN_XFADE.get('mode', 'column')
            if mode == 'layer_col':
                if int(layer) == int(_COLUMN_XFADE.get('layer', 0)):
                    return col in (
                        int(_COLUMN_XFADE.get('from_col', -1)),
                        int(_COLUMN_XFADE.get('to_col', -1)),
                    )
                return _get_layer_src_col(layer) == col
            if mode == 'column_layers':
                from_sig = tuple(_COLUMN_XFADE.get('from_sig') or ())
                to_sig = tuple(_COLUMN_XFADE.get('to_sig') or ())
                if len(from_sig) >= layer and len(to_sig) >= layer:
                    fc = int(from_sig[layer - 1])
                    tc = int(to_sig[layer - 1])
                    if fc != tc:
                        return col in (fc, tc)
                return _get_layer_src_col(layer) == col
            if mode in ('clip', 'sig', 'column'):
                cut_cols = _xfade_video_cut_play_cols(layer)
                if cut_cols is not None:
                    return int(col) in cut_cols
                for sig_name in ('from_sig', 'to_sig'):
                    sig = _COLUMN_XFADE.get(sig_name) or ()
                    if len(sig) >= layer and int(sig[layer - 1]) == col:
                        return True
                if mode in ('clip', 'sig'):
                    return False
            fc = int(_COLUMN_XFADE.get('from_col', 0))
            tc = int(_COLUMN_XFADE.get('to_col', 0))
            return col in (fc, tc)
        except Exception:
            return False
    if _get_layer_src_col(layer) != col:
        return False
    return True


def _prime_video_for_thumbnail(slot, layer, col, force=False):
    """Decode at least one frame so the grid thumbnail is not black while paused."""
    if slot is None:
        return
    v = slot.op('video')
    if v is None:
        return
    layer, col = int(layer), int(col)
    path = _norm_asset_path(_get(layer, col)[1])
    key = (layer, col)
    if not force and path and _PRIMED_VIDEO.get(key) == path:
        return
    _ensure_video_fit(slot)
    fit = slot.op('video_fit')
    try:
        v.par.preload = True
        if force:
            try:
                v.par.reloadpulse.pulse()
            except Exception:
                pass
        if _video_timeline_locked(v):
            v.allowCooking = True
        else:
            v.allowCooking = True
            v.par.play = True
            v.par.cuepulse.pulse()
    except Exception:
        pass
    for node in (v, fit):
        if node is None:
            continue
        try:
            node.cook(force=True)
        except Exception:
            pass
    if not _video_slot_should_play(layer, col):
        _set_video_active(v, False)
    if path:
        _PRIMED_VIDEO[key] = path


def _clear_video_prime_cache(layer=None, col=None):
    if layer is None or col is None:
        _PRIMED_VIDEO.clear()
        return
    _PRIMED_VIDEO.pop((int(layer), int(col)), None)


def _schedule_cell_preview_refresh(layer, col, delay_frames=1, force_video_prime=False):
    layer, col = int(layer), int(col)
    force = bool(force_video_prime)

    def _cb():
        _refresh_cell_preview(layer, col, force_video_prime=force)

    try:
        run(_cb, delayFrames=max(0, int(delay_frames)), fromOP=_root())
    except Exception:
        try:
            run(_cb, delayFrames=max(0, int(delay_frames)))
        except Exception:
            _refresh_cell_preview(layer, col, force_video_prime=force)


def _wire_tox_pick(slot):
    pick = slot.op('pick')
    if pick is not None:
        pick.par.index = 2


def _pause_slot(slot, on=False, keep_tox_cooking=False, clip_type=None):
    if slot is None:
        return
    clip_type = str(clip_type or '').strip().lower()
    v = slot.op('video')
    if v is not None:
        _set_video_active(v, bool(on) and clip_type == 'video')
    t = slot.op('tox')
    if t is not None:
        force_logo_cooking = False
        if clip_type == 'tox' and _is_logo_overlay_tox(t):
            allow = True
            force_logo_cooking = True
            try:
                _keep_logo_overlay_slot_cooking(slot)
            except Exception:
                pass
        elif clip_type == 'tox':
            allow = bool(on) or bool(keep_tox_cooking)
        else:
            allow = False
        try:
            t.allowCooking = allow and (
                force_logo_cooking or global_transport_playing() or bool(keep_tox_cooking)
            )
        except Exception:
            t.allowCooking = allow


def _slot_freeze_source(slot, clip_type=None):
    if slot is None:
        return None
    clip_type = str(clip_type or '').strip().lower()
    if clip_type == 'video':
        return slot.op('video_canvas_fit') or slot.op('video_fit')
    if clip_type == 'tox':
        t = slot.op('tox')
        if _is_logo_overlay_tox(t):
            return slot.op('tox_pick')
        return slot.op('tox_fit')
    try:
        pick = slot.op('pick')
        index = int(float(pick.par.index.eval())) if pick is not None else 0
    except Exception:
        index = 0
    if index == 1:
        return slot.op('video_canvas_fit') or slot.op('video_fit')
    if index == 2:
        t = slot.op('tox')
        if _is_logo_overlay_tox(t):
            return slot.op('tox_pick')
        return slot.op('tox_fit')
    return slot.op('pass') or slot.op('empty')


def _slot_freeze_index(slot, clip_type=None):
    clip_type = str(clip_type or '').strip().lower()
    if clip_type == 'video':
        return 1
    if clip_type == 'tox':
        return 2
    try:
        pick = slot.op('pick')
        index = int(float(pick.par.index.eval())) if pick is not None else 0
        if index in (1, 2):
            return index
    except Exception:
        pass
    return 0


def _tox_animation_pause_nodes(t):
    if t is None:
        return []
    nodes = []
    try:
        children = list(t.children)
    except Exception:
        children = []
    for child in children:
        optype = str(getattr(child, 'OPType', '')).lower()
        name = str(getattr(child, 'name', '')).lower()
        is_driver = (
            optype in ('executedat', 'chopexecutedat')
            or 'execute' in optype
            or 'timer' in optype
            or 'lfo' in optype
            or 'noise' in optype
            or 'feedback' in optype
            or name.endswith('_frame')
            or 'frame' in name
        )
        if is_driver:
            nodes.append(child)
    return nodes


def _set_tox_animation_paused(t, paused=True):
    if t is None:
        return
    key = 'sonomika_animation_pause_state'
    if paused:
        if t.fetch(key, None, search=False) is None:
            state = []
            for node in _tox_animation_pause_nodes(t):
                item = {'path': node.path}
                try:
                    item['allowCooking'] = bool(node.allowCooking)
                except Exception:
                    pass
                try:
                    item['active'] = bool(node.par.active.eval())
                except Exception:
                    pass
                state.append(item)
            try:
                t.store(key, state, search=False)
            except Exception:
                pass
        for node in _tox_animation_pause_nodes(t):
            try:
                if hasattr(node.par, 'active'):
                    node.par.active = False
            except Exception:
                pass
            optype = str(getattr(node, 'OPType', '')).lower()
            if 'feedback' in optype or 'timer' in optype or 'lfo' in optype or 'noise' in optype:
                try:
                    node.allowCooking = False
                except Exception:
                    pass
        try:
            t.allowCooking = True
        except Exception:
            pass
    else:
        state = t.fetch(key, [], search=False) or []
        for item in state:
            try:
                node = op(item.get('path'))
            except Exception:
                node = None
            if node is None:
                continue
            if 'active' in item:
                try:
                    node.par.active = bool(item['active'])
                except Exception:
                    pass
            if 'allowCooking' in item:
                try:
                    node.allowCooking = bool(item['allowCooking'])
                except Exception:
                    pass
        try:
            t.unstore(key)
        except Exception:
            pass
        try:
            t.allowCooking = True
        except Exception:
            pass


def _route_slot_frozen(slot, frozen=True, clip_type=None, capture=True):
    if slot is None:
        return False
    pick = slot.op('pick')
    source = _slot_freeze_source(slot, clip_type)
    source_index = _slot_freeze_index(slot, clip_type)
    if pick is None:
        return False
    if str(clip_type or '').strip().lower() == 'tox':
        t = slot.op('tox')
        if source is not None:
            try:
                source.lock = False
            except Exception:
                pass
            try:
                source.allowCooking = True
            except Exception:
                pass
        try:
            pick.par.index = 2 if frozen else 0
        except Exception:
            pass
        _set_tox_animation_paused(t, frozen)
        return True
    if frozen:
        try:
            pick.par.index = source_index
        except Exception:
            pass
        if source is not None:
            try:
                source.allowCooking = True
            except Exception:
                pass
            if capture:
                try:
                    t = slot.op('tox')
                    if str(clip_type or '').strip().lower() == 'tox' and t is not None:
                        t.allowCooking = True
                except Exception:
                    pass
                try:
                    source.cook(force=True)
                    pick.cook(force=True)
                except Exception:
                    pass
            try:
                source.lock = True
            except Exception:
                pass
            try:
                source.allowCooking = False
            except Exception:
                pass
        _pause_slot(slot, on=False, clip_type=clip_type)
    else:
        if source is not None:
            try:
                source.lock = False
            except Exception:
                pass
            try:
                source.allowCooking = True
            except Exception:
                pass
        try:
            pick.par.index = 0
        except Exception:
            pass
    return True


def _recapture_cell_freeze(layer, col, clip_type=None):
    """After replacing media on a frozen cell, unlock → cook new frame → re-lock."""
    layer, col = int(layer), int(col)
    if not _cell_frozen(layer, col):
        return False
    slot = _slot(layer, col)
    if slot is None:
        return False
    if clip_type is None:
        clip_type, _ = _get(layer, col)
    clip_type = str(clip_type or '').strip().lower()
    source = _slot_freeze_source(slot, clip_type)
    if source is not None:
        try:
            source.lock = False
        except Exception:
            pass
        try:
            source.allowCooking = True
        except Exception:
            pass
    if clip_type == 'video':
        try:
            _prime_video_for_thumbnail(slot, layer, col, force=True)
        except Exception:
            pass
    elif clip_type == 'tox':
        try:
            t = slot.op('tox')
            if t is not None:
                t.allowCooking = True
            if source is not None:
                source.cook(force=True)
        except Exception:
            pass
    return _route_slot_frozen(slot, True, clip_type, capture=True)


def _repair_all_video_playmodes():
    """Existing grids: lock Movie File In TOPs to TouchDesigner timeline."""
    r = _root()
    slots = r.op('slots') if r else None
    if slots is None:
        return
    for layer_comp in slots.children:
        if not layer_comp.isCOMP:
            continue
        for col_comp in layer_comp.children:
            if not col_comp.isCOMP or not col_comp.name.startswith('col_'):
                continue
            v = col_comp.op('video')
            if v is not None:
                _configure_video_source(v, _slot_render_scale(col_comp))


def _valid_clip_type(clip_type):
    return str(clip_type or '').strip().lower() in VALID_CLIP_TYPES


def _normalize_cell(layer, col, clip_type):
    """Keep drop target row/col — grid cells are only video or tox where you put them."""
    return int(layer), int(col)


def _recreate_empty_slot_tox(slot):
    """Destroy loaded TOX contents and rebuild the lightweight empty shell."""
    if slot is None:
        return None
    old = slot.op('tox')
    if old is not None:
        try:
            old.destroy()
        except Exception:
            return None
    try:
        tox = slot.create('baseCOMP', 'tox')
        tox.par.enableexternaltox = True
        black = tox.create('constantTOP', 'black')
        _set_par(black, 'colorr', expr=CANVAS_BG_R_EXPR)
        _set_par(black, 'colorg', expr=CANVAS_BG_G_EXPR)
        _set_par(black, 'colorb', expr=CANVAS_BG_B_EXPR)
        _set_par(black, 'alpha', 1)
        _bind_canvas_res(black)
        out = tox.create('outTOP', 'out1')
        black.outputConnectors[0].connect(out.inputConnectors[0])
        return tox
    except Exception as exc:
        print('Reset empty TOX shell failed:', exc)
        return None


def _reset_slot_media(layer, col, hard=False):
    """Clear slot wiring without touching clip_matrix (for scene switches)."""
    slot = _slot(layer, col)
    if slot is None:
        return
    try:
        _route_slot_pass_only(slot)
    except Exception:
        pass
    v = slot.op('video')
    if v is not None:
        try:
            v.lock = False
        except Exception:
            pass
        v.par.file = ''
        _set_video_active(v, False)
    # Freeze locks the fitted output TOP. A new/cleared set must unlock every
    # cached frame or full-resolution images remain serialized in the .toe.
    for name in ('video_fit', 'video_canvas_fit', 'tox_fit', 'pick', 'out1'):
        node = slot.op(name)
        if node is not None:
            try:
                node.lock = False
            except Exception:
                pass
    t = _recreate_empty_slot_tox(slot) if hard else slot.op('tox')
    if t is not None:
        try:
            t.par.externaltox = ''
        except Exception:
            pass
        t.allowCooking = False
    _clear_video_prime_cache(layer, col)
