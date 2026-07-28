def _depth_to_root(from_op):
    n = 0
    p = from_op
    root = _root()
    while p is not None and p != root:
        n += 1
        p = p.parent()
    return n


def _cell_dims(cell):
    w = int(float(cell.par.w.eval())) or 96
    h = int(float(cell.par.h.eval())) or 64
    return w, h


def _cell_thumb_h(cell):
    _, h = _cell_dims(cell)
    return max(24, h - CELL_LABEL_H)


def _apply_grid_font(txt):
    try:
        txt.par.font = TD_FONT
        txt.par.fontautosize = 'off'
        txt.par.fontsizex = GRID_FONT_SIZE
        txt.par.fontsizey = GRID_FONT_SIZE
        txt.par.keepfontratio = True
    except Exception:
        pass


def _style_name_bar(txt, w, text='', highlight=False, missing=False):
    try:
        txt.par.text.mode = ParMode.CONSTANT
    except Exception:
        pass
    label = text or chr(183)
    txt.par.text = label
    txt.par.resolutionw = max(32, int(w))
    txt.par.resolutionh = CELL_LABEL_H
    try:
        txt.par.fontautosize = 'off'
        txt.par.fontsizex = CELL_NAME_FONT_SIZE
        txt.par.fontsizey = CELL_NAME_FONT_SIZE
        txt.par.keepfontratio = True
    except Exception:
        pass
    txt.par.bgalpha = 1.0
    txt.par.alignx = 'left'
    txt.par.aligny = 'center'
    try:
        txt.par.textoffsetx = 4
    except Exception:
        pass
    if missing:
        txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = (0.95, 0.45, 0.35)
    elif highlight:
        txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = CELL_RING_CR, CELL_RING_CG, CELL_RING_CB
    else:
        txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = UI_TEXT_SECONDARY
    txt.par.bgcolorr, txt.par.bgcolorg, txt.par.bgcolorb = UI_NAME_BAR_BG
    try:
        txt.cook(force=True)
    except Exception:
        pass


FREEZE_BADGE_W = 18


def _cell_missing(layer, col):
    """Missing status wins over freeze, including legacy rows labelled missing."""
    try:
        clip_type, path = _cell_content(layer, col)
        if bool(path) and _asset_file_missing(path, clip_type):
            return True
    except Exception:
        pass
    try:
        tbl = _table()
        idx = _find(tbl, int(layer), int(col)) if tbl is not None else None
        return idx is not None and str(tbl[idx, 'label']).strip().lower() == 'missing'
    except Exception:
        return False


def _style_freeze_badge(txt, missing=False):
    if txt is None:
        return
    try:
        txt.par.text.mode = ParMode.CONSTANT
    except Exception:
        pass
    try:
        txt.par.text = '!' if missing else 'F'
        txt.par.resolutionw = FREEZE_BADGE_W
        txt.par.resolutionh = CELL_LABEL_H
        txt.par.font = TD_FONT
        txt.par.fontautosize = 'off'
        txt.par.fontsizex = CELL_NAME_FONT_SIZE
        txt.par.fontsizey = CELL_NAME_FONT_SIZE
        txt.par.keepfontratio = True
        txt.par.alignx = 'center'
        txt.par.aligny = 'center'
        txt.par.bgalpha = 1.0
        txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = (1.0, 1.0, 1.0)
        if missing:
            txt.par.bgcolorr, txt.par.bgcolorg, txt.par.bgcolorb = (0.75, 0.12, 0.08)
        else:
            txt.par.bgcolorr, txt.par.bgcolorg, txt.par.bgcolorb = (0.0, 0.0, 0.0)
    except Exception:
        pass


def _ensure_freeze_badge(cell, missing=False):
    if cell is None:
        return None
    badge = cell.op('freeze_badge')
    if badge is None:
        badge = cell.create('containerCOMP', 'freeze_badge')
    try:
        badge.par.hmode = 'fixed'
        badge.par.vmode = 'fixed'
        badge.par.align = 'none'
        badge.par.clickthrough = True
        badge.par.drop = 'dropparent'
        badge.par.drag = 'dragno'
        badge.par.w = FREEZE_BADGE_W
        badge.par.h = CELL_LABEL_H
        badge.par.bgalpha = 0.0
    except Exception:
        pass
    txt = badge.op('badge_text')
    if txt is None:
        txt = badge.create('textTOP', 'badge_text')
    _style_freeze_badge(txt, missing=missing)
    try:
        badge.par.top = txt
        badge.par.topfill = 'fill'
    except Exception:
        pass
    return badge


def _layout_freeze_badge(cell, layer=None, col=None, pad=0):
    missing = False
    if layer is not None and col is not None:
        try:
            missing = _cell_missing(layer, col)
        except Exception:
            pass
    badge = _ensure_freeze_badge(cell, missing=missing)
    if badge is None:
        return
    w, _h = _cell_dims(cell)
    thumb_h = max(24, _cell_thumb_h(cell) - int(pad or 0))
    inner_w = max(32, w - int(pad or 0) * 2)
    try:
        badge.par.x = int(pad or 0) + max(0, inner_w - FREEZE_BADGE_W)
        badge.par.y = int(pad or 0) + thumb_h
        badge.par.w = FREEZE_BADGE_W
        badge.par.h = CELL_LABEL_H
        if layer is not None and col is not None:
            badge.par.display = missing or bool(_cell_frozen(layer, col))
    except Exception:
        pass


def _apply_cell_ring(cell, layer, col, active_col, active_layer):
    """Single cyan ring on cells included in the live composition."""
    if cell is None:
        return
    layer, col = int(layer), int(col)
    selected = _is_composition_cell(layer, col)
    try:
        if selected:
            bw = CELL_RING_W
            br, bg, bb = CELL_RING_CR, CELL_RING_CG, CELL_RING_CB
            cell.par.bgcolorr, cell.par.bgcolorg, cell.par.bgcolorb = (
                CELL_BG_SELECTED_R, CELL_BG_SELECTED_G, CELL_BG_SELECTED_B)
        else:
            bw = 'off'
            br, bg, bb = CELL_RING_IDLE_CR, CELL_RING_IDLE_CG, CELL_RING_IDLE_CB
            cell.par.bgcolorr, cell.par.bgcolorg, cell.par.bgcolorb = (
                CELL_BG_IDLE_R, CELL_BG_IDLE_G, CELL_BG_IDLE_B)
        for pname in ('leftborder', 'rightborder', 'topborder', 'bottomborder'):
            getattr(cell.par, pname).val = bw
        cell.par.borderbr = br
        cell.par.borderbg = bg
        cell.par.borderbb = bb
        cell.par.borderbalpha = 1.0
        cell.par.marginl = 0
        cell.par.marginr = 0
        cell.par.margint = 0
        cell.par.marginb = 0
        cell.par.bgalpha = 0.0
        cell.par.borderover = True
        _layout_cell_inner(cell, 0)
        _layout_freeze_badge(cell, layer, col, 0)
    except Exception:
        pass


def _cell_ring_pad(layer, col):
    return 0


def _thumbnail_quality():
    try:
        s = _settings()
        if s is not None:
            q = int(float(s.par.Thumbquality.eval()))
            return max(25, min(100, q))
    except Exception:
        pass
    return 75


def _thumbnail_res(w, h):
    q = _thumbnail_quality()
    return max(16, int(round(float(w) * q / 100.0))), max(16, int(round(float(h) * q / 100.0)))


def _layout_cell_geometry(cell, layer, col, cell_w, thumb_h, cell_h):
    """Position cell + thumb + name for current grid metrics (respects composition ring)."""
    if cell is None:
        return
    layer, col = int(layer), int(col)
    try:
        cell.par.x = _col_x(col, cell_w)
        cell.par.w = cell_w
        cell.par.h = cell_h
        cell.par.hmode = 'fixed'
        cell.par.vmode = 'fixed'
        cell.par.align = 'none'
    except Exception:
        pass
    pad = _cell_ring_pad(layer, col)
    _layout_cell_inner(cell, pad)
    thumb = cell.op('cell_thumb')
    name = cell.op('cell_name')
    inner_w = max(32, int(cell_w) - pad * 2)
    inner_thumb_h = max(16, int(thumb_h) - pad)
    rw, rh = _thumbnail_res(inner_w, inner_thumb_h)
    if thumb is not None:
        try:
            thumb.par.topfill = CELL_TOPFILL
            thumb.par.align = 'none'
        except Exception:
            pass
        empty = thumb.op('empty')
        preview = thumb.op('preview')
        if empty is not None:
            empty.par.resolutionw = rw
            empty.par.resolutionh = rh
            _style_empty_thumb(empty)
        if preview is not None:
            preview.par.resolutionw = rw
            preview.par.resolutionh = rh
    if name is not None:
        try:
            name.par.topfill = 'fill'
            name.par.align = 'none'
        except Exception:
            pass


def _layout_cell_inner(cell, pad=0):
    """Inset thumb + name when selection ring padding is active."""
    if cell is None:
        return
    pad = int(pad or 0)
    w, h = _cell_dims(cell)
    thumb_h = max(24, _cell_thumb_h(cell) - pad)
    inner_w = max(32, w - pad * 2)
    rw, rh = _thumbnail_res(inner_w, thumb_h)
    thumb = cell.op('cell_thumb')
    name = cell.op('cell_name')
    if thumb is not None:
        try:
            thumb.par.x = pad
            thumb.par.w = inner_w
            thumb.par.h = thumb_h
            thumb.par.y = pad
            empty = thumb.op('empty')
            preview = thumb.op('preview')
            if empty is not None:
                empty.par.resolutionw = rw
                empty.par.resolutionh = rh
            if preview is not None:
                preview.par.resolutionw = rw
                preview.par.resolutionh = rh
        except Exception:
            pass
    if name is not None:
        try:
            name.par.x = pad
            name.par.w = inner_w
            name.par.h = CELL_LABEL_H
            name.par.y = pad + thumb_h
        except Exception:
            pass
    _layout_freeze_badge(cell, None, None, pad)


def _style_empty_thumb(empty):
    """Dark grey placeholder matching TD panel / empty cell UI."""
    if empty is None:
        return
    try:
        empty.par.colorr = EMPTY_CELL_R
        empty.par.colorg = EMPTY_CELL_G
        empty.par.colorb = EMPTY_CELL_B
        empty.par.alpha = 1.0
    except Exception:
        pass


def _style_black_thumb(empty):
    """Opaque black fallback for loaded cells whose live preview is unavailable."""
    if empty is None:
        return
    try:
        empty.par.colorr = 0
        empty.par.colorg = 0
        empty.par.colorb = 0
        empty.par.alpha = 1.0
    except Exception:
        pass


def _set_thumb_canvas_res(top, fallback_w, fallback_h):
    """Use canvas aspect for black loaded-preview fallback thumbnails."""
    if top is None:
        return
    try:
        top.par.resolutionw = max(1, int(_canvas_w()))
        top.par.resolutionh = max(1, int(_canvas_h()))
        return
    except Exception:
        pass
    try:
        top.par.resolutionw = max(32, int(fallback_w))
        top.par.resolutionh = max(16, int(fallback_h))
    except Exception:
        pass


def _show_cell_black_preview(cell, preview):
    """Loaded clip/source exists, but no thumbnail can cook yet."""
    if cell is None or preview is None:
        return
    try:
        thumb = preview.parent()
        empty = thumb.op('empty') if thumb is not None else None
        if empty is None and thumb is not None:
            empty = thumb.create('constantTOP', 'empty')
        w, h = _cell_dims(cell)
        thumb_h = _cell_thumb_h(cell)
        rw, rh = _thumbnail_res(w, thumb_h)
        _style_black_thumb(empty)
        _set_thumb_canvas_res(empty, rw, rh)
        preview.par.top = empty
        preview.par.top.mode = ParMode.CONSTANT
        preview.par.outputresolution = 'custom'
        _set_thumb_canvas_res(preview, rw, rh)
        if thumb is not None:
            thumb.par.bgcolorr = EMPTY_CELL_R
            thumb.par.bgcolorg = EMPTY_CELL_G
            thumb.par.bgcolorb = EMPTY_CELL_B
            thumb.par.top = preview
            thumb.par.topfill = CELL_TOPFILL
    except Exception:
        pass


def _cleanup_cell_thumb(thumb):
    """Remove duplicate preview/empty/fit TOPs left by older layout code."""
    if thumb is None:
        return
    keep = {'preview', 'empty', 'preview_fit'}
    for ch in list(thumb.children):
        if not getattr(ch, 'name', None):
            continue
        n = ch.name
        if n in keep:
            continue
        if n.startswith('preview') or n.startswith('empty'):
            try:
                ch.destroy()
            except Exception:
                pass
    fit = thumb.op('preview_fit')
    if fit is not None:
        try:
            fit.destroy()
        except Exception:
            pass


def _slot_preview_top(layer, col, clip_type):
    """Slot TOP for grid thumbnail (direct op ref — reliable in selectTOP)."""
    root = _root()
    if root is None:
        return None
    if clip_type == 'video':
        slot = root.op('slots/layer_{}/col_{}'.format(layer, col))
        return (slot.op('video_canvas_fit') or slot.op('video_fit')) if slot else None
    if clip_type == 'tox':
        slot = root.op('slots/layer_{}/col_{}'.format(layer, col))
        return slot.op('tox_fit') if slot else None
    return None


def _ensure_cell_layout(cell):
    """Cell layout: thumbnail on top, name strip below."""
    w, h = _cell_dims(cell)
    thumb_h = _cell_thumb_h(cell)
    thumb = cell.op('cell_thumb')
    if thumb is None:
        thumb = cell.create('containerCOMP', 'cell_thumb')
    name = cell.op('cell_name')
    if name is None:
        name = cell.create('containerCOMP', 'cell_name')
    for ch in (thumb, name):
        ch.par.w = w
        ch.par.hmode = 'fixed'
        ch.par.vmode = 'fixed'
        ch.par.align = 'none'
        try:
            ch.par.clickthrough = True
            ch.par.drop = 'dropno'
        except Exception:
            pass
    thumb.par.h = thumb_h
    thumb.par.y = 0
    try:
        thumb.par.bgcolorr, thumb.par.bgcolorg, thumb.par.bgcolorb = (
            EMPTY_CELL_R, EMPTY_CELL_G, EMPTY_CELL_B)
        thumb.par.bgalpha = 1.0
    except Exception:
        pass
    name.par.h = CELL_LABEL_H
    name.par.y = thumb_h
    name.par.bgcolorr, name.par.bgcolorg, name.par.bgcolorb = UI_NAME_BAR_BG
    try:
        name.par.bgalpha = 1.0
    except Exception:
        pass
    _cleanup_cell_thumb(thumb)
    empty = thumb.op('empty')
    preview = thumb.op('preview')
    if preview is None:
        if empty is None:
            empty = thumb.create('constantTOP', 'empty')
        preview = thumb.create('selectTOP', 'preview')
        preview.par.top = empty
    elif empty is None:
        empty = thumb.create('constantTOP', 'empty')
    _style_empty_thumb(empty)
    rw, rh = _thumbnail_res(w, thumb_h)
    empty.par.resolutionw = max(32, rw)
    empty.par.resolutionh = max(16, rh)
    preview.par.resolutionw = max(32, rw)
    preview.par.resolutionh = max(16, rh)
    try:
        thumb.par.top = preview
        thumb.par.topfill = CELL_TOPFILL
    except Exception:
        pass
    txt = name.op('label_text')
    if txt is None:
        txt = name.create('textTOP', 'label_text')
    old_txt = cell.op('label_text')
    if old_txt is not None and old_txt != txt:
        try:
            old_txt.destroy()
        except Exception:
            pass
    name.par.top = txt
    name.par.topfill = 'fill'
    try:
        cell.par.top = ''
    except Exception:
        pass
    _layout_freeze_badge(cell)
    return thumb, name, preview, txt


def _reset_cell_preview(layer, col):
    """Blank thumbnail when cell has no loaded clip (clears stale pass-through)."""
    r = _root()
    cell = _grid_cell(r, layer, col)
    if cell is None:
        return
    thumb, _, preview, txt = _ensure_cell_layout(cell)
    if preview is not None:
        try:
            empty = preview.parent().op('empty')
            if empty is not None:
                _style_empty_thumb(empty)
                for node in (empty, preview):
                    try:
                        node.lock = False
                        node.bypass = False
                    except Exception:
                        pass
                preview.par.top = empty
                preview.par.top.mode = ParMode.CONSTANT
                empty.cook(force=True)
                preview.cook(force=True)
                if thumb is not None:
                    # Point the panel directly at the blank TOP so it cannot
                    # retain the Select TOP's previously cooked thumbnail.
                    thumb.par.top = empty
                    thumb.par.topfill = CELL_TOPFILL
                    thumb.cook(force=True)
        except Exception:
            pass
    if txt is not None:
        w = int(float(cell.par.w.eval())) or CELL_W
        _style_name_bar(txt, w, chr(183))
    _layout_freeze_badge(cell, layer, col)
    try:
        _THUMB_LAST_REFRESH.pop((int(layer), int(col)), None)
    except Exception:
        pass


def _reset_empty_grid_previews():
    """Force every empty cell panel back to its blank thumbnail."""
    for layer in range(1, _num_layers() + 1):
        for col in range(1, _num_cols() + 1):
            _ctype, path = _get(layer, col)
            if not str(path or '').strip():
                _reset_cell_preview(layer, col)


def _thumbnail_fps():
    try:
        s = _settings()
        if s is not None:
            return max(0, int(float(s.par.Thumbfps.eval())))
    except Exception:
        pass
    return 5


def _thumbnail_refresh_allowed(layer, col, force=False):
    if force:
        return True
    fps = _thumbnail_fps()
    if fps <= 0:
        return False
    if fps >= 60:
        return True
    try:
        now = float(absTime.seconds)
    except Exception:
        try:
            now = float(_now_seconds())
        except Exception:
            return True
    key = (int(layer), int(col))
    last = _THUMB_LAST_REFRESH.get(key)
    if last is not None and (now - float(last)) < (1.0 / float(fps)):
        return False
    _THUMB_LAST_REFRESH[key] = now
    return True


def _refresh_cell_preview(layer, col, force_video_prime=False, force=False):
    r = _root()
    cell = _grid_cell(r, layer, col)
    if cell is None:
        return
    thumb, _, preview, _ = _ensure_cell_layout(cell)
    clip_type, path = _cell_content(layer, col)
    if preview is None or not path:
        _reset_cell_preview(layer, col)
        return
    if clip_type == 'tox' and not _is_composition_cell(layer, col):
        _show_cell_black_preview(cell, preview)
        return
    if not _thumbnail_refresh_allowed(layer, col, force=force or force_video_prime):
        return
    if clip_type == 'video':
        slot = _slot(layer, col)
        if slot is not None:
            _prime_video_for_thumbnail(slot, layer, col, force=force_video_prime)
    src = _slot_preview_top(layer, col, clip_type)
    if src is None:
        _show_cell_black_preview(cell, preview)
        return
    try:
        src.cook(force=True)
    except Exception:
        pass
    try:
        preview.par.top = src
        try:
            preview.par.top.mode = ParMode.CONSTANT
        except Exception:
            pass
        if thumb is not None:
            thumb.par.top = preview
            thumb.par.topfill = CELL_TOPFILL
            try:
                thumb.cook(force=True)
            except Exception:
                pass
    except Exception as exc:
        print('Cell preview failed L{} C{}: {}'.format(layer, col, exc))


def _refresh_cell_display(layer, col, force_video_prime=False):
    """Update one cell's thumbnail, name strip, and selection ring."""
    r = _root()
    if r is None:
        return
    cell = _grid_cell(r, layer, col)
    if cell is None:
        return
    clip_type, path = _cell_content(layer, col)
    _, _, _, label = _ensure_cell_layout(cell)
    try:
        active_col = int(float(r.par.Activecolumn.eval()))
        active_layer = int(float(r.par.Activelayer.eval()))
    except Exception:
        active_col, active_layer = 1, 1
    selected = _is_composition_cell(layer, col)
    if label is not None:
        w = int(float(cell.par.w.eval())) or CELL_W
        pad = 0
        inner_w = max(32, w - pad * 2)
        _style_name_bar(
            label, inner_w, _cell_display_name(layer, col), highlight=selected,
            missing=_cell_missing(layer, col),
        )
    _layout_freeze_badge(cell, layer, col)
    _sync_cell_label_row(layer, col)
    _apply_cell_ring(cell, layer, col, active_col, active_layer)
    if path:
        _refresh_cell_preview(layer, col, force_video_prime=force_video_prime, force=force_video_prime)
    else:
        _reset_cell_preview(layer, col)


def _refresh_cell_selection_display(layer, col):
    """Refresh one cell's selection styling without cooking its preview."""
    r = _root()
    if r is None:
        return
    cell = _grid_cell(r, layer, col)
    if cell is None:
        return
    _, _, _, label = _ensure_cell_layout(cell)
    selected = _is_composition_cell(layer, col)
    clip_type, path = _cell_content(layer, col)
    if label is not None:
        w = int(float(cell.par.w.eval())) or CELL_W
        _style_name_bar(
            label,
            max(32, w),
            _cell_display_name(layer, col),
            highlight=selected,
            missing=_cell_missing(layer, col),
        )
    try:
        active_col = int(float(r.par.Activecolumn.eval()))
        active_layer = int(float(r.par.Activelayer.eval()))
    except Exception:
        active_col, active_layer = 1, 1
    _apply_cell_ring(cell, layer, col, active_col, active_layer)


def _sync_cell_label_row(layer, col):
    tbl = _table()
    if tbl is None:
        return
    idx = _find(tbl, layer, col)
    if idx is None:
        return
    try:
        tbl[idx, 'label'] = _cell_display_name(layer, col)
    except Exception:
        pass


def _ui_live_cells():
    try:
        return set((int(layer), int(col)) for layer, col in _composition_deps())
    except Exception:
        cells = set()
        try:
            for layer in range(1, _num_layers() + 1):
                cells.add((layer, _get_layer_src_col(layer)))
        except Exception:
            pass
        return cells


def _ui_visible_cols(buffer=2):
    ncols = _num_cols()
    if ncols <= 0:
        return set()
    visible = min(ncols, max(1, int(VISIBLE_COLS)))
    scroll = 0.0
    r = _root()
    stack = _ui_grid_stack(r) if r is not None else None
    if stack is not None:
        for name in ('scrollu', 'scrollx', 'u'):
            try:
                scroll = float(getattr(stack.panel, name))
                break
            except Exception:
                pass
    scroll = max(0.0, min(1.0, scroll))
    first = 1 + int(round(scroll * max(0, ncols - visible)))
    first = max(1, min(ncols, first - int(buffer)))
    last = min(ncols, first + visible + int(buffer) * 2 - 1)
    return set(range(first, last + 1))


def _ui_refresh_cols(extra_cols=None, full=False):
    global _LAST_UI_LIVE_CELLS
    ncols = _num_cols()
    if full or ncols <= (VISIBLE_COLS + 4):
        cols = set(range(1, ncols + 1))
    else:
        cols = set(_ui_visible_cols())
    live_cells = _ui_live_cells()
    prev_live = set(_LAST_UI_LIVE_CELLS or set())
    for _layer, col in live_cells | prev_live:
        cols.add(int(col))
    r = _root()
    if r is not None:
        for pname in ('Activecolumn', 'Selectedcol'):
            try:
                cols.add(int(float(getattr(r.par, pname).eval())))
            except Exception:
                pass
    if extra_cols is not None:
        try:
            for col in extra_cols:
                cols.add(int(col))
        except TypeError:
            try:
                cols.add(int(extra_cols))
            except Exception:
                pass
    cols = set(c for c in cols if 1 <= int(c) <= ncols)
    _LAST_UI_LIVE_CELLS = live_cells
    return cols


def _refresh_ui(cols=None, full=False):
    r = _root()
    tbl = _table()
    if r is None or tbl is None:
        return
    active_col = int(float(r.par.Activecolumn.eval()))
    active_layer = int(float(r.par.Activelayer.eval()))
    refresh_cols = _ui_refresh_cols(cols, full=full)
    for layer in range(1, _num_layers() + 1):
        for col in sorted(refresh_cols):
            cell = _grid_cell(r, layer, col)
            if cell is None:
                continue
            clip_type, path = _cell_content(layer, col)
            _, _, _, label = _ensure_cell_layout(cell)
            selected = _is_composition_cell(layer, col)
            if label is not None:
                w = int(float(cell.par.w.eval())) or 96
                pad = 0
                inner_w = max(32, w - pad * 2)
                _style_name_bar(
                    label, inner_w, _cell_display_name(layer, col), highlight=selected,
                    missing=_cell_missing(layer, col),
                )
            _layout_freeze_badge(cell, layer, col)
            _sync_cell_label_row(layer, col)
            _apply_cell_ring(cell, layer, col, active_col, active_layer)
            if path:
                _refresh_cell_preview(layer, col)
            else:
                _reset_cell_preview(layer, col)
    try:
        parts = []
        for layer in range(_num_layers(), 0, -1):
            sc = _get_layer_src_col(layer)
            parts.append('{}:c{}'.format(_layer_label(layer), sc))
        r.par.Status = 'Scene {} | {}'.format(_active_scene(), ' '.join(parts))
    except Exception:
        pass


def _scene_has_content(scene=None):
    scene = _active_scene() if scene is None else int(scene)
    tbl = _table()
    if tbl is None:
        return False
    for i in range(1, tbl.numRows):
        if int(tbl[i, 'scene']) != scene:
            continue
        if str(tbl[i, 'path']).strip():
            return True
    return False


def _prep_cell_slot(layer, col, play=True, restart_video=False):
    """Load/play one grid cell slot (used for cross-column chain sources)."""
    layer, col = int(layer), int(col)
    slot = _slot(layer, col)
    if slot is None:
        return
    _ensure_slot_chain(slot, layer)
    ctype, path = _get(layer, col)
    pick = slot.op('pick')
    if not path or not _valid_clip_type(ctype):
        _route_slot_pass_only(slot)
        _pause_slot(slot, on=False, clip_type='')
        return
    slot_live = _video_slot_should_play(layer, col)
    _pause_slot(
        slot,
        on=bool(play),
        keep_tox_cooking=_tox_cell_keep_cooking(layer, col, ctype, path, slot_live, slot),
        clip_type=ctype,
    )
    if ctype == 'video':
        _wire_video(
            slot, path, play=play,
            resume=bool(restart_video and slot_live),
        )
        _route_slot_content(slot, 1, layer)
    else:
        _wire_tox(slot, path, layer, col)
        _route_slot_content(slot, 2, layer)
    level = slot.op('layer_opacity')
    if level is not None:
        _set_level_opacity(level, layer_opacity(layer))
