PERF_READOUT_PAD = 10
PERF_READOUT_GAP = 14
PERF_GPU_W = 126
PERF_FRAME_W = 158
PERF_FPS_W = 72
_PERF_LAST_SAMPLE = {'seconds': None, 'frame': None}
_PERF_REALTIME_SAMPLE = {'t': None, 'fps': None, 'frame_ms': None}


def _perf_readouts_total_w():
    return PERF_GPU_W + PERF_FRAME_W + PERF_FPS_W + PERF_READOUT_GAP * 2


def _perf_readouts_x0():
    return max(0, UI_W - _perf_readouts_total_w() - PERF_READOUT_PAD)


def _style_perf_readout_text(txt, w, h, text=''):
    txt.par.text = text or ''
    txt.par.resolutionw = max(32, int(w))
    txt.par.resolutionh = max(14, int(h))
    _apply_grid_font(txt)
    txt.par.bgalpha = 0.0
    txt.par.alignx = 'left'
    txt.par.aligny = 'center'
    txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = TD_TEXT_ACTIVE


def _ensure_perf_readout(bar, name, w):
    if bar is None:
        return None
    comp = bar.op(name)
    if comp is None:
        comp = bar.create('containerCOMP', name)
    inner_h = max(14, SCENE_BAR_H - 4)
    try:
        comp.par.w = w
        comp.par.h = inner_h
        comp.par.y = SCENE_BAR_CONTENT_Y
        comp.par.hmode = 'fixed'
        comp.par.vmode = 'fixed'
        comp.par.align = 'none'
        comp.par.display = True
        comp.par.enable = True
        comp.par.clickthrough = True
        comp.par.drop = 'dropno'
        comp.par.drag = 'dragno'
        comp.par.bgalpha = 0.0
    except Exception:
        pass
    txt = comp.op('readout_text')
    if txt is None:
        txt = comp.create('textTOP', 'readout_text')
    _style_perf_readout_text(txt, w, inner_h, '')
    try:
        comp.par.top = txt
        comp.par.topfill = 'fit'
    except Exception:
        pass
    return comp


def _ensure_perf_stats_chop(bar):
    if bar is None:
        return None
    chop = bar.op('perf_stats')
    if chop is None:
        try:
            chop = bar.create('performCHOP', 'perf_stats')
        except Exception:
            chop = None
    if chop is not None:
        try:
            chop.allowCooking = True
        except Exception:
            pass
        for pname in ('fps', 'msec', 'gpumemused', 'totalgpumem'):
            try:
                getattr(chop.par, pname).val = True
            except Exception:
                pass
    return chop


def _ensure_perf_readouts(bar):
    if bar is None:
        return
    _ensure_perf_stats_chop(bar)
    _ensure_perf_readout(bar, 'readout_gpu', PERF_GPU_W)
    _ensure_perf_readout(bar, 'readout_frame', PERF_FRAME_W)
    _ensure_perf_readout(bar, 'readout_fps', PERF_FPS_W)


def _layout_perf_readouts(bar):
    if bar is None:
        return
    _ensure_perf_readouts(bar)
    x = _perf_readouts_x0()
    inner_h = max(14, SCENE_BAR_H - 4)
    for name, w in (
        ('readout_gpu', PERF_GPU_W),
        ('readout_frame', PERF_FRAME_W),
        ('readout_fps', PERF_FPS_W),
    ):
        comp = bar.op(name)
        if comp is None:
            continue
        try:
            comp.par.x = x
            comp.par.y = SCENE_BAR_CONTENT_Y
            comp.par.w = w
            comp.par.h = inner_h
            comp.par.display = True
        except Exception:
            pass
        x += w + PERF_READOUT_GAP


def _chan_val(chop, names):
    if chop is None:
        return None
    for name in names:
        try:
            ch = chop.chan(name)
            if ch is not None:
                return float(ch.eval())
        except Exception:
            pass
    return None


def _stats_from_perform_chop():
    """Perform CHOP: fps, msec."""
    paths = ['/local/perform']
    try:
        r = _root()
        if r is not None:
            paths.append('{}/ui/scene_bar/perf_stats'.format(r.path))
    except Exception:
        pass
    for path in paths:
        try:
            pchop = op(path)
        except Exception:
            pchop = None
        if pchop is None or getattr(pchop, 'numChans', 0) < 1:
            continue
        fps = _chan_val(pchop, ('fps', 'FPS'))
        msec = _chan_val(pchop, ('msec', 'frame_ms', 'frametime'))
        frame_ms = None
        fps_i = None
        if fps is not None and fps > 0:
            fps_i = int(round(fps))
            if msec is not None and msec > 0:
                frame_ms = int(round(msec))
            else:
                frame_ms = int(round(1000.0 / fps))
        elif msec is not None and msec > 0:
            frame_ms = int(round(msec))
            fps_i = max(1, int(round(1000.0 / frame_ms)))
        if frame_ms is not None or fps_i is not None:
            return frame_ms, fps_i
    return None, None


def _gpu_mem_from_perform_chop():
    paths = ['/local/perform']
    try:
        r = _root()
        if r is not None:
            paths.append('{}/ui/scene_bar/perf_stats'.format(r.path))
    except Exception:
        pass
    for path in paths:
        try:
            pchop = op(path)
        except Exception:
            pchop = None
        if pchop is None or getattr(pchop, 'numChans', 0) < 1:
            continue
        used = _chan_val(pchop, ('gpu_mem_used', 'gpumemused', 'gpuMemUsed', 'gpu_used'))
        total = _chan_val(pchop, ('total_gpu_mem', 'totalgpumem', 'gpu_mem_total', 'gpuMemTotal', 'gpu_total'))
        if used is None:
            continue
        try:
            if total is not None and total > 0:
                return max(0, min(100, int(round((float(used) / float(total)) * 100.0))))
            return max(0, int(round(float(used))))
        except Exception:
            pass
    return 0


def _stats_from_abs_time():
    """absTime.step is frame count; stepSeconds is elapsed seconds (correct for timing)."""
    global _PERF_LAST_SAMPLE
    frame_ms = None
    fps = None
    try:
        step_sec = float(absTime.stepSeconds)
        if step_sec > 0.0:
            frame_ms = int(round(step_sec * 1000.0))
            fps = int(round(1.0 / step_sec))
    except Exception:
        pass
    try:
        sec = float(absTime.seconds)
        fr = float(absTime.frame)
        last = _PERF_LAST_SAMPLE
        if last['seconds'] is not None and sec > last['seconds']:
            dt = sec - last['seconds']
            df = fr - last['frame']
            if dt > 0.00001 and df >= 0.0:
                fps_delta = int(round(df / dt))
                ms_delta = int(round(1000.0 * dt / max(df, 1.0)))
                if fps_delta > 0:
                    fps = fps_delta
                if ms_delta > 0:
                    frame_ms = ms_delta
        _PERF_LAST_SAMPLE = {'seconds': sec, 'frame': fr}
    except Exception:
        pass
    return frame_ms, fps


def _stats_from_wall_clock():
    """Measured real callback FPS; avoids target-FPS readouts masking dropped frames."""
    global _PERF_REALTIME_SAMPLE
    try:
        import time
        now = time.perf_counter()
    except Exception:
        return None, None
    last_t = _PERF_REALTIME_SAMPLE.get('t')
    _PERF_REALTIME_SAMPLE['t'] = now
    if last_t is None:
        return _PERF_REALTIME_SAMPLE.get('frame_ms'), _PERF_REALTIME_SAMPLE.get('fps')
    dt = now - float(last_t)
    if dt <= 0.00001 or dt > 2.0:
        return _PERF_REALTIME_SAMPLE.get('frame_ms'), _PERF_REALTIME_SAMPLE.get('fps')
    inst_fps = 1.0 / dt
    inst_ms = dt * 1000.0
    prev_fps = _PERF_REALTIME_SAMPLE.get('fps')
    prev_ms = _PERF_REALTIME_SAMPLE.get('frame_ms')
    # Smooth enough to read, but responsive to sudden drops.
    if prev_fps is None:
        fps = inst_fps
    else:
        fps = (float(prev_fps) * 0.78) + (inst_fps * 0.22)
    if prev_ms is None:
        frame_ms = inst_ms
    else:
        frame_ms = (float(prev_ms) * 0.78) + (inst_ms * 0.22)
    _PERF_REALTIME_SAMPLE['fps'] = fps
    _PERF_REALTIME_SAMPLE['frame_ms'] = frame_ms
    return max(1, int(round(frame_ms))), max(1, int(round(fps)))


def _stats_from_monitor():
    frame_ms = None
    fps = None
    try:
        mon = op('/local/monitor')
    except Exception:
        mon = None
    if mon is None:
        return frame_ms, fps
    try:
        f = _chan_val(mon, ('fps', 'FPS'))
        if f is not None and f > 0:
            fps = int(round(f))
    except Exception:
        pass
    try:
        m = _chan_val(mon, ('msec', 'frametime', 'frame_ms'))
        if m is not None and m > 0:
            frame_ms = int(round(m))
    except Exception:
        pass
    return frame_ms, fps


def _sample_perf_stats():
    frame_ms = None
    fps = None

    ms_rt, f_rt = _stats_from_wall_clock()
    if f_rt is not None and f_rt > 0:
        fps = f_rt
    if ms_rt is not None and ms_rt > 0:
        frame_ms = ms_rt

    ms0, f0 = _stats_from_perform_chop()
    # Perform CHOP can report target FPS, so only use it as a fallback.
    if f0 is not None and f0 > 0:
        if fps is None:
            fps = f0
    if ms0 is not None and ms0 > 0:
        if frame_ms is None:
            frame_ms = ms0

    if fps is None or fps <= 1 or frame_ms is None or frame_ms >= 500:
        ms2, f2 = _stats_from_abs_time()
        if f2 is not None and f2 > 0:
            fps = f2
        if ms2 is not None and ms2 > 0:
            frame_ms = ms2

    if fps is None or fps <= 0:
        _, f3 = _stats_from_monitor()
        if f3 is not None and f3 > 0:
            fps = f3

    if frame_ms is None or frame_ms <= 0:
        if fps is not None and fps > 0:
            frame_ms = int(round(1000.0 / fps))
        else:
            frame_ms = 16

    if fps is None or fps <= 0:
        fps = max(1, int(round(1000.0 / max(frame_ms, 1))))

    return int(frame_ms), int(fps)


def _set_readout_text(comp, text):
    if comp is None:
        return
    txt = comp.op('readout_text')
    if txt is None:
        return
    try:
        w = int(float(comp.par.w.eval())) or PERF_FRAME_W
        h = max(14, int(float(comp.par.h.eval())) or SCENE_BAR_H - 4)
        _style_perf_readout_text(txt, w, h, text)
        comp.par.top = txt
        comp.par.topfill = 'fit'
    except Exception:
        pass


def _update_perf_readouts():
    r = _root()
    ui = r.op('ui') if r else None
    bar = ui.op('scene_bar') if ui else None
    if bar is None:
        return
    _ensure_perf_readouts(bar)
    frame_ms, fps = _sample_perf_stats()
    gpu_mem = _gpu_mem_from_perform_chop()
    _set_readout_text(
        bar.op('readout_gpu'),
        'GPU MEM : {:d} %'.format(gpu_mem),
    )
    _set_readout_text(
        bar.op('readout_frame'),
        'FRAME TIME : {:d} msec'.format(frame_ms),
    )
    _set_readout_text(
        bar.op('readout_fps'),
        'FPS : {:d}'.format(fps),
    )
