AUDIO_PANEL_H = 148
AUDIO_SPECT_H = 124
AUDIO_SPECT_PAD = 6
# Audio Analysis panel above settings (spectrum + side meters).
AUDIO_BAND_STRIP_H = 84  # 50% of previous 168
AUDIO_BAND_STRIP_PAD = 4
AUDIO_ANALYSIS_SIDE_W = 96
AUDIO_PEAK_THRESH_W = 52
# Gap between trigger meter bars and the 0-1 / 1-0 reverse button under them.
AUDIO_METER_REV_GAP = 8
AUDIO_MONITOR_W = 720
AUDIO_MONITOR_H = 220
AUDIO_MONITOR_VIEW_PAD = 10
AUDIO_MONITOR_NAME = 'audio_monitor'
AUDIO_MONITOR_WINDOW = 'audio_monitor_window'
# Legacy flag — Spectrum toggle removed; strip is always shown.
_AUDIO_MONITOR_OPEN = True
DEFAULT_AUDIO_MONITOR = True
_AUDIO_PAGE_PRESERVE_IDX = None
_AUDIO_PAGE_PRESERVE_UNTIL = 0.0
_AUDIO_ACTIVATE_TOKEN = 0
# Low: left ~0–46%, threshold near upper third. High: right ~52–96%, threshold near lower third.
DEFAULT_BASS_POS = 0.23
DEFAULT_BASS_WIDTH = 0.46
DEFAULT_HIGH_POS = 0.745
DEFAULT_HIGH_WIDTH = 0.44
DEFAULT_AUDIO_GAIN = 30.0
DEFAULT_THRESH_LOW = 0.71
DEFAULT_THRESH_HIGH = 0.28
DEFAULT_THRESH_PEAK = 0.32
DEFAULT_AUDIO_SMOOTH = 0.0
DEFAULT_AUDIO_ACTIVE = False
AUDIO_GAIN_MAX = 64.0
AUDIO_MIN_BAND_WIDTH = 0.02
AUDIO_READOUT_W = 72
AUDIO_BAND_TAG_H = 18
AUDIO_BAND_HANDLE_W = 1
AUDIO_BAND_RANGE_H = 0
AUDIO_THRESH_SLIDER_W = 16
AUDIO_THRESH_THUMB_H = 3
AUDIO_BAND_HANDLE_U = 0.015
AUDIO_THRESH_ZONE_U = 0.05
AUDIO_FREQ_MIN_HZ = 20.0
AUDIO_HIST_BINS = 128
AUDIO_HIST_RENDER_W = 240
AUDIO_HIST_RENDER_W_MAX = 800
AUDIO_HIST_RENDER_H = 52
AUDIO_HIST_RENDER_H_MAX = 400
# Overlay panel rebuild cadence when open (textTOP / panel geometry — major CPU cost).
AUDIO_HIST_COOK_INTERVAL = 15
# Spectrum *visual* refresh stride (frames). 3 ≈ 20fps @60. Analysis CHOPs stay full-rate.
AUDIO_HIST_VIS_FRAME_STRIDE = 3
AUDIO_HIST_BAR = TD_BG_MAIN
AUDIO_HIST_BAR_MIN = 0.04
# Histogram motion lag (seconds) — higher = slower / smoother bars.
AUDIO_HIST_SMOOTH_ATTACK = 0.08
AUDIO_HIST_SMOOTH_RELEASE = 0.22
_AUDIO_HIST_SIZE = None
_AUDIO_HIST_TICK = 0
_AUDIO_HIST_PIPELINE = 38
_AUDIO_HIST_OVERLAY_DIRTY = True
_AUDIO_HIST_VIEW_BIND = None
_AUDIO_HIST_VIS_COOKING = None
AUDIO_HIST_BAR_SCALE_Y = 113.0
AUDIO_HIST_BAR_COUNT = 48
# GPU temporal mix: weight of the current frame (rest = previous). Cheap vs CHOP lag.
AUDIO_HIST_SMOOTH_CURR = 0.68
# Side meters: smooth levels so integer bar heights don't flicker.
AUDIO_METER_SMOOTH_ATTACK = 0.10
AUDIO_METER_SMOOTH_RELEASE = 0.28
AUDIO_METER_TRIG_ATTACK = 0.02
AUDIO_METER_TRIG_RELEASE = 0.12
AUDIO_METER_LAG_CHOP = 'meter_lag'
AUDIO_METER_DISP_CHOP = 'meter_display'


def _spectrum_temporal_shader():
    """Mix current bars with the previous frame to kill flicker without CHOP lag."""
    curr = max(0.35, min(0.95, float(AUDIO_HIST_SMOOTH_CURR)))
    return (
        '// Temporal smooth for spectrum bars (prev/curr mix)\n'
        'layout(location = 0) out vec4 fragColor;\n'
        'void main()\n'
        '{\n'
        '\tvec4 curr = texture(sTD2DInputs[0], vUV.st);\n'
        '\tvec4 prev = texture(sTD2DInputs[1], vUV.st);\n'
        '\tfragColor = TDOutputSwizzle(mix(prev, curr, %.4f));\n'
        '}\n'
    ) % curr


def _spectrum_pixel_shader():
    """Discrete grey spectrum bars with even integer pixel spacing."""
    bars = max(8, int(AUDIO_HIST_BAR_COUNT))
    r, g, b = AUDIO_HIST_BAR
    return (
        '// B&W discrete spectrum bars (even pixel spacing)\n'
        'layout(location = 0) out vec4 fragColor;\n'
        'void main()\n'
        '{\n'
        '\tconst int BARS = %d;\n'
        '\tint w = int(uTDOutputInfo.res.z);\n'
        '\tint x = int(floor(vUV.x * float(w)));\n'
        '\tx = clamp(x, 0, max(w - 1, 0));\n'
        '\t// Integer partition so every bar gets floor/ceil width evenly.\n'
        '\tint bar = (x * BARS) / max(w, 1);\n'
        '\tint x0 = (bar * w) / BARS;\n'
        '\tint x1 = ((bar + 1) * w) / BARS;\n'
        '\tint local = x - x0;\n'
        '\tint barW = max(x1 - x0, 1);\n'
        '\t// 1px black gap on the right edge of each bar.\n'
        '\tif (local >= barW - 1) {\n'
        '\t\tfragColor = TDOutputSwizzle(vec4(0.0, 0.0, 0.0, 1.0));\n'
        '\t\treturn;\n'
        '\t}\n'
        '\tfloat u = (float(bar) + 0.5) / float(BARS);\n'
        '\tfloat amp = texture(sTD2DInputs[0], vec2(u, 0.5)).r;\n'
        '\tamp = clamp(amp, 0.0, 1.0);\n'
        '\tfloat a = step(vUV.y, amp);\n'
        '\tvec3 rgb = vec3(%.4f, %.4f, %.4f) * a;\n'
        '\tfragColor = TDOutputSwizzle(vec4(rgb, 1.0));\n'
        '}\n'
    ) % (int(bars), float(r), float(g), float(b))


# Band overlays — shared app dark UI palette (ui_theme).
# Low/High use the same bar + grip tone (High’s lighter fill).
AUDIO_BAND_LOW = TD_SLIDER_FILL
AUDIO_BAND_LOW_BODY = TD_BG_HEADER
AUDIO_BAND_HIGH = TD_SLIDER_FILL
AUDIO_BAND_HIGH_BODY = TD_BG_HEADER
AUDIO_THRESH_PEAK_COLOR = TD_SLIDER_THUMB
AUDIO_BAND_BODY_ALPHA = 0.45
AUDIO_BAND_HANDLE_ALPHA = 0.85
AUDIO_BAND_TAG_ALPHA = 0.92
AUDIO_BAND_TAG_TEXT = TD_TEXT_ACTIVE
# Peak threshold cue: thin horizontal tick into the spectrum.
AUDIO_PEAK_TICK_H = 1
AUDIO_PEAK_TICK_EXTEND = 10
AUDIO_PEAK_TICK_INSET = 2
_AUDIO_HIST_DRAG = {
    'mode': None,
    'last_uv': None,
    'last_px': None,
    'band_offset': 0.0,
    'start_uv': None,
    'axis': None,
    'writing_thresh': False,
    'last_thresh_px': None,
    'live_thresh': None,
    'live_thresh_band': None,
    'live_band': None,
    'live_pos': None,
    'live_width': None,
}
AUDIO_ENGINE_NAME = 'audio_engine'

# Settings -> Audio tab: device controls + live triggers for mapping.
_AUDIO_TAB_VISIBLE = (
    ('Audiodeviceindex', 'Input Device'),
    ('Audiorefresh', 'Refresh Audio Input'),
    ('Audioactive', 'Audio Active'),
    ('Audiogain', 'Gain'),
    ('Audiooutkick', 'Low Trigger'),
    ('Audioreverselow', 'Reverse Low Trigger'),
    ('Audiothresholdlow', 'Low Threshold'),
    ('Audioouthit', 'High Trigger'),
    ('Audioreversehigh', 'Reverse High Trigger'),
    ('Audiothresholdhigh', 'High Threshold'),
    ('Audiooutpeakhit', 'Peak Trigger'),
    ('Audioreversepeak', 'Reverse Peak Trigger'),
    ('Audiothresholdpeak', 'Peak Threshold'),
    ('Audiooutlow', 'Low'),
    ('Audioouthigh', 'High'),
    ('Audiooutpeak', 'Peak'),
)
# No extra internal Audio pars — everything needed is in the visible layout.
_AUDIO_TAB_INTERNAL = (
)

_AUDIO_TRIGGER_REVERSE_PARS = (
    ('low', 'Audioreverselow'),
    ('high', 'Audioreversehigh'),
    ('peak', 'Audioreversepeak'),
)

_AUDIO_BAND_STORE = {
    'bass': ('audio_bass_pos', 'audio_bass_width', DEFAULT_BASS_POS, DEFAULT_BASS_WIDTH),
    'high': ('audio_high_pos', 'audio_high_width', DEFAULT_HIGH_POS, DEFAULT_HIGH_WIDTH),
}

_REMOVED_AUDIO_PARS = (
    'Audiobasspos',
    'Audiobasswidth',
    'Audiohighpos',
    'Audiohighwidth',
    'Audiosmoothvalues',
    'Audiobassrange',
    'Audiohighrange',
    'Audiooutlowtrig',
    'Audioouthightrig',
    'Audiohistfreeze',
    'Audiomonitor',
)
AUDIO_OUT_CHOP = 'out_values'
AUDIO_LAG_CHOP = 'out_lag'
AUDIO_DISPLAY_CHOP = 'out_display'
AUDIO_SETTINGS = '/settings'


def _sync_spectrum_threshold_shader(force=False):
    """Update compact threshold/range textures without recompiling GLSL."""
    eng = _audio_engine()
    s = _settings()
    if eng is None or s is None:
        return False
    values = []
    for par_name, default in (
        ('Audiothresholdlow', DEFAULT_THRESH_LOW),
        ('Audiothresholdhigh', DEFAULT_THRESH_HIGH),
        ('Audiothresholdpeak', DEFAULT_THRESH_PEAK),
    ):
        try:
            value = _norm(float(getattr(s.par, par_name).eval()))
        except Exception:
            value = default
        values.append(value)
    top = eng.op('spect_thresholds')
    if top is None:
        top = _ensure_constant_top(eng, 'spect_thresholds', tuple(values), alpha=1.0)
        _set_top_res(top, 1, 1)
        force = True
    changed = False
    try:
        current = (
            float(top.par.colorr.eval()),
            float(top.par.colorg.eval()),
            float(top.par.colorb.eval()),
        )
        if force or any(abs(a - b) > 1e-6 for a, b in zip(current, values)):
            top.par.colorr, top.par.colorg, top.par.colorb = values
            changed = True
    except Exception:
        pass
    bass_lo, bass_hi = _audio_band_norms('bass')
    high_lo, high_hi = _audio_band_norms('high')
    ranges = (bass_lo, bass_hi, high_lo, high_hi)
    range_top = eng.op('spect_band_ranges')
    if range_top is None:
        range_top = _ensure_constant_top(
            eng, 'spect_band_ranges', ranges[:3], alpha=ranges[3],
        )
        _set_top_res(range_top, 1, 1)
        force = True
    try:
        current_ranges = (
            float(range_top.par.colorr.eval()),
            float(range_top.par.colorg.eval()),
            float(range_top.par.colorb.eval()),
            float(range_top.par.alpha.eval()),
        )
        if force or any(abs(a - b) > 1e-6 for a, b in zip(current_ranges, ranges)):
            range_top.par.colorr = ranges[0]
            range_top.par.colorg = ranges[1]
            range_top.par.colorb = ranges[2]
            range_top.par.alpha = ranges[3]
            changed = True
    except Exception:
        pass
    return changed


def _audio_settings_path():
    for path in (AUDIO_SETTINGS,):
        try:
            if op(path) is not None:
                return path
        except Exception:
            pass
    return AUDIO_SETTINGS


def _audio_panel_visible():
    return False


def _audio_monitor_window_op():
    try:
        return op('/' + AUDIO_MONITOR_WINDOW)
    except Exception:
        return None


_AUDIO_ACTIVE_TAB_HOLD_UNTIL = 0.0
_AUDIO_SPECTRUM_SYNC_LOCK = False
_AUDIO_TAB_FORCE_LOCK = False


def _audio_active_tab_hold_active():
    """True briefly after Audio Active toggles — blocks Canvas tab steal from resize."""
    global _AUDIO_ACTIVE_TAB_HOLD_UNTIL
    try:
        import time
        return float(time.time()) < float(_AUDIO_ACTIVE_TAB_HOLD_UNTIL)
    except Exception:
        return False


def _snap_perform_settings_to_audio():
    """Set Perform pageindex to Audio only — no spectrum sync (avoids recursion)."""
    global _AUDIO_TAB_FORCE_LOCK
    if _AUDIO_TAB_FORCE_LOCK:
        return False
    audio_idx = _audio_settings_tab_index()
    if audio_idx is None:
        return False
    r = _root()
    ui = r.op('ui') if r is not None else None
    panel = ui.op('settings_params') if ui is not None else None
    if panel is None:
        return False
    _AUDIO_TAB_FORCE_LOCK = True
    try:
        try:
            if hasattr(panel.par, 'syncpage'):
                panel.par.syncpage = False
        except Exception:
            pass
        try:
            if int(float(panel.par.pageindex.eval())) != int(audio_idx):
                panel.par.pageindex = int(audio_idx)
        except Exception:
            pass
    finally:
        _AUDIO_TAB_FORCE_LOCK = False
    return True


def _begin_audio_active_tab_hold(seconds=0.45):
    """Deprecated no-op — do not force the Audio tab (was fighting user navigation)."""
    global _AUDIO_ACTIVE_TAB_HOLD_UNTIL
    _AUDIO_ACTIVE_TAB_HOLD_UNTIL = 0.0


def on_audio_active_changed():
    global _AUDIO_ACTIVATE_TOKEN
    _AUDIO_ACTIVATE_TOKEN += 1
    activate_token = int(_AUDIO_ACTIVATE_TOKEN)
    """Audio Active: live vs grey only — never rebuild/reflow the settings panel."""
    try:
        _sync_audio_active()
    except Exception:
        pass
    # Enabling a saved parameter does not always reopen the native capture
    # endpoint. Match the device restart performed by Refresh Audio Input.
    if _audio_active():
        try:
            _ensure_audio_engine()
            _refresh_audio_device_menu(force=True)
            _apply_audio_device()
            _restart_audio_device_input()
            eng = _audio_engine()
            if eng is not None:
                _heal_audio_output_chain(eng)
                eng.cook(force=True)
                _heal_audio_spectrum_if_needed(eng)
            _sync_audio_output_pars()
        except Exception as exc:
            print('Audio activate restart:', exc)
        # On project reopen the Windows capture endpoint may not be ready
        # during this callback. Retry once after the project has settled.
        def _delayed_audio_activate():
            if activate_token != int(_AUDIO_ACTIVATE_TOKEN) or not _audio_active():
                return
            try:
                refresh_audio_input()
                _enforce_audio_spectrum_runtime(refresh_visuals=True)
            except Exception as exc:
                print('Delayed audio activate restart:', exc)
        try:
            if not _defer_run(_delayed_audio_activate, delayFrames=30, fromOP=_root()):
                _delayed_audio_activate()
        except Exception:
            pass
    # force=False: if the Audio slot is already open, only restyle (no height/page churn).
    _sync_audio_spectrum_for_settings_tab(force=False)
    # Active-off clears audio_band_view.top. The cached display binding still
    # matches when Active comes back on, so a normal sync will not restore it.
    if _audio_active():
        try:
            _enforce_audio_spectrum_runtime(refresh_visuals=True)
        except Exception:
            pass


def on_audio_monitor_changed():
    """Legacy no-op — Spectrum toggle removed; strip always stays open."""
    _sync_audio_spectrum_for_settings_tab(force=False)


def _audio_monitor_is_open():
    """Always True — Spectrum toggle removed."""
    return True


def _audio_histogram_visible():
    """Spectrum chrome is interactive (bands/thresholds)."""
    return _audio_spectrum_interactive()


def _audio_spectrum_slot_visible():
    """Spectrum strip is always reserved above settings."""
    return True


def _audio_spectrum_interactive():
    """Bands/thresholds work when Audio Active is on."""
    try:
        return bool(_audio_active())
    except Exception:
        return False


def _audio_spectrum_is_live():
    """Spectrum animation cooking follows Audio Active."""
    return _audio_spectrum_interactive()


def _sync_audio_monitor_toggle(s=None):
    """Destroy leftover Spectrum toggle if present."""
    global _AUDIO_MONITOR_OPEN
    _AUDIO_MONITOR_OPEN = True
    _destroy_audio_monitor_toggle(s)


def _destroy_audio_monitor_toggle(s=None):
    if s is None:
        s = _settings()
    if s is None:
        return False
    try:
        getattr(s.par, 'Audiomonitor').destroy()
        return True
    except Exception:
        return False


def _ensure_audio_monitor_toggle(s=None, page=None):
    """Spectrum toggle removed — destroy any leftover Audiomonitor par."""
    del page
    _destroy_audio_monitor_toggle(s)
    return None


# Back-compat alias used by older call sites.
def _sync_audio_monitor_pulse_label(s=None):
    _sync_audio_monitor_toggle(s)


def _perform_settings_pageindex():
    try:
        r = _root()
        ui = r.op('ui') if r is not None else None
        panel = ui.op('settings_params') if ui is not None else None
        if panel is None:
            return None
        return int(float(panel.par.pageindex.eval()))
    except Exception:
        return None


def _set_perform_settings_pageindex(idx):
    if idx is None:
        return False
    try:
        r = _root()
        ui = r.op('ui') if r is not None else None
        panel = ui.op('settings_params') if ui is not None else None
        if panel is None:
            return False
        if int(float(panel.par.pageindex.eval())) != int(idx):
            panel.par.pageindex = int(idx)
        return True
    except Exception:
        return False


_AUDIO_PAGE_PRESERVE_IDX = None
_AUDIO_PAGE_PRESERVE_UNTIL = 0.0


def _preserve_settings_page_briefly(seconds=0.35):
    """Remember the current Perform tab and restore it if TD steals it mid-click."""
    global _AUDIO_PAGE_PRESERVE_IDX, _AUDIO_PAGE_PRESERVE_UNTIL
    idx = _perform_settings_pageindex()
    if idx is None:
        return
    _AUDIO_PAGE_PRESERVE_IDX = int(idx)
    try:
        import time
        _AUDIO_PAGE_PRESERVE_UNTIL = float(time.time()) + float(seconds)
    except Exception:
        _AUDIO_PAGE_PRESERVE_UNTIL = 0.0
    root = _root()

    def _restore():
        try:
            import time
            if float(time.time()) > float(_AUDIO_PAGE_PRESERVE_UNTIL):
                return
        except Exception:
            pass
        want = _AUDIO_PAGE_PRESERVE_IDX
        if want is None:
            return
        cur = _perform_settings_pageindex()
        if cur is not None and int(cur) != int(want):
            _set_perform_settings_pageindex(want)
        # Keep restoring briefly while the click settles.
        try:
            import time
            if float(time.time()) < float(_AUDIO_PAGE_PRESERVE_UNTIL):
                _defer_run(_restore, delayMilliSeconds=50, fromOP=root)
        except Exception:
            pass

    if not _defer_run(_restore, delayMilliSeconds=1, fromOP=root):
        try:
            run(_restore, delayMilliSeconds=1, fromOP=root)
        except Exception:
            pass


def _audio_settings_tab_index():
    settings = _settings()
    if settings is None:
        return None
    try:
        pages = [pg.name for pg in settings.customPages]
        if 'Audio' in pages:
            return pages.index('Audio')
    except Exception:
        pass
    return None


def _audio_settings_tab_active():
    """True while the Perform settings panel is on the Audio tab.

    Only the Perform `settings_params` pageindex counts — /settings in the
    network editor often stays on another page when syncpage is off.
    """
    audio_idx = _audio_settings_tab_index()
    if audio_idx is None:
        return False
    r = _root()
    ui = r.op('ui') if r is not None else None
    panel = ui.op('settings_params') if ui is not None else None
    if panel is None:
        return False
    try:
        return int(float(panel.par.pageindex.eval())) == int(audio_idx)
    except Exception:
        return False


def _force_settings_tab(page_name='Audio'):
    """Synchronously select a settings tab on both /settings and Perform panel."""
    global _AUDIO_TAB_FORCE_LOCK
    if _AUDIO_TAB_FORCE_LOCK:
        return False
    page_name = _canonical_settings_tab_name(page_name or 'Audio')
    idx = None
    try:
        idx = _settings_tab_index(page_name)
    except Exception:
        idx = None
    if idx is None:
        try:
            settings = _settings()
            pages = [pg.name for pg in settings.customPages] if settings is not None else []
            if page_name in pages:
                idx = pages.index(page_name)
        except Exception:
            idx = None
    if idx is None:
        return False
    settings = _settings()
    r = _root()
    ui = r.op('ui') if r is not None else None
    panel = ui.op('settings_params') if ui is not None else None
    _AUDIO_TAB_FORCE_LOCK = True
    try:
        try:
            if panel is not None and hasattr(panel.par, 'syncpage'):
                panel.par.syncpage = False
        except Exception:
            pass
        try:
            if settings is not None:
                settings.par.pageindex = idx
        except Exception:
            pass
        try:
            if panel is not None:
                panel.par.pageindex = idx
        except Exception:
            pass
    finally:
        _AUDIO_TAB_FORCE_LOCK = False
    # Do not call spectrum sync here — pageindex callbacks re-enter and crash TD.
    return True


def _keep_settings_on_audio_tab():
    """Pin Perform settings on Audio after spectrum layout churn."""
    _snap_perform_settings_to_audio()
    try:
        _pin_settings_tab('Audio', defer_frames=(0, 1, 2, 3, 5))
    except Exception:
        pass


def _perform_bottom_zone_h():
    """Height of the bottom preview/settings row (independent of spectrum open)."""
    try:
        content_h = _layout_grid_geometry()
        return int(_layout_bottom_h(content_h))
    except Exception:
        pass
    r = _root()
    ui = r.op('ui') if r is not None else None
    settings_panel = ui.op('settings_params') if ui is not None else None
    h = 120
    try:
        if settings_panel is not None:
            h = max(h, int(settings_panel.par.h.eval()))
    except Exception:
        pass
    return h


def _settings_full_bottom_h():
    return max(120, int(_perform_bottom_zone_h()))


def _ensure_audio_inactive_overlay(strip, show_note=True):
    """Full-bleed dark veil; optional centered note when audio input is off."""
    if strip is None:
        return None
    ov = strip.op('inactive_overlay')
    if ov is None:
        ov = strip.create('containerCOMP', 'inactive_overlay')
    ow = max(1, int(float(strip.par.w.eval())))
    oh = max(1, int(float(strip.par.h.eval())) or AUDIO_BAND_STRIP_H)
    try:
        ov.par.x = 0
        ov.par.y = 0
        ov.par.w = ow
        ov.par.h = oh
        ov.par.hmode = 'fixed'
        ov.par.vmode = 'fixed'
        ov.par.align = 'none'
        ov.par.bgcolorr = ov.par.bgcolorg = ov.par.bgcolorb = 0.0
        ov.par.bgalpha = 0.72
        if hasattr(ov.par, 'layer'):
            ov.par.layer = 50
        if hasattr(ov.par, 'clickthrough'):
            ov.par.clickthrough = True
    except Exception:
        pass
    txt = ov.op('note')
    if txt is None:
        txt = ov.create('textTOP', 'note')
    try:
        # Message only when Audio Active is off — Spectrum-off is just a CPU/GPU save.
        if show_note:
            txt.par.text = 'Audio input disabled'
            txt.par.resolutionw = max(64, ow)
            txt.par.resolutionh = max(24, oh)
            txt.par.font = TD_FONT
            txt.par.fontsizex = TD_FONT_SIZE_SMALL
            txt.par.fontsizey = TD_FONT_SIZE_SMALL
            txt.par.alignx = 'center'
            txt.par.aligny = 'center'
            txt.par.wordwrap = False
            txt.par.bgalpha = 0.0
            txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = TD_TEXT_LABEL
            ov.par.top = txt
            ov.par.topfill = 'fitbest'
        else:
            ov.par.top = ''
            txt.par.text = ''
    except Exception:
        pass
    return ov


def _apply_audio_spectrum_live_style(strip, live=None):
    """Interactive when Active; Spectrum only gates animation cooking. Active-off = overlay."""
    if strip is None:
        return
    interactive = _audio_spectrum_interactive()
    cooking = bool(live) if live is not None else _audio_spectrum_is_live()
    cooking = bool(cooking) and interactive
    audio_active = False
    try:
        audio_active = bool(_audio_active())
    except Exception:
        audio_active = False
    # Overlay/message only when Audio Active is off.
    show_overlay = (not audio_active) and _audio_spectrum_slot_visible()
    try:
        strip.par.display = True
        strip.par.enable = True
        strip.par.h = AUDIO_BAND_STRIP_H
        strip.par.bgalpha = 1.0
        if hasattr(strip.par, 'layer'):
            strip.par.layer = 10
        strip.par.bgcolorr, strip.par.bgcolorg, strip.par.bgcolorb = TD_BG_HEADER
    except Exception:
        pass
    view = strip.op('audio_band_view')
    if view is not None:
        try:
            view.par.display = True
            view.par.enable = interactive
            view.par.bgalpha = 1.0
            view.par.bgcolorr = view.par.bgcolorg = view.par.bgcolorb = 0.0
            if not interactive:
                view.par.top = ''
        except Exception:
            pass
    for name in ('analysis_side', 'peak_thresh_bar', 'peak_tick'):
        ch = strip.op(name)
        if ch is None:
            continue
        try:
            ch.par.display = True
            ch.par.enable = interactive
            if hasattr(ch.par, 'bgalpha'):
                ch.par.bgalpha = 1.0
        except Exception:
            pass
    # Band hits stay clickable whenever Active.
    if view is not None:
        for ch in list(view.children):
            try:
                ch.par.enable = interactive
                if interactive:
                    ch.par.display = True
            except Exception:
                pass
    ov = _ensure_audio_inactive_overlay(strip, show_note=show_overlay)
    if ov is not None:
        try:
            ov.par.w = max(1, int(float(strip.par.w.eval())))
            ov.par.h = max(1, int(float(strip.par.h.eval())) or AUDIO_BAND_STRIP_H)
            ov.par.display = show_overlay
            # Critical: disabled+hidden overlays must not sit above the spectrum and eat clicks.
            ov.par.enable = show_overlay
            ov.par.bgalpha = 0.72 if show_overlay else 0.0
            if hasattr(ov.par, 'layer'):
                ov.par.layer = 50 if show_overlay else 0
            if not show_overlay:
                ov.par.top = ''
                ov.par.w = 1
                ov.par.h = 1
        except Exception:
            pass
    if interactive:
        try:
            _set_spectrogram_visual_cooking(cooking and (not _audio_hist_frozen()))
            # Display sync / overlay layout owned by _update_audio_readouts (stride-gated).
        except Exception:
            pass
    else:
        _set_spectrogram_visual_cooking(False)


def _relayout_audio_spectrum_chrome():
    """Spectrum in reserved slot above settings. Height reserved while Audio tab is open."""
    r = _root()
    ui = r.op('ui') if r is not None else None
    if ui is None:
        return False
    settings_panel = ui.op('settings_params')
    if settings_panel is None:
        return False
    bottom_h = _perform_bottom_zone_h()
    reserve = _audio_band_strip_reserve_h()
    want_h = max(120, int(bottom_h) - int(reserve))
    try:
        settings_panel.par.x = _settings_panel_x()
        settings_panel.par.w = _settings_panel_w()
        settings_panel.par.y = 0
        cur_h = int(float(settings_panel.par.h.eval()))
        if cur_h != want_h:
            # Entering/leaving Audio changes height once; Spectrum on/off does not.
            _preserve_settings_page_briefly()
            settings_panel.par.h = want_h
        settings_panel.par.hmode = 'fixed'
        settings_panel.par.vmode = 'fixed'
        settings_panel.par.display = True
    except Exception:
        pass
    try:
        _layout_audio_band_strip(bottom_h)
    except Exception:
        pass
    return True


def _spectrum_strip_is_shown():
    """True when the spectrum slot chrome is visible (live or greyed)."""
    r = _root()
    ui = r.op('ui') if r is not None else None
    strip = ui.op('audio_band_strip') if ui is not None else None
    if strip is None:
        return False
    try:
        return bool(strip.par.display.eval()) and int(float(strip.par.h.eval())) > 0
    except Exception:
        return False


def _expand_audio_spectrum_strip(live=None):
    """Show spectrum in the reserved slot (live or greyed)."""
    if live is None:
        live = _audio_spectrum_is_live()
    try:
        eng = _audio_engine()
        if eng is None:
            eng = _ensure_audio_engine()
        _sync_audio_active()
    except Exception:
        eng = _audio_engine()
    if eng is not None and live:
        try:
            _heal_audio_output_chain(eng)
        except Exception:
            pass
        try:
            if eng.op('spect_bars_glsl') is None or eng.op('spect_hist_hold') is None:
                _heal_audio_spectrum_if_needed(eng)
        except Exception:
            pass
    try:
        strip = _ensure_audio_band_strip()
        _apply_audio_spectrum_live_style(strip, live)
    except Exception as exc:
        print('Audio Spectrum: expand failed:', exc)
        return False
    try:
        _relayout_audio_spectrum_chrome()
    except Exception as exc:
        print('Audio Spectrum: layout failed:', exc)
        return False
    try:
        strip = _root().op('ui/audio_band_strip') if _root() else None
        _apply_audio_spectrum_live_style(strip, live)
    except Exception:
        pass
    return True


def _fold_audio_spectrum_strip():
    """Hide spectrum and release the reserved settings height (leaving Audio tab)."""
    global _AUDIO_HIST_VIEW_BIND, _AUDIO_HIST_VIS_COOKING
    _AUDIO_HIST_VIEW_BIND = None
    _AUDIO_HIST_VIS_COOKING = None
    r = _root()
    ui = r.op('ui') if r is not None else None
    strip = ui.op('audio_band_strip') if ui is not None else None
    if strip is not None:
        for ch in list(strip.children):
            try:
                ch.par.display = False
                ch.par.enable = False
            except Exception:
                pass
            try:
                if hasattr(ch.par, 'top'):
                    ch.par.top = ''
            except Exception:
                pass
        try:
            strip.par.display = False
            strip.par.enable = False
            strip.par.h = 0
            strip.par.bgalpha = 0.0
        except Exception:
            pass
    _set_spectrogram_visual_cooking(False)
    try:
        _relayout_audio_spectrum_chrome()
    except Exception:
        pass
    return True


def _sync_audio_spectrum_for_settings_tab(force=False, defer_geom=None):
    """Keep spectrum strip always reserved above settings (greyed if Audio Active off)."""
    global _AUDIO_SPECTRUM_SYNC_LOCK
    del defer_geom
    if _AUDIO_SPECTRUM_SYNC_LOCK:
        return True
    _AUDIO_SPECTRUM_SYNC_LOCK = True
    try:
        live = _audio_spectrum_is_live()
        shown = _spectrum_strip_is_shown()
        # Slot already open → only restyle live/grey. Never reflow settings_params
        # (reflow under the mouse near tabs steals pageindex).
        if shown:
            strip = None
            try:
                strip = _root().op('ui/audio_band_strip')
            except Exception:
                strip = None
            _apply_audio_spectrum_live_style(strip, live)
            if live and force:
                try:
                    eng = _audio_engine()
                    if eng is not None and (
                        eng.op('spect_bars_glsl') is None or eng.op('spect_hist_hold') is None
                    ):
                        _heal_audio_spectrum_if_needed(eng)
                except Exception:
                    pass
            return True
        return _expand_audio_spectrum_strip(live=live)
    finally:
        _AUDIO_SPECTRUM_SYNC_LOCK = False


def _sync_audio_band_strip_visibility(strip=None):
    """Keep spectrum slot visible; live vs greyed from Audio Active."""
    if strip is None:
        r = _root()
        ui = r.op('ui') if r else None
        strip = ui.op('audio_band_strip') if ui is not None else None
    if strip is None:
        return False
    _apply_audio_spectrum_live_style(strip, _audio_spectrum_is_live())
    return True


def _ensure_settings_pageindex_parexec():
    """Watch Perform settings_params pageindex so spectrum folds when leaving Audio."""
    r = _root()
    if r is None:
        return None
    ui = r.op('ui')
    panel = ui.op('settings_params') if ui is not None else None
    if panel is None:
        return None
    pe = r.op('settings_page_parexec')
    if pe is None:
        pe = r.create('parameterexecuteDAT', 'settings_page_parexec')
    script = (
        "def onValueChange(par):\n"
        "    try:\n"
        "        logic = op('/project1/performance_mode').op('logic').module\n"
        "        # If a spectrum/active click is settling, restore the pre-click tab\n"
        "        # instead of snapping to Audio or folding early.\n"
        "        try:\n"
        "            import time\n"
        "            until = float(getattr(logic, '_AUDIO_PAGE_PRESERVE_UNTIL', 0) or 0)\n"
        "            want = getattr(logic, '_AUDIO_PAGE_PRESERVE_IDX', None)\n"
        "            if want is not None and float(time.time()) < until:\n"
        "                cur = int(float(par.eval()))\n"
        "                if cur != int(want):\n"
        "                    par.owner.par.pageindex = int(want)\n"
        "                return\n"
        "        except Exception:\n"
        "            pass\n"
        "        if hasattr(logic, '_sync_audio_spectrum_for_settings_tab'):\n"
        "            logic._sync_audio_spectrum_for_settings_tab(force=True)\n"
        "    except Exception:\n"
        "        pass\n"
    )
    try:
        pe.par.op = panel.path
        pe.par.pars = 'pageindex'
        pe.par.active = True
        if hasattr(pe.par, 'valuechange'):
            pe.par.valuechange = True
    except Exception:
        pass
    try:
        if (pe.text or '').strip() != script.strip():
            pe.text = script
    except Exception:
        pass
    return pe


def _mark_audio_hist_overlays_dirty():
    global _AUDIO_HIST_OVERLAY_DIRTY
    _AUDIO_HIST_OVERLAY_DIRTY = True


def _audio_hist_frozen(s=None):
    """Freeze Spectrum UI removed — histogram always lives."""
    return False


def toggle_audio_hist_freeze():
    """No-op — Freeze Spectrum control removed."""
    return False


def _apply_audio_hist_freeze_state(strip=None, s=None):
    """Keep histogram cooking live (freeze control removed)."""
    _set_spectrogram_visual_cooking(True)
    try:
        r = _root()
        ui = r.op('ui') if r is not None else None
        strip = strip or (ui.op('audio_band_strip') if ui is not None else None)
        view = strip.op('audio_band_view') if strip is not None else None
        if view is not None:
            _sync_spectrogram_display(view, force=True)
    except Exception:
        pass
    _destroy_audio_hist_freeze_button(strip)
    return True


def _destroy_audio_hist_freeze_button(strip=None):
    """Remove legacy Freeze button under the analysis meters."""
    if strip is None:
        try:
            r = _root()
            ui = r.op('ui') if r is not None else None
            strip = ui.op('audio_band_strip') if ui is not None else None
        except Exception:
            strip = None
    side = strip.op('analysis_side') if strip is not None else None
    if side is None:
        return False
    btn = side.op('hist_freeze')
    if btn is None:
        return False
    try:
        btn.destroy()
    except Exception:
        return False
    return True


def _sync_audio_hist_freeze_button(strip=None):
    """No-op — Freeze Spectrum button removed."""
    _destroy_audio_hist_freeze_button(strip)
    return False


def _audio_panel_reserve_h():
    return 0


def _ensure_spectrogram_freeze_hold(eng, src=None):
    """cacheTOP that passes through live bars, or holds the last frame when frozen."""
    if eng is None:
        return None
    hold = eng.op('spect_hist_hold')
    if hold is None:
        hold = eng.create('cacheTOP', 'spect_hist_hold')
    if src is None:
        src = eng.op('spect_render')
    if src is not None:
        _wire_top_inputs(hold, (src,))
    try:
        # Always-cook off; Active updates while live, Off holds last frame.
        if hasattr(hold.par, 'alwayscook'):
            hold.par.alwayscook = False
    except Exception:
        pass
    return hold


def _set_spectrogram_visual_cooking(enabled, force=False):
    """Bypass display-only histogram CHOPs/TOPs when closed.

    Analysis triggers (audiospect / analyze / out_values) stay active for Audio Active.
    """
    global _AUDIO_HIST_VIS_COOKING
    enabled = bool(enabled)
    if enabled and (not force) and _audio_hist_frozen():
        enabled = False
    if _AUDIO_HIST_VIS_COOKING is enabled:
        return
    eng = _audio_engine()
    if eng is None:
        return
    bypass = not enabled
    for name in (
        'spect_bar_norm', 'spect_bar_sel', 'spect_bar_vis', 'spect_chopto',
        'spect_bars_glsl', 'spect_bar_fb', 'spect_bars_smooth',
        'spect_render', 'spect_comp', 'spect_bg',
    ):
        node = eng.op(name)
        if node is None:
            continue
        try:
            if bool(node.bypass) != bypass:
                node.bypass = bypass
        except Exception:
            pass
    hold = eng.op('spect_hist_hold')
    if hold is not None:
        try:
            hold.bypass = False
        except Exception:
            pass
    _AUDIO_HIST_VIS_COOKING = enabled


def _audio_engine():
    r = _root()
    if r is None:
        return None
    return r.op(AUDIO_ENGINE_NAME)


def _audio_settings_pars_for_set():
    return [
        'Audioactive',
        'Audiodeviceindex',
        'Audiogain',
        'Audiothresholdlow',
        'Audiothresholdhigh',
        'Audiothresholdpeak',
        'Audioreverselow',
        'Audioreversehigh',
        'Audioreversepeak',
    ]


def _audio_trigger_reverse_par(band_key):
    for key, par_name in _AUDIO_TRIGGER_REVERSE_PARS:
        if key == band_key:
            return par_name
    return None


def _audio_trigger_reverse_on(band_key, s=None):
    par_name = _audio_trigger_reverse_par(band_key)
    if not par_name:
        return False
    if s is None:
        s = _settings()
    if s is None:
        return False
    try:
        return bool(int(float(getattr(s.par, par_name).eval())))
    except Exception:
        return False


def toggle_audio_trigger_reverse(band_key):
    """Flip Low/High/Peak trigger polarity (0-1 vs 1-0)."""
    par_name = _audio_trigger_reverse_par(band_key)
    if not par_name:
        return False
    s = _settings()
    if s is None:
        return False
    try:
        p = getattr(s.par, par_name)
        p.val = 0 if bool(int(float(p.eval()))) else 1
    except Exception:
        return False
    # Expressions already reference the reverse toggles — do not rewire outs
    # here (that rebuilds settings_params and resets the tab scroll).
    try:
        _sync_audio_trigger_reverse_ui()
    except Exception:
        pass
    return True


def _audio_band_storage_keys():
    keys = []
    for _band, (pos_key, width_key, _def_pos, _def_width) in _AUDIO_BAND_STORE.items():
        keys.extend((pos_key, width_key))
    return keys


def _export_audio_band_storage(s=None):
    if s is None:
        s = _settings()
    if s is None:
        return {}
    out = {}
    for key in _audio_band_storage_keys():
        try:
            out[key] = float(s.fetch(key))
        except Exception:
            pass
    return out


def _apply_audio_band_storage(s, data):
    if s is None or not isinstance(data, dict):
        return False
    applied = False
    for key, val in data.items():
        if key not in _audio_band_storage_keys():
            continue
        try:
            s.store(key, float(val))
            applied = True
        except Exception:
            pass
    return applied


def _audio_band_pos_width_values(band):
    # Prefer in-drag live geometry so analysis storage is not spammed mid-drag.
    if (
        _AUDIO_HIST_DRAG.get('live_band') == band
        and _AUDIO_HIST_DRAG.get('live_pos') is not None
        and _AUDIO_HIST_DRAG.get('live_width') is not None
    ):
        return (
            _norm(_AUDIO_HIST_DRAG['live_pos']),
            max(AUDIO_MIN_BAND_WIDTH, float(_AUDIO_HIST_DRAG['live_width'])),
        )
    pos_key, width_key, def_pos, def_width = _AUDIO_BAND_STORE[band]
    s = _settings()
    if s is None:
        return def_pos, def_width
    try:
        pos = float(s.fetch(pos_key, def_pos))
        width = float(s.fetch(width_key, def_width))
    except Exception:
        pos, width = def_pos, def_width
    return _norm(pos), max(AUDIO_MIN_BAND_WIDTH, float(width))


def _audio_band_fetch_expr(band, component='pos'):
    s_path = _audio_settings_path().replace("'", "\\'")
    pos_key, width_key, def_pos, def_width = _AUDIO_BAND_STORE[band]
    if component == 'pos':
        return "float(op('{s}').fetch('{k}', {d}))".format(s=s_path, k=pos_key, d=def_pos)
    return "float(op('{s}').fetch('{k}', {d}))".format(s=s_path, k=width_key, d=def_width)


def _init_audio_band_storage(s=None, force=False):
    if s is None:
        s = _settings()
    if s is None:
        return
    for _band, (pos_key, width_key, def_pos, def_width) in _AUDIO_BAND_STORE.items():
        if force or s.fetch(pos_key, None) is None:
            s.store(pos_key, def_pos)
        if force or s.fetch(width_key, None) is None:
            s.store(width_key, def_width)


def _migrate_audio_band_storage_from_pars(s=None):
    if s is None:
        s = _settings()
    if s is None:
        return
    _init_audio_band_storage(s)
    migrations = (
        ('Audiobasspos', 'audio_bass_pos'),
        ('Audiobasswidth', 'audio_bass_width'),
        ('Audiohighpos', 'audio_high_pos'),
        ('Audiohighwidth', 'audio_high_width'),
    )
    for par_name, store_key in migrations:
        try:
            s.store(store_key, float(getattr(s.par, par_name).eval()))
        except Exception:
            pass


def _destroy_removed_audio_pars(s=None):
    if s is None:
        s = _settings()
    if s is None:
        return
    for name in _REMOVED_AUDIO_PARS:
        try:
            getattr(s.par, name).destroy()
        except Exception:
            pass


def _audio_active():
    s = _settings()
    if s is None:
        return False
    try:
        return bool(s.par.Audioactive.eval())
    except Exception:
        return DEFAULT_AUDIO_ACTIVE


def _sync_audio_active():
    eng = _audio_engine()
    if eng is None:
        return
    active = _audio_active()
    try:
        eng.allowCooking = active
    except Exception:
        pass
    dev = eng.op('audiodevin1')
    if dev is not None:
        try:
            dev.par.active = active
        except Exception:
            pass
    if active:
        try:
            _apply_audio_device()
        except Exception:
            pass


def _norm(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(v)))


def _audio_gain_setting():
    s = _settings()
    if s is None:
        return max(0.001, float(DEFAULT_AUDIO_GAIN))
    try:
        return max(0.001, float(s.par.Audiogain.eval()))
    except Exception:
        return max(0.001, float(DEFAULT_AUDIO_GAIN))


def _normalize_audio_readout(raw):
    """Map analyze RMS to 0-1, compensating for Gain setting."""
    return _norm(float(raw) / _audio_gain_setting())


def _audio_smooth_amount():
    return 0.0


def _audio_lag_attack_expr():
    return '0'


def _audio_lag_release_expr():
    return '0'


def _configure_audio_lag_chop(lag):
    if lag is None:
        return
    try:
        lag.par.lag1.expr = _audio_lag_attack_expr()
        lag.par.lag1.mode = ParMode.EXPRESS
        lag.par.lag2.expr = _audio_lag_release_expr()
        lag.par.lag2.mode = ParMode.EXPRESS
    except Exception:
        pass
    for unit_name in ('lagunit', 'unit'):
        try:
            p = getattr(lag.par, unit_name)
            names = [str(x).lower() for x in (p.menuNames or [])]
            if any('sec' in n for n in names):
                for i, n in enumerate(names):
                    if 'sec' in n:
                        p.val = p.menuNames[i]
                        break
        except Exception:
            pass


def _audio_output_chain_is_broken(eng):
    if eng is None:
        return True
    lag = eng.op(AUDIO_LAG_CHOP)
    disp = eng.op(AUDIO_DISPLAY_CHOP)
    outv = eng.op(AUDIO_OUT_CHOP)
    if outv is None or lag is None or disp is None:
        return True
    try:
        if str(disp.opType) != 'nullCHOP':
            return True
        if disp.errors():
            return True
        if _chop_input_owner(disp) != lag:
            return True
        if _chop_input_owner(lag) != outv:
            return True
    except Exception:
        return True
    return False


def _remove_legacy_audio_skip_chop(eng=None):
    if eng is None:
        eng = _audio_engine()
    if eng is None:
        return
    for name in ('out_skip',):
        node = eng.op(name)
        if node is not None:
            try:
                node.destroy()
            except Exception:
                pass


def _ensure_audio_output_chain(eng=None):
    """Raw out_values -> lag (smooth) -> out_display."""
    if eng is None:
        eng = _audio_engine()
    if eng is None:
        return None
    outv = eng.op(AUDIO_OUT_CHOP)
    if outv is None:
        return None

    lag = eng.op(AUDIO_LAG_CHOP)
    if lag is None:
        lag = eng.create('lagCHOP', AUDIO_LAG_CHOP)
    _configure_audio_lag_chop(lag)
    _wire_chop(outv, lag)

    disp = eng.op(AUDIO_DISPLAY_CHOP)
    if disp is not None and str(disp.opType) != 'nullCHOP':
        try:
            disp.destroy()
        except Exception:
            pass
        disp = None
    if disp is None:
        disp = eng.create('nullCHOP', AUDIO_DISPLAY_CHOP)
    _wire_chop(lag, disp)
    _remove_legacy_audio_skip_chop(eng)
    return disp


def _heal_audio_output_chain(eng=None):
    if eng is None:
        eng = _audio_engine()
    if eng is None:
        return None
    if not _audio_output_chain_is_broken(eng):
        lag = eng.op(AUDIO_LAG_CHOP)
        _configure_audio_lag_chop(lag)
        return eng.op(AUDIO_DISPLAY_CHOP)
    return _ensure_audio_output_chain(eng)


_AUDIO_TRIGGER_OUTPUT_PARS = (
    # (band_key, settings out par, reverse toggle par, raw gate CHOP)
    ('low', 'Audiooutkick', 'Audioreverselow', 'trigger_low'),
    ('high', 'Audioouthit', 'Audioreversehigh', 'trigger_high'),
    ('peak', 'Audiooutpeakhit', 'Audioreversepeak', 'trigger_peak'),
)

_AUDIO_LEVEL_OUTPUT_PARS = (
    ('peak', 'Audiooutpeak'),
    ('low', 'Audiooutlow'),
    ('high', 'Audioouthigh'),
)


def _audio_engine_op_path():
    eng = _audio_engine()
    if eng is not None:
        return eng.path
    r = _root()
    if r is not None:
        return r.path + '/' + AUDIO_ENGINE_NAME
    return '/project1/performance_mode/audio_engine'


def _audio_channel_read_expr(channel, normalized=True):
    """Safe CHOP channel read for parameter expressions (never returns None)."""
    eng_path = _audio_engine_op_path().replace("'", "\\'")
    raw_path = "{}/{}".format(eng_path, AUDIO_OUT_CHOP)
    raw = "float(op('{raw}')['{channel}'] or 0)".format(raw=raw_path, channel=channel)
    # out_values levels are already gain-normalized 0-1; clamp for safety.
    if not normalized:
        return raw
    return "min(max({}, 0), 1)".format(raw)


def _audio_out_trigger_expr(band_key, reverse_par, gate_chop):
    """0-1 trigger for Map/Pulse — applies Reverse so outs always match the toggle."""
    eng_path = _audio_engine_op_path().replace("'", "\\'")
    gate_path = "{}/{}".format(eng_path, gate_chop).replace("'", "\\'")
    # Raw gate from logicCHOP (chan1); reverse in the expression so Map sees it.
    gate = (
        "min(max(float((op('{g}')['chan1'] if op('{g}') else 0) or 0), 0), 1)"
    ).format(g=gate_path)
    return (
        "me.par.Audioactive * ("
        "me.par.{rev} * (1.0 - ({gate})) + (1.0 - me.par.{rev}) * ({gate})"
        ")"
    ).format(rev=reverse_par, gate=gate)


def audio_chop_reference_expr(channel='low', scale=100):
    """Live Reference expression for effect parameters (reads cooking audio CHOP)."""
    settings = _audio_settings_path().replace("'", "\\'")
    core = (
        "min(max({} * op('{s}').par.Audioactive, 0), 1)"
    ).format(_audio_channel_read_expr(channel, normalized=True), s=settings)
    if float(scale) == 1.0:
        return core
    return '{} * {}'.format(core, float(scale))


def _wire_audio_par_expr(p, expr):
    """Bind a settings float to an expression without spamming panel rebuilds."""
    try:
        cur = str(getattr(p, 'expr', '') or '').strip()
    except Exception:
        cur = ''
    need_expr = cur != expr
    need_mode = True
    try:
        need_mode = p.mode != ParMode.EXPRESSION
    except Exception:
        need_mode = True
    if not need_expr and not need_mode:
        try:
            p.clampMin = True
            p.clampMax = True
            p.normMin = 0.0
            p.normMax = 1.0
            p.readOnly = True
        except Exception:
            pass
        return
    was_ro = bool(getattr(p, 'readOnly', False))
    if was_ro:
        p.readOnly = False
    if need_expr:
        p.expr = expr
    if need_mode:
        p.mode = ParMode.EXPRESSION
    try:
        p.clampMin = True
        p.clampMax = True
        p.normMin = 0.0
        p.normMax = 1.0
    except Exception:
        pass
    p.readOnly = True


def _wire_audio_output_exprs(s=None):
    """Wire continuous levels + triggers from out_values into Settings pars."""
    if s is None:
        s = _settings()
    if s is None:
        return
    for ch_name, par_name in _AUDIO_LEVEL_OUTPUT_PARS:
        try:
            _wire_audio_par_expr(getattr(s.par, par_name), _audio_channel_read_expr(ch_name, normalized=True))
        except Exception:
            pass
    for _band, par_name, rev_par, gate_chop in _AUDIO_TRIGGER_OUTPUT_PARS:
        try:
            _wire_audio_par_expr(
                getattr(s.par, par_name),
                _audio_out_trigger_expr(_band, rev_par, gate_chop),
            )
        except Exception:
            pass
    try:
        heal_unsafe_parameter_binds()
    except Exception:
        pass


def on_audio_smooth_change():
    """Legacy hook — smoothing removed; refresh output wiring."""
    _wire_audio_output_exprs()


def _heal_audio_output_exprs(s=None):
    """Re-wire if TD left Out pars in stale CONSTANT mode (breaks Reference)."""
    if s is None:
        s = _settings()
    if s is None:
        return False
    checks = (
        [(_audio_channel_read_expr(ch, normalized=True), name) for ch, name in _AUDIO_LEVEL_OUTPUT_PARS]
        + [
            (_audio_out_trigger_expr(band, rev, gate), name)
            for band, name, rev, gate in _AUDIO_TRIGGER_OUTPUT_PARS
        ]
    )
    for expected, par_name in checks:
        try:
            p = getattr(s.par, par_name)
            if p.mode != ParMode.EXPRESSION:
                _wire_audio_output_exprs(s)
                return True
            if str(getattr(p, 'expr', '') or '').strip() != expected:
                _wire_audio_output_exprs(s)
                return True
        except Exception:
            pass
    return False


def _sync_audio_output_pars():
    _heal_audio_output_exprs()
    eng = _audio_engine()
    if eng is not None:
        _heal_audio_output_chain(eng)


def _audio_tab_par_order():
    return _audio_tab_visible_par_order()


def _audio_tab_visible_par_order():
    return tuple(name for name, _label in _AUDIO_TAB_VISIBLE)


def _audio_tab_allowed_pars():
    """Visible + internal Audio pars that must not be destroyed by cleanup."""
    return set(_audio_tab_visible_par_order()) | set(_AUDIO_TAB_INTERNAL)


def _sync_audio_tab_layout(s=None):
    """Audio tab: device + spectrum + live triggers for mapping."""
    if s is None:
        s = _settings()
    if s is None:
        return
    for index, (name, label) in enumerate(_AUDIO_TAB_VISIBLE):
        try:
            p = getattr(s.par, name)
            p.label = label
            p.enable = True
            p.order = float(index)
        except Exception:
            pass
    # Internal engine pars stay enabled (TD can't hide them; disable only greys them out).
    # Park them after the visible block so the main Audio controls stay on top.
    hidden_start = float(len(_AUDIO_TAB_VISIBLE) + 10)
    visible = set(_audio_tab_visible_par_order())
    for offset, name in enumerate(_AUDIO_TAB_INTERNAL):
        if name in visible:
            continue
        try:
            p = getattr(s.par, name)
            p.enable = True
            p.order = hidden_start + float(offset)
        except Exception:
            pass
    _sync_audio_monitor_pulse_label(s)


def _reorder_audio_tab_pars():
    s = _settings()
    if s is None:
        return
    _sync_audio_tab_layout(s)


def _settings_expr(par_name):
    return "op('{}').par.{}".format(_audio_settings_path(), par_name)


def _ensure_audio_settings():
    s = _settings()
    if s is None:
        return
    page = None
    for pg in s.customPages:
        if pg.name == 'Audio':
            page = pg
            break
    if page is None:
        page = s.appendCustomPage('Audio')

    def _toggle(name, label, default):
        try:
            getattr(s.par, name)
        except Exception:
            p = page.appendToggle(name, label=label)
            p.default = default
            p.val = default

    def _flt(name, label, default, mn=0.0, mx=1.0, readonly=False):
        try:
            p = getattr(s.par, name)
        except Exception:
            p = page.appendFloat(name, label=label)
            p.default = default
            p.val = default
            p.min = mn
            p.max = mx
        else:
            p = getattr(s.par, name)
        try:
            p.label = label
        except Exception:
            pass
        try:
            p.min = mn
            p.max = mx
        except Exception:
            pass
        if readonly:
            try:
                p.readOnly = True
            except Exception:
                pass
        return p

    def _menu(name, label, names, labels, default):
        try:
            getattr(s.par, name)
        except Exception:
            p = page.appendMenu(name, label=label)
            p.menuNames = names
            p.menuLabels = labels
            p.default = default
            p.val = default

    def _out_flt(name, label):
        p = _flt(name, label, 0.0, 0.0, 1.0, readonly=True)
        try:
            p.clampMin = True
            p.clampMax = True
            p.normMin = 0.0
            p.normMax = 1.0
        except Exception:
            pass
        return p

    for stale in (
        'Audioselectband', 'Audiopanelshow', 'Audiodevicelabel', 'Audioshowhist',
        'Audiollowmin', 'Audiollowmax', 'Audiohighmin', 'Audiohighmax',
        'Audiollowrange', 'Audionormnote', 'Audionormpeak', 'Audionormlow', 'Audionormhigh',
        'Audioskip', 'Audionote',
    ) + _REMOVED_AUDIO_PARS:
        try:
            getattr(s.par, stale).destroy()
        except Exception:
            pass

    _migrate_audio_band_storage_from_pars(s)

    _toggle('Audioactive', 'Audio Active', DEFAULT_AUDIO_ACTIVE)
    _flt('Audiogain', 'Gain', DEFAULT_AUDIO_GAIN, 0.0, AUDIO_GAIN_MAX)
    _menu('Audiodeviceindex', 'Input Device', ('0',), ('Default',), '0')
    try:
        getattr(s.par, 'Audiorefresh')
    except AttributeError:
        try:
            page.appendPulse('Audiorefresh', label='Refresh Audio Input')
        except Exception:
            pass
    _ensure_audio_monitor_toggle(s, page)
    _flt('Audiothresholdlow', 'Low Threshold', DEFAULT_THRESH_LOW, 0.0, 1.0)
    _flt('Audiothresholdhigh', 'High Threshold', DEFAULT_THRESH_HIGH, 0.0, 1.0)
    _flt('Audiothresholdpeak', 'Peak Threshold', DEFAULT_THRESH_PEAK, 0.0, 1.0)
    _toggle('Audioreverselow', 'Reverse Low Trigger', False)
    _toggle('Audioreversehigh', 'Reverse High Trigger', False)
    _toggle('Audioreversepeak', 'Reverse Peak Trigger', False)
    _out_flt('Audiooutlow', 'Low')
    _out_flt('Audiooutkick', 'Low Trigger')
    _out_flt('Audioouthigh', 'High')
    _out_flt('Audioouthit', 'High Trigger')
    _out_flt('Audiooutpeak', 'Peak')
    _out_flt('Audiooutpeakhit', 'Peak Trigger')

    _destroy_removed_audio_pars(s)
    _wire_audio_output_exprs(s)
    _sync_audio_tab_layout(s)


_AUDIO_DEVICE_REFRESH_TICK = 0


def _as_audio_menu_list(items):
    if items is None:
        return []
    if isinstance(items, str):
        return [items]
    if isinstance(items, (list, tuple)):
        return [str(x) for x in items]
    return [str(items)]


def _audio_device_display_labels(labels):
    """VB-Audio capture endpoint is named CABLE Output in TD; users expect CABLE Input."""
    out = []
    for label in labels:
        text = str(label)
        if 'CABLE Output' in text and 'VB-Audio' in text:
            out.append('CABLE Input (VB-Audio Virtual Cable)')
        else:
            out.append(text)
    return out


def _audio_device_setting_index(cur, dev_names):
    """Settings menu stores simple indices; accept legacy device tokens too."""
    dev_names = _as_audio_menu_list(dev_names)
    if not dev_names:
        return '0'
    cur = str(cur).strip()
    if cur.isdigit():
        i = int(cur)
        if 0 <= i < len(dev_names):
            return str(i)
    if cur in dev_names:
        return str(dev_names.index(cur))
    return '0'


def _audio_device_token_from_setting(cur, dev_names):
    dev_names = _as_audio_menu_list(dev_names)
    if not dev_names:
        return 'default'
    idx = _audio_device_setting_index(cur, dev_names)
    i = int(idx)
    if 0 <= i < len(dev_names):
        return dev_names[i]
    return dev_names[0]


def _preferred_audio_device_index(labels):
    for i, label in enumerate(_as_audio_menu_list(labels)):
        text = str(label).upper()
        if 'CABLE' in text and ('INPUT' in text or 'OUTPUT' in text):
            return str(i)
    return None


def _apply_preferred_audio_device():
    """Default to VB-Audio CABLE Input when present."""
    s = _settings()
    if s is None:
        return
    try:
        labels = _as_audio_menu_list(s.par.Audiodeviceindex.menuLabels)
    except Exception:
        return
    preferred = _preferred_audio_device_index(labels)
    if preferred is None:
        return
    try:
        p = s.par.Audiodeviceindex
        if str(p.eval()) == str(p.default):
            p.val = preferred
            _apply_audio_device()
    except Exception:
        pass


def _refresh_audio_device_menu(force=False):
    s = _settings()
    eng = _audio_engine()
    if s is None or eng is None:
        return
    dev = eng.op('audiodevin1')
    if dev is None:
        return
    try:
        if force:
            dev.par.active = False
            dev.par.active = True
            dev.cook(force=True)
    except Exception:
        pass
    try:
        dev_names = _as_audio_menu_list(dev.par.device.menuNames)
        labels = _audio_device_display_labels(dev.par.device.menuLabels)
    except Exception:
        dev_names, labels = ['default'], ['default']
    if not dev_names:
        dev_names, labels = ['default'], ['default']
    if len(labels) != len(dev_names):
        labels = list(dev_names)
    # Long Windows device IDs break parameterCOMP menus — use 0..n-1 indices.
    menu_names = [str(i) for i in range(len(dev_names))]
    menu_labels = _as_audio_menu_list(labels)
    try:
        p = s.par.Audiodeviceindex
        if not force:
            try:
                cur_names = tuple(_as_audio_menu_list(p.menuNames))
                cur_labels = tuple(_as_audio_menu_list(p.menuLabels))
            except Exception:
                cur_names = cur_labels = ()
            if cur_names == tuple(menu_names) and cur_labels == tuple(menu_labels):
                return
        cur_idx = _audio_device_setting_index(p.eval(), dev_names)
    except Exception:
        cur_idx = '0'
    try:
        p.menuNames = list(menu_names)
        p.menuLabels = list(menu_labels)
        p.val = cur_idx
    except Exception:
        pass


def _apply_audio_device():
    s = _settings()
    eng = _audio_engine()
    if s is None or eng is None:
        return
    dev = eng.op('audiodevin1')
    if dev is None:
        return
    try:
        dev_names = _as_audio_menu_list(dev.par.device.menuNames)
        token = _audio_device_token_from_setting(s.par.Audiodeviceindex.eval(), dev_names)
        if token in dev_names:
            # Packaged projects can restore the menu value while the native
            # capture endpoint remains unopened. Restart the CHOP whenever the
            # requested token is not already live.
            active = _audio_active()
            dev.par.active = False
            dev.par.device = token
            dev.par.active = bool(active)
            if active:
                dev.cook(force=True)
    except Exception:
        pass


def _wire_chop(src, dst, out_idx=0, in_idx=0):
    if src is None or dst is None:
        return
    try:
        src.outputConnectors[out_idx].connect(dst.inputConnectors[in_idx])
    except Exception:
        pass


def _wire_sop(src, dst, out_idx=0, in_idx=0):
    if src is None or dst is None:
        return
    try:
        src.outputConnectors[out_idx].connect(dst.inputConnectors[in_idx])
    except Exception:
        pass


def _ensure_geo_in_sop(geo):
    if geo is None:
        return None
    geo_in = geo.op('in1')
    if geo_in is None:
        try:
            geo_in = geo.create('inSOP', 'in1')
        except Exception:
            geo_in = None
    return geo_in


def _set_chop_expr(chop, par_name, expr):
    if chop is None:
        return
    try:
        p = getattr(chop.par, par_name)
        p.expr = expr
        p.mode = ParMode.EXPRESS
    except Exception:
        pass


def _chop_input_owner(chop, in_idx=0):
    if chop is None:
        return None
    try:
        conns = chop.inputConnectors[in_idx].connections
        if not conns:
            return None
        return conns[0].owner
    except Exception:
        return None


def _chop_scalar_abs(chop, chan='chan1'):
    if chop is None:
        return 0.0
    try:
        return abs(float(chop[chan].eval()))
    except Exception:
        try:
            return abs(float(chop[chan]))
        except Exception:
            return 0.0


def _chop_channel_max_abs(chop, chan='chan1'):
    if chop is None:
        return 0.0
    try:
        peak = 0.0
        for i in range(chop.numSamples):
            peak = max(peak, abs(float(chop[chan][i])))
        return peak
    except Exception:
        return 0.0


def _configure_audio_spectrum_chop(spect):
    if spect is None:
        return
    try:
        # Visual mode spans the full range to Nyquist. Keep the established
        # 1024 FFT so existing Low/High trigger thresholds retain their scale.
        spect.par.mode = 'visual'
        spect.par.fftsize = '1024'
        spect.par.frequencylog = True
        spect.par.highfreqboost = 0.75
        spect.par.outputmenu = 'setmanually'
        spect.par.outlength = AUDIO_HIST_BINS
        spect.par.timeslice = False
    except Exception:
        pass


def _enforce_audio_spectrum_runtime(refresh_visuals=False):
    """Restore the full-range display without rebuilding the trigger chain."""
    eng = _audio_engine()
    if eng is None:
        return False
    spect = eng.op('audiospect1')
    gain = eng.op('gain1')
    if spect is None or gain is None:
        return False
    _configure_audio_spectrum_chop(spect)
    if _chop_input_owner(spect) is not gain:
        _wire_chop(gain, spect)
    # The histogram must read the complete Audio Spectrum channel, not a stale
    # channel name retained from an earlier audio device.
    sel = eng.op('spect_bar_sel')
    if sel is not None:
        try:
            channels = list(spect.chans())
            sel.par.channames = channels[0].name if channels else 'chan1'
        except Exception:
            pass
    if refresh_visuals:
        try:
            root_comp = _root()
            strip = root_comp.op('ui/audio_band_strip') if root_comp is not None else None
            view = strip.op('audio_band_view') if strip is not None else None
            if view is not None:
                _sync_spectrogram_display(view, force=True)
        except Exception:
            pass
    return True


def _rebuild_audio_spectrum_chain(eng):
    """Recreate audiospectrum and rewire downstream analysis nodes."""
    if eng is None:
        return False
    gain = eng.op('gain1')
    try:
        eng.op('audiospect1').destroy()
    except Exception:
        pass
    spect = eng.create('audiospectrumCHOP', 'audiospect1')
    _configure_audio_spectrum_chop(spect)
    _wire_chop(gain, spect)
    for dst_name in ('trim_low', 'trim_high', 'analyze_peak'):
        dst = eng.op(dst_name)
        if dst is not None:
            _wire_chop(spect, dst)
    try:
        eng.cook(force=True)
    except Exception:
        pass
    return True


def _audio_spectrum_is_stale(eng=None):
    if eng is None:
        eng = _audio_engine()
    if eng is None or not _audio_active():
        return False
    spect = eng.op('audiospect1')
    gain = eng.op('gain1')
    dev = eng.op('audiodevin1')
    if spect is None:
        return True
    try:
        if spect.errors():
            return True
    except Exception:
        pass
    if _chop_input_owner(spect) not in (gain, dev):
        return True
    try:
        eng.cook(force=True)
    except Exception:
        pass
    input_level = max(_chop_scalar_abs(gain), _chop_scalar_abs(dev))
    if input_level < 0.005:
        return False
    return _chop_channel_max_abs(spect) < 1e-6


def _heal_audio_spectrum_if_needed(eng=None):
    if eng is None:
        eng = _audio_engine()
    if eng is None or not _audio_active():
        return False
    if not _audio_spectrum_is_stale(eng):
        return False
    print('Sonomika: healing stale audio spectrum CHOP')
    _rebuild_audio_spectrum_chain(eng)
    return True


def _ensure_audio_engine():
    r = _root()
    if r is None:
        return None
    eng = r.op(AUDIO_ENGINE_NAME)
    if eng is None:
        eng = r.create('baseCOMP', AUDIO_ENGINE_NAME)

    devin = eng.op('audiodevin1')
    if devin is None:
        devin = eng.create('audiodeviceinCHOP', 'audiodevin1')

    gain = eng.op('gain1')
    if gain is None:
        gain = eng.create('mathCHOP', 'gain1')
    try:
        gain.par.preoff = 0
        gain.par.gain.expr = _settings_expr('Audiogain')
        gain.par.gain.mode = ParMode.EXPRESS
        gain.par.postoff = 0
    except Exception:
        pass
    _wire_chop(devin, gain)

    spect = eng.op('audiospect1')
    if spect is None:
        spect = eng.create('audiospectrumCHOP', 'audiospect1')
    _configure_audio_spectrum_chop(spect)
    _wire_chop(gain, spect)

    # Mono spectrum for band analyze/triggers (stereo collapses Merge unique names).
    spect_mono = eng.op('spect_mono')
    if spect_mono is None:
        spect_mono = eng.create('selectCHOP', 'spect_mono')
    try:
        chan_names = [c.name for c in spect.chans()]
        spect_mono.par.channames = chan_names[0] if chan_names else 'chan1'
    except Exception:
        try:
            spect_mono.par.channames = 'chan1'
        except Exception:
            pass
    _wire_chop(spect, spect_mono)

    trim_low = eng.op('trim_low')
    if trim_low is not None:
        try:
            # Stale stereo Trim CHOPs keep 2 channels even after mono input — recreate.
            if int(trim_low.numChans) > 1:
                trim_low.destroy()
                trim_low = None
        except Exception:
            pass
    if trim_low is None:
        trim_low = eng.create('trimCHOP', 'trim_low')
    try:
        trim_low.par.relative = 'abs'
        trim_low.par.startunit = 'samples'
        trim_low.par.endunit = 'samples'
    except Exception:
        pass
    _set_chop_expr(
        trim_low, 'start',
        'max(0, ({pos}) - ({width}) * 0.5) * (me.inputs[0].numSamples - 1)'.format(
            pos=_audio_band_fetch_expr('bass', 'pos'),
            width=_audio_band_fetch_expr('bass', 'width'),
        ),
    )
    _set_chop_expr(
        trim_low, 'end',
        'min(1, ({pos}) + ({width}) * 0.5) * (me.inputs[0].numSamples - 1)'.format(
            pos=_audio_band_fetch_expr('bass', 'pos'),
            width=_audio_band_fetch_expr('bass', 'width'),
        ),
    )
    _wire_chop(spect_mono, trim_low)

    trim_high = eng.op('trim_high')
    if trim_high is not None:
        try:
            if int(trim_high.numChans) > 1:
                trim_high.destroy()
                trim_high = None
        except Exception:
            pass
    if trim_high is None:
        trim_high = eng.create('trimCHOP', 'trim_high')
    try:
        trim_high.par.relative = 'abs'
        trim_high.par.startunit = 'samples'
        trim_high.par.endunit = 'samples'
    except Exception:
        pass
    _set_chop_expr(
        trim_high, 'start',
        'max(0, ({pos}) - ({width}) * 0.5) * (me.inputs[0].numSamples - 1)'.format(
            pos=_audio_band_fetch_expr('high', 'pos'),
            width=_audio_band_fetch_expr('high', 'width'),
        ),
    )
    _set_chop_expr(
        trim_high, 'end',
        'min(1, ({pos}) + ({width}) * 0.5) * (me.inputs[0].numSamples - 1)'.format(
            pos=_audio_band_fetch_expr('high', 'pos'),
            width=_audio_band_fetch_expr('high', 'width'),
        ),
    )
    _wire_chop(spect_mono, trim_high)

    analyze_low = eng.op('analyze_low')
    if analyze_low is not None:
        try:
            if int(analyze_low.numChans) > 1:
                analyze_low.destroy()
                analyze_low = None
        except Exception:
            pass
    if analyze_low is None:
        analyze_low = eng.create('analyzeCHOP', 'analyze_low')
    try:
        # TD Analyze CHOP uses 'rmspower' (not 'rms') — Low band energy.
        analyze_low.par.function = 'rmspower'
    except Exception:
        pass
    _wire_chop(trim_low, analyze_low)

    analyze_high = eng.op('analyze_high')
    if analyze_high is not None:
        try:
            if int(analyze_high.numChans) > 1:
                analyze_high.destroy()
                analyze_high = None
        except Exception:
            pass
    if analyze_high is None:
        analyze_high = eng.create('analyzeCHOP', 'analyze_high')
    try:
        # Maximum tracks hi-hat / transient energy better than averaging a wide band
        analyze_high.par.function = 'maximum'
    except Exception:
        pass
    _wire_chop(trim_high, analyze_high)

    analyze_peak = eng.op('analyze_peak')
    if analyze_peak is not None:
        try:
            if int(analyze_peak.numChans) > 1:
                analyze_peak.destroy()
                analyze_peak = None
        except Exception:
            pass
    if analyze_peak is None:
        analyze_peak = eng.create('analyzeCHOP', 'analyze_peak')
    try:
        analyze_peak.par.function = 'maximum'
    except Exception:
        pass
    _wire_chop(spect_mono, analyze_peak)

    def _ensure_norm_for_trigger(name, src):
        """Gain-normalize analyze output so Bass/High Threshold are real 0-1 gates."""
        node = eng.op(name)
        if node is None:
            node = eng.create('mathCHOP', name)
        try:
            node.par.preoff = 0
            node.par.postoff = 0
            node.par.gain.expr = '1.0 / max({}, 0.001)'.format(_settings_expr('Audiogain'))
            node.par.gain.mode = ParMode.EXPRESSION
        except Exception:
            pass
        _wire_chop(src, node)
        return node

    def _configure_band_gate(gate, thr_par_name):
        """0/1 gate while normalized level is inside [threshold, 1]."""
        try:
            gate.par.convert = 'bound'
            thr_expr = _settings_expr(thr_par_name)
            gate.par.boundmin.expr = thr_expr
            gate.par.boundmin.mode = ParMode.EXPRESSION
            gate.par.boundmax = 1.0
            gate.par.boundmax.mode = ParMode.CONSTANT
            if hasattr(gate.par, 'preop'):
                gate.par.preop = 'off'
            if hasattr(gate.par, 'chanop'):
                gate.par.chanop = 'off'
        except Exception:
            pass

    def _ensure_band_gate(name, thr_par_name, src):
        node = eng.op(name)
        if node is not None and getattr(node, 'type', None) != 'logic':
            try:
                node.destroy()
            except Exception:
                pass
            node = None
        if node is None:
            node = eng.create('logicCHOP', name)
        _configure_band_gate(node, thr_par_name)
        _wire_chop(src, node)
        return node

    def _ensure_trigger_reverse(name, reverse_par_name, src):
        """Pass-through or invert a 0/1 gate: out = src*(1-2*rev) + rev."""
        node = eng.op(name)
        if node is None:
            node = eng.create('mathCHOP', name)
        try:
            rev_expr = _settings_expr(reverse_par_name)
            node.par.preoff = 0
            node.par.gain.expr = '1.0 - 2.0 * ({})'.format(rev_expr)
            node.par.gain.mode = ParMode.EXPRESSION
            node.par.postoff.expr = rev_expr
            node.par.postoff.mode = ParMode.EXPRESSION
        except Exception:
            pass
        _wire_chop(src, node)
        return node

    norm_low = _ensure_norm_for_trigger('norm_low', analyze_low)
    norm_high = _ensure_norm_for_trigger('norm_high', analyze_high)
    norm_peak = _ensure_norm_for_trigger('norm_peak', analyze_peak)

    trig_low = _ensure_band_gate('trigger_low', 'Audiothresholdlow', norm_low)
    trig_high = _ensure_band_gate('trigger_high', 'Audiothresholdhigh', norm_high)
    trig_peak = _ensure_band_gate('trigger_peak', 'Audiothresholdpeak', norm_peak)
    out_trig_low = _ensure_trigger_reverse('trigger_low_rev', 'Audioreverselow', trig_low)
    out_trig_high = _ensure_trigger_reverse('trigger_high_rev', 'Audioreversehigh', trig_high)
    out_trig_peak = _ensure_trigger_reverse('trigger_peak_rev', 'Audioreversepeak', trig_peak)

    # Recreate merge when channel count is wrong (stereo collapse or leftover).
    merge = eng.op('merge1')
    need_new_merge = merge is None
    if merge is not None:
        try:
            if int(merge.numChans) != 6:
                need_new_merge = True
        except Exception:
            need_new_merge = True
    if need_new_merge and merge is not None:
        try:
            merge.destroy()
        except Exception:
            pass
        merge = None
    if merge is None:
        merge = eng.create('mergeCHOP', 'merge1')
    try:
        merge.par.duplicate = 'unique'
    except Exception:
        pass
    # Levels are gain-normalized 0-1; triggers are 0/1 gates (optional reverse).
    for idx, src in enumerate((
        norm_peak, norm_low, norm_high,
        out_trig_peak, out_trig_low, out_trig_high,
    )):
        _wire_chop(src, merge, in_idx=idx)

    rename = eng.op('rename1')
    if rename is None:
        rename = eng.create('renameCHOP', 'rename1')
    try:
        rename.par.renamefrom = 'chan1 chan2 chan3 chan4 chan5 chan6'
        rename.par.renameto = 'peak low high peak_trigger low_trigger high_trigger'
    except Exception:
        pass
    _wire_chop(merge, rename)

    # Viewer channel order / labels: Low_Trigger, Low, High_Trigger, High, peak
    view_sel = eng.op('out_view_sel')
    if view_sel is None:
        view_sel = eng.create('selectCHOP', 'out_view_sel')
    try:
        view_sel.par.channames = 'low_trigger low high_trigger high peak'
    except Exception:
        pass
    _wire_chop(rename, view_sel)

    view_ren = eng.op('out_view')
    if view_ren is None:
        view_ren = eng.create('renameCHOP', 'out_view')
    try:
        view_ren.par.renamefrom = 'low_trigger low high_trigger high peak'
        view_ren.par.renameto = 'Low_Trigger Low High_Trigger High peak'
    except Exception:
        pass
    _wire_chop(view_sel, view_ren)

    outv = eng.op(AUDIO_OUT_CHOP)
    if outv is None:
        outv = eng.create('nullCHOP', AUDIO_OUT_CHOP)
    _wire_chop(rename, outv)

    _heal_audio_output_chain(eng)
    _wire_audio_output_exprs()

    _refresh_audio_device_menu()
    _apply_audio_device()
    _sync_audio_active()
    _heal_audio_spectrum_if_needed(eng)
    return eng


def _audio_sample_rate():
    eng = _audio_engine()
    dev = eng.op('audiodevin1') if eng is not None else None
    if dev is not None:
        try:
            return max(8000.0, float(dev.rate))
        except Exception:
            pass
    spect = eng.op('audiospect1') if eng is not None else None
    if spect is not None:
        try:
            return max(8000.0, float(spect.rate))
        except Exception:
            pass
    return 44100.0


def _audio_spectrum_log_scale():
    eng = _audio_engine()
    spect = eng.op('audiospect1') if eng is not None else None
    if spect is None:
        return True
    for par_name in ('frequencylog',):
        try:
            return bool(int(float(getattr(spect.par, par_name).eval())))
        except Exception:
            pass
    return True


def _audio_hz_limits():
    rate = _audio_sample_rate()
    nyq = max(100.0, rate * 0.5)
    f_min = AUDIO_FREQ_MIN_HZ
    f_max = nyq
    if f_max <= f_min:
        f_max = f_min + 1.0
    return f_min, f_max, _audio_spectrum_log_scale()


def _audio_norm_to_hz(u):
    """Map normalized spectrogram X (0-1) to Hz (matches audiospectrum log axis)."""
    u = _norm(u)
    f_min, f_max, log_scale = _audio_hz_limits()
    if log_scale:
        return float(f_min) * ((float(f_max) / float(f_min)) ** u)
    eng = _audio_engine()
    spect = eng.op('audiospect1') if eng is not None else None
    num = int(spect.numSamples) if spect is not None else 22050
    return u * max(1, num - 1)


def _audio_hz_format(hz):
    hz = max(0.0, float(hz))
    if hz >= 10000.0:
        return '{:.1f}k'.format(hz / 1000.0)
    if hz >= 1000.0:
        return '{:.2f}k'.format(hz / 1000.0)
    if hz >= 100.0:
        return '{:.0f}'.format(hz)
    return '{:.1f}'.format(hz)


def _audio_range_hz_text(lo_norm, hi_norm):
    lo_hz = _audio_norm_to_hz(lo_norm)
    hi_hz = _audio_norm_to_hz(hi_norm)
    if hi_hz < lo_hz:
        lo_hz, hi_hz = hi_hz, lo_hz
    return '{} - {} Hz'.format(_audio_hz_format(lo_hz), _audio_hz_format(hi_hz))


def _audio_band_edges(pos_par, width_par, default_pos, default_width):
    """Legacy signature — pos_par is 'bass'/'high' or legacy par name."""
    band = 'high' if 'high' in str(pos_par).lower() else 'bass'
    pos, width = _audio_band_pos_width_values(band)
    lo = _norm(pos - width * 0.5)
    hi = _norm(pos + width * 0.5)
    if hi < lo:
        lo, hi = hi, lo
    return lo, hi


def _audio_band_hz_from_pos_width(pos_par, width_par, default_pos, default_width):
    lo, hi = _audio_band_edges(pos_par, width_par, default_pos, default_width)
    return _audio_range_hz_text(lo, hi)


def _audio_band_hz_for_band(band):
    if band == 'high':
        return _audio_band_hz_from_pos_width('high', '', DEFAULT_HIGH_POS, DEFAULT_HIGH_WIDTH)
    return _audio_band_hz_from_pos_width('bass', '', DEFAULT_BASS_POS, DEFAULT_BASS_WIDTH)


def _sync_audio_hz_display_pars():
    return


def _audio_hist_w():
    return max(480, UI_W - AUDIO_SPECT_PAD * 2)


def _audio_band_strip_w():
    """Spectrum width inside the Audio Analysis panel (leaves room for peak bar + meters)."""
    return max(
        200,
        _settings_panel_w()
        - AUDIO_BAND_STRIP_PAD * 4
        - AUDIO_PEAK_THRESH_W
        - AUDIO_ANALYSIS_SIDE_W,
    )


def _audio_band_strip_view_h():
    return max(40, AUDIO_BAND_STRIP_H - AUDIO_BAND_STRIP_PAD * 2)


def _audio_hist_render_size(view_w=None, view_h=None):
    """Render at panel resolution so bars fill the spectrum view 1:1."""
    try:
        vw = int(view_w or 0)
    except Exception:
        vw = 0
    try:
        vh = int(view_h or 0)
    except Exception:
        vh = 0
    if vw <= 0:
        vw = AUDIO_HIST_RENDER_W
    if vh <= 0:
        vh = AUDIO_HIST_RENDER_H
    vw = max(64, min(AUDIO_HIST_RENDER_W_MAX, vw))
    vh = max(48, min(AUDIO_HIST_RENDER_H_MAX, vh))
    return vw, vh


def _set_top_input(top, src):
    if top is None or src is None:
        return
    path = src.path if hasattr(src, 'path') else str(src)
    try:
        top.par.top = path
    except Exception:
        pass


def _wire_top_inputs(comp, sources):
    """Connect TOP inputs via connectors (required for compositeTOP in TD 2025+)."""
    if comp is None:
        return
    sources = [s for s in sources if s is not None]
    try:
        for ic in comp.inputConnectors:
            ic.disconnect()
    except Exception:
        pass
    for idx, src in enumerate(sources):
        try:
            src.outputConnectors[0].connect(comp.inputConnectors[idx])
        except Exception:
            pass
    try:
        comp.par.top = ' '.join(s.path for s in sources)
    except Exception:
        pass


def _configure_composite(comp, sources, operand='over', operand2=None, opacity2=None):
    if comp is None:
        return
    _wire_top_inputs(comp, sources)
    try:
        comp.par.operand = operand
        if operand2 is not None:
            comp.par.operand2 = operand2
    except Exception:
        pass
    if opacity2 is not None:
        try:
            comp.par.opacity2 = opacity2
        except Exception:
            pass
    _set_top_res(comp, _audio_hist_w(), AUDIO_SPECT_H)


def _purge_stray_audio_paramcomps(container):
    """parameterCOMP under the audio strip bleeds /settings (Canvas) into Perform."""
    if container is None:
        return
    for name in ('audio_controls', 'audio_settings', 'settings_embed'):
        stale = container.op(name)
        if stale is not None:
            try:
                stale.destroy()
            except Exception:
                pass
    for ch in list(container.children):
        try:
            if ch.OPType == 'parameterCOMP':
                ch.destroy()
                continue
        except Exception:
            pass
        _purge_stray_audio_paramcomps(ch)


def _set_top_res(top, w, h):
    if top is None:
        return
    try:
        top.par.outputresolution = 'custom'
        top.par.resolutionw = max(1, int(w))
        top.par.resolutionh = max(1, int(h))
    except Exception:
        pass
    try:
        if hasattr(top.par, 'resmult'):
            top.par.resmult = False
    except Exception:
        pass
    try:
        if hasattr(top.par, 'fillmode'):
            # Avoid letterboxing the histogram inside its own TOP.
            names = [str(x).lower() for x in (top.par.fillmode.menuNames or [])]
            for token in ('fill', 'useinput', 'nativeres'):
                hit = next((n for n in names if token == n or token in n), None)
                if hit is not None:
                    top.par.fillmode = top.par.fillmode.menuNames[names.index(hit)]
                    break
    except Exception:
        pass


def _ensure_script_top(eng, name, callbacks_name, script_text, w, h):
    top = eng.op(name) if eng is not None else None
    if top is not None:
        try:
            if top.OPType != 'scriptTOP':
                top.destroy()
                top = None
        except Exception:
            pass
    if top is None and eng is not None:
        top = eng.create('scriptTOP', name)
    cb = eng.op(callbacks_name) if eng is not None else None
    if cb is None and eng is not None:
        cb = eng.create('textDAT', callbacks_name)
    if cb is not None:
        try:
            cb.text = script_text
            cb.par.language = 'python'
        except Exception:
            pass
    if top is not None:
        try:
            if cb is not None:
                top.par.callbacks = cb.path
            top.par.outputresolution = 'custom'
            top.par.resolutionw = max(1, int(w))
            top.par.resolutionh = max(1, int(h))
        except Exception:
            pass
    return top


def _ensure_script_chop(eng, name, callbacks_name, script_text):
    chop = eng.op(name) if eng is not None else None
    if chop is not None:
        try:
            if chop.OPType != 'scriptCHOP':
                chop.destroy()
                chop = None
        except Exception:
            pass
    if chop is None and eng is not None:
        chop = eng.create('scriptCHOP', name)
    cb = eng.op(callbacks_name) if eng is not None else None
    if cb is None and eng is not None:
        cb = eng.create('textDAT', callbacks_name)
    if cb is not None:
        try:
            cb.text = script_text
            cb.par.language = 'python'
        except Exception:
            pass
    if chop is not None and cb is not None:
        try:
            chop.par.callbacks = cb.path
        except Exception:
            pass
    return chop


def _ensure_constant_top(eng, name, rgb, alpha=1.0):
    """constantTOP color; replace stale ramp/other ops left from older audio chains."""
    top = eng.op(name) if eng is not None else None
    if top is not None:
        try:
            if top.OPType != 'constantTOP':
                top.destroy()
                top = None
        except Exception:
            pass
    if top is None and eng is not None:
        top = eng.create('constantTOP', name)
    if top is None:
        return None
    try:
        top.par.colorr = rgb[0]
        top.par.colorg = rgb[1]
        top.par.colorb = rgb[2]
        top.par.alpha = alpha
    except Exception:
        pass
    return top


def _destroy_spectrogram_scripttop(eng):
    """Remove CPU scriptTOP histogram chain."""
    for stale_name in (
        'spect_bars', 'spect_bars_callbacks', 'spect_bars_color', 'spect_bars_tint',
        'spect_bars_boost', 'spect_bars_xform', 'spect_bars_level', 'spect_bars_tint_keys',
        'spect_bars_chop', 'spect_bars_chop_callbacks', 'spect_bar_peak',
    ):
        stale = eng.op(stale_name) if eng is not None else None
        if stale is not None:
            try:
                stale.destroy()
            except Exception:
                pass


def _spect_bar_count(spect):
    try:
        return max(8, int(spect.numSamples))
    except Exception:
        return AUDIO_HIST_BINS


def _cook_audio_histogram_chain(eng):
    if eng is None:
        return
    for name in (
        'spect_bar_norm', 'spect_bar_sel', 'spect_bar_vis', 'spect_chopto',
        'spect_bars_pixel', 'spect_bars_glsl', 'spect_bar_fb',
        'spect_smooth_pixel', 'spect_bars_smooth', 'spect_render', 'spect_comp',
    ):
        node = eng.op(name)
        if node is None:
            continue
        try:
            node.cook(force=True)
        except Exception:
            pass


def _render_top_has_signal(render):
    if render is None:
        return False
    try:
        import numpy as np
        arr = np.array(render.numpyArray())
        rgb = arr[..., :3] if arr.ndim == 3 and arr.shape[-1] >= 3 else arr
        return float(rgb.max()) > 0.01
    except Exception:
        return False


def _destroy_spectrogram_geo_chain(eng):
    """Remove fragile geo-instancing spectrum nodes."""
    if eng is None:
        return
    for stale_name in (
        'spect_bars_null', 'spect_line', 'spect_line_null', 'spect_box',
        'spect_bar_xform', 'spect_geo', 'spect_mat', 'spect_cam',
        'spect_hist_mix', '_probe_chopto', '_probe_glsl', '_probe_glsl_pixel',
        '_probe_glsl_compute',
    ):
        stale = eng.op(stale_name)
        if stale is not None:
            try:
                stale.destroy()
            except Exception:
                pass


def _ensure_spectrogram_gpu_bars(eng, spect):
    """CHOP normalize -> choptoTOP -> GLSL vertical bars (reliable, no geo)."""
    if eng.op('analyze_peak') is None:
        _ensure_audio_engine()

    stale_peak = eng.op('spect_bar_peak')
    if stale_peak is not None:
        try:
            stale_peak.destroy()
        except Exception:
            pass

    norm = eng.op('spect_bar_norm')
    if norm is None:
        norm = eng.create('mathCHOP', 'spect_bar_norm')
    _wire_chop(spect, norm)
    _set_chop_expr(
        norm, 'gain',
        "1.0 / max(op('analyze_peak')['chan1'].eval(), 1e-4)",
    )

    # Mono strip first — audio device channel names vary by driver.
    sel = eng.op('spect_bar_sel')
    if sel is None:
        sel = eng.create('selectCHOP', 'spect_bar_sel')
    _wire_chop(norm, sel)
    try:
        channels = list(spect.chans())
        sel.par.channames = channels[0].name if channels else '*'
    except Exception:
        try:
            sel.par.channames = '*'
        except Exception:
            pass

    # Skip shuffle↔lag smoothing. Lagging N swapped frequency bins was ~20ms/frame
    # and dominated Open Spectrum cost; GLSL bars stay responsive without it.
    for stale_name in (
        'spect_bar_ds', 'spect_bar_shuf', 'spect_bar_lag', 'spect_bar_unshuf',
    ):
        stale = eng.op(stale_name)
        if stale is None:
            continue
        try:
            stale.bypass = True
        except Exception:
            pass

    vis = eng.op('spect_bar_vis')
    if vis is None:
        vis = eng.create('mathCHOP', 'spect_bar_vis')
    _wire_chop(sel, vis)
    try:
        vis.par.preoff = AUDIO_HIST_BAR_MIN
        vis.par.gain = max(0.1, 0.88 * (1.0 - AUDIO_HIST_BAR_MIN))
        vis.par.postoff = 0
    except Exception:
        pass

    chopto = eng.op('spect_chopto')
    if chopto is None:
        chopto = eng.create('choptoTOP', 'spect_chopto')
    try:
        chopto.par.chop = vis.path
        chopto.par.layout = 'rowscropped'
    except Exception:
        pass
    try:
        # Keep native CHOP size (bins x 1); bars GLSL upscales to panel res.
        chopto.par.outputresolution = 'useinput'
    except Exception:
        pass

    pixel = eng.op('spect_bars_pixel')
    if pixel is None:
        pixel = eng.create('textDAT', 'spect_bars_pixel')
    try:
        pixel.text = _spectrum_pixel_shader()
    except Exception:
        pass

    bars = eng.op('spect_bars_glsl')
    if bars is None:
        bars = eng.create('glslTOP', 'spect_bars_glsl')
    try:
        # DAT parameters are path parameters in TD. Assigning the OP object can
        # silently leave the GLSL TOP pointed at its empty docked default DAT.
        bars.par.pixeldat = pixel.path
        bars.par.pixeldat.mode = ParMode.CONSTANT
    except Exception:
        pass
    try:
        # chopto is mono — Use Input makes GLSL R-only so cyan collapses to grey.
        bars.par.format = 'rgba8fixed'
    except Exception:
        pass
    _wire_top_inputs(bars, (chopto,))
    for stale_name in ('spect_thresh_kick', 'spect_thresh_high', 'spect_thresh_peak'):
        stale = eng.op(stale_name)
        if stale is not None:
            try:
                stale.destroy()
            except Exception:
                pass

    # Cheap temporal smooth on the GPU (replaces expensive per-bin CHOP lag).
    smooth_pixel = eng.op('spect_smooth_pixel')
    if smooth_pixel is None:
        smooth_pixel = eng.create('textDAT', 'spect_smooth_pixel')
    try:
        smooth_pixel.text = _spectrum_temporal_shader()
    except Exception:
        pass

    fb = eng.op('spect_bar_fb')
    if fb is None:
        fb = eng.create('feedbackTOP', 'spect_bar_fb')
    # Match bars resolution; Feedback `top` supplies the previous smoothed frame.
    _wire_top_inputs(fb, (bars,))
    try:
        if hasattr(fb.par, 'fillmode'):
            fb.par.fillmode = 'fill'
    except Exception:
        pass

    smooth = eng.op('spect_bars_smooth')
    if smooth is None:
        smooth = eng.create('glslTOP', 'spect_bars_smooth')
    try:
        smooth.par.pixeldat = smooth_pixel.path
        smooth.par.pixeldat.mode = ParMode.CONSTANT
    except Exception:
        pass
    try:
        smooth.par.format = 'rgba8fixed'
    except Exception:
        pass
    _wire_top_inputs(smooth, (bars, fb))
    try:
        # Previous frame of the smoothed output — kills flicker without long trails.
        fb.par.top = smooth.path
    except Exception:
        pass

    # Keep name spect_render for downstream consumers.
    render = eng.op('spect_render')
    if render is not None and render.type != 'null':
        # Replace old renderTOP with a nullTOP passthrough of GLSL bars.
        try:
            render.destroy()
        except Exception:
            pass
        render = None
    if render is None:
        render = eng.create('nullTOP', 'spect_render')
    _wire_top_inputs(render, (smooth,))
    hold = _ensure_spectrogram_freeze_hold(eng, render)
    # Active is pulsed by _sync_spectrogram_display (frame stride); don't force every rebuild.
    if hold is not None:
        try:
            if _audio_hist_frozen() or (not _audio_spectrum_is_live()):
                hold.par.active = False
        except Exception:
            pass
    _cook_audio_histogram_chain(eng)
    return render


def _ensure_spectrogram_visuals(eng, spect, hist_w=None, hist_h=None):
    """chopto + GLSL spectrum bars."""
    if eng is None or spect is None:
        return
    hist_w = hist_w or _audio_band_strip_w()
    hist_h = hist_h or _audio_band_strip_view_h()

    _destroy_spectrogram_scripttop(eng)
    _destroy_spectrogram_geo_chain(eng)

    render = _ensure_spectrogram_gpu_bars(eng, spect)
    # Set resolution after wiring — some TOP connects reset to input/default size.
    for name in (
        'spect_bars_glsl', 'spect_bars_smooth', 'spect_bar_fb', 'spect_render',
    ):
        node = eng.op(name)
        if node is not None:
            _set_top_res(node, hist_w, hist_h)
    render = eng.op('spect_render') or render
    if render is not None:
        _set_top_res(render, hist_w, hist_h)

    bg = _ensure_constant_top(eng, 'spect_bg', (0.0, 0.0, 0.0), alpha=1.0)
    _set_top_res(bg, hist_w, hist_h)

    # Composite: first input is drawn OVER the second in TD.
    # Bars must be first so opaque black bg does not cover them.
    comp = eng.op('spect_comp')
    if comp is None:
        comp = eng.create('compositeTOP', 'spect_comp')
    _wire_top_inputs(comp, (render, bg))
    try:
        comp.par.operand = 'over'
        comp.par.opacity1 = 1.0
        comp.par.opacity2 = 1.0
    except Exception:
        pass
    _set_top_res(comp, hist_w, hist_h)

    for stale_name in (
        'spect_resample',
        'band_low', 'band_bass', 'band_high', 'thresh_low', 'thresh_bass', 'thresh_high',
        'spect_mix_low', 'spect_mix_bass', 'spect_mix_high', 'spect_mix_tl',
        'spect_col', 'spect_col_level', 'spect_col_tint', 'spect_col_color', 'spect_col_place',
        'spect_feedback', 'spect_scroll_xform', 'spect_scroll', 'spect_hist_base',
    ):
        stale = eng.op(stale_name)
        if stale is not None:
            try:
                stale.destroy()
            except Exception:
                pass


def _audio_band_norms(band):
    if band == 'high':
        return _audio_band_edges('high', '', DEFAULT_HIGH_POS, DEFAULT_HIGH_WIDTH)
    return _audio_band_edges('bass', '', DEFAULT_BASS_POS, DEFAULT_BASS_WIDTH)


def _audio_set_band_pos_width(band, pos, width, commit=True):
    """Move/resize band. During drag commit=False → visual only, no storage spam."""
    width = max(AUDIO_MIN_BAND_WIDTH, _norm(width))
    pos = _norm(pos)
    lo = pos - width * 0.5
    hi = pos + width * 0.5
    if lo < 0.0:
        pos -= lo
    if hi > 1.0:
        pos -= hi - 1.0
    pos = _norm(pos)
    if not commit:
        _AUDIO_HIST_DRAG['live_band'] = band
        _AUDIO_HIST_DRAG['live_pos'] = pos
        _AUDIO_HIST_DRAG['live_width'] = width
        _apply_band_position_visual(band, pos, width)
        return
    s = _settings()
    if s is None:
        return
    pos_key, width_key, _def_pos, _def_width = _AUDIO_BAND_STORE[band]
    try:
        s.store(pos_key, pos)
        s.store(width_key, width)
    except Exception:
        pass
    _apply_band_position_visual(band, pos, width)
    _sync_audio_hz_display_pars()
    _mark_audio_hist_overlays_dirty()


def _apply_band_position_visual(band, pos, width, view=None):
    """Reposition Low/High panels only — does not touch analysis storage."""
    if view is None:
        view = _audio_band_view_from_ui()
    if view is None:
        return
    try:
        hist_w = int(view.par.w.eval())
        hist_h = int(view.par.h.eval())
    except Exception:
        return
    width = max(AUDIO_MIN_BAND_WIDTH, _norm(width))
    pos = _norm(pos)
    lo = _norm(pos - width * 0.5)
    hi = _norm(pos + width * 0.5)
    x = int(lo * hist_w)
    bw = max(28, int((hi - lo) * hist_w))
    thr = _audio_threshold_for_band(band)
    tag_h = max(16, min(22, int(hist_h * 0.10)))
    shade_h = max(tag_h + 4, int(round(thr * hist_h)))
    shade_h = min(hist_h, shade_h)
    tag_y = max(0, shade_h - tag_h)
    if band == 'high':
        names = (
            'band_tag_high', 'band_shade_high', 'band_hit_high', 'band_thresh_hit_high',
            'band_handle_high_lo', 'band_handle_high_hi',
        )
    else:
        names = (
            'band_tag_bass', 'band_shade_bass', 'band_hit_bass', 'band_thresh_hit_bass',
            'band_handle_bass_lo', 'band_handle_bass_hi',
        )
    tag, shade, hit, thresh_hit, lo_h, hi_h = (view.op(n) for n in names)
    try:
        if shade is not None:
            shade.par.x = x
            shade.par.w = bw
            shade.par.h = shade_h
            shade.par.y = 0
        if tag is not None:
            tag.par.x = x
            tag.par.w = bw
            tag.par.y = tag_y
            tag.par.h = tag_h
        if hit is not None:
            hit.par.x = x
            hit.par.w = bw
            hit.par.y = 0
            hit.par.h = max(8, shade_h - tag_h)
        if thresh_hit is not None:
            # Label-sized until drag expands it (see _expand_band_thresh_capture).
            thresh_hit.par.x = x
            thresh_hit.par.w = bw
            if not _AUDIO_HIST_DRAG.get('thresh_capture_expanded'):
                thresh_hit.par.y = tag_y
                thresh_hit.par.h = tag_h
        # H-caps: thin full-height grips outside the horizontal bar ends.
        _place_band_h_handles(lo_h, hi_h, x, bw, tag_y, tag_h, hist_w, hist_h)
    except Exception:
        pass


def _place_band_h_handles(lo_h, hi_h, bar_x, bar_w, tag_y, tag_h, hist_w, hist_h=None, rgb=None):
    """Thin frequency grips outside the Low/High bar ends (tall H legs)."""
    if hist_h is None:
        hist_h = max(tag_h, int(tag_y) + int(tag_h))
    lo_x = max(0, int(bar_x) - AUDIO_BAND_HANDLE_W)
    hi_x = min(max(0, int(hist_w) - AUDIO_BAND_HANDLE_W), int(bar_x) + int(bar_w))
    for handle, hx in ((lo_h, lo_x), (hi_h, hi_x)):
        if handle is None:
            continue
        try:
            handle.par.x = hx
            handle.par.y = 0
            handle.par.w = AUDIO_BAND_HANDLE_W
            handle.par.h = max(1, int(hist_h))
            handle.par.display = True
            handle.par.enable = True
            handle.par.clickthrough = False
            handle.par.cursor = 'pointer'
            handle.par.bgalpha = AUDIO_BAND_HANDLE_ALPHA
            if rgb is not None:
                handle.par.bgcolorr, handle.par.bgcolorg, handle.par.bgcolorb = rgb
            _clear_panel_borders(handle)
        except Exception:
            pass


def _audio_set_band_edges(band, lo, hi):
    lo = _norm(lo)
    hi = _norm(hi)
    if hi < lo:
        lo, hi = hi, lo
    width = max(AUDIO_MIN_BAND_WIDTH, hi - lo)
    if lo < 0.0:
        hi -= lo
        lo = 0.0
    if hi > 1.0:
        lo -= hi - 1.0
        hi = 1.0
    width = max(AUDIO_MIN_BAND_WIDTH, hi - lo)
    pos = lo + width * 0.5
    _audio_set_band_pos_width(band, pos, width)


def _audio_band_hit_tolerance(u_tol=None):
    return u_tol if u_tol is not None else AUDIO_BAND_HANDLE_U


def _audio_pick_hist_mode(u, v, hist_w=None):
    """Pick edge handles, band body, or nearest band. Threshold is vertical drag on body."""
    s = _settings()
    if s is None:
        return 'band_bass'
    u = _norm(u)
    tol = _audio_band_hit_tolerance()
    if hist_w is None:
        hist_w = _audio_band_strip_w()
    px_tol = max(AUDIO_BAND_HANDLE_W, tol * max(1, int(hist_w))) / max(1.0, float(hist_w))

    handle_hits = []
    shade_hits = []
    for name in ('bass', 'high'):
        lo, hi = _audio_band_norms(name)
        if abs(u - lo) <= px_tol:
            handle_hits.append((abs(u - lo), name + '_lo'))
        if abs(u - hi) <= px_tol:
            handle_hits.append((abs(u - hi), name + '_hi'))
        if lo <= u <= hi:
            shade_hits.append((abs(u - (lo + hi) * 0.5), 'band_' + name))

    if handle_hits:
        handle_hits.sort(key=lambda item: item[0])
        return handle_hits[0][1]
    if shade_hits:
        shade_hits.sort(key=lambda item: item[0])
        return shade_hits[0][1]
    lo_b, hi_b = _audio_band_norms('bass')
    lo_h, hi_h = _audio_band_norms('high')
    if abs(u - (lo_b + hi_b) * 0.5) <= abs(u - (lo_h + hi_h) * 0.5):
        return 'band_bass'
    return 'band_high'


def clear_audio_hist_drag():
    live_band = _AUDIO_HIST_DRAG.get('live_thresh_band')
    live_thr = _AUDIO_HIST_DRAG.get('live_thresh')
    move_band = _AUDIO_HIST_DRAG.get('live_band')
    move_pos = _AUDIO_HIST_DRAG.get('live_pos')
    move_width = _AUDIO_HIST_DRAG.get('live_width')
    _AUDIO_HIST_DRAG['mode'] = None
    _AUDIO_HIST_DRAG['last_uv'] = None
    _AUDIO_HIST_DRAG['last_px'] = None
    _AUDIO_HIST_DRAG['band_offset'] = 0.0
    _AUDIO_HIST_DRAG['start_uv'] = None
    _AUDIO_HIST_DRAG['axis'] = None
    _AUDIO_HIST_DRAG['writing_thresh'] = False
    _AUDIO_HIST_DRAG['last_thresh_px'] = None
    _AUDIO_HIST_DRAG['live_thresh'] = None
    _AUDIO_HIST_DRAG['live_thresh_band'] = None
    _AUDIO_HIST_DRAG['live_band'] = None
    _AUDIO_HIST_DRAG['live_pos'] = None
    _AUDIO_HIST_DRAG['live_width'] = None
    _AUDIO_HIST_DRAG.pop('peak_bar_op', None)
    _AUDIO_HIST_DRAG.pop('band_thresh_hit_op', None)
    _AUDIO_HIST_DRAG.pop('thresh_grab_v', None)
    _AUDIO_HIST_DRAG.pop('thresh_grab_thr', None)
    _AUDIO_HIST_DRAG.pop('thresh_vis_ops', None)
    _AUDIO_HIST_DRAG.pop('peak_vis_ops', None)
    # Single commit on mouse-up — analysis/CHOPs update once, not per mouse sample.
    if move_band in ('bass', 'high') and move_pos is not None and move_width is not None:
        _audio_set_band_pos_width(move_band, move_pos, move_width, commit=True)
    if live_band in ('bass', 'high', 'peak') and live_thr is not None:
        _audio_commit_threshold(live_band, live_thr, visual=True)
    _restore_band_thresh_hits()
    _mark_audio_hist_overlays_dirty()


def _band_thresh_label_geom(band_key, view=None, thr=None):
    """Pixel rect for the Low/High horizontal threshold bar (label)."""
    if view is None:
        view = _audio_band_view_from_ui()
    if view is None:
        return None
    try:
        hist_w = int(view.par.w.eval())
        hist_h = int(view.par.h.eval())
    except Exception:
        return None
    lo, hi = _audio_band_norms(band_key)
    x = int(lo * hist_w)
    bw = max(28, int((hi - lo) * hist_w))
    if thr is None:
        thr = _audio_threshold_for_band(band_key)
    thr = _norm(thr)
    tag_h = max(16, min(22, int(hist_h * 0.10)))
    shade_h = max(tag_h + 4, int(round(thr * hist_h)))
    shade_h = min(hist_h, shade_h)
    tag_y = max(0, shade_h - tag_h)
    return {
        'view': view,
        'hist_w': hist_w,
        'hist_h': hist_h,
        'x': x,
        'bw': bw,
        'tag_y': tag_y,
        'tag_h': tag_h,
        'shade_h': shade_h,
    }


def _expand_band_thresh_capture(band_key, view=None):
    """After grabbing the horizontal bar, expand hit to full height so drag tracks."""
    geom = _band_thresh_label_geom(band_key, view=view)
    if geom is None:
        return None
    view = geom['view']
    name = 'band_thresh_hit_bass' if band_key == 'bass' else 'band_thresh_hit_high'
    hit = view.op(name)
    if hit is None:
        return None
    try:
        hit.par.x = geom['x']
        hit.par.w = geom['bw']
        hit.par.y = 0
        hit.par.h = geom['hist_h']
        hit.par.display = True
        hit.par.enable = True
        hit.par.clickthrough = False
    except Exception:
        pass
    _AUDIO_HIST_DRAG['thresh_capture_expanded'] = True
    _AUDIO_HIST_DRAG['thresh_capture_band'] = band_key
    _AUDIO_HIST_DRAG['band_thresh_hit_op'] = hit
    return hit


def _begin_band_thresh_drag(band_key, grab_v=None, grab_u=None, view=None):
    """Start Low/High bar drag: up/down = threshold, left/right = band move."""
    view = view or _audio_band_view_from_ui()
    hit = _expand_band_thresh_capture(band_key, view=view)
    thr = _audio_threshold_for_band(band_key)
    if grab_v is None and view is not None:
        try:
            grab_v = max(0.0, min(1.0, float(view.panel.insidev)))
        except Exception:
            try:
                grab_v = max(0.0, min(1.0, float(view.panel.v)))
            except Exception:
                grab_v = thr
    if grab_v is None:
        grab_v = thr
    grab_v = _norm(grab_v)
    if grab_u is None and view is not None:
        try:
            grab_u = max(0.0, min(1.0, float(view.panel.insideu)))
        except Exception:
            try:
                grab_u = max(0.0, min(1.0, float(view.panel.u)))
            except Exception:
                grab_u = 0.5
    grab_u = _norm(grab_u if grab_u is not None else 0.5)
    lo, hi = _audio_band_norms(band_key)
    _AUDIO_HIST_DRAG['mode'] = 'thresh_bass' if band_key == 'bass' else 'thresh_high'
    # Axis locks on first meaningful move (u = band, v = threshold).
    _AUDIO_HIST_DRAG['axis'] = None
    _AUDIO_HIST_DRAG['thresh_grab_thr'] = thr
    _AUDIO_HIST_DRAG['thresh_grab_v'] = grab_v
    _AUDIO_HIST_DRAG['live_thresh'] = thr
    _AUDIO_HIST_DRAG['live_thresh_band'] = band_key
    _AUDIO_HIST_DRAG['band_offset'] = (lo + hi) * 0.5 - grab_u
    _AUDIO_HIST_DRAG['start_uv'] = (grab_u, grab_v)
    _AUDIO_HIST_DRAG['last_thresh_px'] = None
    _AUDIO_HIST_DRAG['last_px'] = None
    return hit, thr


def _restore_band_thresh_hits(view=None):
    """Shrink thresh hits back to the horizontal bar after drag ends."""
    _AUDIO_HIST_DRAG.pop('thresh_capture_expanded', None)
    _AUDIO_HIST_DRAG.pop('thresh_capture_band', None)
    if view is None:
        view = _audio_band_view_from_ui()
    if view is None:
        return
    for band_key, name in (
        ('bass', 'band_thresh_hit_bass'),
        ('high', 'band_thresh_hit_high'),
    ):
        geom = _band_thresh_label_geom(band_key, view=view)
        hit = view.op(name)
        if geom is None or hit is None:
            continue
        try:
            hit.par.x = geom['x']
            hit.par.w = geom['bw']
            hit.par.y = geom['tag_y']
            hit.par.h = geom['tag_h']
            hit.par.display = True
            hit.par.enable = True
            hit.par.clickthrough = False
        except Exception:
            pass


def set_audio_select_band(band):
    pass


def _audio_band_view_from_ui():
    try:
        r = _root()
        ui = r.op('ui') if r is not None else None
        strip = ui.op('audio_band_strip') if ui is not None else None
        return strip.op('audio_band_view') if strip is not None else None
    except Exception:
        return None


def _audio_threshold_for_band(band_key, s=None):
    """Current threshold, preferring in-drag live value (not yet committed)."""
    live_band = _AUDIO_HIST_DRAG.get('live_thresh_band')
    live_thr = _AUDIO_HIST_DRAG.get('live_thresh')
    if live_band == band_key and live_thr is not None:
        return _norm(live_thr)
    if s is None:
        s = _settings()
    par_name = {
        'bass': 'Audiothresholdlow',
        'high': 'Audiothresholdhigh',
        'peak': 'Audiothresholdpeak',
    }.get(band_key)
    if s is None or not par_name:
        return DEFAULT_THRESH_LOW if band_key == 'bass' else DEFAULT_THRESH_HIGH
    try:
        return _norm(float(getattr(s.par, par_name).eval()))
    except Exception:
        return DEFAULT_THRESH_LOW if band_key == 'bass' else DEFAULT_THRESH_HIGH


def _apply_band_threshold_visual(band_key, thr, view=None):
    """Cheap height-only update so vertical threshold drag stays smooth."""
    if band_key == 'peak':
        _apply_peak_thresh_visual(thr)
        return
    if view is None:
        view = _audio_band_view_from_ui()
    if view is None:
        return
    try:
        hist_h = int(view.par.h.eval())
    except Exception:
        return
    thr = _norm(thr)
    tag_h = max(16, min(22, int(hist_h * 0.10)))
    shade_h = max(tag_h + 4, int(round(thr * hist_h)))
    shade_h = min(hist_h, shade_h)
    tag_y = max(0, shade_h - tag_h)
    # During live vertical drag only move shade + label — resizing body/handles
    # every pixel is what tanks the cook rate vs sideways grip drags.
    light = (
        _AUDIO_HIST_DRAG.get('live_thresh_band') == band_key
        and _AUDIO_HIST_DRAG.get('live_thresh') is not None
    )
    cache = _AUDIO_HIST_DRAG.get('thresh_vis_ops')
    if light and isinstance(cache, dict) and cache.get('band') == band_key:
        shade = cache.get('shade')
        tag = cache.get('tag')
    else:
        if band_key == 'high':
            shade = view.op('band_shade_high')
            tag = view.op('band_tag_high')
            hit = view.op('band_hit_high')
            thresh_hit = view.op('band_thresh_hit_high')
            lo_h = view.op('band_handle_high_lo')
            hi_h = view.op('band_handle_high_hi')
        else:
            shade = view.op('band_shade_bass')
            tag = view.op('band_tag_bass')
            hit = view.op('band_hit_bass')
            thresh_hit = view.op('band_thresh_hit_bass')
            lo_h = view.op('band_handle_bass_lo')
            hi_h = view.op('band_handle_bass_hi')
        if light:
            _AUDIO_HIST_DRAG['thresh_vis_ops'] = {
                'band': band_key,
                'shade': shade,
                'tag': tag,
            }
    try:
        if shade is not None and int(shade.par.h.eval()) != shade_h:
            shade.par.h = shade_h
        if tag is not None and int(tag.par.y.eval()) != tag_y:
            tag.par.y = tag_y
        if light:
            return
        # Full sync (idle / mouse-up): body hit, label hit, side grips.
        expanded = (
            _AUDIO_HIST_DRAG.get('thresh_capture_expanded')
            and _AUDIO_HIST_DRAG.get('thresh_capture_band') == band_key
        )
        bar_x = int(tag.par.x.eval()) if tag is not None else 0
        bar_w = int(tag.par.w.eval()) if tag is not None else 28
        try:
            hist_w = int(view.par.w.eval())
        except Exception:
            hist_w = bar_x + bar_w
        if tag is not None and int(tag.par.h.eval()) != tag_h:
            tag.par.h = tag_h
        if thresh_hit is not None and not expanded:
            thresh_hit.par.y = tag_y
            thresh_hit.par.h = tag_h
        if hit is not None:
            body_h = max(8, shade_h - tag_h)
            if int(hit.par.h.eval()) != body_h:
                hit.par.h = body_h
        _place_band_h_handles(lo_h, hi_h, bar_x, bar_w, tag_y, tag_h, hist_w, hist_h)
    except Exception:
        pass


def _peak_thresh_bar_from_ui():
    try:
        r = _root()
        ui = r.op('ui') if r is not None else None
        strip = ui.op('audio_band_strip') if ui is not None else None
        return strip.op('peak_thresh_bar') if strip is not None else None
    except Exception:
        return None


def _apply_peak_thresh_visual(thr, bar=None):
    """Update Peak column to match Low/High: body shade + horizontal label bar."""
    if bar is None:
        bar = _peak_thresh_bar_from_ui()
    if bar is None:
        return
    thr = _norm(thr)
    try:
        hist_h = max(1, int(bar.par.h.eval()))
        bar_w = max(1, int(bar.par.w.eval()))
        bar_x = int(bar.par.x.eval())
        bar_y = int(bar.par.y.eval())
    except Exception:
        return
    tag_h = max(16, min(22, int(hist_h * 0.10)))
    shade_h = max(tag_h + 4, int(round(thr * hist_h)))
    shade_h = min(hist_h, shade_h)
    tag_y = max(0, shade_h - tag_h)
    tick_h = max(1, int(AUDIO_PEAK_TICK_H))
    tick_ext = max(2, int(AUDIO_PEAK_TICK_EXTEND))
    tick_in = max(2, int(AUDIO_PEAK_TICK_INSET))
    tick_y = tag_y + max(0, (tag_h - tick_h) // 2)
    light = (
        _AUDIO_HIST_DRAG.get('live_thresh_band') == 'peak'
        and _AUDIO_HIST_DRAG.get('live_thresh') is not None
    )
    cache = _AUDIO_HIST_DRAG.get('peak_vis_ops')
    if light and isinstance(cache, dict):
        fill = cache.get('fill')
        tag = cache.get('tag')
        tick = cache.get('tick')
    else:
        fill = bar.op('fill')
        tag = bar.op('tag')
        strip = None
        try:
            strip = bar.parent()
        except Exception:
            strip = None
        tick = strip.op('peak_tick') if strip is not None else None
        if light:
            _AUDIO_HIST_DRAG['peak_vis_ops'] = {
                'fill': fill, 'tag': tag, 'tick': tick,
            }
    try:
        if fill is not None and int(fill.par.h.eval()) != shade_h:
            fill.par.h = shade_h
        if tag is not None and int(tag.par.y.eval()) != tag_y:
            tag.par.y = tag_y
        if tick is not None:
            want_y = bar_y + tick_y
            if int(tick.par.y.eval()) != want_y:
                tick.par.y = want_y
        if light:
            return
        # Full sync outside drag.
        thumb = bar.op('thumb')
        for stale_name in ('arrow', 'mark', 'tick'):
            stale = bar.op(stale_name)
            if stale is not None:
                try:
                    stale.par.display = False
                except Exception:
                    pass
        if fill is not None:
            fill.par.y = 0
        if tick is not None:
            want_x = bar_x - tick_ext
            want_w = tick_ext + tick_in
            if int(tick.par.x.eval()) != want_x:
                tick.par.x = want_x
            if int(tick.par.w.eval()) != want_w:
                tick.par.w = want_w
            if int(tick.par.h.eval()) != tick_h:
                tick.par.h = tick_h
            tick.par.bgcolorr, tick.par.bgcolorg, tick.par.bgcolorb = AUDIO_BAND_HIGH
            tick.par.bgalpha = AUDIO_BAND_TAG_ALPHA
            tick.par.display = True
            _clear_panel_borders(tick)
        if tag is not None:
            if int(tag.par.x.eval()) != 0:
                tag.par.x = 0
            if int(tag.par.h.eval()) != tag_h:
                tag.par.h = tag_h
            if int(tag.par.w.eval()) != bar_w:
                tag.par.w = bar_w
            tag.par.bgcolorr, tag.par.bgcolorg, tag.par.bgcolorb = AUDIO_BAND_HIGH
            tag.par.bgalpha = AUDIO_BAND_TAG_ALPHA
            _clear_panel_borders(tag)
            txt = tag.op('txt')
            if txt is not None:
                try:
                    if int(txt.par.resolutionw.eval()) != bar_w:
                        txt.par.resolutionw = bar_w
                    if int(txt.par.resolutionh.eval()) != tag_h:
                        txt.par.resolutionh = tag_h
                    txt.par.bgalpha = 0.0
                except Exception:
                    pass
        if thumb is not None and bool(thumb.par.display.eval()):
            thumb.par.display = False
    except Exception:
        pass


def _audio_threshold_drag_active():
    """True while Low/High threshold is being dragged on the histogram."""
    if _AUDIO_HIST_DRAG.get('live_thresh') is not None:
        return True
    if _AUDIO_HIST_DRAG.get('axis') == 'v':
        return True
    mode = str(_AUDIO_HIST_DRAG.get('mode') or '')
    return mode.startswith('thresh_')


def _audio_hist_drag_active():
    """True from mouse-down until clear — blocks overlay rebuild mid-gesture."""
    if _audio_threshold_drag_active():
        return True
    if _AUDIO_HIST_DRAG.get('live_band') is not None:
        return True
    mode = str(_AUDIO_HIST_DRAG.get('mode') or '')
    if mode.startswith('band_') or mode.endswith('_lo') or mode.endswith('_hi'):
        return True
    if _AUDIO_HIST_DRAG.get('start_uv') is not None:
        return True
    return False


def _audio_quantize_threshold(value, hist_h=None):
    thr = _norm(value)
    if hist_h is None:
        view = _audio_band_view_from_ui()
        try:
            hist_h = max(1, int(view.par.h.eval())) if view is not None else 0
        except Exception:
            hist_h = 0
    if hist_h > 0:
        thr = round(thr * hist_h) / float(hist_h)
    return _norm(thr)


def _audio_commit_threshold(band_key, value, visual=True):
    """Write threshold par + optional visual (used once/frame or on release)."""
    s = _settings()
    if s is None:
        return
    par_name = {
        'bass': 'Audiothresholdlow',
        'high': 'Audiothresholdhigh',
        'peak': 'Audiothresholdpeak',
    }.get(band_key)
    if not par_name:
        return
    thr = _audio_quantize_threshold(value)
    try:
        par = getattr(s.par, par_name)
        if abs(float(par.eval()) - thr) < 1e-6:
            if visual and band_key in ('bass', 'high', 'peak'):
                _apply_band_threshold_visual(band_key, thr)
            return
        _AUDIO_HIST_DRAG['writing_thresh'] = True
        try:
            par.val = thr
        finally:
            _AUDIO_HIST_DRAG['writing_thresh'] = False
    except Exception:
        pass
    if visual and band_key in ('bass', 'high', 'peak'):
        _apply_band_threshold_visual(band_key, thr)


def _audio_set_threshold_par(band_key, value, commit=True):
    """Stash + paint during drag. Analysis pars commit only on mouse-up."""
    axis = _AUDIO_HIST_DRAG.get('axis')
    mode = str(_AUDIO_HIST_DRAG.get('mode') or '')
    defer = (
        (not commit)
        or axis == 'v'
        or mode.startswith('thresh_')
        or _AUDIO_HIST_DRAG.get('live_thresh') is not None
    )
    # Resolve height once; peak uses its own column (not the spectrogram view).
    hist_h = 200
    view = None
    bar = None
    if band_key == 'peak':
        bar = _peak_thresh_bar_from_ui()
        try:
            hist_h = max(1, int(bar.par.h.eval())) if bar is not None else 200
        except Exception:
            hist_h = 200
    else:
        view = _audio_band_view_from_ui()
        try:
            hist_h = max(1, int(view.par.h.eval())) if view is not None else 200
        except Exception:
            hist_h = 200
    thr = _audio_quantize_threshold(value, hist_h=hist_h)
    if defer:
        prev_px = _AUDIO_HIST_DRAG.get('last_thresh_px')
        px = int(round(thr * hist_h))
        _AUDIO_HIST_DRAG['live_thresh'] = thr
        _AUDIO_HIST_DRAG['live_thresh_band'] = band_key
        if prev_px == px:
            return
        _AUDIO_HIST_DRAG['last_thresh_px'] = px
        if band_key == 'peak':
            _apply_peak_thresh_visual(thr, bar=bar)
        else:
            _apply_band_threshold_visual(band_key, thr, view=view)
        return
    _audio_commit_threshold(band_key, thr, visual=True)


def handle_audio_hist_interact(u, v=None, pick_edge=False, hist_w=None):
    # Fast path: Peak / Low/High bar — visual only until mouse-up.
    preset = _AUDIO_HIST_DRAG.get('mode')
    if (
        not pick_edge
        and isinstance(preset, str)
        and preset.startswith('thresh_')
    ):
        u = _norm(u) if u is not None else 0.5
        v = _norm(v) if v is not None else 0.5
        band = preset.split('_', 1)[1]
        bar = None
        view = None
        try:
            if band == 'peak':
                bar = _AUDIO_HIST_DRAG.get('peak_bar_op')
                if bar is None:
                    bar = _peak_thresh_bar_from_ui()
                    _AUDIO_HIST_DRAG['peak_bar_op'] = bar
                vh = max(1, int(bar.par.h.eval())) if bar is not None else 200
                vw = 1
            else:
                view = _audio_band_view_from_ui()
                vh = max(1, int(view.par.h.eval()) if view else 200)
                vw = max(1, int(view.par.w.eval()) if view else 400)
                hit = _AUDIO_HIST_DRAG.get('band_thresh_hit_op')
                if hit is None and view is not None:
                    name = 'band_thresh_hit_bass' if band == 'bass' else 'band_thresh_hit_high'
                    hit = view.op(name)
                    _AUDIO_HIST_DRAG['band_thresh_hit_op'] = hit
        except Exception:
            vh, vw = 200, 400

        # Peak: absolute vertical only.
        if band == 'peak':
            thr = v
            px_v = int(round(thr * vh))
            if _AUDIO_HIST_DRAG.get('last_thresh_px') == px_v:
                return
            thr = px_v / float(vh)
            _AUDIO_HIST_DRAG['last_px'] = ('v', px_v)
            _AUDIO_HIST_DRAG['last_thresh_px'] = px_v
            _AUDIO_HIST_DRAG['live_thresh'] = thr
            _AUDIO_HIST_DRAG['live_thresh_band'] = band
            _apply_peak_thresh_visual(thr, bar=bar)
            return

        # Low/High bar: lock axis from first meaningful move.
        axis = _AUDIO_HIST_DRAG.get('axis')
        if axis is None:
            start = _AUDIO_HIST_DRAG.get('start_uv') or (u, v)
            try:
                su, sv = float(start[0]), float(start[1])
            except Exception:
                su, sv = u, v
            du = abs(u - su) * float(vw)
            dv = abs(v - sv) * float(vh)
            dead = 3.0
            if du < dead and dv < dead:
                return
            axis = 'u' if du >= dv else 'v'
            _AUDIO_HIST_DRAG['axis'] = axis

        if axis == 'u':
            lo, hi = _audio_band_edges(
                band, '',
                DEFAULT_BASS_POS if band == 'bass' else DEFAULT_HIGH_POS,
                DEFAULT_BASS_WIDTH if band == 'bass' else DEFAULT_HIGH_WIDTH,
            )
            width = max(AUDIO_MIN_BAND_WIDTH, hi - lo)
            target_pos = u + float(_AUDIO_HIST_DRAG.get('band_offset', 0.0) or 0.0)
            px_u = int(round(target_pos * vw))
            if _AUDIO_HIST_DRAG.get('last_px') == ('u', px_u):
                return
            _AUDIO_HIST_DRAG['last_px'] = ('u', px_u)
            _audio_set_band_pos_width(band, target_pos, width, commit=False)
            return

        # axis == 'v': grab-offset threshold (click does not jump).
        grab_thr = _AUDIO_HIST_DRAG.get('thresh_grab_thr')
        grab_v = _AUDIO_HIST_DRAG.get('thresh_grab_v')
        if grab_thr is not None and grab_v is not None:
            thr = _norm(float(grab_thr) + (v - float(grab_v)))
        else:
            thr = v
        px_v = int(round(thr * vh))
        if _AUDIO_HIST_DRAG.get('last_thresh_px') == px_v:
            return
        thr = px_v / float(vh)
        _AUDIO_HIST_DRAG['last_px'] = ('v', px_v)
        _AUDIO_HIST_DRAG['last_thresh_px'] = px_v
        _AUDIO_HIST_DRAG['live_thresh'] = thr
        _AUDIO_HIST_DRAG['live_thresh_band'] = band
        if view is None:
            view = _audio_band_view_from_ui()
        _apply_band_threshold_visual(band, thr, view=view)
        return

    s = _settings()
    if s is None:
        return
    u = _norm(u)
    v = _norm(v) if v is not None else 0.5
    view = _audio_band_view_from_ui()
    try:
        vw = max(1, int((hist_w if hist_w else None) or (view.par.w.eval() if view else 400)))
        vh = max(1, int(view.par.h.eval() if view else 200))
    except Exception:
        vw, vh = 400, 200
    # Ignore sub-pixel mouse chatter — one event per panel pixel max.
    axis = _AUDIO_HIST_DRAG.get('axis')
    mode_pre = str(_AUDIO_HIST_DRAG.get('mode') or '')
    px_u = int(u * vw)
    px_v = int(v * vh)
    if axis == 'v' or (mode_pre.startswith('thresh_') and axis != 'u'):
        px_key = ('v', px_v)
    elif axis == 'u':
        px_key = ('u', px_u)
    else:
        px_key = (px_u, px_v)
    if not pick_edge and _AUDIO_HIST_DRAG.get('last_px') == px_key:
        return
    _AUDIO_HIST_DRAG['last_px'] = px_key
    _AUDIO_HIST_DRAG['last_uv'] = (round(u, 5), round(v, 5))
    if pick_edge:
        preset = _AUDIO_HIST_DRAG.get('mode')
        keep_preset = isinstance(preset, str) and (
            preset.startswith('band_')
            or preset.endswith('_lo')
            or preset.endswith('_hi')
            or preset.startswith('thresh_')
        )
        if not keep_preset:
            _AUDIO_HIST_DRAG['mode'] = _audio_pick_hist_mode(u, v, hist_w=hist_w)
        _AUDIO_HIST_DRAG['start_uv'] = (u, v)
        _AUDIO_HIST_DRAG['axis'] = None
        picked = _AUDIO_HIST_DRAG.get('mode', '')
        if picked.startswith('band_'):
            picked_band = picked.split('_', 1)[1]
            picked_lo, picked_hi = _audio_band_norms(picked_band)
            _AUDIO_HIST_DRAG['band_offset'] = (picked_lo + picked_hi) * 0.5 - u
        else:
            _AUDIO_HIST_DRAG['band_offset'] = 0.0
    mode = _AUDIO_HIST_DRAG.get('mode') or _audio_pick_hist_mode(u, v, hist_w=hist_w)

    # Low/High body: sideways band move only. Threshold is the label (tag).
    if mode.startswith('band_'):
        band = mode.split('_', 1)[1]
        lo, hi = _audio_band_edges(
            band, '',
            DEFAULT_BASS_POS if band == 'bass' else DEFAULT_HIGH_POS,
            DEFAULT_BASS_WIDTH if band == 'bass' else DEFAULT_HIGH_WIDTH,
        )
        width = max(AUDIO_MIN_BAND_WIDTH, hi - lo)
        target_pos = u + float(_AUDIO_HIST_DRAG.get('band_offset', 0.0) or 0.0)
        _AUDIO_HIST_DRAG['axis'] = 'u'
        _audio_set_band_pos_width(band, target_pos, width, commit=False)
        return

    if mode.startswith('thresh_'):
        _audio_set_threshold_par(mode.split('_', 1)[1], v, commit=False)
        return

    band = 'bass'
    edge = None
    if mode.endswith('_lo'):
        band = mode.split('_', 1)[0]
        edge = 'lo'
    elif mode.endswith('_hi'):
        band = mode.split('_', 1)[0]
        edge = 'hi'

    lo, hi = _audio_band_edges(
        band, '',
        DEFAULT_BASS_POS if band == 'bass' else DEFAULT_HIGH_POS,
        DEFAULT_BASS_WIDTH if band == 'bass' else DEFAULT_HIGH_WIDTH,
    )

    if edge == 'lo':
        lo = min(u, hi - AUDIO_MIN_BAND_WIDTH)
        width = max(AUDIO_MIN_BAND_WIDTH, hi - lo)
        pos = lo + width * 0.5
        _audio_set_band_pos_width(band, pos, width, commit=False)
        return
    if edge == 'hi':
        hi = max(u, lo + AUDIO_MIN_BAND_WIDTH)
        width = max(AUDIO_MIN_BAND_WIDTH, hi - lo)
        pos = lo + width * 0.5
        _audio_set_band_pos_width(band, pos, width, commit=False)
        return


def _clear_panel_borders(comp):
    """Remove containerCOMP edge outlines (TD default border A/B)."""
    if comp is None:
        return
    try:
        for pname in ('leftborder', 'rightborder', 'topborder', 'bottomborder'):
            getattr(comp.par, pname).val = 'off'
    except Exception:
        pass
    try:
        comp.par.borderaalpha = 0.0
        comp.par.borderbalpha = 0.0
    except Exception:
        pass
    try:
        # Avoid residual border-over highlight edges.
        comp.par.borderover = False
    except Exception:
        pass
    try:
        comp.par.borderar = comp.par.borderag = comp.par.borderab = 0.0
        comp.par.borderbr = comp.par.borderbg = comp.par.borderbb = 0.0
    except Exception:
        pass


def _ensure_band_tag(parent, name, label, rgb, active=False):
    """Bright header strip with Low/High label."""
    comp = parent.op(name) if parent is not None else None
    created = False
    if comp is None and parent is not None:
        comp = parent.create('containerCOMP', name)
        comp.create('textTOP', 'txt')
        created = True
    if comp is None:
        return None
    try:
        if created:
            comp.par.h = AUDIO_BAND_TAG_H
        comp.par.hmode = 'fixed'
        comp.par.vmode = 'fixed'
        comp.par.align = 'none'
        comp.par.display = True
        comp.par.enable = True
        comp.par.clickthrough = False
        comp.par.drop = 'dropno'
        try:
            comp.par.drag = 'usecallbacks'
        except Exception:
            pass
        comp.par.cursor = 'pointer'
        comp.par.bgcolorr, comp.par.bgcolorg, comp.par.bgcolorb = rgb
        comp.par.bgalpha = AUDIO_BAND_TAG_ALPHA
        _clear_panel_borders(comp)
    except Exception:
        pass
    txt = comp.op('txt')
    if txt is not None:
        try:
            try:
                tag_w = max(36, int(comp.par.w.eval()))
            except Exception:
                tag_w = 36
            try:
                tag_h = max(14, int(comp.par.h.eval()))
            except Exception:
                tag_h = AUDIO_BAND_TAG_H
            txt.par.text = label
            # Match panel pixels 1:1 — mismatched res + fit/fill stretches glyphs.
            txt.par.resolutionw = tag_w
            txt.par.resolutionh = tag_h
            txt.par.font = TD_FONT
            txt.par.fontsizex = TD_FONT_SIZE
            txt.par.fontsizey = TD_FONT_SIZE
            txt.par.bgalpha = 0.0
            txt.par.alignx = 'center'
            txt.par.aligny = 'center'
            txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = AUDIO_BAND_TAG_TEXT
            comp.par.top = txt
            comp.par.topfill = 'native'
        except Exception:
            pass
    return comp


def _ensure_band_shade(parent, name, rgb):
    """Darker body fill under the Low/High header."""
    comp = parent.op(name) if parent is not None else None
    if comp is None and parent is not None:
        comp = parent.create('containerCOMP', name)
    if comp is None:
        return None
    try:
        comp.par.align = 'none'
        comp.par.display = True
        comp.par.enable = True
        comp.par.clickthrough = False
        comp.par.drop = 'dropno'
        try:
            comp.par.drag = 'usecallbacks'
        except Exception:
            pass
        comp.par.cursor = 'pointer'
        comp.par.bgcolorr, comp.par.bgcolorg, comp.par.bgcolorb = rgb
        comp.par.bgalpha = AUDIO_BAND_BODY_ALPHA
    except Exception:
        pass
    return comp


def _ensure_band_handle(parent, name, rgb):
    """Visible edge grips for resizing Low/High band width."""
    comp = parent.op(name) if parent is not None else None
    if comp is None and parent is not None:
        comp = parent.create('containerCOMP', name)
    if comp is None:
        return None
    try:
        comp.par.w = AUDIO_BAND_HANDLE_W
        comp.par.hmode = 'fixed'
        comp.par.wmode = 'fixed'
        comp.par.vmode = 'fixed'
        comp.par.align = 'none'
        comp.par.display = True
        comp.par.enable = True
        comp.par.clickthrough = False
        comp.par.drop = 'dropno'
        comp.par.drag = 'dragno'
        comp.par.cursor = 'pointer'
        comp.par.bgcolorr, comp.par.bgcolorg, comp.par.bgcolorb = rgb
        comp.par.bgalpha = 0.35
    except Exception:
        pass
    grip = comp.op('grip')
    if grip is not None:
        try:
            grip.par.display = False
            grip.par.clickthrough = True
            grip.par.bgalpha = 0.0
        except Exception:
            pass
    return comp


def _ensure_thresh_slider(parent, name, rgb):
    """Full-width horizontal threshold bar."""
    comp = parent.op(name) if parent is not None else None
    if comp is None and parent is not None:
        comp = parent.create('containerCOMP', name)
    if comp is None:
        return None
    try:
        comp.par.h = AUDIO_THRESH_THUMB_H
        comp.par.hmode = 'fixed'
        comp.par.wmode = 'fixed'
        comp.par.vmode = 'fixed'
        comp.par.align = 'none'
        comp.par.display = True
        comp.par.enable = True
        comp.par.clickthrough = True
        comp.par.drop = 'dropno'
        comp.par.drag = 'dragno'
        comp.par.cursor = 'ns-resize'
        comp.par.bgcolorr, comp.par.bgcolorg, comp.par.bgcolorb = rgb
        # The container itself is the visible line. This is more reliable than
        # a thin anchored child track, which can disappear behind panel TOPs.
        comp.par.bgalpha = 0.92
    except Exception:
        pass
    track = comp.op('track')
    if track is None:
        track = comp.create('containerCOMP', 'track')
    try:
        track.par.w = 100
        track.par.wmode = 'fixed'
        track.par.hmode = 'fixed'
        track.par.vmode = 'fixed'
        track.par.align = 'none'
        track.par.x = 0
        track.par.y = 0
        track.par.h = AUDIO_THRESH_THUMB_H
        track.par.leftanchor = 0
        track.par.rightanchor = 1
        track.par.leftoffset = 0
        track.par.rightoffset = 0
        track.par.display = True
        track.par.enable = True
        track.par.clickthrough = True
        track.par.bgcolorr, track.par.bgcolorg, track.par.bgcolorb = rgb
        track.par.bgalpha = 1.0
    except Exception:
        pass
    thumb = comp.op('thumb')
    if thumb is None:
        thumb = comp.create('containerCOMP', 'thumb')
    try:
        thumb.par.h = AUDIO_THRESH_THUMB_H
        thumb.par.hmode = 'fixed'
        thumb.par.wmode = 'fixed'
        thumb.par.vmode = 'fixed'
        thumb.par.align = 'none'
        thumb.par.w = 18
        thumb.par.x = 0
        thumb.par.y = 0
        thumb.par.display = False
        thumb.par.enable = True
        thumb.par.clickthrough = True
        thumb.par.bgcolorr, thumb.par.bgcolorg, thumb.par.bgcolorb = (1.0, 1.0, 1.0)
        thumb.par.bgalpha = 0.0
    except Exception:
        pass
    return comp


def _destroy_audio_overlay_stale(view):
    if view is None:
        return
    for stale in (
        'band_pick_bass', 'band_pick_high',
        'thresh_hit_bass', 'thresh_hit_high',
        'thresh_slider_bass', 'thresh_slider_high', 'thresh_slider_peak',
    ):
        comp = view.op(stale)
        if comp is not None:
            try:
                comp.destroy()
            except Exception:
                pass


def _ensure_band_hit(parent, name):
    """Hit target for Low/High (body sideways, or full-height thresh like Peak)."""
    comp = parent.op(name) if parent is not None else None
    if comp is None and parent is not None:
        comp = parent.create('containerCOMP', name)
    if comp is None:
        return None
    try:
        comp.par.hmode = 'fixed'
        comp.par.vmode = 'fixed'
        comp.par.align = 'none'
        comp.par.display = True
        comp.par.enable = True
        comp.par.clickthrough = False
        comp.par.cursor = 'pointer'
        comp.par.drag = 'dragno'
        comp.par.drop = 'dropno'
        comp.par.bgalpha = 0.0
        comp.par.layoutorder = 20
    except Exception:
        pass
    return comp


def _layout_audio_hist_overlays(view):
    if view is None:
        return
    s = _settings()
    if s is None:
        return
    try:
        hist_w = int(view.par.w.eval())
        hist_h = int(view.par.h.eval())
    except Exception:
        hist_w, hist_h = _audio_hist_w(), AUDIO_SPECT_H
    selector_h = max(16, min(22, int(hist_h * 0.10)))
    specs = (
        (
            'band_tag_bass', 'band_shade_bass', 'band_hit_bass', 'band_thresh_hit_bass',
            'band_handle_bass_lo', 'band_handle_bass_hi',
            'Low', 'bass', AUDIO_BAND_LOW, AUDIO_BAND_LOW_BODY,
        ),
        (
            'band_tag_high', 'band_shade_high', 'band_hit_high', 'band_thresh_hit_high',
            'band_handle_high_lo', 'band_handle_high_hi',
            'High', 'high', AUDIO_BAND_HIGH, AUDIO_BAND_HIGH_BODY,
        ),
    )
    for (
        tag_name, shade_name, hit_name, thresh_hit_name, lo_name, hi_name,
        label, band_key, header_rgb, body_rgb,
    ) in specs:
        lo, hi = _audio_band_norms(band_key)
        x = int(lo * hist_w)
        bw = max(28, int((hi - lo) * hist_w))
        thr = _audio_threshold_for_band(band_key, s=s)
        # Bar height = threshold. Drag the column up/down to set it.
        tag_h = selector_h
        shade_h = max(tag_h + 4, int(round(thr * hist_h)))
        shade_h = min(hist_h, shade_h)
        tag_y = max(0, shade_h - tag_h)

        tag = view.op(tag_name) or _ensure_band_tag(
            view, tag_name, label, header_rgb, active=False,
        )
        if tag is not None:
            try:
                tag.par.x = x
                tag.par.y = tag_y
                tag.par.w = bw
                tag.par.h = tag_h
                # Visual label — threshold mouse goes to stationary thresh hit.
                tag.par.clickthrough = True
                tag.par.enable = True
                tag.par.drag = 'dragno'
                tag.par.drop = 'dropno'
                tag.par.cursor = 'pointer'
                tag.par.bgcolorr, tag.par.bgcolorg, tag.par.bgcolorb = header_rgb
                tag.par.bgalpha = AUDIO_BAND_TAG_ALPHA
                _clear_panel_borders(tag)
                try:
                    tag.par.layoutorder = 22
                except Exception:
                    pass
                txt = tag.op('txt')
                if txt is not None:
                    txt.par.resolutionw = bw
                    txt.par.resolutionh = tag_h
                    if str(txt.par.text.eval()) != label:
                        txt.par.text = label
                    tag.par.top = txt
                    tag.par.topfill = 'native'
            except Exception:
                pass

        shade = view.op(shade_name) or _ensure_band_shade(view, shade_name, body_rgb)
        if shade is not None:
            try:
                shade.par.x = x
                shade.par.y = 0
                shade.par.w = bw
                shade.par.h = shade_h
                shade.par.display = True
                shade.par.cursor = 'pointer'
                shade.par.clickthrough = True
                shade.par.enable = True
                shade.par.drag = 'dragno'
                shade.par.drop = 'dropno'
                shade.par.bgcolorr, shade.par.bgcolorg, shade.par.bgcolorb = body_rgb
                shade.par.bgalpha = AUDIO_BAND_BODY_ALPHA
                try:
                    shade.par.layoutorder = 5
                except Exception:
                    pass
            except Exception:
                pass

        # Horizontal-bar hit only. Expands to full height while dragging
        # (_expand_band_thresh_capture) so vertical tracking stays Peak-smooth.
        thresh_hit = view.op(thresh_hit_name) or _ensure_band_hit(view, thresh_hit_name)
        if thresh_hit is not None:
            try:
                thresh_hit.par.x = x
                thresh_hit.par.w = bw
                expanded = (
                    _AUDIO_HIST_DRAG.get('thresh_capture_expanded')
                    and _AUDIO_HIST_DRAG.get('thresh_capture_band') == band_key
                )
                if expanded:
                    thresh_hit.par.y = 0
                    thresh_hit.par.h = hist_h
                else:
                    thresh_hit.par.y = tag_y
                    thresh_hit.par.h = tag_h
                thresh_hit.par.display = True
                thresh_hit.par.enable = True
                thresh_hit.par.clickthrough = False
                thresh_hit.par.cursor = 'pointer'
                thresh_hit.par.bgalpha = 0.0
                try:
                    thresh_hit.par.layoutorder = 24
                except Exception:
                    pass
            except Exception:
                pass

        hit = view.op(hit_name) or _ensure_band_hit(view, hit_name)
        if hit is not None:
            try:
                # Body below the horizontal bar — sideways move only.
                hit.par.x = x
                hit.par.y = 0
                hit.par.w = bw
                hit.par.h = max(8, shade_h - tag_h)
                hit.par.display = True
                hit.par.enable = True
                hit.par.clickthrough = False
                hit.par.cursor = 'pointer'
                hit.par.bgalpha = 0.0
                try:
                    hit.par.layoutorder = 20
                except Exception:
                    pass
            except Exception:
                pass

        lo_handle = view.op(lo_name) or _ensure_band_handle(view, lo_name, header_rgb)
        hi_handle = view.op(hi_name) or _ensure_band_handle(view, hi_name, header_rgb)
        # Thin full-height grips outside the horizontal bar ends → H shape.
        _place_band_h_handles(
            lo_handle, hi_handle, x, bw, tag_y, tag_h, hist_w, hist_h, rgb=header_rgb,
        )
        for handle in (lo_handle, hi_handle):
            if handle is None:
                continue
            try:
                handle.par.layoutorder = 26
            except Exception:
                pass


def _ensure_audio_hist_overlays(view):
    if view is None:
        return
    _ensure_audio_hint(view)
    _destroy_audio_overlay_stale(view)
    _ensure_band_tag(view, 'band_tag_bass', 'Low', AUDIO_BAND_LOW)
    _ensure_band_tag(view, 'band_tag_high', 'High', AUDIO_BAND_HIGH)
    _ensure_band_shade(view, 'band_shade_bass', AUDIO_BAND_LOW_BODY)
    _ensure_band_shade(view, 'band_shade_high', AUDIO_BAND_HIGH_BODY)
    _ensure_band_hit(view, 'band_hit_bass')
    _ensure_band_hit(view, 'band_hit_high')
    _ensure_band_hit(view, 'band_thresh_hit_bass')
    _ensure_band_hit(view, 'band_thresh_hit_high')
    _ensure_band_handle(view, 'band_handle_bass_lo', AUDIO_BAND_LOW)
    _ensure_band_handle(view, 'band_handle_bass_hi', AUDIO_BAND_LOW)
    _ensure_band_handle(view, 'band_handle_high_lo', AUDIO_BAND_HIGH)
    _ensure_band_handle(view, 'band_handle_high_hi', AUDIO_BAND_HIGH)
    _layout_audio_hist_overlays(view)


def _audio_hint_text():
    return ''


def _ensure_audio_hint(parent):
    """Remove legacy Bass/High Hz readout above the spectrum."""
    if parent is None:
        return None
    for name in ('audio_hint',):
        comp = parent.op(name)
        if comp is None:
            continue
        try:
            comp.destroy()
        except Exception:
            try:
                comp.par.display = False
                comp.par.enable = False
                comp.par.h = 0
                comp.par.top = ''
            except Exception:
                pass
    return None


def _destroy_audio_hints():
    """Strip leftover frequency hint labels from spectrum views."""
    paths = (
        'ui/audio_band_strip/audio_band_view',
        'ui/audio_band_strip',
        'ui/audio_panel/audio_spectrogram',
        'ui/audio_panel',
        AUDIO_MONITOR_NAME + '/audio_band_view',
        AUDIO_MONITOR_NAME,
    )
    r = _root()
    if r is None:
        return
    for rel in paths:
        try:
            parent = r.op(rel)
        except Exception:
            parent = None
        if parent is not None:
            _ensure_audio_hint(parent)


def _ensure_audio_readout(parent, name, label):
    comp = parent.op(name) if parent is not None else None
    if comp is None and parent is not None:
        comp = parent.create('containerCOMP', name)
    if comp is None:
        return None
    try:
        comp.par.w = AUDIO_READOUT_W
        comp.par.h = 22
        comp.par.hmode = 'fixed'
        comp.par.vmode = 'fixed'
        comp.par.align = 'none'
        comp.par.display = True
        comp.par.clickthrough = True
        comp.par.bgalpha = 0.0
    except Exception:
        pass
    txt = comp.op('txt')
    if txt is None:
        txt = comp.create('textTOP', 'txt')
    try:
        txt.par.text = label
        txt.par.resolutionw = AUDIO_READOUT_W
        txt.par.resolutionh = 22
        txt.par.font = TD_FONT
        txt.par.fontsizex = TD_FONT_SIZE
        txt.par.fontsizey = TD_FONT_SIZE
        txt.par.bgalpha = 0.0
        txt.par.alignx = 'left'
        txt.par.aligny = 'center'
        txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = TD_TEXT_LABEL
        comp.par.top = txt
        comp.par.topfill = 'fit'
    except Exception:
        pass
    return comp


def _set_audio_readout(comp, text):
    if comp is None:
        return
    txt = comp.op('txt')
    if txt is None:
        return
    try:
        txt.par.text = str(text)
        comp.par.top = txt
    except Exception:
        pass


def _sync_spectrogram_display(view, force=False):
    """Show live spectrum histogram (TOP bars) behind the draggable band overlays."""
    global _AUDIO_HIST_SIZE, _AUDIO_HIST_TICK, _AUDIO_HIST_PIPELINE, _AUDIO_HIST_VIEW_BIND
    if view is None:
        return
    eng = _audio_engine()
    if eng is None:
        return
    spect = eng.op('audiospect1')
    if spect is None:
        return
    show_hist = _audio_histogram_visible()
    cooking = _audio_spectrum_is_live() and (not _audio_hist_frozen())
    stride = max(1, int(AUDIO_HIST_VIS_FRAME_STRIDE))
    # force = pipeline heal / resize; frame stride = regular GPU refresh rate.
    stride_hit = (_AUDIO_HIST_TICK % stride) == 0
    vis_refresh = bool(cooking and (force or stride_hit))
    try:
        view_w = max(1, int(view.par.w.eval()))
    except Exception:
        view_w = _audio_band_strip_w()
    try:
        view_h = max(1, int(view.par.h.eval()))
    except Exception:
        view_h = _audio_band_strip_view_h()
    render_w, render_h = _audio_hist_render_size(view_w, view_h)
    size_key = (render_w, render_h)
    if show_hist:
        render = eng.op('spect_render')
        bars = eng.op('spect_bars_glsl')
        chopto = eng.op('spect_chopto')
        if render is None or bars is None or chopto is None:
            force = True
            vis_refresh = True
        if eng.op('spect_bars') is not None:
            force = True
            vis_refresh = True
        stored_pipe = None
        try:
            stored_pipe = int(eng.fetch('audio_hist_pipeline', 0))
        except Exception:
            stored_pipe = 0
        if stored_pipe != _AUDIO_HIST_PIPELINE:
            force = True
            vis_refresh = True
        # Rebuild visuals only on refresh ticks; Spectrum-off holds the last frame.
        if cooking and vis_refresh and (force or _AUDIO_HIST_SIZE != size_key):
            _AUDIO_HIST_SIZE = size_key
            _ensure_spectrogram_visuals(eng, spect, render_w, render_h)
            try:
                eng.store('audio_hist_pipeline', _AUDIO_HIST_PIPELINE)
            except Exception:
                pass
            _mark_audio_hist_overlays_dirty()
        elif (not cooking) and eng.op('spect_hist_hold') is None:
            _ensure_spectrogram_freeze_hold(eng, render)
        # Keep display chain un-bypassed while Spectrum is on; Active stride gates GPU cooks.
        _set_spectrogram_visual_cooking(cooking)
        hold = _ensure_spectrogram_freeze_hold(eng, eng.op('spect_render'))
        if hold is not None:
            try:
                hold.par.active = bool(cooking and vis_refresh)
                hold.bypass = False
            except Exception:
                pass
    else:
        _set_spectrogram_visual_cooking(False)
    hold = eng.op('spect_hist_hold') if show_hist else None
    hist_top = hold if hold is not None else (eng.op('spect_render') if show_hist else None)
    hist_path = hist_top.path if hist_top is not None else ''
    ov = view.op('spect_view')
    if ov is not None:
        try:
            # This viewer is legacy. On packaged project load it can briefly
            # render the raw audiospectrum CHOP over the intended TOP display.
            ov.destroy()
        except Exception:
            pass
    try:
        spect.viewer = False
    except Exception:
        pass
    bind_key = (hist_path, bool(show_hist), render_w, render_h, view_w, view_h)
    if force or _AUDIO_HIST_VIEW_BIND != bind_key:
        _AUDIO_HIST_VIEW_BIND = bind_key
        if show_hist and hist_top is not None:
            try:
                view.par.top = hist_path
                view.par.topfill = 'native'
                view.par.topleftanchor = 0
                view.par.toprightanchor = 1
                view.par.topbottomanchor = 0
                view.par.toptopanchor = 1
                view.par.topleftoffset = 0
                view.par.toprightoffset = 0
                view.par.topbottomoffset = 0
                view.par.toptopoffset = 0
            except Exception:
                pass
        else:
            try:
                view.par.top = ''
            except Exception:
                pass
        try:
            view.par.display = True
            view.par.enable = True
            view.par.bgalpha = 0.0
        except Exception:
            pass
    _AUDIO_HIST_TICK += 1
    if show_hist and force:
        _cook_audio_histogram_chain(eng)


def _ensure_audio_panel():
    r = _root()
    ui = r.op('ui') if r else None
    if ui is None:
        return None
    panel = ui.op('audio_panel')
    if panel is None:
        panel = ui.create('containerCOMP', 'audio_panel')
    _purge_stray_audio_paramcomps(panel)
    try:
        panel.par.x = 0
        panel.par.y = 0
        panel.par.w = UI_W
        panel.par.h = AUDIO_PANEL_H
        panel.par.hmode = 'fixed'
        panel.par.vmode = 'fixed'
        panel.par.align = 'none'
        panel.par.bgcolorr, panel.par.bgcolorg, panel.par.bgcolorb = TD_BG_HEADER
        panel.par.bgalpha = 0.96
        panel.par.display = _audio_panel_visible()
        panel.par.enable = _audio_panel_visible()
        panel.par.clipping = True
    except Exception:
        pass

    view = panel.op('audio_spectrogram')
    if view is None:
        view = panel.create('containerCOMP', 'audio_spectrogram')
    _purge_stray_audio_paramcomps(view)
    stale_hint = panel.op('audio_hint')
    if stale_hint is not None:
        try:
            stale_hint.destroy()
        except Exception:
            pass
    _ensure_audio_hint(view)
    hist_w = _audio_hist_w()
    try:
        view.par.x = AUDIO_SPECT_PAD
        view.par.y = AUDIO_SPECT_PAD
        view.par.w = hist_w
        view.par.h = AUDIO_SPECT_H
        view.par.hmode = 'fixed'
        view.par.vmode = 'fixed'
        view.par.align = 'none'
        view.par.display = True
        view.par.enable = True
        view.par.bgcolorr, view.par.bgcolorg, view.par.bgcolorb = TD_BG_INPUT
        view.par.bgalpha = 1.0
        view.par.clipping = True
    except Exception:
        pass

    # The spectrum is presented through view.par.top. Do not create an
    # opviewerCOMP here; it exposes raw chan1/chan2 graphs during startup.
    ov = view.op('spect_view')
    if ov is not None:
        try:
            ov.destroy()
        except Exception:
            pass
    _ensure_audio_engine()
    _sync_spectrogram_display(view)
    _ensure_audio_hint(view)
    _ensure_audio_hist_overlays(view)

    readout_y = AUDIO_SPECT_H - 18
    x = hist_w - AUDIO_READOUT_W * 5 - 6
    labels = (
        ('readout_peak', 'peak'),
        ('readout_low', 'low'),
        ('readout_high', 'high'),
        ('readout_lowtrig', 'lowT'),
        ('readout_hightrig', 'hiT'),
    )
    for idx, (name, short) in enumerate(labels):
        comp = _ensure_audio_readout(view, name, short + ': 0.00')
        try:
            comp.par.x = x + idx * (AUDIO_READOUT_W + 3)
            comp.par.y = readout_y
            comp.par.clickthrough = True
        except Exception:
            pass
    try:
        panel.par.layoutorder = 9999
    except Exception:
        pass
    return panel


def _ensure_audio_meter_display(eng=None):
    """Smoothed Low/High/Peak triggers for the side meters only."""
    if eng is None:
        eng = _audio_engine()
    if eng is None:
        return None
    outv = eng.op(AUDIO_OUT_CHOP)
    if outv is None:
        return None

    trig_sel = eng.op('meter_trig_sel')
    if trig_sel is None:
        trig_sel = eng.create('selectCHOP', 'meter_trig_sel')
    try:
        trig_sel.par.channames = 'low_trigger high_trigger peak_trigger'
    except Exception:
        pass
    _wire_chop(outv, trig_sel)

    trig_lag = eng.op('meter_trig_lag')
    if trig_lag is None:
        trig_lag = eng.create('lagCHOP', 'meter_trig_lag')
    try:
        trig_lag.par.lag1 = float(AUDIO_METER_TRIG_ATTACK)
        trig_lag.par.lag2 = float(AUDIO_METER_TRIG_RELEASE)
        for unit_name in ('lagunit', 'unit'):
            try:
                p = getattr(trig_lag.par, unit_name)
                names = [str(x).lower() for x in (p.menuNames or [])]
                for i, n in enumerate(names):
                    if 'sec' in n:
                        p.val = p.menuNames[i]
                        break
            except Exception:
                pass
    except Exception:
        pass
    _wire_chop(trig_sel, trig_lag)

    # Drop unused level-average chain from earlier iterations.
    for stale_name in (
        'meter_sel', 'meter_level_sel', AUDIO_METER_LAG_CHOP, 'meter_merge',
    ):
        node = eng.op(stale_name)
        if node is not None:
            try:
                node.destroy()
            except Exception:
                pass

    disp = eng.op(AUDIO_METER_DISP_CHOP)
    if disp is None:
        disp = eng.create('nullCHOP', AUDIO_METER_DISP_CHOP)
    _wire_chop(trig_lag, disp)
    return disp


def _ensure_audio_meter_bar(
    side, name, label, level_chan, trig_chan, thresh_par, idx, count, hist_h, side_w, eng,
    y_offset=4, reverse_par=None, reverse_key=None, out_par=None,
):
    """Vertical trigger meter + label at top of each column."""
    if side is None or eng is None:
        return None
    gap = 4
    usable_w = max(24, side_w - 8)
    bar_w = max(14, (usable_w - gap * (count - 1)) // count)
    x = 4 + idx * (bar_w + gap)
    label_h = 14
    rev_h = 12
    rev_gap = AUDIO_METER_REV_GAP
    pad = 2
    col_h = max(48, hist_h)
    meter_h = max(28, col_h - label_h - rev_h - rev_gap - pad)
    lamp_h = 8
    fill_max = max(8, meter_h - lamp_h - 2)
    # Drive meters from Settings trigger outs so Reverse + Map stay in sync.
    if not out_par:
        out_par = {
            'low': 'Audiooutkick',
            'high': 'Audioouthit',
            'peak': 'Audiooutpeakhit',
        }.get(reverse_key or '', None)
    _ensure_audio_meter_display(eng)

    col = side.op(name)
    if col is None:
        col = side.create('containerCOMP', name)
    try:
        col.par.w = bar_w
        col.par.h = col_h
        col.par.x = x
        col.par.y = int(y_offset)
        col.par.hmode = 'fixed'
        col.par.vmode = 'fixed'
        col.par.align = 'none'
        col.par.display = True
        col.par.enable = True
        col.par.bgcolorr, col.par.bgcolorg, col.par.bgcolorb = TD_BG_HEADER
        col.par.bgalpha = 1.0
        col.par.clickthrough = True
    except Exception:
        pass

    for stale_name in (
        'dot', 'dot_view', 'ring', 'hole', 'ring_comp', 'dot_over',
        'lbl', 'lbl_panel',
    ):
        stale = col.op(stale_name)
        if stale is not None:
            try:
                stale.destroy()
            except Exception:
                pass

    # Trigger labels at the top of each column.
    lbl = col.op('label_txt')
    if lbl is None:
        lbl = col.create('textTOP', 'label_txt')
    try:
        lbl.par.text = label
        lbl.par.resolutionw = max(bar_w, 28)
        lbl.par.resolutionh = label_h
        lbl.par.font = TD_FONT
        lbl.par.fontsizex = TD_FONT_SIZE_SMALL
        lbl.par.fontsizey = TD_FONT_SIZE_SMALL
        lbl.par.alignx = 'center'
        lbl.par.aligny = 'center'
        lbl.par.fontcolorr, lbl.par.fontcolorg, lbl.par.fontcolorb = TD_TEXT_LABEL
        lbl.par.bgalpha = 0.0
    except Exception:
        pass
    lblp = col.op('label_panel')
    if lblp is None:
        lblp = col.create('containerCOMP', 'label_panel')
    try:
        lblp.par.w = bar_w
        lblp.par.h = label_h
        lblp.par.x = 0
        lblp.par.y = max(0, col_h - label_h)
        lblp.par.hmode = 'fixed'
        lblp.par.vmode = 'fixed'
        lblp.par.top = lbl
        lblp.par.topfill = 'fit'
        lblp.par.bgalpha = 0.0
        lblp.par.clickthrough = True
        lblp.par.display = True
    except Exception:
        pass

    track = col.op('track')
    if track is None:
        track = col.create('containerCOMP', 'track')
    try:
        track.par.w = max(8, bar_w - 6)
        track.par.h = meter_h
        track.par.x = max(0, (bar_w - int(track.par.w)) // 2)
        # Leave clear space between the trigger bars and the 0-1 button.
        track.par.y = rev_h + rev_gap
        track.par.hmode = 'fixed'
        track.par.vmode = 'fixed'
        track.par.bgcolorr, track.par.bgcolorg, track.par.bgcolorb = TD_SLIDER_TRACK
        track.par.bgalpha = 1.0
        track.par.clickthrough = True
        track.par.display = True
    except Exception:
        pass

    fill = track.op('fill')
    if fill is None:
        fill = track.create('containerCOMP', 'fill')
    try:
        fill.par.w = int(track.par.w)
        fill.par.x = 0
        fill.par.y = 0
        fill.par.hmode = 'fixed'
        fill.par.vmode = 'fixed'
        # Height pulsed on AUDIO_HIST_VIS_FRAME_STRIDE (~20fps) — no per-frame expr.
        _par_set_constant(fill.par.h, max(2, int(fill_max * 0.02)))
        fill.par.bgcolorr, fill.par.bgcolorg, fill.par.bgcolorb = TD_SLIDER_FILL
        fill.par.bgalpha = 1.0
        fill.par.clickthrough = True
        fill.par.display = True
    except Exception:
        pass
    try:
        col.store('meter_fill_max', int(fill_max))
        col.store('meter_out_par', str(out_par or ''))
    except Exception:
        pass

    # Trigger lamp sits inside the track at the top (not outside the box).
    lamp = track.op('lamp')
    if lamp is None:
        # Migrate old lamp off the column root if present.
        old_lamp = col.op('lamp')
        if old_lamp is not None:
            try:
                old_lamp.destroy()
            except Exception:
                pass
        lamp = track.create('containerCOMP', 'lamp')
    try:
        lamp.par.w = int(track.par.w)
        lamp.par.h = lamp_h
        lamp.par.x = 0
        lamp.par.y = max(0, meter_h - lamp_h)
        lamp.par.hmode = 'fixed'
        lamp.par.vmode = 'fixed'
        _par_set_constant(lamp.par.bgcolorr, 0.18)
        _par_set_constant(lamp.par.bgcolorg, 0.18)
        _par_set_constant(lamp.par.bgcolorb, 0.18)
        lamp.par.bgalpha = 1.0
        lamp.par.clickthrough = True
        lamp.par.display = True
    except Exception:
        pass

    # Per-trigger reverse toggle (0-1 <-> 1-0).
    _ensure_audio_meter_reverse(col, bar_w, rev_h, reverse_par, reverse_key)

    # Remove legacy threshold tick / level-average markers.
    for stale_name in ('thresh',):
        stale = track.op(stale_name)
        if stale is not None:
            try:
                stale.destroy()
            except Exception:
                pass
    return col


def _par_set_constant(par, value):
    """Clear expression binding and set a constant panel/par value."""
    if par is None:
        return
    try:
        par.expr = ''
    except Exception:
        pass
    try:
        par.mode = ParMode.CONSTANT
    except Exception:
        try:
            import td
            par.mode = td.ParMode.CONSTANT
        except Exception:
            pass
    try:
        par.val = value
    except Exception:
        try:
            par = value
        except Exception:
            pass


def _sync_audio_meter_visuals(strip=None, force=False):
    """Pulse Low/High/Peak meter fills on the same stride as the spectrum (~20fps)."""
    stride = max(1, int(AUDIO_HIST_VIS_FRAME_STRIDE))
    if (not force) and ((_AUDIO_HIST_TICK % stride) != 0):
        return False
    if strip is None:
        try:
            r = _root()
            ui = r.op('ui') if r is not None else None
            strip = ui.op('audio_band_strip') if ui is not None else None
        except Exception:
            strip = None
    side = strip.op('analysis_side') if strip is not None else None
    if side is None:
        return False
    s = _settings()
    if s is None:
        return False
    specs = (
        ('meter_low', 'Audiooutkick'),
        ('meter_high', 'Audioouthit'),
        ('meter_peak', 'Audiooutpeakhit'),
    )
    for meter_name, default_par in specs:
        col = side.op(meter_name)
        if col is None:
            continue
        try:
            out_par = str(col.fetch('meter_out_par', default_par) or default_par)
        except Exception:
            out_par = default_par
        try:
            fill_max = int(col.fetch('meter_fill_max', 0) or 0)
        except Exception:
            fill_max = 0
        track = col.op('track')
        fill = track.op('fill') if track is not None else None
        lamp = track.op('lamp') if track is not None else None
        if fill_max <= 0 and track is not None:
            try:
                lamp_h = int(float(lamp.par.h.eval())) if lamp is not None else 8
                fill_max = max(8, int(float(track.par.h.eval())) - lamp_h - 2)
            except Exception:
                fill_max = 24
        trig = 0.0
        try:
            trig = max(0.0, min(1.0, float(getattr(s.par, out_par).eval())))
        except Exception:
            trig = 0.0
        if fill is not None:
            try:
                _par_set_constant(fill.par.h, max(2, int(trig * fill_max)))
            except Exception:
                pass
        if lamp is not None:
            try:
                c = 0.18 + 0.82 * trig
                _par_set_constant(lamp.par.bgcolorr, c)
                _par_set_constant(lamp.par.bgcolorg, c)
                _par_set_constant(lamp.par.bgcolorb, c)
            except Exception:
                pass
    return True


def _ensure_audio_meter_reverse(col, bar_w, rev_h, reverse_par, reverse_key):
    """Clickable 0-1 / 1-0 toggle at the bottom of a trigger meter."""
    if col is None:
        return None
    rev = col.op('rev')
    if rev is None:
        rev = col.create('containerCOMP', 'rev')
    reversed_on = False
    if reverse_key:
        reversed_on = _audio_trigger_reverse_on(reverse_key)
    try:
        rev.par.w = bar_w
        rev.par.h = rev_h
        rev.par.x = 0
        rev.par.y = 0
        rev.par.hmode = 'fixed'
        rev.par.vmode = 'fixed'
        rev.par.display = True
        rev.par.enable = True
        rev.par.clickthrough = False
        rev.par.cursor = 'pointer'
        rev.par.drag = 'dragno'
        rev.par.drop = 'dropno'
        if reversed_on:
            rev.par.bgcolorr, rev.par.bgcolorg, rev.par.bgcolorb = TD_SLIDER_FILL
            rev.par.bgalpha = 0.85
        else:
            rev.par.bgcolorr, rev.par.bgcolorg, rev.par.bgcolorb = TD_BG_INPUT
            rev.par.bgalpha = 1.0
    except Exception:
        pass

    txt = rev.op('txt')
    if txt is None:
        txt = rev.create('textTOP', 'txt')
    try:
        txt.par.text = '1-0' if reversed_on else '0-1'
        txt.par.resolutionw = max(bar_w, 28)
        txt.par.resolutionh = rev_h
        txt.par.font = TD_FONT
        txt.par.fontsizex = max(7, TD_FONT_SIZE_SMALL - 1)
        txt.par.fontsizey = max(7, TD_FONT_SIZE_SMALL - 1)
        txt.par.alignx = 'center'
        txt.par.aligny = 'center'
        if reversed_on:
            txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = TD_TEXT_ACTIVE
        else:
            txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = TD_TEXT_LABEL
        txt.par.bgalpha = 0.0
    except Exception:
        pass
    try:
        rev.par.top = txt
        rev.par.topfill = 'fit'
    except Exception:
        pass
    if reverse_key:
        try:
            rev.store('audio_trig_reverse', reverse_key)
        except Exception:
            pass
    return rev


def _sync_audio_trigger_reverse_ui(strip=None):
    """Refresh Low/High/Peak reverse button labels/colors from settings."""
    if strip is None:
        try:
            r = _root()
            ui = r.op('ui') if r is not None else None
            strip = ui.op('audio_band_strip') if ui is not None else None
        except Exception:
            strip = None
    if strip is None:
        return False
    side = strip.op('analysis_side')
    if side is None:
        return False
    specs = (
        ('meter_low', 'Audioreverselow', 'low'),
        ('meter_high', 'Audioreversehigh', 'high'),
        ('meter_peak', 'Audioreversepeak', 'peak'),
    )
    for meter_name, _par_name, key in specs:
        col = side.op(meter_name)
        if col is None:
            continue
        rev = col.op('rev')
        if rev is None:
            continue
        try:
            bar_w = int(col.par.w)
            rev_h = int(rev.par.h) if int(rev.par.h) > 0 else 12
        except Exception:
            bar_w, rev_h = 20, 12
        _ensure_audio_meter_reverse(col, bar_w, rev_h, _par_name, key)
    return True


def _ensure_audio_analysis_side(strip, hist_h):
    """Right column: Low / High / Peak vertical level meters."""
    if strip is None:
        return None
    side = strip.op('analysis_side')
    if side is None:
        side = strip.create('containerCOMP', 'analysis_side')
    side_w = AUDIO_ANALYSIS_SIDE_W
    try:
        side.par.w = side_w
        side.par.h = hist_h
        side.par.hmode = 'fixed'
        side.par.vmode = 'fixed'
        side.par.align = 'none'
        side.par.display = True
        side.par.enable = True
        side.par.bgcolorr, side.par.bgcolorg, side.par.bgcolorb = (0.06, 0.06, 0.07)
        side.par.bgalpha = 1.0
        side.par.clipping = True
    except Exception:
        pass

    stale_names = (
        'gain_dial', 'gain_label_panel', 'gain_label', 'values_viewer',
        'trigger_dots', 'dot_lbl_low', 'dot_lbl_high', 'dot_lbl_peak',
        'dot_lbl_low_panel', 'dot_lbl_high_panel', 'dot_lbl_peak_panel',
        'trig_dot_low', 'trig_dot_high', 'trig_dot_peak',
    )
    for name in stale_names:
        stale = side.op(name)
        if stale is not None:
            try:
                stale.destroy()
            except Exception:
                pass
    for stale in list(side.children):
        if (
            stale.name.startswith('gain_')
            or stale.name.startswith('dot_lbl_')
            or stale.name.startswith('trig_dot_')
            or stale.name in ('values_viewer', 'trigger_dots')
        ):
            try:
                stale.destroy()
            except Exception:
                pass

    eng = _ensure_audio_engine()
    if eng is None:
        return side

    _ensure_audio_meter_display(eng)

    for eng_stale in (
        'trigger_dots_sel', 'trigger_dots_chopto',
        'trigger_dots_pixel', 'trigger_dots_glsl',
    ):
        node = eng.op(eng_stale)
        if node is not None:
            try:
                node.destroy()
            except Exception:
                pass

    specs = (
        ('meter_low', 'LOW', 'low', 'low_trigger', 'Audiothresholdlow', 'Audioreverselow', 'low', 'Audiooutkick', 0),
        ('meter_high', 'HIGH', 'high', 'high_trigger', 'Audiothresholdhigh', 'Audioreversehigh', 'high', 'Audioouthit', 1),
        ('meter_peak', 'PEAK', 'peak', 'peak_trigger', 'Audiothresholdpeak', 'Audioreversepeak', 'peak', 'Audiooutpeakhit', 2),
    )
    footer_h = 2
    meter_area_h = max(48, hist_h - footer_h - 2)
    for name, label, level_chan, trig_chan, thresh_par, reverse_par, reverse_key, out_par, idx in specs:
        _ensure_audio_meter_bar(
            side, name, label, level_chan, trig_chan, thresh_par,
            idx, 3, meter_area_h, side_w, eng,
            y_offset=footer_h,
            reverse_par=reverse_par,
            reverse_key=reverse_key,
            out_par=out_par,
        )

    _sync_audio_meter_visuals(strip, force=True)

    # Remove legacy Freeze / Triggers chrome under the meters.
    for stale_name in ('triggers_title', 'triggers_title_panel', 'hist_freeze'):
        stale = side.op(stale_name)
        if stale is not None:
            try:
                stale.destroy()
            except Exception:
                pass
    return side


def _ensure_audio_hist_freeze_button(side, side_w=None, footer_h=18):
    """Removed — destroy leftover button if present."""
    if side is None:
        return None
    btn = side.op('hist_freeze')
    if btn is not None:
        try:
            btn.destroy()
        except Exception:
            pass
    return None


def _ensure_peak_thresh_bar(strip, hist_h):
    """Peak threshold column — Low/High style (shade + label), no side grips."""
    if strip is None:
        return None
    bar_w = AUDIO_PEAK_THRESH_W
    bar = strip.op('peak_thresh_bar')
    if bar is None:
        bar = strip.create('containerCOMP', 'peak_thresh_bar')
    try:
        bar.par.w = bar_w
        bar.par.h = hist_h
        bar.par.hmode = 'fixed'
        bar.par.vmode = 'fixed'
        bar.par.align = 'none'
        bar.par.display = True
        bar.par.enable = True
        bar.par.clickthrough = False
        bar.par.cursor = 'pointer'
        bar.par.drag = 'dragno'
        bar.par.drop = 'dropno'
        bar.par.bgcolorr = bar.par.bgcolorg = bar.par.bgcolorb = 0.0
        bar.par.bgalpha = 0.0
        # Prefer unclipped so the tick can overhang into the spectrum.
        if hasattr(bar.par, 'clipping'):
            bar.par.clipping = False
    except Exception:
        pass

    # Body shade under the Peak label (same language as Low/High).
    fill = bar.op('fill')
    if fill is None:
        fill = bar.create('containerCOMP', 'fill')
    try:
        fill.par.w = bar_w
        fill.par.x = 0
        fill.par.y = 0
        fill.par.hmode = 'fixed'
        fill.par.vmode = 'fixed'
        fill.par.align = 'none'
        fill.par.display = True
        fill.par.enable = True
        fill.par.clickthrough = True
        try:
            fill.par.layoutorder = 1
        except Exception:
            pass
        rgb = AUDIO_BAND_HIGH_BODY
        fill.par.bgcolorr, fill.par.bgcolorg, fill.par.bgcolorb = rgb
        fill.par.bgalpha = AUDIO_BAND_BODY_ALPHA
    except Exception:
        pass

    # Legacy thin thumb — hide (replaced by horizontal Peak label).
    thumb = bar.op('thumb')
    if thumb is None:
        thumb = bar.create('containerCOMP', 'thumb')
    try:
        thumb.par.display = False
        thumb.par.enable = False
        thumb.par.clickthrough = True
        thumb.par.bgalpha = 0.0
    except Exception:
        pass

    # Thin horizontal tick on the strip — overhangs a few px into the spectrum.
    for stale_name in ('arrow', 'mark', 'tick'):
        stale = bar.op(stale_name)
        if stale is not None:
            try:
                stale.destroy()
            except Exception:
                try:
                    stale.par.display = False
                except Exception:
                    pass

    tick = strip.op('peak_tick')
    if tick is None:
        tick = strip.create('containerCOMP', 'peak_tick')
    try:
        tick.par.w = AUDIO_PEAK_TICK_EXTEND + AUDIO_PEAK_TICK_INSET
        tick.par.h = AUDIO_PEAK_TICK_H
        tick.par.hmode = 'fixed'
        tick.par.vmode = 'fixed'
        tick.par.align = 'none'
        tick.par.display = True
        tick.par.enable = True
        tick.par.clickthrough = True
        tick.par.bgcolorr, tick.par.bgcolorg, tick.par.bgcolorb = AUDIO_BAND_HIGH
        tick.par.bgalpha = AUDIO_BAND_TAG_ALPHA
        _clear_panel_borders(tick)
        try:
            tick.par.layoutorder = 40
        except Exception:
            pass
    except Exception:
        pass

    tag = bar.op('tag')
    if tag is None:
        tag = bar.create('containerCOMP', 'tag')
    # Drop legacy top-of-column PK label.
    for stale in ('label_txt',):
        old = bar.op(stale)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass
    txt = tag.op('txt')
    if txt is None:
        txt = tag.create('textTOP', 'txt')
    try:
        tag.par.w = bar_w
        tag.par.h = AUDIO_BAND_TAG_H
        tag.par.x = 0
        tag.par.hmode = 'fixed'
        tag.par.vmode = 'fixed'
        tag.par.align = 'none'
        tag.par.display = True
        tag.par.enable = True
        tag.par.clickthrough = True
        tag.par.cursor = 'pointer'
        tag.par.bgcolorr, tag.par.bgcolorg, tag.par.bgcolorb = AUDIO_BAND_HIGH
        tag.par.bgalpha = AUDIO_BAND_TAG_ALPHA
        _clear_panel_borders(tag)
        try:
            tag.par.layoutorder = 3
        except Exception:
            pass
        if txt is not None:
            txt.par.text = 'Peak'
            txt.par.resolutionw = bar_w
            txt.par.resolutionh = AUDIO_BAND_TAG_H
            txt.par.font = TD_FONT
            txt.par.fontsizex = TD_FONT_SIZE
            txt.par.fontsizey = TD_FONT_SIZE
            txt.par.alignx = 'center'
            txt.par.aligny = 'center'
            txt.par.bgalpha = 0.0
            txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = AUDIO_BAND_TAG_TEXT
            tag.par.top = txt
            tag.par.topfill = 'native'
    except Exception:
        pass

    # Full-height stationary hit — vertical drag only (no side grips).
    hit = bar.op('hit')
    if hit is None:
        hit = bar.create('containerCOMP', 'hit')
    try:
        hit.par.w = bar_w
        hit.par.h = hist_h
        hit.par.x = 0
        hit.par.y = 0
        hit.par.hmode = 'fixed'
        hit.par.vmode = 'fixed'
        hit.par.align = 'none'
        hit.par.display = True
        hit.par.enable = True
        hit.par.clickthrough = False
        hit.par.cursor = 'pointer'
        hit.par.bgalpha = 0.0
        try:
            hit.par.layoutorder = 10
        except Exception:
            pass
        hit.par.drag = 'dragno'
        hit.par.drop = 'dropno'
    except Exception:
        pass

    thr = _audio_threshold_for_band('peak')
    _apply_peak_thresh_visual(thr, bar=bar)
    return bar


def _ensure_audio_band_strip():
    """Audio Analysis panel above the settings panel."""
    r = _root()
    ui = r.op('ui') if r else None
    if ui is None:
        return None
    strip = ui.op('audio_band_strip')
    if strip is None:
        strip = ui.create('containerCOMP', 'audio_band_strip')
    _purge_stray_audio_paramcomps(strip)
    if not _sync_audio_band_strip_visibility(strip):
        return strip
    hist_w = _audio_band_strip_w()
    hist_h = _audio_band_strip_view_h()
    side_w = AUDIO_ANALYSIS_SIDE_W
    try:
        strip.par.x = _settings_panel_x()
        strip.par.w = _settings_panel_w()
        strip.par.h = AUDIO_BAND_STRIP_H
        strip.par.hmode = 'fixed'
        strip.par.vmode = 'fixed'
        strip.par.align = 'none'
        strip.par.clipping = True
        strip.par.bgcolorr, strip.par.bgcolorg, strip.par.bgcolorb = TD_BG_HEADER
        strip.par.bgalpha = 1.0
    except Exception:
        pass

    view = strip.op('audio_band_view')
    if view is None:
        view = strip.create('containerCOMP', 'audio_band_view')
    try:
        view.par.x = AUDIO_BAND_STRIP_PAD
        view.par.y = AUDIO_BAND_STRIP_PAD
        view.par.w = hist_w
        view.par.h = hist_h
        view.par.hmode = 'fixed'
        view.par.vmode = 'fixed'
        view.par.align = 'none'
        view.par.display = True
        view.par.enable = True
        view.par.bgcolorr, view.par.bgcolorg, view.par.bgcolorb = (0.0, 0.0, 0.0)
        view.par.bgalpha = 1.0
        view.par.clipping = True
        view.par.cursor = 'pointer'
    except Exception:
        pass

    side = _ensure_audio_analysis_side(strip, hist_h)
    peak = _ensure_peak_thresh_bar(strip, hist_h)
    if peak is not None:
        try:
            peak.par.x = AUDIO_BAND_STRIP_PAD * 2 + hist_w
            peak.par.y = AUDIO_BAND_STRIP_PAD
            peak.par.w = AUDIO_PEAK_THRESH_W
            peak.par.h = hist_h
        except Exception:
            pass
        _apply_peak_thresh_visual(_audio_threshold_for_band('peak'), bar=peak)
    if side is not None:
        try:
            side.par.x = AUDIO_BAND_STRIP_PAD * 3 + hist_w + AUDIO_PEAK_THRESH_W
            side.par.y = AUDIO_BAND_STRIP_PAD
            side.par.w = side_w
            side.par.h = hist_h
        except Exception:
            pass

    eng = _ensure_audio_engine()
    _sync_spectrogram_display(view, force=True)
    _ensure_audio_hist_overlays(view)
    return strip


def _layout_audio_band_strip(bottom_h):
    """Spectrum sits in the reserved slot above settings (live or greyed)."""
    r = _root()
    ui = r.op('ui') if r else None
    strip = ui.op('audio_band_strip') if ui is not None else None
    slot_y = max(0, int(bottom_h) - AUDIO_BAND_STRIP_H)
    if not _audio_spectrum_slot_visible():
        if strip is not None:
            try:
                strip.par.x = _settings_panel_x()
                strip.par.w = _settings_panel_w()
                strip.par.y = slot_y
                strip.par.h = 0
                strip.par.display = False
                strip.par.enable = False
                strip.par.bgalpha = 0.0
            except Exception:
                pass
        return
    strip = _ensure_audio_band_strip()
    if strip is None:
        return
    interactive = _audio_spectrum_interactive()
    cooking = _audio_spectrum_is_live()
    hist_w = _audio_band_strip_w()
    hist_h = _audio_band_strip_view_h()
    try:
        strip.par.x = _settings_panel_x()
        strip.par.w = _settings_panel_w()
        strip.par.h = AUDIO_BAND_STRIP_H
        strip.par.y = slot_y
        strip.par.display = True
        if hasattr(strip.par, 'layer'):
            strip.par.layer = 10
    except Exception:
        pass
    _apply_audio_spectrum_live_style(strip, cooking)
    view = strip.op('audio_band_view')
    if view is not None:
        try:
            view.par.w = hist_w
            view.par.h = hist_h
        except Exception:
            pass
        if interactive:
            _sync_spectrogram_display(view, force=True)
            _layout_audio_hist_overlays(view)
    peak = strip.op('peak_thresh_bar')
    if peak is None and interactive:
        peak = _ensure_peak_thresh_bar(strip, hist_h)
    if peak is not None:
        try:
            peak.par.x = AUDIO_BAND_STRIP_PAD * 2 + hist_w
            peak.par.y = AUDIO_BAND_STRIP_PAD
            peak.par.w = AUDIO_PEAK_THRESH_W
            peak.par.h = hist_h
            peak.par.display = True
            peak.par.enable = interactive
        except Exception:
            pass
        if interactive:
            _apply_peak_thresh_visual(_audio_threshold_for_band('peak'), bar=peak)
    side = strip.op('analysis_side')
    if side is not None:
        try:
            side.par.x = AUDIO_BAND_STRIP_PAD * 3 + hist_w + AUDIO_PEAK_THRESH_W
            side.par.y = AUDIO_BAND_STRIP_PAD
            side.par.w = AUDIO_ANALYSIS_SIDE_W
            side.par.h = hist_h
            side.par.display = True
            side.par.enable = interactive
        except Exception:
            pass
        if interactive:
            _ensure_audio_analysis_side(strip, hist_h)


def _audio_band_strip_reserve_h():
    """Reserve strip height the whole time the Audio tab is open (greyed or live)."""
    return AUDIO_BAND_STRIP_H if _audio_spectrum_slot_visible() else 0


def _hide_audio_band_strip_ui():
    """Histogram disabled — hide strip and stop overlay cooks."""
    r = _root()
    ui = r.op('ui') if r else None
    strip = ui.op('audio_band_strip') if ui is not None else None
    if strip is not None:
        _sync_audio_band_strip_visibility(strip)


def _hide_audio_panel_ui():
    """Bottom perform strip disabled — audio is configured in Settings -> Audio."""
    r = _root()
    if r is None:
        return
    ui = r.op('ui')
    if ui is None:
        return
    panel = ui.op('audio_panel')
    if panel is not None:
        try:
            panel.par.display = False
            panel.par.enable = False
            panel.par.h = 0
        except Exception:
            pass
    bar = ui.op('scene_bar')
    if bar is None:
        return
    btn = bar.op('scene_audio_toggle')
    if btn is not None:
        try:
            btn.par.display = False
            btn.par.enable = False
        except Exception:
            pass


def _layout_audio_panel():
    _hide_audio_panel_ui()


def _layout_audio_toggle_button(bar):
    if bar is None:
        return
    btn = bar.op('scene_audio_toggle')
    if btn is not None:
        try:
            btn.par.display = False
            btn.par.enable = False
        except Exception:
            pass


def toggle_audio_panel():
    toggle_audio_monitor()


def _audio_monitor_view_size():
    view_w = max(320, AUDIO_MONITOR_W - AUDIO_MONITOR_VIEW_PAD * 2)
    view_h = max(96, AUDIO_MONITOR_H - AUDIO_MONITOR_VIEW_PAD * 2 - 28)
    return view_w, view_h


def _ensure_audio_monitor_panel():
    """Compact interactive spectrum COMP hosted by the floating monitor window."""
    r = _root()
    if r is None:
        return None
    panel = r.op(AUDIO_MONITOR_NAME)
    if panel is None:
        panel = r.create('containerCOMP', AUDIO_MONITOR_NAME)
    _purge_stray_audio_paramcomps(panel)
    view_w, view_h = _audio_monitor_view_size()
    try:
        panel.par.w = AUDIO_MONITOR_W
        panel.par.h = AUDIO_MONITOR_H
        panel.par.hmode = 'fixed'
        panel.par.vmode = 'fixed'
        panel.par.align = 'none'
        panel.par.bgcolorr, panel.par.bgcolorg, panel.par.bgcolorb = TD_BG_HEADER
        panel.par.bgalpha = 1.0
        panel.par.display = True
        panel.par.enable = True
        panel.par.clipping = True
        panel.viewer = False
    except Exception:
        pass

    view = panel.op('audio_band_view')
    if view is None:
        view = panel.create('containerCOMP', 'audio_band_view')
    _purge_stray_audio_paramcomps(view)
    try:
        view.par.x = AUDIO_MONITOR_VIEW_PAD
        view.par.y = AUDIO_MONITOR_VIEW_PAD + 24
        view.par.w = view_w
        view.par.h = view_h
        view.par.hmode = 'fixed'
        view.par.vmode = 'fixed'
        view.par.align = 'none'
        view.par.display = True
        view.par.enable = True
        view.par.bgcolorr, view.par.bgcolorg, view.par.bgcolorb = TD_BG_INPUT
        view.par.bgalpha = 1.0
        view.par.clipping = True
    except Exception:
        pass

    title = panel.op('monitor_title')
    if title is None:
        title = panel.create('containerCOMP', 'monitor_title')
    title_txt = title.op('txt')
    if title_txt is None:
        title_txt = title.create('textTOP', 'txt')
    try:
        title.par.x = AUDIO_MONITOR_VIEW_PAD
        title.par.y = AUDIO_MONITOR_H - 22
        title.par.w = min(280, view_w)
        title.par.h = 20
        title.par.hmode = 'fixed'
        title.par.vmode = 'fixed'
        title.par.clickthrough = True
        title.par.bgalpha = 0.0
        title_txt.par.text = 'Audio Spectrum'
        title_txt.par.resolutionw = 280
        title_txt.par.resolutionh = 20
        title_txt.par.font = TD_FONT
        title_txt.par.fontsizex = TD_FONT_SIZE
        title_txt.par.fontsizey = TD_FONT_SIZE
        title_txt.par.alignx = 'left'
        title_txt.par.aligny = 'center'
        title_txt.par.fontcolorr, title_txt.par.fontcolorg, title_txt.par.fontcolorb = TD_TEXT_LABEL
        title_txt.par.bgalpha = 0.0
        title.par.top = title_txt
        title.par.topfill = 'fit'
    except Exception:
        pass

    if view.op('spect_view') is None:
        view.create('opviewerCOMP', 'spect_view')
    _ensure_audio_engine()
    _sync_spectrogram_display(view, force=True)
    _ensure_audio_hint(view)
    _ensure_audio_hist_overlays(view)

    readout_y = max(2, view_h - 18)
    labels = (
        ('readout_peak', 'peak'),
        ('readout_low', 'low'),
        ('readout_high', 'high'),
        ('readout_lowtrig', 'lowT'),
        ('readout_hightrig', 'hiT'),
    )
    x = max(4, view_w - AUDIO_READOUT_W * 5 - 6)
    for idx, (name, short) in enumerate(labels):
        comp = _ensure_audio_readout(view, name, short + ': 0.00')
        try:
            comp.par.x = x + idx * (AUDIO_READOUT_W + 3)
            comp.par.y = readout_y
            comp.par.clickthrough = True
        except Exception:
            pass
    return panel


def _ensure_audio_monitor_window():
    panel = _ensure_audio_monitor_panel()
    if panel is None:
        return None
    win = _audio_monitor_window_op()
    if win is None:
        try:
            win = op('/').create('windowCOMP', AUDIO_MONITOR_WINDOW)
        except Exception:
            return None
    # Apply each param alone — a missing par (e.g. w/h) must not abort the rest.
    try:
        win.par.winop = panel
    except Exception:
        pass
    try:
        win.par.size = 'custom'
    except Exception:
        pass
    for pname, value in (
        ('winw', AUDIO_MONITOR_W),
        ('winh', AUDIO_MONITOR_H),
        ('w', AUDIO_MONITOR_W),
        ('h', AUDIO_MONITOR_H),
    ):
        try:
            setattr(win.par, pname, value)
        except Exception:
            pass
    try:
        win.par.title = 'Sonomika Audio'
    except Exception:
        pass
    try:
        win.par.borders = True
    except Exception:
        pass
    try:
        win.par.alwaysontop = True
    except Exception:
        pass
    try:
        # Prefer opening on the primary display (multi-monitor safe).
        menus = list(getattr(win.par.justifyoffsetto, 'menuNames', []) or [])
        if 'primarydisplay' in menus:
            win.par.justifyoffsetto = 'primarydisplay'
    except Exception:
        pass
    try:
        win.par.drawwindow = True
    except Exception:
        pass
    try:
        win.nodeX = 40
        win.nodeY = 40
    except Exception:
        pass
    return win


def _ensure_audio_monitor_parexec():
    """Drop legacy Spectrum (Audiomonitor) from settings_parexec watch list."""
    s = _settings()
    if s is None:
        return False
    pe = s.op('settings_parexec') or s.op('parexec')
    if pe is None:
        return False
    changed = False
    try:
        pars = str(pe.par.pars.eval() if hasattr(pe.par.pars, 'eval') else pe.par.pars).strip()
    except Exception:
        pars = ''
    parts = [p for p in pars.split() if p and p != 'Audiomonitor']
    cleaned = ' '.join(parts)
    if cleaned != pars:
        try:
            pe.par.pars = cleaned
            changed = True
        except Exception:
            pass
    try:
        pe.par.valuechange = True
        pe.par.onpulse = True
        pe.par.active = True
    except Exception:
        pass
    return changed


def open_audio_monitor():
    """Legacy — ensure spectrum strip is shown."""
    global _AUDIO_MONITOR_OPEN
    _AUDIO_MONITOR_OPEN = True
    _destroy_audio_monitor_toggle()
    return _sync_audio_spectrum_for_settings_tab(force=True)


def close_audio_monitor():
    """Legacy no-op — spectrum stays visible; use Audio Active to mute input."""
    return open_audio_monitor()


def toggle_audio_monitor():
    """Legacy no-op — spectrum is always shown."""
    return open_audio_monitor()


def handle_audio_spectrum_drag(u, v=None, pick_edge=False):
    handle_audio_hist_interact(u, v=v, pick_edge=pick_edge)


def _update_audio_readouts():
    global _AUDIO_DEVICE_REFRESH_TICK, _AUDIO_HIST_TICK, _AUDIO_HIST_OVERLAY_DIRTY
    _AUDIO_DEVICE_REFRESH_TICK += 1
    # Keep spectrum strip visible above settings every frame.
    try:
        _sync_audio_spectrum_for_settings_tab()
    except Exception:
        pass
    if _AUDIO_DEVICE_REFRESH_TICK % 90 == 0:
        _refresh_audio_device_menu()
    if _AUDIO_DEVICE_REFRESH_TICK % 30 == 0:
        _sync_audio_output_pars()
        _sync_audio_hz_display_pars()
        eng = _audio_engine()
        if eng is not None:
            _heal_audio_output_chain(eng)
    r = _root()
    if not _audio_histogram_visible():
        if _AUDIO_DEVICE_REFRESH_TICK % 30 == 0:
            strip = r.op('ui/audio_band_strip') if r else None
            if strip is not None:
                _sync_audio_band_strip_visibility(strip)
        return
    panel = r.op(AUDIO_MONITOR_NAME) if r else None
    view = panel.op('audio_band_view') if panel is not None else None
    if view is None:
        strip = r.op('ui/audio_band_strip') if r else None
        view = strip.op('audio_band_view') if strip is not None else None
    if view is None:
        return
    # Same stride as spectrum (~20fps @60): update meters before tick advances in display sync.
    try:
        strip = r.op('ui/audio_band_strip') if r else None
        _sync_audio_meter_visuals(strip, force=False)
    except Exception:
        pass
    _sync_spectrogram_display(view)
    dragging = _audio_hist_drag_active()
    # Rebuild overlays only when dirty (band/thresh/open/resize) or on a slow cadence.
    # Per-frame layout rewrites textTOP resolutions and panel geometry — major FPS cost.
    if (not dragging) and (
        _AUDIO_HIST_OVERLAY_DIRTY
        or (_AUDIO_HIST_TICK % AUDIO_HIST_COOK_INTERVAL == 0)
    ):
        _layout_audio_hist_overlays(view)
        _AUDIO_HIST_OVERLAY_DIRTY = False


def _set_audio_par_default(s, par_name, value):
    if s is None:
        return
    try:
        par = getattr(s.par, par_name)
        par.val = value
        par.default = value
    except Exception:
        pass


def _audio_new_set_defaults():
    return (
        ('Audioactive', DEFAULT_AUDIO_ACTIVE),
        ('Audiodeviceindex', '0'),
        ('Audiogain', DEFAULT_AUDIO_GAIN),
        ('Audiothresholdlow', DEFAULT_THRESH_LOW),
        ('Audioreverselow', False),
        ('Audiothresholdhigh', DEFAULT_THRESH_HIGH),
        ('Audioreversehigh', False),
        ('Audiothresholdpeak', DEFAULT_THRESH_PEAK),
        ('Audioreversepeak', False),
    )


def reset_audio_defaults_for_new_set():
    """Restore Audio tab defaults when starting a blank performance set."""
    s = _settings()
    if s is None:
        return False
    _ensure_audio_settings()
    _init_audio_band_storage(s, force=True)
    for par_name, value in _audio_new_set_defaults():
        _set_audio_par_default(s, par_name, value)
    _wire_audio_output_exprs(s)
    eng = _audio_engine()
    if eng is not None:
        _heal_audio_output_chain(eng)
    _sync_audio_active()
    try:
        _apply_audio_device()
    except Exception:
        pass
    try:
        _sync_audio_hz_display_pars()
    except Exception:
        pass
    try:
        _sync_audio_output_pars()
    except Exception:
        pass
    return True


def _cleanup_audio_tab_pars():
    """Remove stray Audio-tab parameters not in the supported layout."""
    s = _settings()
    if s is None:
        return
    allowed = _audio_tab_allowed_pars()
    for par in list(s.customPars):
        try:
            page_name = par.page.name if hasattr(par.page, 'name') else str(par.page)
        except Exception:
            continue
        if page_name != 'Audio':
            continue
        if par.name in allowed:
            continue
        try:
            par.destroy()
        except Exception:
            pass


def _ensure_audio_output_pars():
    """Keep Low/High/Peak level + trigger readouts on the Audio tab."""
    s = _settings()
    if s is None:
        return
    _cleanup_audio_tab_pars()
    # Thresholds are internal (panel-driven) but required for triggerCHOPs.
    _ensure_audio_settings()
    page = None
    for pg in s.customPages:
        if pg.name == 'Audio':
            page = pg
            break
    if page is None:
        return

    def _out(name, label):
        try:
            p = getattr(s.par, name)
        except AttributeError:
            p = page.appendFloat(name, label=label)
            p.default = 0.0
            p.val = 0.0
        try:
            p.min = 0.0
            p.max = 1.0
            p.label = label
        except Exception:
            pass

    _out('Audiooutlow', 'Low')
    _out('Audiooutkick', 'Low Trigger')
    _out('Audioouthigh', 'High')
    _out('Audioouthit', 'High Trigger')
    _out('Audiooutpeak', 'Peak')
    _out('Audiooutpeakhit', 'Peak Trigger')

    _destroy_removed_audio_pars(s)
    _wire_audio_output_exprs(s)
    _sync_audio_tab_layout(s)


def _ensure_audio_refresh_pulse():
    """Add Refresh pulse on existing Audio tabs without full rebuild."""
    s = _settings()
    if s is None:
        return
    page = None
    for pg in s.customPages:
        if pg.name == 'Audio':
            page = pg
            break
    if page is None:
        return
    try:
        getattr(s.par, 'Audiorefresh')
    except AttributeError:
        try:
            page.appendPulse('Audiorefresh', label='Refresh Audio Input')
        except Exception:
            pass
    _ensure_audio_monitor_toggle(s, page)
    _ensure_audio_monitor_parexec()
    _reorder_audio_tab_pars()


def _restart_audio_device_input():
    eng = _audio_engine()
    if eng is None:
        return
    dev = eng.op('audiodevin1')
    if dev is None:
        return
    want_active = _audio_active()
    try:
        dev.par.active = False
        dev.cook(force=True)
    except Exception:
        pass
    try:
        dev.par.active = want_active
        dev.cook(force=True)
    except Exception:
        pass


def refresh_audio_input():
    """Restart audio capture, refresh device list; stay on Audio tab."""
    try:
        _pin_settings_tab('Audio')
    except Exception:
        pass
    _ensure_audio_engine()
    _refresh_audio_device_menu(force=True)
    _apply_audio_device()
    _restart_audio_device_input()
    _sync_audio_active()
    eng = _audio_engine()
    if eng is not None:
        _heal_audio_output_chain(eng)
        if _audio_active():
            try:
                eng.cook(force=True)
            except Exception:
                pass
            _heal_audio_spectrum_if_needed(eng)
    _sync_audio_hz_display_pars()
    _sync_audio_output_pars()
    try:
        idx = _settings_tab_index('Audio')
        settings = _settings()
        if idx is not None and settings is not None:
            settings.par.pageindex = idx
    except Exception:
        pass
    try:
        _nudge_settings_params_panel('Audio')
    except Exception:
        pass
    return True


def configure_audio_analysis():
    _ensure_audio_settings()
    _init_audio_band_storage()
    _ensure_audio_refresh_pulse()
    _ensure_audio_output_pars()
    _ensure_audio_engine()
    _wire_audio_output_exprs()
    _refresh_audio_device_menu(force=True)
    _apply_preferred_audio_device()
    _sync_audio_active()
    _sync_audio_hz_display_pars()
    _hide_audio_panel_ui()
    try:
        _destroy_audio_monitor_toggle()
    except Exception:
        pass
    try:
        _ensure_settings_pageindex_parexec()
    except Exception:
        pass
    try:
        _ensure_audio_band_strip()
        _expand_audio_spectrum_strip()
        _destroy_audio_hints()
    except Exception:
        pass
    try:
        _refresh_panel_exec_panels()
    except Exception:
        pass
    try:
        _layout_perform_ui()
    except Exception:
        pass
    try:
        _sync_audio_spectrum_for_settings_tab(force=True)
    except Exception:
        pass


def audio_out_chop_path():
    eng = _audio_engine()
    if eng is None:
        return ''
    outv = eng.op(AUDIO_OUT_CHOP)
    return outv.path if outv is not None else ''
