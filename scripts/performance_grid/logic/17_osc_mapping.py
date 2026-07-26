import json
import os

OSC_MAPPING_SLOTS = 8
GRID_OSC_DEFAULT_PREFIX = '/live'
DEFAULT_OSC_IP = '127.0.0.1'
MIDI_MAPPING_SLOTS = 32
MIDI_CC_MAPPING_SLOTS = 16
_MIDI_MAPPINGS = []
_MIDI_CC_MAPPINGS = []
_MIDI_MAPPINGS_LOADED = False
_MIDI_POLL_FP = None
_MIDI_EVENT_FP = None
_MIDI_EVENT_TS = 0.0
MIDI_DEVICE_TABLE = '/local/midi/device'
MIDI_TAKEOVER_MODES = ('none', 'pickup', 'valuescaling')
MIDI_TAKEOVER_LABELS = ('None', 'Pickup', 'Value Scaling')
MIDI_TAKEOVER_DEFAULT = 'valuescaling'
MIDI_TAKEOVER_PICKUP_EPS = 2.0 / 127.0
MIDI_TAKEOVER_SCALE_STEP = 0.22
MIDI_TAKEOVER_REARM_DELTA = 0.35
_MIDI_TAKEOVER_PICKED_UP = set()
_MIDI_TAKEOVER_LAST_NORM = {}
_MIDI_MENU_REFRESH_DEPTH = 0
_MIDI_NOTE_DEFER_ARMED = False
_MIDI_NOTE_DEFER_TARGET = None
_GRID_OSC_DEFER_ARMED = False
_GRID_OSC_DEFER_PAYLOAD = None
_GRID_OSC_ROUTING = False
PULSE_OSC_ADDRESS_PREFIX = '/sonomika/pulse'


def _midi_menu_refresh_active():
    return _MIDI_MENU_REFRESH_DEPTH > 0


def _as_menu_list(items):
    """Menu names/labels must be a list of strings — never list(a_str) (splits into chars)."""
    if items is None:
        return []
    if isinstance(items, str):
        return [items]
    if isinstance(items, (list, tuple)):
        return [str(x) for x in items]
    return [str(items)]


def _short_menu_label(text, limit=40):
    text = str(text or '').strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + '…'


def _apply_menu_options(par, names, labels=None, default=None, force=False):
    """Set menuNames/menuLabels as lists (never a bare string — splits per character in UI)."""
    if par is None:
        return
    names = [str(n) for n in _as_menu_list(names)]
    if not names:
        names = ['1']
    labels = [str(l) for l in _as_menu_list(labels if labels is not None else names)]
    if len(labels) != len(names):
        labels = list(names)
    if not force:
        try:
            cur_names = [str(n) for n in _as_menu_list(par.menuNames)]
            cur_labels = [str(l) for l in _as_menu_list(par.menuLabels)]
            if cur_names == names and cur_labels == labels:
                try:
                    cur = str(par.eval()).strip()
                    fallback = str(default if default is not None else names[0])
                    if cur not in names:
                        par.val = fallback
                except Exception:
                    pass
                return
        except Exception:
            pass
    try:
        par.menuNames = list(names)
        par.menuLabels = list(labels)
        # Assign twice — fixes Perform parameterCOMP showing generic Label 1/2/3.
        par.menuNames = list(names)
        par.menuLabels = list(labels)
        if default is not None:
            par.default = str(default)
    except Exception:
        pass
    try:
        cur = str(par.eval()).strip()
        fallback = str(default if default is not None else names[0])
        if cur not in names:
            par.val = fallback
    except Exception:
        pass


def _midi_device_menu_options():
    entries = _midi_mapper_entries()
    if not entries:
        return ['1'], ['Device 1 (MIDI Device Mapper)']
    names = []
    labels = []
    for did, in_name in entries:
        sid = _midi_mapper_id_str(did)
        names.append(sid)
        labels.append(_short_menu_label(in_name or 'Device {}'.format(sid), 52))
    return names, labels


# Legacy template stems -> current JSON filename (without .json).
_MIDI_TEMPLATE_ALIASES = {
    'move8x4': 'ableton_move_pad_grid',
    't0': 'ableton_move_pad_grid',
    '8x4': 'ableton_move_pad_grid',
    'pad_grid_8x4': 'ableton_move_pad_grid',
    'movecols': 'ableton_move_columns_scenes',
    'columns': 'ableton_move_columns_scenes',
    't1': 'ableton_move_columns_scenes',
    'cols': 'ableton_move_columns_scenes',
    'columns_scenes': 'ableton_move_columns_scenes',
    'columns_scenes_knobs_2_9': 'ableton_move_columns_scenes_knobs_controllers',
}


def _midi_template_folder_candidates():
    try:
        base = project.folder
    except Exception:
        base = ''
    candidates = []
    if base:
        candidates.append(os.path.join(base, 'SonomikaTD', 'templates', 'midi'))
        candidates.append(os.path.join(base, 'templates', 'midi'))
    try:
        candidates.append(os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'midi'))
    except Exception:
        pass
    seen = set()
    out = []
    for folder in candidates:
        folder = os.path.normpath(folder)
        if folder in seen:
            continue
        seen.add(folder)
        out.append(folder)
    return out


def _midi_template_label(stem, path=None):
    stem = str(stem or '').strip()
    return _short_menu_label(stem.replace('_', ' ').title(), 52)


def _midi_template_menu_options():
    names = _midi_template_names()
    labels = [_midi_template_label(n, path) for n, path in zip(names, _midi_template_files())]
    return names, labels


def _midi_default_template_name():
    names = _midi_template_names()
    return names[0] if names else ''


def _refresh_midi_device_menu():
    s = _settings_op()
    if s is None:
        return
    try:
        par = s.par.Mididevice
    except AttributeError:
        return
    if getattr(par, 'style', '') != 'Menu':
        return
    names, labels = _midi_device_menu_options()
    _apply_menu_options(par, names, labels)


def _refresh_midi_template_menu(force=False):
    s = _settings_op()
    if s is None:
        return False
    try:
        par = s.par.Miditemplate
    except AttributeError:
        return False
    if getattr(par, 'style', '') != 'Menu':
        return False
    try:
        cur = str(par.eval()).strip()
    except Exception:
        cur = None
    names, labels = _midi_template_menu_options()
    default = cur if cur in names else None
    _apply_menu_options(par, names, labels, default=default, force=force)
    return True


def refresh_midi_template_list():
    """Rescan templates/midi, refresh Template menu + Perform panel; stay on Midi tab."""
    global _MIDI_MENU_REFRESH_DEPTH
    try:
        _pin_settings_tab('Midi')
    except Exception:
        pass
    _MIDI_MENU_REFRESH_DEPTH += 1
    try:
        _refresh_midi_template_menu(force=True)
    finally:
        _MIDI_MENU_REFRESH_DEPTH = max(0, _MIDI_MENU_REFRESH_DEPTH - 1)
    try:
        idx = _settings_tab_index('Midi')
        settings = _settings_op()
        if idx is not None and settings is not None:
            try:
                settings.par.pageindex = idx
            except Exception:
                pass
    except Exception:
        pass
    try:
        _nudge_settings_params_panel('Midi')
    except Exception:
        pass
    return True


def _refresh_midi_takeover_menu():
    s = _settings_op()
    if s is None:
        return
    try:
        par = s.par.Miditakeovermode
    except AttributeError:
        return
    if getattr(par, 'style', '') != 'Menu':
        return
    _apply_menu_options(
        par,
        list(MIDI_TAKEOVER_MODES),
        list(MIDI_TAKEOVER_LABELS),
        default=MIDI_TAKEOVER_DEFAULT,
    )


def _normalize_template_stem(name):
    name = str(name or '').strip()
    if not name or len(name) <= 2:
        return _midi_default_template_name()
    name = _MIDI_TEMPLATE_ALIASES.get(name, name)
    available = _midi_template_names()
    if name in available:
        return name
    return _midi_default_template_name()


def _menu_names_char_split(par):
    """Menu with menuNames set to a string splits into one row per character in parameterCOMP."""
    try:
        if getattr(par, 'style', '') != 'Menu':
            return False
        names = par.menuNames
        if isinstance(names, str):
            return len(names) > 1
        if isinstance(names, (list, tuple)) and len(names) >= 2:
            singles = sum(1 for n in names if len(str(n)) <= 1)
            return singles >= max(2, len(names) // 2)
    except Exception:
        pass
    return False


def _midi_menus_corrupt():
    """Detect broken menus (string menuNames) or pre-dropdown Int/Str layout."""
    s = _settings_op()
    if s is None:
        return True
    try:
        getattr(s.par, 'Midideviceid')
        return True
    except AttributeError:
        pass
    try:
        getattr(s.par, 'Midideviceinfo')
        return True
    except AttributeError:
        pass
    for par in list(s.customPars):
        try:
            pg = par.page.name if hasattr(par.page, 'name') else str(par.page)
        except Exception:
            continue
        if pg != 'Midi':
            continue
        if par.name in ('Mididevice', 'Miditemplate', 'Miditakeovermode') and _menu_names_char_split(par):
            return True
    try:
        dev = s.par.Mididevice
        tpl = s.par.Miditemplate
        takeover = s.par.Miditakeovermode
    except AttributeError:
        return True
    if (
        getattr(dev, 'style', '') != 'Menu'
        or getattr(tpl, 'style', '') != 'Menu'
        or getattr(takeover, 'style', '') != 'Menu'
    ):
        return True
    if (
        _menu_names_char_split(dev)
        or _menu_names_char_split(tpl)
        or _menu_names_char_split(takeover)
    ):
        return True
    try:
        takeover_labels = [str(x).lower() for x in takeover.menuLabels]
        if any(lbl.startswith('label') for lbl in takeover_labels):
            return True
    except Exception:
        pass
    return False


def _osc_callback_text():
    return _read_embedded_dat_validated('osc_callbacks.py', 'onReceiveOSC')


def _midi_callback_text():
    return _read_embedded_dat_validated('midi_callbacks.py', 'onReceiveMIDI')


def _midi_table_exec_text():
    return _read_embedded_dat_validated('midi_table_exec.py', 'onTableChange')


def _destroy_legacy_settings_dats(s=None):
    """Remove stale duplicate callback DATs from older /settings layouts."""
    if s is None:
        s = _settings_op()
    if s is None:
        return
    for name in ('osc_in_callbacks', 'midi_in_callbacks'):
        try:
            s.op(name).destroy()
        except Exception:
            pass


def _ensure_midi_table_exec(midi):
    s = _settings_op()
    if s is None or midi is None:
        return None
    de = s.op('midi_table_exec')
    if de is None:
        try:
            de = s.create('datexecuteDAT', 'midi_table_exec')
        except Exception:
            return None
    try:
        text = _midi_table_exec_text()
        if _callback_dat_valid(text, 'onTableChange') or not str(de.text or '').strip():
            de.text = text
        de.par.language = 'python'
        de.par.dat = midi
        # Callbacks handle MIDI; table exec duplicated note events and could crash TD.
        de.par.tablechange = False
        de.par.active = False
    except Exception:
        pass
    return de


def _set_if_par(node, name, value):
    try:
        getattr(node.par, name).val = value
        return True
    except Exception:
        return False


def _callback_dat_valid(text, marker):
    text = str(text or '')
    return bool(text.strip()) and marker in text


def _apply_callback_dat_text(cb, text, marker, label):
    """Write callback DAT text without wiping a working script on load failure."""
    if cb is None:
        return False
    existing = str(cb.text or '')
    new_text = str(text or '')
    if _callback_dat_valid(new_text, marker):
        if existing.strip() != new_text.strip():
            cb.text = new_text
        try:
            cb.par.language = 'python'
        except Exception:
            pass
        return True
    if _callback_dat_valid(existing, marker):
        return True
    if existing.strip():
        print('OSC: {} DAT is invalid; try Reload Scripts.'.format(label))
    else:
        print('OSC: could not load {}; OSC/MIDI mapping will not run.'.format(label))
    return False


def _ensure_osc_input():
    s = _settings_op()
    if s is None:
        return None
    _destroy_legacy_settings_dats(s)
    try:
        clear_embedded_dat_cache(('osc_callbacks.py',))
    except Exception:
        pass
    cb = s.op('osc_callbacks')
    if cb is None:
        cb = s.create('textDAT', 'osc_callbacks')
    _apply_callback_dat_text(cb, _osc_callback_text(), 'onReceiveOSC', 'osc_callbacks')
    osc = s.op('osc_in')
    if osc is None:
        try:
            osc = s.create('oscinDAT', 'osc_in')
        except Exception as exc:
            print('OSC: could not create oscinDAT:', exc)
            return None
    _set_if_par(osc, 'active', False)
    _set_if_par(osc, 'callbacks', cb)
    _set_if_par(osc, 'executeloc', 'callbacks')
    _set_if_par(osc, 'port', int(_osc_port()))
    _set_if_par(osc, 'localaddress', _osc_ip())
    _set_if_par(osc, 'active', bool(_osc_active()))
    return osc


def _ensure_midi_input():
    s = _settings_op()
    if s is None:
        return None
    _destroy_legacy_settings_dats(s)
    try:
        clear_embedded_dat_cache(('midi_callbacks.py', 'midi_table_exec.py'))
    except Exception:
        pass
    cb = s.op('midi_callbacks')
    if cb is None:
        cb = s.create('textDAT', 'midi_callbacks')
    _apply_callback_dat_text(cb, _midi_callback_text(), 'onReceiveMIDI', 'midi_callbacks')
    midi = s.op('midi_in')
    if midi is None:
        try:
            midi = s.create('midiinDAT', 'midi_in')
        except Exception as exc:
            print('MIDI: could not create midiinDAT:', exc)
            return None
    _set_if_par(midi, 'callbacks', cb)
    _set_if_par(midi, 'executeloc', 'callbacks')
    _set_if_par(midi, 'device', MIDI_DEVICE_TABLE)
    try:
        was_active = bool(midi.par.active.eval())
        midi.par.active = False
        midi.par.active = was_active
    except Exception:
        _set_if_par(midi, 'active', True)
    try:
        midi.par.clamp = True
        midi.par.maxlines = 64
        midi.par.filter = False
    except Exception:
        pass
    _ensure_midi_table_exec(midi)
    return midi


def _osc_active():
    s = _settings_op()
    if s is None:
        return False
    found = False
    active = False
    for name in ('Oscactive', 'Gridoscactive'):
        try:
            found = True
            active = active or bool(getattr(s.par, name).eval())
        except Exception:
            pass
    return active if found else True


def _osc_port():
    s = _settings_op()
    if s is None:
        return 7000
    for name in ('Oscport', 'Gridoscport'):
        try:
            return max(1, min(65535, int(float(getattr(s.par, name).eval()))))
        except Exception:
            pass
    return 7000


def _osc_ip():
    """Local NIC IP for oscinDAT localaddress; blank = all interfaces."""
    s = _settings_op()
    if s is None:
        return ''
    for name in ('Oscip', 'Gridoscip'):
        try:
            ip = str(getattr(s.par, name).eval()).strip()
            if ip:
                return ip
        except Exception:
            pass
    return DEFAULT_OSC_IP


def _osc_settings_page(name):
    s = _settings_op()
    if s is None:
        return None
    if name == SETTINGS_TAB_GRID_OSC:
        names = SETTINGS_TAB_GRID_OSC_LEGACY + (SETTINGS_TAB_GRID_OSC,)
    elif name == SETTINGS_TAB_PERF:
        names = ('Performance', SETTINGS_TAB_PERF)
    else:
        names = (name,)
    for pg in s.customPages:
        try:
            if pg.name in names:
                return pg
        except Exception:
            pass
    return None


def _osc_page_par_order():
    names = ['Oscactive', 'Oscport', 'Oscip', 'Osclastaddress', 'Osclastvalue']
    for idx in range(1, OSC_MAPPING_SLOTS + 1):
        names.extend([
            'Osc{}address'.format(idx),
            'Osc{}min'.format(idx),
            'Osc{}max'.format(idx),
            'Osc{}value'.format(idx),
        ])
    return names


def _grid_osc_page_par_order():
    return [
        'Gridoscactive',
        'Gridoscport',
        'Gridoscip',
        'Gridoscprefix',
        'Gridoscnote',
        'Gridoscnote2',
        'Gridosclastaddress',
    ]


def _par_page_name(par):
    try:
        page = par.page
        return page.name if hasattr(page, 'name') else str(page)
    except Exception:
        return ''


def _reorder_custom_page_pars(page_name, ordered_names):
    s = _settings_op()
    if s is None:
        return
    for index, name in enumerate(ordered_names):
        try:
            par = getattr(s.par, name)
        except AttributeError:
            continue
        if _par_page_name(par) != page_name:
            continue
        try:
            par.order = float(index)
        except Exception:
            pass


def _ensure_osc_settings_layout():
    """Create missing network pars and fix tab order (IP directly under Port)."""
    s = _settings_op()
    if s is None:
        return
    _migrate_settings_tab_names(s)
    osc_page = _osc_settings_page('OSC')
    if osc_page is not None:
        try:
            getattr(s.par, 'Oscip')
        except AttributeError:
            try:
                p = osc_page.appendStr('Oscip', label='IP')
                p.val = DEFAULT_OSC_IP
                p.readOnly = True
            except Exception:
                pass
        _reorder_custom_page_pars('OSC', _osc_page_par_order())
    grid_page = _osc_settings_page(SETTINGS_TAB_GRID_OSC)
    if grid_page is not None:
        try:
            if grid_page.name in SETTINGS_TAB_GRID_OSC_LEGACY:
                grid_page.name = SETTINGS_TAB_GRID_OSC
        except Exception:
            pass
    if grid_page is not None:
        try:
            getattr(s.par, 'Gridoscport')
        except AttributeError:
            try:
                p = grid_page.appendInt('Gridoscport', label='OSC Port')
                p.default = int(_osc_port())
                p.val = int(_osc_port())
                p.min = 1
                p.max = 65535
            except Exception:
                pass
        try:
            getattr(s.par, 'Gridoscip')
        except AttributeError:
            try:
                p = grid_page.appendStr('Gridoscip', label='IP')
                p.val = _osc_ip()
                p.readOnly = True
            except Exception:
                pass
        _reorder_custom_page_pars(SETTINGS_TAB_GRID_OSC, _grid_osc_page_par_order())
    for name in ('Oscip', 'Gridoscip'):
        try:
            par = getattr(s.par, name)
            if not str(par.eval()).strip():
                par.val = DEFAULT_OSC_IP
        except Exception:
            pass
    try:
        ip = str(s.par.Oscip.eval()).strip() or DEFAULT_OSC_IP
        s.par.Oscip = ip
        s.par.Gridoscip = ip
    except Exception:
        pass


def configure_osc_input():
    _ensure_osc_settings_layout()
    osc = _ensure_osc_input()
    if osc is None:
        return False
    try:
        osc.par.active = False
    except Exception:
        pass
    _set_if_par(osc, 'port', int(_osc_port()))
    _set_if_par(osc, 'localaddress', _osc_ip())
    _set_if_par(osc, 'active', bool(_osc_active()))
    return True


def heal_osc_callbacks_if_needed():
    """Re-wire OSC callbacks if the DAT was cleared or never loaded."""
    s = _settings_op()
    if s is None:
        return False
    cb = s.op('osc_callbacks')
    osc = s.op('osc_in')
    needs_heal = cb is None or not _callback_dat_valid(cb.text, 'onReceiveOSC')
    if not needs_heal and osc is not None:
        try:
            wired = osc.par.callbacks.eval()
            needs_heal = wired is None or wired != cb
        except Exception:
            needs_heal = True
    if not needs_heal:
        return True
    return bool(configure_osc_input())


def _ensure_midi_tab_pars():
    """Rebuild simplified Midi tab from TouchDesigner MIDI Device Mapper."""
    s = _settings_op()
    if s is None:
        return
    midi_page = None
    for pg in s.customPages:
        if pg.name == 'Midi':
            midi_page = pg
            break
    if midi_page is None:
        midi_page = s.appendCustomPage('Midi')
    midi_saved = {}
    for par in list(s.customPars):
        try:
            if par.page == midi_page.name:
                midi_saved[par.name] = par.eval()
                par.destroy()
        except Exception:
            pass
    saved_id = _midi_mapper_id_str(
        midi_saved.get('Mididevice', midi_saved.get('Midideviceid', '1'))
    )
    saved_template = _normalize_template_stem(midi_saved.get('Miditemplate', _midi_default_template_name()))
    saved_takeover = str(
        midi_saved.get('Miditakeovermode', MIDI_TAKEOVER_DEFAULT)
    ).strip().lower().replace(' ', '').replace('_', '')
    if saved_takeover not in MIDI_TAKEOVER_MODES:
        saved_takeover = MIDI_TAKEOVER_DEFAULT
    dev_names, dev_labels = _midi_device_menu_options()
    default_id = saved_id if saved_id in dev_names else dev_names[0]
    try:
        dev = midi_page.appendMenu('Mididevice', label='MIDI Device')
        _apply_menu_options(dev, dev_names, dev_labels, default=default_id)
    except Exception:
        pass
    tmpl_names, tmpl_labels = _midi_template_menu_options()
    default_tpl = saved_template if saved_template in tmpl_names else (tmpl_names[0] if tmpl_names else '')
    try:
        tpl = midi_page.appendMenu('Miditemplate', label='Template')
        _apply_menu_options(tpl, tmpl_names, tmpl_labels, default=default_tpl)
    except Exception:
        pass
    try:
        midi_page.appendPulse('Midirefreshtemplates', label='Refresh Templates')
    except Exception:
        pass
    default_takeover = saved_takeover if saved_takeover in MIDI_TAKEOVER_MODES else MIDI_TAKEOVER_DEFAULT
    try:
        takeover = midi_page.appendMenu('Miditakeovermode', label='Takeover Mode')
        _apply_menu_options(
            takeover,
            list(MIDI_TAKEOVER_MODES),
            list(MIDI_TAKEOVER_LABELS),
            default=default_takeover,
        )
        takeover.val = default_takeover
    except Exception:
        pass
    try:
        p = midi_page.appendStr('Midireceived', label='Received')
        p.val = '(waiting)'
        p.readOnly = False
        p.mode = ParMode.CONSTANT
    except Exception:
        pass
    order = (
        'Mididevice', 'Miditemplate', 'Midirefreshtemplates', 'Miditakeovermode',
        'Midireceived',
    )
    for index, name in enumerate(order):
        try:
            getattr(s.par, name).order = float(index)
        except Exception:
            pass


def _remove_legacy_midi_mapping_par():
    s = _settings_op()
    if s is None:
        return
    try:
        s.par.Midimapping.destroy()
    except Exception:
        pass
    try:
        s.par.Midivalue.destroy()
    except Exception:
        pass


def _ensure_midi_refresh_pulse():
    """Add Refresh Templates pulse on existing Midi tabs without full rebuild."""
    s = _settings_op()
    if s is None:
        return
    try:
        getattr(s.par, 'Midirefreshtemplates')
        return
    except AttributeError:
        pass
    midi_page = None
    for pg in s.customPages:
        if pg.name == 'Midi':
            midi_page = pg
            break
    if midi_page is None:
        return
    try:
        midi_page.appendPulse('Midirefreshtemplates', label='Refresh Templates')
    except Exception:
        return
    order = {
        'Mididevice': 0,
        'Miditemplate': 1,
        'Midirefreshtemplates': 2,
        'Miditakeovermode': 3,
        'Midireceived': 4,
    }
    for name, index in order.items():
        try:
            getattr(s.par, name).order = float(index)
        except Exception:
            pass


def _midi_tab_needs_build():
    s = _settings_op()
    if s is None:
        return False
    for name in ('Mididevice', 'Miditemplate', 'Miditakeovermode', 'Midireceived'):
        try:
            getattr(s.par, name)
        except Exception:
            return True
    return _midi_menus_corrupt()


def reset_midi_defaults_for_new_set():
    """Blank performance set: smooth MIDI knob takeover by default."""
    s = _settings_op()
    if s is None:
        return False
    try:
        par = s.par.Miditakeovermode
    except AttributeError:
        try:
            configure_midi_input()
            par = s.par.Miditakeovermode
        except Exception:
            return False
    try:
        _refresh_midi_takeover_menu()
        par.val = MIDI_TAKEOVER_DEFAULT
        par.default = MIDI_TAKEOVER_DEFAULT
    except Exception:
        return False
    try:
        clear_midi_takeover_sync()
    except Exception:
        pass
    return True


def configure_midi_input():
    global _MIDI_MAPPINGS_LOADED
    try:
        clear_map_dial_midi_blocks()
        clear_map_dial_midi_sync()
        clear_midi_takeover_sync()
    except Exception:
        pass
    midi = _ensure_midi_input()
    if midi is None:
        return False
    s = _settings_op()
    if _midi_tab_needs_build() or _midi_menus_corrupt():
        _ensure_midi_tab_pars()
    else:
        _ensure_midi_refresh_pulse()
    _remove_legacy_midi_mapping_par()
    _refresh_midi_device_menu()
    _refresh_midi_template_menu()
    _refresh_midi_takeover_menu()
    _apply_midi_mapper_id(midi)
    apply_midi_template()
    try:
        _refresh_settings_params_panel()
    except Exception:
        pass
    try:
        midi.par.active = True
    except Exception:
        pass
    return True


def _midi_mapper_id_str(raw):
    try:
        if isinstance(raw, (list, tuple)):
            raw = raw[0] if raw else ''
        return str(int(float(raw)))
    except Exception:
        return str(raw or '').strip()


def _midi_mapper_id():
    s = _settings_op()
    if s is None:
        return 1
    try:
        return max(0, min(127, int(float(_midi_mapper_id_str(s.par.Mididevice.eval())))))
    except Exception:
        pass
    try:
        return max(0, min(127, int(float(s.par.Midideviceid.eval()))))
    except Exception:
        return 1


def _table_col_index(tbl, names, default=0):
    headers = {}
    try:
        for c in range(tbl.numCols):
            headers[str(tbl[0, c]).strip().lower()] = c
    except Exception:
        return default
    for name in names:
        key = name.lower()
        if key in headers:
            return headers[key]
    return default


def _midi_mapper_entries():
    entries = []
    try:
        tbl = op(MIDI_DEVICE_TABLE)
    except Exception:
        tbl = None
    if tbl is None or tbl.numRows < 2:
        return entries
    id_col = _table_col_index(tbl, ('id',), 0)
    in_col = _table_col_index(tbl, ('in', 'in device', 'indevice', 'input'), 1)
    for r in range(1, tbl.numRows):
        try:
            did = str(tbl[r, id_col]).strip()
            if not did:
                continue
            in_name = str(tbl[r, in_col]).strip() if in_col < tbl.numCols else ''
            entries.append((did, in_name or 'Device {}'.format(did)))
        except Exception:
            pass
    return entries


def _apply_midi_mapper_id(midi):
    device_id = _midi_mapper_id()
    try:
        _set_if_par(midi, 'device', MIDI_DEVICE_TABLE)
        midi.par.id = str(device_id)
    except Exception:
        return False
    return True


def _midi_table_cell(tbl, row, names, default_col=0):
    for name in names:
        try:
            return tbl[row, name]
        except Exception:
            pass
    try:
        return tbl[row, default_col]
    except Exception:
        return ''


def _midi_in_has_header(midi):
    try:
        return str(midi[0, 0]).strip().lower() == 'message'
    except Exception:
        return False


def _poll_midi_in_table():
    """Fallback when MIDI callbacks are unavailable (normally unused)."""
    global _MIDI_POLL_FP
    s = _settings_op()
    if s is None:
        return
    midi = s.op('midi_in')
    if midi is None:
        return
    try:
        rows = int(midi.numRows)
    except Exception:
        return
    first_data = 1 if _midi_in_has_header(midi) else 0
    if rows <= first_data:
        return
    row = rows - 1
    try:
        message = str(_midi_table_cell(midi, row, ('message',), 0))
        channel = str(_midi_table_cell(midi, row, ('channel',), 2))
        index = str(_midi_table_cell(midi, row, ('index',), 3))
        value = str(_midi_table_cell(midi, row, ('value',), 4))
        fp = _midi_event_fingerprint(message, channel, index, value)
    except Exception:
        return
    if fp == _MIDI_POLL_FP:
        return
    _MIDI_POLL_FP = fp
    _handle_midi_message(message, channel, index, value, None)


def _midi_templates_folder():
    """Primary templates folder (for docs / mkdir); scan uses all candidates."""
    for folder in _midi_template_folder_candidates():
        if os.path.isdir(folder):
            return folder
    folder = os.path.normpath(
        _midi_template_folder_candidates()[0]
        if _midi_template_folder_candidates()
        else os.path.join('templates', 'midi')
    )
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        pass
    return folder


def _midi_template_files():
    by_stem = {}
    for folder in _midi_template_folder_candidates():
        if not os.path.isdir(folder):
            continue
        try:
            for name in os.listdir(folder):
                if not name.lower().endswith('.json'):
                    continue
                path = os.path.join(folder, name)
                stem = os.path.splitext(name)[0]
                prev = by_stem.get(stem)
                if prev is None or os.path.getmtime(path) >= os.path.getmtime(prev):
                    by_stem[stem] = path
        except Exception:
            pass
    return [by_stem[k] for k in sorted(by_stem.keys())]


def _midi_template_names():
    return [os.path.splitext(os.path.basename(path))[0] for path in _midi_template_files()]


def _midi_template_path(name):
    name = _normalize_template_stem(name)
    if not name or name == 'None':
        return ''
    for path in _midi_template_files():
        stem = os.path.splitext(os.path.basename(path))[0]
        if name == stem:
            return path
    return ''


def apply_midi_template(name=None):
    global _MIDI_MAPPINGS, _MIDI_CC_MAPPINGS, _MIDI_MAPPINGS_LOADED
    s = _settings_op()
    if name is None and s is not None:
        try:
            name = str(s.par.Miditemplate.eval()).strip()
        except Exception:
            name = _midi_default_template_name()
    name = _normalize_template_stem(name)
    path = _midi_template_path(name)
    if not path:
        return False
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception:
        return False
    mappings = data.get('mappings') if isinstance(data, dict) else data
    if not isinstance(mappings, list):
        return False
    loaded = []
    loaded_cc = []
    for item in mappings:
        if not isinstance(item, dict):
            continue
        target = str(item.get('target', '')).strip()
        if not target:
            continue
        note = str(item.get('note', '')).strip()
        cc = str(item.get('cc', item.get('controller', ''))).strip()
        ch = str(item.get('channel', '')).strip()
        if note and len(loaded) < MIDI_MAPPING_SLOTS:
            loaded.append({'note': note, 'target': target, 'channel': ch})
        elif cc and len(loaded_cc) < MIDI_CC_MAPPING_SLOTS:
            entry = {'cc': cc, 'target': target, 'channel': ch}
            if isinstance(item, dict):
                if 'min' in item:
                    entry['min'] = item['min']
                if 'max' in item:
                    entry['max'] = item['max']
            loaded_cc.append(entry)
    cc_list = data.get('cc_mappings') if isinstance(data, dict) else None
    if isinstance(cc_list, list):
        for item in cc_list:
            if len(loaded_cc) >= MIDI_CC_MAPPING_SLOTS:
                break
            if not isinstance(item, dict):
                continue
            cc = str(item.get('cc', item.get('controller', ''))).strip()
            target = str(item.get('target', '')).strip()
            if cc and target:
                entry = {
                    'cc': cc,
                    'target': target,
                    'channel': str(item.get('channel', '')).strip(),
                }
                if 'min' in item:
                    entry['min'] = item['min']
                if 'max' in item:
                    entry['max'] = item['max']
                loaded_cc.append(entry)
    _MIDI_MAPPINGS = loaded
    _MIDI_CC_MAPPINGS = loaded_cc[:MIDI_CC_MAPPING_SLOTS]
    _MIDI_MAPPINGS_LOADED = True
    return True


def _set_osc_status(address, value):
    s = _settings_op()
    if s is None:
        return
    try:
        s.par.Osclastaddress = _normalize_osc_address(address)
        if isinstance(value, (list, tuple)):
            s.par.Osclastvalue = ', '.join(str(v) for v in value)
        else:
            s.par.Osclastvalue = str(value)
    except Exception:
        pass


def _normalize_osc_address(address):
    address = str(address or '').strip()
    if address and not address.startswith('/'):
        address = '/' + address
    return address


def _osc_mapping(idx):
    s = _settings_op()
    if s is None:
        return None
    try:
        address = _normalize_osc_address(getattr(s.par, 'Osc{}address'.format(idx)).eval())
        out_min = float(getattr(s.par, 'Osc{}min'.format(idx)).eval())
        out_max = float(getattr(s.par, 'Osc{}max'.format(idx)).eval())
    except Exception:
        return None
    if not address:
        return None
    return {
        'enabled': True,
        'address': address,
        'min': out_min,
        'max': out_max,
    }


def _map_osc_value(raw, out_min, out_max):
    try:
        v = float(raw)
    except Exception:
        return raw
    lo = float(out_min)
    hi = float(out_max)
    return lo + (hi - lo) * v


def _set_osc_slot_value(idx, value):
    s = _settings_op()
    if s is None:
        return
    try:
        par = getattr(s.par, 'Osc{}value'.format(idx))
        try:
            par.readOnly = False
        except Exception:
            pass
        try:
            par.mode = ParMode.CONSTANT
        except Exception:
            pass
        par.val = value
    except Exception:
        pass


def _grid_osc_format_shared_note(prefix=None, num_cols=None, max_show=12):
    """UI hint: shared/simple mode is one OSC address per column."""
    prefix = str(prefix or GRID_OSC_DEFAULT_PREFIX).strip().rstrip('/')
    if not prefix.startswith('/'):
        prefix = '/' + prefix
    try:
        ncols = int(num_cols) if num_cols is not None else _num_cols()
    except Exception:
        ncols = max_show
    ncols = max(1, min(ncols, max_show))
    addrs = ['{}/col{}'.format(prefix, c) for c in range(1, ncols + 1)]
    return '  '.join(addrs)


def _grid_osc_format_pairs_note(prefix=None, num_layers=None, max_show=4):
    """UI hint: advanced mode — colN sets column, Ln assigns that row."""
    prefix = str(prefix or GRID_OSC_DEFAULT_PREFIX).strip().rstrip('/')
    if not prefix.startswith('/'):
        prefix = '/' + prefix
    try:
        nlayers = int(num_layers) if num_layers is not None else _num_layers()
    except Exception:
        nlayers = max_show
    nlayers = max(1, min(nlayers, max_show))
    # Example: col1_L2_col2_L4 → L2 plays col1, L4 plays col2, …
    demo_layers = [2, 4, 2, 4]
    parts = []
    for col in range(1, nlayers + 1):
        parts.append('col{}'.format(col))
        label = demo_layers[(col - 1) % len(demo_layers)]
        if label <= nlayers:
            parts.append('L{}'.format(label))
    return prefix + '/' + '_'.join(parts)


def _grid_osc_active():
    s = _settings_op()
    if s is None:
        return False
    try:
        return bool(s.par.Gridoscactive.eval())
    except Exception:
        return True


def _grid_osc_prefix():
    s = _settings_op()
    if s is None:
        return GRID_OSC_DEFAULT_PREFIX
    try:
        prefix = str(s.par.Gridoscprefix.eval()).strip()
        return prefix or GRID_OSC_DEFAULT_PREFIX
    except Exception:
        return GRID_OSC_DEFAULT_PREFIX


def _grid_osc_threshold():
    return 0.5


def _set_grid_osc_status(address):
    s = _settings_op()
    if s is None:
        return
    try:
        s.par.Gridosclastaddress = str(address)
    except Exception:
        pass


def _grid_osc_value_on(args):
    raw = args[0] if args else 1.0
    try:
        return float(raw) >= _grid_osc_threshold(), raw
    except Exception:
        return bool(raw), raw


def _grid_osc_col_from_token(token):
    token = str(token).strip().lower()
    if not token.startswith('col'):
        return None
    digits = ''.join(ch for ch in token[3:] if ch.isdigit())
    if not digits:
        return None
    try:
        return max(1, min(_num_cols(), int(digits)))
    except Exception:
        return None


def _grid_osc_layer_from_token(token):
    token = str(token).strip().upper()
    if not token.startswith('L'):
        return None
    digits = ''.join(ch for ch in token[1:] if ch.isdigit())
    if not digits:
        return None
    try:
        label_idx = int(digits)
        if label_idx < 1 or label_idx > _num_layers():
            return None
        return _num_layers() - label_idx + 1
    except Exception:
        return None


def _grid_osc_pairs_from_parts(parts):
    pairs = []
    current_col = None
    pending_layer = None
    for part in parts:
        col = _grid_osc_col_from_token(part)
        layer = _grid_osc_layer_from_token(part)
        if col is not None:
            current_col = col
            if pending_layer is not None:
                pairs.append((pending_layer, current_col))
                pending_layer = None
            continue
        if layer is not None:
            if current_col is not None:
                pairs.append((layer, current_col))
            else:
                pending_layer = layer
    return pairs


def _parse_grid_osc_address(address):
    prefix = _grid_osc_prefix().strip().rstrip('/')
    if prefix and not prefix.startswith('/'):
        prefix = '/' + prefix
    address = str(address).strip()
    if address and not address.startswith('/'):
        address = '/' + address
    if prefix and not address.startswith(prefix + '/'):
        return None, [], []
    tail = address[len(prefix):].strip('/') if prefix else address.strip('/')
    if not tail:
        return None, [], []
    parts = []
    for chunk in tail.replace('__', '_').replace('-', '_').split('_'):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    pairs = _grid_osc_pairs_from_parts(parts)
    col = None
    layers = []
    for part in parts:
        if col is None:
            col = _grid_osc_col_from_token(part)
            if col is not None:
                continue
        layer = _grid_osc_layer_from_token(part)
        if layer is not None and layer not in layers:
            layers.append(layer)
    return col, layers, pairs


def _grid_osc_is_simple_shared(col, layers, pairs):
    """True when address is only prefix/colN (e.g. /live/col1) — all layers -> column."""
    return col is not None and not pairs and not layers


def _grid_osc_should_trigger(address, args, col, layers, pairs):
    """Simple column addresses trigger on bang or value>=threshold; ignore explicit 0 release."""
    on, _raw = _grid_osc_value_on(args)
    if on:
        return True
    if _grid_osc_is_simple_shared(col, layers, pairs) and not args:
        return True
    return False


def _grid_osc_routing_active():
    return bool(_GRID_OSC_ROUTING)


def _apply_grid_osc_action_immediate(col, layers, pairs):
    """Column/layer composition routing (must not run inside oscinDAT callback)."""
    global _GRID_OSC_ROUTING
    _GRID_OSC_ROUTING = True
    try:
        if _grid_osc_is_simple_shared(col, layers, pairs):
            composition_select_column(col)
        elif pairs:
            for layer, pair_col in pairs:
                composition_assign_layer_cell(layer, pair_col, toggle=False)
        elif layers:
            for layer in layers:
                composition_assign_layer_cell(layer, col, toggle=False)
        else:
            composition_select_column(col)
        return True
    finally:
        _GRID_OSC_ROUTING = False


def _defer_grid_osc_ui_refresh(layer=None, col=None):
    """Match UI clicks: switch composition now, repaint panels next frame."""
    r = _root()
    if r is None:
        return

    def _ui():
        try:
            _refresh_ui()
            if layer is not None and col is not None:
                _update_cell_params_ui(int(layer), int(col))
            _open_output()
        except Exception:
            pass

    if not global_transport_playing():
        _ui()
        return
    if not _defer_run(_ui, delayFrames=1, fromOP=r):
        _ui()


def _defer_grid_osc_action(col, layers, pairs, address):
    """Leave oscin callback immediately; apply routing same frame, UI next frame."""
    global _GRID_OSC_DEFER_ARMED, _GRID_OSC_DEFER_PAYLOAD
    _GRID_OSC_DEFER_PAYLOAD = (col, layers, pairs, str(address or ''))
    if _GRID_OSC_DEFER_ARMED:
        return True
    _GRID_OSC_DEFER_ARMED = True

    def _run():
        global _GRID_OSC_DEFER_ARMED, _GRID_OSC_DEFER_PAYLOAD
        _GRID_OSC_DEFER_ARMED = False
        pending = _GRID_OSC_DEFER_PAYLOAD
        _GRID_OSC_DEFER_PAYLOAD = None
        if not pending:
            return
        action_col, action_layers, action_pairs, action_address = pending
        try:
            _apply_grid_osc_action_immediate(action_col, action_layers, action_pairs)
            _set_grid_osc_status(action_address)
            if action_pairs:
                layer, pair_col = action_pairs[-1]
                _defer_grid_osc_ui_refresh(layer=layer, col=pair_col)
            elif action_layers:
                _defer_grid_osc_ui_refresh(layer=action_layers[-1], col=action_col)
            else:
                _defer_grid_osc_ui_refresh()
        except Exception as exc:
            print('Grid OSC action failed:', action_address, exc)

    if _defer_run(_run, delayFrames=0):
        return True
    _GRID_OSC_DEFER_ARMED = False
    _GRID_OSC_DEFER_PAYLOAD = None
    ok = _apply_grid_osc_action_immediate(col, layers, pairs)
    _set_grid_osc_status(address)
    _defer_grid_osc_ui_refresh(
        layer=(pairs[-1][0] if pairs else (layers[-1] if layers else None)),
        col=(pairs[-1][1] if pairs else col),
    )
    return ok


def _handle_grid_osc_message(address, args):
    if not _grid_osc_active():
        return False
    col, layers, pairs = _parse_grid_osc_address(address)
    if col is None and not pairs:
        prefix = _grid_osc_prefix().strip().rstrip('/')
        if prefix and not prefix.startswith('/'):
            prefix = '/' + prefix
        if str(address).strip().startswith(prefix + '/'):
            _set_grid_osc_status(address)
        return False
    if not _grid_osc_should_trigger(address, args, col, layers, pairs):
        _set_grid_osc_status(address)
        return True
    _defer_grid_osc_action(col, layers, pairs, address)
    return True


def _set_midi_received(text, value=None):
    s = _settings_op()
    if s is None:
        return
    try:
        p = s.par.Midireceived
        try:
            p.readOnly = False
            p.mode = ParMode.CONSTANT
        except Exception:
            pass
        p.val = str(text)
    except Exception:
        pass


def _midi_note_id(channel, note):
    try:
        return '{}:{}'.format(int(channel), int(note))
    except Exception:
        return '{}:{}'.format(channel, note)


def _midi_message_is_note(message):
    msg = str(message or '').strip().lower()
    if not msg:
        return False
    if 'note' in msg:
        return True
    try:
        code = int(float(message))
        return code in (8, 9, 10)
    except Exception:
        pass
    return False


def _midi_message_is_cc(message):
    msg = str(message or '').strip().lower()
    if not msg:
        return False
    if 'control' in msg or msg == 'cc' or msg.startswith('cc '):
        return True
    if msg in ('cc', 'ctl', 'controlchange', 'control_change'):
        return True
    # TouchDesigner often passes numeric message types for Control Change.
    try:
        code = int(float(message))
        return code in (10, 11, 12, 13, 14)
    except Exception:
        pass
    return False


def _midi_should_route_cc(message, channel, index):
    """Route CC mappings; reject note-ons (e.g. note 79 ≠ CC 79)."""
    if _midi_message_is_note(message):
        return False
    if _midi_message_is_cc(message):
        return True
    # TD callbacks sometimes pass an empty message type; index is the CC number.
    if not str(message or '').strip():
        return bool(_MIDI_CC_MAPPINGS and _midi_cc_matches_any(channel, index))
    return False


def _midi_channel_matches(spec, channel):
    spec = str(spec or '').strip()
    if not spec or spec == '*':
        return True
    try:
        want = int(float(spec))
        got = int(float(channel))
        if want == got:
            return True
        # MIDI channel 1 may arrive as 0 in some TD paths only.
        return want == 1 and got == 0
    except Exception:
        return False


def _midi_cc_id(channel, controller):
    try:
        return '{}:{}'.format(int(channel), int(controller))
    except Exception:
        return '{}:{}'.format(channel, controller)


def _midi_cc_number(controller):
    try:
        return int(float(controller))
    except Exception:
        return None


def _midi_cc_matches(mapping_cc, channel, controller, mapping_channel=''):
    mapping_cc = str(mapping_cc or '').strip()
    if not mapping_cc:
        return False
    if mapping_channel and not _midi_channel_matches(mapping_channel, channel):
        return False
    cc_id = _midi_cc_id(channel, controller)
    if mapping_cc == cc_id:
        return True
    ctrl = _midi_cc_number(controller)
    if mapping_cc.startswith('*:') and ctrl is not None:
        try:
            return int(mapping_cc[2:]) == ctrl
        except Exception:
            pass
    if ctrl is None:
        return mapping_cc == str(controller).strip()
    try:
        want = int(float(''.join(ch for ch in mapping_cc if ch.isdigit() or ch == '-') or mapping_cc))
    except Exception:
        want = None
    if want is None:
        return False
    if want == ctrl:
        return True
    for prefix in ('CC', 'cc'):
        if mapping_cc == prefix + str(ctrl):
            return True
    return False


def _layer_index_from_row_label(token):
    """Map grid row label (e.g. L4) to internal layer index."""
    token = str(token or '').strip().upper()
    if not token.startswith('L'):
        return None
    digits = ''.join(ch for ch in token[1:] if ch.isdigit())
    if not digits:
        return None
    want = 'L{}'.format(int(digits))
    for layer in range(1, _num_layers() + 1):
        if _layer_label(layer) == want:
            return layer
    return None


def _parse_midi_opacity_target(target):
    target = str(target or '').strip()
    if not target:
        return None
    for part in target.replace('__', '_').replace('-', '_').split('_'):
        layer = _layer_index_from_row_label(part)
        if layer is not None:
            return layer
    for part in target.replace('__', ':').split(':'):
        layer = _layer_index_from_row_label(part)
        if layer is not None:
            return layer
    return None


def _selected_layer_col():
    r = _root()
    if r is None:
        return 1, 1
    try:
        layer = int(float(r.par.Selectedlayer.eval()))
    except Exception:
        layer = 1
    try:
        col = int(float(r.par.Selectedcol.eval()))
    except Exception:
        col = 1
    return max(1, min(_num_layers(), layer)), max(1, min(_num_cols(), col))


def _parse_midi_col_token(token):
    token = str(token or '').strip().lower().replace('-', '_')
    if not token.startswith('col'):
        return None
    digits = ''.join(ch for ch in token[3:] if ch.isdigit())
    if not digits:
        return None
    try:
        return max(1, min(_num_cols(), int(digits)))
    except Exception:
        return None


def _parse_midi_param_location(token):
    loc = str(token or '').strip().replace('-', '_')
    loc_low = loc.lower()
    layer = None
    col = None
    if '_col' in loc_low:
        left, _, right = loc_low.partition('_col')
        layer = _layer_index_from_row_label(left)
        col = _parse_midi_col_token('col' + right)
    elif loc_low.startswith('col'):
        col = _parse_midi_col_token(loc_low)
    else:
        layer = _layer_index_from_row_label(loc)
    return layer, col


def _parse_midi_param_target(target):
    raw = str(target or '').strip()
    if not raw:
        return None
    parts = raw.split(':')
    head = parts[0].lower()
    if head in ('par', 'param'):
        rest = parts[1:]
        if not rest:
            return None
        if len(rest) == 1:
            return {'kind': 'cell', 'layer': None, 'col': None, 'par': rest[0]}
        layer, col = _parse_midi_param_location(rest[0])
        return {
            'kind': 'cell',
            'layer': layer,
            'col': col,
            'par': rest[-1],
        }
    if head == 'settings':
        if len(parts) < 2:
            return None
        return {'kind': 'settings', 'par': parts[1]}
    return None


def _find_par_on_op(op, name):
    if op is None:
        return None
    want = str(name or '').strip()
    if not want:
        return None
    try:
        return getattr(op.par, want)
    except Exception:
        pass
    want_low = want.lower()
    try:
        for par in list(op.pars()):
            if str(par.name).lower() == want_low:
                return par
    except Exception:
        pass
    try:
        for par in list(op.customPars):
            if str(par.name).lower() == want_low:
                return par
    except Exception:
        pass
    return None


def _midi_cc_at_endpoint(raw):
    try:
        cc = float(raw)
    except Exception:
        return False
    return cc <= 0.0 or cc >= 127.0


def _set_op_par_value(par, value, force=False):
    if par is None:
        return False
    try:
        value = float(value)
    except Exception:
        return False
    try:
        current = float(par.eval())
        if not force and abs(current - value) < (1.0 / 127.0):
            return True
    except Exception:
        pass
    try:
        if par.mode != ParMode.CONSTANT:
            par.mode = ParMode.CONSTANT
    except Exception:
        pass
    try:
        par.val = _absolute_to_par_val(par, value)
        return True
    except Exception:
        return False


def _midi_mapping_value_range(mapping_item, par=None):
    min_v = None
    max_v = None
    if isinstance(mapping_item, dict):
        if 'min' in mapping_item:
            try:
                min_v = float(mapping_item['min'])
            except Exception:
                pass
        if 'max' in mapping_item:
            try:
                max_v = float(mapping_item['max'])
            except Exception:
                pass
    if par is not None:
        if min_v is None or max_v is None:
            try:
                slider_lo, slider_hi = _param_slider_range(par)
            except Exception:
                slider_lo, slider_hi = 0.0, 1.0
            if min_v is None:
                min_v = slider_lo
            if max_v is None:
                max_v = slider_hi
    if min_v is None:
        min_v = 0.0
    if max_v is None:
        max_v = 1.0
    return min_v, max_v


def _map_midi_cc_value(raw, out_min, out_max):
    try:
        v = float(raw) / 127.0
    except Exception:
        v = 0.0
    v = max(0.0, min(1.0, v))
    lo = float(out_min)
    hi = float(out_max)
    return lo + (hi - lo) * v


def _midi_takeover_mode():
    s = _settings_op()
    if s is None:
        return MIDI_TAKEOVER_DEFAULT
    try:
        raw = str(s.par.Miditakeovermode.eval()).strip().lower().replace(' ', '')
    except Exception:
        return MIDI_TAKEOVER_DEFAULT
    if raw in MIDI_TAKEOVER_MODES:
        return raw
    return MIDI_TAKEOVER_DEFAULT


def _midi_takeover_cc_key(channel, index):
    return '{}:{}'.format(str(channel).strip(), str(index).strip())


def clear_midi_takeover_sync(cc_key=None):
    """Reset pickup / scaling state (e.g. after UI drag or template reload)."""
    global _MIDI_TAKEOVER_PICKED_UP, _MIDI_TAKEOVER_LAST_NORM
    if cc_key is None:
        _MIDI_TAKEOVER_PICKED_UP.clear()
        _MIDI_TAKEOVER_LAST_NORM.clear()
        return
    key = str(cc_key)
    _MIDI_TAKEOVER_PICKED_UP.discard(key)
    _MIDI_TAKEOVER_LAST_NORM.pop(key, None)


def _midi_value_to_norm(value, min_v, max_v):
    lo = float(min_v)
    hi = float(max_v)
    span = hi - lo
    if span <= 0.0:
        return max(0.0, min(1.0, float(value)))
    return max(0.0, min(1.0, (float(value) - lo) / span))


def _midi_norm_to_value(norm, min_v, max_v):
    lo = float(min_v)
    hi = float(max_v)
    span = hi - lo
    if span <= 0.0:
        return lo
    return lo + max(0.0, min(1.0, float(norm))) * span


def _midi_pickup_crossed(last_norm, target_norm, current_norm):
    if abs(float(target_norm) - float(current_norm)) <= MIDI_TAKEOVER_PICKUP_EPS:
        return True
    if last_norm is None:
        return False
    last_norm = float(last_norm)
    target_norm = float(target_norm)
    current_norm = float(current_norm)
    lo = min(last_norm, target_norm)
    hi = max(last_norm, target_norm)
    return lo <= current_norm <= hi


def _apply_midi_takeover(channel, index, current_value, target_value, min_v, max_v):
    """Apply Takeover Mode to a mapped CC target (None / Pickup / Value Scaling)."""
    mode = _midi_takeover_mode()
    lo = float(min_v)
    hi = float(max_v)
    current_norm = _midi_value_to_norm(current_value, lo, hi)
    target_norm = _midi_value_to_norm(target_value, lo, hi)
    if mode == 'none':
        return float(target_value)
    cc_key = _midi_takeover_cc_key(channel, index)
    if target_norm <= 0.0 or target_norm >= 1.0:
        # A physical CC at 0/127 must be able to hit the configured endpoints.
        # Takeover still smooths the middle, but it should not strand controls at
        # e.g. 0.03 or 0.97 when the controller is fully closed/open.
        _MIDI_TAKEOVER_LAST_NORM[cc_key] = target_norm
        if mode == 'pickup':
            _MIDI_TAKEOVER_PICKED_UP.add(cc_key)
        return float(target_value)
    if mode == 'valuescaling':
        step = float(MIDI_TAKEOVER_SCALE_STEP)
        blended = current_norm + (target_norm - current_norm) * step
        blended = max(0.0, min(1.0, blended))
        _MIDI_TAKEOVER_LAST_NORM[cc_key] = target_norm
        return _midi_norm_to_value(blended, lo, hi)
    # pickup
    if cc_key in _MIDI_TAKEOVER_PICKED_UP:
        if abs(float(target_norm) - float(current_norm)) > float(MIDI_TAKEOVER_REARM_DELTA):
            _MIDI_TAKEOVER_PICKED_UP.discard(cc_key)
        else:
            _MIDI_TAKEOVER_LAST_NORM[cc_key] = target_norm
            return float(target_value)
    last_norm = _MIDI_TAKEOVER_LAST_NORM.get(cc_key)
    if _midi_pickup_crossed(last_norm, target_norm, current_norm):
        _MIDI_TAKEOVER_PICKED_UP.add(cc_key)
        _MIDI_TAKEOVER_LAST_NORM[cc_key] = target_norm
        return float(target_value)
    _MIDI_TAKEOVER_LAST_NORM[cc_key] = target_norm
    return _midi_norm_to_value(current_norm, lo, hi)


def _resolve_midi_param_op(spec):
    if spec.get('kind') == 'settings':
        return _settings_op()
    layer = spec.get('layer')
    col = spec.get('col')
    sel_layer, sel_col = _selected_layer_col()
    if layer is None:
        layer = sel_layer
    if col is None:
        col = sel_col
    return _cell_param_target(layer, col)


def _trigger_midi_param_target(target, midi_value, mapping_item=None, channel=None, index=None):
    spec = _parse_midi_param_target(target)
    if spec is None:
        return False
    op = _resolve_midi_param_op(spec)
    if op is None:
        return False
    par = _find_par_on_op(op, spec.get('par'))
    if par is None:
        return False
    min_v, max_v = _midi_mapping_value_range(mapping_item, par)
    target_value = _map_midi_cc_value(midi_value, min_v, max_v)
    try:
        current_value = float(par.eval())
    except Exception:
        current_value = target_value
    if channel is not None and index is not None:
        target_value = _apply_midi_takeover(
            channel, index, current_value, target_value, min_v, max_v,
        )
    return _set_op_par_value(par, target_value, force=_midi_cc_at_endpoint(midi_value))


def _parse_midi_map_target(target):
    """Parse map:1, map:cell:1, map:global:3 (Map Controller dial + bank)."""
    raw = str(target or '').strip().lower().replace('-', '_')
    parts = [p for p in raw.replace(':', '_').split('_') if p]
    scope = None
    if 'global' in parts:
        scope = 'global'
    elif 'cell' in parts or 'layer' in parts:
        scope = 'cell'
    tail = ''
    for prefix in ('map_dial_', 'map_dial:', 'map_dial', 'map_', 'map:', 'map'):
        if raw.startswith(prefix):
            tail = raw[len(prefix):].lstrip(':_')
            break
    if not tail:
        parts = [p for p in raw.split('_') if p]
        for part in reversed(parts):
            if part.isdigit():
                tail = part
                break
    if not tail:
        return None
    digits = ''.join(ch for ch in tail if ch.isdigit())
    if not digits:
        return None
    try:
        idx = int(digits)
    except Exception:
        return None
    try:
        count = int(MAP_DIAL_COUNT)
    except Exception:
        count = 8
    if 1 <= idx <= count:
        return {'scope': scope, 'index': idx}
    return None


def _parse_midi_map_index(target):
    """Parse map:1 … map:8 (Map Controller dial index, active bank)."""
    parsed = _parse_midi_map_target(target)
    if parsed is None:
        return None
    return parsed['index']


def _trigger_midi_map_target(target, midi_value, mapping_item=None, channel=None, index=None):
    """Drive a Map Controller dial (active or scoped cell/global bank)."""
    parsed = _parse_midi_map_target(target)
    if parsed is None:
        return False
    idx = parsed['index']
    scope = parsed['scope']
    min_v, max_v = _midi_mapping_value_range(mapping_item, None)
    lo = float(min_v)
    hi = float(max_v)
    span = hi - lo if hi > lo else 1.0
    try:
        cc = max(0.0, min(127.0, float(midi_value)))
    except Exception:
        cc = 0.0
    target_norm = max(0.0, min(1.0, lo + (cc / 127.0) * span))
    current_norm = map_dial_norm_scoped(idx, scope)
    final_norm = target_norm
    if channel is not None and index is not None:
        final_norm = _midi_value_to_norm(
            _apply_midi_takeover(
                channel, index, current_norm, target_norm, 0.0, 1.0,
            ),
            0.0, 1.0,
        )
    try:
        return set_map_dial_value_scoped(
            idx, final_norm, scope=scope, light=True, paint=False, from_midi=True,
        )
    except Exception:
        return False


def _trigger_midi_opacity_target(target, midi_value, channel=None, index=None):
    layer = _parse_midi_opacity_target(target)
    if layer is None:
        return False
    try:
        raw = float(midi_value)
    except Exception:
        raw = 0.0
    target_opacity = max(0.0, min(1.0, raw / 127.0))
    current_opacity = layer_opacity(layer)
    if channel is not None and index is not None:
        target_opacity = max(0.0, min(1.0, _apply_midi_takeover(
            channel, index, current_opacity, target_opacity, 0.0, 1.0,
        )))
    set_layer_opacity_interactive(layer, target_opacity)
    return True


def _midi_note_matches(mapping_note, channel, note):
    mapping_note = str(mapping_note or '').strip()
    if not mapping_note:
        return False
    note_id = _midi_note_id(channel, note)
    if mapping_note == note_id:
        return True
    try:
        note_num = str(int(float(note)))
    except Exception:
        note_num = str(note).strip()
    if mapping_note == note_num:
        return True
    for prefix in ('Note', 'note'):
        if mapping_note == prefix + note_num:
            return True
    if mapping_note.startswith('*:') and mapping_note[2:] == note_num:
        return True
    return False


def _parse_midi_scene_target(target):
    token = str(target or '').strip().lower().replace('-', '_')
    if not token.startswith('scene'):
        return None
    digits = ''.join(ch for ch in token[5:] if ch.isdigit())
    if not digits:
        return None
    try:
        return max(1, min(_num_scenes(), int(digits)))
    except Exception:
        return None


def _trigger_midi_scene_target(target):
    scene = _parse_midi_scene_target(target)
    if scene is None:
        return False
    switch_scene(scene)
    return True


def _apply_midi_grid_target_immediate(target):
    """Column/layer composition routing (safe outside midiin callback)."""
    target = str(target or '').strip()
    if not target:
        return False
    address = target
    if not address.startswith('/'):
        address = '/' + address
    col, layers, pairs = _parse_grid_osc_address(address)
    if col is None and not pairs:
        prefix = _grid_osc_prefix().strip().rstrip('/') or GRID_OSC_DEFAULT_PREFIX
        if not prefix.startswith('/'):
            prefix = '/' + prefix
        col, layers, pairs = _parse_grid_osc_address(prefix + '/' + target.strip('/'))
    if col is None and not pairs:
        return False
    prev_sig = tuple(_get_layer_src_col(layer) for layer in range(1, _num_layers() + 1))
    ok = _apply_grid_osc_action_immediate(col, layers, pairs)
    if ok:
        _defer_midi_grid_selection_repaint(prev_sig)
        try:
            if _cell_param_focus_mode() == 'delayed':
                r = _root()
                if pairs:
                    focus_layer, focus_col = pairs[-1]
                elif layers:
                    focus_layer, focus_col = layers[-1], col
                else:
                    try:
                        focus_layer = int(float(r.par.Selectedlayer.eval()))
                    except Exception:
                        focus_layer = _base_layer()
                    focus_col = col
                if focus_layer is not None and focus_col is not None:
                    _schedule_cell_params_ui(int(focus_layer), int(focus_col), delay_frames=18)
        except Exception:
            pass
    return ok


def _defer_midi_grid_selection_repaint(prev_sig=None):
    """Repaint composition rings for prev+current live cells (sync — defer was dropping click highlights)."""
    r = _root()
    if r is None:
        return
    try:
        n = _num_layers()
        prev = tuple(prev_sig or ())
        targets = set()
        for layer in range(1, n + 1):
            if layer <= len(prev):
                targets.add((layer, int(prev[layer - 1])))
            targets.add((layer, int(_get_layer_src_col(layer))))
        try:
            targets.add((
                int(float(r.par.Selectedlayer.eval())),
                int(float(r.par.Selectedcol.eval())),
            ))
        except Exception:
            pass
        for layer, col in sorted(targets):
            if 1 <= layer <= n and 1 <= col <= _num_cols():
                _refresh_cell_selection_display(layer, col)
    except Exception as exc:
        print('MIDI selection repaint failed:', exc)


def _apply_midi_note_target_immediate(target):
    target = str(target or '').strip()
    if not target:
        return False
    if _trigger_midi_scene_target(target):
        return True
    return _apply_midi_grid_target_immediate(target)


def _defer_midi_note_target(target):
    """Schedule pad/scene note actions — composition UI must not run in midiin callback."""
    global _MIDI_NOTE_DEFER_ARMED, _MIDI_NOTE_DEFER_TARGET
    target = str(target or '').strip()
    if not target:
        return False
    # Paused timeline: apply + ring move now (frame/ms defer can still miss cooks).
    if not global_transport_playing():
        _MIDI_NOTE_DEFER_ARMED = False
        _MIDI_NOTE_DEFER_TARGET = None
        try:
            cell_change_log('midi.note.immediate_paused', target)
        except Exception:
            pass
        return _apply_midi_note_target_immediate(target)
    _MIDI_NOTE_DEFER_TARGET = target
    if _MIDI_NOTE_DEFER_ARMED:
        return True
    _MIDI_NOTE_DEFER_ARMED = True

    def _run():
        global _MIDI_NOTE_DEFER_ARMED, _MIDI_NOTE_DEFER_TARGET
        _MIDI_NOTE_DEFER_ARMED = False
        pending = _MIDI_NOTE_DEFER_TARGET
        _MIDI_NOTE_DEFER_TARGET = None
        if not pending:
            return
        try:
            cell_change_log('midi.note.deferred', pending)
        except Exception:
            pass
        try:
            _apply_midi_note_target_immediate(pending)
        except Exception as exc:
            print('MIDI note target failed:', pending, exc)

    # Wall-clock defer while playing still leaves the midiin callback quickly.
    try:
        fromOP = _cell_change_root()
        run(_run, delayMilliSeconds=1, fromOP=fromOP)
        return True
    except Exception:
        pass
    if _defer_run(_run, delayFrames=1):
        return True
    _MIDI_NOTE_DEFER_ARMED = False
    _MIDI_NOTE_DEFER_TARGET = None
    return _apply_midi_note_target_immediate(target)


def _trigger_midi_note_target(target):
    return _defer_midi_note_target(target)


def _trigger_midi_grid_target(target):
    target = str(target or '').strip()
    if not target:
        return False
    address = target if target.startswith('/') else '/' + target
    col, layers, pairs = _parse_grid_osc_address(address)
    if col is None and not pairs:
        prefix = _grid_osc_prefix().strip().rstrip('/') or GRID_OSC_DEFAULT_PREFIX
        if not prefix.startswith('/'):
            prefix = '/' + prefix
        col, layers, pairs = _parse_grid_osc_address(prefix + '/' + target.strip('/'))
    if col is None and not pairs:
        return False
    return _defer_grid_osc_action(col, layers, pairs, address)


def _format_midi_received(message, channel, index, val):
    kind = 'cc' if _midi_should_route_cc(message, channel, index) else 'note'
    return '{} | ch {} {} {} val {}'.format(message, channel, kind, index, val)


def _midi_event_fingerprint(message, channel, index, value):
    try:
        val = round(float(value), 4)
    except Exception:
        val = str(value)
    return (
        str(message).strip().lower(),
        str(channel).strip(),
        str(index).strip(),
        val,
    )


def _midi_duplicate_event(message, channel, index, value):
    """midiinDAT callback + table DAT fallback can report the same event twice."""
    global _MIDI_EVENT_FP, _MIDI_EVENT_TS
    fp = _midi_event_fingerprint(message, channel, index, value)
    now = _now_seconds()
    try:
        recent = (now - float(_MIDI_EVENT_TS)) < 0.08
    except Exception:
        recent = False
    if fp == _MIDI_EVENT_FP and recent:
        return True
    _MIDI_EVENT_FP = fp
    _MIDI_EVENT_TS = now
    return False


def _midi_cc_matches_any(channel, index):
    for item in _MIDI_CC_MAPPINGS:
        if _midi_cc_matches(item.get('cc', ''), channel, index, item.get('channel', '')):
            return True
    return False


def _handle_midi_cc_mappings(channel, index, val, message=None):
    if not _midi_should_route_cc(message, channel, index):
        return False
    handled = False
    matched = None
    for item in _MIDI_CC_MAPPINGS:
        if not _midi_cc_matches(
            item.get('cc', ''),
            channel,
            index,
            item.get('channel', ''),
        ):
            continue
        matched = item
        break
    if matched is None:
        return False
    target = str(matched.get('target', '')).strip()
    if _trigger_midi_map_target(target, val, matched, channel, index):
        return True
    if _trigger_midi_opacity_target(target, val, channel, index):
        return True
    if _trigger_midi_param_target(target, val, matched, channel, index):
        return True
    if _trigger_midi_grid_target(target):
        return True
    return False


def _handle_midi_message(message, channel, index, value, input_name=None):
    msg = str(message)
    if _midi_duplicate_event(msg, channel, index, value):
        return False
    try:
        val = float(value)
    except Exception:
        val = 0.0
    handled = False
    if _midi_should_route_cc(msg, channel, index):
        _set_midi_received(_format_midi_received(msg, channel, index, val))
        handled = _handle_midi_cc_mappings(channel, index, val, message=msg)
        return handled
    _set_midi_received(_format_midi_received(msg, channel, index, val))
    if val <= 0:
        return False
    for item in _MIDI_MAPPINGS:
        note_spec = item.get('note', '')
        if not _midi_note_matches(note_spec, channel, index):
            continue
        ch_spec = item.get('channel', '')
        if ch_spec and not _midi_channel_matches(ch_spec, channel):
            continue
        if _trigger_midi_note_target(item.get('target', '')):
            handled = True
    return handled


def _is_internal_pulse_osc_address(address):
    """pulse_osc_out shares the listen UDP port — ignore loopback on localhost."""
    addr = _normalize_osc_address(address)
    return addr.startswith(PULSE_OSC_ADDRESS_PREFIX)


def _handle_osc_message(address, args):
    if not _osc_active():
        return False
    address = _normalize_osc_address(address)
    if _is_internal_pulse_osc_address(address):
        return False
    raw_values = list(args) if args else []
    values = raw_values if raw_values else [0.0]
    _set_osc_status(address, values)
    handled = _handle_grid_osc_message(address, raw_values)
    matched_slots = []
    for idx in range(1, OSC_MAPPING_SLOTS + 1):
        mapping = _osc_mapping(idx)
        if not mapping:
            continue
        if _normalize_osc_address(address) != mapping['address']:
            continue
        matched_slots.append((idx, mapping))
    for match_index, item in enumerate(matched_slots):
        idx, mapping = item
        # If one OSC address carries multiple link values, feed slots in order.
        value_index = min(match_index, len(values) - 1)
        if len(values) > 1 and idx <= len(values):
            value_index = idx - 1
        raw_value = values[value_index]
        out_value = _map_osc_value(raw_value, mapping['min'], mapping['max'])
        _set_osc_slot_value(idx, out_value)
        if mapping.get('enabled'):
            handled = True
    return handled
