def _cell_params_op(layer, col):
    slot = _slot(layer, col)
    if slot is None:
        return None, ''
    clip_type, path = _get(layer, col)
    if not path:
        return None, clip_type
    if clip_type == 'video':
        return slot.op('video'), clip_type
    if clip_type == 'tox':
        return slot.op('tox'), clip_type
    return None, clip_type


def _get_selected_cell_page(root):
    for pg in root.customPages:
        if pg.name == 'Selected Cell':
            return pg
    return root.appendCustomPage('Selected Cell')


def _par_on_page(par, page):
    try:
        pg = par.page
    except Exception:
        return False
    try:
        if pg == page:
            return True
    except Exception:
        pass
    try:
        return getattr(pg, 'name', None) == page.name
    except Exception:
        return False


def _clear_selected_cell_pars(root, page):
    doomed = []
    for p in list(root.customPars):
        try:
            if _par_on_page(p, page):
                doomed.append(p)
        except Exception:
            pass
    cell_change_log('selected_cell.clear', 'count={}'.format(len(doomed)))
    for p in doomed:
        try:
            cell_change_log('selected_cell.destroy', getattr(p, 'name', '?'))
            try:
                if p.mode == ParMode.BIND:
                    p.bindExpr = ''
                    p.mode = ParMode.CONSTANT
            except Exception:
                pass
            p.destroy()
        except Exception as exc:
            cell_change_log('selected_cell.destroy.error', getattr(p, 'name', '?'), exc=exc)


def _selected_cell_tab_key(layer, col, target):
    target_path = ''
    if target is not None:
        try:
            target_path = target.path.replace('\\', '/')
        except Exception:
            pass
    return (int(layer), int(col), target_path)


def _update_selected_cell_info(layer, col):
    r = _root()
    if r is None:
        return
    _, path = _get(layer, col)
    label = _cell_display_name(layer, col) if path else '(empty)'
    try:
        info = getattr(r.par, 'Cellinfo')
        info.val = 'Row {} Col {} — {}'.format(layer, col, label)
    except Exception:
        pass


def _bind_expr_for_par(master_par):
    owner = master_par.owner
    if owner is None:
        return None
    return "op('{}').par.{}".format(owner.path.replace('\\', '/'), master_par.name)


def _append_bound_par(page, master_par):
    if master_par is None or master_par.name.startswith('__'):
        return None
    expr = _bind_expr_for_par(master_par)
    if not expr:
        return None
    label = master_par.label or master_par.name
    name = master_par.name
    style = master_par.style
    try:
        if style == 'Int':
            pg = page.appendInt(name, label=label)
        elif style == 'Float':
            pg = page.appendFloat(name, label=label)
        elif style == 'Toggle':
            pg = page.appendToggle(name, label=label)
        elif style == 'Str':
            pg = page.appendStr(name, label=label)
        elif style == 'File':
            pg = page.appendFile(name, label=label)
        elif style == 'Menu':
            pg = page.appendMenu(name, label=label)
            try:
                pg.menuNames = master_par.menuNames
                pg.menuLabels = master_par.menuLabels
            except Exception:
                pass
        elif style == 'Pulse':
            pg = page.appendPulse(name, label=label)
        else:
            return None
        pg.bindExpr = expr
        return pg
    except Exception:
        return None


def _sync_selected_cell_tab(layer, col, target, clip_type):
    """Track selected cell label only — params show via cell_params / layer_fx panels."""
    r = _root()
    if r is None:
        return
    key = _selected_cell_tab_key(layer, col, target)
    cell_change_log('selected_cell.sync.start', 'L{} C{} key={}'.format(layer, col, key))
    if _PARAMS_UI_STATE.get('selected_cell_key') == key:
        _update_selected_cell_info(layer, col)
        cell_change_log('selected_cell.sync.skip')
        return
    page = _get_selected_cell_page(r)
    _clear_selected_cell_pars(r, page)
    _PARAMS_UI_STATE['selected_cell_key'] = key
    ctype, path = _get(layer, col)
    label = _cell_display_name(layer, col) if path else '(empty)'
    try:
        info = getattr(r.par, 'Cellinfo')
        info.val = 'Row {} Col {} — {}'.format(layer, col, label)
        try:
            info.readOnly = True
        except Exception:
            pass
    except AttributeError:
        info = page.appendStr('Cellinfo', label='Selected')
        info.val = 'Row {} Col {} — {}'.format(layer, col, label)
        try:
            info.readOnly = True
        except Exception:
            pass
    cell_change_log('selected_cell.sync.done', 'info_only')


def _configure_cell_params_panel(panel, target=None, clip_type=''):
    """parameterCOMP like native node dialog — header, page tabs, all pages."""
    if panel is None:
        return
    try:
        panel.par.header = True
        panel.par.pagenames = True
        panel.par.labels = True
        panel.par.separators = True
        panel.par.allowexpand = True
        panel.par.pagescope = '*'
        panel.par.parscope = '*'
        panel.par.combinescopes = 'any'
        panel.par.autoscroll = True
        panel.par.display = True
    except Exception:
        pass
    if target is None:
        try:
            panel.par.enable = False
            panel.par.op = ''
        except Exception:
            pass
        return
    try:
        panel.par.op = target
        panel.par.enable = True
        panel.par.builtin = True
        panel.par.custom = clip_type == 'tox' or bool(getattr(target, 'customPars', None) and target.customPars)
    except Exception:
        pass


def _cell_panel_w():
    """Original equal-split width; extra settings width comes from a narrower preview."""
    base_panel_w = int(UI_W // 2)
    return max(320, int((base_panel_w - CELL_GAP * 4) / 2))


def _settings_panel_x():
    return UI_PANEL_X + _cell_panel_w() + CELL_GAP * 4


def _settings_panel_w():
    """Right edge at UI_W — same width as cell_params."""
    try:
        floor = int(SETTINGS_PANEL_MIN_W)
    except Exception:
        floor = 320
    return max(floor, int(UI_W - _settings_panel_x()))


def _configure_settings_params_panel(panel, force=False):
    if panel is None:
        return
    settings = _settings()
    settings_path = settings.path if settings is not None else ''
    try:
        cur = panel.par.op.eval()
        cur_path = cur.path if cur is not None else ''
    except Exception:
        cur_path = ''
    already_bound = bool(settings_path and cur_path == settings_path)
    # If already pointing at /settings, do not rebind. Rebinding (or enabling
    # syncpage) snaps the Perform panel back to Canvas when /settings is on
    # a different page than the panel.
    if not force and already_bound:
        _PARAMS_UI_STATE['settings_target_path'] = settings_path
        try:
            panel.par.display = True
            panel.par.enable = True
            panel.par.drag = 'dragno'
            panel.par.drop = 'dropno'
            panel.par.mousewheel = False
        except Exception:
            pass
        return
    # Preserve the visible Perform tab across op rebinds.
    keep_panel_idx = None
    keep_settings_idx = None
    try:
        keep_panel_idx = int(float(panel.par.pageindex.eval()))
    except Exception:
        pass
    if settings is not None:
        try:
            keep_settings_idx = int(float(settings.par.pageindex.eval()))
        except Exception:
            pass
    try:
        saved_sync = bool(panel.par.syncpage.eval())
    except Exception:
        saved_sync = False
    try:
        panel.par.header = True
        panel.par.pagenames = True
        panel.par.labels = True
        panel.par.separators = True
        panel.par.allowexpand = True
        panel.par.pagescope = '*'
        panel.par.parscope = '*'
        panel.par.combinescopes = 'any'
        panel.par.autoscroll = True
        panel.par.display = True
        panel.par.enable = settings is not None
        panel.par.builtin = False
        panel.par.custom = True
        if settings is not None:
            panel.par.op = ''
            panel.par.op = settings.path
            _PARAMS_UI_STATE['settings_target_path'] = settings.path
        else:
            panel.par.op = ''
            _PARAMS_UI_STATE['settings_target_path'] = ''
        panel.par.drag = 'dragno'
        panel.par.drop = 'dropno'
        panel.par.mousewheel = False
        # Keep Perform panel page independent of network editor /settings page.
        panel.par.syncpage = False
    except Exception:
        pass
    try:
        if keep_panel_idx is not None:
            panel.par.pageindex = keep_panel_idx
    except Exception:
        pass
    try:
        if settings is not None and keep_settings_idx is not None:
            settings.par.pageindex = keep_settings_idx
    except Exception:
        pass
    try:
        panel.par.syncpage = saved_sync
    except Exception:
        pass


def _refresh_settings_params_panel():
    """Re-sync Perform settings panel after New Set (lightweight — no per-frame cooking)."""
    r = _root()
    ui = r.op('ui') if r else None
    panel = ui.op('settings_params') if ui else None
    settings = _settings()
    if panel is None:
        return False
    state = None
    try:
        state = _settings_panel_page_state()
    except Exception:
        state = None
    try:
        _disable_legacy_settings_panel_exec()
    except Exception:
        pass
    _configure_settings_params_panel(panel, force=True)
    if settings is not None:
        try:
            op_path = settings.path
            panel.par.op = ''
            panel.par.op = op_path
        except Exception:
            pass
    try:
        if state:
            _restore_settings_panel_page(state)
    except Exception:
        pass
    try:
        _refresh_panel_exec_panels()
    except Exception:
        pass
    return True
    return True


def _settings_panel_page_state():
    """Remember Perform settings tab while /settings custom pages are healed."""
    r = _root()
    ui = r.op('ui') if r else None
    panel = ui.op('settings_params') if ui else None
    settings = _settings()
    state = {}
    if panel is not None:
        try:
            state['panel_pageindex'] = int(float(panel.par.pageindex.eval()))
        except Exception:
            pass
    if settings is not None:
        try:
            state['settings_pageindex'] = int(float(settings.par.pageindex.eval()))
        except Exception:
            pass
        try:
            pages = [pg.name for pg in settings.customPages]
            idx = state.get('settings_pageindex')
            if idx is not None and 0 <= idx < len(pages):
                state['page_name'] = pages[idx]
        except Exception:
            pass
    return state or None


def _restore_settings_panel_page(state):
    if not state:
        return
    r = _root()
    ui = r.op('ui') if r else None
    panel = ui.op('settings_params') if ui else None
    settings = _settings()
    page_name = _canonical_settings_tab_name(state.get('page_name'))
    if settings is not None and page_name:
        try:
            pages = [pg.name for pg in settings.customPages]
            if page_name in pages:
                settings.par.pageindex = pages.index(page_name)
        except Exception:
            pass
    if 'settings_pageindex' in state and settings is not None and page_name is None:
        try:
            settings.par.pageindex = int(state['settings_pageindex'])
        except Exception:
            pass
    if panel is not None:
        if page_name and settings is not None:
            try:
                pages = [pg.name for pg in settings.customPages]
                if page_name in pages:
                    panel.par.pageindex = pages.index(page_name)
            except Exception:
                pass
        elif 'panel_pageindex' in state:
            try:
                panel.par.pageindex = int(state['panel_pageindex'])
            except Exception:
                pass


def _pin_settings_tab(page_name='Midi', defer_frames=(0, 1, 2, 3, 5, 8, 12)):
    """Keep Perform settings panel on a tab after param/menu edits (pulse/menu refresh resets to Canvas)."""
    page_name = _canonical_settings_tab_name(page_name or 'Midi')
    state = {'page_name': page_name}
    try:
        captured = _settings_panel_page_state()
        if captured:
            state.update(captured)
            state['page_name'] = page_name
    except Exception:
        pass

    def _restore():
        try:
            _restore_settings_panel_page(state)
        except Exception:
            pass

    for delay in defer_frames:
        delay = int(delay)
        if delay <= 0:
            _restore()
            continue
        # delayFrames freeze while transport is paused — use ms fallback.
        if not _defer_run(_restore, delayFrames=delay, fromOP=_root()):
            try:
                run(_restore, delayMilliSeconds=max(1, delay * 16), fromOP=_root())
            except Exception:
                try:
                    run(_restore, delayFrames=delay)
                except Exception:
                    pass


def _settings_tab_index(page_name='Midi'):
    page_name = _canonical_settings_tab_name(page_name or 'Midi')
    settings = _settings()
    if settings is None:
        return None
    try:
        pages = [pg.name for pg in settings.customPages]
        if page_name in pages:
            return pages.index(page_name)
    except Exception:
        pass
    return None


def _nudge_settings_params_panel(page_name='Midi'):
    """Reload Perform settings_params menus; keep the requested tab selected."""
    page_name = _canonical_settings_tab_name(page_name or 'Midi')
    idx = _settings_tab_index(page_name)
    if idx is None:
        return False
    r = _root()
    ui = r.op('ui') if r else None
    panel = ui.op('settings_params') if ui else None
    settings = _settings()
    if panel is None or settings is None:
        return False
    op_path = settings.path
    state = {'page_name': page_name}

    def _lock_tab():
        try:
            settings.par.pageindex = idx
        except Exception:
            pass
        try:
            panel.par.pageindex = idx
        except Exception:
            pass

    def _rebind():
        _lock_tab()
        saved_sync = False
        try:
            saved_sync = bool(panel.par.syncpage.eval())
        except Exception:
            pass
        try:
            panel.par.syncpage = True
            settings.par.pageindex = idx
        except Exception:
            pass
        try:
            panel.par.op = ''
            panel.par.op = op_path
        except Exception:
            pass
        try:
            panel.par.syncpage = saved_sync
        except Exception:
            pass
        _lock_tab()
        try:
            _restore_settings_panel_page(state)
        except Exception:
            pass
        _pin_settings_tab(page_name)

    _lock_tab()
    try:
        run(_rebind, delayFrames=1, fromOP=_root())
    except Exception:
        _rebind()
    _pin_settings_tab(page_name)
    return True


def _ensure_settings_params_panel():
    r = _root()
    ui = r.op('ui') if r else None
    if ui is None:
        return None
    panel = ui.op('settings_params')
    if panel is None:
        panel = ui.create('parameterCOMP', 'settings_params')
        panel.par.x = _settings_panel_x()
        panel.par.w = _settings_panel_w()
        panel.par.h = PARAM_PANEL_H
        panel.par.hmode = 'fixed'
        panel.par.vmode = 'fixed'
        panel.par.y = 0
        try:
            panel.par.drop = 'dropno'
            panel.par.drag = 'dragno'
            panel.par.display = True
            panel.par.enable = True
        except Exception:
            pass
    _configure_settings_params_panel(panel)
    return panel


def _ensure_cell_params_panel():
    r = _root()
    ui = r.op('ui') if r else None
    if ui is None:
        return None
    panel = ui.op('cell_params')
    created = False
    if panel is None:
        panel = ui.create('parameterCOMP', 'cell_params')
        created = True
        panel.par.x = 0
        panel.par.w = _cell_panel_w()
        panel.par.h = PARAM_PANEL_H
        panel.par.hmode = 'fixed'
        panel.par.vmode = 'fixed'
        panel.par.y = 0
        try:
            panel.par.drop = 'dropno'
            panel.par.drag = 'dragno'
            panel.par.display = True
            panel.par.enable = False
        except Exception:
            pass
    if created:
        _configure_cell_params_panel(panel)
    return panel


def _cell_param_focus_mode():
    settings = _settings()
    if settings is None:
        return 'delayed'
    try:
        mode = str(settings.par.Cellparamfocus.eval()).strip().lower()
    except Exception:
        return 'delayed'
    if mode == 'immediate':
        return 'delayed'
    if mode in ('delayed', 'double', 'off'):
        return mode
    return 'delayed'


def _schedule_cell_params_ui(layer, col, delay_frames=18):
    r = _root()
    if r is None:
        return False
    try:
        layer, col = int(layer), int(col)
    except Exception:
        return False
    token = '{}:{}:{}'.format(layer, col, absTime.frame)
    try:
        r.store('sonomika_pending_cell_param_focus', token)
    except Exception:
        pass

    def _apply_delayed_cell_params_ui():
        try:
            if r.fetch('sonomika_pending_cell_param_focus', None) != token:
                return
        except Exception:
            pass
        try:
            if int(float(r.par.Selectedlayer.eval())) != layer:
                return
            if int(float(r.par.Selectedcol.eval())) != col:
                return
        except Exception:
            pass
        _update_cell_params_ui(layer, col, force=True)

    try:
        return bool(_defer_run(
            _apply_delayed_cell_params_ui,
            delayFrames=max(1, int(delay_frames)),
            fromOP=r,
        ))
    except Exception:
        return False


def focus_cell_params(layer=None, col=None):
    """Force the selected cell parameter panel to retarget now."""
    return _update_cell_params_ui(layer, col, force=True)


def _update_cell_params_ui(layer=None, col=None, force=False):
    """Show effect accordions or the plain parameter panel for other cell types."""
    r = _root()
    if r is None:
        return
    ui = r.op('ui')
    if ui is None:
        return
    if layer is None or col is None:
        try:
            layer = int(float(r.par.Selectedlayer.eval()))
            col = int(float(r.par.Selectedcol.eval()))
        except Exception:
            return
    layer, col = int(layer), int(col)
    if not force:
        mode = _cell_param_focus_mode()
        if mode == 'off':
            _update_selected_cell_info(layer, col)
            return
        if mode == 'double':
            _update_selected_cell_info(layer, col)
            return
        if mode == 'delayed':
            _update_selected_cell_info(layer, col)
            if _schedule_cell_params_ui(layer, col):
                return
    cell_change_log('cell_params_ui.start', 'L{} C{}'.format(layer, col))
    target, clip_type = _cell_params_op(layer, col)
    _selected_type, selected_path = _get(layer, col)
    cell_change_log('cell_params_ui.type', '{} path={}'.format(clip_type, selected_path))
    if clip_type == 'tox' or not selected_path:
        panel = ui.op('cell_params')
        if panel is not None:
            try:
                panel.par.op = ''
                panel.par.enable = False
                cell_change_log('cell_params_ui.clear_panel')
            except Exception as exc:
                cell_change_log('cell_params_ui.clear_panel.error', exc=exc)
        _PARAMS_UI_STATE['target_path'] = ''
        try:
            _refresh_layer_fx_ui(layer, col)
            cell_change_log('cell_params_ui.layer_fx.done')
        except Exception as exc:
            cell_change_log('cell_params_ui.layer_fx.error', exc=exc)
        try:
            _apply_params_tab_visibility()
            cell_change_log('cell_params_ui.tabs')
        except Exception as exc:
            cell_change_log('cell_params_ui.tabs.error', exc=exc)
        try:
            sync_map_control_context()
            cell_change_log('cell_params_ui.map_ctx')
        except Exception as exc:
            cell_change_log('cell_params_ui.map_ctx.error', exc=exc)
        try:
            repair_map_dial_binds()
            cell_change_log('cell_params_ui.map_repair')
        except Exception as exc:
            cell_change_log('cell_params_ui.map_repair.error', exc=exc)
        cell_change_log('cell_params_ui.done_tox')
        return
    panel = _ensure_cell_params_panel()
    if panel is None:
        return
    target_path = target.path if target is not None else ''
    if _PARAMS_UI_STATE.get('target_path') != target_path:
        _PARAMS_UI_STATE['target_path'] = target_path
        _sync_selected_cell_tab(layer, col, target, clip_type)
        _configure_cell_params_panel(panel, target, clip_type)
    else:
        try:
            cur = panel.par.op.eval()
            if target is not None and (cur is None or cur.path != target.path):
                _configure_cell_params_panel(panel, target, clip_type)
        except Exception:
            _configure_cell_params_panel(panel, target, clip_type)
    _apply_params_tab_visibility()
    try:
        sync_map_control_context()
    except Exception:
        pass
    try:
        repair_map_dial_binds()
    except Exception:
        pass


def _preview_panel_dims(max_w, max_h):
    """Fit canvas aspect inside the preview zone (no grey letterbox bars)."""
    cw = max(1, int(_canvas_w()))
    ch = max(1, int(_canvas_h()))
    max_w = max(1, int(max_w))
    max_h = max(1, int(max_h))
    scale = min(max_w / float(cw), max_h / float(ch))
    return max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))


def _layout_program_preview_in_zone(prev, zone_w, zone_h):
    """Center canvas-aspect preview in the black preview zone (panel coords, origin bottom-left)."""
    if prev is None:
        return
    zone_w = max(1, int(zone_w))
    zone_h = max(1, int(zone_h))
    pw, ph = _preview_panel_dims(zone_w, max(1, zone_h - 2))
    ph = min(ph, max(1, zone_h - 2))
    pw = min(pw, max(1, zone_w - 2))
    try:
        prev.par.w = pw
        prev.par.h = ph
        prev.par.x = max(0, int((zone_w - pw) / 2))
        prev.par.y = max(0, min(zone_h - ph, int((zone_h - ph) / 2)))
        prev.par.hmode = 'fixed'
        prev.par.vmode = 'fixed'
        prev.par.align = 'none'
        prev.par.display = True
        prev.par.enable = True
        prev.par.clipping = True
        _crop_panel_children(prev, True)
    except Exception:
        pass


def _sanitize_program_preview(ui, zone, prev):
    """Keep a single preview under program_preview_zone (stale ui-level copy overlaps audio bar)."""
    if ui is None:
        return prev
    found = None
    for ch in list(ui.children):
        if getattr(ch, 'name', '') != 'program_preview':
            continue
        if zone is not None and ch.parent == zone:
            found = ch
            continue
        if zone is not None:
            try:
                ch.parent = zone
                found = ch
            except Exception:
                try:
                    ch.destroy()
                except Exception:
                    pass
        else:
            found = ch
    if prev is None:
        prev = found
    if zone is not None:
        for ch in list(zone.children):
            if getattr(ch, 'name', '') == 'program_preview' and prev is not None and ch != prev:
                try:
                    ch.destroy()
                except Exception:
                    pass
    return prev


def _ensure_program_preview_zone(ui):
    zone = ui.op('program_preview_zone') if ui is not None else None
    if zone is None and ui is not None:
        zone = ui.create('containerCOMP', 'program_preview_zone')
    if zone is None:
        return None
    try:
        zone.par.bgcolorr, zone.par.bgcolorg, zone.par.bgcolorb = UI_PREVIEW_BG
        zone.par.clickthrough = True
        zone.par.drop = 'dropno'
        zone.par.drag = 'dragno'
        zone.par.display = True
        zone.par.enable = True
        zone.par.clipping = True
        zone.par.hmode = 'fixed'
        zone.par.vmode = 'fixed'
        zone.par.align = 'none'
    except Exception:
        pass
    return zone


def _ensure_program_preview_sel(prev):
    """Single selectTOP on program chain — avoid overTOP (was masking live output)."""
    if prev is None:
        return None
    sel = prev.op('program_sel')
    if sel is None:
        sel = prev.create('selectTOP', 'program_sel')
    for stale in ('program_view', 'program_bg', 'preview'):
        node = prev.op(stale)
        if node is not None and node != sel:
            try:
                node.destroy()
            except Exception:
                pass
    try:
        prev.par.top = sel
        prev.par.topfill = 'best'
        prev.par.bgcolorr, prev.par.bgcolorg, prev.par.bgcolorb = UI_PREVIEW_BG
        prev.par.display = True
        prev.par.enable = True
    except Exception:
        pass
    return sel


def _program_preview_source(r):
    """TOP that feeds the perform preview; follow the actual routed program."""
    if r is None:
        return None
    for name in ('program_sel', 'global_fx_out', 'chain_out'):
        src = r.op(name)
        if src is not None:
            return src
    return None


def _sync_program_preview():
    """Preview: canvas aspect frame, black letterbox, live program TOP."""
    r = _root()
    if r is None:
        return
    ui = r.op('ui')
    if ui is None:
        return
    zone = _ensure_program_preview_zone(ui)
    prev = None
    if zone is not None:
        prev = zone.op('program_preview')
    if prev is None:
        prev = ui.op('program_preview')
    if prev is None:
        parent = zone if zone is not None else ui
        prev = parent.create('containerCOMP', 'program_preview')
    elif zone is not None and prev.parent != zone:
        try:
            prev.parent = zone
        except Exception:
            pass
    prev = _sanitize_program_preview(ui, zone, prev)
    sel = _ensure_program_preview_sel(prev)
    if sel is None:
        return
    _repair_opaque_black_sources()
    src = _program_preview_source(r)
    try:
        sel.par.outputresolution = 'useinput'
    except Exception:
        pass
    if src is not None:
        try:
            sel.par.top = src
            sel.par.top.mode = ParMode.CONSTANT
        except Exception:
            pass
    else:
        try:
            sel.par.top.expr = "op({!r}).op('out1')".format(r.path.replace('\\', '/'))
            sel.par.top.mode = ParMode.EXPRESS
        except Exception:
            pass


def _sync_root_output():
    """Root program_pick / output window match /settings canvas size."""
    try:
        pick = _program_pick()
        _set_top_chain_res(pick)
    except Exception:
        pass
    try:
        rout = op('/out1')
        if rout is not None:
            rout.par.outputresolution = 'useinput'
    except Exception:
        pass
    try:
        win = op('/output_window')
        if win is not None:
            win.par.w.expr = _canvas_w_expr()
            win.par.w.mode = ParMode.EXPRESS
            win.par.h.expr = _canvas_h_expr()
            win.par.h.mode = ParMode.EXPRESS
    except Exception:
        pass


def _ensure_program_preview():
    """Bottom-left live program preview (50/50 width split with params UI)."""
    r = _root()
    ui = r.op('ui') if r else None
    if ui is None:
        return None
    zone = _ensure_program_preview_zone(ui)
    prev = zone.op('program_preview') if zone is not None else None
    if prev is None:
        prev = ui.op('program_preview')
    parent = zone if zone is not None else ui
    if prev is None:
        prev = parent.create('containerCOMP', 'program_preview')
    elif zone is not None and prev.parent != zone:
        try:
            prev.parent = zone
        except Exception:
            pass
    prev = _sanitize_program_preview(ui, zone, prev)
    try:
        prev.par.clickthrough = True
        prev.par.drop = 'dropno'
        prev.par.drag = 'dragno'
        prev.par.clipping = True
    except Exception:
        pass
    legacy = prev.op('preview')
    if legacy is not None:
        try:
            legacy.destroy()
        except Exception:
            pass
    _sync_program_preview()
    return prev


def _layout_bottom_h(content_h):
    """Height of preview + params strip."""
    sbh = SCENE_BAR_H + SCENE_BAR_TOP_PAD + SCENE_GRID_GAP
    available = UI_H - sbh - int(content_h) - 4
    preview_min = max(140, BOTTOM_ZONE_MIN)
    return max(preview_min, available)


def _sync_grid_ui():
    """Relayout grid geometry, then refresh rings/thumbnails (order matters)."""
    _layout_perform_ui()
    _refresh_ui()


def _layout_perform_ui():
    """Perform window = 1920x1080; grid full-width on top, preview + params 50/50 below."""
    r = _root()
    ui = r.op('ui') if r else None
    if ui is None:
        return
    prev = _ensure_program_preview()
    panel = _ensure_cell_params_panel()
    settings_panel = _ensure_settings_params_panel()
    bar = ui.op('scene_bar')
    content_h = _layout_grid_geometry()
    bottom_h = _layout_bottom_h(content_h)
    stack = _ui_grid_stack(_root())
    try:
        ui.par.x = 0
        ui.par.y = 0
        ui.par.w = UI_W
        ui.par.h = UI_H
        ui.par.wmode = 'fixed'
        ui.par.hmode = 'fixed'
        ui.par.align = 'none'
    except Exception:
        pass
    zone = _ensure_program_preview_zone(ui) if ui is not None else None
    if zone is not None:
        try:
            zone.par.x = 0
            zone.par.y = 0
            zone.par.w = PREVIEW_W
            zone.par.h = bottom_h
            zone.par.hmode = 'fixed'
            zone.par.vmode = 'fixed'
            zone.par.align = 'none'
            zone.par.display = True
            zone.par.enable = True
            zone.par.clipping = True
            zone.par.layoutorder = 2
        except Exception:
            pass
    if prev is not None:
        try:
            prev = _sanitize_program_preview(ui, zone, prev)
            _layout_program_preview_in_zone(prev, PREVIEW_W, bottom_h)
            _sync_program_preview()
        except Exception:
            pass
    # Top: scene bar + grid (full width, cells left → right).
    y_top = UI_H
    if bar is not None:
        try:
            bar.par.x = 0
            bar.par.y = y_top - SCENE_BAR_H - SCENE_BAR_TOP_PAD
            bar.par.w = UI_W
            bar.par.h = SCENE_BAR_H
            bar.par.align = 'none'
            bar.par.display = True
        except Exception:
            pass
        y_top -= SCENE_BAR_H + SCENE_BAR_TOP_PAD + SCENE_GRID_GAP
    target = stack if stack is not None else _ui_grid(_root())
    if target is not None:
        try:
            target.par.x = GRID_X0 if stack is not None else 0
            target.par.y = y_top - content_h
            target.par.w = UI_W - GRID_X0 if stack is not None else UI_W
            target.par.h = content_h
            target.par.align = 'none'
        except Exception:
            pass
        if stack is not None:
            try:
                _layout_fixed_grid_gutter(y_top - content_h, content_h, _layout_cell_h(_num_layers()))
            except Exception:
                pass
    # Bottom: preview (left) + selected-cell params + settings.
    _layout_params_column(bottom_h)
    if panel is not None:
        try:
            panel.par.display = True
        except Exception:
            pass
    strip_reserve = _audio_band_strip_reserve_h()
    _layout_audio_band_strip(bottom_h)
    if settings_panel is not None:
        try:
            settings_panel.par.x = _settings_panel_x()
            settings_panel.par.y = 0
            settings_panel.par.w = _settings_panel_w()
            settings_panel.par.h = max(120, int(bottom_h) - int(strip_reserve))
            settings_panel.par.hmode = 'fixed'
            settings_panel.par.vmode = 'fixed'
            settings_panel.par.align = 'none'
            settings_panel.par.display = True
            _configure_settings_params_panel(settings_panel, force=False)
            _refresh_panel_exec_panels()
        except Exception:
            pass
    try:
        perform = op('/perform')
        if perform is not None:
            winop = perform.par.winop.eval()
            if winop and ui.path in str(winop):
                perform.par.winw = UI_W
                perform.par.winh = UI_H
    except Exception:
        pass


def _ensure_root_output():
    try:
        restore_root_settings_layout(reposition=False)
    except Exception:
        pass
    r = _root()
    mo = r.op('out1') if r else None
    if mo is None:
        return
    expr = "op('{}')".format(mo.path)
    try:
        pick = _program_pick()
        if pick is None:
            pick = op('/').create('selectTOP', 'program_pick')
        pick.par.top.expr = expr
        pick.par.top.mode = ParMode.EXPRESS
        _set_top_chain_res(pick)
        rout = op('/out1')
        if rout is None:
            rout = op('/').create('outTOP', 'out1')
        try:
            rout.par.outputresolution = 'useinput'
        except Exception:
            pass
        pick.outputConnectors[0].connect(rout.inputConnectors[0])
        win = op('/output_window')
        if win is None:
            win = op('/').create('windowCOMP', 'output_window')
        win.par.winop = rout
        win.par.w.expr = _canvas_w_expr()
        win.par.w.mode = ParMode.EXPRESS
        win.par.h.expr = _canvas_h_expr()
        win.par.h.mode = ParMode.EXPRESS
    except Exception:
        pass


def _open_output():
    _ensure_root_output()
    try:
        win = op('/output_window')
        if win is not None and not win.par.drawwindow.eval():
            win.par.display = True
            win.par.drawwindow = True
            win.par.winopen.pulse()
    except Exception:
        pass


def _layout_thumb_h(cell_w):
    return max(27, int(round(cell_w * 9.0 / 16.0)))


def _layout_cell_w_for_viewport():
    """Width so VISIBLE_COLS fit in full-width grid; cols 17–20 scroll."""
    avail = UI_W - GRID_X0
    return max(64, (avail - (VISIBLE_COLS - 1) * CELL_GAP) // VISIBLE_COLS)


def _grid_layers_fit_rows(num_layers):
    """Row count used to size cells in the fixed perform viewport."""
    n = max(1, int(num_layers))
    return min(n, VISIBLE_ROWS) if n > VISIBLE_ROWS else n


def _grid_row_h(cell_h):
    return int(cell_h) + 2


def _grid_rows_scroll_h(num_layers, cell_h):
    row_h = _grid_row_h(cell_h)
    n = max(1, int(num_layers))
    return n * (row_h + CELL_GAP) + CELL_GAP


def _grid_rows_viewport_h(num_layers, cell_h):
    row_h = _grid_row_h(cell_h)
    vis = _grid_layers_fit_rows(num_layers)
    return vis * (row_h + CELL_GAP) + CELL_GAP


def _grid_hscroll_thickness():
    return 12


def _grid_header_top_pad():
    return 6


def _grid_needs_hscroll(cell_w=None):
    return _grid_content_w(cell_w) > (UI_W - GRID_X0) + 2


def _grid_zone_h(num_layers, cell_h, cell_w=None):
    """Scene-bar stack height: column header + visible rows + optional h-scrollbar."""
    base = _grid_header_top_pad() + GRID_HDR_H + CELL_GAP + _grid_rows_viewport_h(num_layers, cell_h)
    if _grid_needs_hscroll(cell_w):
        return base + _grid_hscroll_thickness()
    return base


def _ui_grid(r):
    ui = r.op('ui') if r else None
    if ui is None:
        return None
    stack = ui.op('grid_stack')
    if stack is not None:
        g = stack.op('grid')
        if g is not None:
            return g
    return ui.op('grid')


def _ui_grid_header(r):
    ui = r.op('ui') if r else None
    if ui is None:
        return None
    stack = ui.op('grid_stack')
    if stack is not None:
        gh = stack.op('grid_header')
        if gh is not None:
            return gh
    gh = ui.op('grid_header')
    if gh is not None:
        return gh
    grid = _ui_grid(r)
    if grid is not None:
        return grid.op('header_row')
    return None


def _ui_grid_stack(r):
    return r.op('ui/grid_stack') if r else None


def _ui_grid_gutter(r):
    ui = r.op('ui') if r else None
    if ui is None:
        return None
    gutter = ui.op('grid_gutter')
    if gutter is None:
        gutter = ui.create('containerCOMP', 'grid_gutter')
    return gutter


def _grid_cell(r, layer, col):
    """Grid cell COMP (works with ui/grid or ui/grid_stack/grid)."""
    grid = _ui_grid(r)
    if grid is None:
        return None
    layer, col = int(layer), int(col)
    return grid.op('row_{}/cell_{}_{}'.format(layer, layer, col))


def _ensure_grid_header_split(r):
    """Column header row lives outside the vertically scrolling grid body."""
    ui = r.op('ui')
    grid_body = _ui_grid(r)
    if ui is None or grid_body is None:
        return
    if grid_body.op('header_row') is None and _ui_grid_header(r) is not None:
        return
    hdr = grid_body.op('header_row')
    if hdr is None:
        return
    stack = ui.op('grid_stack')
    gh = stack.op('grid_header') if stack is not None else ui.op('grid_header')
    if gh is None:
        if stack is not None:
            gh = stack.create('containerCOMP', 'grid_header')
        else:
            gh = ui.create('containerCOMP', 'grid_header')
    try:
        gh.par.w = _grid_content_w()
        gh.par.h = GRID_HDR_H
        gh.par.hmode = 'fixed'
        gh.par.vmode = 'fixed'
        gh.par.align = 'none'
        gh.par.phscrollbar = 'off'
        gh.par.pvscrollbar = 'off'
        gh.par.drop = 'dropno'
        gh.par.drag = 'dragno'
    except Exception:
        pass
    for ch in list(hdr.children):
        try:
            ch.parent = gh
        except Exception:
            try:
                dup = ch.copy(gh)
                ch.destroy()
            except Exception:
                pass
    try:
        hdr.destroy()
    except Exception:
        pass


def _ensure_grid_stack(r):
    """Wrap grid_header + grid so horizontal scroll keeps columns aligned."""
    ui = r.op('ui')
    if ui is None:
        return
    _ensure_grid_header_split(r)
    grid = _ui_grid(r)
    gh = _ui_grid_header(r)
    if grid is None:
        return
    stack = ui.op('grid_stack')
    if stack is None:
        stack = ui.create('containerCOMP', 'grid_stack')
        try:
            stack.par.w = UI_W
            stack.par.hmode = 'fixed'
            stack.par.vmode = 'fixed'
            stack.par.align = 'none'
            stack.par.phscrollbar = 'auto'
            stack.par.pvscrollbar = 'off'
            stack.par.drop = 'dropno'
            stack.par.drag = 'dragno'
        except Exception:
            pass
    try:
        if gh is not None and gh.parent != stack:
            gh.parent = stack
        if grid.parent != stack:
            grid.parent = stack
    except Exception:
        pass


def _layout_cell_size(num_layers=None):
    """16:9 cells; ~16 columns visible (horizontal scroll); >7 rows vertical scroll."""
    if num_layers is None:
        num_layers = _num_layers()
    rows_fit = _grid_layers_fit_rows(num_layers)
    cell_w = _layout_cell_w_for_viewport()
    thumb_h = _layout_thumb_h(cell_w)
    cell_h = thumb_h + CELL_LABEL_H
    sbh = SCENE_BAR_H + SCENE_BAR_TOP_PAD + SCENE_GRID_GAP
    bottom_h = BOTTOM_ZONE_MIN + 4
    hdr_h = GRID_HDR_H
    grid_h = UI_H - sbh - bottom_h - 8
    overhead = hdr_h + CELL_GAP + rows_fit * 2 + max(0, rows_fit - 1) * CELL_GAP
    usable_h = max(0, grid_h - overhead)
    max_cell_h = max(CELL_LABEL_H + 27, int(usable_h / rows_fit))
    if cell_h > max_cell_h:
        thumb_h = max(27, max_cell_h - CELL_LABEL_H)
        cell_w = max(64, int(round(thumb_h * CELL_ASPECT)))
        cell_h = thumb_h + CELL_LABEL_H
    return cell_w, thumb_h, cell_h


def _layout_cell_w(num_layers=None):
    return _layout_cell_size(num_layers)[0]


def _layout_cell_h(num_layers=None, cell_w=None):
    if cell_w is not None:
        return _layout_thumb_h(cell_w) + CELL_LABEL_H
    return _layout_cell_size(num_layers)[2]


def _cell_step(cell_w=None):
    if cell_w is None:
        cell_w = _layout_cell_w()
    return cell_w + CELL_GAP


def _grid_content_w(cell_w=None):
    return _num_cols() * _cell_step(cell_w)


def _col_x(col, cell_w=None):
    return (int(col) - 1) * _cell_step(cell_w)


def _layer_label(layer):
    n = _num_layers()
    layer = int(layer)
    if layer < 1 or layer > n:
        return 'L?'
    return 'L{}'.format(n - layer + 1)


def _layout_hdr_cell(comp, hdr_h=None):
    """Inset header label cells so text is not clipped at the top edge."""
    if comp is None:
        return
    if hdr_h is None:
        hdr_h = GRID_HDR_H
    inner = max(14, hdr_h - GRID_HDR_PAD * 2)
    try:
        comp.par.y = GRID_HDR_PAD
        comp.par.h = inner
    except Exception:
        pass
    txt = comp.op('label_text')
    if txt is not None:
        try:
            w = int(float(comp.par.w.eval())) or CELL_W
            label = txt.par.text.eval()
            _style_header_text(txt, w, inner, label)
            comp.par.top = txt
            comp.par.topfill = 'fit'
        except Exception:
            pass


def _style_header_text(txt, w, h, text=''):
    txt.par.text = text or ''
    txt.par.resolutionw = max(32, int(w))
    txt.par.resolutionh = max(16, int(h))
    _apply_grid_font(txt)
    try:
        txt.par.font = TD_FONT
    except Exception:
        pass
    txt.par.bgalpha = 0.0
    txt.par.alignx = 'center'
    txt.par.aligny = 'center'
    txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = TD_TEXT_LABEL


def _pin_scroll_label(comp):
    if comp is None:
        return
    try:
        comp.par.scrolloverlay = 'over'
    except Exception:
        pass


def _crop_panel_children(comp, on=True):
    """Best-effort child clipping for row viewports."""
    if comp is None:
        return
    for pname in ('crop', 'cropchildren', 'clip', 'clippanel'):
        try:
            getattr(comp.par, pname).val = bool(on)
        except Exception:
            pass


def _layout_fixed_grid_gutter(stack_y, zone_h, cell_h):
    """Fixed Layer/Opacity gutter outside the horizontal scrolling grid_stack."""
    r = _root()
    gutter = _ui_grid_gutter(r)
    if gutter is None:
        return
    n = _num_layers()
    hdr_h = GRID_HDR_H
    row_h = _grid_row_h(cell_h)
    rows_scroll_h = _grid_rows_scroll_h(n, cell_h)
    rows_viewport_h = _grid_rows_viewport_h(n, cell_h)
    hbar = _grid_hscroll_thickness() if _grid_needs_hscroll(_layout_cell_w(n)) else 0
    top_pad = _grid_header_top_pad()
    hdr_y = zone_h - top_pad - hdr_h
    grid_y = hdr_y - CELL_GAP - rows_viewport_h
    try:
        gutter.par.x = 0
        gutter.par.y = stack_y
        gutter.par.w = GRID_X0
        gutter.par.h = zone_h
        gutter.par.hmode = 'fixed'
        gutter.par.vmode = 'fixed'
        gutter.par.align = 'none'
        gutter.par.display = True
        gutter.par.enable = True
        gutter.par.bgcolorr = 0
        gutter.par.bgcolorg = 0
        gutter.par.bgcolorb = 0
        gutter.par.bgalpha = 0
        gutter.par.drop = 'dropno'
        gutter.par.drag = 'dragno'
    except Exception:
        pass
    header = gutter.op('fixed_header')
    if header is None:
        header = gutter.create('containerCOMP', 'fixed_header')
    try:
        header.par.x = 0
        header.par.y = hdr_y + hbar
        header.par.w = GRID_X0
        header.par.h = hdr_h
        header.par.hmode = 'fixed'
        header.par.vmode = 'fixed'
        header.par.align = 'none'
        header.par.display = True
    except Exception:
        pass
    corner = header.op('corner')
    if corner is None:
        corner = header.create('containerCOMP', 'corner')
    try:
        corner.par.x = 0
        corner.par.w = ROW_LABEL_W
        corner.par.h = hdr_h
    except Exception:
        pass
    txt = corner.op('label_text')
    if txt is None:
        txt = corner.create('textTOP', 'label_text')
    _style_header_text(txt, ROW_LABEL_W, hdr_h, 'Layer')
    try:
        corner.par.top = txt
        corner.par.topfill = 'fit'
    except Exception:
        pass
    _layout_hdr_cell(corner, hdr_h)
    opacity_hdr = header.op('opacity_hdr')
    if opacity_hdr is None:
        opacity_hdr = header.create('containerCOMP', 'opacity_hdr')
    try:
        opacity_hdr.par.x = ROW_LABEL_W + CELL_GAP
        opacity_hdr.par.w = ROW_OPACITY_HDR_W
        opacity_hdr.par.h = hdr_h
    except Exception:
        pass
    txt = opacity_hdr.op('label_text')
    if txt is None:
        txt = opacity_hdr.create('textTOP', 'label_text')
    _style_header_text(txt, ROW_OPACITY_HDR_W, hdr_h, 'Opacity')
    try:
        opacity_hdr.par.top = txt
        opacity_hdr.par.topfill = 'fit'
    except Exception:
        pass
    _layout_hdr_cell(opacity_hdr, hdr_h)
    rows = gutter.op('fixed_rows')
    if rows is None:
        rows = gutter.create('containerCOMP', 'fixed_rows')
    try:
        rows.par.x = 0
        rows.par.y = grid_y + hbar
        rows.par.w = GRID_X0
        rows.par.h = rows_viewport_h
        rows.par.hmode = 'fixed'
        rows.par.vmode = 'fixed'
        rows.par.align = 'none'
        rows.par.phscrollbar = 'off'
        rows.par.pvscrollbar = 'off'
        rows.par.scrollbarthickness = 12
        rows.par.display = True
        rows.par.enable = True
        rows.par.bgcolorr = 0
        rows.par.bgcolorg = 0
        rows.par.bgcolorb = 0
        rows.par.bgalpha = 0
        rows.par.drop = 'dropno'
        rows.par.drag = 'dragno'
        _crop_panel_children(rows, True)
    except Exception:
        pass
    y_top = rows_scroll_h
    for layer in range(1, n + 1):
        row = rows.op('row_{}'.format(layer))
        if row is None:
            row = rows.create('containerCOMP', 'row_{}'.format(layer))
        try:
            row.par.x = 0
            row.par.y = y_top - row_h
            row.par.w = GRID_X0
            row.par.h = row_h
            row.par.hmode = 'fixed'
            row.par.vmode = 'fixed'
            row.par.align = 'none'
            row.par.display = True
        except Exception:
            pass
        rl = row.op('rowlabel')
        if rl is None:
            rl = row.create('containerCOMP', 'rowlabel')
        try:
            rl.par.x = 0
            rl.par.w = ROW_LABEL_W
            rl.par.h = cell_h - 2
            rl.par.drop = 'dropno'
            rl.par.drag = 'dragno'
        except Exception:
            pass
        txt = rl.op('label_text')
        if txt is None:
            txt = rl.create('textTOP', 'label_text')
        _style_header_text(txt, ROW_LABEL_W, cell_h - 2, _layer_label(layer))
        try:
            rl.par.top = txt
            rl.par.topfill = 'fit'
        except Exception:
            pass
        try:
            _ensure_row_opacity_slider(row, layer)
            _layout_row_opacity_slider(row, layer, cell_h)
        except Exception:
            pass
        y_top -= row_h + CELL_GAP
    for child in list(rows.children):
        if child.name.startswith('row_'):
            try:
                idx = int(child.name.split('_')[1])
                if idx > n:
                    child.par.display = False
            except Exception:
                pass
    for child in list(gutter.children):
        if child.name.startswith('row_'):
            try:
                child.par.display = False
            except Exception:
                pass


def sync_grid_vertical_scroll(value=None):
    """Scroll grid rows and fixed row labels together using the right-edge proxy."""
    global _GRID_SCROLL_V
    r = _root()
    if r is None:
        return False
    grid = _ui_grid(r)
    gutter = _ui_grid_gutter(r)
    fixed_rows = gutter.op('fixed_rows') if gutter is not None else None
    if grid is None:
        return False
    n = _num_layers()
    cell_w, thumb_h, cell_h = _layout_cell_size(n)
    row_h = _grid_row_h(cell_h)
    rows_scroll_h = _grid_rows_scroll_h(n, cell_h)
    rows_viewport_h = _grid_rows_viewport_h(n, cell_h)
    max_scroll = max(0, rows_scroll_h - rows_viewport_h)
    if value is None:
        value = _GRID_SCROLL_V
        try:
            ui = r.op('ui')
            proxy = ui.op('grid_vscroll') if ui is not None else None
            if proxy is not None:
                value = _GRID_SCROLL_V
        except Exception:
            pass
    try:
        value = max(0.0, min(1.0, float(value)))
    except Exception:
        value = 0.0
    _GRID_SCROLL_V = value
    offset = max_scroll * value
    y_top = rows_scroll_h
    for layer in range(1, n + 1):
        y = y_top - row_h - offset
        row = grid.op('row_{}'.format(layer))
        visible = y + row_h > 0 and y < rows_viewport_h
        if row is not None:
            try:
                row.par.y = y
                row.par.display = bool(visible)
            except Exception:
                pass
        frow = fixed_rows.op('row_{}'.format(layer)) if fixed_rows is not None else None
        if frow is not None:
            try:
                frow.par.y = y
                frow.par.display = bool(visible)
            except Exception:
                pass
        y_top -= row_h + CELL_GAP
    try:
        ui = r.op('ui')
        proxy = ui.op('grid_vscroll') if ui is not None else None
        thumb = proxy.op('scroll_thumb') if proxy is not None else None
        if proxy is not None and thumb is not None:
            h = max(1, int(float(proxy.par.h.eval())))
            thumb_h = max(18, int(round(h * min(1.0, rows_viewport_h / max(1.0, rows_scroll_h)))))
            thumb.par.x = 1
            thumb.par.w = max(2, int(float(proxy.par.w.eval())) - 2)
            thumb.par.h = thumb_h
            thumb.par.y = int(round((1.0 - value) * max(0, h - thumb_h)))
            thumb.par.display = max_scroll > 0
    except Exception:
        pass
    try:
        grid.cook(force=True)
    except Exception:
        pass
    try:
        if fixed_rows is not None:
            fixed_rows.cook(force=True)
    except Exception:
        pass
    return True


def grid_vertical_scroll_value():
    try:
        return max(0.0, min(1.0, float(_GRID_SCROLL_V)))
    except Exception:
        return 0.0


def _layout_grid_geometry():
    """Column header fixed above row body; vertical scroll on rows when layers > VISIBLE_ROWS."""
    r = _root()
    if r is None:
        return 0
    _ensure_grid_stack(r)
    grid = _ui_grid(r)
    if grid is None:
        return 0
    n = _num_layers()
    cell_w, thumb_h, cell_h = _layout_cell_size(n)
    content_w = _grid_content_w(cell_w)
    hdr_h = GRID_HDR_H
    row_h = _grid_row_h(cell_h)
    rows_scroll_h = _grid_rows_scroll_h(n, cell_h)
    rows_viewport_h = _grid_rows_viewport_h(n, cell_h)
    hbar = _grid_hscroll_thickness() if _grid_needs_hscroll(cell_w) else 0
    top_pad = _grid_header_top_pad()
    zone_h = _grid_zone_h(n, cell_h, cell_w)
    vscroll = False
    stack = _ui_grid_stack(r)
    hdr = _ui_grid_header(r)
    hdr_y = zone_h - top_pad - hdr_h
    if stack is not None:
        try:
            stack.par.x = GRID_X0
            stack.par.w = UI_W - GRID_X0
            stack.par.h = zone_h
            stack.par.hmode = 'fixed'
            stack.par.vmode = 'fixed'
            stack.par.align = 'none'
            stack.par.phscrollbar = 'on' if hbar else 'off'
            stack.par.pvscrollbar = 'off'
            stack.par.scrollbarthickness = hbar or 12
        except Exception:
            pass
    if hdr is not None:
        try:
            hdr.par.w = content_w
            hdr.par.h = hdr_h
            hdr.par.y = hdr_y
            hdr.par.x = 0
            hdr.par.hmode = 'fixed'
            hdr.par.vmode = 'fixed'
            hdr.par.phscrollbar = 'off'
            hdr.par.pvscrollbar = 'off'
        except Exception:
            pass
        corner = hdr.op('corner')
        if corner is not None:
            try:
                corner.par.x = 0
                corner.par.w = ROW_LABEL_W
                corner.par.display = False
            except Exception:
                pass
            _layout_hdr_cell(corner, hdr_h)
            _pin_scroll_label(corner)
        opacity_hdr = hdr.op('opacity_hdr')
        if opacity_hdr is None:
            try:
                opacity_hdr = hdr.create('containerCOMP', 'opacity_hdr')
            except Exception:
                opacity_hdr = None
        if opacity_hdr is not None:
            try:
                opacity_hdr.par.x = ROW_LABEL_W + CELL_GAP
                opacity_hdr.par.w = ROW_OPACITY_HDR_W
                opacity_hdr.par.h = hdr_h
                opacity_hdr.par.display = False
            except Exception:
                pass
            txt = opacity_hdr.op('label_text')
            if txt is None:
                try:
                    txt = opacity_hdr.create('textTOP', 'label_text')
                except Exception:
                    txt = None
            if txt is not None:
                _style_header_text(txt, ROW_OPACITY_HDR_W, hdr_h, 'Opacity')
                try:
                    opacity_hdr.par.top = txt
                    opacity_hdr.par.topfill = 'fit'
                except Exception:
                    pass
            _layout_hdr_cell(opacity_hdr, hdr_h)
            _pin_scroll_label(opacity_hdr)
        for col in range(1, _num_cols() + 1):
            ch = hdr.op('colhdr_{}'.format(col))
            if ch is None:
                continue
            try:
                ch.par.x = _col_x(col, cell_w)
                ch.par.w = cell_w
            except Exception:
                pass
            _layout_hdr_cell(ch, hdr_h)
    # Header and grid body are both horizontal-scroll content; a separate right-edge
    # proxy owns the visible vertical scrollbar.
    try:
        grid.par.w = content_w
        grid.par.h = rows_viewport_h
        grid.par.hmode = 'fixed'
        grid.par.vmode = 'fixed'
        grid.par.align = 'none'
        grid.par.phscrollbar = 'off' if stack is not None else 'auto'
        grid.par.pvscrollbar = 'off'
        grid.par.scrollbarthickness = 12
        try:
            grid.par.scrolloverlay = 'over'
        except Exception:
            pass
        _crop_panel_children(grid, True)
        if stack is not None:
            grid.par.y = hdr_y - CELL_GAP - rows_viewport_h
            grid.par.x = 0
    except Exception:
        pass
    # Top-down inside row grid (TD y=0 is bottom).
    y_top = rows_scroll_h
    for layer in range(1, n + 1):
        row = grid.op('row_{}'.format(layer))
        if row is None:
            continue
        try:
            row.par.w = content_w
            row.par.h = row_h
            row.par.y = y_top - row_h
            row.par.x = 0
            row.par.display = True
        except Exception:
            pass
        rl = row.op('rowlabel')
        if rl is not None:
            try:
                rl.par.x = 0
                rl.par.w = ROW_LABEL_W
                rl.par.h = cell_h - 2
                rl.par.display = False
            except Exception:
                pass
            _pin_scroll_label(rl)
            txt = rl.op('label_text')
            if txt is not None:
                _style_header_text(txt, ROW_LABEL_W, cell_h - 2, _layer_label(layer))
                rl.par.top = txt
                rl.par.topfill = 'fit'
        try:
            slider = row.op('rowopacity')
            if slider is not None:
                slider.par.display = False
        except Exception:
            pass
        for col in range(1, _num_cols() + 1):
            cell = row.op('cell_{}_{}'.format(layer, col))
            if cell is None:
                continue
            try:
                _layout_cell_geometry(cell, layer, col, cell_w, thumb_h, cell_h)
            except Exception:
                pass
        y_top -= row_h + CELL_GAP
    try:
        stack_y = float(stack.par.y.eval()) if stack is not None else 0
    except Exception:
        stack_y = 0
    _layout_fixed_grid_gutter(stack_y, zone_h, cell_h)
    try:
        ui = r.op('ui')
        proxy = ui.op('grid_vscroll') if ui is not None else None
        if proxy is None and ui is not None:
            proxy = ui.create('containerCOMP', 'grid_vscroll')
        if proxy is not None:
            scroll_w = 18
            proxy.par.x = UI_W - scroll_w
            proxy.par.y = stack_y + hdr_y - CELL_GAP - rows_viewport_h
            proxy.par.w = scroll_w
            proxy.par.h = rows_viewport_h
            proxy.par.hmode = 'fixed'
            proxy.par.vmode = 'fixed'
            proxy.par.align = 'none'
            proxy.par.phscrollbar = 'off'
            proxy.par.pvscrollbar = 'off'
            proxy.par.scrollbarthickness = 12
            proxy.par.display = False
            proxy.par.enable = False
            proxy.par.bgcolorr, proxy.par.bgcolorg, proxy.par.bgcolorb = TD_SLIDER_TRACK
            proxy.par.bgalpha = 0.85
            proxy.par.drop = 'dropno'
            proxy.par.drag = 'dragno'
            proxy.par.clickthrough = False
            thumb = proxy.op('scroll_thumb')
            if thumb is None:
                thumb = proxy.create('containerCOMP', 'scroll_thumb')
            thumb.par.bgcolorr, thumb.par.bgcolorg, thumb.par.bgcolorb = TD_SLIDER_THUMB
            thumb.par.bgalpha = 1.0
            thumb.par.clickthrough = True
            try:
                sync_grid_vertical_scroll()
            except Exception:
                pass
    except Exception:
        pass
    for row in list(grid.children):
        if row.name.startswith('row_'):
            try:
                if int(row.name.split('_')[1]) > n:
                    row.par.display = False
            except Exception:
                pass
    try:
        gutter = _ui_grid_gutter(r)
        fixed_rows = gutter.op('fixed_rows') if gutter is not None else None
        if fixed_rows is not None:
            for row in list(fixed_rows.children):
                if row.name.startswith('row_'):
                    try:
                        if int(row.name.split('_')[1]) > n:
                            row.par.display = False
                    except Exception:
                        pass
    except Exception:
        pass
    return zone_h


def repair_cell_previews():
    """Fix grid thumbnails after layout/script changes."""
    r = _root()
    if r is None:
        return
    for layer in range(1, _num_layers() + 1):
        for col in range(1, _num_cols() + 1):
            _refresh_cell_preview(layer, col)


def repair_cell_labels():
    """Name strip under each grid cell; restore header/row labels."""
    r = _root()
    if r is None:
        return
    _ensure_grid_stack(r)
    grid = _ui_grid(r)
    if grid is None:
        return
    hdr = _ui_grid_header(r)
    if hdr is not None:
        for ch in hdr.children:
            if not ch.isCOMP:
                continue
            if ch.name in ('corner', 'opacity_hdr'):
                _pin_scroll_label(ch)
            _layout_hdr_cell(ch, GRID_HDR_H)
    _layout_grid_geometry()
    for layer in range(1, _num_layers() + 1):
        row = grid.op('row_{}'.format(layer))
        if row is None:
            continue
        rl = row.op('rowlabel')
        if rl is not None:
            _pin_scroll_label(rl)
            txt = rl.op('label_text')
            if txt is not None:
                w = int(float(rl.par.w.eval())) or ROW_LABEL_W
                h = max(14, int(float(rl.par.h.eval())) or CELL_H - 2)
                _style_header_text(txt, w, h, _layer_label(layer))
                rl.par.top = txt
                rl.par.topfill = 'fit'
    try:
        ui = r.op('ui')
        if ui is not None:
            ui.par.w = UI_W
            ui.par.h = UI_H
    except Exception:
        pass
    _sync_grid_ui()


def repair_ui_drops():
    """Grid cells: drag clips between cells + Explorer file drops."""
    r = _root()
    if r is None:
        return
    try:
        _repair_all_video_playmodes()
    except Exception:
        pass
    _ensure_grid_stack(r)
    ui = r.op('ui')
    grid = _ui_grid(r)
    legacy = r.op('legacy_drop')
    for comp in (ui, _ui_grid_stack(r), _ui_grid_header(r), grid):
        if comp is None:
            continue
        try:
            comp.par.drop = 'dropno'
            comp.par.drag = 'dragno'
            comp.par.clickthrough = False
        except Exception:
            pass
    if grid is not None:
        cb = grid.op('cell_dragdrop')
        if cb is not None:
            try:
                cb.text = CELL_DRAGDROP
                cb.par.language = 'python'
            except Exception:
                pass
        hdr = _ui_grid_header(r)
        if hdr is not None:
            try:
                hdr.par.drop = 'dropno'
                hdr.par.drag = 'dragno'
            except Exception:
                pass
            for ch in hdr.children:
                if ch.isCOMP:
                    try:
                        ch.par.drop = 'dropno'
                        ch.par.drag = 'dragno'
                    except Exception:
                        pass
        for layer in range(1, _num_layers() + 1):
            row = grid.op('row_{}'.format(layer))
            if row is None:
                continue
            try:
                row.par.drop = 'dropno'
                row.par.drag = 'dragno'
            except Exception:
                pass
            for ch in row.children:
                if ch.isCOMP and not ch.name.startswith('cell_'):
                    try:
                        ch.par.drop = 'dropno'
                        ch.par.drag = 'dragno'
                    except Exception:
                        pass
            for col in range(1, _num_cols() + 1):
                cell = row.op('cell_{}_{}'.format(layer, col))
                if cell is None:
                    continue
                _repair_cell_dragdrop(cell, grid, legacy)
    bar = ui.op('scene_bar') if ui else None
    if bar is not None:
        _repair_scene_bar_dragdrop(bar)
    try:
        _ensure_global_fx_dragdrop_dat()
        _ensure_cell_fx_dragdrop_dat()
        _wire_global_fx_chain()
        _ensure_params_column_tabs()
        _refresh_global_fx_ui()
        _refresh_layer_fx_ui()
    except Exception:
        pass
    print('Grid cells accept drag-reposition and Explorer drops; scene buttons accept drag-reorder')


def _repair_cell_dragdrop(cell, grid, legacy):
    cb = grid.op('cell_dragdrop') if grid else None
    try:
        cell.par.builtindrop = False
        cell.par.clickthrough = False
        cell.par.drag = 'usecallbacks'
        cell.par.drop = 'usecallbacks'
        if legacy is not None:
            cell.par.dropscript = legacy
        if cb is not None:
            cell.par.dragdropcallbacks = cb
    except Exception:
        pass
    for part_name in ('cell_thumb', 'cell_name'):
        part = cell.op(part_name)
        if part is None:
            continue
        try:
            part.par.clickthrough = True
            part.par.drop = 'dropparent'
            part.par.drag = 'dragno'
        except Exception:
            pass
