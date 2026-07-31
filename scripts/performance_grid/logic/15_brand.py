import os
_LOGO_ASSET_NAME = 'sonomika_logo.png'
_ACCORDION_ICON_FILE = 'accord.png'
_TRANSPORT_ICON_FILES = {
    # PNG raster of assets/angles-left-solid-full.svg (moviefileinTOP)
    'scene_to_start': 'transport_to_start.png',
    'scene_play': 'transport_play.png',
    'scene_pause': 'transport_pause.png',
}


def _scene_bar_controls_x0():
    """X where play / scene controls align with the left edge of clip columns."""
    return GRID_X0


def _scene_bar_logo_y():
    """Center wordmark with scene/transport tiles (panel y is from bottom)."""
    return (
        SCENE_BAR_CONTENT_Y
        + max(0, (SCENE_BTN_H - LOGO_H) // 2)
        + SCENE_BAR_LOGO_Y_NUDGE
    )


def _scene_bar_logo_x():
    """Align logo with Layer column titles (centered in ROW_LABEL_W)."""
    try:
        return int(SCENE_BAR_LOGO_X) + int(SCENE_BAR_LOGO_X_NUDGE)
    except Exception:
        return max(SCENE_BAR_LOGO_PAD, (ROW_LABEL_W - 36) // 2) + 5


def _ui_asset_path(filename):
    """Resolve PNG under assets/; prefer path relative to project.folder."""
    filename = str(filename or '').strip()
    if not filename:
        return ''
    # Release builds embed UI media in /project1's virtual file system so the
    # .toe remains portable when distributed without the assets directory.
    try:
        owner = op('/project1')
        for key in ('assets/sonomika/' + filename, 'assets/' + filename):
            if owner is not None:
                hits = owner.vfs.find(pattern=key)
                if hits:
                    return hits[0].virtualPath
    except Exception:
        pass
    rel_paths = (
        ('assets', 'sonomika', filename),
        ('assets', filename),
        ('SonomikaTD', 'assets', 'sonomika', filename),
        ('SonomikaTD', 'assets', filename),
    )
    candidates = []

    def _add_dir(base):
        if not base:
            return
        base = os.path.normpath(base).replace('\\', '/')
        for rel in rel_paths:
            candidates.append(os.path.normpath(os.path.join(base, *rel)).replace('\\', '/'))

    try:
        _add_dir(project.folder)
    except Exception:
        pass
    try:
        pf = os.path.dirname(os.path.normpath(project.file))
        _add_dir(pf)
        d = pf
        for _ in range(8):
            parent = os.path.dirname(d)
            if not parent or parent == d:
                break
            d = parent
            _add_dir(d)
    except Exception:
        pass
    try:
        r = _root()
        if r is not None:
            _add_dir(r.project.folder)
    except Exception:
        pass
    env = os.environ.get('SONOMIKA_TD_ROOT', '').strip()
    if env:
        _add_dir(env)
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        candidates.append(
            os.path.normpath(os.path.join(here, '..', '..', 'assets', filename)).replace('\\', '/')
        )
    except Exception:
        pass
    seen = set()
    for p in candidates:
        if not p or p in seen:
            continue
        seen.add(p)
        if os.path.isfile(p):
            return _project_rel_ui_asset_path(p)
    return ''


def _project_rel_ui_asset_path(path):
    """Store UI asset paths relative to project.folder when the file lives there."""
    path = os.path.normpath(str(path or '')).replace('\\', '/')
    if not path:
        return ''
    try:
        pf = os.path.normpath(str(project.folder or '')).replace('\\', '/')
        if pf:
            rel = os.path.relpath(path, pf).replace('\\', '/')
            if rel and not rel.startswith('..') and not os.path.isabs(rel):
                return rel
    except Exception:
        pass
    return path


def _logo_path():
    return _ui_asset_path(_LOGO_ASSET_NAME)


def _accordion_icon_path():
    return _ui_asset_path(_ACCORDION_ICON_FILE)


def _transport_icon_path(button_name):
    return _ui_asset_path(_TRANSPORT_ICON_FILES.get(str(button_name or '').strip(), ''))


def _set_par_safe(op_node, name, value):
    try:
        par = getattr(op_node.par, name)
    except Exception:
        return False
    try:
        par.val = value
        return True
    except Exception:
        return False


def _style_logo_text(txt, w, h, label='SONOMIKA'):
    txt.par.text = label
    txt.par.resolutionw = max(64, int(w))
    txt.par.resolutionh = max(14, int(h))
    _apply_grid_font(txt)
    try:
        txt.par.font = TD_FONT
    except Exception:
        pass
    txt.par.bgalpha = 0.0
    txt.par.alignx = 'left'
    txt.par.aligny = 'center'
    txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = TD_TEXT_ACTIVE
    try:
        txt.par.bold = True
    except Exception:
        pass


def _top_has_image(src):
    if src is None:
        return False
    try:
        src.cook(force=True)
        return int(src.width) > 0 and int(src.height) > 0
    except Exception:
        return False


def _logo_src_has_image(src):
    return _top_has_image(src)


def _transport_icon_tile_size(btn=None):
    """Raster / panel size for the transport glyph (full button tile)."""
    w, h = int(SCENE_BTN_W), int(SCENE_BTN_H)
    if btn is not None:
        try:
            w = max(8, int(btn.par.w))
            h = max(8, int(btn.par.h))
        except Exception:
            pass
    return w, h


def _configure_transport_icon_fit(fit, tile_w=None, tile_h=None):
    """Letterbox PNG centered in the button; scale shrinks from tile center."""
    if fit is None:
        return
    if tile_w is None or tile_h is None:
        tile_w, tile_h = _transport_icon_tile_size()
    scale = max(0.15, min(1.0, float(TRANSPORT_ICON_SCALE)))
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


def _layout_transport_icon_view(btn):
    """Re-apply fitTOP centering after button resize."""
    if btn is None:
        return
    view = btn.op('icon_view')
    if view is not None:
        try:
            view.destroy()
        except Exception:
            pass
    fit = btn.op('icon_fit')
    if fit is not None:
        tw, th = _transport_icon_tile_size(btn)
        _configure_transport_icon_fit(fit, tw, th)


def _connect_top_chain(nodes):
    """Wire nodes[0] -> nodes[1] -> ... in order."""
    for i in range(len(nodes) - 1):
        a, b = nodes[i], nodes[i + 1]
        if a is None or b is None:
            return False
        try:
            if not b.inputConnectors[0].connections or b.inputConnectors[0].connections[0].owner != a:
                a.outputConnectors[0].connect(b.inputConnectors[0])
        except Exception:
            return False
    return True


def _wire_transport_button_icon(btn, button_name):
    """PNG on button background; fitTOP justify centers (default is bottom-left)."""
    path = _transport_icon_path(button_name)
    if not path or btn is None:
        return False
    for old_name in ('icon_display', 'icon_inv', 'icon_mono', 'icon_view'):
        old = btn.op(old_name)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass
    src = btn.op('icon_src')
    if src is not None and src.opType != 'moviefileinTOP':
        try:
            src.destroy()
        except Exception:
            pass
        src = None
    try:
        if src is None:
            src = btn.create('moviefileinTOP', 'icon_src')
        _set_par_safe(src, 'outputresolution', 'useinput')
        _set_par_safe(src, 'play', True)
        src.par.file = path.replace('\\', '/')
        try:
            src.par.reloadpulse.pulse()
        except Exception:
            pass
        if not _top_has_image(src):
            return False
    except Exception:
        return False
    fit = btn.op('icon_fit')
    if fit is None:
        try:
            fit = btn.create('fitTOP', 'icon_fit')
        except Exception:
            fit = None
    tile_w, tile_h = _transport_icon_tile_size(btn)
    if fit is not None:
        _configure_transport_icon_fit(fit, tile_w, tile_h)
        if not _connect_top_chain([src, fit]):
            try:
                src.outputConnectors[0].connect(fit.inputConnectors[0])
            except Exception:
                pass
    try:
        if fit is not None:
            btn.par.top = fit.path
            btn.par.topfill = SCENE_BTN_TOPFILL
        btn.par.clickthrough = False
        txt = btn.op('label_text')
        if txt is not None:
            try:
                txt.par.text = ''
                txt.par.clickthrough = True
            except Exception:
                pass
    except Exception:
        return False
    return True


def _wire_logo_image(logo, path):
    """Use PNG wordmark when available; text fallback handles unsupported media cases."""
    old = logo.op('logo_invert')
    if old is not None:
        try:
            old.destroy()
        except Exception:
            pass
    src = logo.op('logo_src')
    if src is not None and src.opType != 'moviefileinTOP':
        try:
            src.destroy()
        except Exception:
            pass
        src = None
    try:
        if src is None:
            src = logo.create('moviefileinTOP', 'logo_src')
        _set_par_safe(src, 'outputresolution', 'useinput')
        _set_par_safe(src, 'play', True)
        src.par.file = path.replace('\\', '/')
        try:
            src.par.reloadpulse.pulse()
        except Exception:
            pass
        if not _logo_src_has_image(src):
            return False
    except Exception:
        return False
    try:
        logo.par.top = src.path
        logo.par.topfill = 'best'
        logo.par.display = True
        logo.par.enable = True
        txt = logo.op('logo_text')
        if txt is not None:
            try:
                txt.par.text = ''
            except Exception:
                pass
    except Exception:
        return False
    return True


def _wire_logo_text(logo):
    """White wordmark text (always visible fallback)."""
    txt = logo.op('logo_text')
    if txt is None:
        txt = logo.create('textTOP', 'logo_text')
    _style_logo_text(txt, LOGO_W, LOGO_H, 'SONOMIKA')
    try:
        txt.cook(force=True)
    except Exception:
        pass
    try:
        logo.par.top = txt
        logo.par.topfill = 'best'
        logo.par.display = True
        logo.par.enable = True
    except Exception:
        pass
    return True


def _ensure_scene_logo(bar):
    """Top-left brand on scene bar (not top-right — perf readouts use the right side)."""
    if bar is None:
        return None
    logo = bar.op('brand_logo')
    if logo is None:
        logo = bar.create('containerCOMP', 'brand_logo')
    try:
        logo.par.drop = 'dropno'
        logo.par.drag = 'dragno'
        logo.par.clickthrough = True
        logo.par.bgcolorr = 0.0
        logo.par.bgcolorg = 0.0
        logo.par.bgcolorb = 0.0
        logo.par.bgalpha = 0.0
        logo.par.display = True
        logo.par.enable = True
    except Exception:
        pass
    path = _logo_path()
    used_image = False
    if path:
        try:
            used_image = _wire_logo_image(logo, path)
        except Exception as exc:
            print('Logo image failed:', exc)
            used_image = False
    if not used_image:
        _wire_logo_text(logo)
    try:
        logo.move(bar, index=max(0, bar.numChildren - 1))
    except Exception:
        pass
    return logo


def _layout_scene_logo(bar):
    logo = _ensure_scene_logo(bar)
    if logo is None:
        return
    try:
        logo.par.display = True
        logo.par.enable = True
        logo.par.x = _scene_bar_logo_x()
        logo.par.y = _scene_bar_logo_y()
        logo.par.w = LOGO_W
        logo.par.h = LOGO_H
        logo.par.hmode = 'fixed'
        logo.par.vmode = 'fixed'
        logo.par.align = 'none'
    except Exception:
        pass
