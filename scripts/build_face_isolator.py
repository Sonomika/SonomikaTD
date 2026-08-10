"""Build Face Isolator TOX — CPU metadata + GPU composite.

Architecture (per other-dev advice):
  source_router ──┬──→ GPU crop/layout/over chain → out1
                  └──→ analysis (320px) → delayed numpy → YuNet (scriptCHOP)
                                                      → faces CHOP metadata

Display never downloads full-res video. Detection uses numpyArray(delayed=True).
"""
import os

ROOT = os.path.abspath(os.path.join(project.folder, '..')) if os.path.basename(project.folder).lower() == 'production' else project.folder
OUTS = (
    os.path.join(ROOT, 'production', 'tox', 'face_isolator', 'face_isolator.tox'),
    os.path.join(ROOT, 'production', 'tox premium', 'Released', 'face_isolator.tox'),
)

MAX_FACES = 8

SOURCE_EXPR = (
    "(parent().parent().op('video_canvas_fit') if parent().parent().op('video') and "
    "str(parent().parent().op('video').par.file.eval() or '') else "
    "(parent().parent().op('upstream') or parent().op('input1')))"
)

TRACKER_CB = r'''import os, math, time
import cv2
import numpy as np

_detector = None
_detector_key = ''
_tracks = []
_next_id = 1
_next_slot = 0
_free_slots = []
_last_detect_frame = -10**9
_last_float_frame = None
_last_status = ''
_bootstrapped = False
_last_frame_sig = None
_static_streak = 0
MAX_SLOTS = 8
# Still images (or paused video) keep the same analysis pixels — avoid re-running YuNet
_STATIC_STREAK_LOCK = 3
_STATIC_DETECT_EVERY = 180
NUM_JOURNEYS = 12
_morph_from = 0
_morph_to = 0
_morph_t0 = 0.0
_morph_active = False
_morph_menu_seen = None
_hold_faces = []
_hold_miss = 0
HOLD_MAX = 45
SPIN_MODE = 8  # 3D Boxes chapter (spinning)
TILE_MODE = 0  # Over Video — flat front face over live video
FACE_MODE = 1  # cubes parked above tracked faces
ARRIVAL_MODE = 11
_box_xy_smooth = {}
# --- Chapter 1 (Creative): bold cube rotations (no Above Face) ---
# Menu order → pose/rot mode ids (skips FACE_MODE=1)
JOURNEY_B_MODES = (0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
NUM_JOURNEYS_B = len(JOURNEY_B_MODES)
CHAPTER_B_PARS = [
    'Cbovervideo', 'Cbisometric', 'Cbhundredfold', 'Cbconnect', 'Cbcascade', 'Cborbit',
    'Cbmirror', 'Cbboxes3d', 'Cbconstellation', 'Cbparade', 'Cbarrival',
]
CHAPTER_B_LABELS = [
    '1 Over Video', '2 Isometric March', '3 Hundredfold', '4 The Connect', '5 Cascade', '6 Orbit',
    '7 Mirror Hall', '8 3D Boxes', '9 Constellation', '10 Parade', '11 Arrival',
]
JOURNEY_B_NAMES = [
    'Over Video', 'Isometric March', 'Hundredfold', 'The Connect', 'Cascade', 'Orbit',
    'Mirror Hall', '3D Boxes', 'Constellation', 'Parade', 'Arrival',
]
FLAT_B = (TILE_MODE,)  # Over Video stays frontal / no tumble
SPIN_B = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11)  # every other chapter tumbles hard
# --- Chapter 2 (Expressive): same chapters + wilder moves / rotations ---
JOURNEY_C_MODES = JOURNEY_B_MODES
NUM_JOURNEYS_C = len(JOURNEY_C_MODES)
CHAPTER_C_PARS = [
    'Ccovervideo', 'Ccisometric', 'Cchundredfold', 'Ccconnect', 'Cccascade', 'Ccorbit',
    'Ccmirror', 'Ccboxes3d', 'Ccconstellation', 'Ccparade', 'Ccarrival',
]
CHAPTER_C_LABELS = list(CHAPTER_B_LABELS)
JOURNEY_C_NAMES = list(JOURNEY_B_NAMES)
SPIN_C = SPIN_B
_journey_set_seen = None

def _model(comp):
    ext = str(comp.par.externaltox.eval() or '')
    roots = [
        os.path.join(project.folder, 'assets', 'human_object_tracker', 'model'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(ext))), 'assets', 'human_object_tracker', 'model'),
    ]
    for root in roots:
        path = os.path.join(root, 'face_detection_yunet_2023mar.onnx')
        if os.path.isfile(path):
            return path
    return ''

def _looks_like_face(r, frame_w=320, frame_h=180):
    """Strict landmark geometry — YuNet often scores hands highly, so be harsh."""
    if r is None or len(r) < 15:
        return False
    x, y, bw, bh = float(r[0]), float(r[1]), float(r[2]), float(r[3])
    score = float(r[-1])
    if bw < 12 or bh < 12 or score < 0.55:
        return False
    # Ignore tiny blobs (common hand/noise false positives at analysis res)
    if (bw * bh) < (float(frame_w) * float(frame_h) * 0.0020):
        return False
    aspect = bw / max(bh, 1e-3)
    if aspect < 0.72 or aspect > 1.32:
        return False
    re_x, re_y = float(r[4]), float(r[5])
    le_x, le_y = float(r[6]), float(r[7])
    n_x, n_y = float(r[8]), float(r[9])
    rm_x, rm_y = float(r[10]), float(r[11])
    lm_x, lm_y = float(r[12]), float(r[13])
    # Landmarks must sit inside the box
    slack = 0.06 * max(bw, bh)
    for px, py in ((re_x, re_y), (le_x, le_y), (n_x, n_y), (rm_x, rm_y), (lm_x, lm_y)):
        if px < x - slack or py < y - slack or px > x + bw + slack or py > y + bh + slack:
            return False
    # YuNet order: right eye, left eye, nose, right mouth, left mouth
    if re_x >= le_x or rm_x >= lm_x:
        return False
    eye_dx = abs(le_x - re_x)
    eye_dy = abs(le_y - re_y)
    mouth_dx = abs(lm_x - rm_x)
    # Hands often collapse or exaggerate feature spacing
    if eye_dx < bw * 0.28 or eye_dx > bw * 0.60:
        return False
    if eye_dy > bh * 0.10:
        return False
    if mouth_dx < bw * 0.20 or mouth_dx > bw * 0.52:
        return False
    eye_y = (re_y + le_y) * 0.5
    mouth_y = (rm_y + lm_y) * 0.5
    ey = (eye_y - y) / bh
    ny = (n_y - y) / bh
    my = (mouth_y - y) / bh
    nx = (n_x - x) / bw
    # Canonical face vertical layout
    if not (0.22 <= ey <= 0.48):
        return False
    if not (0.42 <= ny <= 0.68):
        return False
    if not (0.58 <= my <= 0.88):
        return False
    if not (eye_y < n_y < mouth_y) or (mouth_y - eye_y) < bh * 0.22:
        return False
    # Nose between the eyes and near centre
    if n_x < re_x or n_x > le_x:
        return False
    if nx < 0.34 or nx > 0.66:
        return False
    mouth_cx = (rm_x + lm_x) * 0.5
    if abs(mouth_cx - n_x) > bw * 0.16:
        return False
    if mouth_cx < re_x - bw * 0.04 or mouth_cx > le_x + bw * 0.04:
        return False
    # Eye-mouth triangle should have decent area (hands flatten this)
    tri = abs(re_x * (le_y - mouth_y) + le_x * (mouth_y - re_y) + mouth_cx * (re_y - le_y))
    if tri < bw * bh * 0.045:
        return False
    return True

def _faces(comp, rgb):
    global _detector, _detector_key
    h, w = rgb.shape[:2]
    path = _model(comp)
    if not path:
        return []
    user_conf = max(0.55, min(0.95, float(comp.par.Confidence)))
    # Confidence is the real accept floor (was far too low via *0.55)
    detect_thresh = max(0.50, user_conf - 0.18)
    accept_score = user_conf
    key = '%s_%d_%d_%.3f' % (path, w, h, detect_thresh)
    if _detector is None or key != _detector_key:
        _detector = cv2.FaceDetectorYN.create(path, '', (w, h), detect_thresh, 0.3, 5000)
        _detector_key = key
    else:
        _detector.setInputSize((w, h))
        _detector.setScoreThreshold(detect_thresh)
    _, rows = _detector.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    found = []
    if rows is not None:
        for r in rows:
            if float(r[-1]) < accept_score or not _looks_like_face(r, w, h):
                continue
            x, y, bw, bh = float(r[0]), float(r[1]), float(r[2]), float(r[3])
            found.append([max(0.0, x), max(0.0, y), min(float(w), x + bw), min(float(h), y + bh), float(r[-1])])
    found.sort(key=lambda b: b[4], reverse=True)
    return found[:max(1, min(MAX_SLOTS, int(comp.par.Maxfaces)))]

def _box_center(b):
    return ((b[0] + b[2]) * 0.5, (b[1] + b[3]) * 0.5)

def _iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    aa = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    bb = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = aa + bb - inter
    return inter / union if union > 0 else 0.0

def _alloc_slot():
    global _next_slot, _free_slots
    if _free_slots:
        return _free_slots.pop(0)
    s = _next_slot
    _next_slot += 1
    return s

def _release_slot(slot):
    global _free_slots
    if slot is None:
        return
    if slot not in _free_slots:
        _free_slots.append(int(slot))
        _free_slots.sort()

def _update_targets(comp, boxes, frame_w, frame_h):
    global _tracks, _next_id
    conf_min = max(0.55, min(0.95, float(comp.par.Confidence)))
    persist = max(8, int(comp.par.Persistence))
    dets = [list(b) for b in boxes if (b[2] - b[0]) >= 10 and (b[3] - b[1]) >= 10 and b[4] >= conf_min]
    tracks = list(_tracks)
    diag = max(1.0, (frame_w * frame_w + frame_h * frame_h) ** 0.5)
    pairs = []
    for ti, t in enumerate(tracks):
        tb = t.get('target', t['box'])
        for di, b in enumerate(dets):
            iou = _iou(tb, b)
            cx, cy = _box_center(b)
            tx, ty = _box_center(tb)
            dist = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5 / diag
            score = iou * 3.0 - dist
            # Hands jitter more — require tighter match to keep a track alive
            min_iou = 0.12 if t.get('confirmed') else 0.20
            max_dist = 0.12 if t.get('confirmed') else 0.08
            if iou >= min_iou or dist < max_dist:
                pairs.append((score, ti, di))
    pairs.sort(key=lambda p: p[0], reverse=True)
    used_t, used_d, result = set(), set(), []
    for score, ti, di in pairs:
        if ti in used_t or di in used_d:
            continue
        used_t.add(ti); used_d.add(di)
        t = tracks[ti]; b = dets[di]
        t['target'] = list(b)
        t['life'] = persist
        t['hit'] = True
        t['misses'] = 0
        t['hits_streak'] = int(t.get('hits_streak', 0)) + 1
        # Multi-frame confirm — hands often flash 1–2 hits then jump
        if t['hits_streak'] >= 2 or float(b[4]) >= 0.90:
            t['confirmed'] = True
        if 'slot' not in t:
            t['slot'] = _alloc_slot()
        result.append(t)
    for di, b in enumerate(dets):
        if di in used_d:
            continue
        box = list(b)
        result.append({
            'id': _next_id, 'box': box[:], 'target': box[:], 'life': persist,
            'hit': True, 'misses': 0, 'hits_streak': 1,
            'confirmed': float(b[4]) >= 0.90, 'slot': _alloc_slot(),
            'floatpos': [0.5, 0.5], 'floatvel': [1.0, 0.7],
        })
        _next_id += 1
    # Ghost tracks at old positions put non-faces in boxes — coast briefly only
    drop_after = max(2, min(8, persist // 6))
    for ti, t in enumerate(tracks):
        if ti in used_t:
            continue
        t['hit'] = False
        t['hits_streak'] = 0
        t['misses'] = int(t.get('misses', 0)) + 1
        t['life'] -= 1
        if t.get('confirmed') and t['misses'] <= drop_after and t['life'] >= 0:
            result.append(t)
        else:
            _release_slot(t.get('slot'))
    result.sort(key=lambda t: (0 if t.get('confirmed') else 1, -float(t.get('target', t['box'])[4]), t.get('slot', t['id']), t['id']))
    max_faces = max(1, min(MAX_SLOTS, int(comp.par.Maxfaces)))
    if len(result) > max_faces:
        for t in result[max_faces:]:
            _release_slot(t.get('slot'))
        result = result[:max_faces]
    result.sort(key=lambda t: (t.get('slot', t['id']), t['id']))
    _tracks = result

def _follow_targets(comp, float_dt):
    if float_dt <= 0:
        return
    s = max(0.35, min(0.95, float(comp.par.Smoothing)))
    alpha = min(0.85, max(0.04, (1.0 - s) * min(1.0, float_dt * 60.0)))
    for t in _tracks:
        box = t['box']
        tgt = t.get('target', box)
        t['box'] = [box[i] + (tgt[i] - box[i]) * alpha for i in range(4)] + [tgt[4] if len(tgt) > 4 else 1.0]

def _smoothstep(u):
    u = 0.0 if u < 0.0 else (1.0 if u > 1.0 else float(u))
    return u * u * (3.0 - 2.0 * u)

def _lerp(a, b, u):
    return a + (b - a) * u

def _lerp_angle(a, b, u):
    d = (float(b) - float(a) + 180.0) % 360.0 - 180.0
    return float(a) + d * u

def _journey_set(comp):
    """0 = chapter 1 creative, 1 = chapter 2 expressive."""
    try:
        idx = int(comp.par.Journeyset.menuIndex)
        return idx if idx in (0, 1) else 0
    except Exception:
        return 0

def _set_modes(set_idx):
    """Pose/rot mode ids available in this chapter set."""
    return JOURNEY_C_MODES if int(set_idx) == 1 else JOURNEY_B_MODES

def _set_count(set_idx):
    return len(_set_modes(set_idx))

def _set_chapter_pars(set_idx):
    return CHAPTER_C_PARS if int(set_idx) == 1 else CHAPTER_B_PARS

def _set_menu_par(comp, set_idx):
    """Chapter menu parameter for the active set."""
    name = 'Pulsemodec' if int(set_idx) == 1 else 'Pulsemodeb'
    return getattr(comp.par, name, None)

def _mode_to_menu(mode, set_idx):
    """Pose/rot mode id → chapter menu index."""
    modes = _set_modes(set_idx)
    try:
        return int(modes.index(int(mode)))
    except ValueError:
        return 0

def _menu_to_mode(menu_idx, set_idx):
    """Chapter menu index → pose/rot mode id."""
    modes = _set_modes(set_idx)
    return int(modes[int(menu_idx) % len(modes)])

def _menu_chapter_mode(menu_par, set_idx):
    """Resolve pose/rot mode from the active set's chapter menu."""
    span = _set_count(set_idx)
    if menu_par is None:
        return _menu_to_mode(0, set_idx)
    try:
        names = list(menu_par.menuNames)
        val = str(menu_par.eval())
        if val in names:
            return _menu_to_mode(names.index(val), set_idx)
    except Exception:
        pass
    try:
        return _menu_to_mode(int(menu_par.menuIndex), set_idx)
    except Exception:
        return _menu_to_mode(0, set_idx)

def _start_journey_morph(frm, to, now=None, set_idx=0):
    global _morph_from, _morph_to, _morph_t0, _morph_active
    modes = _set_modes(set_idx)
    frm_i, to_i = int(frm), int(to)
    _morph_from = frm_i if frm_i in modes else modes[0]
    _morph_to = to_i if to_i in modes else modes[0]
    try:
        _morph_t0 = float(absTime.seconds if now is None else now)
    except Exception:
        _morph_t0 = float(time.time() if now is None else now)
    _morph_active = _morph_from != _morph_to

def _chapter_enabled(comp, mode, set_idx=0):
    """True unless the chapter's enable toggle exists and is off."""
    try:
        pars = _set_chapter_pars(set_idx)
        mi = _mode_to_menu(mode, set_idx)
        return bool(getattr(comp.par, pars[int(mi) % len(pars)]))
    except Exception:
        return True

def _next_enabled_chapter(comp, cur, set_idx=0):
    """Next enabled chapter after cur (Pulse Journey). Stays put if all off."""
    modes = list(_set_modes(set_idx))
    try:
        i0 = modes.index(int(cur))
    except ValueError:
        i0 = 0
    for step in range(1, len(modes) + 1):
        nxt = modes[(i0 + step) % len(modes)]
        if _chapter_enabled(comp, nxt, set_idx):
            return nxt
    return modes[i0]

def _member_weight(frm, to, u, members):
    """Blend 0..1 for chapters belonging to a behaviour group."""
    a = 1.0 if int(frm) in members else 0.0
    b = 1.0 if int(to) in members else 0.0
    return a + (b - a) * float(u)

def _journey_morph_u(now, dur):
    """Return (ease_u, from_mode, to_mode)."""
    global _morph_active
    if not _morph_active or _morph_from == _morph_to:
        _morph_active = False
        return 1.0, _morph_to, _morph_to
    span = max(0.08, float(dur))
    raw = (float(now) - float(_morph_t0)) / span
    if raw >= 1.0:
        _morph_active = False
        return 1.0, _morph_to, _morph_to
    return _smoothstep(raw), _morph_from, _morph_to

def _boxes_mix_weight(frm, to, u):
    """0..1 how much of the spinning 3D-Boxes chapter is active."""
    if frm == SPIN_MODE and to == SPIN_MODE:
        return 1.0
    if frm == SPIN_MODE:
        return 1.0 - u
    if to == SPIN_MODE:
        return u
    return 0.0

def _face_mode_weight(frm, to, u):
    """0..1 how much of the face-anchor chapter is active."""
    if frm == FACE_MODE and to == FACE_MODE:
        return 1.0
    if frm == FACE_MODE:
        return 1.0 - u
    if to == FACE_MODE:
        return u
    return 0.0

def _tile_mode_weight(frm, to, u):
    """0..1 how much of the flat-tile chapter is active."""
    if frm == TILE_MODE and to == TILE_MODE:
        return 1.0
    if frm == TILE_MODE:
        return 1.0 - u
    if to == TILE_MODE:
        return u
    return 0.0

_overlay_fade = 0.0
_OVERLAY_FADE_IN_SECS = 0.22   # dissolve video in after cubes land
_OVERLAY_FADE_OUT_SECS = 0.12  # hide video quickly when leaving

def _overlay_video_target(mode_from, mode_to, mode, morph_active, morph_u):
    """0..1 target for live-video underlay (Above Face / Over Video only).

    Video stays off for the whole morph *into* those chapters (avoids a 1-frame
    flash when the morph ends). It fades out early when leaving. Between the two
    flat chapters it stays on.
    """
    flat = (FACE_MODE, TILE_MODE)
    mf, mt, md = int(mode_from), int(mode_to), int(mode)
    u = max(0.0, min(1.0, float(morph_u)))
    if mf in flat and mt in flat:
        return 1.0
    if morph_active:
        # Leaving flat → hide video in the first quarter of the morph
        if mf in flat and mt not in flat:
            return max(0.0, min(1.0, 1.0 - (u / 0.25)))
        # Entering flat (or other morphs) — keep underlay black until settled
        return 0.0
    return 1.0 if md in flat else 0.0

def _ensure_overlay_bg_mix(comp):
    """Crossfade black ↔ video underlay for face_cubes_over (no journey_out swaps)."""
    face_over = comp.op('face_cubes_over')
    src = comp.op('source_router')
    if face_over is None or src is None:
        return None
    black = comp.op('boxes3d_black')
    if black is None:
        black = comp.create('constantTOP', 'boxes3d_black')
        black.par.colorr = 0
        black.par.colorg = 0
        black.par.colorb = 0
        black.par.alpha = 1
    try:
        black.par.outputresolution = 'custom'
        black.par.resolutionw.expr = "max(1, op('source_router').width)"
        black.par.resolutionh.expr = "max(1, op('source_router').height)"
    except Exception:
        pass
    mix = comp.op('overlay_bg_mix')
    if mix is None:
        mix = comp.create('crossTOP', 'overlay_bg_mix')
        try:
            mix.nodeX = face_over.nodeX - 200
            mix.nodeY = face_over.nodeY - 120
        except Exception:
            pass
    # input0 = black, input1 = live source; cross 0=black … 1=video
    try:
        need = True
        if len(mix.inputs) >= 2 and mix.inputs[0] == black and mix.inputs[1] == src:
            need = False
        if need:
            for c in list(mix.inputConnectors):
                while c.connections:
                    c.disconnect()
            mix.inputConnectors[0].connect(black)
            if len(mix.inputConnectors) < 2:
                src.outputConnectors[0].connect(mix)
            else:
                mix.inputConnectors[1].connect(src)
    except Exception:
        pass
    # face_cubes_over: cubes over underlay mix
    try:
        proxy = comp.op('boxes3d_render_proxy')
        if proxy is None:
            proxy = comp.create('selectTOP', 'boxes3d_render_proxy')
            rend = comp.op('boxes3d/render')
            if rend is not None:
                proxy.par.top = rend.path
            _ensure_select_follows_top(proxy)
        fc0 = face_over.inputConnectors[0]
        if not fc0.connections or fc0.connections[0].owner != proxy:
            while fc0.connections:
                fc0.disconnect()
            fc0.connect(proxy)
        fc1 = face_over.inputConnectors[1]
        if not fc1.connections or fc1.connections[0].owner != mix:
            while fc1.connections:
                fc1.disconnect()
            fc1.connect(mix)
    except Exception:
        pass
    # Legacy hard switch (if present) — leave bypassed / unwired
    return mix

def _separate_boxes(pts, min_dist, iters=16):
    """Push 2D points apart until pairwise distance >= min_dist."""
    n = len(pts)
    if n < 2 or min_dist <= 1e-6:
        return pts
    for _ in range(iters):
        for i in range(n):
            for j in range(i + 1, n):
                dx = pts[j][0] - pts[i][0]
                dy = pts[j][1] - pts[i][1]
                d = math.hypot(dx, dy)
                if d < 1e-5:
                    ang = (i * 2.399963 + j) % (math.pi * 2.0)
                    dx = math.cos(ang)
                    dy = math.sin(ang)
                    d = 1e-5
                if d < min_dist:
                    push = 0.5 * (min_dist - d) / d
                    pts[i][0] -= dx * push
                    pts[i][1] -= dy * push
                    pts[j][0] += dx * push
                    pts[j][1] += dy * push
    return pts

def _fit_boxes_in_frame(pts, xmin=-1.0, xmax=1.0, ymin=-0.72, ymax=0.72, margin=0.02):
    """Scale+clamp point cloud so every point stays inside the ortho frame."""
    if not pts:
        return pts
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    cx = 0.5 * (minx + maxx)
    cy = 0.5 * (miny + maxy)
    span_x = max(1e-6, maxx - minx)
    span_y = max(1e-6, maxy - miny)
    avail_x = max(1e-6, (xmax - xmin) - 2.0 * margin)
    avail_y = max(1e-6, (ymax - ymin) - 2.0 * margin)
    scale = min(1.0, avail_x / span_x, avail_y / span_y)
    for p in pts:
        p[0] = max(xmin + margin, min(xmax - margin, cx + (p[0] - cx) * scale))
        p[1] = max(ymin + margin, min(ymax - margin, cy + (p[1] - cy) * scale))
    return pts

def _ensure_select_follows_top(node):
    """Select TOPs that use par.top must custom-res to the selected TOP.

    Hardcoded 810x1440 (or Use Input with no wire) stretches landscape 1920x1080
    into portrait and makes cubes look wrong.
    """
    if node is None or not hasattr(node.par, 'top'):
        return
    try:
        we = node.par.resolutionw.expr or ''
        he = node.par.resolutionh.expr or ''
        if (
            str(node.par.outputresolution.eval()) == 'custom'
            and 'me.par.top' in we
            and 'me.par.top' in he
        ):
            return
        node.par.outputresolution = 'custom'
        node.par.outputaspect = 'resolution'
        node.par.resolutionw.expr = "max(1, int(op(me.par.top).width))"
        node.par.resolutionh.expr = "max(1, int(op(me.par.top).height))"
    except Exception:
        pass

def _ortho_view_bounds(comp, ortho_w=2.0):
    """Visible world X/Y half-extents for an ortho cam matching source aspect.

    Portrait 1080x1920 → tall Y range, tight X sides; landscape is the reverse.
    """
    src = comp.op('source_router')
    try:
        w = float(src.width) if src is not None else 1080.0
        h = float(src.height) if src is not None else 1920.0
    except Exception:
        w, h = 1080.0, 1920.0
    w = max(1.0, w)
    h = max(1.0, h)
    half_x = float(ortho_w) * 0.5
    half_y = half_x * (h / w)
    return -half_x, half_x, -half_y, half_y

def _uv_to_world(dstx, dsty, ortho_w, h_over_w):
    """Map top-origin UV to ortho world XY matching the visible frame."""
    half_x = float(ortho_w) * 0.5
    half_y = half_x * max(1e-6, float(h_over_w))
    wx = (float(dstx) - 0.5) * 2.0 * half_x
    wy = (0.5 - float(dsty)) * 2.0 * half_y
    return wx, wy

def _frame_size_cap(n, xmax, xmin, ymax, ymin, gap):
    """Shrink cubes so a grid fits the shorter visible axis (portrait width or landscape height)."""
    n = max(1, int(n))
    cols = max(1, int(math.ceil(math.sqrt(float(n)))))
    span = min(max(1e-6, float(xmax) - float(xmin)), max(1e-6, float(ymax) - float(ymin)))
    return max(0.06, span / (cols * max(1.05, float(gap))) * 0.9)

def _audio_cube_size(comp):
    """Remap Cubesize (bind Audiooutlow here) through Cubesizelow..High with Smooth."""
    try:
        lo = max(0.05, min(2.0, float(comp.par.Cubesizelow)))
    except Exception:
        lo = 0.15
    try:
        hi = max(0.05, min(2.0, float(comp.par.Cubesizehigh)))
    except Exception:
        hi = 0.9
    if hi < lo:
        lo, hi = hi, lo
    try:
        # 0 = no smoothing (instant), 1 = full smoothing (heavy lag)
        sm = max(0.0, min(1.0, float(comp.par.Cubesizesmooth)))
    except Exception:
        sm = 0.9
    # Cubesize is the driver — bind op('/settings').par.Audiooutlow to it
    try:
        raw = max(0.0, min(1.0, float(comp.par.Cubesize)))
    except Exception:
        raw = 0.0
    prev = comp.fetch('_cube_size_audio_s', None)
    follow = 1.0 - sm
    if prev is None or follow >= 1.0:
        smoothed = raw
    elif follow <= 0.0:
        smoothed = float(prev)
    else:
        smoothed = float(prev) + (raw - float(prev)) * follow
    comp.store('_cube_size_audio_s', smoothed)
    return max(0.05, min(2.0, lo + (hi - lo) * smoothed))

def _panel_to_world_size(panel, cube_size, xmax, xmin, ymax, ymin):
    """UV panel size → world cube size using the shorter visible axis.

    Keeps cubes screen-square and stops landscape 1920x1080 from overfilling
    the short axis (which read as vertically squashed / crushed cubes).
    """
    short = min(max(1e-6, float(xmax) - float(xmin)), max(1e-6, float(ymax) - float(ymin)))
    raw = float(panel) * short * 1.35 * max(0.05, float(cube_size))
    return max(0.06, min(short * 0.92, raw))

def _face_to_world_size(side_px, aw, ortho_w):
    """World cube size matching the on-screen face square (analysis px → UV → world)."""
    return max(0.04, float(ortho_w) * (float(side_px) / max(1.0, float(aw))))

def _journey_pose(mode, i, n, tid, now, jspeed, scale_f, cols, rows, panel_grid, face_uv=None):
    """Return dstx, dsty, panel_size, rotate_deg for journey pulse modes."""
    t = now * max(0.05, float(jspeed))
    u = (i + 0.5) / max(n, 1)
    # 0 Over Video — flat face flush to camera on tracked face
    if mode == TILE_MODE:
        if face_uv is not None:
            fx, fy = face_uv[0], face_uv[1]
        else:
            fx, fy = 0.5, 0.45
        return fx, fy, panel_grid * 0.9, 0.0
    # 1 Above Face — primary on face centre; cook loop stacks clones above
    if mode == FACE_MODE:
        if face_uv is not None:
            fx, fy = face_uv[0], face_uv[1]
        else:
            fx, fy = 0.5, 0.4
        return fx, fy, panel_grid * 0.75, 0.0
    # 2 Isometric March — convoy drifts on a diamond grid
    if mode == 2:
        col, row = i % cols, i // cols
        march = (t * 0.12) % 1.0
        dstx = ((col + 0.5) / cols + march * 0.35 + row * 0.04) % 1.0
        dsty = ((row + 0.5) / rows + march * 0.18) % 1.0
        dstx = 0.12 + dstx * 0.76
        dsty = 0.14 + dsty * 0.72
        return dstx, dsty, panel_grid * 0.85, -26.0 + (i % 2) * 8.0
    # 3 Hundredfold — seed faces
    if mode == 3:
        col, row = i % cols, i // cols
        return (col + 0.5) / cols, (row + 0.5) / rows, panel_grid * 0.35, -18.0
    # 4 The Connect — open ring
    if mode == 4:
        ang = t * 0.4 + u * math.pi * 2.0
        rad = min(0.42, 0.24 + 0.022 * n + 0.03 * math.sin(t + tid))
        return 0.5 + math.cos(ang) * rad, 0.5 + math.sin(ang) * rad * 0.75, panel_grid * 0.75, 0.0
    # 5 Cascade — staircase tumble
    if mode == 5:
        fall = (t * 0.35 + u) % 1.4
        dstx = 0.15 + u * 0.7
        dsty = -0.1 + fall * 1.15
        if dsty > 1.05:
            dsty = dsty - 1.2
        return dstx, min(0.92, max(0.08, dsty)), panel_grid * 0.7, 12.0 + fall * 25.0
    # 6 Orbit
    if mode == 6:
        ang = t * 0.7 + u * math.pi * 2.0
        rad = min(0.42, 0.26 + 0.02 * n)
        return 0.5 + math.cos(ang) * rad, 0.5 + math.sin(ang) * rad * 0.7, panel_grid * 0.7, (math.degrees(ang) + 90.0) % 360.0
    # 7 Mirror Hall
    if mode == 7:
        side = -1.0 if (i % 2 == 0) else 1.0
        dstx = 0.5 + side * (0.18 + 0.12 * math.sin(t * 0.8 + u * 3))
        dsty = 0.2 + ((i // 2) + 0.5) / max(1, math.ceil(n / 2.0)) * 0.6
        return dstx, dsty, panel_grid * 0.65, side * 18.0
    # 8 3D Boxes — spinning cluster layout
    if mode == 8:
        col, row = i % max(cols, 1), i // max(cols, 1)
        bob = 0.03 * math.sin(t * 1.4 + tid * 0.7)
        drift = (t * 0.08 + u * 0.2) % 0.15
        dstx = 0.14 + (col + 0.5) / max(cols, 1) * 0.72 + drift * 0.3
        dsty = 0.16 + (row + 0.5) / max(rows, 1) * 0.68 + bob
        return dstx, dsty, panel_grid * 0.72, -22.0
    # 9 Constellation
    if mode == 9:
        seed = (tid * 12.9898 + i * 78.233) % 1.0
        seed2 = (tid * 4.123 + i * 19.19) % 1.0
        drift = 0.03 * math.sin(t * 0.6 + seed * 6)
        return 0.1 + seed * 0.8 + drift, 0.12 + seed2 * 0.76, max(0.06, panel_grid * 0.28), 0.0
    # 10 Parade
    if mode == 10:
        x = (u + t * 0.1) % 1.0
        return 0.08 + x * 0.84, 0.5 + 0.06 * math.sin(t * 2 + i), panel_grid * 0.8, -8.0
    # 11 Arrival — clean grid home
    col, row = i % cols, i // cols
    return (col + 0.5) / cols, (row + 0.5) / rows, panel_grid, 0.0

def _journey_pose_b(mode, i, n, tid, now, jspeed, scale_f, cols, rows, panel_grid, face_uv=None):
    """Creative set — same layouts as Classic (A)."""
    return _journey_pose(mode, i, n, tid, now, jspeed, scale_f, cols, rows, panel_grid, face_uv)

def _journey_rot_b(mode, i, n, tid, now, jspeed):
    """Bold multi-axis cube spins for Classic layouts (degrees).

    Over Video (0) and Above Face (1) stay locked flat to camera.
    """
    t = now * max(0.05, float(jspeed))
    u = (i + 0.5) / max(n, 1)
    if mode == FACE_MODE or mode == TILE_MODE:
        return 0.0, 0.0, 0.0
    if mode == 2:  # Isometric March
        return -32.0 + 10.0 * math.sin(t * 1.2 + i), (t * 58.0 + i * 42.0) % 360.0, -22.0
    if mode == 3:  # Hundredfold
        return (t * 48.0 + i * 55.0) % 360.0, (t * 72.0 + tid * 33.0) % 360.0, (t * 31.0 + i * 27.0) % 360.0
    if mode == 4:  # The Connect
        return -20.0, (t * 80.0 + u * 360.0) % 360.0, 12.0 * math.sin(t * 1.4 + i)
    if mode == 5:  # Cascade
        fall = (t * 0.35 + u) % 1.4
        return 18.0 + fall * 55.0, (t * 40.0 + i * 50.0) % 360.0, fall * 35.0
    if mode == 6:  # Orbit
        ang = t * 0.7 + u * math.pi * 2.0
        return -25.0, (math.degrees(ang) + 90.0) % 360.0, 18.0 * math.sin(ang)
    if mode == 7:  # Mirror Hall
        side = -1.0 if (i % 2 == 0) else 1.0
        return side * 28.0, (t * 50.0 + i * 60.0) % 360.0, side * 16.0
    if mode == 8:  # 3D Boxes
        return -30.0, (t * 90.0 + i * 45.0) % 360.0, -18.0
    if mode == 9:  # Constellation
        return (t * 35.0 + tid * 70.0) % 360.0, (t * 55.0 + i * 40.0) % 360.0, (t * 22.0) % 360.0
    if mode == 10:  # Parade
        return -15.0 + 12.0 * math.sin(t * 2.0 + i), (t * 65.0 + i * 30.0) % 360.0, 10.0
    if mode == 11:  # Arrival
        return -22.0, (t * 42.0 + i * 48.0) % 360.0, 14.0 * math.cos(t * 1.1 + u * 4.0)
    return -18.0, (t * 40.0 + i * 35.0) % 360.0, 0.0




def _journey_pose_c(mode, i, n, tid, now, jspeed, scale_f, cols, rows, panel_grid, face_uv=None):
    """Expressive set — same chapters as B with wilder pathing."""
    t = now * max(0.05, float(jspeed)) * 1.35
    u = (i + 0.5) / max(n, 1)
    if mode == TILE_MODE:
        if face_uv is not None:
            fx, fy = face_uv[0], face_uv[1]
        else:
            fx, fy = 0.5, 0.45
        return fx, fy, panel_grid * 0.9, 0.0
    if mode == FACE_MODE:
        if face_uv is not None:
            fx, fy = face_uv[0], face_uv[1]
        else:
            fx, fy = 0.5, 0.4
        return fx, fy, panel_grid * 0.75, 0.0
    if mode == 2:
        col, row = i % cols, i // cols
        march = (t * 0.22) % 1.0
        weave = 0.08 * math.sin(t * 2.4 + i * 0.9)
        dstx = ((col + 0.5) / cols + march * 0.55 + row * 0.06 + weave) % 1.0
        dsty = ((row + 0.5) / rows + march * 0.28 + 0.05 * math.cos(t * 1.7 + tid)) % 1.0
        return 0.08 + dstx * 0.84, 0.10 + dsty * 0.80, panel_grid * 0.82, -38.0 + (i % 3) * 12.0
    if mode == 3:
        ang = t * 0.9 + u * math.pi * 2.0 + tid * 0.2
        rad = min(0.48, 0.08 + 0.4 * (0.5 + 0.5 * math.sin(t * 0.7 + u * 4)))
        return 0.5 + math.cos(ang) * rad, 0.5 + math.sin(ang) * rad * 0.85, panel_grid * 0.28, (math.degrees(ang)) % 360.0
    if mode == 4:
        ang = t * 0.65 + u * math.pi * 2.0
        rad = min(0.46, 0.2 + 0.03 * n + 0.08 * math.sin(t * 2.0 + tid))
        fx = math.sin(ang)
        fy = math.sin(ang) * math.cos(ang)
        return 0.5 + fx * rad, 0.5 + fy * rad * 1.15, panel_grid * 0.7, math.degrees(ang)
    if mode == 5:
        fall = (t * 0.55 + u * 1.3) % 1.6
        bounce = abs(math.sin(fall * math.pi)) * 0.12
        dstx = 0.1 + ((u + t * 0.08) % 1.0) * 0.8
        dsty = -0.15 + fall * 1.2 + bounce
        if dsty > 1.08:
            dsty = dsty - 1.25
        return dstx, min(0.94, max(0.06, dsty)), panel_grid * 0.65, 20.0 + fall * 50.0
    if mode == 6:
        ang = t * 1.15 + u * math.pi * 2.0
        radx = min(0.46, 0.22 + 0.03 * n)
        rady = radx * (0.55 + 0.25 * math.sin(t * 0.8))
        return 0.5 + math.cos(ang) * radx, 0.5 + math.sin(ang * 1.3) * rady, panel_grid * 0.68, (-math.degrees(ang) * 1.5) % 360.0
    if mode == 7:
        side = -1.0 if (i % 2 == 0) else 1.0
        shear = 0.14 * math.sin(t * 1.6 + u * 5)
        dstx = 0.5 + side * (0.22 + 0.16 * math.sin(t * 1.1 + u * 3) + shear)
        dsty = 0.12 + ((i // 2) + 0.5) / max(1, math.ceil(n / 2.0)) * 0.76
        dsty += 0.05 * math.sin(t * 2.2 + i)
        return min(0.92, max(0.08, dstx)), min(0.92, max(0.08, dsty)), panel_grid * 0.6, side * (28.0 + 18.0 * math.sin(t + i))
    if mode == 8:
        col, row = i % max(cols, 1), i // max(cols, 1)
        swirl = t * 0.5 + u * math.pi * 2
        bob = 0.06 * math.sin(t * 2.2 + tid * 0.9)
        dstx = 0.5 + math.cos(swirl) * (0.12 + 0.28 * (col + 0.5) / max(cols, 1))
        dsty = 0.5 + math.sin(swirl) * (0.10 + 0.26 * (row + 0.5) / max(rows, 1)) + bob
        return min(0.9, max(0.1, dstx)), min(0.9, max(0.1, dsty)), panel_grid * 0.7, -40.0 + (i % 4) * 15.0
    if mode == 9:
        seed = (tid * 12.9898 + i * 78.233) % 1.0
        seed2 = (tid * 4.123 + i * 19.19) % 1.0
        drift = 0.07 * math.sin(t * 1.1 + seed * 8)
        drift2 = 0.06 * math.cos(t * 0.9 + seed2 * 7)
        return 0.08 + seed * 0.84 + drift, 0.1 + seed2 * 0.8 + drift2, max(0.05, panel_grid * 0.24), (t * 40 + i * 25) % 360.0
    if mode == 10:
        x = (u + t * 0.18) % 1.0
        wave = 0.14 * math.sin(t * 3.2 + i * 0.7)
        return 0.06 + x * 0.88, 0.5 + wave, panel_grid * 0.78, -18.0 + wave * 80.0
    col, row = i % cols, i // cols
    breath = 0.04 * math.sin(t * 1.8 + (col + row) * 0.6)
    return (col + 0.5) / cols, (row + 0.5) / rows + breath, panel_grid * (0.95 + 0.08 * math.sin(t + i)), 8.0 * math.sin(t * 0.7 + i)

def _journey_rot_c(mode, i, n, tid, now, jspeed):
    """Wilder multi-axis spins than Creative (B). Over Video stays flat."""
    t = now * max(0.05, float(jspeed)) * 1.45
    u = (i + 0.5) / max(n, 1)
    if mode == FACE_MODE or mode == TILE_MODE:
        return 0.0, 0.0, 0.0
    if mode == 2:
        return -48.0 + 22.0 * math.sin(t * 1.8 + i), (t * 95.0 + i * 55.0) % 360.0, -30.0 + 12.0 * math.cos(t + tid)
    if mode == 3:
        return (t * 88.0 + i * 70.0) % 360.0, (t * 110.0 + tid * 45.0) % 360.0, (t * 64.0 + i * 38.0) % 360.0
    if mode == 4:
        return -35.0 + 15.0 * math.sin(t * 2.2 + i), (t * 120.0 + u * 360.0) % 360.0, 22.0 * math.sin(t * 1.9 + i)
    if mode == 5:
        fall = (t * 0.55 + u) % 1.6
        return 30.0 + fall * 90.0, (t * 70.0 + i * 60.0) % 360.0, fall * 55.0
    if mode == 6:
        ang = t * 1.15 + u * math.pi * 2.0
        return -40.0, (math.degrees(ang) * 1.6) % 360.0, 28.0 * math.sin(ang * 1.3)
    if mode == 7:
        side = -1.0 if (i % 2 == 0) else 1.0
        return side * 42.0, (t * 85.0 + i * 70.0) % 360.0, side * 28.0 * math.sin(t * 1.5 + i)
    if mode == 8:
        return -45.0 + 10.0 * math.sin(t + i), (t * 140.0 + i * 55.0) % 360.0, -28.0
    if mode == 9:
        return (t * 70.0 + tid * 90.0) % 360.0, (t * 95.0 + i * 60.0) % 360.0, (t * 50.0 + tid) % 360.0
    if mode == 10:
        return -25.0 + 20.0 * math.sin(t * 3.0 + i), (t * 100.0 + i * 40.0) % 360.0, 16.0 * math.cos(t * 2.0 + i)
    if mode == 11:
        return -30.0 + 18.0 * math.sin(t * 1.6 + i), (t * 75.0 + i * 55.0) % 360.0, 22.0 * math.cos(t * 1.4 + u * 5.0)
    return -28.0, (t * 70.0 + i * 45.0) % 360.0, 12.0



def _set_lines(comp, amount, web):
    """Show/hide the 3D connector lines (shared by every set)."""
    lg = comp.op('boxes3d/lines_geo')
    if lg is None:
        return
    on = float(amount) > 0.35
    try:
        if bool(lg.par.display) != on:
            lg.par.display = on
    except Exception:
        return
    if not on:
        return
    try:
        lg.store('linemode', 1 if float(web) > 0.5 else 0)
    except Exception:
        pass
    mat = lg.op('lines_mat')
    if mat is not None:
        for pname, val in (
            ('linenearalpha', max(0.05, min(1.0, float(amount)))),
            ('widthnear', 2.0 + 3.0 * float(amount)),
            ('widthfar', 2.0 + 3.0 * float(amount)),
        ):
            try:
                setattr(mat.par, pname, val)
            except Exception:
                pass
    sop = lg.op('lines_sop')
    if sop is not None:
        try:
            sop.cook(force=True)
        except Exception:
            pass


def _set_status(comp, text):
    global _last_status
    if text != _last_status:
        comp.par.Status = text
        _last_status = text

def _analysis_frame(comp):
    """Delayed GPU readback — does not stall the current display frame."""
    global _bootstrapped
    top = comp.op('analysis_resolution')
    if top is None:
        return None
    frame = top.numpyArray(delayed=True)
    if frame is None:
        # Prime the delayed pipeline once
        if not _bootstrapped:
            top.numpyArray(delayed=True)
            _bootstrapped = True
        return None
    return frame

def _frame_sig(arr):
    """Cheap fingerprint so still images can skip repeated YuNet runs."""
    try:
        h, w = int(arr.shape[0]), int(arr.shape[1])
        y0, x0 = h // 4, w // 4
        y1, x1 = (3 * h) // 4, (3 * w) // 4
        s = (
            float(arr[y0, x0, 0])
            + float(arr[y1, x1, 0])
            + float(arr[h // 2, w // 2, 1])
            + float(arr[y0, x1, 2])
        )
        return (h, w, round(s, 4), round(float(arr.mean()), 5))
    except Exception:
        return None

def onCook(scriptOp):
    global _last_detect_frame, _last_float_frame, _box_xy_smooth
    global _last_frame_sig, _static_streak
    comp = scriptOp.parent()
    rate = max(1.0, float(project.cookRate))
    frame = int(absTime.frame)

    analysis = comp.op('analysis_resolution')
    if analysis is not None:
        try:
            if analysis.par.outputresolution.eval() != 'custom':
                analysis.par.outputresolution = 'custom'
            pw = int(comp.par.Processresolution)
            if pw < 160:
                comp.par.Processresolution = 320
            elif pw > 400:
                comp.par.Processresolution = 400
        except Exception:
            pass

    detect_every = int(comp.par.Detectionrate)
    if detect_every < 8:
        detect_every = 8
        comp.par.Detectionrate = 8
    # Frozen still underneath: almost never re-detect once we have tracks
    if _static_streak >= _STATIC_STREAK_LOCK and _tracks:
        detect_every = max(detect_every, int(_STATIC_DETECT_EVERY))
    if int(comp.par.Maxfaces) > MAX_SLOTS:
        comp.par.Maxfaces = MAX_SLOTS

    if _last_float_frame is None:
        float_dt = 1.0 / rate
    elif frame == _last_float_frame:
        float_dt = 0.0
    else:
        float_dt = min(0.1, max(0.0, (frame - _last_float_frame) / rate))
    _last_float_frame = frame

    aw = max(1, int(analysis.width)) if analysis else 320
    ah = max(1, int(analysis.height)) if analysis else 180

    if comp.par.Active and frame - _last_detect_frame >= detect_every:
        arr = _analysis_frame(comp)
        if arr is not None:
            sig = _frame_sig(arr)
            if sig is not None and sig == _last_frame_sig:
                _static_streak += 1
            else:
                _static_streak = 0
                _last_frame_sig = sig
            # Identical analysis pixels (still image / paused frame): keep tracks, skip YuNet
            if _static_streak >= 2 and _tracks:
                _last_detect_frame = frame
            else:
                # delayed download is [h, w, c] float; TD numpy row0 = BOTTOM of image
                rgb = np.ascontiguousarray(np.clip(arr[:, :, :3] * 255.0, 0, 255), dtype=np.uint8)
                rgb = np.ascontiguousarray(np.flipud(rgb))  # YuNet expects y=0 at top
                ah, aw = rgb.shape[:2]
                _update_targets(comp, _faces(comp, rgb), aw, ah)
                _last_detect_frame = frame

    _follow_targets(comp, float_dt)

    # Layout slots → CHOP samples (GPU reads these; no CPU image build)
    # Keep Maxfaces boxes filled — duplicate real faces when tracks drop
    global _hold_faces, _hold_miss
    real_tracks = [t for t in _tracks if t.get('confirmed') and int(t.get('misses', 0)) <= 1]
    real_tracks.sort(key=lambda t: (t.get('slot', t['id']), t['id']))
    if real_tracks:
        _hold_faces = [{'box': list(t['box']), 'id': int(t['id'])} for t in real_tracks]
        _hold_miss = 0
    elif _hold_faces and _hold_miss < HOLD_MAX:
        # Avoid empty-frame bg flashes when detection briefly drops
        _hold_miss += 1
        real_tracks = [
            {'box': h['box'], 'id': h['id'], 'confirmed': True, 'misses': 0}
            for h in _hold_faces
        ]
    else:
        _hold_miss += 1
    try:
        box_count = max(1, min(MAX_SLOTS, int(comp.par.Maxfaces)))
    except Exception:
        box_count = MAX_SLOTS
    if real_tracks:
        tracks = [real_tracks[i % len(real_tracks)] for i in range(box_count)]
    else:
        tracks = []
    n = max(1, len(tracks)) if tracks else 1
    cols = max(1, int(math.ceil(math.sqrt(n * float(aw) / max(float(ah), 1.0)))))
    rows = max(1, int(math.ceil(n / float(cols))))
    while cols * rows < n:
        cols += 1
    pad_f = float(comp.par.Padding)
    scale_f = min(1.0, max(0.25, float(comp.par.Facescale)))
    now = absTime.seconds
    morph_now = absTime.seconds
    set_idx = _journey_set(comp)
    set_n = _set_count(set_idx)
    menu_par = _set_menu_par(comp, set_idx)
    target_mode = _menu_chapter_mode(menu_par, set_idx)
    try:
        jspeed = float(comp.par.Journeyspeed)
    except Exception:
        jspeed = 1.0
    try:
        morph_secs = float(comp.par.Morphsecs)
    except Exception:
        morph_secs = 1.25
    try:
        cube_bright = max(0.0, min(1.0, float(comp.par.Cubebrightness)))
    except Exception:
        cube_bright = 0.45
    try:
        cube_size = _audio_cube_size(comp)
    except Exception:
        try:
            cube_size = max(0.05, min(2.0, float(comp.par.Cubesize)))
        except Exception:
            cube_size = 0.4

    global _morph_menu_seen, _morph_to, _morph_from, _morph_active, _journey_set_seen, _overlay_fade
    # Switching chapter sets jumps straight in — no morph across sets
    if _journey_set_seen is None or int(_journey_set_seen) != int(set_idx):
        _journey_set_seen = int(set_idx)
        _morph_from = target_mode
        _morph_to = target_mode
        _morph_active = False
        _morph_menu_seen = target_mode
        _overlay_fade = 0.0
    # Pulse Journey button (parexec increments journey_pulse_n)
    try:
        pulse_n = int(comp.fetch('journey_pulse_n', 0) or 0)
        pulse_done = int(comp.fetch('journey_pulse_done', 0) or 0)
        if pulse_n != pulse_done:
            comp.store('journey_pulse_done', pulse_n)
            nxt = _next_enabled_chapter(comp, _morph_to, set_idx)
            if nxt == int(_morph_to) and not _chapter_enabled(comp, nxt, set_idx):
                # All chapters disabled — ignore pulse
                pass
            else:
                _start_journey_morph(_morph_to, nxt, morph_now, set_idx)
                target_mode = nxt
                try:
                    names = list(menu_par.menuNames)
                    mi = _mode_to_menu(nxt, set_idx)
                    if 0 <= mi < len(names):
                        menu_par.val = names[mi]
                    else:
                        menu_par.menuIndex = mi
                except Exception:
                    try:
                        menu_par.menuIndex = _mode_to_menu(nxt, set_idx)
                    except Exception:
                        pass
                _morph_menu_seen = nxt
    except Exception:
        pass
    # Manual menu change also morphs; retarget if morph_to drifted from menu
    if _morph_menu_seen is None:
        _morph_menu_seen = target_mode
        _morph_from = target_mode
        _morph_to = target_mode
        _morph_active = False
    elif int(target_mode) != int(_morph_menu_seen):
        cur = int(_morph_to)
        if _morph_active and int(_morph_from) != int(_morph_to):
            try:
                span = max(1e-3, float(morph_secs))
                raw = (float(morph_now) - float(_morph_t0)) / span
                cur = int(_morph_to) if raw >= 0.5 else int(_morph_from)
            except Exception:
                cur = int(_morph_to)
        _start_journey_morph(cur, target_mode, morph_now, set_idx)
        _morph_menu_seen = target_mode
    elif int(target_mode) != int(_morph_to):
        # Menu matches seen but morph target drifted — snap to menu
        _morph_from = target_mode
        _morph_to = target_mode
        _morph_active = False
        _morph_menu_seen = target_mode
    # Safety: hung morph or menu drift — snap when morph overruns
    if _morph_active:
        try:
            age = float(morph_now) - float(_morph_t0)
        except Exception:
            age = 0.0
        if age < 0.0 or age > max(0.6, float(morph_secs) * 2.5):
            _morph_active = False
            _morph_from = target_mode
            _morph_to = target_mode
            _morph_menu_seen = target_mode

    morph_u, mode_from, mode_to = _journey_morph_u(morph_now, morph_secs)
    if not _morph_active:
        # Stay locked to the chapter menu once a morph finishes
        mode_from = target_mode
        mode_to = target_mode
        _morph_from = target_mode
        _morph_to = target_mode
        morph_u = 1.0
    mode = mode_to if morph_u >= 0.5 else mode_from
    # Always render real 3D cubes — no 2D↔3D crossfade
    boxes_w = 1.0
    fx_c = None
    # 1 Creative / 2 Expressive
    spin_members = SPIN_C if set_idx == 1 else SPIN_B
    spin_amt = _member_weight(mode_from, mode_to, morph_u, spin_members)
    face_amt = _face_mode_weight(mode_from, mode_to, morph_u)
    tile_amt = _tile_mode_weight(mode_from, mode_to, morph_u)
    flat_amt = max(face_amt, tile_amt)
    overlay_amt = flat_amt

    # CHOP: MAX_SLOTS samples
    # active, cropl, cropr, cropb, cropt, dstx, dsty, dstsize, faceid, rotate, journeymode
    chans = ['active', 'cropl', 'cropr', 'cropb', 'cropt', 'dstx', 'dsty', 'dstsize', 'faceid', 'rotate', 'journeymode']
    data = np.zeros((len(chans), MAX_SLOTS), dtype=np.float32)

    journey_names = JOURNEY_C_NAMES if set_idx == 1 else JOURNEY_B_NAMES

    def _jname(mode):
        mi = _mode_to_menu(mode, set_idx)
        return journey_names[mi] if 0 <= mi < len(journey_names) else 'Journey'

    box_world = []  # [{idx, x, y, sz}] collected then separated so cubes never overlap
    n_real = max(1, len(real_tracks)) if real_tracks else 1
    # Blend ortho with flat_amt so cam + layout stay in sync (no hard cut at 0.5)
    flat_cam = max(0.0, min(1.0, float(flat_amt)))
    ortho_w = _lerp(2.8, 2.0, flat_cam)
    xmin, xmax, ymin, ymax = _ortho_view_bounds(comp, ortho_w)
    try:
        src0 = comp.op('source_router')
        src_w = float(src0.width) if src0 is not None else 1080.0
        src_h = float(src0.height) if src0 is not None else 1920.0
    except Exception:
        src_w, src_h = 1080.0, 1920.0
    h_over_w = max(1e-6, src_h / max(1.0, src_w))
    is_portrait = (src_w / max(1.0, src_h)) < 0.95

    for i, t in enumerate(tracks[:MAX_SLOTS]):
        b = t['box']
        bw = max(2.0, b[2] - b[0]); bh = max(2.0, b[3] - b[1])
        side = max(bw, bh) * (1.0 + max(0.0, pad_f))
        side = min(side, float(min(aw, ah)))
        cx = (b[0] + b[2]) * 0.5
        cy = (b[1] + b[3]) * 0.5
        # Keep the face centred in the square crop. Near-edge clamping used to
        # slide the window (bad on 1920x1080 where the short axis hits first);
        # shrink the square instead so the face stays in the middle.
        half = side * 0.5
        half = min(half, cx, float(aw) - cx, cy, float(ah) - cy)
        half = max(1.0, half)
        side = half * 2.0
        x0 = cx - half
        y0 = cy - half
        left = x0 / float(aw)
        right = (x0 + side) / float(aw)
        bottom = 1.0 - (y0 + side) / float(ah)
        top = 1.0 - y0 / float(ah)

        col = i % cols
        row = i // cols
        cell_w = 1.0 / cols
        cell_h = 1.0 / rows
        panel_grid = min(cell_w, cell_h) * scale_f * 0.92
        rot = 0.0

        # Chapters drive pose; face_uv / panel sizing below

        face_top_uv = float(b[1]) / float(ah)
        face_half_uv = max(0.01, (float(b[3]) - float(b[1])) * 0.5 / float(ah))
        face_uv = (cx / float(aw), cy / float(ah), face_top_uv, face_half_uv)
        # Stack duplicate copies so same-face clones don't fully occlude
        if overlay_amt > 0.001:
            dup = i // n_real
            if face_amt >= tile_amt:
                # Above Face: keep primary on the face; only clones climb up
                if dup > 0:
                    face_uv = (
                        face_uv[0],
                        max(0.04, face_uv[1] - 0.07 * dup),
                        max(0.0, face_top_uv - 0.07 * dup),
                        face_half_uv,
                    )
            else:
                # flat tiles: slight horizontal stagger for duplicates
                face_uv = (
                    min(0.92, max(0.08, face_uv[0] + (0.05 * ((dup % 2) * 2 - 1) * ((dup + 1) // 2)))),
                    face_uv[1],
                    face_top_uv,
                    face_half_uv,
                )
        pose_fn = _journey_pose_c if set_idx == 1 else _journey_pose_b
        a = pose_fn(
            mode_from, i, n, int(t['id']), now, jspeed, scale_f, cols, rows, panel_grid, face_uv
        )
        if mode_from == mode_to or morph_u >= 0.999:
            # Use destination pose when morph is effectively done (Over Video
            # has no face_amt override — using mode_from here caused a 1-frame snap).
            bpose = pose_fn(
                mode_to, i, n, int(t['id']), now, jspeed, scale_f, cols, rows, panel_grid, face_uv
            )
            dstx, dsty, panel, rot = bpose
        else:
            bpose = pose_fn(
                mode_to, i, n, int(t['id']), now, jspeed, scale_f, cols, rows, panel_grid, face_uv
            )
            dstx = _lerp(a[0], bpose[0], morph_u)
            dsty = _lerp(a[1], bpose[1], morph_u)
            panel = _lerp(a[2], bpose[2], morph_u)
            rot = _lerp_angle(a[3], bpose[3], morph_u)

        # Above Face / Over Video: panel matches the tracked face square in UV
        if max(face_amt, tile_amt) > 0.001:
            face_panel = float(side) / max(1.0, float(min(aw, ah)))
            panel = _lerp(panel, face_panel, max(face_amt, tile_amt))

        data[0, i] = 1.0
        data[1, i] = left
        data[2, i] = max(0.0, right)
        data[3, i] = max(0.0, bottom)
        data[4, i] = max(0.0, top)
        data[5, i] = dstx
        data[6, i] = dsty
        data[7, i] = panel
        data[8, i] = float(t['id'])
        data[9, i] = rot
        data[10, i] = float(mode_to)

        # Lock square box pixel size on GPU nodes (expr custom-res is unreliable in slots)
        try:
            src = comp.op('source_router')
            sw = max(1, int(src.width)) if src else 1440
            sh = max(1, int(src.height)) if src else 810
            px = max(32, int(panel * min(sw, sh)))
            box_px = max(32, int(px * 1.45))
            for name in ('rsz_%d' % i, 'border_%d' % i, 'labelbar_%d' % i, 'labeltxt_%d' % i):
                node = comp.op(name)
                if node is None:
                    continue
                node.par.outputresolution = 'custom'
                node.par.outputaspect = 'resolution'
                node.par.resolutionw = px
                node.par.resolutionh = px
            for name in ('box_side_%d' % i, 'box_top_%d' % i, 'box_side_t_%d' % i, 'box_top_t_%d' % i, 'box_front_t_%d' % i, 'box_canvas_%d' % i, 'box_mid_%d' % i, 'box_mid2_%d' % i, 'box_assy_%d' % i):
                node = comp.op(name)
                if node is None:
                    continue
                node.par.outputresolution = 'custom'
                node.par.outputaspect = 'resolution'
                node.par.resolutionw = box_px
                node.par.resolutionh = box_px
            pb = comp.op('placeb_%d' % i)
            if pb is not None:
                # 2D face stage parked — output is always the 3D boxes render
                pb.par.tx = 10
                pb.par.ty = 10
                pb.par.rotate = 0
            # Real 3D boxes on every journey chapter (spin only on 3D Boxes)
            geo = comp.op('boxes3d/geo_%d' % i)
            if geo is not None:
                if data[0, i] > 0.5:
                    # UV→world matches ortho visible frame (aspect-correct)
                    wx, wy = _uv_to_world(dstx, dsty, ortho_w, h_over_w)
                    sz = _panel_to_world_size(panel, cube_size, xmax, xmin, ymax, ymin)
                    # Above Face / Over Video: cube matches the on-screen face size
                    face_flat = max(face_amt, tile_amt)
                    if face_flat > 0.001:
                        sz_face = _face_to_world_size(side, aw, ortho_w)
                        sz = _lerp(sz, sz_face, face_flat)
                    # Above Face: first cube on the face; extras stack above the head
                    if face_amt > 0.01:
                        dup = i // n_real
                        fx_uv = cx / float(aw)
                        fy_uv = cy / float(ah)
                        ax, on_wy = _uv_to_world(fx_uv, fy_uv, ortho_w, h_over_w)
                        if dup <= 0:
                            target_wy = on_wy
                        else:
                            ftop = float(b[1]) / float(ah)
                            _, top_wy = _uv_to_world(fx_uv, ftop, ortho_w, h_over_w)
                            gap = max(0.02, sz * 0.22)
                            target_wy = top_wy + (sz * 0.5) + gap + (dup - 1) * (sz * 1.1)
                            # Prefer hanging slightly off the top edge over covering the face
                            target_wy = min(target_wy, ymax + sz * 0.2)
                        wx = _lerp(wx, ax, face_amt)
                        wy = _lerp(wy, target_wy, face_amt)
                        half_x = float(ortho_w) * 0.5
                        half_y = half_x * h_over_w
                        dstx = max(0.02, min(0.98, wx / max(1e-6, 2.0 * half_x) + 0.5))
                        dsty = max(0.02, min(0.98, 0.5 - wy / max(1e-6, 2.0 * half_y)))
                        data[5, i] = dstx
                        data[6, i] = dsty
                    elif tile_amt > 0.01:
                        # Over Video: pin to tracked face centres (same override Above Face gets)
                        fx_uv = cx / float(aw)
                        fy_uv = cy / float(ah)
                        ax, ay = _uv_to_world(fx_uv, fy_uv, ortho_w, h_over_w)
                        wx = _lerp(wx, ax, tile_amt)
                        wy = _lerp(wy, ay, tile_amt)
                        half_x = float(ortho_w) * 0.5
                        half_y = half_x * h_over_w
                        dstx = max(0.02, min(0.98, wx / max(1e-6, 2.0 * half_x) + 0.5))
                        dsty = max(0.02, min(0.98, 0.5 - wy / max(1e-6, 2.0 * half_y)))
                        data[5, i] = dstx
                        data[6, i] = dsty
                    box_world.append({'i': i, 'x': wx, 'y': wy, 'sz': sz})
                    # Creative / Expressive rotations per chapter
                    rot_fn = _journey_rot_c if set_idx == 1 else _journey_rot_b
                    entering_flat = (
                        int(mode_to) in (FACE_MODE, TILE_MODE)
                        and int(mode_from) not in (FACE_MODE, TILE_MODE)
                    )
                    if entering_flat:
                        # No tumble while morphing into Over Video
                        grx, gry, grz = 0.0, 0.0, 0.0
                    else:
                        ra = rot_fn(mode_from, i, n, int(t['id']), now, jspeed)
                        if mode_from == mode_to or morph_u >= 0.999:
                            rb = rot_fn(mode_to, i, n, int(t['id']), now, jspeed)
                            grx, gry, grz = rb
                        else:
                            rb = rot_fn(mode_to, i, n, int(t['id']), now, jspeed)
                            grx = _lerp_angle(ra[0], rb[0], morph_u)
                            gry = _lerp_angle(ra[1], rb[1], morph_u)
                            grz = _lerp_angle(ra[2], rb[2], morph_u)
                        flat_lock = max(0.0, min(1.0, max(face_amt, tile_amt) * 2.0))
                        if flat_lock > 0.001:
                            grx = _lerp_angle(grx, 0.0, flat_lock)
                            gry = _lerp_angle(gry, 0.0, flat_lock)
                            grz = _lerp_angle(grz, 0.0, flat_lock)
                    geo.par.rx = grx
                    geo.par.ry = gry
                    geo.par.rz = grz
                    try:
                        boxsop = geo.op('box')
                        if boxsop is not None:
                            boxsop.par.texture = 'faceoutside'
                            boxsop.par.sizex = sz
                            boxsop.par.sizey = sz
                            boxsop.par.sizez = sz
                        mat = geo.op('mat')
                        face = comp.op('rsz_%d' % i)
                        if mat is not None and face is not None:
                            mat.par.colormap = face.path
                            try:
                                mat.par.emitmap = face.path
                            except Exception:
                                pass
                            # Brightness slider drives emit + ambient/diffuse
                            try:
                                amb = 0.35 + 0.65 * cube_bright
                                mat.par.diffr = amb
                                mat.par.diffg = amb
                                mat.par.diffb = amb
                                mat.par.ambr = amb
                                mat.par.ambg = amb
                                mat.par.ambb = amb
                                mat.par.emitr = cube_bright
                                mat.par.emitg = cube_bright
                                mat.par.emitb = cube_bright
                            except Exception:
                                pass
                    except Exception:
                        pass
                else:
                    geo.par.tx = 30
                    geo.par.ty = 0
                    geo.par.tz = 0

            pl = comp.op('place_%d' % i)
            if pl is not None:
                pl.par.sx = float(px) / float(sw)
                pl.par.sy = float(px) / float(sh)
                pl.par.tx = 10
                pl.par.ty = 10
                pl.par.rotate = 0
            # Fake 2D extruded sides stay off
            for bname in ('box_side_fade_%d' % i, 'box_top_fade_%d' % i):
                bf = comp.op(bname)
                if bf is not None:
                    bf.par.opacity = 0.0
            # Connect-mode link lines (2D stage — hidden while output is 3D-only)
            line = comp.op('line_%d' % i)
            if line is not None:
                lf = comp.op('line_fade_%d' % i)
                if lf is not None:
                    lf.par.opacity = 0.0
        except Exception:
            pass

    # Push cubes apart so they never overlap; optionally keep inside visible sides
    constrain_sides = True
    try:
        constrain_sides = bool(comp.par.Constrainsides)
    except Exception:
        constrain_sides = True
    stop_overlap = True
    try:
        stop_overlap = bool(comp.par.Stopoverlap)
    except Exception:
        stop_overlap = True
    # Above Face / Over Video always allow overlap (ignore Stop Overlapping)
    if max(face_amt, tile_amt) > 0.5:
        stop_overlap = False
    spread = 1.25
    try:
        spread = max(0.0, float(comp.par.Cubespread))
    except Exception:
        spread = 1.25
    if box_world:
        if stop_overlap:
            # 1.05 = edges almost touching; Cubespread only adds EXTRA space.
            # (Old formula used spread as a multiplier, so spread=0 → still overlapped.)
            spin_boost = 1.12 if spin_amt > 0.001 else 1.05
            gap = spin_boost + 0.4 * max(0.0, min(3.0, spread))
        else:
            gap = (1.35 if spin_amt > 0.001 else 1.15) * max(0.05, spread)
        # Fit cubes to the shorter visible axis on both portrait and landscape
        # (skip on Above Face / Over Video — size must match the video face)
        sz_cap = _frame_size_cap(len(box_world), xmax, xmin, ymax, ymin, gap)
        face_flat = max(face_amt, tile_amt)
        for b in box_world:
            if face_flat > 0.5:
                continue
            if b['sz'] > sz_cap:
                b['sz'] = sz_cap
                geo = comp.op('boxes3d/geo_%d' % b['i'])
                if geo is not None:
                    boxsop = geo.op('box')
                    if boxsop is not None:
                        boxsop.par.sizex = sz_cap
                        boxsop.par.sizey = sz_cap
                        boxsop.par.sizez = sz_cap
        max_sz = max(b['sz'] for b in box_world)
        min_dist = max_sz * gap
        # If packing still exceeds the shorter axis, soften distance so separation can converge
        short_span = min(xmax - xmin, ymax - ymin)
        if constrain_sides or is_portrait or (src_w / max(1.0, src_h)) > 1.05:
            cols = max(1, int(math.ceil(math.sqrt(float(len(box_world))))))
            fit_span = max(1e-6, short_span - max_sz)
            max_pair = fit_span / max(1, cols - 1) if cols > 1 else fit_span
            if min_dist > max_pair:
                if stop_overlap and face_flat <= 0.5:
                    # Shrink cubes to keep edge-to-edge instead of allowing overlap
                    fit_sz = max(0.06, max_pair / max(1.02, gap))
                    for b in box_world:
                        if b['sz'] > fit_sz:
                            b['sz'] = fit_sz
                            geo = comp.op('boxes3d/geo_%d' % b['i'])
                            if geo is not None:
                                boxsop = geo.op('box')
                                if boxsop is not None:
                                    boxsop.par.sizex = fit_sz
                                    boxsop.par.sizey = fit_sz
                                    boxsop.par.sizez = fit_sz
                    max_sz = max(b['sz'] for b in box_world)
                    min_dist = max_sz * gap
                    if min_dist > max_pair:
                        min_dist = max(max_sz * 1.02, max_pair)
                else:
                    min_dist = max(max_sz * 1.02, max_pair)
        pts = [[b['x'], b['y']] for b in box_world]
        # Inset by half cube size so faces don't clip past the frame edges
        edge_m = max_sz * 0.55
        sep_iters = int(12 + 10 * min(2.0, spread if spread > 0.05 else (1.0 if stop_overlap else 0.0)))
        # Extra settle passes on non-square frames (portrait or landscape)
        if abs((src_w / max(1.0, src_h)) - 1.0) > 0.08:
            sep_iters = int(sep_iters * 1.5)
        if stop_overlap:
            sep_iters = max(sep_iters, 24)
        keep_in_frame = constrain_sides or is_portrait or (src_w / max(1.0, src_h)) > 1.05
        if face_amt > 0.85 or tile_amt > 0.85:
            # Stay glued near tracked faces; Stop Overlapping ignored on these chapters
            if keep_in_frame:
                soft_m = max_sz * 0.35
                for k, b in enumerate(box_world):
                    pts[k][0] = max(xmin + soft_m, min(xmax - soft_m, pts[k][0]))
                    pts[k][1] = max(ymin + soft_m, min(ymax - soft_m, pts[k][1]))
        elif stop_overlap:
            _separate_boxes(pts, min_dist, iters=sep_iters)
            if keep_in_frame:
                _fit_boxes_in_frame(
                    pts, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, margin=edge_m)
                _separate_boxes(pts, min_dist * 0.98, iters=max(10, sep_iters // 2))
                for k, b in enumerate(box_world):
                    pts[k][0] = max(xmin + edge_m, min(xmax - edge_m, pts[k][0]))
                    pts[k][1] = max(ymin + edge_m, min(ymax - edge_m, pts[k][1]))
            else:
                _separate_boxes(pts, min_dist * 0.98, iters=max(10, sep_iters // 2))
                # Non-square frames still keep cubes inside even if constrain is off
                if is_portrait or (src_w / max(1.0, src_h)) > 1.05:
                    for k, b in enumerate(box_world):
                        pts[k][0] = max(xmin + edge_m, min(xmax - edge_m, pts[k][0]))
                        pts[k][1] = max(ymin + edge_m, min(ymax - edge_m, pts[k][1]))
            # Final pass: enforce no-overlap after clamps
            _separate_boxes(pts, max_sz * 1.02, iters=max(12, sep_iters // 2))
        elif keep_in_frame:
            for k, b in enumerate(box_world):
                pts[k][0] = max(xmin + edge_m, min(xmax - edge_m, pts[k][0]))
                pts[k][1] = max(ymin + edge_m, min(ymax - edge_m, pts[k][1]))
        # Smooth world positions on portrait to avoid frame-to-frame packing flicker
        # Above Face / Over Video must stick to trackers — no lag smoothing.
        if face_amt > 0.85 or tile_amt > 0.85:
            smooth = 1.0
        else:
            smooth = 0.4 if is_portrait else 1.0
        live_ids = set()
        for k, b in enumerate(box_world):
            geo = comp.op('boxes3d/geo_%d' % b['i'])
            if geo is None:
                continue
            tx, ty = pts[k][0], pts[k][1]
            if keep_in_frame:
                if face_amt > 0.85 or tile_amt > 0.85:
                    # Soft sides only — allow Above Face cubes to sit past the top
                    # edge rather than being shoved back down onto the head.
                    soft_m = max_sz * 0.3
                    tx = max(xmin + soft_m, min(xmax - soft_m, tx))
                    if face_amt > 0.85:
                        ty = max(ymin + soft_m, min(ymax + max_sz * 0.25, ty))
                    else:
                        ty = max(ymin + soft_m, min(ymax - soft_m, ty))
                else:
                    tx = max(xmin + edge_m, min(xmax - edge_m, tx))
                    ty = max(ymin + edge_m, min(ymax - edge_m, ty))
            bid = int(b['i'])
            live_ids.add(bid)
            prev = _box_xy_smooth.get(bid)
            if prev is not None and smooth < 0.999:
                tx = prev[0] + (tx - prev[0]) * smooth
                ty = prev[1] + (ty - prev[1]) * smooth
            _box_xy_smooth[bid] = (tx, ty)
            geo.par.tx = tx
            geo.par.ty = ty
            geo.par.tz = 0.0
        for old_id in list(_box_xy_smooth.keys()):
            if old_id not in live_ids:
                _box_xy_smooth.pop(old_id, None)

    # Clear unused GPU slots beyond the filled box count
    clear_from = len(tracks) if tracks else 0
    for i in range(clear_from, MAX_SLOTS):
        try:
            pb = comp.op('placeb_%d' % i)
            if pb is not None:
                pb.par.tx = 10
                pb.par.ty = 10
                pb.par.rotate = 0
            lf = comp.op('line_fade_%d' % i)
            if lf is not None:
                lf.par.opacity = 0.0
            geo = comp.op('boxes3d/geo_%d' % i)
            if geo is not None:
                geo.par.tx = 30
                geo.par.ty = 0
                geo.par.tz = 0
            # zero active flag already default for unwritten samples
        except Exception:
            pass

    # Always output the 3D boxes render (every journey chapter uses cubes)
    try:
        cam = comp.op('boxes3d/cam')
        rend = comp.op('boxes3d/render')
        la = comp.op('boxes3d/lookat')
        light = comp.op('boxes3d/light')
        fill = comp.op('boxes3d/fill')
        if cam is not None:
            cam.par.projection = 'ortho'
            # Smooth angled → frontal with flat_amt (Above Face / Over Video).
            # Hard cut at 0.5 caused a 1-frame pop on Creative (spinning cubes).
            fcam = max(0.0, min(1.0, float(flat_amt)))
            _ang = math.radians(18.0 * (1.0 - fcam))
            _elev = math.radians(10.0 * (1.0 - fcam))
            _dist = _lerp(4.2, 5.0, fcam)
            cam.par.orthowidth = _lerp(2.8, 2.0, fcam)
            cam.par.tx = _dist * math.sin(_ang)
            cam.par.ty = _dist * math.sin(_elev)
            cam.par.tz = _dist * math.cos(_ang) * math.cos(_elev)
            if la is not None:
                cam.par.lookat = la
                cam.par.rx = 0
                cam.par.ry = 0
                cam.par.rz = 0
            else:
                cam.par.rx = -math.degrees(math.atan2(cam.par.ty.eval(), math.hypot(cam.par.tx.eval(), cam.par.tz.eval())))
                cam.par.ry = math.degrees(math.atan2(cam.par.tx.eval(), cam.par.tz.eval()))
                cam.par.rz = 0
        if light is not None:
            try:
                light.par.lighttype = 'distant'
                light.par.dimmer = 1.0 + 1.8 * cube_bright
                light.par.tx = 2.0
                light.par.ty = 3.0
                light.par.tz = 4.0
                light.par.rx = -35.0
                light.par.ry = 25.0
            except Exception:
                pass
        if fill is not None:
            try:
                fill.par.lighttype = 'distant'
                fill.par.dimmer = 0.4 + 1.0 * cube_bright
                fill.par.tx = -2.0
                fill.par.ty = 1.5
                fill.par.tz = 3.0
                fill.par.rx = -20.0
                fill.par.ry = -30.0
            except Exception:
                pass
        # Keep select TOPs matched to live source aspect (portrait OR landscape)
        _ensure_select_follows_top(comp.op('source_router'))
        _ensure_select_follows_top(comp.op('boxes3d_sel'))
        _ensure_select_follows_top(comp.op('journey_out'))
        if rend is not None:
            rend.par.bgcolorr = 0
            rend.par.bgcolorg = 0
            rend.par.bgcolorb = 0
            # Transparent clear — black/video underlay is composited underneath
            rend.par.bgcolora = 0
            # Lock render to source resolution every cook (avoids res flicker)
            try:
                src = comp.op('source_router')
                if src is not None:
                    rend.par.outputresolution = 'custom'
                    rend.par.resolutionw = max(1, int(src.width))
                    rend.par.resolutionh = max(1, int(src.height))
            except Exception:
                pass
            try:
                lights = []
                if light is not None:
                    lights.append(light.path)
                if fill is not None:
                    lights.append(fill.path)
                if lights:
                    rend.par.lights = ' '.join(lights)
            except Exception:
                pass

        boxes_fade = comp.op('journey_boxes_fade')
        if boxes_fade is not None:
            boxes_fade.par.opacity = 1.0

        # Always composite cubes over a crossfaded underlay (black ↔ live video).
        # Never swap journey_out between TOPs mid-morph — that caused a 1-frame flash.
        jout = comp.op('journey_out')
        boxes_sel = comp.op('boxes3d_sel')
        rend_op = comp.op('boxes3d/render')
        face_over = comp.op('face_cubes_over')
        src = comp.op('source_router')
        if boxes_sel is not None and rend_op is not None:
            boxes_sel.par.top = rend_op.path
        _set_lines(comp, 0.0, 0.0)
        bg_mix = _ensure_overlay_bg_mix(comp)
        target = _overlay_video_target(mode_from, mode_to, mode, _morph_active, morph_u)
        # Ease toward target — never snap on zero-dt re-cooks (that caused a
        # 1-frame full-video flash when Connect → Above Face finished).
        if float_dt > 0.0:
            if target >= _overlay_fade:
                fade_secs = max(0.05, float(_OVERLAY_FADE_IN_SECS))
            else:
                fade_secs = max(0.05, float(_OVERLAY_FADE_OUT_SECS))
            k = min(1.0, float(float_dt) / fade_secs)
            _overlay_fade = _overlay_fade + (target - _overlay_fade) * k
            if abs(_overlay_fade - target) < 0.002:
                _overlay_fade = target
        if bg_mix is not None:
            try:
                bg_mix.par.cross = max(0.0, min(1.0, float(_overlay_fade)))
            except Exception:
                pass
        # Transparent cube render so underlay shows around boxes
        if rend_op is not None:
            rend_op.par.bgcolora = 0
        if face_over is not None and jout is not None:
            jout.par.top = face_over.path
        elif jout is not None and boxes_sel is not None:
            jout.par.top = boxes_sel.path
            if rend_op is not None:
                rend_op.par.bgcolora = 1
        # Hard-lock out1 to journey_out
        try:
            out1 = comp.op('out1')
            jn = comp.op('journey_out')
            if out1 is not None and jn is not None:
                conn = out1.inputConnectors[0]
                if not conn.connections or conn.connections[0].owner != jn:
                    while conn.connections:
                        conn.disconnect()
                    conn.connect(jn)
        except Exception:
            pass
    except Exception:
        pass

    scriptOp.clear()
    for name in chans:
        scriptOp.appendChan(name)
    scriptOp.numSamples = MAX_SLOTS
    for ci, name in enumerate(chans):
        chan = scriptOp[name]
        for s in range(MAX_SLOTS):
            chan[s] = float(data[ci, s])
    jname = _jname(mode_to)
    n_real = len(real_tracks)
    n_boxes = len(tracks)
    tag = ('1', '2')[set_idx] if set_idx in (0, 1) else '1'
    if _morph_active and mode_from != mode_to:
        jfrom = _jname(mode_from)
        _set_status(comp, '[{}] {} → {} | {} tracked → {} boxes / detect every {}'.format(
            tag, jfrom, jname, n_real, n_boxes, detect_every))
    else:
        _set_status(comp, '[{}] {} | {} tracked → {} boxes / detect every {}'.format(
            tag, jname, n_real, n_boxes, detect_every))

def onSetupParameters(scriptOp):
    return

def onPulse(par):
    return
'''

# Script SOP that links cube centres with polylines (Set C "Wires" / "Web")
LINES_SOP_CB = r'''
def cook(scriptOp):
    scriptOp.clear()
    geo = scriptOp.parent()
    boxes = geo.parent()
    pts = []
    for i in range(8):
        g = boxes.op('geo_%d' % i)
        if g is None:
            continue
        try:
            x = float(g.par.tx); y = float(g.par.ty); z = float(g.par.tz)
        except Exception:
            continue
        if abs(x) > 5.0:  # parked slot
            continue
        pts.append((x, y, z))
    if len(pts) < 2:
        return
    try:
        web = int(geo.fetch('linemode', 0) or 0)
    except Exception:
        web = 0
    pts.sort(key=lambda p: p[0])
    pairs = []
    if web:
        for a in range(len(pts)):
            for b in range(a + 1, len(pts)):
                pairs.append((pts[a], pts[b]))
    else:
        for a in range(len(pts) - 1):
            pairs.append((pts[a], pts[a + 1]))
    for pa, pb in pairs:
        poly = scriptOp.appendPoly(2, closed=False, addPoints=True)
        poly[0].point.x = pa[0]; poly[0].point.y = pa[1]; poly[0].point.z = pa[2]
        poly[1].point.x = pb[0]; poly[1].point.y = pb[1]; poly[1].point.z = pb[2]
    return
'''

# Builds the Set C effect chain + connector-line geometry. Idempotent so it can
# run against an already-built tox as well as a fresh one.
FXC_BUILDER = r'''
def build_fx_c(c, lines_cb_text):
    def mk(kind, name, x, y, parent=None):
        host = parent if parent is not None else c
        o = host.op(name)
        if o is None:
            o = host.create(kind, name)
        try:
            o.nodeX = x
            o.nodeY = y
        except Exception:
            pass
        return o

    def wire(node, idx, srcop):
        if node is None or srcop is None:
            return
        conn = node.inputConnectors[idx]
        if conn.connections and conn.connections[0].owner is srcop:
            return
        while conn.connections:
            conn.disconnect()
        conn.connect(srcop)

    def setp(node, **kw):
        for pname, val in kw.items():
            try:
                setattr(node.par, pname, val)
            except Exception:
                pass

    bx, by = 2400, 400
    rend = c.op('boxes3d/render')

    src = mk('selectTOP', 'fxc_src', bx, by)
    if rend is not None:
        setp(src, top=rend.path)

    fb = mk('feedbackTOP', 'fxc_fb', bx, by - 160)
    wire(fb, 0, src)
    fb_x = mk('transformTOP', 'fxc_fb_x', bx + 150, by - 160)
    wire(fb_x, 0, fb)
    setp(fb_x, extend='zero')
    fb_l = mk('levelTOP', 'fxc_fb_l', bx + 300, by - 160)
    wire(fb_l, 0, fb_x)
    setp(fb_l, opacity=0.0)

    mix = mk('compositeTOP', 'fxc_mix', bx + 450, by)
    wire(mix, 0, fb_l)
    wire(mix, 1, src)
    setp(mix, operand='add')

    noise = mk('noiseTOP', 'fxc_noise', bx + 450, by - 320)
    setp(noise, type='random', mono=True, monochrome=True)

    disp = mk('displaceTOP', 'fxc_disp', bx + 600, by)
    wire(disp, 0, mix)
    wire(disp, 1, noise)
    setp(disp, horzsource='red', vertsource='green', extend='zero',
         displaceweightx=0.0, displaceweighty=0.0)

    ch_r = mk('transformTOP', 'fxc_ch_r', bx + 750, by - 130)
    wire(ch_r, 0, disp)
    setp(ch_r, extend='zero', tunit='fraction')
    ch_b = mk('transformTOP', 'fxc_ch_b', bx + 750, by + 130)
    wire(ch_b, 0, disp)
    setp(ch_b, extend='zero', tunit='fraction')

    reo1 = mk('reorderTOP', 'fxc_reo1', bx + 900, by)
    wire(reo1, 0, ch_r)
    wire(reo1, 1, disp)
    setp(reo1, outputred='input1', outputredchan='red',
         outputgreen='input2', outputgreenchan='green',
         outputblue='input2', outputbluechan='blue',
         outputalpha='input2', outputalphachan='alpha')
    reo2 = mk('reorderTOP', 'fxc_reo2', bx + 1050, by)
    wire(reo2, 0, ch_b)
    wire(reo2, 1, reo1)
    setp(reo2, outputred='input2', outputredchan='red',
         outputgreen='input2', outputgreenchan='green',
         outputblue='input1', outputbluechan='blue',
         outputalpha='input2', outputalphachan='alpha')

    scan_n = mk('noiseTOP', 'fxc_scan_noise', bx + 1050, by - 320)
    setp(scan_n, type='random', mono=True, monochrome=True,
         sx=0.001, sy=240.0, amp=0.45, offset=0.6)
    scan_m = mk('compositeTOP', 'fxc_scan', bx + 1200, by - 160)
    wire(scan_m, 0, scan_n)
    wire(scan_m, 1, reo2)
    setp(scan_m, operand='multiply')
    scan_sw = mk('switchTOP', 'fxc_scan_sw', bx + 1350, by)
    wire(scan_sw, 0, reo2)
    wire(scan_sw, 1, scan_m)
    setp(scan_sw, index=0)

    pix_dn = mk('resolutionTOP', 'fxc_pix_dn', bx + 1500, by - 160)
    wire(pix_dn, 0, scan_sw)
    setp(pix_dn, filtertype='nearest')
    pix_up = mk('resolutionTOP', 'fxc_pix_up', bx + 1650, by - 160)
    wire(pix_up, 0, pix_dn)
    setp(pix_up, filtertype='nearest', inputfiltertype='nearest')
    pix_sw = mk('switchTOP', 'fxc_pix_sw', bx + 1800, by)
    wire(pix_sw, 0, scan_sw)
    wire(pix_sw, 1, pix_up)
    setp(pix_sw, index=0)

    blur = mk('blurTOP', 'fxc_blur', bx + 1950, by - 160)
    wire(blur, 0, pix_sw)
    setp(blur, size=0)
    bloom = mk('compositeTOP', 'fxc_bloom', bx + 2100, by - 160)
    wire(bloom, 0, blur)
    wire(bloom, 1, pix_sw)
    setp(bloom, operand='add')
    bloom_sw = mk('switchTOP', 'fxc_bloom_sw', bx + 2250, by)
    wire(bloom_sw, 0, pix_sw)
    wire(bloom_sw, 1, bloom)
    setp(bloom_sw, index=0)

    lvl = mk('levelTOP', 'fxc_lvl', bx + 2400, by)
    wire(lvl, 0, bloom_sw)
    fx_out = mk('nullTOP', 'fxc_out', bx + 2550, by)
    wire(fx_out, 0, lvl)
    setp(fb, top=fx_out.path)

    # Connector lines live in the 3D scene so they follow the camera
    boxes = c.op('boxes3d')
    if boxes is not None:
        lg = boxes.op('lines_geo')
        if lg is None:
            lg = boxes.create('geometryCOMP', 'lines_geo')
            for kid in list(lg.children):
                try:
                    kid.destroy()
                except Exception:
                    pass
        lg.nodeX = 200
        lg.nodeY = -420
        lcb = lg.op('lines_callbacks')
        if lcb is None:
            lcb = lg.create('textDAT', 'lines_callbacks')
        lcb.text = lines_cb_text
        lcb.nodeX = -200
        lcb.nodeY = 100
        lsop = lg.op('lines_sop')
        if lsop is None:
            lsop = lg.create('scriptSOP', 'lines_sop')
        setp(lsop, callbacks=lcb)
        try:
            lsop.display = True
            lsop.render = True
        except Exception:
            pass
        lmat = lg.op('lines_mat')
        if lmat is None:
            lmat = lg.create('lineMAT', 'lines_mat')
        setp(lmat, linenearcolorr=1.0, linenearcolorg=0.55, linenearcolorb=0.2,
             linenearalpha=0.85, widthnear=3.0, widthfar=3.0)
        setp(lg, material=lmat.path)
        try:
            lg.par.display = False
        except Exception:
            pass
    return c.op('fxc_out')
'''

# --- build network ---
root = op('/project1')
old = root.op('__build_face_isolator')
if old:
    old.destroy()

c = root.create('baseCOMP', '__build_face_isolator')
page = c.appendCustomPage('Face Isolator')

def tog(n, l, v):
    p = page.appendToggle(n, label=l); p.default = v; p.val = v; return p
def flt(n, l, v, lo, hi):
    p = page.appendFloat(n, label=l)
    p.default = v; p.val = v; p.min = lo; p.max = hi; p.normMin = lo; p.normMax = hi
    p.clampMin = True; p.clampMax = True; return p
def iint(n, l, v, lo, hi):
    p = page.appendInt(n, label=l)
    p.default = v; p.val = v; p.min = lo; p.max = hi; p.normMin = lo; p.normMax = hi
    p.clampMin = True; p.clampMax = True; return p

tog('Active', 'Active', True)
flt('Confidence', 'Face Confidence', .90, .1, .95)
iint('Detectionrate', 'Detect Every Frames', 12, 8, 60)
iint('Processresolution', 'Processing Width', 320, 160, 400)
iint('Maxfaces', 'Maximum Faces', 8, 1, 8)
flt('Padding', 'Face Padding', .28, 0, 1)
flt('Facescale', 'Face Panel Scale', 0.88, .25, 1.0)
flt('Smoothing', 'Tracking Smoothing', .75, 0, .95)
iint('Persistence', 'Tracking Persistence', 60, 8, 180)
tog('Monochrome', 'Monochrome Faces', True)
# Shared journey/cube settings — own tab (not on Chapters 1/2)
cs_page = c.appendCustomPage('Chapter Settings')
p = cs_page.appendMenu('Journeyset', label='Chapter Set')
c.cook(force=True)
p = c.par.Journeyset
p.menuNames = ['creative', 'expressive']
p.menuLabels = ['1 Creative', '2 Expressive']
p.default = 0
p.val = 0
cs_page.appendPulse('Journeypulse', label='Pulse Journey')

def cs_flt(n, l, v, lo, hi):
    p = cs_page.appendFloat(n, label=l)
    p.default = v; p.val = v; p.min = lo; p.max = hi; p.normMin = lo; p.normMax = hi
    p.clampMin = True; p.clampMax = True; return p
def cs_tog(n, l, v):
    p = cs_page.appendToggle(n, label=l); p.default = v; p.val = v; return p

cs_flt('Morphsecs', 'Morph Seconds', 1.25, 0.2, 4.0)
cs_flt('Journeyspeed', 'Journey Speed', 1.0, 0, 3)
cs_flt('Cubebrightness', 'Cube Brightness', 0.45, 0, 1)
cs_flt('Cubesize', 'Cube Size', 0.4, 0.05, 2)  # bind Audiooutlow here (0–1 driver)
cs_flt('Cubesizelow', 'Cube Size Low', 0.15, 0.05, 2)
cs_flt('Cubesizehigh', 'Cube Size High', 0.9, 0.05, 2)
cs_flt('Cubesizesmooth', 'Cube Size Smooth', 0.9, 0, 1)
cs_flt('Cubespread', 'Cube Spread', 1.25, 0, 3)
cs_tog('Stopoverlap', 'Stop Overlapping', True)
cs_tog('Constrainsides', 'Constrain to Sides', True)

# Chapter 1 — Creative (menu + enables)
cb_page = c.appendCustomPage('Chapters 1')
p = cb_page.appendMenu('Pulsemodeb', label='Chapter')
c.cook(force=True)
p = c.par.Pulsemodeb
p.menuNames = [
    'overvideo', 'isometric', 'hundredfold', 'connect', 'cascade',
    'orbit', 'mirror', 'boxes3d', 'constellation', 'parade', 'arrival',
]
p.menuLabels = [
    '1 Over Video', '2 Isometric March', '3 Hundredfold', '4 The Connect', '5 Cascade', '6 Orbit',
    '7 Mirror Hall', '8 3D Boxes', '9 Constellation', '10 Parade', '11 Arrival',
]
p.default = 0
p.val = 0
for _pn, _pl in zip(
    [
        'Cbovervideo', 'Cbisometric', 'Cbhundredfold', 'Cbconnect', 'Cbcascade', 'Cborbit',
        'Cbmirror', 'Cbboxes3d', 'Cbconstellation', 'Cbparade', 'Cbarrival',
    ],
    [
        '1 Over Video', '2 Isometric March', '3 Hundredfold', '4 The Connect', '5 Cascade', '6 Orbit',
        '7 Mirror Hall', '8 3D Boxes', '9 Constellation', '10 Parade', '11 Arrival',
    ],
):
    p = cb_page.appendToggle(_pn, label=_pl)
    p.default = True
    p.val = True

# Chapter 2 — Expressive (same chapters, wilder motion)
cc_page = c.appendCustomPage('Chapters 2')
p = cc_page.appendMenu('Pulsemodec', label='Chapter')
c.cook(force=True)
p = c.par.Pulsemodec
p.menuNames = list(c.par.Pulsemodeb.menuNames)
p.menuLabels = list(c.par.Pulsemodeb.menuLabels)
p.default = 0
p.val = 0
for _pn, _pl in zip(
    [
        'Ccovervideo', 'Ccisometric', 'Cchundredfold', 'Ccconnect', 'Cccascade', 'Ccorbit',
        'Ccmirror', 'Ccboxes3d', 'Ccconstellation', 'Ccparade', 'Ccarrival',
    ],
    [
        '1 Over Video', '2 Isometric March', '3 Hundredfold', '4 The Connect', '5 Cascade', '6 Orbit',
        '7 Mirror Hall', '8 3D Boxes', '9 Constellation', '10 Parade', '11 Arrival',
    ],
):
    p = cc_page.appendToggle(_pn, label=_pl)
    p.default = True
    p.val = True


p = page.appendStr('Status', label='Status'); p.val = 'Ready (GPU path)'; p.readOnly = True

c.par.Processresolution = 320
c.par.Detectionrate = 12
c.par.Maxfaces = 8
c.par.Confidence = 0.9

inp = c.create('inTOP', 'input1')
source = c.create('selectTOP', 'source_router')
source.par.top.expr = SOURCE_EXPR
# Follow selected TOP size — never hardcode 810x1440 (breaks 1920x1080)
source.par.outputresolution = 'custom'
source.par.outputaspect = 'resolution'
source.par.resolutionw.expr = "max(1, int(op(me.par.top).width))"
source.par.resolutionh.expr = "max(1, int(op(me.par.top).height))"

# Analysis branch — NOT in display path
analysis = c.create('fitTOP', 'analysis_resolution')
analysis.inputConnectors[0].connect(source)
analysis.par.outputresolution = 'custom'
analysis.par.resolutionw.expr = 'max(160, int(parent().par.Processresolution))'
analysis.par.resolutionh.expr = (
    "max(1, int(max(160, int(parent().par.Processresolution)) * "
    "op('source_router').height / max(op('source_router').width, 1)))"
)

tracker = c.create('scriptCHOP', 'tracker')
cb = tracker.par.callbacks.eval()
cb.text = TRACKER_CB
# Force cook every frame so floating + delayed detect keep running
tracker.par.timeslice = True

# Background at source resolution (fixed black)
bg = c.create('constantTOP', 'bg')
bg.par.colorr = 0
bg.par.colorg = 0
bg.par.colorb = 0
bg.par.alpha = 1
bg.par.outputresolution = 'custom'
bg.par.resolutionw.expr = "max(1, op('source_router').width)"
bg.par.resolutionh.expr = "max(1, op('source_router').height)"

prev = bg
face_nodes = []
for i in range(MAX_FACES):
    crop = c.create('cropTOP', 'crop_%d' % i)
    crop.inputConnectors[0].connect(source)
    crop.par.cropleftunit = 'fraction'
    crop.par.croprightunit = 'fraction'
    crop.par.cropbottomunit = 'fraction'
    crop.par.croptopunit = 'fraction'
    crop.par.cropleft.expr = "op('tracker')['cropl'][%d] if op('tracker')['active'][%d] > 0.5 else 0.4" % (i, i)
    crop.par.cropright.expr = "op('tracker')['cropr'][%d] if op('tracker')['active'][%d] > 0.5 else 0.4" % (i, i)
    crop.par.cropbottom.expr = "op('tracker')['cropb'][%d] if op('tracker')['active'][%d] > 0.5 else 0.4" % (i, i)
    crop.par.croptop.expr = "op('tracker')['cropt'][%d] if op('tracker')['active'][%d] > 0.5 else 0.4" % (i, i)

    mono = c.create('monochromeTOP', 'mono_%d' % i)
    mono.inputConnectors[0].connect(crop)
    # Bypass mono when toggle off via switch
    sw = c.create('switchTOP', 'mono_sw_%d' % i)
    sw.par.index.expr = 'parent().par.Monochrome'
    sw.inputConnectors[0].connect(crop)
    sw.inputConnectors[1].connect(mono)
    # ensure 2 inputs
    while len(sw.inputConnectors) < 2:
        pass

    # Square panel size in pixels from dstsize * min(src w,h)
    size_expr = (
        "max(32, int(op('tracker')['dstsize'][%d] * min(op('source_router').width, op('source_router').height)))" % i
    )
    sx_expr = (
        "(op('tracker')['dstsize'][%d] * min(op('source_router').width, op('source_router').height)) / max(op('source_router').width, 1)" % i
    )
    sy_expr = (
        "(op('tracker')['dstsize'][%d] * min(op('source_router').width, op('source_router').height)) / max(op('source_router').height, 1)" % i
    )
    tx_expr = "(op('tracker')['dstx'][%d] - 0.5) if op('tracker')['active'][%d] > 0.5 else 10" % (i, i)
    ty_expr = "(0.5 - op('tracker')['dsty'][%d]) if op('tracker')['active'][%d] > 0.5 else 10" % (i, i)

    panel = c.create('fitTOP', 'panel_%d' % i)
    panel.inputConnectors[0].connect(sw)
    panel.par.fit = 'fill'

    # Force square box pixels (fitTOP custom res is unreliable in slots)
    rsz = c.create('resolutionTOP', 'rsz_%d' % i)
    rsz.inputConnectors[0].connect(panel)
    rsz.par.outputresolution = 'custom'
    rsz.par.outputaspect = 'resolution'
    rsz.par.resolutionw.expr = size_expr
    rsz.par.resolutionh.expr = size_expr

    # Unused legacy place node
    placed = c.create('transformTOP', 'place_%d' % i)
    placed.inputConnectors[0].connect(rsz)
    placed.par.outputresolution = 'custom'
    placed.par.outputaspect = 'resolution'
    placed.par.resolutionw.expr = "max(1, op('source_router').width)"
    placed.par.resolutionh.expr = "max(1, op('source_router').height)"
    placed.par.tunit = 'fraction'
    placed.par.tx.expr = tx_expr
    placed.par.ty.expr = ty_expr
    placed.par.sx.expr = sx_expr
    placed.par.sy.expr = sy_expr
    try:
        placed.par.extend = 'zero'
    except Exception:
        pass

    # Border rectangle matching rsz pixel size
    border = c.create('rectangleTOP', 'border_%d' % i)
    border.par.outputresolution = 'custom'
    border.par.outputaspect = 'resolution'
    border.par.resolutionw.expr = size_expr
    border.par.resolutionh.expr = size_expr
    border.par.sizex = 1
    border.par.sizey = 1
    border.par.sizeunit = 'fraction'
    border.par.fillalpha = 0
    border.par.bgalpha = 0
    border.par.borderalpha = 1
    border.par.borderr = 1
    border.par.borderg = 0.2
    border.par.borderb = 0.05
    border.par.borderwidth = 3
    try:
        border.par.borderwidthunit = 'pixels'
    except Exception:
        pass

    # Over TOP: Input1 over Input2 — border frame must be ON TOP of the face
    # (opaque face over border completely hides the stroke)
    bordered = c.create('overTOP', 'bord_over_%d' % i)
    bordered.inputConnectors[0].connect(border)
    bordered.inputConnectors[1].connect(rsz)

    # Face ID label bar (bottom strip + text)
    labelbar = c.create('rectangleTOP', 'labelbar_%d' % i)
    labelbar.par.outputresolution = 'custom'
    labelbar.par.outputaspect = 'resolution'
    labelbar.par.resolutionw.expr = size_expr
    labelbar.par.resolutionh.expr = size_expr
    labelbar.par.sizex = 1
    labelbar.par.sizey = 0.16
    labelbar.par.sizeunit = 'fraction'
    labelbar.par.centerx = 0
    labelbar.par.centery = -0.42
    labelbar.par.centerunit = 'fraction'
    labelbar.par.fillalpha = 0.92
    labelbar.par.fillcolorr = 1
    labelbar.par.fillcolorg = 0.2
    labelbar.par.fillcolorb = 0.05
    labelbar.par.bgalpha = 0
    labelbar.par.borderalpha = 0

    labeltxt = c.create('textTOP', 'labeltxt_%d' % i)
    labeltxt.par.outputresolution = 'custom'
    labeltxt.par.outputaspect = 'resolution'
    labeltxt.par.resolutionw.expr = size_expr
    labeltxt.par.resolutionh.expr = size_expr
    labeltxt.par.text.expr = "'ID ' + str(int(op('tracker')['faceid'][%d]))" % i
    labeltxt.par.font = 'Verdana'
    labeltxt.par.fontsizex = 18
    labeltxt.par.fontsizexunit = 'points'
    labeltxt.par.alignx = 'center'
    labeltxt.par.aligny = 'bottom'
    try:
        labeltxt.par.positiony = 8
        labeltxt.par.positionunit = 'pixels'
    except Exception:
        pass
    labeltxt.par.fontcolorr = 1
    labeltxt.par.fontcolorg = 1
    labeltxt.par.fontcolorb = 1
    labeltxt.par.fontalpha = 1
    labeltxt.par.bgalpha = 0

    label_combo = c.create('overTOP', 'label_combo_%d' % i)
    label_combo.inputConnectors[0].connect(labeltxt)
    label_combo.inputConnectors[1].connect(labelbar)

    label_fade = c.create('levelTOP', 'label_fade_%d' % i)
    label_fade.inputConnectors[0].connect(label_combo)
    label_fade.par.opacity = 1

    label_over = c.create('overTOP', 'label_over_%d' % i)
    label_over.inputConnectors[0].connect(label_fade)
    label_over.inputConnectors[1].connect(bordered)

    # Place small bordered+labeled panel onto full-frame transparent canvas
    placed2 = c.create('transformTOP', 'placeb_%d' % i)
    placed2.inputConnectors[0].connect(label_over)
    placed2.par.outputresolution = 'custom'
    placed2.par.outputaspect = 'resolution'
    placed2.par.resolutionw.expr = "max(1, op('source_router').width)"
    placed2.par.resolutionh.expr = "max(1, op('source_router').height)"
    placed2.par.tunit = 'fraction'
    placed2.par.tx.expr = tx_expr
    placed2.par.ty.expr = ty_expr
    placed2.par.sx.expr = sx_expr
    placed2.par.sy.expr = sy_expr
    try:
        placed2.par.extend = 'zero'
    except Exception:
        pass

    fade = c.create('levelTOP', 'fade_%d' % i)
    fade.inputConnectors[0].connect(placed2)
    fade.par.opacity.expr = "op('tracker')['active'][%d]" % i

    # Over TOP: Input1 over Input2 — face panel over accumulated background
    over = c.create('overTOP', 'over_%d' % i)
    over.inputConnectors[0].connect(fade)
    over.inputConnectors[1].connect(prev)
    prev = over

    # layout nodes
    crop.nodeX = 600; crop.nodeY = -i * 120
    sw.nodeX = 780; sw.nodeY = -i * 120
    mono.nodeX = 780; mono.nodeY = -i * 120 - 40
    panel.nodeX = 960; panel.nodeY = -i * 120
    rsz.nodeX = 1050; rsz.nodeY = -i * 120
    border.nodeX = 1140; border.nodeY = -i * 120
    bordered.nodeX = 1260; bordered.nodeY = -i * 120
    labelbar.nodeX = 1320; labelbar.nodeY = -i * 120
    labeltxt.nodeX = 1380; labeltxt.nodeY = -i * 120
    label_over.nodeX = 1440; label_over.nodeY = -i * 120
    placed2.nodeX = 1560; placed2.nodeY = -i * 120
    fade.nodeX = 1680; fade.nodeY = -i * 120
    over.nodeX = 1860; over.nodeY = -i * 120
    face_nodes.append(over)

out = c.create('nullTOP', 'out1')
out.inputConnectors[0].connect(prev)

# Set C effect chain + connector lines
_fxc_ns = {}
exec(FXC_BUILDER, _fxc_ns)
_fxc_ns['build_fx_c'](c, LINES_SOP_CB)

inp.nodeX = 0
source.nodeX = 160
analysis.nodeX = 320; analysis.nodeY = 200
tracker.nodeX = 480; tracker.nodeY = 200
bg.nodeX = 600; bg.nodeY = 120

for path in OUTS:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c.save(path)
    print('Saved', os.path.getsize(path), path)

print('Architecture: delayed CPU detect + GPU composite, max faces', MAX_FACES)
c.destroy()
