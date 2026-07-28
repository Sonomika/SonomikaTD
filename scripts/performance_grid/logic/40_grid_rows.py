def _refresh_panel_exec_panels():
    r = _root()
    if r is None:
        return
    pe = r.op('panel_exec')
    grid = _ui_grid(r)
    if pe is None or grid is None:
        return
    paths = []
    ui = r.op('ui')
    stack = _ui_grid_stack(r)
    try:
        if stack is not None:
            paths.append(stack.path)
    except Exception:
        pass
    try:
        paths.append(grid.path)
    except Exception:
        pass
    settings_panel = ui.op('settings_params') if ui else None
    if settings_panel is not None:
        paths.append(settings_panel.path)
    tab_bar = ui.op('params_tab_bar') if ui else None
    if tab_bar is not None:
        paths.append(tab_bar.path)
        for name in ('params_tab_layer', 'params_tab_global'):
            btn = tab_bar.op(name)
            if btn is not None:
                paths.append(btn.path)
    gfx_panel = ui.op('global_fx_panel') if ui else None
    if gfx_panel is not None:
        paths.append(gfx_panel.path)
        for ch in gfx_panel.children:
            if ch.isCOMP and ch.name.startswith('gfx_row_'):
                paths.append(ch.path)
                for sub in ch.children:
                    if sub.isCOMP:
                        paths.append(sub.path)
    lfx_panel = ui.op('layer_fx_panel') if ui else None
    if lfx_panel is not None:
        paths.append(lfx_panel.path)
        for ch in lfx_panel.children:
            if ch.isCOMP and ch.name.startswith('lfx_row_'):
                paths.append(ch.path)
                for sub in ch.children:
                    if sub.isCOMP:
                        paths.append(sub.path)
    map_sec = ui.op('map_control_section') if ui else None
    if map_sec is not None:
        def _append_comp_tree(comp, depth=0, max_depth=8):
            if comp is None or depth > max_depth:
                return
            try:
                if comp.isCOMP:
                    paths.append(comp.path)
                    for ch in comp.children:
                        if ch.isCOMP:
                            _append_comp_tree(ch, depth + 1, max_depth)
            except Exception:
                pass

        _append_comp_tree(map_sec)
    bar = ui.op('scene_bar') if ui else None
    if bar is not None:
        for ch in bar.children:
            if ch.isCOMP:
                paths.append(ch.path)
        bpm = bar.op('scene_bpm')
        if bpm is not None:
            for name in ('bpm_up', 'bpm_down', 'bpm_value'):
                child = bpm.op(name)
                if child is not None:
                    paths.append(child.path)
    audio_strip = ui.op('audio_band_strip') if ui else None
    if audio_strip is not None and _audio_histogram_visible():
        paths.append(audio_strip.path)
        view = audio_strip.op('audio_band_view')
        if view is not None:
            paths.append(view.path)
            for ch in view.children:
                if ch.isCOMP and ch.name in (
                    'band_shade_bass', 'band_shade_high',
                    'band_handle_bass_lo', 'band_handle_bass_hi',
                    'band_handle_high_lo', 'band_handle_high_hi',
                    'band_tag_bass', 'band_tag_high',
                    'band_hit_bass', 'band_hit_high',
                    'band_thresh_hit_bass', 'band_thresh_hit_high',
                    'thresh_slider_bass', 'thresh_slider_high',
                    'thresh_slider_peak',
                ):
                    paths.append(ch.path)
        peak_bar = audio_strip.op('peak_thresh_bar')
        if peak_bar is not None:
            paths.append(peak_bar.path)
            hit = peak_bar.op('hit')
            if hit is not None:
                paths.append(hit.path)
        side = audio_strip.op('analysis_side')
        if side is not None:
            for meter_name in ('meter_low', 'meter_high', 'meter_peak'):
                meter = side.op(meter_name)
                if meter is None:
                    continue
                rev = meter.op('rev')
                if rev is not None:
                    paths.append(rev.path)
    audio_monitor = r.op(AUDIO_MONITOR_NAME) if r is not None else None
    if audio_monitor is not None and _audio_histogram_visible():
        paths.append(audio_monitor.path)
        view = audio_monitor.op('audio_band_view')
        if view is not None:
            paths.append(view.path)
            for ch in view.children:
                if ch.isCOMP and ch.name in (
                    'band_shade_bass', 'band_shade_high',
                    'band_handle_bass_lo', 'band_handle_bass_hi',
                    'band_handle_high_lo', 'band_handle_high_hi',
                    'band_tag_bass', 'band_tag_high',
                    'band_hit_bass', 'band_hit_high',
                    'band_thresh_hit_bass', 'band_thresh_hit_high',
                    'thresh_slider_bass', 'thresh_slider_high',
                    'thresh_slider_peak',
                ):
                    paths.append(ch.path)
    hdr = _ui_grid_header(r)
    if hdr is not None:
        corner = hdr.op('corner')
        if corner is not None:
            paths.append(corner.path)
        for ch in hdr.children:
            if ch.isCOMP and ch.name.startswith('colhdr_'):
                paths.append(ch.path)
    gutter = ui.op('grid_gutter') if ui else None
    if gutter is not None:
        header = gutter.op('fixed_header')
        if header is not None:
            for ch in header.children:
                if ch.isCOMP:
                    paths.append(ch.path)
        fixed_rows = gutter.op('fixed_rows') or gutter
        for layer in range(1, _num_layers() + 1):
            row = fixed_rows.op('row_{}'.format(layer))
            if row is None:
                continue
            rl = row.op('rowlabel')
            if rl is not None:
                paths.append(rl.path)
            opacity = row.op('rowopacity')
            if opacity is not None:
                paths.append(opacity.path)
                fader = opacity.op('opacity_fader')
                if fader is not None:
                    paths.append(fader.path)
    for layer in range(1, _num_layers() + 1):
        row = grid.op('row_{}'.format(layer))
        if row is None:
            continue
        rl = row.op('rowlabel')
        if rl is not None:
            paths.append(rl.path)
        for col in range(1, _num_cols() + 1):
            cell = row.op('cell_{}_{}'.format(layer, col))
            if cell is not None:
                paths.append(cell.path)
    try:
        pe.par.panels = ' '.join(paths)
        pe.par.panelvalue = 'lselect rselect u v insidev mousev scrollu scrollx wheel'
        pe.par.offtoon = True
        pe.par.ontooff = True
        pe.par.valuechange = True
        pe.par.whileon = True
    except Exception:
        pass


CANVAS_W_EXPR = 'op("/settings").par.Canvaswidth'
CANVAS_H_EXPR = 'op("/settings").par.Canvasheight'
CANVAS_BG_R_EXPR = 'op("/settings").par.Canvasbgr'
CANVAS_BG_G_EXPR = 'op("/settings").par.Canvasbgg'
CANVAS_BG_B_EXPR = 'op("/settings").par.Canvasbgb'


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
            try:
                par.mode = ParMode.CONSTANT
            except Exception:
                pass
        return True
    except Exception:
        return False


def _max_existing_layer(slots, grid):
    mx = 0
    if slots is not None:
        for ch in slots.children:
            if ch.name.startswith('layer_'):
                try:
                    mx = max(mx, int(ch.name.split('_')[1]))
                except Exception:
                    pass
    if grid is not None:
        for ch in grid.children:
            if ch.name.startswith('row_'):
                try:
                    mx = max(mx, int(ch.name.split('_')[1]))
                except Exception:
                    pass
    return mx


def _bind_canvas_res(top):
    if top is None:
        return
    _set_par(top, 'outputresolution', 'custom')
    # /settings is the canonical location. Resolve the active settings COMP
    _set_par(top, 'resolutionw', expr=_canvas_w_expr())
    _set_par(top, 'resolutionh', expr=_canvas_h_expr())
    try:
        top.par.resmult = False
    except Exception:
        pass


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
    _configure_video_source(video)
    _set_par(video, 'preload', True)
    _set_video_active(video, False)
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
    out = slot.create('outTOP', 'out1')
    _ensure_slot_layer_blend(slot, layer_idx)
    _route_slot_pass_only(slot)
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
    for col in range(1, _num_cols() + 1):
        out = _build_slot(layer, col, layer_idx)
        out.outputConnectors[0].connect(switch.inputConnectors[col])
    layer.create('outTOP', 'out1')
    switch.outputConnectors[0].connect(layer.op('out1').inputConnectors[0])
    return layer


def _create_grid_row(grid, layer, root, legacy_drop=None):
    row = grid.op('row_{}'.format(layer))
    if row is not None:
        return row
    row = grid.create('containerCOMP', 'row_{}'.format(layer))
    _set_par(row, 'w', _grid_content_w())
    _set_par(row, 'h', CELL_H + 2)
    try:
        row.par.drop = 'dropno'
        row.par.drag = 'dragno'
    except Exception:
        pass
    rl = row.create('containerCOMP', 'rowlabel')
    _set_par(rl, 'w', ROW_LABEL_W)
    _set_par(rl, 'h', CELL_H - 2)
    _pin_scroll_label(rl)
    try:
        rl.par.drop = 'dropno'
        rl.par.drag = 'dragno'
    except Exception:
        pass
    txt = rl.op('label_text')
    if txt is None:
        txt = rl.create('textTOP', 'label_text')
    _style_header_text(txt, ROW_LABEL_W, CELL_H - 2, _layer_label(layer))
    _set_par(rl, 'top', txt)
    _set_par(rl, 'topfill', 'fit')
    _hide_grid_row_opacity(row)
    for c in range(1, _num_cols() + 1):
        cell = row.create('containerCOMP', 'cell_{}_{}'.format(layer, c))
        _set_par(cell, 'x', _col_x(c))
        _set_par(cell, 'w', CELL_W)
        _set_par(cell, 'h', CELL_H)
        _ensure_cell_layout(cell)
        _repair_cell_dragdrop(cell, grid, legacy_drop)
    return row


def _ensure_max_layers(root):
    """Create hidden slot chains + grid rows up to MAX_LAYERS (needed for Add Row)."""
    _ensure_grid_stack(root)
    slots = root.op('slots')
    grid = _ui_grid(root)
    legacy = root.op('legacy_drop')
    if slots is None or grid is None:
        return
    mx = _max_existing_layer(slots, grid)
    for layer_idx in range(mx + 1, MAX_LAYERS + 1):
        if slots.op('layer_{}'.format(layer_idx)) is None:
            _build_layer(slots, layer_idx)
        _create_grid_row(grid, layer_idx, root, legacy)


def _shift_comp_layers_on_insert(ref, scene=None):
    scene = _active_scene() if scene is None else int(scene)
    tbl = _comp_table()
    if tbl is None:
        return
    rows = []
    for i in range(1, tbl.numRows):
        try:
            if int(tbl[i, 'scene']) != scene:
                continue
            ly = int(tbl[i, 'layer'])
            if ly >= ref:
                rows.append((ly, int(tbl[i, 'src_col'])))
        except Exception:
            continue
    for ly, _ in sorted(rows, key=lambda x: -x[0]):
        _clear_layer_src_col(ly, scene=scene)
    for ly, sc in rows:
        _set_layer_src_col(ly + 1, sc, scene=scene)


def _shift_comp_layers_on_delete(ref, scene=None):
    scene = _active_scene() if scene is None else int(scene)
    tbl = _comp_table()
    if tbl is None:
        return
    rows = []
    for i in range(1, tbl.numRows):
        try:
            if int(tbl[i, 'scene']) != scene:
                continue
            ly = int(tbl[i, 'layer'])
            if ly > ref:
                rows.append((ly, int(tbl[i, 'src_col'])))
        except Exception:
            continue
    for ly, _ in sorted(rows, key=lambda x: -x[0]):
        _clear_layer_src_col(ly, scene=scene)
    for ly, sc in rows:
        _set_layer_src_col(ly - 1, sc, scene=scene)
    _clear_layer_src_col(ref, scene=scene)


def add_row_above(ref_layer):
    """Insert an empty FX row above ref_layer. Base row stays at bottom."""
    r = _root()
    if r is None:
        return False
    n = _num_layers()
    if n >= MAX_LAYERS:
        print('Max layers ({}) reached'.format(MAX_LAYERS))
        return False
    ref = max(1, min(int(ref_layer), n))
    _ensure_max_layers(r)
    _set_scene_grid_dims(_active_scene(), num_layers=n + 1)
    try:
        _set_num_layers(n + 1)
        p = r.par.Activelayer
        if float(p.max) < n + 1:
            p.normMax = MAX_LAYERS
        p2 = r.par.Selectedlayer
        if float(p2.max) < n + 1:
            p2.normMax = MAX_LAYERS
    except Exception:
        pass
    skip = _all_grid_coords()
    for col in range(1, _num_cols() + 1):
        for i in range(n, ref - 1, -1):
            _transfer_cell(i, col, i + 1, col, skip_evict=skip)
        clear_cell(ref, col)
        _ensure_slot_chain(_slot(ref, col), ref)
    _shift_comp_layers_on_insert(ref)
    _rebuild_composition()
    _cache_scene_cell_params(_active_scene())
    repair_cell_labels()
    _refresh_panel_exec_panels()
    print('Added row above {} ({} layers)'.format(_layer_label(ref), n + 1))
    return True


def delete_row(ref_layer):
    """Remove FX row ref_layer and shift rows above down. Base row (L1) cannot be deleted."""
    r = _root()
    if r is None:
        return False
    n = _num_layers()
    if n <= MIN_LAYERS:
        print('Minimum {} layers — cannot delete'.format(MIN_LAYERS))
        return False
    ref = max(1, min(int(ref_layer), n))
    if ref == _base_layer():
        print('Cannot delete base row (L1)')
        return False
    label = _layer_label(ref)
    skip = [(layer, col) for layer in range(1, n + 1) for col in range(1, _num_cols() + 1)]
    _set_scene_grid_dims(_active_scene(), num_layers=n - 1)
    try:
        _set_num_layers(n - 1)
        for pname in ('Activelayer', 'Selectedlayer'):
            p = getattr(r.par, pname, None)
            if p is None:
                continue
            cur = int(float(p.eval()))
            if cur == ref:
                p.val = max(1, min(ref, n - 1))
            elif cur > ref:
                p.val = cur - 1
        p = r.par.Activelayer
        if float(p.max) < n - 1:
            p.normMax = MAX_LAYERS
        p2 = r.par.Selectedlayer
        if float(p2.max) < n - 1:
            p2.normMax = MAX_LAYERS
    except Exception:
        pass
    for col in range(1, _num_cols() + 1):
        for i in range(ref, n):
            _transfer_cell(i + 1, col, i, col, skip_evict=skip)
        clear_cell(n, col)
        _ensure_slot_chain(_slot(n, col), n)
    _shift_comp_layers_on_delete(ref)
    _rebuild_composition()
    _cache_scene_cell_params(_active_scene())
    repair_cell_labels()
    _refresh_panel_exec_panels()
    print('Deleted {} ({} layers)'.format(label, n - 1))
    return True


def clear_cell(layer, col):
    layer, col = int(layer), int(col)
    tbl = _table()
    idx = _find(tbl, layer, col)
    if idx is not None:
        tbl[idx, 'type'] = ''
        tbl[idx, 'path'] = ''
        tbl[idx, 'label'] = ''
        try:
            tbl[idx, 'render_scale'] = '100'
        except Exception:
            pass
        try:
            tbl[idx, 'update_rate'] = '1'
            tbl[idx, 'frozen'] = '0'
        except Exception:
            pass
    slot = _slot(layer, col)
    if slot is not None:
        try:
            _route_slot_pass_only(slot)
        except Exception:
            pass
        v = slot.op('video')
        if v is not None:
            v.par.file = ''
            _set_video_active(v, False)
        t = slot.op('tox')
        if t is not None:
            try:
                t.par.externaltox = ''
            except Exception:
                pass
            t.allowCooking = False
    _clear_video_prime_cache(layer, col)
    _reset_cell_preview(layer, col)
    try:
        clear_cell_map_out_param_binds(layer, col)
    except Exception:
        pass
    try:
        clear_cell_map_control_store(layer, col)
    except Exception:
        pass
    try:
        purge_map_control_bindings_for_cell(layer, col)
    except Exception:
        pass
    try:
        clear_cell_fx(layer, col)
    except Exception:
        pass


def move_cell(from_layer, from_col, to_layer, to_col):
    """Move or swap a loaded clip between grid cells."""
    from_layer, from_col = int(from_layer), int(from_col)
    to_layer, to_col = int(to_layer), int(to_col)
    if from_layer == to_layer and from_col == to_col:
        return False
    src_type, src_path = _get(from_layer, from_col)
    if not src_path:
        return False
    dst_layer, dst_col = _normalize_cell(to_layer, to_col, src_type)
    dst_type, dst_path = _get(dst_layer, dst_col)
    src_params = _snapshot_cell_params(from_layer, from_col, src_type)
    dst_params = _snapshot_cell_params(dst_layer, dst_col, dst_type) if dst_path else []
    src_cell_fx = snapshot_cell_fx(from_layer, from_col)
    dst_cell_fx = snapshot_cell_fx(dst_layer, dst_col) if dst_path else []
    src_map_control = snapshot_cell_map_control(from_layer, from_col)
    dst_map_control = snapshot_cell_map_control(dst_layer, dst_col) if dst_path else {}
    src_render_scale = _cell_render_scale(from_layer, from_col)
    src_update_rate = _cell_update_rate(from_layer, from_col)
    src_frozen = _cell_frozen(from_layer, from_col)
    dst_render_scale = _cell_render_scale(dst_layer, dst_col) if dst_path else 100
    dst_update_rate = _cell_update_rate(dst_layer, dst_col) if dst_path else 1
    dst_frozen = _cell_frozen(dst_layer, dst_col) if dst_path else False
    skip = [(from_layer, from_col), (dst_layer, dst_col)]
    if dst_path:
        load_cell(dst_layer, dst_col, src_type, src_path, skip_evict=skip, par_state=src_params, auto_add_fx_row=False)
        set_cell_render_scale(dst_layer, dst_col, src_render_scale)
        set_cell_update_rate(dst_layer, dst_col, src_update_rate)
        set_cell_frozen(dst_layer, dst_col, src_frozen)
        load_cell(from_layer, from_col, dst_type, dst_path, skip_evict=skip, par_state=dst_params, auto_add_fx_row=False)
        set_cell_render_scale(from_layer, from_col, dst_render_scale)
        set_cell_update_rate(from_layer, from_col, dst_update_rate)
        set_cell_frozen(from_layer, from_col, dst_frozen)
        restore_cell_fx(dst_layer, dst_col, src_cell_fx)
        restore_cell_fx(from_layer, from_col, dst_cell_fx)
        restore_cell_map_control(
            dst_layer, dst_col, src_map_control,
            src_layer=from_layer, src_col=from_col,
        )
        restore_cell_map_control(
            from_layer, from_col, dst_map_control,
            src_layer=dst_layer, src_col=dst_col,
        )
    else:
        load_cell(
            dst_layer, dst_col, src_type, src_path,
            skip_evict=[(from_layer, from_col)],
            par_state=src_params,
            auto_add_fx_row=False,
        )
        set_cell_render_scale(dst_layer, dst_col, src_render_scale)
        set_cell_update_rate(dst_layer, dst_col, src_update_rate)
        set_cell_frozen(dst_layer, dst_col, src_frozen)
        restore_cell_fx(dst_layer, dst_col, src_cell_fx)
        restore_cell_map_control(
            dst_layer, dst_col, src_map_control,
            src_layer=from_layer, src_col=from_col,
        )
        clear_cell(from_layer, from_col)
    touched = {from_col, to_col, dst_col}
    _refresh_composition_for_cols(touched)
    _refresh_ui()
    _finalize_cell_move_map_and_video(
        (from_layer, from_col),
        (dst_layer, dst_col),
        moved_type=src_type,
        swapped=bool(dst_path),
    )
    # Finalize force-reloads moved TOX shells. Restore custom parameter state
    # afterwards so direct audio/pulse binds survive the new slot path.
    if src_type == 'tox' and src_params:
        _restore_cell_params(dst_layer, dst_col, src_type, src_params)
        _schedule_cell_par_restore(dst_layer, dst_col, src_type, src_params)
    if dst_path and dst_type == 'tox' and dst_params:
        _restore_cell_params(from_layer, from_col, dst_type, dst_params)
        _schedule_cell_par_restore(from_layer, from_col, dst_type, dst_params)
    return True


def _finalize_cell_move_map_and_video(src_pos, dst_pos, moved_type=None, swapped=False):
    """Re-sync map binds and clip wiring after drag-reposition between cells."""
    dst_layer, dst_col = int(dst_pos[0]), int(dst_pos[1])
    try:
        activate_cell_map_control(dst_layer, dst_col, force=True)
    except Exception:
        try:
            repair_map_dial_binds()
            sync_map_control_context()
        except Exception:
            pass
    moved = str(moved_type or '').strip().lower()
    positions = [dst_pos]
    if swapped:
        positions.append(src_pos)
    for layer, col in positions:
        ctype, path = _get(int(layer), int(col))
        if not path:
            continue
        slot = _slot(int(layer), int(col))
        if slot is None:
            continue
        ctype = str(ctype or '').strip().lower()
        try:
            if ctype == 'video':
                _clear_video_prime_cache(int(layer), int(col))
                live = global_transport_playing() and _video_slot_should_play(int(layer), int(col))
                _wire_video(slot, path, play=live, resume=True, force_reload=True)
            elif ctype == 'tox':
                _wire_tox(slot, path, int(layer), int(col), force_reload=True)
        except Exception:
            pass
    if moved == 'tox':
        try:
            schedule_cell_map_bind_repair(dst_layer, dst_col)
        except Exception:
            pass
    try:
        _update_cell_params_ui(dst_layer, dst_col)
    except Exception:
        pass


def load_cell(layer, col, clip_type, path, skip_evict=None, par_state=None, auto_add_fx_row=False):
    if not path or not _valid_clip_type(clip_type):
        return
    layer, col = _normalize_cell(layer, col, clip_type)
    if auto_add_fx_row and str(clip_type).strip().lower() == 'tox' and layer == _base_layer() and _num_layers() < MAX_LAYERS:
        # Effects need a source row below them. If dropped on the base row,
        # make room below and keep the effect at the user's drop location.
        add_row_above(layer)
        layer, col = _normalize_cell(layer, col, clip_type)
    if str(clip_type).strip().lower() == 'tox' and not cell_accepts_tox_clip_load(layer, col):
        print('Cannot load effect (.tox) into a video cell')
        return
    path = _norm_asset_path(path)
    skip_evict = skip_evict or []
    dup_cols = _evict_duplicate_assets(clip_type, path, layer, col, skip=skip_evict)
    if str(clip_type).strip().lower() != 'tox':
        try:
            clear_cell_fx(layer, col)
        except Exception:
            pass
    _set(layer, col, clip_type, path)
    try:
        tbl = _table()
        idx = _find(tbl, layer, col)
        if idx is not None:
            tbl[idx, 'label'] = _cell_display_name(layer, col)
    except Exception:
        pass
    slot = _slot(layer, col)
    if slot is None:
        return
    slot_live = _video_slot_should_play(layer, col)
    live = global_transport_playing() and slot_live
    if clip_type == 'video':
        _clear_video_prime_cache(layer, col)
        # Always force reopen so replacing one video with another (or the same
        # re-exported filename) refreshes the Movie File In + thumbnail.
        _wire_video(slot, path, play=live, force_reload=True)
    else:
        _wire_tox(slot, path, layer, col)
        _warm_html_tox(slot, path, layer, col, force=True)
        _prime_html_tox_slot(slot, frames=90)
    # Frozen cells lock the video/tox output TOP — unlock, cook new media, re-lock.
    try:
        if not _cell_frozen(layer, col):
            _pause_slot(
                slot,
                on=live,
                keep_tox_cooking=_tox_cell_keep_cooking(layer, col, clip_type, path, slot_live, slot),
                clip_type=clip_type,
            )
    except Exception:
        _pause_slot(
            slot,
            on=live,
            keep_tox_cooking=_tox_cell_keep_cooking(layer, col, clip_type, path, slot_live, slot),
            clip_type=clip_type,
        )
    if par_state:
        try:
            clear_cell_map_out_param_binds(layer, col, clip_type)
        except Exception:
            pass
        _restore_cell_params(layer, col, clip_type, par_state)
        _schedule_cell_par_restore(layer, col, clip_type, par_state)
    _refresh_composition_for_cols(set(dup_cols) | {col})
    try:
        if _cell_frozen(layer, col):
            _recapture_cell_freeze(layer, col, clip_type)
    except Exception:
        pass
    if clip_type == 'video':
        _prime_video_for_thumbnail(slot, layer, col, force=True)
    _refresh_cell_display(layer, col, force_video_prime=(clip_type == 'video'))
    try:
        _wire_slot_cell_fx_chain(layer, col, slot)
    except Exception:
        pass
    if clip_type == 'video':
        _schedule_cell_preview_refresh(layer, col, 1, force_video_prime=True)
        _schedule_cell_preview_refresh(layer, col, 4, force_video_prime=True)
        _schedule_cell_preview_refresh(layer, col, 12, force_video_prime=True)
        _schedule_cell_preview_refresh(layer, col, 30, force_video_prime=True)
    print('Loaded {} row {} col {} -> {}'.format(clip_type, layer, col, _label(path)))
    return path
