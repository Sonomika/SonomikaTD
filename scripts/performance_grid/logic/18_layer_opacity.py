LAYER_OPACITY_DEFAULT = 1.0
_OPACITY_VALUE_EPS = 1.0 / 128.0
_LAYER_OPACITY_APPLIED = {}
_LAYER_OPACITY_UI_PCT = {}
OPACITY_SLIDER_PAD = 2
OPACITY_GROOVE_W = 2
OPACITY_SLIDER_THUMB_H = 8
OPACITY_VALUE_H = 14
OPACITY_VALUE_GAP = 2


def _read_panel_v(panel):
    if panel is None:
        return None
    for name in ('insidev', 'v', 'mousev'):
        try:
            value = float(getattr(panel, name))
            if 0.0 <= value <= 1.0:
                return value
        except Exception:
            pass
    try:
        owner_panel = panel.owner.panel
    except Exception:
        owner_panel = None
    if owner_panel is not None:
        for name in ('insidev', 'v', 'mousev'):
            try:
                value = float(getattr(owner_panel, name))
                if 0.0 <= value <= 1.0:
                    return value
            except Exception:
                pass
    return None


def _opacity_slider_row_parts(owner):
    slider = None
    fader = None
    p = owner
    for _ in range(10):
        if p is None:
            break
        name = getattr(p, 'name', '')
        if name == 'rowopacity':
            slider = p
        if name == 'opacity_fader':
            fader = p
        try:
            p = p.parent()
        except Exception:
            break
    if slider is None and fader is not None:
        try:
            slider = fader.parent()
        except Exception:
            pass
    if fader is None and slider is not None:
        fader = slider.op('opacity_fader')
    return slider, fader


def opacity_slider_value_from_panel(panel, owner):
    """Map panel coordinates to 0-1 across the visible fader track."""
    slider, fader = _opacity_slider_row_parts(owner)
    if fader is None:
        return 1.0
    v = _read_panel_v(panel)
    if v is None:
        return 1.0
    try:
        panel_owner = panel.owner if panel is not None else owner
    except Exception:
        panel_owner = owner
    if panel_owner is None:
        return 1.0
    try:
        py = v * float(panel_owner.par.h.eval())
    except Exception:
        return 1.0
    rel_y = py
    node = panel_owner
    while node is not None and slider is not None and node != slider:
        try:
            rel_y += float(node.par.y.eval())
            node = node.parent()
        except Exception:
            break
    try:
        fader_y = float(fader.par.y.eval())
        fader_h = float(fader.par.h.eval())
    except Exception:
        return 1.0
    if fader_h <= 0:
        return 1.0
    pad = float(OPACITY_SLIDER_PAD)
    inner_h = max(1.0, fader_h - 2.0 * pad)
    track_rel = rel_y - fader_y
    return max(0.0, min(1.0, (track_rel - pad) / inner_h))


def _layer_opacity_page(root):
    for pg in root.customPages:
        if pg.name == 'Layer Opacity':
            return pg
    return root.appendCustomPage('Layer Opacity')


def _layer_opacity_par(layer):
    r = _root()
    if r is None:
        return None
    name = 'Layer{}opacity'.format(int(layer))
    try:
        return getattr(r.par, name)
    except Exception:
        pass
    page = _layer_opacity_page(r)
    p = page.appendFloat(name, label='Layer {} Opacity'.format(int(layer)))
    p.default = LAYER_OPACITY_DEFAULT
    p.val = LAYER_OPACITY_DEFAULT
    p.min = 0.0
    p.max = 1.0
    try:
        p.normMin = 0.0
        p.normMax = 1.0
    except Exception:
        pass
    return p


def _ensure_layer_opacity_pars():
    for layer in range(1, MAX_LAYERS + 1):
        _layer_opacity_par(layer)


def layer_opacity(layer):
    p = _layer_opacity_par(layer)
    if p is None:
        return LAYER_OPACITY_DEFAULT
    try:
        return max(0.0, min(1.0, float(p.eval())))
    except Exception:
        return LAYER_OPACITY_DEFAULT


def _layer_opacity_par_name(layer):
    return 'Layer{}opacity'.format(int(layer))


def _bind_slot_level_opacity_expr(slot, layer):
    """Drive slot levelTOP from the row opacity custom par (one write updates all)."""
    level = slot.op('layer_opacity') if slot is not None else None
    if level is None:
        return False
    try:
        level.par.opacity.expr = "parent(4).par.{}".format(_layer_opacity_par_name(layer))
        level.par.opacity.mode = ParMode.EXPRESS
        return True
    except Exception:
        return False


def _slot_level_opacity_is_expr(level):
    if level is None:
        return False
    try:
        return level.par.opacity.mode == ParMode.EXPRESS
    except Exception:
        return False


def _set_level_premultiply(level, enabled=True):
    if level is None:
        return
    for pname in ('premultrgbbyalpha', 'postmultalpha', 'multiplyalpha'):
        try:
            getattr(level.par, pname).val = bool(enabled)
            return
        except Exception:
            continue


def _set_level_opacity(level, value):
    if level is None:
        return
    value = max(0.0, min(1.0, float(value)))
    try:
        level.par.opacity = value
    except Exception:
        pass
    _set_level_premultiply(level, True)


def _disconnect_input(input_connector):
    try:
        for conn in list(input_connector.connections):
            conn.disconnect()
    except Exception:
        pass


def _ensure_slot_layer_blend(slot, layer=None):
    """Composite clip over the row below; opacity applies to clip only."""
    if slot is None:
        return None
    pick = slot.op('pick')
    pass_sel = slot.op('pass')
    out = slot.op('out1')
    if pick is None or pass_sel is None or out is None:
        return None
    over = slot.op('layer_over')
    if over is None:
        try:
            over = slot.create('overTOP', 'layer_over')
            _set_top_chain_res(over)
        except Exception:
            return None
    level = slot.op('layer_opacity')
    if level is None:
        try:
            level = slot.create('levelTOP', 'layer_opacity')
            _set_top_chain_res(level)
        except Exception:
            return None
    try:
        _disconnect_input(pick.inputConnectors[3])
    except Exception:
        pass
    try:
        pick.outputConnectors[0].connect(level.inputConnectors[0])
    except Exception:
        pass
    try:
        level.outputConnectors[0].connect(over.inputConnectors[0])
        pass_sel.outputConnectors[0].connect(over.inputConnectors[1])
    except Exception:
        pass
    _set_level_premultiply(level, True)
    if layer is not None:
        _set_level_opacity(level, layer_opacity(layer))
    try:
        _connect_slot_content_to_level(slot, layer)
    except Exception:
        pass
    return over


def _route_slot_pass_only(slot):
    """Empty cell: pass through the stack below unchanged."""
    _ensure_slot_layer_blend(slot)
    pass_sel = slot.op('pass')
    out = slot.op('out1')
    if pass_sel is None or out is None:
        return
    try:
        _disconnect_input(out.inputConnectors[0])
        pass_sel.outputConnectors[0].connect(out.inputConnectors[0])
    except Exception:
        pass


def _route_slot_content(slot, pick_index, layer=None):
    """Clip cell: blend content over upstream using layer opacity."""
    _ensure_slot_layer_blend(slot, layer)
    pick = slot.op('pick')
    over = slot.op('layer_over')
    level = slot.op('layer_opacity')
    out = slot.op('out1')
    if pick is not None:
        try:
            pick.par.index = int(pick_index)
        except Exception:
            pass
    if over is not None and out is not None:
        try:
            _disconnect_input(out.inputConnectors[0])
            over.outputConnectors[0].connect(out.inputConnectors[0])
        except Exception:
            pass


def _cook_composition_output():
    r = _root()
    if r is None:
        return
    for name in ('chain_out', 'program_sel', 'out1'):
        try:
            node = r.op(name)
            if node is not None:
                node.cook(force=True)
        except Exception:
            pass


def _ensure_slot_opacity(slot, layer=None):
    if slot is None:
        return None
    _ensure_slot_layer_blend(slot, layer)
    return slot.op('layer_opacity')


def _opacity_cols_for_layer(layer):
    """Live composition slots for this layer (not every grid column)."""
    layer = int(layer)
    cols = set()
    for sl, sc in _composition_deps():
        if int(sl) == layer:
            cols.add(int(sc))
    if not cols:
        try:
            cols.add(int(_get_layer_src_col(layer)))
        except Exception:
            cols.add(1)
    return sorted(cols)


def _heal_slot_layer_opacity_routing(slot, layer, col):
    """Keep level premultiplied, routed through layer_over, and par-bound."""
    if slot is None:
        return
    level = slot.op('layer_opacity')
    _set_level_premultiply(level, True)
    ctype, path = _get(int(layer), int(col))
    if path and _valid_clip_type(ctype):
        pick_idx = 1 if ctype == 'video' else 2
        _route_slot_content(slot, pick_idx, layer)
    _bind_slot_level_opacity_expr(slot, layer)


def _ensure_layer_opacity_expr_bindings(deps=None):
    """Bind live composition slots to row opacity pars (cheap, no rewiring)."""
    if deps is None:
        deps = _composition_deps()
    seen = set()
    for layer, col in deps:
        key = (int(layer), int(col))
        if key in seen:
            continue
        seen.add(key)
        slot = _slot(layer, col)
        if slot is None:
            continue
        level = slot.op('layer_opacity')
        if _slot_level_opacity_is_expr(level):
            continue
        _bind_slot_level_opacity_expr(slot, layer)


def _heal_layer_opacity_routing(layers=None, cols=None):
    layer_list = [int(layers)] if layers is not None else range(1, _num_layers() + 1)
    col_list = list(cols) if cols is not None else range(1, _num_cols() + 1)
    for layer in layer_list:
        for col in col_list:
            slot = _slot(layer, col)
            if slot is not None:
                _heal_slot_layer_opacity_routing(slot, layer, col)


def _apply_opacity_to_slots_fast(layer, value, cols):
    layer = int(layer)
    value = max(0.0, min(1.0, float(value)))
    for col in cols:
        slot = _slot(layer, col)
        if slot is None:
            continue
        level = slot.op('layer_opacity')
        if level is None:
            continue
        if _slot_level_opacity_is_expr(level):
            continue
        try:
            level.par.opacity = value
        except Exception:
            pass


def _apply_opacity_to_slots(layer, value, cols):
    layer = int(layer)
    for col in cols:
        slot = _slot(layer, col)
        if slot is None:
            continue
        level = slot.op('layer_opacity')
        if level is None:
            _ensure_slot_opacity(slot, layer)
            level = slot.op('layer_opacity')
        if _slot_level_opacity_is_expr(level):
            continue
        _set_level_opacity(level, value)


def apply_layer_opacities():
    _ensure_layer_opacity_pars()
    _heal_layer_opacity_routing()
    all_cols = range(1, _num_cols() + 1)
    for layer in range(1, MAX_LAYERS + 1):
        value = layer_opacity(layer)
        p = _layer_opacity_par(layer)
        if p is not None:
            try:
                p.val = value
            except Exception:
                pass
        _LAYER_OPACITY_APPLIED[layer] = value
        _LAYER_OPACITY_UI_PCT[layer] = int(round(value * 100.0))
    _refresh_layer_opacity_ui()


def _fixed_opacity_row(layer):
    r = _root()
    gutter = _ui_grid_gutter(r)
    if gutter is None:
        return None
    fixed_rows = gutter.op('fixed_rows')
    if fixed_rows is None:
        return None
    return fixed_rows.op('row_{}'.format(int(layer)))


def set_layer_opacity(
    layer,
    value,
    paint_ui=True,
    force_cook=False,
    all_slots=False,
    update_par=True,
    slider_only=False,
):
    """Set layer opacity. Drag updates the row par; bound levelTOPs follow instantly."""
    layer = int(layer)
    value = max(0.0, min(1.0, float(value)))
    pct = int(round(value * 100.0))
    last = _LAYER_OPACITY_APPLIED.get(layer)
    skip_slots = False
    if not all_slots and not force_cook and last is not None:
        skip_slots = abs(last - value) < _OPACITY_VALUE_EPS
        if skip_slots and not slider_only and not paint_ui:
            if _LAYER_OPACITY_UI_PCT.get(layer) == pct:
                return value
        if skip_slots and not slider_only and paint_ui and _LAYER_OPACITY_UI_PCT.get(layer) == pct:
            return value
    if update_par:
        p = _layer_opacity_par(layer)
        if p is not None:
            try:
                p.val = value
            except Exception:
                pass
    if not skip_slots:
        cols = range(1, _num_cols() + 1) if all_slots else _opacity_cols_for_layer(layer)
        expr_driven = update_par and not all_slots
        if expr_driven:
            slot = _slot(layer, cols[0] if cols else _get_layer_src_col(layer))
            level = slot.op('layer_opacity') if slot is not None else None
            expr_driven = _slot_level_opacity_is_expr(level)
        if expr_driven:
            pass
        elif slider_only:
            _apply_opacity_to_slots_fast(layer, value, cols)
        else:
            _apply_opacity_to_slots(layer, value, cols)
        _LAYER_OPACITY_APPLIED[layer] = value
    if force_cook:
        _cook_composition_output()
    if paint_ui:
        row = _fixed_opacity_row(layer)
        if row is not None:
            ui_pct = _LAYER_OPACITY_UI_PCT.get(layer)
            pct_changed = ui_pct != pct
            if slider_only or pct_changed:
                _paint_opacity_slider(
                    row,
                    layer,
                    value,
                    slider_only=slider_only,
                    update_text=pct_changed,
                )
                if pct_changed:
                    _LAYER_OPACITY_UI_PCT[layer] = pct
        elif all_slots:
            _refresh_layer_opacity_ui(layer)
    return value


def set_layer_opacity_interactive(layer, value, mouse_drag=True):
    """Mouse drag updates the row par; bound levelTOPs follow instantly."""
    return set_layer_opacity(
        layer,
        value,
        paint_ui=True,
        force_cook=False,
        all_slots=False,
        update_par=True,
        slider_only=bool(mouse_drag),
    )


def commit_layer_opacity_drag(layer):
    """Write custom par after mouse up (no panel v re-sample)."""
    layer = int(layer)
    value = _LAYER_OPACITY_APPLIED.get(layer)
    if value is None:
        value = layer_opacity(layer)
    p = _layer_opacity_par(layer)
    if p is not None:
        try:
            p.val = float(value)
        except Exception:
            pass
    return value


def _row_is_fixed_gutter(row):
    try:
        parent = row.parent()
        return parent is not None and parent.name == 'fixed_rows'
    except Exception:
        return False


def _hide_grid_row_opacity(row):
    if row is None:
        return
    slider = row.op('rowopacity')
    if slider is None:
        return
    try:
        slider.par.display = False
        slider.par.enable = False
    except Exception:
        pass


def _style_opacity_slider_part(comp, rgb, alpha=1.0, clickthrough=True):
    if comp is None:
        return
    try:
        comp.par.clickthrough = bool(clickthrough)
        comp.par.drop = 'dropparent'
        comp.par.drag = 'dragno'
        comp.par.bgcolorr, comp.par.bgcolorg, comp.par.bgcolorb = rgb
        comp.par.bgalpha = float(alpha)
        comp.par.hmode = 'fixed'
        comp.par.vmode = 'fixed'
        comp.par.align = 'none'
    except Exception:
        pass


def _opacity_slider_total_h(cell_h=None):
    if cell_h is None:
        cell_h = _layout_cell_h()
    return max(14, int(cell_h) - 2)


def _opacity_fader_height(total_h=None):
    if total_h is None:
        total_h = _opacity_slider_total_h()
    return max(8, int(total_h) - OPACITY_VALUE_H - OPACITY_VALUE_GAP)


def _opacity_fader_width():
    try:
        return int(ROW_OPACITY_FADER_W)
    except Exception:
        return int(ROW_OPACITY_HDR_W)


def _opacity_slider_inner_size(fader_h, fader_w=None):
    pad = int(OPACITY_SLIDER_PAD)
    fw = int(fader_w or _opacity_fader_width())
    h = max(8, int(fader_h) - pad * 2)
    return fw, h, pad


def _opacity_track_layout(fader_w, inner_h, value, pad=0):
    """Thin center track + full-width thumb; fader_w is the wide mouse target."""
    fader_w = max(8, int(fader_w))
    groove_w = min(int(OPACITY_GROOVE_W), max(1, fader_w - 2))
    track_x = max(0, (fader_w - groove_w) // 2)
    fill_h = max(0, min(inner_h, int(round(inner_h * float(value)))))
    thumb_h = min(int(OPACITY_SLIDER_THUMB_H), inner_h)
    thumb_w = fader_w
    thumb_x = 0
    thumb_y = max(0, min(inner_h - thumb_h, fill_h - thumb_h // 2))
    y0 = int(pad)
    return {
        'groove': (track_x, y0, groove_w, inner_h),
        'fill': (track_x, y0, groove_w, fill_h),
        'thumb': (thumb_x, y0 + thumb_y, thumb_w, thumb_h),
    }


def _opacity_value_label(value):
    return str(int(round(max(0.0, min(1.0, float(value))) * 100.0)))


def _style_opacity_value_text(txt, w, h, value):
    if txt is None:
        return
    try:
        txt.par.text = _opacity_value_label(value)
        txt.par.resolutionw = max(24, int(w))
        txt.par.resolutionh = max(10, int(h))
        txt.par.font = TD_FONT
        txt.par.fontautosize = 'off'
        txt.par.fontsizex = TD_FONT_SIZE_SMALL
        txt.par.fontsizey = TD_FONT_SIZE_SMALL
        txt.par.keepfontratio = True
        txt.par.bgalpha = 0.0
        txt.par.alignx = 'center'
        txt.par.aligny = 'center'
        txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = TD_TEXT_LABEL
        txt.cook(force=True)
    except Exception:
        pass


def _upgrade_opacity_slider(slider):
    """Vertical TD fader + numeric value box underneath."""
    if slider is None:
        return
    for old_name in ('opacity_label',):
        old = slider.op(old_name)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass
    try:
        slider.par.top = ''
    except Exception:
        pass
    fader = slider.op('opacity_fader')
    if fader is None:
        fader = slider.create('containerCOMP', 'opacity_fader')
    try:
        fader.par.drop = 'dropno'
        fader.par.drag = 'dragno'
        fader.par.clickthrough = False
        fader.par.bgcolorr, fader.par.bgcolorg, fader.par.bgcolorb = TD_SLIDER_TRACK
        fader.par.bgalpha = 0.12
        fader.par.hmode = 'fixed'
        fader.par.vmode = 'fixed'
        fader.par.align = 'none'
    except Exception:
        pass
    for stray in ('opacity_groove', 'opacity_fill', 'opacity_thumb'):
        ch = slider.op(stray)
        if ch is not None:
            try:
                ch.destroy()
            except Exception:
                pass
    groove = fader.op('opacity_groove')
    if groove is None:
        groove = fader.create('containerCOMP', 'opacity_groove')
    _style_opacity_slider_part(groove, TD_SLIDER_GROOVE, alpha=1.0, clickthrough=True)
    fill = fader.op('opacity_fill')
    if fill is None:
        fill = fader.create('containerCOMP', 'opacity_fill')
    _style_opacity_slider_part(fill, TD_SLIDER_FILL, alpha=1.0, clickthrough=True)
    thumb = fader.op('opacity_thumb')
    if thumb is None:
        thumb = fader.create('containerCOMP', 'opacity_thumb')
    _style_opacity_slider_part(thumb, TD_SLIDER_THUMB, alpha=1.0, clickthrough=True)
    value_box = slider.op('opacity_value')
    if value_box is None:
        value_box = slider.create('containerCOMP', 'opacity_value')
    _style_opacity_slider_part(value_box, TD_BG_INPUT, alpha=1.0, clickthrough=True)
    txt = value_box.op('label_text')
    if txt is None:
        txt = value_box.create('textTOP', 'label_text')
    try:
        value_box.par.top = txt
        value_box.par.topfill = 'fit'
    except Exception:
        pass


def _ensure_row_opacity_slider(row, layer):
    if row is None:
        return None
    if not _row_is_fixed_gutter(row):
        _hide_grid_row_opacity(row)
        return None
    slider = row.op('rowopacity')
    if slider is None:
        slider = row.create('containerCOMP', 'rowopacity')
    try:
        slider.par.drop = 'dropno'
        slider.par.drag = 'dragno'
        slider.par.clickthrough = False
        slider.par.enable = True
        slider.par.bgcolorr, slider.par.bgcolorg, slider.par.bgcolorb = 0, 0, 0
        slider.par.bgalpha = 0.0
        slider.par.hmode = 'fixed'
        slider.par.vmode = 'fixed'
        slider.par.align = 'none'
    except Exception:
        pass
    _upgrade_opacity_slider(slider)
    _layout_row_opacity_slider(row, layer)
    return slider


def _apply_opacity_slider_visuals(fader, value, value_box=None, update_text=True):
    if fader is None:
        return
    try:
        fader_h = int(fader.par.h.eval())
    except Exception:
        fader_h = _opacity_fader_height()
    try:
        fw = int(fader.par.w.eval())
    except Exception:
        fw = _opacity_fader_width()
    fw, inner_h, pad = _opacity_slider_inner_size(fader_h, fw)
    layout = _opacity_track_layout(fw, inner_h, value, pad=pad)
    for comp, key in (
        (fader.op('opacity_fill'), 'fill'),
        (fader.op('opacity_thumb'), 'thumb'),
    ):
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
        except Exception:
            pass
    if value_box is not None and update_text:
        _style_opacity_value_text(
            value_box.op('label_text'),
            ROW_OPACITY_HDR_W,
            OPACITY_VALUE_H,
            value,
        )


def _paint_opacity_slider(row, layer, value=None, cell_h=None, slider_only=False, update_text=True):
    slider = row.op('rowopacity') if row is not None else None
    if slider is None:
        return
    if value is None:
        value = layer_opacity(layer)
    value = max(0.0, min(1.0, float(value)))
    fader = slider.op('opacity_fader')
    value_box = slider.op('opacity_value')
    if slider_only and fader is not None:
        _apply_opacity_slider_visuals(fader, value, value_box, update_text=update_text)
        return
    total_h = _opacity_slider_total_h(cell_h)
    fader_h = _opacity_fader_height(total_h)
    if fader is not None:
        try:
            fw = _opacity_fader_width()
            fader.par.x = 0
            fader.par.y = OPACITY_VALUE_H + OPACITY_VALUE_GAP
            fader.par.w = fw
            fader.par.h = fader_h
            fader.par.display = True
            fader.par.clickthrough = False
            fader.par.enable = True
        except Exception:
            pass
        fw, inner_h, pad = _opacity_slider_inner_size(fader_h, fw)
        layout = _opacity_track_layout(fw, inner_h, value, pad=pad)
        groove = fader.op('opacity_groove')
        fill = fader.op('opacity_fill')
        thumb = fader.op('opacity_thumb')
        for comp, key in (
            (groove, 'groove'),
            (fill, 'fill'),
            (thumb, 'thumb'),
        ):
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
            except Exception:
                pass
    if value_box is not None:
        try:
            value_box.par.x = 0
            value_box.par.y = 0
            value_box.par.w = ROW_OPACITY_HDR_W
            value_box.par.h = OPACITY_VALUE_H
            value_box.par.display = True
        except Exception:
            pass
        _style_opacity_value_text(value_box.op('label_text'), ROW_OPACITY_HDR_W, OPACITY_VALUE_H, value)


def _layout_row_opacity_slider(row, layer, cell_h=None):
    slider = row.op('rowopacity') if row is not None else None
    if slider is None:
        return
    total_h = _opacity_slider_total_h(cell_h)
    value = layer_opacity(layer)
    try:
        slider.par.x = ROW_LABEL_W + CELL_GAP
        slider.par.y = 0
        slider.par.w = ROW_OPACITY_HDR_W
        slider.par.h = total_h
        slider.par.hmode = 'fixed'
        slider.par.vmode = 'fixed'
        slider.par.align = 'none'
        slider.par.display = True
        slider.par.clickthrough = False
        slider.par.enable = True
        slider.par.drop = 'dropno'
        slider.par.drag = 'dragno'
    except Exception:
        pass
    fader = slider.op('opacity_fader')
    if fader is not None:
        try:
            fader.par.clickthrough = False
            fader.par.enable = True
        except Exception:
            pass
    _paint_opacity_slider(row, layer, value, cell_h)


def _refresh_layer_opacity_ui(layer=None):
    r = _root()
    grid = _ui_grid(r)
    gutter = _ui_grid_gutter(r)
    fixed_rows = gutter.op('fixed_rows') if gutter is not None else None
    if grid is None and gutter is None:
        return
    layers = [int(layer)] if layer is not None else range(1, _num_layers() + 1)
    for ly in layers:
        if grid is not None:
            _hide_grid_row_opacity(grid.op('row_{}'.format(ly)))
        fixed_row = fixed_rows.op('row_{}'.format(ly)) if fixed_rows is not None else None
        if fixed_row is None and gutter is not None:
            fixed_row = gutter.op('row_{}'.format(ly))
        if fixed_row is not None:
            _ensure_row_opacity_slider(fixed_row, ly)
    try:
        _refresh_panel_exec_panels()
    except Exception:
        pass
