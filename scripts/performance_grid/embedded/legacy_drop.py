LEGACY_DROP = r'''# Explorer -> grid cell only (.tox or video file paths in args[0]).
import os

VIDEO_EXTS = {
    '.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv',
    '.mpg', '.mpeg', '.mxf', '.gif', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp',
}
VALID_CLIP_TYPES = ('video', 'tox')

def _coords(name):
    if name.startswith('cell_'):
        p = name.split('_')
        if len(p) == 3:
            return int(p[1]), int(p[2])
    return None, None

def _coords_from_panel(panel):
    p = panel
    for _ in range(8):
        if p is None:
            break
        layer, col = _coords(getattr(p, 'name', ''))
        if layer is not None:
            return layer, col
        try:
            p = p.parent()
        except Exception:
            break
    return None, None

def _root(panel):
    p = panel
    for _ in range(16):
        if p is None:
            break
        try:
            if p.op('logic') is not None:
                return p
        except Exception:
            pass
        try:
            p = p.parent()
        except Exception:
            break
    return None

panel = None
for idx in range(len(args) - 1, 0, -1):
    try:
        p = op(str(args[idx]))
        if p is not None and p.isCOMP:
            layer, col = _coords_from_panel(p)
            if layer is not None:
                panel = p if p.name.startswith('cell_') else p
                while panel is not None and not panel.name.startswith('cell_'):
                    try:
                        panel = panel.parent()
                    except Exception:
                        panel = None
                        break
                break
    except Exception:
        pass

filepath = ''
for a in args:
    try:
        s = str(a).strip().strip('"')
        if not s:
            continue
        if s.lower().startswith('file:///'):
            s = s[8:]
        elif s.lower().startswith('file://'):
            s = s[7:]
        candidate = os.path.normpath(s).replace('\\\\', '/')
        if os.path.isfile(candidate):
            filepath = candidate
            break
    except Exception:
        pass

if not panel:
    pass
elif not filepath or not os.path.isfile(filepath):
    print('Drop ignored (Explorer .tox / video only):', filepath)
else:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.tox' or ext in VIDEO_EXTS:
        layer, col = _coords_from_panel(panel)
        root = _root(panel)
        if root and layer is not None and col is not None:
            logic = root.op('logic').module
            clip_type = 'tox' if ext == '.tox' else 'video'
            if clip_type == 'tox' and hasattr(logic, 'cell_accepts_tox_clip_load'):
                if not logic.cell_accepts_tox_clip_load(layer, col):
                    print('Cannot load effect (.tox) into a video cell')
                else:
                    logic.load_cell(layer, col, clip_type, filepath)
                    print('Dropped', os.path.basename(filepath), '-> row', layer, 'col', col)
            elif clip_type == 'tox':
                ctype, src = logic.get_cell(layer, col)
                if src and str(ctype).strip().lower() == 'video':
                    print('Cannot load effect (.tox) into a video cell')
                else:
                    logic.load_cell(layer, col, clip_type, filepath)
                    print('Dropped', os.path.basename(filepath), '-> row', layer, 'col', col)
            else:
                logic.load_cell(layer, col, clip_type, filepath)
                print('Dropped', os.path.basename(filepath), '-> row', layer, 'col', col)
    else:
        print('Drop ignored (need .tox or video):', filepath)
'''
