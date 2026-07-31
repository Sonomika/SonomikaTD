import json
import os

_RECORDING_NORMALIZE_PROCESS = None
_RECORDING_NORMALIZE_OUTPUT = ''

try:
    ParMode
except NameError:
    try:
        from td import ParMode
    except Exception:
        class ParMode:
            CONSTANT = 0
            EXPRESS = 1
            EXPORT = 2
            BIND = 3
            EXPRESSION = 1


def _now_seconds():
    try:
        return float(absTime.seconds)
    except Exception:
        pass
    r = _root()
    if r is not None:
        try:
            return float(r.time.seconds)
        except Exception:
            pass
    try:
        import time
        return float(time.time())
    except Exception:
        return 0.0


def _program_out_expr():
    # global_fx_out is a passthrough when no global effects are loaded, so it is
    # always the stable final program route.
    return "op('global_fx_out')"


def take_program_screenshot():
    """Save the current post-effects program frame beside the project."""
    r = _root()
    settings = _settings_op()
    source = r.op('global_fx_out') if r is not None else None
    if source is None or settings is None:
        print('Screenshot failed: final program output is unavailable')
        return None
    try:
        folder_value = str(settings.par.Screenshotfolder.eval()).strip()
        folder_value = folder_value or 'screenshots'
        folder = (
            os.path.normpath(folder_value)
            if os.path.isabs(folder_value)
            else os.path.join(str(project.folder), folder_value)
        )
        os.makedirs(folder, exist_ok=True)
        stamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(folder, 'Sonomika_{}.png'.format(stamp))
        source.cook(force=True)
        source.save(path)
        print('Screenshot saved -> {}'.format(path))
        return path
    except Exception as exc:
        print('Screenshot failed: {}'.format(exc))
        return None


def _set_recording_status(value):
    settings = _settings_op()
    if settings is not None:
        try:
            settings.par.Recordingstatus = value
        except Exception:
            pass


def _poll_recording_normalization():
    """Update the Rec status when the background FFmpeg job completes."""
    global _RECORDING_NORMALIZE_PROCESS, _RECORDING_NORMALIZE_OUTPUT
    process = _RECORDING_NORMALIZE_PROCESS
    if process is None:
        return
    result = process.poll()
    if result is None:
        _defer_run(
            _poll_recording_normalization,
            delayMilliSeconds=250,
            fromOP=_root(),
        )
        return
    output_path = _RECORDING_NORMALIZE_OUTPUT
    _RECORDING_NORMALIZE_PROCESS = None
    _RECORDING_NORMALIZE_OUTPUT = ''
    if result == 0 and os.path.isfile(output_path):
        _set_recording_status(
            'Normalized: {}'.format(os.path.basename(output_path)))
        print('Normalized recording audio -> {}'.format(output_path))
    else:
        _set_recording_status('Normalization failed (original kept)')
        print('Audio normalization failed; original recording was kept')


def _normalize_recording_audio(path, target_lufs=-14):
    """Create a loudness-normalized copy without blocking TouchDesigner."""
    global _RECORDING_NORMALIZE_PROCESS, _RECORDING_NORMALIZE_OUTPUT
    try:
        import shutil
        import subprocess
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            # TouchDesigner ships FFmpeg beside its executable, but that folder
            # is not necessarily included in the process PATH.
            candidates = []
            try:
                candidates.append(os.path.join(str(app.binFolder), 'ffmpeg.exe'))
            except Exception:
                pass
            try:
                import sys
                candidates.append(os.path.join(
                    os.path.dirname(os.path.abspath(sys.executable)),
                    'ffmpeg.exe',
                ))
            except Exception:
                pass
            ffmpeg = next(
                (candidate for candidate in candidates
                 if candidate and os.path.isfile(candidate)),
                None,
            )
        if not ffmpeg:
            _set_recording_status('Normalization unavailable: FFmpeg not found')
            print('Audio normalization skipped: FFmpeg was not found in PATH')
            return False
        stem, extension = os.path.splitext(path)
        output_path = '{}_normalized{}'.format(stem, extension)
        try:
            target_lufs = -10 if int(target_lufs) == -10 else -14
        except Exception:
            target_lufs = -14
        command = [
            ffmpeg, '-y', '-i', path,
            '-map', '0:v:0', '-map', '0:a:0',
            '-c:v', 'copy',
            '-af', 'loudnorm=I={}:TP=-1:LRA=11'.format(target_lufs),
            # TouchDesigner's bundled FFmpeg does not include an AAC encoder.
            # MP3 is supported by both that build and the MP4 container.
            '-c:a', 'libmp3lame', '-b:a', '192k',
            output_path,
        ]
        startupinfo = None
        creationflags = 0
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        _RECORDING_NORMALIZE_PROCESS = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
        _RECORDING_NORMALIZE_OUTPUT = output_path
        _set_recording_status('Normalizing audio...')
        _defer_run(
            _poll_recording_normalization,
            delayMilliSeconds=250,
            fromOP=_root(),
        )
        return True
    except Exception as exc:
        _RECORDING_NORMALIZE_PROCESS = None
        _RECORDING_NORMALIZE_OUTPUT = ''
        _set_recording_status('Normalization failed (original kept)')
        print('Audio normalization failed: {}'.format(exc))
        return False


def toggle_screen_recording():
    """Start or stop recording the final program, with optional app audio."""
    r = _root()
    settings = _settings_op()
    try:
        _pin_settings_tab('Rec')
    except Exception:
        pass
    source = r.op('global_fx_out') if r is not None else None
    if r is None or settings is None or source is None:
        print('Recording failed: final program output is unavailable')
        return False
    recorder = r.op('screen_recorder')
    if recorder is None:
        try:
            recorder = r.create('moviefileoutTOP', 'screen_recorder')
            source.outputConnectors[0].connect(recorder.inputConnectors[0])
            recorder.nodeX = source.nodeX + 220
            recorder.nodeY = source.nodeY
        except Exception as exc:
            print('Recording failed: {}'.format(exc))
            return False
    try:
        is_recording = bool(recorder.par.record.eval())
    except Exception:
        is_recording = False
    if is_recording:
        try:
            recording_path = str(recorder.par.file.eval())
            normalize_audio = False
            target_lufs = -14
            try:
                normalize_audio = (
                    bool(settings.par.Recordaudio.eval())
                    and bool(settings.par.Normalizerecordingaudio.eval())
                )
                target_lufs = (
                    -10
                    if str(settings.par.Recordingloudness.eval()) == 'loud'
                    else -14
                )
            except Exception:
                pass
            recorder.par.record = False
            settings.par.Recordingstatus = 'Stopped'
            print('Screen recording stopped')
            if normalize_audio and recording_path:
                # Give Movie File Out time to close and finalize its container.
                _defer_run(
                    lambda: _normalize_recording_audio(
                        recording_path, target_lufs),
                    delayMilliSeconds=750,
                    fromOP=r,
                )
            try:
                _pin_settings_tab('Rec')
            except Exception:
                pass
            return False
        except Exception as exc:
            print('Could not stop recording: {}'.format(exc))
            return True
    try:
        folder_value = str(settings.par.Recordingfolder.eval()).strip()
        folder_value = folder_value or 'recordings'
        folder = (
            os.path.normpath(folder_value)
            if os.path.isabs(folder_value)
            else os.path.join(str(project.folder), folder_value)
        )
        os.makedirs(folder, exist_ok=True)
        stamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
        codec_names = list(recorder.par.videocodec.menuNames)
        use_h264 = 'h264' in codec_names
        if use_h264:
            recorder.par.videocodec = 'h264'
        try:
            quality = max(0.0, min(1.0, float(
                settings.par.Recordingquality.eval())))
        except Exception:
            quality = 0.75
        # Dense particle motion needs far more bitrate than the Movie File Out
        # default. Scale a 12–100 Mbps 1080p target by output pixel count.
        try:
            pixels = max(1, int(source.width) * int(source.height))
        except Exception:
            pixels = 1920 * 1080
        resolution_scale = max(0.5, float(pixels) / float(1920 * 1080))
        avg_kbps = min(
            240000.0,
            (12000.0 + quality * quality * 88000.0) * resolution_scale)
        peak_kbps = min(300000.0, avg_kbps * 1.25)
        try:
            recorder.par.qualityscale = quality
        except Exception:
            pass
        try:
            modes = list(recorder.par.qualitymode.menuNames)
            wanted = (
                'high' if quality >= 0.38
                else 'balanced')
            if wanted in modes:
                recorder.par.qualitymode = wanted
        except Exception:
            pass
        try:
            profiles = list(recorder.par.profile.menuNames)
            if 'high' in profiles:
                recorder.par.profile = 'high'
        except Exception:
            pass
        try:
            rate_modes = list(recorder.par.ratecontrolmode.menuNames)
            if 'variablehq' in rate_modes:
                recorder.par.ratecontrolmode = 'variablehq'
            elif 'variable' in rate_modes:
                recorder.par.ratecontrolmode = 'variable'
        except Exception:
            pass
        try:
            recorder.par.avgbitrate = avg_kbps
            recorder.par.peakbitrate = peak_kbps
        except Exception:
            pass
        extension = '.mp4' if use_h264 else '.mov'
        path = os.path.join(folder, 'Sonomika_{}{}'.format(stamp, extension))
        recorder.par.file = path
        try:
            recorder.par.fps = float(project.cookRate)
        except Exception:
            pass
        record_audio = bool(settings.par.Recordaudio.eval())
        audio = r.op('audio_engine/out_record') if record_audio else None
        device = r.op('audio_engine/audiodevin1') if record_audio else None
        try:
            audio_active = bool(settings.par.Audioactive.eval())
            device_active = bool(device.par.active.eval())
            device_ok = not bool(device.errors())
            stream_ok = (
                int(audio.numChans) > 0
                and int(audio.numSamples) > 0
                and float(audio.rate) >= 8000.0
            )
            if not (audio_active and device_active and device_ok and stream_ok):
                audio = None
        except Exception:
            audio = None
        recorder.par.audiochop = audio if audio is not None else ''
        recorder.par.record = True
        settings.par.Recordingstatus = (
            'Recording with audio' if audio is not None else 'Recording video only')
        print('Screen recording started -> {}'.format(path))
        try:
            _pin_settings_tab('Rec')
        except Exception:
            pass
        return True
    except Exception as exc:
        try:
            recorder.par.record = False
            settings.par.Recordingstatus = 'Error'
        except Exception:
            pass
        print('Recording failed: {}'.format(exc))
        return False


def _set_top_expr(top, expr):
    if top is None or not expr:
        return False
    try:
        top.par.top.expr = expr
        try:
            top.par.top.mode = ParMode.EXPRESS
        except Exception:
            try:
                top.par.top.mode = ParMode.EXPRESSION
            except Exception:
                pass
        return True
    except Exception:
        return False

NUM_COLS = 30
VISIBLE_COLS = 16
VISIBLE_ROWS = 9
MIN_LAYERS = 4
MAX_LAYERS = 9
DEFAULT_LAYERS = 4
CELL_LABEL_H = 16
CELL_H = 64
CELL_W = 128
CELL_GAP = 2
CELL_ASPECT = 16.0 / 9.0
CELL_TOPFILL = 'best'
ROW_LABEL_W = 72
ROW_OPACITY_W = 14
ROW_OPACITY_FADER_W = 58
ROW_OPACITY_HDR_W = 58
ROW_OPACITY_RIGHT_PAD = 14
UI_W = 1920
UI_H = 1080
SETTINGS_PANEL_EXTRA_W = 80
PREVIEW_W = UI_W // 2 - SETTINGS_PANEL_EXTRA_W
UI_PANEL_W = UI_W - PREVIEW_W
UI_PANEL_X = PREVIEW_W
GRID_VIEW_W = UI_W
BOTTOM_ZONE_MIN = 360
GRID_X0 = ROW_LABEL_W + ROW_OPACITY_HDR_W + CELL_GAP + ROW_OPACITY_RIGHT_PAD + CELL_GAP
_CLIPBOARD = {
    'type': '', 'path': '', 'source_layer': None, 'source_col': None,
    'is_cut': False, 'par_state': [], 'cell_fx': [], 'map_control': {},
    'render_scale': 100, 'update_rate': 1, 'frozen': False,
}
_COLUMN_CLIPBOARD = {'source_col': None, 'cells': []}
_FX_CLIPBOARD = {
    'path': '', 'label': '', 'bypass': False, 'expanded': False, 'par_state': [],
}
_PRIMED_VIDEO = {}
_GLOBAL_TRANSPORT_PLAYING = True
_TIMELINE_RATE_WHEN_PLAYING = 60.0
_PARAMS_UI_STATE = {'target_path': None, 'settings_target_path': None, 'selected_cell_key': None}
_SCENE_GRID_DIMS = {}
_SCENE_PARAM_STATE = {}
_CELL_PAR_LAST_GOOD = {}
_GRID_SCROLL_V = 0.0
_LAST_UI_LIVE_CELLS = set()
_LAST_LIVE_SLOT_COLS = {}
_THUMB_LAST_REFRESH = {}
TOX_FEED_SCALE = 0.5
TOX_FEED_MIN_W = 320
TOX_FEED_MIN_H = 180
TOX_FEED_MAX_W = 512
TOX_FEED_MAX_H = 512


def _td_timeline():
    """Project root timeline (TouchDesigner playbar)."""
    try:
        return op('/').time
    except Exception:
        return None


def global_transport_playing():
    """Performance-mode transport; mirrored to the TD timeline in _set_global_transport_playing."""
    return bool(_GLOBAL_TRANSPORT_PLAYING)


def _set_global_transport_playing(on):
    """Keep TD's UI timeline running; pause media independently.

    A zero-rate timeline prevents Panel Execute/PopMenu interaction in some
    packaged projects, including cell right-click menus. Grid media and TOX
    animation are already paused separately by _sync_layer_slot_pause_states.
    """
    global _GLOBAL_TRANSPORT_PLAYING, _TIMELINE_RATE_WHEN_PLAYING
    on = bool(on)
    _GLOBAL_TRANSPORT_PLAYING = on
    t = _td_timeline()
    if t is None:
        return
    try:
        if on:
            try:
                cur = float(getattr(t, 'rate', 0) or 0)
            except Exception:
                cur = 0.0
            restore = float(_TIMELINE_RATE_WHEN_PLAYING or 0) or 60.0
            # Pause uses rate 0; treat near-zero as paused too (stale/partial pauses).
            if cur < 1.0:
                try:
                    t.rate = restore if restore >= 1.0 else 60.0
                except Exception:
                    try:
                        t.rate = 60.0
                    except Exception:
                        pass
            t.play = True
        else:
            try:
                cur = float(getattr(t, 'rate', 60.0) or 60.0)
                if cur >= 1.0:
                    _TIMELINE_RATE_WHEN_PLAYING = cur
            except Exception:
                pass
            t.play = True
            try:
                restore = float(_TIMELINE_RATE_WHEN_PLAYING or 0) or 60.0
                t.rate = restore if restore >= 1.0 else 60.0
            except Exception:
                t.play = True
    except Exception:
        pass


def goto_timeline_start():
    """Jump TouchDesigner playhead to timeline start (transport rewind-to-start)."""
    t = _td_timeline()
    if t is None:
        return False
    try:
        start = float(t.start)
    except Exception:
        start = 1.0
    ok = False
    try:
        t.frame = start
        ok = True
    except Exception:
        try:
            t.frame = 1
            ok = True
        except Exception:
            ok = False
    if ok:
        try:
            _sync_transport_button_states()
        except Exception:
            pass
    return ok


PARAM_PANEL_H = 220
SETTINGS_PANEL_MIN_W = 320
SETTINGS_TAB_GRID_OSC = 'GrdOSC'
SETTINGS_TAB_PERF = 'Perf'
SETTINGS_TAB_GRID_OSC_LEGACY = ('Grid OSC', 'GRID OSC')


def _canonical_settings_tab_name(page_name):
    name = str(page_name or '')
    if name in SETTINGS_TAB_GRID_OSC_LEGACY:
        return SETTINGS_TAB_GRID_OSC
    if name == 'Performance':
        return SETTINGS_TAB_PERF
    return name


def _migrate_settings_tab_names(settings=None):
    """Shorten tab labels so all settings pages fit the equal-width Perform panels."""
    if settings is None:
        try:
            settings = _settings()
        except Exception:
            settings = None
    if settings is None:
        return
    for pg in list(settings.customPages):
        try:
            pg.name = _canonical_settings_tab_name(pg.name)
        except Exception:
            pass


MIN_SCENES = 1
MAX_SCENES = 32
DEFAULT_SCENES = 1
SCENE_BTN_W = 28
SCENE_BTN_H = 22
TRANSPORT_ICON_PX = 64
TRANSPORT_ICON_SCALE = 0.42
SCENE_BAR_H = 26
SCENE_BAR_TOP_PAD = 12
SCENE_BAR_CONTENT_Y = 4
SCENE_BAR_LOGO_PAD = 8
SCENE_BAR_LOGO_TEXT_W = 36  # approx width of centered Layer / L# labels in ROW_LABEL_W
SCENE_BAR_LOGO_X = max(SCENE_BAR_LOGO_PAD, (ROW_LABEL_W - SCENE_BAR_LOGO_TEXT_W) // 2)
SCENE_BAR_LOGO_GAP = 10
SCENE_BAR_LOGO_Y_NUDGE = 1
SCENE_BAR_LOGO_X_NUDGE = 2
LOGO_NATURAL_W = 1808
LOGO_NATURAL_H = 318
LOGO_H = 18
LOGO_W = int(round(LOGO_H * LOGO_NATURAL_W / LOGO_NATURAL_H))
SCENE_GRID_GAP = 12
GRID_HDR_H = 30
GRID_HDR_PAD = 2
TRANSPORT_ICON_TO_START = '\u23ee'  # ⏮ skip to start
TRANSPORT_ICON_PLAY = '\u25b6'   # ▶
TRANSPORT_ICON_PAUSE = '\u275a \u275a'  # two bars (not U+23F8 — draws a box in Symbol font)
SCENE_TRANSPORT_BUTTONS = ('scene_to_start', 'scene_play', 'scene_pause')
TRANSPORT_ICON_FONT_SIZE = GRID_FONT_SIZE
VIDEO_EXTS = {
    '.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv',
    '.mpg', '.mpeg', '.mxf', '.gif', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp',
}
VALID_CLIP_TYPES = ('video', 'tox')
_EMBEDDED_DAT_CACHE = {}


def clear_embedded_dat_cache(names=None):
    """Drop cached embedded DAT sources (call after script reload)."""
    if not names:
        _EMBEDDED_DAT_CACHE.clear()
        return
    for name in names:
        _EMBEDDED_DAT_CACHE.pop(name, None)
INFRA_COMP_LEGACY = '/sonomika_infra'
SETTINGS_COMP = '/settings'
SETTINGS_COMP_LEGACY = '/sonomika_infra/settings'
PROGRAM_PICK_COMP = '/program_pick'
PROGRAM_PICK_COMP_LEGACY = '/sonomika_infra/program_pick'
_LEGACY_INFRA_PATH_REPLACEMENTS = (
    ("'/sonomika_infra/settings'", "'/settings'"),
    ('"/sonomika_infra/settings"', '"/settings"'),
    ("op('/sonomika_infra/settings')", "op('/settings')"),
    ('op("/sonomika_infra/settings")', 'op("/settings")'),
    ("'/sonomika_infra/program_pick'", "'/program_pick'"),
    ('"/sonomika_infra/program_pick"', '"/program_pick"'),
    ("op('/sonomika_infra/program_pick')", "op('/program_pick')"),
    ('op("/sonomika_infra/program_pick")', 'op("/program_pick")'),
)


SONOMIKA_SCRIPTS_STORE_KEY = 'sonomika_scripts_dir'


def _is_scripts_dir(path):
    if not path:
        return False
    return os.path.isdir(os.path.join(os.path.normpath(str(path)), 'performance_grid'))


def _walk_up_scripts_dir(start_dir, max_levels=8):
    d = os.path.normpath(str(start_dir or ''))
    if not d or not os.path.isdir(d):
        return ''
    for _ in range(max_levels):
        scripts = os.path.join(d, 'scripts')
        if _is_scripts_dir(scripts):
            return os.path.normpath(scripts).replace('\\', '/')
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return ''


def _stored_scripts_dir():
    try:
        stored = str(op('/').fetch(SONOMIKA_SCRIPTS_STORE_KEY, '') or '').strip()
        if _is_scripts_dir(stored):
            return os.path.normpath(stored).replace('\\', '/')
    except Exception:
        pass
    return ''


def _remember_scripts_dir(scripts_dir):
    if not _is_scripts_dir(scripts_dir):
        return
    try:
        op('/').store(
            SONOMIKA_SCRIPTS_STORE_KEY,
            os.path.normpath(str(scripts_dir)).replace('\\', '/'),
        )
    except Exception:
        pass


def _discover_scripts_dir():
    stored = _stored_scripts_dir()
    if stored:
        return stored
    env = os.environ.get('SONOMIKA_TD_ROOT', '').strip()
    if env:
        scripts = os.path.join(env, 'scripts')
        if _is_scripts_dir(scripts):
            _remember_scripts_dir(scripts)
            return os.path.normpath(scripts).replace('\\', '/')
    try:
        proj = op('/').project
        pf = str(getattr(proj, 'folder', '') or '').strip()
        toe = str(getattr(proj, 'file', '') or getattr(proj, 'savePath', '') or '').strip()
    except Exception:
        pf = ''
        toe = ''
    candidates = []
    if pf:
        candidates.extend([
            os.path.join(pf, 'scripts'),
            os.path.join(pf, 'SonomikaTD', 'scripts'),
            _walk_up_scripts_dir(pf),
        ])
    if toe:
        toe_dir = os.path.dirname(toe)
        candidates.extend([
            os.path.join(toe_dir, 'scripts'),
            os.path.join(toe_dir, 'SonomikaTD', 'scripts'),
            os.path.join(os.path.dirname(toe_dir), 'SonomikaTD', 'scripts'),
            _walk_up_scripts_dir(toe_dir),
        ])
    seen = set()
    for scripts in candidates:
        if not scripts:
            continue
        scripts = os.path.normpath(scripts).replace('\\', '/')
        if scripts in seen:
            continue
        seen.add(scripts)
        if _is_scripts_dir(scripts):
            _remember_scripts_dir(scripts)
            return scripts
    return ''


def _package_root():
    """SonomikaTD repo root — logic DAT cannot import performance_grid.paths."""
    scripts = _discover_scripts_dir()
    if scripts:
        return os.path.normpath(os.path.dirname(scripts)).replace('\\', '/')
    return ''


_CELL_CHANGE_LOG_KEY = 'sonomika_cell_change_trail'
_CELL_CHANGE_LOG_LAST_KEY = 'sonomika_cell_change_last'
_CELL_CHANGE_LOG_MAX = 48
_CELL_CHANGE_LOG_FILE = 'sonomika_cell_change.log'


def _cell_change_log_path():
    for base in (
        lambda: str(op('/').project.folder or '').strip(),
        _package_root,
    ):
        try:
            folder = base() if callable(base) else ''
            if folder:
                return os.path.join(folder, _CELL_CHANGE_LOG_FILE).replace('\\', '/')
        except Exception:
            pass
    return _CELL_CHANGE_LOG_FILE


def _cell_change_root():
    try:
        r = _root()
        if r is not None:
            return r
    except Exception:
        pass
    try:
        return op('/project1/performance_mode')
    except Exception:
        return None


def cell_change_log(step, detail='', exc=None):
    """Record cell-focus steps for native-crash diagnosis (last line = fault)."""
    try:
        if not bool(_root().fetch('sonomika_cell_change_debug', False)):
            return
    except Exception:
        return
    import time
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    frame = ''
    try:
        frame = str(absTime.frame)
    except Exception:
        pass
    msg = '[{} frame {}] {}'.format(ts, frame, step)
    if detail:
        msg += ' | ' + str(detail)
    if exc is not None:
        msg += ' | ERR ' + str(exc)
    print('Sonomika cell:', msg)
    entry = {
        't': ts,
        'frame': frame,
        'step': str(step),
        'detail': str(detail or ''),
    }
    if exc is not None:
        entry['error'] = str(exc)
    r = _cell_change_root()
    if r is not None:
        try:
            import json
            trail = []
            try:
                raw = r.fetch(_CELL_CHANGE_LOG_KEY, '[]')
                if isinstance(raw, str):
                    trail = json.loads(raw) if raw else []
                elif isinstance(raw, (list, tuple)):
                    trail = list(raw)
            except Exception:
                trail = []
            trail.append(entry)
            trail = trail[-_CELL_CHANGE_LOG_MAX:]
            r.store(_CELL_CHANGE_LOG_KEY, json.dumps(trail))
            r.store(_CELL_CHANGE_LOG_LAST_KEY, msg)
        except Exception:
            pass
    try:
        with open(_cell_change_log_path(), 'a', encoding='utf-8') as fh:
            fh.write(msg + '\n')
    except Exception:
        pass


def _defer_run(callback, delayFrames=1, fromOP=None, delayMilliSeconds=None):
    """Schedule callback; use wall-clock when paused so UI/MIDI still advance."""
    if fromOP is None:
        fromOP = _cell_change_root()
    # Timeline pause freezes delayFrames; prefer milliseconds then.
    use_ms = delayMilliSeconds
    if use_ms is None:
        try:
            if not global_transport_playing():
                use_ms = max(1, int(delayFrames) * 16)
        except Exception:
            use_ms = None
    try:
        if use_ms is not None:
            run(callback, delayMilliSeconds=int(use_ms), fromOP=fromOP)
            return True
        run(callback, delayFrames=int(delayFrames), fromOP=fromOP)
        return True
    except Exception as exc:
        cell_change_log('defer.run.error', exc=exc)
        return False


def dump_cell_change_trail():
    """Print recent cell-change steps (run from Textport after a crash)."""
    r = _cell_change_root()
    lines = ['--- sonomika cell change trail ---']
    if r is not None:
        try:
            lines.append('last: ' + str(r.fetch(_CELL_CHANGE_LOG_LAST_KEY, '(none)')))
        except Exception:
            pass
        try:
            import json
            raw = r.fetch(_CELL_CHANGE_LOG_KEY, '[]')
            trail = json.loads(raw) if isinstance(raw, str) else list(raw or [])
            for row in trail[-20:]:
                lines.append(
                    '{t} f{frame} {step} {detail}'.format(
                        t=row.get('t', ''),
                        frame=row.get('frame', ''),
                        step=row.get('step', ''),
                        detail=row.get('detail', ''),
                    ).strip())
        except Exception as exc:
            lines.append('trail read failed: ' + str(exc))
    try:
        path = _cell_change_log_path()
        lines.append('log file: ' + path)
        with open(path, 'r', encoding='utf-8') as fh:
            tail = fh.readlines()[-20:]
        lines.extend([ln.rstrip() for ln in tail])
    except Exception as exc:
        lines.append('log file read failed: ' + str(exc))
    text = '\n'.join(lines)
    print(text)
    return text


def _settings_comp_path():
    for path in (SETTINGS_COMP, SETTINGS_COMP_LEGACY):
        try:
            if op(path) is not None:
                return path
        except Exception:
            pass
    return SETTINGS_COMP


def _settings():
    try:
        s = _find_settings_comp()
        if s is not None:
            return s
        return op(_settings_comp_path())
    except Exception:
        return None


def _settings_op():
    return _settings()


def _program_pick_path():
    for path in (PROGRAM_PICK_COMP, PROGRAM_PICK_COMP_LEGACY):
        try:
            if op(path) is not None:
                return path
        except Exception:
            pass
    return PROGRAM_PICK_COMP


def _program_pick():
    try:
        return op(_program_pick_path())
    except Exception:
        return None


def _set_node_viewer(node, visible):
    if node is None:
        return
    try:
        node.viewer = bool(visible)
    except Exception:
        pass


def _move_to_root(node):
    td_root = op('/')
    if node is None or td_root is None:
        return None
    try:
        if node.parent() == td_root:
            return node
        copied = td_root.copy(node, name=node.name, includeDocked=True)
        try:
            node.destroy()
        except Exception:
            pass
        return copied or td_root.op(node.name)
    except Exception:
        return node


def _find_settings_comp():
    for path in (SETTINGS_COMP, SETTINGS_COMP_LEGACY, '/project1/settings'):
        try:
            s = op(path)
            if s is not None:
                return s
        except Exception:
            pass
    try:
        for ch in op('/').findChildren(depth=4):
            if ch.name == 'settings' and ch.isCOMP:
                return ch
    except Exception:
        pass
    return None


def _heal_legacy_infra_path_refs():
    """Rewrite parameter expressions still pointing at /sonomika_infra/*."""
    healed = 0
    try:
        nodes = op('/').findChildren()
    except Exception:
        return 0
    for node in nodes:
        try:
            pars = node.pars()
        except Exception:
            continue
        for par in pars:
            for field in ('expr', 'bindExpr'):
                try:
                    raw = str(getattr(par, field, '') or '')
                except Exception:
                    continue
                if INFRA_COMP_LEGACY not in raw:
                    continue
                new = raw
                for old, repl in _LEGACY_INFRA_PATH_REPLACEMENTS:
                    new = new.replace(old, repl)
                if new == raw:
                    continue
                try:
                    setattr(par, field, new)
                    healed += 1
                except Exception:
                    pass
    return healed


def restore_root_settings_layout(reposition=False):
    """Move /settings to project root and remove sonomika_infra."""
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
        elif root_node is None:
            try:
                legacy = op(INFRA_COMP_LEGACY + '/' + name)
            except Exception:
                legacy = None
            if legacy is not None:
                _move_to_root(legacy)

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

    settings = _find_settings_comp()
    if settings is not None and settings.parent() != td_root:
        settings = _move_to_root(settings)
    if settings is not None:
        if reposition:
            try:
                perform = op('/perform')
                settings.nodeX = float(perform.nodeX) + 220 if perform else settings.nodeX
                settings.nodeY = float(perform.nodeY) - 300 if perform else settings.nodeY
            except Exception:
                pass
        _set_node_viewer(settings, False)
    pick = td_root.op('program_pick')
    if pick is not None:
        _set_node_viewer(pick, False)
    _set_node_viewer(td_root.op('local'), False)
    for path in ('/mcp_webserver_base', '/project1/mcp_webserver_base'):
        try:
            mcp = op(path)
            if mcp is not None:
                _set_node_viewer(mcp, False)
        except Exception:
            pass
    _heal_legacy_infra_path_refs()
    try:
        _refresh_settings_params_panel()
    except Exception:
        pass
    return settings


def tidy_root_network_view(layout=False):
    """Hide technical nodes; layout=True also repositions root tiles (first-time setup only)."""
    td_root = op('/')
    if td_root is None:
        return False
    restore_root_settings_layout(reposition=layout)
    if not layout:
        try:
            _refresh_settings_params_panel()
        except Exception:
            pass
        return True

    perform = op('/perform')
    try:
        bx = float(perform.nodeX) if perform is not None else 0.0
        by = float(perform.nodeY) if perform is not None else 0.0
    except Exception:
        bx, by = 0.0, 0.0

    project = op('/project1')
    if project is not None:
        try:
            project.nodeX = bx
            project.nodeY = by - 300
            project.viewer = True
        except Exception:
            pass

    settings = td_root.op('settings')
    if settings is not None:
        try:
            settings.nodeX = bx + 220
            settings.nodeY = by - 300
            _set_node_viewer(settings, False)
        except Exception:
            pass

    pick = td_root.op('program_pick')
    if pick is not None:
        try:
            pick.nodeX = bx + 200
            pick.nodeY = by
            _set_node_viewer(pick, False)
        except Exception:
            pass

    for name, ox, oy, show in (
        ('out1', 400, 0, True),
        ('output_window', 400, 200, False),
        ('SonomikaTD', 600, 0, True),
    ):
        node = td_root.op(name)
        if node is None:
            continue
        try:
            node.nodeX = bx + ox
            node.nodeY = by + oy
            _set_node_viewer(node, show)
        except Exception:
            pass

    for path in ('/mcp_webserver_base', '/project1/mcp_webserver_base'):
        try:
            mcp = op(path)
            if mcp is not None:
                mcp.nodeX = bx + 440
                mcp.nodeY = by - 300
                _set_node_viewer(mcp, False)
        except Exception:
            pass

    _set_node_viewer(td_root.op('local'), False)
    try:
        _refresh_settings_params_panel()
    except Exception:
        pass
    return True


def _unwrap_embedded_dat_text(text):
    """Strip `NAME = r'''` wrappers from embedded DAT source files."""
    text = str(text or '')
    first = text.find("r'''")
    if first >= 0:
        text = text[first + 4:]
    last = text.rfind("'''")
    if last >= 0:
        text = text[:last]
    if text.startswith('\n'):
        text = text[1:]
    return text


def _read_embedded_dat_validated(name, marker=None):
    """Load embedded DAT text; retry once from disk if marker is missing."""
    text = _read_embedded_dat(name)
    if marker and (not text or marker not in text):
        clear_embedded_dat_cache((name,))
        text = _read_embedded_dat(name)
    return text or ''


def _read_embedded_dat(name):
    """Load embedded DAT source from performance_grid/embedded (disk or assemble)."""
    if name in _EMBEDDED_DAT_CACHE:
        return _EMBEDDED_DAT_CACHE[name]
    text = None
    try:
        from performance_grid.assemble import read_embedded
        text = read_embedded(name)
    except Exception:
        pass
    if not text:
        scripts = _discover_scripts_dir()
        if scripts:
            path = os.path.join(scripts, 'performance_grid', 'embedded', name)
            if os.path.isfile(path):
                try:
                    with open(path, encoding='utf-8') as fh:
                        text = _unwrap_embedded_dat_text(fh.read())
                except Exception:
                    pass
    if text:
        _EMBEDDED_DAT_CACHE[name] = text
    return text
