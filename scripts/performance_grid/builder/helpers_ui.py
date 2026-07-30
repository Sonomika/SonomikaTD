from performance_grid.constants_builder import (
    CANVAS_BG_B_EXPR,
    CANVAS_BG_G_EXPR,
    CANVAS_BG_R_EXPR,
    CANVAS_H_EXPR,
    CANVAS_W_EXPR,
    SETTINGS_COMP,
    SETTINGS_TAB_PERF,
)


def _build_program_preview(ui):
    """Bottom-left live program preview (black, canvas aspect)."""
    zone = ui.op('program_preview_zone')
    if zone is None:
        zone = ui.create('containerCOMP', 'program_preview_zone')
        _set_par(zone, 'bgcolorr', UI_PREVIEW_BG[0])
        _set_par(zone, 'bgcolorg', UI_PREVIEW_BG[1])
        _set_par(zone, 'bgcolorb', UI_PREVIEW_BG[2])
        _set_par(zone, 'clickthrough', True)
        _set_par(zone, 'drop', 'dropno')
        _set_par(zone, 'drag', 'dragno')
    prev = zone.op('program_preview')
    if prev is None:
        prev = ui.op('program_preview')
    if prev is None:
        prev = zone.create('containerCOMP', 'program_preview')
    elif prev.parent != zone:
        try:
            prev.parent = zone
        except Exception:
            pass
    _set_par(prev, 'bgcolorr', UI_PREVIEW_BG[0])
    _set_par(prev, 'bgcolorg', UI_PREVIEW_BG[1])
    _set_par(prev, 'bgcolorb', UI_PREVIEW_BG[2])
    _set_par(prev, 'clickthrough', True)
    _set_par(prev, 'drop', 'dropno')
    _set_par(prev, 'drag', 'dragno')
    sel = prev.op('program_sel')
    if sel is None:
        sel = prev.create('selectTOP', 'program_sel')
    _set_par(sel, 'outputresolution', 'useinput')
    root = op('/project1/performance_mode')
    src = root.op('global_fx_out') if root else None
    if src is None and root is not None:
        src = root.op('program_sel')
    if src is None and root is not None:
        src = root.op('chain_out')
    if src is not None:
        _set_par(sel, 'top', src)
    legacy = prev.op('preview')
    for stale in ('program_view', 'program_bg'):
        node = prev.op(stale)
        if node is not None:
            try:
                node.destroy()
            except Exception:
                pass
    if legacy is not None:
        try:
            legacy.destroy()
        except Exception:
            pass
    try:
        prev.par.top = sel
        prev.par.topfill = 'best'
        prev.par.display = True
        prev.par.enable = True
    except Exception:
        pass
    return prev


def _create_grid_row(grid, layer, root, legacy_drop=None):
    row = grid.op('row_{}'.format(layer))
    if row is not None:
        return row
    row = grid.create('containerCOMP', 'row_{}'.format(layer))
    _set_par(row, 'w', _grid_content_w())
    _set_par(row, 'h', CELL_H + 2)
    _pass_drop(row)
    rl = row.create('containerCOMP', 'rowlabel')
    label = 'L{}'.format(max(1, DEFAULT_LAYERS - layer + 1))
    try:
        n = int(float(root.par.Numlayers.eval()))
        label = 'L{}'.format(n - layer + 1)
    except Exception:
        pass
    _make_cell(rl, ROW_LABEL_W, CELL_H - 2, label, kind='header')
    _style_cell(rl, 'label')
    _pin_scroll_label(rl)
    _pass_drop(rl)
    for c in range(1, NUM_COLS + 1):
        cell = row.create('containerCOMP', 'cell_{}_{}'.format(layer, c))
        _make_cell(cell, CELL_W, CELL_H)
        _set_par(cell, 'x', _col_x(c))
        _enable_cell_dragdrop(cell, grid, legacy_drop)
    return row


def _ensure_max_layers(root):
    """Pre-build hidden rows/slots up to MAX_LAYERS for dynamic add-row."""
    _ensure_numlayers_par(root)
    slots = root.op('slots')
    grid = root.op('ui/grid')
    legacy = root.op('legacy_drop')
    if slots is None or grid is None:
        return
    mx = _max_existing_layer(slots, grid)
    for layer_idx in range(mx + 1, MAX_LAYERS + 1):
        if slots.op('layer_{}'.format(layer_idx)) is None:
            _build_layer(slots, layer_idx)
        _create_grid_row(grid, layer_idx, root, legacy)
    _update_layer_par_limits(root)


def _update_column_par_limits(root):
    for pname in ('Activecolumn', 'Selectedcol'):
        try:
            p = getattr(root.par, pname)
            p.normMax = NUM_COLS
            if float(p.eval()) > NUM_COLS:
                p.val = NUM_COLS
        except Exception:
            pass


def _ensure_grid_columns(root):
    """Grow UI cells + slot chains up to NUM_COLS (safe on existing comps)."""
    ui = root.op('ui')
    stack = ui.op('grid_stack') if ui else None
    grid = stack.op('grid') if stack is not None else root.op('ui/grid')
    if grid is None:
        return
    hdr = stack.op('grid_header') if stack is not None else None
    if hdr is None:
        hdr = grid.op('header_row')
    if hdr is None and ui is not None:
        hdr = ui.op('grid_header')
    _setup_grid_scroll(grid, stack)
    mx = _max_grid_col(grid, hdr)
    if mx >= NUM_COLS:
        _update_column_par_limits(root)
        return
    content_w = _grid_content_w()
    if hdr is not None:
        _set_par(hdr, 'w', content_w)
    for c in range(mx + 1, NUM_COLS + 1):
        if hdr is not None:
            ch = hdr.create('containerCOMP', 'colhdr_{}'.format(c))
            _make_cell(ch, CELL_W, GRID_HDR_H, 'Col {}'.format(c), kind='header')
            _style_cell(ch, 'header')
            _set_par(ch, 'x', _col_x(c))
            _pass_drop(ch)
        for layer in range(1, MAX_LAYERS + 1):
            row = grid.op('row_{}'.format(layer))
            if row is None:
                continue
            _set_par(row, 'w', content_w)
            cell = row.create('containerCOMP', 'cell_{}_{}'.format(layer, c))
            _make_cell(cell, CELL_W, CELL_H)
            _set_par(cell, 'x', _col_x(c))
            _enable_cell_dragdrop(cell, grid, root.op('legacy_drop'))
    slots = root.op('slots')
    if slots is not None:
        for layer_idx in range(1, MAX_LAYERS + 1):
            layer = slots.op('layer_{}'.format(layer_idx))
            if layer is None:
                continue
            sw = layer.op('switch')
            for c in range(mx + 1, NUM_COLS + 1):
                if layer.op('col_{}'.format(c)) is not None:
                    continue
                out = _build_slot(layer, c, layer_idx)
                if sw is not None:
                    try:
                        out.outputConnectors[0].connect(sw.inputConnectors[c])
                    except Exception as exc:
                        print('Column slot wire', layer_idx, c, exc)
    _update_column_par_limits(root)


def _set_par(node, name, value=None, expr=None):
    try:
        par = getattr(node.par, name)
    except Exception:
        return False
    try:
        if expr is not None:
            par.expr = expr
            par.mode = ParMode.EXPRESS
        else:
            par.val = value
            par.mode = ParMode.CONSTANT
        return True
    except Exception:
        return False


def _style_cell(comp, kind='cell'):
    if kind == 'header':
        comp.par.bgcolorr, comp.par.bgcolorg, comp.par.bgcolorb = TD_BG_HEADER
    elif kind == 'label':
        comp.par.bgcolorr, comp.par.bgcolorg, comp.par.bgcolorb = TD_BG_MAIN
    else:
        comp.par.bgcolorr, comp.par.bgcolorg, comp.par.bgcolorb = CELL_BG_IDLE_R, CELL_BG_IDLE_G, CELL_BG_IDLE_B
        try:
            comp.par.bgalpha = 0.0
            for pname in ('leftborder', 'rightborder', 'topborder', 'bottomborder'):
                getattr(comp.par, pname).val = 'off'
            comp.par.borderover = True
        except Exception:
            pass


def _make_cell(comp, w, h, label='', kind='grid'):
    _set_par(comp, 'w', w)
    _set_par(comp, 'h', h)
    _set_par(comp, 'hmode', 'fixed')
    _set_par(comp, 'vmode', 'fixed')
    _style_cell(comp, 'cell')
    if kind == 'header':
        txt = comp.create('textTOP', 'label_text')
        _set_par(txt, 'text', label or '')
        _set_par(txt, 'font', TD_FONT)
        _set_par(txt, 'fontautosize', 'off')
        _set_par(txt, 'fontsizex', GRID_FONT_SIZE)
        _set_par(txt, 'fontsizey', GRID_FONT_SIZE)
        _set_par(txt, 'keepfontratio', True)
        _set_par(txt, 'resolutionw', max(32, int(w)))
        _set_par(txt, 'resolutionh', max(16, int(h)))
        _set_par(txt, 'bgalpha', 0.0)
        _set_par(txt, 'alignx', 'center')
        _set_par(txt, 'aligny', 'center')
        _set_par(txt, 'fontcolorr', TD_TEXT_LABEL[0])
        _set_par(txt, 'fontcolorg', TD_TEXT_LABEL[1])
        _set_par(txt, 'fontcolorb', TD_TEXT_LABEL[2])
        _set_par(comp, 'top', txt)
        _set_par(comp, 'topfill', 'fit')
        return
    thumb = comp.create('containerCOMP', 'cell_thumb')
    _set_par(thumb, 'w', w)
    _set_par(thumb, 'h', CELL_THUMB_H)
    _set_par(thumb, 'y', 0)
    _set_par(thumb, 'hmode', 'fixed')
    _set_par(thumb, 'vmode', 'fixed')
    _set_par(thumb, 'align', 'none')
    _pass_drop(thumb)
    try:
        thumb.par.clickthrough = True
    except Exception:
        pass
    name = comp.create('containerCOMP', 'cell_name')
    _set_par(name, 'w', w)
    _set_par(name, 'h', CELL_LABEL_H)
    _set_par(name, 'y', CELL_THUMB_H)
    _set_par(name, 'hmode', 'fixed')
    _set_par(name, 'vmode', 'fixed')
    _set_par(name, 'align', 'none')
    _set_par(name, 'bgcolorr', UI_NAME_BAR_BG[0])
    _set_par(name, 'bgcolorg', UI_NAME_BAR_BG[1])
    _set_par(name, 'bgcolorb', UI_NAME_BAR_BG[2])
    _pass_drop(name)
    try:
        name.par.clickthrough = True
    except Exception:
        pass
    empty = thumb.create('constantTOP', 'empty')
    _set_par(empty, 'colorr', EMPTY_CELL_R)
    _set_par(empty, 'colorg', EMPTY_CELL_G)
    _set_par(empty, 'colorb', EMPTY_CELL_B)
    _set_par(empty, 'alpha', 1.0)
    _set_par(empty, 'resolutionw', max(32, int(w)))
    _set_par(empty, 'resolutionh', max(16, CELL_THUMB_H))
    preview = thumb.create('selectTOP', 'preview')
    _set_par(preview, 'resolutionw', max(32, int(w)))
    _set_par(preview, 'resolutionh', max(16, CELL_THUMB_H))
    _set_par(preview, 'top', empty)
    _set_par(thumb, 'top', preview)
    _set_par(thumb, 'topfill', 'best')
    txt = name.create('textTOP', 'label_text')
    _set_par(txt, 'text', chr(183))
    _set_par(txt, 'font', TD_FONT)
    _set_par(txt, 'fontautosize', 'off')
    _set_par(txt, 'fontsizex', CELL_NAME_FONT_SIZE)
    _set_par(txt, 'fontsizey', CELL_NAME_FONT_SIZE)
    _set_par(txt, 'keepfontratio', True)
    _set_par(txt, 'resolutionw', max(32, int(w)))
    _set_par(txt, 'resolutionh', CELL_LABEL_H)
    _set_par(txt, 'bgalpha', 1.0)
    _set_par(txt, 'alignx', 'left')
    _set_par(txt, 'aligny', 'center')
    _set_par(txt, 'textoffsetx', 4)
    _set_par(txt, 'fontcolorr', UI_TEXT_SECONDARY[0])
    _set_par(txt, 'fontcolorg', UI_TEXT_SECONDARY[1])
    _set_par(txt, 'fontcolorb', UI_TEXT_SECONDARY[2])
    _set_par(txt, 'bgcolorr', UI_NAME_BAR_BG[0])
    _set_par(txt, 'bgcolorg', UI_NAME_BAR_BG[1])
    _set_par(txt, 'bgcolorb', UI_NAME_BAR_BG[2])
    _set_par(name, 'top', txt)
    _set_par(name, 'topfill', 'fill')
    badge = comp.create('containerCOMP', 'freeze_badge')
    _set_par(badge, 'x', max(0, int(w) - 18))
    _set_par(badge, 'y', CELL_THUMB_H)
    _set_par(badge, 'w', 18)
    _set_par(badge, 'h', CELL_LABEL_H)
    _set_par(badge, 'hmode', 'fixed')
    _set_par(badge, 'vmode', 'fixed')
    _set_par(badge, 'align', 'none')
    _set_par(badge, 'display', False)
    _set_par(badge, 'bgalpha', 0.0)
    _pass_drop(badge)
    try:
        badge.par.clickthrough = True
        badge.par.drop = 'dropparent'
        badge.par.drag = 'dragno'
    except Exception:
        pass
    badge_txt = badge.create('textTOP', 'badge_text')
    _set_par(badge_txt, 'text', 'F')
    _set_par(badge_txt, 'font', TD_FONT)
    _set_par(badge_txt, 'fontautosize', 'off')
    _set_par(badge_txt, 'fontsizex', CELL_NAME_FONT_SIZE)
    _set_par(badge_txt, 'fontsizey', CELL_NAME_FONT_SIZE)
    _set_par(badge_txt, 'keepfontratio', True)
    _set_par(badge_txt, 'resolutionw', 18)
    _set_par(badge_txt, 'resolutionh', CELL_LABEL_H)
    _set_par(badge_txt, 'bgalpha', 1.0)
    _set_par(badge_txt, 'alignx', 'center')
    _set_par(badge_txt, 'aligny', 'center')
    _set_par(badge_txt, 'fontcolorr', 1.0)
    _set_par(badge_txt, 'fontcolorg', 1.0)
    _set_par(badge_txt, 'fontcolorb', 1.0)
    _set_par(badge_txt, 'bgcolorr', 0.0)
    _set_par(badge_txt, 'bgcolorg', 0.0)
    _set_par(badge_txt, 'bgcolorb', 0.0)
    _set_par(badge, 'top', badge_txt)
    _set_par(badge, 'topfill', 'fill')
    _set_par(comp, 'top', '')


def _pass_drop(comp):
    try:
        comp.par.drop = 'dropno'
        comp.par.clickthrough = False
    except Exception:
        pass


def _enable_cell_dragdrop(cell, grid=None, legacy_drop=None):
    if grid is None:
        p = cell
        for _ in range(8):
            if p is None:
                break
            if getattr(p, 'name', '') == 'grid':
                grid = p
                break
            try:
                p = p.parent()
            except Exception:
                break
    if grid is None:
        return
    cb = grid.op('cell_dragdrop')
    if legacy_drop is None:
        root = grid
        for _ in range(8):
            if root is not None and root.op('logic') is not None:
                break
            try:
                root = root.parent()
            except Exception:
                root = None
                break
        legacy_drop = root.op('legacy_drop') if root else None
    try:
        cell.par.builtindrop = False
        cell.par.clickthrough = False
        cell.par.drag = 'usecallbacks'
        cell.par.drop = 'usecallbacks'
        if legacy_drop is not None:
            cell.par.dropscript = legacy_drop
        if cb is not None:
            cell.par.dragdropcallbacks = cb
    except Exception:
        pass
    for part_name in ('cell_thumb', 'cell_name', 'freeze_badge'):
        part = cell.op(part_name)
        if part is None:
            continue
        try:
            part.par.clickthrough = True
            part.par.drop = 'dropparent'
            part.par.drag = 'dragno'
        except Exception:
            pass


def _cell_panel_w():
    base_panel_w = int(UI_W // 2)
    return max(320, int((base_panel_w - CELL_GAP * 4) / 2))


def _settings_panel_x():
    return UI_PANEL_X + _cell_panel_w() + CELL_GAP * 4


def _settings_panel_w():
    try:
        floor = int(SETTINGS_PANEL_MIN_W)
    except Exception:
        floor = 320
    return max(floor, int(UI_W - _settings_panel_x()))


def _setup_cell_params_panel(ui, grid_h):
    panel = ui.create('parameterCOMP', 'cell_params')
    _set_par(panel, 'w', _cell_panel_w())
    _set_par(panel, 'h', PARAM_PANEL_H)
    _set_par(panel, 'x', UI_PANEL_X)
    _set_par(panel, 'y', 0)
    _set_par(panel, 'hmode', 'fixed')
    _set_par(panel, 'vmode', 'fixed')
    _set_par(panel, 'display', True)
    _set_par(panel, 'enable', False)
    _set_par(panel, 'header', True)
    _set_par(panel, 'pagenames', True)
    _set_par(panel, 'labels', True)
    _set_par(panel, 'separators', True)
    _set_par(panel, 'allowexpand', True)
    _set_par(panel, 'pagescope', '*')
    _set_par(panel, 'parscope', '*')
    _set_par(panel, 'combinescopes', 'any')
    _set_par(panel, 'autoscroll', True)
    _set_par(panel, 'builtin', True)
    _pass_drop(panel)
    try:
        panel.par.drag = 'dragno'
    except Exception:
        pass
    settings_panel = ui.create('parameterCOMP', 'settings_params')
    _set_par(settings_panel, 'w', _settings_panel_w())
    _set_par(settings_panel, 'h', PARAM_PANEL_H)
    _set_par(settings_panel, 'x', _settings_panel_x())
    _set_par(settings_panel, 'y', 0)
    _set_par(settings_panel, 'hmode', 'fixed')
    _set_par(settings_panel, 'vmode', 'fixed')
    _set_par(settings_panel, 'display', True)
    _set_par(settings_panel, 'enable', True)
    _set_par(settings_panel, 'header', True)
    _set_par(settings_panel, 'pagenames', True)
    _set_par(settings_panel, 'labels', True)
    _set_par(settings_panel, 'separators', True)
    _set_par(settings_panel, 'allowexpand', True)
    _set_par(settings_panel, 'pagescope', '*')
    _set_par(settings_panel, 'parscope', '*')
    _set_par(settings_panel, 'combinescopes', 'any')
    _set_par(settings_panel, 'autoscroll', True)
    _set_par(settings_panel, 'builtin', False)
    _set_par(settings_panel, 'custom', True)
    try:
        settings = op(SETTINGS_COMP)
        if settings is not None:
            settings_panel.par.op = ''
            settings_panel.par.op = settings.path
        settings_panel.par.drag = 'dragno'
        settings_panel.par.drop = 'dropno'
    except Exception:
        pass
    return panel


def _setup_scene_dragdrop(bar):
    if bar is None:
        return None
    cb = bar.op('scene_dragdrop')
    if cb is None:
        cb = bar.create('textDAT', 'scene_dragdrop')
    try:
        from performance_grid.assemble import SCENE_DRAGDROP
        cb.text = SCENE_DRAGDROP
        cb.par.language = 'python'
    except Exception:
        pass
    return cb


def _enable_scene_dragdrop(btn, bar=None):
    if btn is None:
        return
    if bar is None:
        p = btn
        for _ in range(8):
            if p is None:
                break
            if getattr(p, 'name', '') == 'scene_bar':
                bar = p
                break
            try:
                p = p.parent()
            except Exception:
                break
    if bar is None:
        return
    cb = bar.op('scene_dragdrop')
    if cb is None:
        cb = _setup_scene_dragdrop(bar)
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


def _wire_scene_bar_dragdrop(bar):
    if bar is None:
        return
    _setup_scene_dragdrop(bar)
    for ch in bar.children:
        if not ch.isCOMP:
            continue
        if ch.name.startswith('scene_btn_'):
            _enable_scene_dragdrop(ch, bar)


def _setup_grid_dragdrop(grid):
    if grid is None:
        return None
    cb = grid.op('cell_dragdrop')
    if cb is None:
        cb = grid.create('textDAT', 'cell_dragdrop')
    cb.text = CELL_DRAGDROP
    cb.par.language = 'python'
    _set_par(grid, 'drag', 'dragno')
    _set_par(grid, 'drop', 'dropno')
    return cb


def _build_slot(layer_comp, col, layer_idx):
    slot = layer_comp.create('baseCOMP', 'col_{}'.format(col))
    slot.nodeX = col * 140
    slot.nodeY = 80

    empty = slot.create('constantTOP', 'empty')
    _set_par(empty, 'colorr', expr=CANVAS_BG_R_EXPR)
    _set_par(empty, 'colorg', expr=CANVAS_BG_G_EXPR)
    _set_par(empty, 'colorb', expr=CANVAS_BG_B_EXPR)
    _set_par(empty, 'alpha', 1)
    _bind_canvas_res(empty)

    chain_src = None
    if layer_idx < MAX_LAYERS:
        upstream = slot.create('selectTOP', 'upstream')
        _bind_canvas_res(upstream)
        _set_par(upstream, 'top', empty)
        chain_src = upstream

    pass_sel = slot.create('selectTOP', 'pass')
    _bind_canvas_res(pass_sel)
    if chain_src is not None:
        _set_par(pass_sel, 'top', expr="op('upstream')")
    else:
        _set_par(pass_sel, 'top', empty)

    video = slot.create('moviefileinTOP', 'video')
    _set_par(video, 'outputresolution', 'useinput')
    try:
        video.par.playmode = 'locked'
    except Exception:
        pass
    try:
        video.allowCooking = False
    except Exception:
        _set_par(video, 'play', False)
    _set_par(video, 'preload', True)

    video_fit = slot.create('fitTOP', 'video_fit')
    _bind_canvas_res(video_fit)
    _set_par(video_fit, 'fit', 'fitoutside')

    video_canvas_fit = slot.create('fitTOP', 'video_canvas_fit')
    _bind_canvas_res(video_canvas_fit)
    _set_par(video_canvas_fit, 'fit', 'fitoutside')

    tox = slot.create('baseCOMP', 'tox')
    tox.par.enableexternaltox = True
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

    tox_fit = slot.create('fitTOP', 'tox_fit')
    _bind_canvas_res(tox_fit)
    _set_par(tox_fit, 'fit', 'fitoutside')

    pick = slot.create('switchTOP', 'pick')
    _set_par(pick, 'index', 0)
    empty.outputConnectors[0].connect(pick.inputConnectors[0])
    video.outputConnectors[0].connect(video_fit.inputConnectors[0])
    video_fit.outputConnectors[0].connect(video_canvas_fit.inputConnectors[0])
    video_canvas_fit.outputConnectors[0].connect(pick.inputConnectors[1])
    tox_pick.outputConnectors[0].connect(tox_fit.inputConnectors[0])
    tox_fit.outputConnectors[0].connect(pick.inputConnectors[2])
    over = slot.create('overTOP', 'layer_over')
    _bind_canvas_res(over)
    opacity = slot.create('levelTOP', 'layer_opacity')
    _bind_canvas_res(opacity)
    _set_par(opacity, 'opacity', 1)
    for pname in ('premultrgbbyalpha', 'postmultalpha', 'multiplyalpha'):
        try:
            getattr(opacity.par, pname).val = True
            break
        except Exception:
            continue
    out = slot.create('outTOP', 'out1')
    pick.outputConnectors[0].connect(opacity.inputConnectors[0])
    opacity.outputConnectors[0].connect(over.inputConnectors[0])
    pass_sel.outputConnectors[0].connect(over.inputConnectors[1])
    over.outputConnectors[0].connect(out.inputConnectors[0])
    return out


def _build_layer(slots, layer_idx):
    layer = slots.create('baseCOMP', 'layer_{}'.format(layer_idx))
    layer.nodeX = 0
    layer.nodeY = layer_idx * 120

    black = layer.create('constantTOP', 'black')
    _set_par(black, 'colorr', expr=CANVAS_BG_R_EXPR)
    _set_par(black, 'colorg', expr=CANVAS_BG_G_EXPR)
    _set_par(black, 'colorb', expr=CANVAS_BG_B_EXPR)
    _set_par(black, 'alpha', 1)
    _bind_canvas_res(black)

    switch = layer.create('switchTOP', 'switch')
    _set_par(switch, 'index', 0)
    black.outputConnectors[0].connect(switch.inputConnectors[0])

    for col in range(1, NUM_COLS + 1):
        out = _build_slot(layer, col, layer_idx)
        out.outputConnectors[0].connect(switch.inputConnectors[col])

    layer.create('outTOP', 'out1')
    switch.outputConnectors[0].connect(layer.op('out1').inputConnectors[0])
    return layer


def _bind_canvas_res(top):
    """Bind TOP output resolution to /settings canvas size."""
    if top is None:
        return
    _set_par(top, 'outputresolution', 'custom')
    _set_par(top, 'resolutionw', expr=CANVAS_W_EXPR)
    _set_par(top, 'resolutionh', expr=CANVAS_H_EXPR)
    try:
        top.par.resmult = False
    except Exception:
        pass


def _ensure_reload_scripts_maintenance(settings):
    """Reload Scripts pulse at the bottom of the About tab."""
    if settings is None:
        return False
    needs_create = True
    pulse = None
    try:
        par = settings.par.Reloadscripts
        try:
            page = par.page.name if hasattr(par.page, 'name') else str(par.page)
        except Exception:
            page = ''
        if page == 'About':
            needs_create = False
            pulse = par
        else:
            par.destroy()
    except AttributeError:
        pass
    except Exception:
        try:
            settings.par.Reloadscripts.destroy()
        except Exception:
            pass
    about_page = None
    for pg in settings.customPages:
        if pg.name == 'About':
            about_page = pg
            break
    if about_page is None:
        about_page = settings.appendCustomPage('About')
    if needs_create:
        pulse = about_page.appendPulse('Reloadscripts', label='Reload Scripts (Dev)')
    if pulse is None:
        return False
    try:
        pulse.label = 'Reload Scripts (Dev)'
        settings.par.Reloadscripts.label = 'Reload Scripts (Dev)'
    except Exception:
        pass
    for name, index in (
        ('Aboutbrand', 0),
        ('Aboutinfo', 1),
        ('Reloadscripts', 2),
    ):
        try:
            getattr(settings.par, name).order = float(index)
        except Exception:
            pass
    pe = settings.op('settings_parexec')
    if pe is not None:
        try:
            pars = str(pe.par.pars.eval()).split()
            for name in (
                'Screenshotfolder', 'Takescreenshot', 'Recordingfolder',
                'Recordingquality', 'Recordaudio', 'Togglerecording', 'Reloadscripts',
            ):
                if name not in pars:
                    pars.append(name)
            pe.par.pars = ' '.join(pars)
            pe.par.onpulse = True
            pe.par.active = True
        except Exception:
            pass
    return True


def _performance_mode_ui_grid(ui):
    """Grid body lives under ui/grid_stack/grid in current layouts."""
    if ui is None:
        return None
    stack = ui.op('grid_stack')
    if stack is not None:
        grid = stack.op('grid')
        if grid is not None:
            return grid
    return ui.op('grid')


def _performance_mode_ready(root):
    """True when launcher has UI container, logic, slots, and grid."""
    if root is None:
        return False
    ui = root.op('ui')
    # op.type is the short name (e.g. 'container'), not 'containerCOMP'.
    if ui is None or getattr(ui, 'family', '') != 'COMP':
        return False
    if root.op('logic') is None or root.op('slots') is None:
        return False
    return _performance_mode_ui_grid(ui) is not None


def _performance_mode_patchable(root):
    """True when script DATs can be updated without destroying the comp."""
    if root is None:
        return False
    return root.op('logic') is not None


def _heal_perform_window(comp_path=None):
    """Bind /perform to performance_mode/ui; clear winop if launcher is incomplete."""
    comp_path = comp_path or DEFAULT_COMP
    root = op(comp_path) if comp_path else None
    perform = op('/perform')
    if perform is None:
        return False
    if not _performance_mode_ready(root):
        print(
            'Perform: performance_mode is incomplete (missing ui/logic/slots). '
            'Pulse Reload Scripts once to rebuild, or run build_simple_grid(open_perform=True).'
        )
        return False
    ui = root.op('ui')
    try:
        winop = perform.par.winop.eval()
        winop_path = winop.path if hasattr(winop, 'path') else str(winop or '')
        bad = winop_path != ui.path
    except Exception:
        bad = True
    if bad:
        try:
            perform.par.winop = ui.path
            perform.par.interact = True
            perform.par.drawwindow = True
            perform.par.winw = UI_W
            perform.par.winh = UI_H
        except Exception:
            pass
    try:
        logic = root.op('logic')
        mod = logic.module if logic is not None and hasattr(logic, 'module') else None
        if mod is not None:
            if hasattr(mod, 'configure_audio_analysis'):
                mod.configure_audio_analysis()
            if hasattr(mod, '_layout_perform_ui'):
                mod._layout_perform_ui()
            if hasattr(mod, '_refresh_panel_exec_panels'):
                mod._refresh_panel_exec_panels()
        settings_panel = ui.op('settings_params') if ui is not None else None
        if settings_panel is not None and mod is not None:
            if hasattr(mod, '_refresh_settings_params_panel'):
                mod._refresh_settings_params_panel()
            elif hasattr(mod, '_configure_settings_params_panel'):
                mod._configure_settings_params_panel(settings_panel)
    except Exception:
        pass
    return True
