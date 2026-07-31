import os

from performance_grid.builder.helpers_ui import _wire_scene_bar_dragdrop
from performance_grid.constants_builder import *  # noqa: F401,F403

def _ensure_column_xfade_nodes(root):
    """Builder/repair: chain_prev + chain_next -> column_xfade."""
    if root is None:
        return None, None, None
    prev = root.op('chain_prev')
    nxt = root.op('chain_next')
    cross = root.op('column_xfade')
    if prev is None:
        prev = root.create('selectTOP', 'chain_prev')
    if nxt is None:
        nxt = root.create('selectTOP', 'chain_next')
    if cross is None:
        cross = root.create('crossTOP', 'column_xfade')
        try:
            prev.outputConnectors[0].connect(cross.inputConnectors[0])
            nxt.outputConnectors[0].connect(cross.inputConnectors[1])
        except Exception:
            pass
    for node in (prev, nxt, cross):
        _bind_canvas_res(node)
    return prev, nxt, cross


def _layout_thumb_h(cell_w):
    return max(27, int(round(cell_w * 9.0 / 16.0)))


def _layout_cell_w_for_viewport():
    avail = UI_W - GRID_X0
    return max(64, (avail - (VISIBLE_COLS - 1) * CELL_GAP) // VISIBLE_COLS)


def _layout_cell_size(num_layers=None):
    if num_layers is None:
        num_layers = DEFAULT_LAYERS
    cell_w = _layout_cell_w_for_viewport()
    thumb_h = _layout_thumb_h(cell_w)
    cell_h = thumb_h + CELL_LABEL_H
    sbh = SCENE_BAR_H + SCENE_BAR_TOP_PAD + SCENE_GRID_GAP
    bottom_h = BOTTOM_ZONE_MIN + 4
    hdr_h = GRID_HDR_H
    grid_h = UI_H - sbh - bottom_h - 8
    overhead = hdr_h + CELL_GAP + num_layers * 2 + max(0, num_layers - 1) * CELL_GAP
    usable_h = max(0, grid_h - overhead)
    if num_layers < 1:
        num_layers = 1
    max_cell_h = max(CELL_LABEL_H + 27, int(usable_h / num_layers))
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
    return NUM_COLS * _cell_step(cell_w)


def _col_x(col, cell_w=None):
    return (int(col) - 1) * _cell_step(cell_w)


def _setup_grid_scroll(grid, stack=None):
    needs_h = _grid_content_w() > (UI_W - GRID_X0) + 2
    hbar = 12 if needs_h else 0
    if stack is not None:
        _set_par(stack, 'x', GRID_X0)
        _set_par(stack, 'w', UI_W - GRID_X0)
        _set_par(stack, 'phscrollbar', 'on' if needs_h else 'off')
        _set_par(stack, 'pvscrollbar', 'off')
        try:
            stack.par.scrollbarthickness = hbar or 12
        except Exception:
            pass
    _set_par(grid, 'phscrollbar', 'off')
    _set_par(grid, 'pvscrollbar', 'off')
    try:
        grid.par.scrollbarthickness = 12
    except Exception:
        pass


def _pin_scroll_label(comp):
    try:
        comp.par.scrolloverlay = 'over'
    except Exception:
        pass


def _max_grid_col(grid, hdr=None):
    if hdr is None and grid is not None:
        hdr = grid.op('header_row')
        if hdr is None:
            parent = grid.parent
            if parent is not None:
                hdr = parent.op('grid_header')
    mx = 0
    if hdr is not None:
        for ch in hdr.children:
            if ch.name.startswith('colhdr_'):
                try:
                    mx = max(mx, int(ch.name.split('_')[1]))
                except Exception:
                    pass
    return mx


def _collect_panel_paths(root):
    ui = root.op('ui')
    if ui is None:
        return []
    stack = ui.op('grid_stack')
    grid = stack.op('grid') if stack is not None else ui.op('grid')
    if grid is None:
        return []
    paths = []
    try:
        if stack is not None:
            paths.append(stack.path)
    except Exception:
        pass
    try:
        paths.append(grid.path)
    except Exception:
        pass
    bar = ui.op('scene_bar')
    if bar is not None:
        for ch in bar.children:
            if ch.isCOMP:
                paths.append(ch.path)
    hdr = stack.op('grid_header') if stack is not None else None
    if hdr is None:
        hdr = ui.op('grid_header')
    if hdr is None:
        hdr = grid.op('header_row')
    if hdr is not None:
        for ch in hdr.children:
            if ch.isCOMP and ch.name.startswith('colhdr_'):
                paths.append(ch.path)
    n = DEFAULT_LAYERS
    try:
        n = max(MIN_LAYERS, min(MAX_LAYERS, int(float(root.par.Numlayers.eval()))))
    except Exception:
        pass
    gutter = ui.op('grid_gutter')
    if gutter is not None:
        header = gutter.op('fixed_header')
        if header is not None:
            for ch in header.children:
                if ch.isCOMP:
                    paths.append(ch.path)
        fixed_rows = gutter.op('fixed_rows') or gutter
        for layer in range(1, n + 1):
            row = fixed_rows.op('row_{}'.format(layer))
            if row is None:
                continue
            rl = row.op('rowlabel')
            if rl is not None:
                paths.append(rl.path)
            opacity = row.op('rowopacity')
            if opacity is not None:
                paths.append(opacity.path)
    for layer in range(1, n + 1):
        row = grid.op('row_{}'.format(layer))
        if row is None:
            continue
        rl = row.op('rowlabel')
        if rl is not None:
            paths.append(rl.path)
        for col in range(1, NUM_COLS + 1):
            cell = row.op('cell_{}_{}'.format(layer, col))
            if cell is not None:
                paths.append(cell.path)
    return paths


def _update_layer_par_limits(root):
    n = DEFAULT_LAYERS
    try:
        n = max(MIN_LAYERS, min(MAX_LAYERS, int(float(root.par.Numlayers.eval()))))
    except Exception:
        pass
    for pname in ('Activecolumn', 'Selectedcol'):
        try:
            p = getattr(root.par, pname)
            p.normMax = NUM_COLS
            if float(p.eval()) > NUM_COLS:
                p.val = NUM_COLS
        except Exception:
            pass
    for pname in ('Activelayer', 'Selectedlayer', 'Numlayers'):
        try:
            p = getattr(root.par, pname)
            p.normMax = MAX_LAYERS
            if pname != 'Numlayers' and float(p.eval()) > n:
                p.val = n
        except Exception:
            pass


def _grid_custom_page(root):
    page = None
    try:
        for pg in root.customPages:
            if pg.name == 'Grid':
                page = pg
                break
    except Exception:
        pass
    if page is None:
        page = root.appendCustomPage('Grid')
    return page


def _first_par(par_or_list):
    try:
        if isinstance(par_or_list, (list, tuple)):
            return par_or_list[0]
    except Exception:
        pass
    return par_or_list


def _ensure_int_par(root, page, name, label, default, mn, mx):
    try:
        p = getattr(root.par, name)
    except Exception:
        p = _first_par(page.appendInt(name, label=label))
    try:
        p.default = default
        p.min = mn
        p.max = mx
        p.normMin = mn
        p.normMax = mx
        value = int(float(p.eval()))
        p.val = max(mn, min(mx, value))
    except Exception:
        try:
            p.val = default
        except Exception:
            pass
    return p


def _ensure_str_par(root, page, name, label, default):
    try:
        p = getattr(root.par, name)
    except Exception:
        p = _first_par(page.appendStr(name, label=label))
    try:
        if not str(p.eval()):
            p.val = default
    except Exception:
        pass
    return p


def _ensure_grid_custom_pars(root):
    """Repair core Grid custom parameters after partial script reloads."""
    if root is None:
        return
    page = _grid_custom_page(root)
    for name, label, default, mn, mx in (
        ('Numscenes', 'Scenes', DEFAULT_SCENES, MIN_SCENES, MAX_SCENES),
        ('Activescene', 'Active Scene', 1, MIN_SCENES, MAX_SCENES),
        ('Numlayers', 'Layers', DEFAULT_LAYERS, MIN_LAYERS, MAX_LAYERS),
        ('Numcols', 'Columns', NUM_COLS, 1, 256),
        ('Activelayer', 'Active Layer', 1, 1, MAX_LAYERS),
        ('Activecolumn', 'Active Column', 1, 1, NUM_COLS),
        ('Selectedlayer', 'Layer', 1, 1, MAX_LAYERS),
        ('Selectedcol', 'Column', 1, 1, NUM_COLS),
    ):
        _ensure_int_par(root, page, name, label, default, mn, mx)
    _ensure_str_par(root, page, 'Status', 'Status', 'Ready')
    _update_layer_par_limits(root)


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


def _ensure_numlayers_par(root):
    try:
        p = root.par.Numlayers
        p.normMax = MAX_LAYERS
        return
    except Exception:
        pass
    page = None
    for pg in root.customPages:
        if pg.name == 'Grid':
            page = pg
            break
    if page is None:
        page = root.appendCustomPage('Grid')
    p = page.appendInt('Numlayers', label='Layers')
    p.default = DEFAULT_LAYERS
    p.val = DEFAULT_LAYERS
    p.min = MIN_LAYERS
    p.max = MAX_LAYERS


def _ensure_scenes_par(root):
    try:
        p = root.par.Numscenes
        p.normMax = MAX_SCENES
        try:
            p2 = root.par.Activescene
            p2.normMax = MAX_SCENES
        except Exception:
            pass
        return
    except Exception:
        pass
    page = None
    for pg in root.customPages:
        if pg.name == 'Grid':
            page = pg
            break
    if page is None:
        page = root.appendCustomPage('Grid')
    p = page.appendInt('Numscenes', label='Scenes')
    p.default = DEFAULT_SCENES
    p.val = DEFAULT_SCENES
    p.min = MIN_SCENES
    p.max = MAX_SCENES
    p2 = page.appendInt('Activescene', label='Active Scene')
    p2.default = 1
    p2.val = 1
    p2.min = MIN_SCENES
    p2.max = MAX_SCENES


def _make_scene_button(parent, name, label):
    btn = parent.create('containerCOMP', name)
    _set_par(btn, 'w', SCENE_BTN_W)
    _set_par(btn, 'h', SCENE_BTN_H)
    _set_par(btn, 'hmode', 'fixed')
    _set_par(btn, 'vmode', 'fixed')
    _pass_drop(btn)
    _set_par(btn, 'bgalpha', SCENE_CONTROL_TILE_ALPHA)
    _set_par(btn, 'bgcolorr', SCENE_BTN_TILE_BG[0])
    _set_par(btn, 'bgcolorg', SCENE_BTN_TILE_BG[1])
    _set_par(btn, 'bgcolorb', SCENE_BTN_TILE_BG[2])
    txt = btn.create('textTOP', 'label_text')
    _set_par(txt, 'text', label)
    _set_par(txt, 'font', TD_FONT)
    _set_par(txt, 'fontautosize', 'off')
    _set_par(txt, 'fontsizex', GRID_FONT_SIZE)
    _set_par(txt, 'fontsizey', GRID_FONT_SIZE)
    _set_par(txt, 'keepfontratio', True)
    _set_par(txt, 'resolutionw', SCENE_BTN_W)
    _set_par(txt, 'resolutionh', SCENE_BTN_H)
    _set_par(txt, 'bgalpha', 0.0)
    _set_par(txt, 'alignx', 'center')
    _set_par(txt, 'aligny', 'center')
    _set_par(txt, 'fontcolorr', TD_TEXT_LABEL[0])
    _set_par(txt, 'fontcolorg', TD_TEXT_LABEL[1])
    _set_par(txt, 'fontcolorb', TD_TEXT_LABEL[2])
    _set_par(btn, 'top', txt)
    _set_par(btn, 'topfill', SCENE_BTN_TOPFILL)
    try:
        txt.par.clickthrough = True
        btn.par.clickthrough = False
    except Exception:
        pass
    return btn


def _make_scene_label(parent):
    comp = parent.op('scene_label')
    if comp is None:
        comp = parent.create('containerCOMP', 'scene_label')
    _set_par(comp, 'w', 48)
    _set_par(comp, 'h', SCENE_BTN_H)
    _set_par(comp, 'hmode', 'fixed')
    _set_par(comp, 'vmode', 'fixed')
    _set_par(comp, 'bgalpha', 0)
    _pass_drop(comp)
    txt = comp.op('label_text')
    if txt is None:
        txt = comp.create('textTOP', 'label_text')
    _set_par(txt, 'text', 'Scene')
    _set_par(txt, 'font', TD_FONT)
    _set_par(txt, 'fontautosize', 'off')
    _set_par(txt, 'fontsizex', GRID_FONT_SIZE)
    _set_par(txt, 'fontsizey', GRID_FONT_SIZE)
    _set_par(txt, 'keepfontratio', True)
    _set_par(txt, 'resolutionw', 48)
    _set_par(txt, 'resolutionh', SCENE_BTN_H)
    _set_par(txt, 'bgalpha', 0.0)
    _set_par(txt, 'alignx', 'center')
    _set_par(txt, 'aligny', 'center')
    _set_par(txt, 'fontcolorr', TD_TEXT_LABEL[0])
    _set_par(txt, 'fontcolorg', TD_TEXT_LABEL[1])
    _set_par(txt, 'fontcolorb', TD_TEXT_LABEL[2])
    _set_par(comp, 'top', txt)
    _set_par(comp, 'topfill', SCENE_BTN_TOPFILL)
    try:
        txt.par.clickthrough = True
        comp.par.clickthrough = True
    except Exception:
        pass
    return comp


def _make_open_effects_folder_link(parent):
    w = 168
    # Keep clear of the performance readouts on the top-right.
    perf_readout_reserved_w = 420
    comp = parent.op('open_effects_folder')
    if comp is None:
        comp = parent.create('containerCOMP', 'open_effects_folder')
    _set_par(comp, 'x', max(0, UI_W - perf_readout_reserved_w - w - 18))
    _set_par(comp, 'y', SCENE_BAR_CONTENT_Y)
    _set_par(comp, 'w', w)
    _set_par(comp, 'h', SCENE_BTN_H)
    _set_par(comp, 'hmode', 'fixed')
    _set_par(comp, 'vmode', 'fixed')
    _set_par(comp, 'bgalpha', SCENE_CONTROL_TILE_ALPHA)
    _set_par(comp, 'bgcolorr', SCENE_BTN_TILE_BG[0])
    _set_par(comp, 'bgcolorg', SCENE_BTN_TILE_BG[1])
    _set_par(comp, 'bgcolorb', SCENE_BTN_TILE_BG[2])
    _set_par(comp, 'display', True)
    _set_par(comp, 'enable', True)
    _pass_drop(comp)
    txt = comp.op('label_text')
    if txt is None:
        txt = comp.create('textTOP', 'label_text')
    _set_par(txt, 'text', 'Open Effects Folder')
    _set_par(txt, 'font', TD_FONT)
    _set_par(txt, 'fontautosize', 'off')
    _set_par(txt, 'fontsizex', GRID_FONT_SIZE)
    _set_par(txt, 'fontsizey', GRID_FONT_SIZE)
    _set_par(txt, 'keepfontratio', True)
    _set_par(txt, 'resolutionw', w)
    _set_par(txt, 'resolutionh', SCENE_BTN_H)
    _set_par(txt, 'bgalpha', 0.0)
    _set_par(txt, 'alignx', 'center')
    _set_par(txt, 'aligny', 'center')
    _set_par(txt, 'fontcolorr', TD_TEXT_LABEL[0])
    _set_par(txt, 'fontcolorg', TD_TEXT_LABEL[1])
    _set_par(txt, 'fontcolorb', TD_TEXT_LABEL[2])
    _set_par(comp, 'top', txt)
    _set_par(comp, 'topfill', SCENE_BTN_TOPFILL)
    try:
        txt.par.clickthrough = True
        comp.par.clickthrough = False
    except Exception:
        pass
    return comp


def _build_brand_logo(bar):
    """White SONOMIKA wordmark at top-left of scene bar (works before logic onInit)."""
    logo = bar.op('brand_logo')
    if logo is None:
        logo = bar.create('containerCOMP', 'brand_logo')
    _set_par(logo, 'x', SCENE_BAR_LOGO_X + SCENE_BAR_LOGO_X_NUDGE)
    logo_y = SCENE_BAR_CONTENT_Y + max(0, (SCENE_BTN_H - LOGO_H) // 2) + SCENE_BAR_LOGO_Y_NUDGE
    _set_par(logo, 'y', logo_y)
    _set_par(logo, 'w', LOGO_W)
    _set_par(logo, 'h', LOGO_H)
    _set_par(logo, 'display', True)
    _set_par(logo, 'enable', True)
    try:
        logo.par.clickthrough = True
        logo.par.bgalpha = 0.0
    except Exception:
        pass
    logo_path = _build_logo_path()
    if logo_path:
        src = logo.op('logo_src')
        if src is None:
            try:
                src = logo.create('moviefileinTOP', 'logo_src')
            except Exception:
                src = None
        if src is not None:
            try:
                src.par.outputresolution = 'useinput'
                src.par.play = True
                src.par.file = logo_path.replace('\\', '/')
                src.par.reloadpulse.pulse()
                logo.par.top = src.path
                logo.par.topfill = 'best'
                txt = logo.op('logo_text')
                if txt is not None:
                    try:
                        txt.par.text = ''
                    except Exception:
                        pass
                return logo
            except Exception:
                pass
    txt = logo.op('logo_text')
    if txt is None:
        txt = logo.create('textTOP', 'logo_text')
    _set_par(txt, 'text', 'SONOMIKA')
    _set_par(txt, 'font', TD_FONT)
    _set_par(txt, 'fontautosize', 'off')
    _set_par(txt, 'fontsizex', GRID_FONT_SIZE)
    _set_par(txt, 'fontsizey', GRID_FONT_SIZE)
    _set_par(txt, 'keepfontratio', True)
    _set_par(txt, 'resolutionw', LOGO_W)
    _set_par(txt, 'resolutionh', LOGO_H)
    _set_par(txt, 'bgalpha', 0.0)
    _set_par(txt, 'alignx', 'left')
    _set_par(txt, 'aligny', 'center')
    _set_par(txt, 'fontcolorr', TD_TEXT_ACTIVE[0])
    _set_par(txt, 'fontcolorg', TD_TEXT_ACTIVE[1])
    _set_par(txt, 'fontcolorb', TD_TEXT_ACTIVE[2])
    try:
        txt.par.bold = True
    except Exception:
        pass
    _set_par(logo, 'top', txt)
    _set_par(logo, 'topfill', 'best')
    return logo


def _build_logo_path():
    rels = (
        ('assets', 'sonomika', 'sonomika_logo.png'),
        ('assets', 'sonomika_logo.png'),
        ('SonomikaTD', 'assets', 'sonomika', 'sonomika_logo.png'),
        ('SonomikaTD', 'assets', 'sonomika_logo.png'),
    )
    candidates = []
    try:
        pf = project.folder.replace('\\', '/')
        for rel in rels:
            candidates.append(os.path.normpath(os.path.join(pf, *rel)).replace('\\', '/'))
    except Exception:
        pass
    env = os.environ.get('SONOMIKA_TD_ROOT', '').strip()
    if env:
        candidates.append(
            os.path.normpath(os.path.join(env, 'assets', 'sonomika', 'sonomika_logo.png')).replace('\\', '/')
        )
        candidates.append(
            os.path.normpath(os.path.join(env, 'assets', 'sonomika_logo.png')).replace('\\', '/')
        )
    seen = set()
    for path in candidates:
        if not path or path in seen:
            continue
        seen.add(path)
        if os.path.isfile(path):
            try:
                pf = os.path.normpath(str(project.folder or '')).replace('\\', '/')
                rel = os.path.relpath(path, pf).replace('\\', '/')
                if rel and not rel.startswith('..') and not os.path.isabs(rel):
                    return rel
            except Exception:
                pass
            return path
    return ''


def _build_scene_bar(ui, root):
    bar = ui.op('scene_bar')
    if bar is None:
        bar = ui.create('containerCOMP', 'scene_bar')
    _set_par(bar, 'x', 0)
    _set_par(bar, 'y', 0)
    _set_par(bar, 'w', UI_W)
    _set_par(bar, 'h', SCENE_BAR_H)
    _set_par(bar, 'hmode', 'fixed')
    _set_par(bar, 'vmode', 'fixed')
    _set_par(bar, 'align', 'none')
    _set_par(bar, 'bgalpha', SCENE_BAR_BG_ALPHA)
    _pass_drop(bar)
    _ensure_scenes_par(root)
    logo = _build_brand_logo(bar)
    x = SCENE_BAR_LOGO_PAD + LOGO_W + SCENE_BAR_LOGO_GAP
    try:
        logic = root.op('logic').module
        if hasattr(logic, '_ensure_scene_logo'):
            logic._ensure_scene_logo(bar)
        if hasattr(logic, '_layout_scene_logo'):
            logic._layout_scene_logo(bar)
        if hasattr(logic, '_scene_bar_controls_x0'):
            x = int(logic._scene_bar_controls_x0())
    except Exception:
        pass
    paths = []
    if logo is not None:
        paths.append(logo.path)
    for name in ('scene_to_start', 'scene_play', 'scene_pause'):
        btn = bar.op(name)
        if btn is None:
            try:
                logic = root.op('logic').module
                if hasattr(logic, '_create_scene_transport_button'):
                    btn = logic._create_scene_transport_button(bar, name)
                else:
                    btn = _make_scene_button(bar, name, '')
            except Exception:
                btn = _make_scene_button(bar, name, '')
        try:
            wired = False
            try:
                logic = root.op('logic').module
                if hasattr(logic, '_wire_transport_button_icon'):
                    wired = bool(logic._wire_transport_button_icon(btn, name))
                if wired and hasattr(logic, '_layout_transport_icon_view'):
                    logic._layout_transport_icon_view(btn)
                if hasattr(logic, '_apply_transport_btn_style'):
                    logic._apply_transport_btn_style(btn)
            except Exception:
                pass
            if wired:
                try:
                    btn.par.topfill = SCENE_BTN_TOPFILL
                except Exception:
                    pass
            else:
                txt = btn.op('label_text')
                if txt is not None:
                    txt.par.resolutionw = SCENE_BTN_W
                    txt.par.resolutionh = SCENE_BTN_H
                    txt.par.fontsizex = GRID_FONT_SIZE
                    txt.par.fontsizey = GRID_FONT_SIZE
                    txt.par.keepfontratio = True
                    txt.par.alignx = 'center'
                    txt.par.aligny = 'center'
                    btn.par.top = txt
                    btn.par.topfill = SCENE_BTN_TOPFILL
        except Exception:
            pass
        _set_par(btn, 'x', x)
        _set_par(btn, 'y', SCENE_BAR_CONTENT_Y)
        _set_par(btn, 'display', True)
        paths.append(btn.path)
        x += SCENE_BTN_W + 4
    try:
        logic = root.op('logic').module
        if hasattr(logic, '_layout_scene_bpm'):
            x = int(logic._layout_scene_bpm(bar, x))
    except Exception:
        x += 16
    scene_label = _make_scene_label(bar)
    _set_par(scene_label, 'x', x)
    _set_par(scene_label, 'y', SCENE_BAR_CONTENT_Y)
    _set_par(scene_label, 'display', True)
    x += 48 + 8
    n = DEFAULT_SCENES
    try:
        n = max(MIN_SCENES, min(MAX_SCENES, int(float(root.par.Numscenes.eval()))))
    except Exception:
        pass
    for s in range(1, n + 1):
        btn = bar.op('scene_btn_{}'.format(s))
        if btn is None:
            btn = _make_scene_button(bar, 'scene_btn_{}'.format(s), str(s))
        _set_par(btn, 'x', x)
        _set_par(btn, 'y', SCENE_BAR_CONTENT_Y)
        _set_par(btn, 'display', True)
        paths.append(btn.path)
        x += SCENE_BTN_W + 4
    add = bar.op('scene_add')
    if add is None:
        add = _make_scene_button(bar, 'scene_add', '+')
        try:
            add.par.bgalpha = SCENE_CONTROL_TILE_ALPHA
            add.par.bgcolorr, add.par.bgcolorg, add.par.bgcolorb = SCENE_BTN_TILE_BG
        except Exception:
            pass
    _set_par(add, 'x', x)
    _set_par(add, 'y', SCENE_BAR_CONTENT_Y)
    _set_par(add, 'display', True)
    paths.append(add.path)
    effects = _make_open_effects_folder_link(bar)
    if effects is not None:
        paths.append(effects.path)
    _wire_scene_bar_dragdrop(bar)
    return bar, paths


