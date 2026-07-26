SCENE_BPM_W = 86
SCENE_BAR_SECTION_GAP = SCENE_BTN_W + 20
SCENE_BPM_GAP = SCENE_BAR_SECTION_GAP
SCENE_BPM_LABEL_W = 30
SCENE_BPM_VALUE_W = 34
SCENE_BPM_ARROW_W = 14
SCENE_BPM_MIN = 20.0
SCENE_BPM_MAX = 300.0
_BPM_DISPLAY_LAST = None


def _format_project_bpm(bpm):
    bpm = float(bpm)
    if abs(bpm - round(bpm)) < 0.05:
        return str(int(round(bpm)))
    return '{:.1f}'.format(bpm)


def project_tempo():
    t = _td_timeline()
    if t is None:
        return 120.0
    try:
        return max(SCENE_BPM_MIN, min(SCENE_BPM_MAX, float(t.tempo)))
    except Exception:
        return 120.0


def set_project_tempo(bpm):
    t = _td_timeline()
    if t is None:
        return False
    try:
        bpm = max(SCENE_BPM_MIN, min(SCENE_BPM_MAX, float(bpm)))
        t.tempo = bpm
        _sync_settings_pulse_bpm(bpm)
        _paint_scene_bpm_display()
        return True
    except Exception:
        return False


def adjust_project_tempo(delta, fine=False):
    step = 0.1 if fine else 1.0
    return set_project_tempo(project_tempo() + float(delta) * step)


def _sync_settings_pulse_bpm(bpm):
    try:
        s = _settings()
    except Exception:
        s = None
    if s is None:
        return
    try:
        if hasattr(s.par, 'Pulsecustombpm') and bool(s.par.Pulsecustombpm.eval()):
            return
        s.par.Pulsebpm = float(bpm)
    except Exception:
        pass


def _style_scene_bpm_text(txt, w, h, text='', alignx='center'):
    if txt is None:
        return
    w = max(8, int(w))
    h = max(8, int(h))
    try:
        txt.par.text = str(text)
        txt.par.resolutionw = w
        txt.par.resolutionh = h
        txt.par.font = TD_FONT
        txt.par.fontautosize = 'off'
        txt.par.fontsizex = GRID_FONT_SIZE
        txt.par.fontsizey = GRID_FONT_SIZE
        txt.par.keepfontratio = True
        txt.par.bgalpha = 0.0
        txt.par.alignx = alignx
        txt.par.aligny = 'center'
        txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = SCENE_IDLE_TEXT
        txt.cook(force=True)
    except Exception:
        pass


def _create_scene_bpm_arrow(parent, name, glyph):
    btn = parent.op(name)
    if btn is None:
        btn = parent.create('containerCOMP', name)
    try:
        btn.par.w = SCENE_BPM_ARROW_W
        btn.par.h = SCENE_BTN_H // 2
        btn.par.hmode = 'fixed'
        btn.par.vmode = 'fixed'
        btn.par.drop = 'dropno'
        btn.par.drag = 'dragno'
        btn.par.display = True
        btn.par.enable = True
        btn.par.clickthrough = False
    except Exception:
        pass
    txt = btn.op('label_text')
    if txt is None:
        txt = btn.create('textTOP', 'label_text')
    arrow_h = max(8, SCENE_BTN_H // 2)
    _style_scene_bpm_text(txt, SCENE_BPM_ARROW_W, arrow_h, glyph)
    try:
        txt.par.clickthrough = True
        txt.par.fontsizex = max(6, GRID_FONT_SIZE - 2)
        txt.par.fontsizey = max(6, GRID_FONT_SIZE - 2)
    except Exception:
        pass
    _apply_scene_tile_top(btn, txt)
    _apply_scene_control_bg(btn, is_active=False)
    return btn


def _ensure_scene_bpm(bar):
    if bar is None:
        return None
    comp = bar.op('scene_bpm')
    if comp is None:
        comp = bar.create('containerCOMP', 'scene_bpm')
    try:
        comp.par.w = SCENE_BPM_W
        comp.par.h = SCENE_BTN_H
        comp.par.hmode = 'fixed'
        comp.par.vmode = 'fixed'
        comp.par.align = 'none'
        comp.par.drop = 'dropno'
        comp.par.drag = 'dragno'
        comp.par.display = True
        comp.par.enable = True
        comp.par.clickthrough = True
    except Exception:
        pass
    label = comp.op('bpm_label')
    if label is None:
        label = comp.create('containerCOMP', 'bpm_label')
    try:
        label.par.w = SCENE_BPM_LABEL_W
        label.par.h = SCENE_BTN_H
        label.par.x = 0
        label.par.y = 0
        label.par.clickthrough = True
        label.par.display = True
    except Exception:
        pass
    label_txt = label.op('label_text')
    if label_txt is None:
        label_txt = label.create('textTOP', 'label_text')
    _style_scene_bpm_text(label_txt, SCENE_BPM_LABEL_W, SCENE_BTN_H, 'BPM', alignx='left')
    try:
        label_txt.par.clickthrough = True
    except Exception:
        pass
    _apply_scene_tile_top(label, label_txt)

    value = comp.op('bpm_value')
    if value is None:
        value = comp.create('containerCOMP', 'bpm_value')
    try:
        value.par.w = SCENE_BPM_VALUE_W
        value.par.h = SCENE_BTN_H
        value.par.x = SCENE_BPM_LABEL_W
        value.par.y = 0
        value.par.drop = 'dropno'
        value.par.drag = 'dragno'
        value.par.display = True
        value.par.enable = True
        value.par.clickthrough = False
        value.par.mousewheel = True
    except Exception:
        pass
    value_txt = value.op('label_text')
    if value_txt is None:
        value_txt = value.create('textTOP', 'label_text')
    try:
        value_txt.par.clickthrough = True
    except Exception:
        pass
    _apply_scene_tile_top(value, value_txt)
    _apply_scene_control_bg(value, is_active=False)

    up = _create_scene_bpm_arrow(comp, 'bpm_up', '\u25b2')
    down = _create_scene_bpm_arrow(comp, 'bpm_down', '\u25bc')
    arrow_x = SCENE_BPM_LABEL_W + SCENE_BPM_VALUE_W + 2
    arrow_h = max(8, SCENE_BTN_H // 2)
    try:
        up.par.x = arrow_x
        up.par.y = SCENE_BTN_H - arrow_h
        down.par.x = arrow_x
        down.par.y = 0
    except Exception:
        pass
    _paint_scene_bpm_display()
    return comp


def _paint_scene_bpm_display():
    global _BPM_DISPLAY_LAST
    r = _root()
    ui = r.op('ui') if r else None
    bar = ui.op('scene_bar') if ui else None
    comp = bar.op('scene_bpm') if bar is not None else None
    if comp is None:
        return
    value = comp.op('bpm_value')
    if value is None:
        return
    txt = value.op('label_text')
    if txt is None:
        return
    bpm = project_tempo()
    text = _format_project_bpm(bpm)
    if text == _BPM_DISPLAY_LAST:
        return
    _BPM_DISPLAY_LAST = text
    _style_scene_bpm_text(txt, SCENE_BPM_VALUE_W, SCENE_BTN_H, text)


def _layout_scene_bpm(bar, x):
    comp = _ensure_scene_bpm(bar)
    if comp is None:
        return x
    # Match section spacing used before the Scene label (transport loop leaves 4px).
    x += max(0, SCENE_BAR_SECTION_GAP - 4)
    try:
        comp.par.display = True
        comp.par.x = int(x)
        comp.par.y = SCENE_BAR_CONTENT_Y
        comp.par.w = SCENE_BPM_W
        comp.par.h = SCENE_BTN_H
    except Exception:
        pass
    _paint_scene_bpm_display()
    return x + SCENE_BPM_W + SCENE_BPM_GAP


def _update_scene_bpm_display():
    _paint_scene_bpm_display()
