import os

from performance_grid.assemble import assemble_settings_parexec
from performance_grid.constants_builder import *  # noqa: F401,F403
from performance_grid.paths import sonomika_sets_dir
from performance_grid.builder.helpers_ui import _bind_canvas_res, _set_par

try:
    ParMode
except NameError:
    try:
        from td import ParMode
    except Exception:
        class ParMode:
            CONSTANT = 0

SETTINGS_PAREXEC = assemble_settings_parexec(
    default_set_name=DEFAULT_SET_NAME,
    sets_subdir=SETS_SUBDIR,
)

ABOUT_BRAND = 'Sonomika 1.0'
ABOUT_INFO = 'https://linktr.ee/sonomika'
_ABOUT_PAR_NAMES = frozenset(('Aboutbrand', 'Aboutinfo'))
_SPOUT_PAR_NAMES = ('Spoutactive', 'Spoutname')


def _pulse_parexec_slot_pars():
    parts = []
    for slot in range(1, PULSE_SLOTS + 1):
        parts.extend([
            'Pulse{}active'.format(slot),
            'Pulse{}division'.format(slot),
            'Pulse{}skip'.format(slot),
            'Pulse{}lfo'.format(slot),
            'Pulse{}kick'.format(slot),
            'Pulse{}peak'.format(slot),
            'Pulse{}min'.format(slot),
            'Pulse{}max'.format(slot),
        ])
    return ' '.join(parts)


def _resolve_settings():
    s = op(SETTINGS_COMP)
    if s is not None:
        return s
    try:
        s = op('/sonomika_infra/settings')
        if s is not None:
            return s
    except Exception:
        pass
    return None


def _resolve_program_pick():
    p = op(PROGRAM_PICK_COMP)
    if p is not None:
        return p
    try:
        p = op('/sonomika_infra/program_pick')
        if p is not None:
            return p
    except Exception:
        pass
    return None


def _move_to_root(node):
    td_root = op('/')
    if node is None or td_root is None:
        return None
    try:
        if node.parent() is td_root:
            return node
        copied = td_root.copy(node, name=node.name, includeDocked=True)
        try:
            node.destroy()
        except Exception:
            pass
        return copied or td_root.op(node.name)
    except Exception:
        return node


def _restore_root_settings():
    """Move /settings to project root and remove sonomika_infra."""
    try:
        pm = op('/project1/performance_mode')
        logic = pm.op('logic').module if pm is not None else None
        if logic is not None and hasattr(logic, 'restore_root_settings_layout'):
            return logic.restore_root_settings_layout(reposition=False)
    except Exception:
        pass
    td_root = op('/')
    if td_root is None:
        return None
    infra = td_root.op('sonomika_infra')
    for name in ('settings', 'program_pick'):
        root_node = td_root.op(name)
        infra_node = infra.op(name) if infra is not None else None
        if root_node is None and infra_node is not None:
            _move_to_root(infra_node)
        elif root_node is not None and infra_node is not None:
            try:
                infra_node.destroy()
            except Exception:
                pass
    if infra is not None:
        for child in list(infra.children):
            try:
                if td_root.op(child.name) is None:
                    _move_to_root(child)
                else:
                    child.destroy()
            except Exception:
                pass
        try:
            if len(infra.children) == 0:
                infra.destroy()
        except Exception:
            pass
    return td_root.op('settings')


def _destroy_root_op(name):
    try:
        target = op('/' + name)
    except Exception:
        target = None
    if target is not None:
        try:
            target.destroy()
        except Exception:
            pass


def _remove_legacy_spout_output(settings=None):
    """Drop old settings-driven Spout controls and senders."""
    if settings is None:
        settings = _resolve_settings()
    if settings is not None:
        for name in _SPOUT_PAR_NAMES:
            try:
                getattr(settings.par, name).destroy()
            except Exception:
                pass
        for pg in list(settings.customPages):
            if pg.name != 'Output':
                continue
            try:
                pg.destroy()
            except Exception:
                pass
            break
    for name in ('spout_out', 'syphonspoutout1', 'perform_view'):
        _destroy_root_op(name)


def _create_syphon_spout_out(td_root, name):
    for op_type in ('syphonspoutoutTOP', 'spoutoutTOP'):
        try:
            return td_root.create(op_type, name)
        except Exception:
            continue
    return None


def _ensure_out1_spout_output():
    """Root /out1 -> /SonomikaTD Spout sender, without Settings controls."""
    td_root = op('/')
    if td_root is None:
        return None
    rout = td_root.op('out1')
    if rout is None:
        return None
    _remove_legacy_spout_output()

    sender = td_root.op('SonomikaTD')
    if sender is None:
        sender = _create_syphon_spout_out(td_root, 'SonomikaTD')
        if sender is None:
            return None
    try:
        rout.outputConnectors[0].connect(sender.inputConnectors[0])
    except Exception:
        pass
    try:
        sender.par.sendername = 'SonomikaTD'
        sender.par.active = True
        sender.par.outputresolution = 'useinput'
    except Exception:
        pass
    try:
        perform = op('/perform')
        bx = perform.nodeX if perform else 0
        by = perform.nodeY if perform else 0
        sender.nodeX = bx + 520
        sender.nodeY = by
    except Exception:
        pass
    return sender


def _canonical_settings_tab_name(page_name):
    name = str(page_name or '')
    if name in SETTINGS_TAB_GRID_OSC_LEGACY:
        return SETTINGS_TAB_GRID_OSC
    if name == 'Performance':
        return SETTINGS_TAB_PERF
    return name


def _migrate_settings_tab_names(settings):
    """Shorten tab labels so all settings pages fit the equal-width Perform panels."""
    if settings is None:
        return
    for pg in list(settings.customPages):
        try:
            pg.name = _canonical_settings_tab_name(pg.name)
        except Exception:
            pass


def _par_page_name(par):
    try:
        page = par.page
        return page.name if hasattr(page, 'name') else str(page)
    except Exception:
        return ''


def _reorder_custom_page_pars(settings, page_name, ordered_names):
    """TD append* adds pars at page end; set .order for display sequence."""
    if settings is None:
        return
    for index, name in enumerate(ordered_names):
        try:
            par = getattr(settings.par, name)
        except AttributeError:
            continue
        if _par_page_name(par) != page_name:
            continue
        try:
            par.order = float(index)
        except Exception:
            pass


def _remove_custom_page(settings, page_name):
    if settings is None:
        return False
    for pg in list(settings.customPages):
        if pg.name != page_name:
            continue
        try:
            pg.destroy()
            return True
        except Exception:
            return False
    return False


def _osc_page_par_order():
    names = ['Oscactive', 'Oscport', 'Oscip', 'Osclastaddress', 'Osclastvalue']
    for idx in range(1, 9):
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


_FADE_PAR_ORDER = (
    'Fadeactive',
    'Cellcrossfade',
    'Columncrossfade',
    'Columncrossfadedur',
)
_FADE_KEEP_PARS = frozenset(_FADE_PAR_ORDER)


def _fade_page_par_order():
    return list(_FADE_PAR_ORDER)


def _purge_fade_page_legacy_pars(settings, col_page):
    """Remove dead experimental fade controls from older builds."""
    for legacy_name in (
        'Clipcrossfade', 'Columncrossfadevideo', 'Fadeexperimentalnote',
        'Optimisecellfade', 'Cellfadedur',
        'Crossupdateeveryframes', 'Pauseunrelatedcells', 'Incomingupdateeveryframes',
    ):
        try:
            getattr(settings.par, legacy_name).destroy()
        except Exception:
            pass
    if col_page is None:
        return
    for par in list(col_page.pars):
        try:
            if par.name not in _FADE_KEEP_PARS:
                par.destroy()
        except Exception:
            pass


def _fade_settings_page(settings):
    if settings is None:
        return None
    for pg in settings.customPages:
        if pg.name in ('Fade', 'Crossfade', 'Columns'):
            if pg.name != 'Fade':
                try:
                    pg.name = 'Fade'
                except Exception:
                    pass
            return pg
    return settings.appendCustomPage('Fade')


def _ensure_fade_tab_pars(settings):
    """Fade tab: master Fade toggle, then Cells / Column choices + duration."""
    if settings is None:
        return False
    col_page = _fade_settings_page(settings)

    def _ensure_toggle(name, label, default):
        try:
            getattr(settings.par, name)
        except AttributeError:
            p = col_page.appendToggle(name, label=label)
            p.val = default
            p.default = default

    def _ensure_float(name, label, default, mn, mx):
        try:
            getattr(settings.par, name)
        except AttributeError:
            p = col_page.appendFloat(name, label=label)
            p.default = default
            p.val = default
            p.min = mn
            p.max = mx

    try:
        getattr(settings.par, 'Fadeactive')
        fade_active_created = False
    except AttributeError:
        fade_active_created = True
        p = col_page.appendToggle('Fadeactive', label='Fade')
        try:
            cell_on = bool(int(float(settings.par.Cellcrossfade.eval())))
        except Exception:
            cell_on = False
        try:
            col_on = bool(int(float(settings.par.Columncrossfade.eval())))
        except Exception:
            col_on = False
        p.val = cell_on or col_on
        p.default = DEFAULT_FADE_ACTIVE
    if not fade_active_created:
        _ensure_toggle('Fadeactive', 'Fade', DEFAULT_FADE_ACTIVE)
    try:
        settings.par.Fadeactive.label = 'Fade'
    except Exception:
        pass

    try:
        getattr(settings.par, 'Cellcrossfade')
        cell_xfade_created = False
    except AttributeError:
        cell_xfade_created = True
        p = col_page.appendToggle('Cellcrossfade', label='Crossfade Cells')
        try:
            p.val = bool(int(float(settings.par.Columncrossfade.eval())))
        except Exception:
            p.val = DEFAULT_CELL_CROSSFADE
        p.default = DEFAULT_CELL_CROSSFADE
    if not cell_xfade_created:
        _ensure_toggle('Cellcrossfade', 'Crossfade Cells', DEFAULT_CELL_CROSSFADE)
    try:
        settings.par.Cellcrossfade.label = 'Crossfade Cells'
        settings.par.Cellcrossfade.startSection = True
    except Exception:
        pass
    _ensure_toggle('Columncrossfade', 'Crossfade Column', DEFAULT_COLUMN_CROSSFADE)
    try:
        settings.par.Columncrossfade.label = 'Crossfade Column'
    except Exception:
        pass
    _ensure_float('Columncrossfadedur', 'Crossfade Duration (sec)', DEFAULT_COLUMN_CROSSFADE_DUR, 0.05, 10.0)
    try:
        settings.par.Columncrossfadedur.label = 'Crossfade Duration (sec)'
    except Exception:
        pass
    _purge_fade_page_legacy_pars(settings, col_page)
    _reorder_custom_page_pars(settings, 'Fade', _fade_page_par_order())
    return True


def heal_fade_tab(settings=None):
    """Drop legacy fade pars and reorder — safe to call on script reload."""
    if settings is None:
        settings = _resolve_settings()
    return _ensure_fade_tab_pars(settings)


def _apply_settings_menu(par, label, names, labels, default):
    """Refresh menuNames/menuLabels (fixes Perform UI showing 'Label 1')."""
    if par is None:
        return
    try:
        par.label = label
    except Exception:
        pass
    names = tuple(str(n) for n in names)
    labels = tuple(str(l) for l in labels)
    if len(labels) != len(names):
        labels = names
    try:
        par.menuNames = names
        par.menuLabels = labels
        par.menuNames = names
        par.menuLabels = labels
        par.default = default
        if str(par.eval()) not in names:
            par.val = default
    except Exception:
        pass


def _ensure_perf_tab_pars(settings):
    """Perf tab menus — safe to call on script reload."""
    if settings is None:
        return False
    _migrate_settings_tab_names(settings)
    perf_page = None
    for pg in settings.customPages:
        if pg.name in ('Performance', SETTINGS_TAB_PERF):
            perf_page = pg
            break
    if perf_page is None:
        perf_page = settings.appendCustomPage(SETTINGS_TAB_PERF)
    elif perf_page.name != SETTINGS_TAB_PERF:
        try:
            perf_page.name = SETTINGS_TAB_PERF
        except Exception:
            pass

    def _ensure_menu(name, label, names, labels, default):
        try:
            p = getattr(settings.par, name)
        except AttributeError:
            p = perf_page.appendMenu(name, label=label)
        _apply_settings_menu(p, label, names, labels, default)
        return p

    try:
        settings.par.Performancemode.destroy()
    except Exception:
        pass
    _ensure_menu(
        'Allrenderscale', 'All Cell Render Scale',
        ['100', '75', '67', '50', '25'],
        ['100%', '75%', '67%', '50%', '25%'],
        '100',
    )
    _ensure_menu(
        'Fxrowrenderscale', 'FX render scale',
        ['100', '75', '67', '50', '25'],
        ['100%', '75%', '67%', '50%', '25%'],
        '75',
    )
    for name in ('Defaultrenderscale', 'Defaultupdaterate'):
        try:
            getattr(settings.par, name).destroy()
        except Exception:
            pass
    _ensure_menu(
        'Thumbfps', 'Thumbnail FPS',
        ['60', '30', '15', '5', '1', '0'],
        ['Full', '30 FPS', '15 FPS', '5 FPS', '1 FPS', 'Off'],
        '5',
    )
    _ensure_menu(
        'Thumbquality', 'Thumbnail Quality',
        ['100', '75', '50', '25'],
        ['Full', '75%', '50%', '25%'],
        '75',
    )
    _ensure_menu(
        'Toxcookmode', 'Disable TOX Cooking',
        ['html', 'live', 'all'],
        ['Non-HTML', 'Not Active', 'Off'],
        'html',
    )
    _ensure_menu(
        'Cellparamfocus', 'Cell Parameter Focus',
        ['delayed', 'double', 'off'],
        ['Delayed', 'Double Click', 'Off'],
        'delayed',
    )
    return True


def heal_perf_tab(settings=None):
    """Repair Perf tab menu labels — safe to call on script reload."""
    if settings is None:
        settings = _resolve_settings()
    return _ensure_perf_tab_pars(settings)


def heal_reload_scripts_button(settings=None):
    """Move Reload Scripts (Dev) pulse to the bottom of the About tab."""
    if settings is None:
        settings = _resolve_settings()
    if settings is None:
        return False
    try:
        from performance_grid.builder.helpers_ui import _ensure_reload_scripts_maintenance
        return _ensure_reload_scripts_maintenance(settings)
    except Exception:
        return False


def _ensure_canvas_tab_pars(settings):
    """Canvas Preset menu — safe to call on script reload."""
    if settings is None:
        return False
    try:
        preset = settings.par.Canvaspreset
    except Exception:
        return False
    names = _canvas_preset_names(settings)
    default = '1920x1080' if '1920x1080' in names else (names[0] if names else '1920x1080')
    _apply_settings_menu(preset, 'Canvas Preset', names, names, default)
    return True


def heal_canvas_tab(settings=None):
    """Repair Canvas tab menu labels — safe to call on script reload."""
    if settings is None:
        settings = _resolve_settings()
    return _ensure_canvas_tab_pars(settings)


def reset_fade_defaults_for_new_set(settings=None):
    """Blank performance set: Fade off; Cells + Column toggles on (ready when Fade enabled)."""
    if settings is None:
        settings = _resolve_settings()
    if settings is None:
        return False
    _ensure_fade_tab_pars(settings)
    for name, val in (
        ('Fadeactive', DEFAULT_FADE_ACTIVE),
        ('Cellcrossfade', DEFAULT_CELL_CROSSFADE),
        ('Columncrossfade', DEFAULT_COLUMN_CROSSFADE),
    ):
        try:
            par = getattr(settings.par, name)
            par.val = bool(val)
            par.default = bool(val)
        except Exception:
            pass
    try:
        settings.par.Columncrossfadedur = DEFAULT_COLUMN_CROSSFADE_DUR
    except Exception:
        pass
    return True


def _audio_page_par_order():
    return [
        'Audiodeviceindex',
        'Audiorefresh',
        'Audioactive',
        'Audiogain',
        'Audiooutkick',
        'Audioreverselow',
        'Audiothresholdlow',
        'Audioouthit',
        'Audioreversehigh',
        'Audiothresholdhigh',
        'Audiooutpeakhit',
        'Audioreversepeak',
        'Audiothresholdpeak',
        'Audiooutlow',
        'Audioouthigh',
        'Audiooutpeak',
    ]


def _ensure_about_page(settings):
    """Read-only About tab on /settings (shown in Perform settings_params panel)."""
    if settings is None:
        return
    # Recreate About so it is the final settings tab.
    for pg in settings.customPages:
        if pg.name == 'About':
            try:
                pg.destroy()
            except Exception:
                pass
            break
    about_page = settings.appendCustomPage('About')

    for stale in ('Txt', 'Abouttxt', 'Abouttext', 'Aboutlocation', 'Aboutlink'):
        try:
            getattr(settings.par, stale).destroy()
        except Exception:
            pass
    for par in list(settings.customPars):
        try:
            if par.page != about_page.name or par.name in _ABOUT_PAR_NAMES:
                continue
            par.destroy()
        except Exception:
            pass

    def _ensure_about_str(name, label, value):
        try:
            p = getattr(settings.par, name)
        except AttributeError:
            p = about_page.appendStr(name, label=label)
        try:
            p.val = value
        except Exception:
            pass
        try:
            p.readOnly = True
        except Exception:
            pass
        return p

    _ensure_about_str('Aboutbrand', 'About', ABOUT_BRAND)
    _ensure_about_str('Aboutinfo', 'Information', ABOUT_INFO)
    rec_page = None
    for pg in settings.customPages:
        if pg.name == 'Rec':
            rec_page = pg
            break
    if rec_page is None:
        rec_page = settings.appendCustomPage('Rec')
    for name in (
        'Screenshotfolder', 'Takescreenshot', 'Recordingfolder',
        'Recordaudio', 'Togglerecording', 'Recordingstatus',
    ):
        try:
            par = getattr(settings.par, name)
            page_name = (
                par.page.name if hasattr(par.page, 'name') else str(par.page))
            if page_name != 'Rec':
                par.destroy()
        except Exception:
            pass
    try:
        screenshot_folder = settings.par.Screenshotfolder
    except AttributeError:
        screenshot_folder = rec_page.appendStr(
            'Screenshotfolder', label='Screenshot Folder')
        screenshot_folder.default = 'screenshots'
        screenshot_folder.val = 'screenshots'
    try:
        screenshot_folder.label = 'Screenshot Folder'
        screenshot_folder.order = 0
    except Exception:
        pass
    try:
        screenshot = settings.par.Takescreenshot
    except AttributeError:
        screenshot = rec_page.appendPulse(
            'Takescreenshot', label='Take Screenshot')
    try:
        screenshot.label = 'Take Screenshot'
        screenshot.order = 1
    except Exception:
        pass
    try:
        recording_folder = settings.par.Recordingfolder
    except AttributeError:
        recording_folder = rec_page.appendStr(
            'Recordingfolder', label='Recording Folder')
        recording_folder.default = 'recordings'
        recording_folder.val = 'recordings'
    try:
        recording_folder.label = 'Recording Folder'
        recording_folder.order = 2
    except Exception:
        pass
    try:
        record_audio = settings.par.Recordaudio
    except AttributeError:
        record_audio = rec_page.appendToggle(
            'Recordaudio', label='Record Audio')
        record_audio.default = True
        record_audio.val = True
    try:
        record_audio.label = 'Record Audio'
        record_audio.order = 3
    except Exception:
        pass
    try:
        toggle_recording = settings.par.Togglerecording
    except AttributeError:
        toggle_recording = rec_page.appendPulse(
            'Togglerecording', label='Start / Stop Screen Recording')
    try:
        toggle_recording.label = 'Start / Stop Screen Recording'
        toggle_recording.order = 4
    except Exception:
        pass
    try:
        recording_status = settings.par.Recordingstatus
    except AttributeError:
        recording_status = rec_page.appendStr(
            'Recordingstatus', label='Recording Status')
    try:
        recording_status.val = 'Stopped'
        recording_status.readOnly = True
        recording_status.order = 5
    except Exception:
        pass
    try:
        from performance_grid.builder.helpers_ui import _ensure_reload_scripts_maintenance
        _ensure_reload_scripts_maintenance(settings)
    except Exception:
        pass
    try:
        names = [pg.name for pg in settings.customPages]
        desired = [name for name in names if name not in ('Rec', 'About')]
        desired.extend(['Rec', 'About'])
        settings.sortCustomPages(*desired)
    except Exception:
        pass


def _default_set_file_path(settings=None):
    """Relative path stored in Savefile/Openfile (beside the .toe)."""
    return 'sets/{}'.format(DEFAULT_SET_FILENAME)


def _rel_set_file_path(path):
    """Convert absolute set path to project.folder-relative form."""
    path = str(path or '').strip().replace('\\', '/')
    if not path:
        return ''
    if not os.path.isabs(path) and not (len(path) > 1 and path[1] == ':'):
        return path.lstrip('./')
    try:
        pf = str(project.folder or '').strip()
        if pf:
            rel = os.path.relpath(os.path.normpath(path), os.path.normpath(pf)).replace('\\', '/')
            if not rel.startswith('..'):
                return rel
    except Exception:
        pass
    return path


def _legacy_set_path(path):
    """True when Save/Open path should be replaced with sets/ default."""
    p = str(path or '').strip().replace('\\', '/')
    if not p:
        return True
    if os.path.isabs(p) or (len(p) > 1 and p[1] == ':'):
        return True
    if 'performance_sets' in p.replace('\\', '/'):
        return True
    if p.rstrip('/').endswith('Documents'):
        return True
    if 'OneDrive' in p or '/Users/' in p:
        return True
    return False


def _ensure_sets_page_controls(settings):
    """Rebuild Sets tab controls on the Sets page (file paths + pulse actions)."""
    if settings is None:
        return False
    sets_page = None
    for pg in settings.customPages:
        if pg.name == 'Sets':
            sets_page = pg
            break
    if sets_page is None:
        sets_page = settings.appendCustomPage('Sets')

    save_path = ''
    open_path = ''
    try:
        save_path = str(settings.par.Savefile.eval()).strip()
    except Exception:
        pass
    try:
        open_path = str(settings.par.Openfile.eval()).strip()
    except Exception:
        pass

    for name in (
        'Setname',
        'Setfile',
        'Setpath',
        'Browseset',
        'Newset',
        'Savefile',
        'Saveset',
        'Openfile',
        'Openset',
    ):
        try:
            getattr(settings.par, name).destroy()
        except Exception:
            pass

    sets_page.appendPulse('Newset', label='New Set')
    sets_page.appendFile('Openfile', label='Open File')
    sets_page.appendPulse('Openset', label='Open')
    sets_page.appendFile('Savefile', label='Save File')
    sets_page.appendPulse('Saveset', label='Save')
    _reorder_custom_page_pars(
        settings,
        'Sets',
        ('Newset', 'Openfile', 'Openset', 'Savefile', 'Saveset'),
    )

    default_path = _default_set_file_path(settings)
    if _legacy_set_path(save_path):
        save_path = ''
    else:
        save_path = _rel_set_file_path(save_path)
    if _legacy_set_path(open_path):
        open_path = ''
    else:
        open_path = _rel_set_file_path(open_path)
    try:
        settings.par.Savefile = save_path or default_path
        settings.par.Openfile = open_path or save_path or default_path
    except Exception:
        pass
    return True


def _saved_canvas_dims(settings):
    if settings is None:
        return None
    try:
        w = int(float(settings.fetch('saved_canvas_width', 0)))
        h = int(float(settings.fetch('saved_canvas_height', 0)))
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    try:
        w = int(float(settings.par.Savedcanvaswidth.eval()))
        h = int(float(settings.par.Savedcanvasheight.eval()))
    except Exception:
        return None
    if w <= 0 or h <= 0:
        return None
    return w, h


def _canvas_preset_names(settings):
    names = list(CANVAS_PRESET_NAMES)
    dims = _saved_canvas_dims(settings)
    if dims is not None:
        custom_name = '{}x{}'.format(int(dims[0]), int(dims[1]))
        if custom_name not in names:
            names.append(custom_name)
    return names


def _wire_settings_parexec(settings):
    """Keep settings_parexec listening to all custom settings parameters."""
    if settings is None:
        return
    parexec = settings.op('settings_parexec')
    if parexec is None:
        parexec = settings.create('parameterexecuteDAT', 'settings_parexec')
    parexec.par.op = settings
    try:
        osc_pars = []
        for idx in range(1, 9):
            osc_pars.extend([
                'Osc{}address'.format(idx),
                'Osc{}min'.format(idx),
                'Osc{}max'.format(idx),
                'Osc{}value'.format(idx),
            ])
        parexec.par.pars = (
            'Canvaswidth Canvasheight Canvaspreset Canvasbg Savecanvassize '
            'Allrenderscale Fxrowrenderscale Thumbfps Thumbquality Toxcookmode Cellparamfocus '
            'Fadeactive Cellcrossfade Columncrossfade Columncrossfadedur '
            'Oscactive Oscport Oscip ' + ' '.join(osc_pars) + ' '
            'Gridoscactive Gridoscport Gridoscip Gridoscprefix Gridoscnote Gridoscnote2 '
            'Mididevice Miditemplate Miditakeovermode Midirefreshtemplates '
            'Pulseactive Pulsecustombpm Pulsebpm '
            + _pulse_parexec_slot_pars() + ' '
            'Audioactive Audiogain Audiodeviceindex Audiorefresh '
            'Audiothresholdlow Audiothresholdhigh Audiothresholdpeak '
            'Newset Savefile Saveset Openfile Openset Takescreenshot '
            'Screenshotfolder Recordingfolder Recordaudio Togglerecording '
            'Reloadscripts'
        )
        parexec.par.valuechange = True
        parexec.par.onpulse = True
        parexec.par.active = True
    except Exception:
        pass
    parexec.text = SETTINGS_PAREXEC


def _build_settings(perf_comp=None):
    """Canvas size COMP at top level /settings."""
    td_root = op('/')
    if td_root is None:
        return None
    _restore_root_settings()
    parent = td_root
    settings = _resolve_settings()
    created_settings = settings is None
    legacy = op('/project1/settings')
    if settings is None:
        if legacy is not None:
            try:
                settings = parent.copy(legacy, name='settings', includeDocked=True)
                legacy.destroy()
            except Exception:
                try:
                    settings = parent.copy(legacy, name='settings', includeDocked=False)
                    legacy.destroy()
                except Exception:
                    settings = parent.create('baseCOMP', 'settings')
        else:
            settings = parent.create('baseCOMP', 'settings')
    elif legacy is not None and legacy.path != settings.path:
        try:
            legacy.destroy()
        except Exception:
            pass
    if perf_comp is not None and created_settings:
        try:
            settings.nodeX = perf_comp.nodeX
            settings.nodeY = perf_comp.nodeY + 280
        except Exception:
            pass
    _migrate_settings_tab_names(settings)
    page = None
    for pg in settings.customPages:
        if pg.name == 'Canvas':
            page = pg
            break
    if page is None:
        page = settings.appendCustomPage('Canvas')

    def _ensure_int(name, label, default, mn, mx):
        try:
            getattr(settings.par, name)
        except Exception:
            p = page.appendInt(name, label=label)
            p.default = default
            p.val = default
            p.min = mn
            p.max = mx

    def _ensure_canvas_float(name, label, default, mn=0.0, mx=1.0):
        try:
            p = getattr(settings.par, name)
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
        except Exception:
            pass
        return p

    _ensure_int('Canvaswidth', 'Canvas Width', DEFAULT_CANVAS_W, 320, 7680)
    _ensure_int('Canvasheight', 'Canvas Height', DEFAULT_CANVAS_H, 320, 4320)

    bg = [DEFAULT_CANVAS_BG_R, DEFAULT_CANVAS_BG_G, DEFAULT_CANVAS_BG_B]
    for name, idx in (('Canvasbgr', 0), ('Canvasbgg', 1), ('Canvasbgb', 2)):
        try:
            bg[idx] = float(getattr(settings.par, name).eval())
        except Exception:
            pass
    bg_r, bg_g, bg_b = bg
    for name in ('Canvasbgr', 'Canvasbgg', 'Canvasbgb'):
        try:
            getattr(settings.par, name).destroy()
        except Exception:
            pass
    try:
        bg_par = settings.par.Canvasbg
    except AttributeError:
        bg_par = page.appendRGB('Canvasbg', label='Background Color')
        bg_par.default = (DEFAULT_CANVAS_BG_R, DEFAULT_CANVAS_BG_G, DEFAULT_CANVAS_BG_B)
        bg_par.val = (bg_r, bg_g, bg_b)
    try:
        settings.par.Canvasbg.label = 'Background Color'
    except Exception:
        pass
    old_saved_dims = _saved_canvas_dims(settings)
    if old_saved_dims is not None:
        try:
            settings.store('saved_canvas_width', int(old_saved_dims[0]))
            settings.store('saved_canvas_height', int(old_saved_dims[1]))
        except Exception:
            pass
    for name in ('Savedcanvaswidth', 'Savedcanvasheight'):
        try:
            getattr(settings.par, name).destroy()
        except Exception:
            pass
    try:
        preset_par = settings.par.Canvaspreset
    except Exception:
        preset_par = page.appendMenu('Canvaspreset', label='Canvas Preset')
        preset_par.val = '1920x1080'
    try:
        preset_names = _canvas_preset_names(settings)
        _apply_settings_menu(
            preset_par, 'Canvas Preset', preset_names, preset_names,
            '1920x1080' if '1920x1080' in preset_names else preset_names[0],
        )
    except Exception:
        pass
    try:
        settings.par.Savecanvassize
    except Exception:
        page.appendPulse('Savecanvassize', label='Save Canvas Size')
    try:
        settings.par.Applycanvas.destroy()
    except Exception:
        pass

    _ensure_fade_tab_pars(settings)

    _ensure_perf_tab_pars(settings)

    osc_page = None
    for pg in settings.customPages:
        if pg.name == 'OSC':
            osc_page = pg
            break
    if osc_page is None:
        osc_page = settings.appendCustomPage('OSC')

    def _ensure_osc_int(name, label, default, mn, mx):
        try:
            p = getattr(settings.par, name)
        except AttributeError:
            p = osc_page.appendInt(name, label=label)
            p.default = default
            p.val = default
        p.min = mn
        p.max = mx
        return p

    def _ensure_osc_float(name, label, default, mn, mx, readonly=False):
        try:
            p = getattr(settings.par, name)
        except AttributeError:
            p = osc_page.appendFloat(name, label=label)
            p.default = default
            p.val = default
        p.min = mn
        p.max = mx
        try:
            p.readOnly = bool(readonly)
        except Exception:
            pass
        if name.lower().startswith('osc') and name.lower().endswith('value'):
            try:
                p.readOnly = False
            except Exception:
                pass
            try:
                p.mode = ParMode.CONSTANT
            except Exception:
                pass
        return p

    def _ensure_osc_toggle(name, label, default):
        try:
            p = getattr(settings.par, name)
        except AttributeError:
            p = osc_page.appendToggle(name, label=label)
            p.default = default
            p.val = default
        return p

    def _ensure_osc_str(name, label, default='', readonly=False):
        try:
            p = getattr(settings.par, name)
        except AttributeError:
            p = osc_page.appendStr(name, label=label)
            p.val = default
        else:
            try:
                p.label = label
            except Exception:
                pass
        try:
            p.readOnly = bool(readonly)
        except Exception:
            pass
        return p

    def _mark_section(par):
        try:
            par.startSection = True
        except Exception:
            pass

    osc_ip_saved = DEFAULT_OSC_IP
    try:
        saved = str(settings.par.Oscip.eval()).strip()
        if saved:
            osc_ip_saved = saved
    except Exception:
        pass

    _ensure_osc_toggle('Oscactive', 'OSC Active', True)
    _ensure_osc_int('Oscport', 'OSC Port', 7000, 1, 65535)
    _ensure_osc_str('Oscip', 'IP', osc_ip_saved)
    _ensure_osc_str('Osclastaddress', 'Last Address', '', readonly=True)
    _ensure_osc_str('Osclastvalue', 'Last Value', '', readonly=True)
    for idx in range(1, 9):
        try:
            getattr(settings.par, 'Osc{}target'.format(idx)).destroy()
        except Exception:
            pass
        try:
            getattr(settings.par, 'Osc{}enable'.format(idx)).destroy()
        except Exception:
            pass
        section = _ensure_osc_str('Osc{}address'.format(idx), '{} Address'.format(idx), '')
        _mark_section(section)
        _ensure_osc_float('Osc{}min'.format(idx), '{} Min'.format(idx), 0.0, -100000.0, 100000.0)
        _ensure_osc_float('Osc{}max'.format(idx), '{} Max'.format(idx), 1.0, -100000.0, 100000.0)
        _ensure_osc_float('Osc{}value'.format(idx), '{} Value'.format(idx), 0.0, -100000.0, 100000.0, readonly=False)

    _reorder_custom_page_pars(settings, 'OSC', _osc_page_par_order())

    grid_osc_page = None
    for pg in settings.customPages:
        if pg.name in SETTINGS_TAB_GRID_OSC_LEGACY + (SETTINGS_TAB_GRID_OSC,):
            grid_osc_page = pg
            break
    if grid_osc_page is None:
        grid_osc_page = settings.appendCustomPage(SETTINGS_TAB_GRID_OSC)
    elif grid_osc_page.name != SETTINGS_TAB_GRID_OSC:
        try:
            grid_osc_page.name = SETTINGS_TAB_GRID_OSC
        except Exception:
            pass

    def _ensure_grid_osc_toggle(name, label, default):
        try:
            p = getattr(settings.par, name)
        except AttributeError:
            p = grid_osc_page.appendToggle(name, label=label)
            p.default = default
            p.val = default
        return p

    def _ensure_grid_osc_float(name, label, default, mn, mx, readonly=False):
        try:
            p = getattr(settings.par, name)
        except AttributeError:
            p = grid_osc_page.appendFloat(name, label=label)
            p.default = default
            p.val = default
        p.min = mn
        p.max = mx
        try:
            p.readOnly = bool(readonly)
        except Exception:
            pass
        return p

    def _ensure_grid_osc_str(name, label, default='', readonly=False):
        try:
            p = getattr(settings.par, name)
        except AttributeError:
            p = grid_osc_page.appendStr(name, label=label)
            p.val = default
        else:
            try:
                p.label = label
            except Exception:
                pass
        try:
            p.readOnly = bool(readonly)
        except Exception:
            pass
        return p

    def _ensure_grid_osc_int(name, label, default, mn, mx):
        try:
            p = getattr(settings.par, name)
        except AttributeError:
            p = grid_osc_page.appendInt(name, label=label)
            p.default = default
            p.val = default
        p.min = mn
        p.max = mx
        return p

    grid_ip_saved = DEFAULT_OSC_IP
    grid_port_saved = 7000
    try:
        saved = str(settings.par.Gridoscip.eval()).strip()
        if saved:
            grid_ip_saved = saved
    except Exception:
        pass
    try:
        grid_port_saved = max(1, min(65535, int(float(settings.par.Gridoscport.eval()))))
    except Exception:
        try:
            grid_port_saved = max(1, min(65535, int(float(settings.par.Oscport.eval()))))
        except Exception:
            pass
    _ensure_grid_osc_toggle('Gridoscactive', 'Grid OSC Active', True)
    _ensure_grid_osc_int('Gridoscport', 'OSC Port', grid_port_saved, 1, 65535)
    _ensure_grid_osc_str('Gridoscip', 'IP', grid_ip_saved or osc_ip_saved or DEFAULT_OSC_IP)
    try:
        settings.par.Gridoscport = int(settings.par.Oscport.eval())
        ip = str(settings.par.Oscip.eval()).strip() or DEFAULT_OSC_IP
        settings.par.Gridoscip = ip
        if not str(settings.par.Oscip.eval()).strip():
            settings.par.Oscip = ip
    except Exception:
        pass
    _ensure_grid_osc_str('Gridoscprefix', 'Address Prefix', '/live')
    try:
        getattr(settings.par, 'Gridoscthreshold').destroy()
    except Exception:
        pass
    osc_prefix = '/live'
    try:
        osc_prefix = str(settings.par.Gridoscprefix.eval()).strip() or '/live'
    except Exception:
        pass
    num_cols = NUM_COLS
    if perf_comp is not None:
        try:
            num_cols = max(1, int(float(perf_comp.par.Numcols.eval())))
        except Exception:
            pass
    prefix = osc_prefix.strip().rstrip('/')
    if not prefix.startswith('/'):
        prefix = '/' + prefix
    show_cols = max(1, min(int(num_cols), 12))
    shared_default = '  '.join(
        '{}/col{}'.format(prefix, c) for c in range(1, show_cols + 1)
    )
    pairs_default = '{}/col1_L2_col2_L4_col3_L2_col4_L4'.format(prefix)
    note = _ensure_grid_osc_str('Gridoscnote', 'Simple', shared_default, readonly=True)
    try:
        note.val = shared_default
    except Exception:
        pass
    _mark_section(note)
    note2 = _ensure_grid_osc_str('Gridoscnote2', 'Advanced', pairs_default, readonly=True)
    try:
        note2.val = pairs_default
    except Exception:
        pass
    _ensure_grid_osc_str('Gridosclastaddress', 'Last Address', '', readonly=True)
    _reorder_custom_page_pars(settings, SETTINGS_TAB_GRID_OSC, _grid_osc_page_par_order())
    for old_name in ('Gridosclastvalue', 'Gridosclastaction'):
        try:
            getattr(settings.par, old_name).destroy()
        except Exception:
            pass

    # Pulse tab (right of Grid OSC) — params built by logic.configure_pulse_engine().
    for pg in settings.customPages:
        if pg.name == 'Pulse':
            break
    else:
        settings.appendCustomPage('Pulse')

    # Audio tab (between Pulse and Midi) — params built by logic.configure_audio_analysis().
    for pg in settings.customPages:
        if pg.name == 'Audio':
            break
    else:
        settings.appendCustomPage('Audio')

    # Midi tab menus are built by logic.configure_midi_input() (device mapper + templates).
    for pg in settings.customPages:
        if pg.name == 'Midi':
            break
    else:
        settings.appendCustomPage('Midi')

    _remove_custom_page(settings, 'Maintenance')
    _ensure_sets_page_controls(settings)
    _remove_legacy_spout_output(settings)
    _ensure_about_page(settings)
    _wire_settings_parexec(settings)
    try:
        pm = perf_comp
        if pm is None:
            pm = op('/project1/performance_mode')
        if pm is not None:
            logic = pm.op('logic')
            if logic is not None and hasattr(logic, 'module'):
                mod = logic.module
                if hasattr(mod, 'configure_audio_analysis'):
                    mod.configure_audio_analysis()
                    _reorder_custom_page_pars(settings, 'Audio', _audio_page_par_order())
                if hasattr(mod, '_ensure_pulse_page_order'):
                    mod._ensure_pulse_page_order()
    except Exception:
        pass
    _restore_root_settings()
    return settings


def _set_node_viewer(node, visible):
    if node is None:
        return
    try:
        node.viewer = bool(visible)
    except Exception:
        pass


def _tidy_root_network_view(layout=False):
    """Hide technical root nodes; layout=True repositions tiles (builder setup only)."""
    td_root = op('/')
    if td_root is None:
        return False
    _restore_root_settings()
    if not layout:
        local = td_root.op('local')
        _set_node_viewer(local, False)
        settings = td_root.op('settings')
        if settings is not None:
            _set_node_viewer(settings, False)
        pick = td_root.op('program_pick')
        if pick is not None:
            _set_node_viewer(pick, False)
        return True

    perform = op('/perform')
    try:
        bx = float(perform.nodeX) if perform is not None else 0.0
        by = float(perform.nodeY) if perform is not None else 0.0
    except Exception:
        bx, by = 0.0, 0.0

    pick = td_root.op('program_pick')
    rout = td_root.op('out1')
    win = td_root.op('output_window')
    spout = td_root.op('SonomikaTD')
    if pick is not None:
        pick.nodeX = bx + 200
        pick.nodeY = by
        _set_node_viewer(pick, False)
    if rout is not None:
        rout.nodeX = bx + 400
        rout.nodeY = by
        _set_node_viewer(rout, True)
    if win is not None:
        win.nodeX = bx + 400
        win.nodeY = by + 200
        _set_node_viewer(win, False)
    if spout is not None:
        spout.nodeX = bx + 600
        spout.nodeY = by
        _set_node_viewer(spout, True)

    project = op('/project1')
    if project is not None:
        project.nodeX = bx
        project.nodeY = by - 300
        _set_node_viewer(project, True)

    settings = td_root.op('settings')
    if settings is not None:
        settings.nodeX = bx + 220
        settings.nodeY = by - 300
        _set_node_viewer(settings, False)

    for path in ('/mcp_webserver_base', '/project1/mcp_webserver_base'):
        mcp = op(path)
        if mcp is not None:
            try:
                mcp.nodeX = bx + 440
                mcp.nodeY = by - 300
            except Exception:
                pass
            _set_node_viewer(mcp, False)

    local = td_root.op('local')
    _set_node_viewer(local, False)
    return True


def _setup_root_output(source_out):
    td_root = op('/')
    _restore_root_settings()
    pick = _resolve_program_pick()
    if pick is None:
        pick = td_root.create('selectTOP', 'program_pick')
    _set_par(pick, 'top', expr="op('{}')".format(source_out.path))
    _bind_canvas_res(pick)

    rout = td_root.op('out1')
    if rout is None:
        rout = td_root.create('outTOP', 'out1')
    try:
        pick.outputConnectors[0].connect(rout.inputConnectors[0])
    except Exception:
        pass

    win = td_root.op('output_window')
    if win is None:
        win = td_root.create('windowCOMP', 'output_window')
    _set_par(win, 'winop', rout)
    _set_par(win, 'w', expr=CANVAS_W_EXPR)
    _set_par(win, 'h', expr=CANVAS_H_EXPR)
    try:
        win.par.display = False
        win.par.drawwindow = True
        perform = op('/perform')
        bx = perform.nodeX if perform else 0
        by = perform.nodeY if perform else 0
        pick.nodeX = bx + 160
        pick.nodeY = by
        rout.nodeX = bx + 320
        rout.nodeY = by
        win.nodeX = bx + 320
        win.nodeY = by + 180
        rout.viewer = True
    except Exception:
        pass
    _ensure_out1_spout_output()
    _tidy_root_network_view(layout=True)
    return rout, win


def _project_parent():
    p = op('/project1')
    if p is not None:
        return p
    for c in op('/').children:
        if c.isCOMP and c.name not in ('ui', 'sys', 'local'):
            return c
    return op('/')


def bootstrap_mcp(base_path=None):
    """Start MCP WebServer DAT (port 9981) so Cursor can connect."""
    base = op(base_path) if base_path else None
    if base is None:
        for path in (
            '/project1/mcp_webserver_base',
            '/mcp_webserver_base',
        ):
            try:
                base = op(path)
            except Exception:
                base = None
            if base is not None:
                break
    if base is None:
        parent = _project_parent()
        if parent is not None:
            for ch in parent.children:
                if 'mcp_webserver' in ch.name.lower():
                    base = ch
                    break
    if base is None:
        print('mcp_webserver_base not found — import mcp_webserver_base.tox to /project1')
        return False

    ws = None
    for name in ('webserver1', 'webserver', 'server'):
        ws = base.op(name)
        if ws is not None and getattr(ws, 'type', '') == 'webserver':
            break
        ws = None
    if ws is None:
        for ch in base.findChildren(depth=3):
            if getattr(ch, 'type', '') == 'webserver':
                ws = ch
                break
    if ws is None:
        print('No WebServer DAT inside', base.path)
        return False

    try:
        ws.par.port = 9981
    except Exception:
        pass
    try:
        ws.par.active = False
        ws.par.active = True
    except Exception:
        pass

    print('MCP WebServer:', ws.path)
    print('  active =', ws.par.active.eval())
    print('  port   =', ws.par.port.eval())
    print('Textport should show: ===== HTTP SERVER STARTED =====')
    print('Then restart TouchDesigner MCP in Cursor (Settings → MCP → touchdesigner)')
    return True


def diag_mcp():
    """Print MCP / webserver status to Textport."""
    print('=== TouchDesigner grid diagnostic ===')
    print('Project folder:', project.folder)
    parent = _project_parent()
    print('Project COMP:', parent.path if parent else None)
    servers = []
    try:
        for o in op('/').findChildren():
            if getattr(o, 'type', '') == 'webserver':
                port = None
                try:
                    port = o.par.port.eval()
                except Exception:
                    pass
                active = None
                try:
                    active = o.par.active.eval()
                except Exception:
                    pass
                servers.append((o.path, active, port))
    except Exception as e:
        print('Webserver scan error:', e)
    if servers:
        for path, active, port in servers:
            print('Web Server:', path, 'active=', active, 'port=', port)
    else:
        print('No Web Server DAT found — MCP in Cursor will return 404 until TD server is running.')
        print('Add/start mcp_webserver_base from touchdesigner-mcp-td in this toe.')
    pm = op('/project1/performance_mode')
    if pm is None and parent:
        pm = parent.op('performance_mode')
    print('performance_mode:', pm.path if pm else 'NOT BUILT')
    print('=====================================')
    return {'folder': project.folder, 'servers': servers, 'performance_mode': pm.path if pm else None}


def _safe_teardown(comp_path):
    """Close windows referencing comp before destroy — avoids TD crash on rebuild."""
    existing = op(comp_path)
    if existing is None:
        return
    try:
        win = op('/output_window')
        if win is not None:
            try:
                win.par.winclose.pulse()
            except Exception:
                pass
            win.par.drawwindow = False
    except Exception:
        pass
    try:
        existing.destroy()
    except Exception:
        pass
