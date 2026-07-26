CELL_DRAGDROP = r'''# Drag clips between cells; drop .tox / video from Explorer.
import os
import tdu

VIDEO_EXTS = {
    '.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv',
    '.mpg', '.mpeg', '.mxf', '.gif', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp',
}
VALID_CLIP_TYPES = ('video', 'tox')

CLIP_TAG = '__perf_cell_clip__'


def _root_from_cell(comp):
    p = comp
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


def _cell_coords(comp):
    return _resolve_drop_cell(comp)


def _resolve_drop_cell(comp):
    p = comp
    for _ in range(8):
        if p is None:
            break
        name = getattr(p, 'name', '')
        if name.startswith('cell_'):
            parts = name.split('_')
            if len(parts) == 3:
                return int(parts[1]), int(parts[2])
        try:
            p = p.parent()
        except Exception:
            break
    return None, None


def _normalize_drag_path(path):
    if path is None:
        return ''
    path = str(path).strip().strip('"')
    if not path:
        return ''
    low = path.lower()
    if low.startswith('file:///'):
        path = path[8:]
    elif low.startswith('file://'):
        path = path[7:]
    path = path.replace('\\', '/')
    if os.name == 'nt' and len(path) > 2 and path[0] == '/' and path[2] == ':':
        path = path[1:]
    elif os.name == 'nt' and len(path) > 2 and path[0] == '/' and path[2] == '/':
        path = path[1] + ':' + path[2:]
    return os.path.normpath(path).replace('\\', '/')


def _clip_item(layer, col, clip_type, path):
    return {
        CLIP_TAG: True,
        'layer': int(layer),
        'col': int(col),
        'type': str(clip_type),
        'path': str(path),
    }


def _is_clip(item):
    return isinstance(item, dict) and item.get(CLIP_TAG)


def _path_from_item(item):
    if _is_clip(item):
        return item.get('path')
    if isinstance(item, str):
        return _normalize_drag_path(item)
    if isinstance(item, tdu.FileInfo):
        try:
            return _normalize_drag_path(str(item.path))
        except Exception:
            pass
    if hasattr(item, 'path'):
        try:
            return _normalize_drag_path(str(item.path))
        except Exception:
            pass
    try:
        return _normalize_drag_path(str(item))
    except Exception:
        pass
    return None


def _file_clip(path):
    path = _normalize_drag_path(path)
    if not path:
        return None, None, 'empty path'
    ext = os.path.splitext(path)[1].lower()
    if ext == '.tox':
        if not os.path.isfile(path):
            return None, None, 'tox missing: ' + path
        return 'tox', path, ''
    if ext in VIDEO_EXTS:
        if not os.path.isfile(path):
            return None, None, 'video missing: ' + path
        return 'video', path, ''
    if ext:
        return None, None, 'bad type: ' + ext
    return None, None, 'no extension: ' + path


def _first_file_clip(items):
    reasons = []
    for item in items:
        clip_type, path, reason = _file_clip(_path_from_item(item))
        if clip_type:
            return clip_type, path, ''
        if reason:
            reasons.append(reason)
    return None, None, (reasons[0] if reasons else 'no file in drag')


def onDragStartGetItems(comp, info):
    layer, col = _resolve_drop_cell(comp)
    if layer is None:
        return []
    root = _root_from_cell(comp)
    logic = root.op('logic').module if root else None
    if logic is None:
        return []
    clip_type, path = logic.get_cell(layer, col)
    if not path:
        return []
    return [_clip_item(layer, col, clip_type, path)]


def _cell_accepts_file_drop(logic, layer, col, clip_type):
    if logic is None or clip_type != 'tox':
        return True
    if hasattr(logic, 'cell_accepts_tox_clip_load'):
        return bool(logic.cell_accepts_tox_clip_load(layer, col))
    ctype, src = logic.get_cell(layer, col)
    if src and str(ctype).strip().lower() == 'video':
        return False
    return True


def onHoverStartGetAccept(comp, info):
    items = info.get('dragItems', [])
    if not items:
        return False
    layer, col = _resolve_drop_cell(comp)
    if layer is None:
        return False
    root = _root_from_cell(comp)
    logic = root.op('logic').module if root else None
    if _is_clip(items[0]):
        src = items[0]
        if src['layer'] == layer and src['col'] == col:
            return False
        if not _cell_accepts_file_drop(logic, layer, col, src.get('type')):
            return False
        return True
    clip_type, path, _reason = _first_file_clip(items)
    if clip_type is None:
        return False
    return _cell_accepts_file_drop(logic, layer, col, clip_type)


def onHoverEnd(comp, info):
    return


def onDropGetResults(comp, info):
    root = _root_from_cell(comp)
    logic = root.op('logic').module if root else None
    layer, col = _resolve_drop_cell(comp)
    items = info.get('dragItems', [])
    if logic is None or layer is None or col is None or not items:
        return {'droppedOn': comp}
    item = items[0]
    if _is_clip(item):
        if item['layer'] == layer and item['col'] == col:
            return {'droppedOn': comp}
        if not _cell_accepts_file_drop(logic, layer, col, item.get('type')):
            return {'droppedOn': comp}
        logic.move_cell(item['layer'], item['col'], layer, col)
        print('Cut (moved) clip -> row {} col {}'.format(layer, col))
        return {'droppedOn': comp, 'modified': comp}
    clip_type, path, reason = _first_file_clip(items)
    if not clip_type:
        print('Drop ignored:', reason or 'unsupported drag')
        return {'droppedOn': comp}
    if not _cell_accepts_file_drop(logic, layer, col, clip_type):
        print('Drop rejected: cannot place {} on row {} col {}'.format(
            clip_type, layer, col))
        return {'droppedOn': comp}
    logic.load_cell(layer, col, clip_type, path)
    print('Dropped', os.path.basename(path), '-> row', layer, 'col', col)
    return {'droppedOn': comp, 'modified': comp}
'''
