import math
import random

PULSE_SLOTS = 6
PULSE_PAGE_ORDER = [
    'Canvas', 'Sets', 'OSC', SETTINGS_TAB_GRID_OSC, 'Pulse', 'Audio', 'Midi', 'Fade',
    SETTINGS_TAB_PERF, 'Rec', 'About',
]
PULSE_DIVISION_NAMES = ['1_32', '1_16', '1_8', '1_4', '1_2', '1bar', '2bar', '4bar', '8bar']
PULSE_DIVISION_LABELS = [
    '1/32', '1/16', '1/8', '1/4', '1/2', '1 Bar', '2 Bars', '4 Bars', '8 Bars',
]
PULSE_DIVISION_BEATS = {
    '1_32': 0.125,
    '1_16': 0.25,
    '1_8': 0.5,
    '1_4': 1.0,
    '1_2': 2.0,
    '1bar': 4.0,
    '2bar': 8.0,
    '4bar': 16.0,
    '8bar': 32.0,
}
PULSE_LEGACY_DIVISION_MAP = {
    '1': '1_4',
    '2': '1_8',
    '4': '1_16',
    '8': '1_32',
    '16': '1_32',
    '32': '1_32',
}
PULSE_DEFAULT_DIVISIONS = ['1_16', '1_8', '1_4', '1_2', '1_16', '1_8']
PULSE_DEFAULT_SKIPS = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
PULSE_DEFAULT_LFO = False
PULSE_DEFAULT_MIN = 0.0
PULSE_DEFAULT_MAX = 1.0
PULSE_DEFAULT_CUSTOM_BPM = False
PULSE_RANGE_MIN = 0.0
PULSE_RANGE_MAX = 100000.0
PULSE_DEFAULT_ADDRESSES = {
    1: '/sonomika/pulse1',
    2: '/sonomika/pulse2',
    3: '/sonomika/pulse3',
    4: '/sonomika/pulse4',
    5: '/sonomika/pulse5',
    6: '/sonomika/pulse6',
}
PULSE_HOLD_FLASH_SEC = 0.08


def _clamp_pulse(v, lo, hi):
    return max(lo, min(hi, float(v)))


def _mark_section(par):
    if par is None:
        return
    try:
        par.startSection = True
    except Exception:
        pass


def _migrate_pulse_division(value, default):
    value = str(value or '').strip()
    if value in PULSE_DIVISION_NAMES:
        return value
    for name, label in zip(PULSE_DIVISION_NAMES, PULSE_DIVISION_LABELS):
        if value == str(label):
            return str(name)
    return PULSE_LEGACY_DIVISION_MAP.get(value, default)


def _resolve_menu_value(value, names, labels, default, migrate_fn=None):
    raw = str(value or '').strip()
    name_list = [str(n) for n in names]
    label_list = [str(l) for l in labels]
    if raw in name_list:
        return raw
    for name, label in zip(name_list, label_list):
        if raw == label:
            return name
    if migrate_fn is not None:
        migrated = migrate_fn(raw, default)
        if migrated in name_list:
            return migrated
    return default


def _division_name_to_index(name, default_name='1_16'):
    resolved = _migrate_pulse_division(name, default_name)
    try:
        return int(PULSE_DIVISION_NAMES.index(resolved))
    except ValueError:
        return int(PULSE_DIVISION_NAMES.index(_migrate_pulse_division(default_name, default_name)))


def _division_index_to_name(index, default_name='1_16'):
    try:
        idx = int(round(float(index)))
    except Exception:
        idx = _division_name_to_index(default_name, default_name)
    idx = max(0, min(len(PULSE_DIVISION_NAMES) - 1, idx))
    return PULSE_DIVISION_NAMES[idx]


def _pulse_division_label(slot):
    return '{} Division'.format(int(slot))


def _refresh_pulse_division_label(par_name):
    """No-op: dynamic label updates made the settings panel jump tabs while dragging."""


def _ensure_division_par(page, s, slot, default_div):
    names = _pulse_slot_names(slot)
    par_name = names['division']
    default_name = _migrate_pulse_division(default_div, default_div)
    current_name = default_name
    par = None

    try:
        par = getattr(s.par, par_name)
    except AttributeError:
        par = None

    if par is not None:
        try:
            style = str(par.style)
            if style == 'Int':
                current_name = _division_index_to_name(par.eval(), default_name)
                par.destroy()
                par = None
            elif style == 'Menu':
                current_name = _migrate_pulse_division(par.eval(), default_name)
            else:
                current_name = _migrate_pulse_division(par.eval(), default_name)
                par.destroy()
                par = None
        except Exception:
            par = None

    if par is None:
        par = page.appendMenu(par_name, label=_pulse_division_label(slot))
        par.default = default_name
        par.val = current_name

    try:
        par.menuNames = list(PULSE_DIVISION_NAMES)
        par.menuLabels = list(PULSE_DIVISION_LABELS)
        par.val = _migrate_pulse_division(par.eval(), default_name)
        par.label = _pulse_division_label(slot)
    except Exception:
        pass
    return par


def _pulse_tab_ready():
    s = _settings_op()
    if s is None:
        return False
    has_page = False
    try:
        for pg in s.customPages:
            if pg.name == 'Pulse':
                has_page = True
                break
    except Exception:
        return False
    if not has_page:
        return False
    try:
        getattr(s.par, 'Pulseactive')
        getattr(s.par, _pulse_slot_names(PULSE_SLOTS)['value'])
        getattr(s.par, _pulse_slot_names(1)['lfo'])
        getattr(s.par, 'Pulsecustombpm')
    except AttributeError:
        return False
    try:
        getattr(s.par, 'Pulseusetempo')
        return False
    except AttributeError:
        pass
    return True


def _ensure_pulse_custom_bpm_par(s=None, page=None):
    """Replace legacy Pulseusetempo with Pulsecustombpm (inverted semantics)."""
    if s is None:
        s = _settings_op()
    if s is None:
        return False
    if page is None:
        page = _pulse_settings_page()
    if page is None:
        return False
    legacy_use_timeline = None
    try:
        legacy_use_timeline = bool(int(float(s.par.Pulseusetempo.eval())))
    except Exception:
        pass
    has_custom = True
    try:
        getattr(s.par, 'Pulsecustombpm')
    except AttributeError:
        has_custom = False
    if not has_custom:
        if legacy_use_timeline is not None:
            custom_default = not legacy_use_timeline
        else:
            custom_default = PULSE_DEFAULT_CUSTOM_BPM
        p = page.appendToggle('Pulsecustombpm', label='Custom BPM')
        p.default = PULSE_DEFAULT_CUSTOM_BPM
        p.val = custom_default
    try:
        s.par.Pulsecustombpm.label = 'Custom BPM'
    except Exception:
        pass
    try:
        getattr(s.par, 'Pulseusetempo').destroy()
    except Exception:
        pass
    return True


def _ensure_pulse_page_order():
    s = _settings_op()
    if s is None:
        return False
    _migrate_settings_tab_names(s)
    page_state = _settings_panel_page_state()
    try:
        current = [pg.name for pg in s.customPages]
        desired = [name for name in PULSE_PAGE_ORDER if name in current]
        for name in current:
            if name not in desired:
                desired.append(name)
        if current == desired:
            return True
        s.sortCustomPages(*desired)
    except Exception:
        return False
    finally:
        _restore_settings_panel_page(page_state)
    return True


def _pulse_settings_page():
    s = _settings_op()
    if s is None:
        return None
    for pg in s.customPages:
        if pg.name == 'Pulse':
            return pg
    return s.appendCustomPage('Pulse')


def _pulse_slot_names(slot):
    n = int(slot)
    return {
        'active': 'Pulse{}active'.format(n),
        'division': 'Pulse{}division'.format(n),
        'skip': 'Pulse{}skip'.format(n),
        'lfo': 'Pulse{}lfo'.format(n),
        'kick': 'Pulse{}kick'.format(n),
        'peak': 'Pulse{}peak'.format(n),
        'min': 'Pulse{}min'.format(n),
        'max': 'Pulse{}max'.format(n),
        'value': 'Pulse{}value'.format(n),
    }


def _ensure_pulse_slot_sections(s=None):
    """Divider line above each pulse generator block on the Pulse tab."""
    if s is None:
        s = _settings_op()
    if s is None:
        return False
    for slot in range(1, PULSE_SLOTS + 1):
        try:
            _mark_section(getattr(s.par, _pulse_slot_names(slot)['active']))
        except Exception:
            pass
    return True


def _pulse_page_par_order():
    names = ['Pulseactive', 'Pulsecustombpm', 'Pulsebpm']
    for slot in range(1, PULSE_SLOTS + 1):
        p = _pulse_slot_names(slot)
        names.extend([
            p['active'],
            p['division'],
            p['skip'],
            p['lfo'],
            p['kick'],
            p['peak'],
            p['min'],
            p['max'],
            p['value'],
        ])
    return names


def _destroy_legacy_pulse_pars(s):
    for name in (
        'Pulsevalue',
        'Pulsedivision',
        'Pulseskip',
        'Pulseoscactive',
        'Pulseoscaddress',
        'Pulseoscnote',
        'Pulseosclast',
        'Pulsecount',
        'Pulseholds',
        'Pulseholdchance',
    ):
        try:
            getattr(s.par, name).destroy()
        except Exception:
            pass
    for slot in range(1, PULSE_SLOTS + 1):
        try:
            getattr(s.par, 'Pulse{}address'.format(slot)).destroy()
        except Exception:
            pass


def _ensure_pulse_tab_pars():
    """Create or repair the Pulse settings tab."""
    s = _settings_op()
    if s is None:
        return False
    page = _pulse_settings_page()
    if page is None:
        return False

    def _ensure_toggle(name, label, default):
        try:
            p = getattr(s.par, name)
        except AttributeError:
            p = page.appendToggle(name, label=label)
            p.default = default
            p.val = default
        return p

    def _ensure_float(name, label, default, mn, mx, readonly=False):
        try:
            p = getattr(s.par, name)
        except AttributeError:
            p = page.appendFloat(name, label=label)
            p.default = default
            p.val = default
        try:
            p.min = mn
            p.max = mx
            p.normMin = mn
            p.normMax = mx
            p.clampMin = True
            p.clampMax = True
            p.readOnly = bool(readonly)
        except Exception:
            pass
        return p

    def _ensure_menu(name, label, names, labels, default, migrate_fn=None):
        try:
            p = getattr(s.par, name)
        except AttributeError:
            p = page.appendMenu(name, label=label)
            p.default = default
            p.val = default
        try:
            p.menuNames = list(names)
            p.menuLabels = list(labels)
            resolved = _resolve_menu_value(p.eval(), names, labels, default, migrate_fn=migrate_fn)
            if str(p.eval()) != resolved:
                p.val = resolved
        except Exception:
            pass
        return p

    _destroy_legacy_pulse_pars(s)

    _ensure_toggle('Pulseactive', 'Active', False)
    _ensure_pulse_custom_bpm_par(s, page)
    _ensure_float('Pulsebpm', 'BPM', 120.0, 20.0, 300.0)
    _sync_pulse_bpm_par_state()

    for slot in range(1, PULSE_SLOTS + 1):
        p = _pulse_slot_names(slot)
        default_div = PULSE_DEFAULT_DIVISIONS[slot - 1]
        section = _ensure_toggle(p['active'], '{} Active'.format(slot), False)
        _mark_section(section)
        _ensure_division_par(page, s, slot, default_div)
        _ensure_float(
            p['skip'],
            '{} Skip %'.format(slot),
            PULSE_DEFAULT_SKIPS[slot - 1],
            0.0,
            100.0,
        )
        _ensure_toggle(p['lfo'], '{} LFO'.format(slot), PULSE_DEFAULT_LFO)
        _ensure_toggle(p['kick'], '{} Audio Kick'.format(slot), False)
        _ensure_toggle(p['peak'], '{} Audio Peak'.format(slot), False)
        _ensure_float(
            p['min'],
            '{} Min'.format(slot),
            PULSE_DEFAULT_MIN,
            PULSE_RANGE_MIN,
            PULSE_RANGE_MAX,
        )
        _ensure_float(
            p['max'],
            '{} Max'.format(slot),
            PULSE_DEFAULT_MAX,
            PULSE_RANGE_MIN,
            PULSE_RANGE_MAX,
        )
        _ensure_float(
            p['value'],
            '{} Value'.format(slot),
            PULSE_DEFAULT_MIN,
            PULSE_RANGE_MIN,
            PULSE_RANGE_MAX,
            readonly=True,
        )

    page_state = _settings_panel_page_state()
    try:
        _reorder_custom_page_pars('Pulse', _pulse_page_par_order())
        _ensure_pulse_page_order()
    finally:
        _restore_settings_panel_page(page_state)
    return True


def _pulse_frame_exec_text():
    return _read_embedded_dat('pulse_frame_exec.py') or ''


def _ensure_pulse_frame_exec():
    s = _settings_op()
    if s is None:
        return None
    ex = s.op('pulse_frame_exec')
    if ex is None:
        ex = s.create('executeDAT', 'pulse_frame_exec')
    try:
        ex.text = _pulse_frame_exec_text()
        ex.par.active = True
        ex.par.framestart = True
        ex.par.frameend = False
    except Exception:
        pass
    return ex


def _ensure_settings_parexec_wired():
    s = _settings_op()
    if s is None:
        return False
    try:
        from performance_grid.builder.helpers_settings import _wire_settings_parexec
        _wire_settings_parexec(s)
        return True
    except Exception:
        return False


def _pulse_settings_sig():
    s = _settings_op()
    if s is None:
        return None
    names = ['Pulseactive', 'Pulsecustombpm']
    names.extend(_pulse_slot_names(slot)['active'] for slot in range(1, PULSE_SLOTS + 1))
    names = tuple(names)
    try:
        return tuple(int(bool(getattr(s.par, name).eval())) for name in names)
    except Exception:
        return None


def _store_pulse_settings_sig(sig=None):
    s = _settings_op()
    if s is None:
        return
    if sig is None:
        sig = _pulse_settings_sig()
    if sig is not None:
        s.store('pulse_settings_sig', sig, search=False)


def _disable_legacy_settings_panel_exec():
    """Remove broken per-panel execute added in an earlier pulse fix."""
    r = _root()
    if r is None:
        return
    pe = r.op('settings_panel_exec')
    if pe is None:
        return
    try:
        pe.par.active = False
    except Exception:
        pass


def _apply_pulse_settings_change(par_name):
    """React immediately to Pulse tab toggles (Perform panel + /settings parexec)."""
    name = str(par_name or '')
    if not name.startswith('Pulse'):
        return False
    _ensure_pulse_frame_exec()
    _ensure_pulse_osc_out()
    if name == 'Pulseactive':
        _reset_pulse_sync()
        if _pulse_active():
            _ensure_pulse_master_slot()
        else:
            _clear_pulse_slot_values()
    elif name == 'Pulsecustombpm':
        _reset_pulse_sync()
        _sync_pulse_bpm_par_state()
    elif name == 'Pulsebpm':
        _reset_pulse_sync()
        _sync_pulse_bpm_par_state()
    elif name.endswith('active') or 'division' in name or name.endswith('skip') or name.endswith('lfo') or name.endswith('kick') or name.endswith('peak'):
        _reset_pulse_sync()
    _store_pulse_settings_sig()
    update_pulse_engine()
    return True


def _ensure_pulse_osc_out():
    s = _settings_op()
    if s is None:
        return None
    osc = s.op('pulse_osc_out')
    if osc is None:
        try:
            osc = s.create('oscoutDAT', 'pulse_osc_out')
        except Exception:
            return None
    try:
        osc.par.active = True
        osc.par.address = _osc_ip()
        osc.par.port = int(_osc_port())
    except Exception:
        pass
    return osc


def configure_pulse_engine(reset_sync=True, heal_pars=None):
    _migrate_settings_tab_names()
    if heal_pars is None:
        heal_pars = not _pulse_tab_ready()
    if heal_pars:
        _ensure_pulse_tab_pars()
    else:
        _ensure_pulse_custom_bpm_par()
        _ensure_pulse_slot_sections()
        _ensure_pulse_page_order()
    _ensure_pulse_frame_exec()
    _ensure_pulse_osc_out()
    _ensure_settings_parexec_wired()
    _disable_legacy_settings_panel_exec()
    if reset_sync:
        _reset_pulse_sync()
    _sync_pulse_bpm_par_state()
    return True


def _set_pulse_toggle_off(name):
    s = _settings_op()
    if s is None:
        return
    try:
        par = getattr(s.par, name)
        par.default = False
        par.val = False
    except Exception:
        pass


def reset_pulse_defaults_for_new_set():
    """Turn pulse engine off when starting a blank performance set."""
    s = _settings_op()
    if s is None:
        return False
    _ensure_pulse_tab_pars()
    _set_pulse_toggle_off('Pulseactive')
    _set_pulse_toggle_off('Pulsecustombpm')
    for slot in range(1, PULSE_SLOTS + 1):
        names = _pulse_slot_names(slot)
        _set_pulse_toggle_off(names['active'])
        try:
            getattr(s.par, names['value']).val = _pulse_slot_output(slot, 0.0)
        except Exception:
            pass
    _reset_pulse_sync()
    _clear_pulse_slot_values()
    _sync_pulse_bpm_par_state()
    _store_pulse_settings_sig()
    return True


def refresh_pulse_osc_out():
    _ensure_pulse_osc_out()
    return True


def _pulse_active():
    s = _settings_op()
    if s is None:
        return False
    try:
        return bool(s.par.Pulseactive.eval())
    except Exception:
        return False


def _pulse_custom_bpm():
    s = _settings_op()
    if s is None:
        return False
    try:
        return bool(s.par.Pulsecustombpm.eval())
    except AttributeError:
        try:
            return not bool(s.par.Pulseusetempo.eval())
        except Exception:
            return False
    except Exception:
        return False


def _pulse_use_tempo():
    """True when pulses follow TouchDesigner timeline tempo (Custom BPM off)."""
    return not _pulse_custom_bpm()


_PULSE_BPM_SYNC_GUARD = 0


def _sync_pulse_bpm_par_state():
    """Timeline mode mirrors TD tempo; custom mode uses Pulsebpm (always draggable)."""
    global _PULSE_BPM_SYNC_GUARD
    s = _settings_op()
    if s is None:
        return
    custom = _pulse_custom_bpm()
    try:
        par = s.par.Pulsebpm
        par.readOnly = False
        if not custom:
            tempo = project_tempo()
            if abs(float(par.eval()) - tempo) > 0.001:
                _PULSE_BPM_SYNC_GUARD += 1
                try:
                    par.val = tempo
                finally:
                    _PULSE_BPM_SYNC_GUARD -= 1
    except Exception:
        pass


def _pulse_timeline_playing():
    try:
        return bool(global_transport_playing())
    except Exception:
        pass
    return True


def _ensure_pulse_master_slot():
    """Master Active alone does nothing — enable slot 1 if none are on."""
    if not _pulse_active():
        return
    if any(_pulse_slot_active(slot) for slot in range(1, PULSE_SLOTS + 1)):
        return
    try:
        _settings_op().par.Pulse1active = True
    except Exception:
        pass


def _pulse_bpm():
    if _pulse_use_tempo():
        try:
            t = op('/').time
            if t is not None:
                return max(1.0, float(t.tempo))
        except Exception:
            pass
        return 120.0
    s = _settings_op()
    if s is None:
        return 120.0
    try:
        return max(1.0, float(s.par.Pulsebpm.eval()))
    except Exception:
        return 120.0


def _pulse_slot_beats(slot):
    s = _settings_op()
    if s is None:
        return 1.0
    names = _pulse_slot_names(slot)
    default_div = PULSE_DEFAULT_DIVISIONS[slot - 1]
    try:
        par = getattr(s.par, names['division'])
        if str(par.style) == 'Int':
            raw = _division_index_to_name(par.eval(), default_div)
        else:
            raw = _migrate_pulse_division(par.eval(), default_div)
        return max(0.0625, float(PULSE_DIVISION_BEATS.get(raw, 1.0)))
    except Exception:
        return 1.0


def _pulse_slot_skip_chance(slot):
    s = _settings_op()
    if s is None:
        return 0.0
    names = _pulse_slot_names(slot)
    try:
        return max(0.0, min(100.0, float(getattr(s.par, names['skip']).eval()))) / 100.0
    except Exception:
        return 0.0


def _pulse_slot_lfo(slot):
    s = _settings_op()
    if s is None:
        return False
    names = _pulse_slot_names(slot)
    try:
        return bool(getattr(s.par, names['lfo']).eval())
    except Exception:
        return False


def _pulse_slot_kick(slot):
    s = _settings_op()
    if s is None:
        return False
    names = _pulse_slot_names(slot)
    try:
        return bool(getattr(s.par, names['kick']).eval())
    except Exception:
        return False


def _pulse_slot_peak(slot):
    s = _settings_op()
    if s is None:
        return False
    names = _pulse_slot_names(slot)
    try:
        return bool(getattr(s.par, names['peak']).eval())
    except Exception:
        return False


def _audio_kick_level():
    """0-1 kick gate from Settings Out Kick (bass threshold trigger)."""
    s = _settings_op()
    if s is None:
        return 0.0
    try:
        if hasattr(s.par, 'Audioactive') and not bool(s.par.Audioactive.eval()):
            return 0.0
    except Exception:
        pass
    try:
        if hasattr(s.par, 'Audiooutkick'):
            return float(s.par.Audiooutkick.eval())
    except Exception:
        pass
    try:
        eng = op('/project1/performance_mode/audio_engine')
        outv = eng.op('out_values') if eng is not None else None
        if outv is not None:
            return float(outv['low_trigger'] or 0)
    except Exception:
        pass
    return 0.0


def _audio_peak_hit_level():
    """0-1 peak hit gate from Settings Out Peak Hit."""
    s = _settings_op()
    if s is None:
        return 0.0
    try:
        if hasattr(s.par, 'Audioactive') and not bool(s.par.Audioactive.eval()):
            return 0.0
    except Exception:
        pass
    try:
        if hasattr(s.par, 'Audiooutpeakhit'):
            return float(s.par.Audiooutpeakhit.eval())
    except Exception:
        pass
    try:
        eng = op('/project1/performance_mode/audio_engine')
        outv = eng.op('out_values') if eng is not None else None
        if outv is not None:
            return float(outv['peak_trigger'] or 0)
    except Exception:
        pass
    return 0.0


def _pulse_lfo_raw(phase):
    """Smooth 0→1→0 cosine ease over one division cycle."""
    return 0.5 - 0.5 * math.cos(2.0 * math.pi * float(phase))


def _pulse_holds_max_seconds():
    return 0.0


def _pulse_hold_chance():
    return 0.0


def _pulse_should_sustain(slot, pulse_index):
    chance = _pulse_hold_chance()
    if chance <= 0.0:
        return False
    if chance >= 1.0:
        return True
    rng = random.Random(int(pulse_index) * 9187 + int(slot) * 4243 + 17)
    return rng.random() < chance


def _pulse_flash_duration(interval):
    return min(PULSE_HOLD_FLASH_SEC, max(0.03, float(interval) * 0.35))


def _pulse_sustain_duration(slot, pulse_index):
    holds_sec = _pulse_holds_max_seconds()
    if holds_sec <= 0.0:
        return 0.0
    rng = random.Random(int(pulse_index) * 7919 + int(slot) * 104729 + 31337)
    lo = max(0.35, holds_sec * 0.55)
    hi = max(lo, holds_sec)
    return lo + rng.random() * (hi - lo)


def _pulse_hold_duration(slot, pulse_index, interval):
    if _pulse_holds_max_seconds() <= 0.0 or not _pulse_should_sustain(slot, pulse_index):
        return _pulse_flash_duration(interval)
    return _pulse_sustain_duration(slot, pulse_index)


def _pulse_slot_active(slot):
    s = _settings_op()
    if s is None:
        return False
    names = _pulse_slot_names(slot)
    try:
        return bool(getattr(s.par, names['active']).eval())
    except Exception:
        return False


def _pulse_slot_min_max(slot):
    s = _settings_op()
    if s is None:
        return PULSE_DEFAULT_MIN, PULSE_DEFAULT_MAX
    names = _pulse_slot_names(slot)
    try:
        lo = float(getattr(s.par, names['min']).eval())
    except Exception:
        lo = PULSE_DEFAULT_MIN
    try:
        hi = float(getattr(s.par, names['max']).eval())
    except Exception:
        hi = PULSE_DEFAULT_MAX
    lo = _clamp_pulse(lo, PULSE_RANGE_MIN, PULSE_RANGE_MAX)
    hi = _clamp_pulse(hi, PULSE_RANGE_MIN, PULSE_RANGE_MAX)
    return lo, hi


def _pulse_slot_output(slot, raw):
    lo, hi = _pulse_slot_min_max(slot)
    return _map_osc_value(raw, lo, hi)


def _pulse_slot_interval(slot):
    bpm = _pulse_bpm()
    if bpm <= 0.0:
        return None
    return (60.0 / bpm) * float(_pulse_slot_beats(slot))


def _pulse_now_seconds():
    try:
        return float(absTime.seconds)
    except Exception:
        pass
    try:
        t = op('/').time
        if t is not None:
            return float(t.seconds)
    except Exception:
        pass
    return 0.0


def _pulse_wall_seconds():
    try:
        import time as _time
        return float(_time.time())
    except Exception:
        return _pulse_now_seconds()


def _reset_pulse_sync():
    s = _settings_op()
    if s is None:
        return
    s.store('pulse_manual_origin', -1.0, search=False)
    for slot in range(1, PULSE_SLOTS + 1):
        s.store('pulse{}_last_index'.format(slot), -1, search=False)
        s.store('pulse{}_hold_until'.format(slot), 0.0, search=False)
        s.store('pulse{}_lfo_phase'.format(slot), -1.0, search=False)


def _pulse_engine_time():
    s = _settings_op()
    if s is None:
        return 0.0
    if _pulse_use_tempo() and _pulse_timeline_playing():
        return _pulse_now_seconds()
    origin = float(s.fetch('pulse_manual_origin', -1.0, search=False) or -1.0)
    wall = _pulse_wall_seconds()
    if origin < 0.0:
        s.store('pulse_manual_origin', wall, search=False)
        origin = wall
    return max(0.0, wall - origin)


def _set_pulse_par(name, value):
    s = _settings_op()
    if s is None:
        return
    try:
        par = getattr(s.par, name)
        try:
            par.readOnly = False
        except Exception:
            pass
        par.val = value
    except Exception:
        pass


def _send_pulse_slot_osc(slot, value=1.0):
    s = _settings_op()
    if s is None:
        return False
    osc = _ensure_pulse_osc_out()
    if osc is None:
        return False
    try:
        address = PULSE_DEFAULT_ADDRESSES.get(
            int(slot),
            '/sonomika/pulse{}'.format(int(slot)),
        )
        osc.par.address = _osc_ip()
        osc.par.port = int(_osc_port())
        osc.sendOSC(address, [float(value)])
        return True
    except Exception:
        return False


def _should_skip_pulse(slot, pulse_index):
    chance = _pulse_slot_skip_chance(slot)
    if chance <= 0.0:
        return False
    if chance >= 1.0:
        return True
    rng = random.Random(int(pulse_index) * 7919 + int(slot) * 104729)
    return rng.random() < chance


def _clear_pulse_slot_values():
    for slot in range(1, PULSE_SLOTS + 1):
        names = _pulse_slot_names(slot)
        _set_pulse_par(names['value'], _pulse_slot_output(slot, 0.0))


def _fire_pulse_slot(slot, pulse_index, now, interval):
    s = _settings_op()
    if s is None:
        return
    names = _pulse_slot_names(slot)
    if _should_skip_pulse(slot, pulse_index):
        _set_pulse_par(names['value'], _pulse_slot_output(slot, 0.0))
        return
    out_val = _pulse_slot_output(slot, 1.0)
    _set_pulse_par(names['value'], out_val)
    _send_pulse_slot_osc(slot, out_val)
    s.store(
        'pulse{}_hold_until'.format(slot),
        now + _pulse_hold_duration(slot, pulse_index, interval),
        search=False,
    )


def _update_pulse_slot_lfo(slot, now, interval):
    """Continuous eased oscillation between min and max."""
    s = _settings_op()
    if s is None:
        return
    names = _pulse_slot_names(slot)
    pulse_index = int(now / interval)
    phase = (float(now) / float(interval)) % 1.0
    if _should_skip_pulse(slot, pulse_index):
        _set_pulse_par(names['value'], _pulse_slot_output(slot, 0.0))
        s.store('pulse{}_lfo_phase'.format(slot), phase, search=False)
        return

    last_phase = float(s.fetch('pulse{}_lfo_phase'.format(slot), -1.0, search=False) or -1.0)
    raw = _pulse_lfo_raw(phase)
    val = _pulse_slot_output(slot, raw)
    _set_pulse_par(names['value'], val)
    if last_phase >= 0.0 and phase < last_phase:
        _send_pulse_slot_osc(slot, val)
    s.store('pulse{}_lfo_phase'.format(slot), phase, search=False)


def _update_pulse_slot_peak(slot, now, interval):
    """Fire this pulse slot on rising edge of Settings Out Peak Hit."""
    s = _settings_op()
    if s is None:
        return
    hit = _audio_peak_hit_level()
    prev = float(s.fetch('pulse{}_peak_prev'.format(slot), 0.0, search=False) or 0.0)
    s.store('pulse{}_peak_prev'.format(slot), hit, search=False)
    edge = 0.35
    if hit < edge or prev >= edge:
        return
    last = float(s.fetch('pulse{}_peak_last'.format(slot), -1e9, search=False) or -1e9)
    if (now - last) < 0.12:
        return
    hold_interval = interval if interval and interval > 0 else 0.25
    pulse_index = int(now * 1000.0) + int(slot) * 31
    _fire_pulse_slot(slot, pulse_index, now, hold_interval)
    s.store('pulse{}_peak_last'.format(slot), now, search=False)


def _update_pulse_slot_kick(slot, now, interval):
    """Fire this pulse slot on rising edge of Settings Out Kick."""
    s = _settings_op()
    if s is None:
        return
    kick = _audio_kick_level()
    prev = float(s.fetch('pulse{}_kick_prev'.format(slot), 0.0, search=False) or 0.0)
    s.store('pulse{}_kick_prev'.format(slot), kick, search=False)
    edge = 0.35
    if kick < edge or prev >= edge:
        return
    last = float(s.fetch('pulse{}_kick_last'.format(slot), -1e9, search=False) or -1e9)
    if (now - last) < 0.12:
        return
    hold_interval = interval if interval and interval > 0 else 0.25
    pulse_index = int(now * 1000.0) + int(slot) * 17
    _fire_pulse_slot(slot, pulse_index, now, hold_interval)
    s.store('pulse{}_kick_last'.format(slot), now, search=False)


def _update_pulse_slot(slot, now):
    s = _settings_op()
    if s is None:
        return
    names = _pulse_slot_names(slot)
    if not _pulse_slot_active(slot):
        _set_pulse_par(names['value'], _pulse_slot_output(slot, 0.0))
        return

    interval = _pulse_slot_interval(slot)
    kick_enabled = _pulse_slot_kick(slot)
    peak_enabled = _pulse_slot_peak(slot)

    # Audio-only slots still fire without needing BPM timeline divisions.
    if (kick_enabled or peak_enabled) and (interval is None or interval <= 0.0):
        interval = 0.25

    if interval is None or interval <= 0.0:
        if kick_enabled:
            _update_pulse_slot_kick(slot, now, 0.25)
        if peak_enabled:
            _update_pulse_slot_peak(slot, now, 0.25)
        if not kick_enabled and not peak_enabled:
            _set_pulse_par(names['value'], _pulse_slot_output(slot, 0.0))
        return

    if _pulse_slot_lfo(slot):
        _update_pulse_slot_lfo(slot, now, interval)
        if kick_enabled:
            _update_pulse_slot_kick(slot, now, interval)
        if peak_enabled:
            _update_pulse_slot_peak(slot, now, interval)
        return

    pulse_index = int(now / interval)
    last_index = int(s.fetch('pulse{}_last_index'.format(slot), -1, search=False) or -1)
    hold_until = float(s.fetch('pulse{}_hold_until'.format(slot), 0.0, search=False) or 0.0)

    if pulse_index > last_index:
        _fire_pulse_slot(slot, pulse_index, now, interval)
        s.store('pulse{}_last_index'.format(slot), int(pulse_index), search=False)
    elif now >= hold_until:
        kick_hold = float(s.fetch('pulse{}_hold_until'.format(slot), 0.0, search=False) or 0.0)
        if now >= kick_hold:
            _set_pulse_par(names['value'], _pulse_slot_output(slot, 0.0))

    if kick_enabled:
        _update_pulse_slot_kick(slot, now, interval)
    if peak_enabled:
        _update_pulse_slot_peak(slot, now, interval)


def update_pulse_engine(frame=None):
    s = _settings_op()
    if s is None:
        return False
    if not _pulse_active():
        _clear_pulse_slot_values()
        return False
    _ensure_pulse_master_slot()
    if _pulse_use_tempo() and not _pulse_timeline_playing():
        _clear_pulse_slot_values()
        return False

    now = _pulse_engine_time()
    for slot in range(1, PULSE_SLOTS + 1):
        _update_pulse_slot(slot, now)
    return True
