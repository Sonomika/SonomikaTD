GLOBAL_FX_DRAGDROP = r'''# Drag .tox onto Global tab; drag row headers to reorder.
import os
import tdu

GLOBAL_FX_TAG = '__perf_global_fx__'


def _root_from_comp(comp):
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
    path = path.replace('\\\\', '/')
    if os.name == 'nt' and len(path) > 2 and path[0] == '/' and path[2] == '/':
        path = path[1] + ':' + path[2:]
    return os.path.normpath(path).replace('\\\\', '/')


def _path_from_item(item):
    if isinstance(item, dict) and item.get(GLOBAL_FX_TAG):
        return None
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


def _tox_path(items):
    for item in items or []:
        if isinstance(item, dict) and item.get(GLOBAL_FX_TAG):
            continue
        path = _path_from_item(item)
        if path and os.path.isfile(path) and path.lower().endswith('.tox'):
            return path
    return ''


def _fx_id_from_comp(comp):
    p = comp
    for _ in range(8):
        if p is None:
            break
        name = getattr(p, 'name', '')
        if name.startswith('gfx_row_hdr_'):
            try:
                return int(name.split('_')[-1])
            except Exception:
                return None
        if name.startswith('gfx_row_'):
            try:
                return int(name.split('_')[-1])
            except Exception:
                return None
        try:
            p = p.parent()
        except Exception:
            break
    return None


def _fx_item(fx_id):
    return {GLOBAL_FX_TAG: True, 'id': int(fx_id)}


def _is_fx(item):
    return isinstance(item, dict) and item.get(GLOBAL_FX_TAG)


def onDragStartGetItems(comp, info):
    if not getattr(comp, 'name', '').startswith('gfx_drag_'):
        return []
    fx_id = _fx_id_from_comp(comp)
    if fx_id is None:
        return []
    return [_fx_item(fx_id)]


def onHoverStartGetAccept(comp, info):
    items = info.get('dragItems', [])
    if not items:
        return False
    if _is_fx(items[0]):
        target = _fx_id_from_comp(comp)
        if target is None:
            name = getattr(comp, 'name', '')
            return name == 'global_fx_panel'
        return int(items[0]['id']) != int(target)
    return bool(_tox_path(items))


def onHoverEnd(comp, info):
    return


def onDropGetResults(comp, info):
    root = _root_from_comp(comp)
    logic = root.op('logic').module if root else None
    items = info.get('dragItems', [])
    if logic is None or not items:
        return {'droppedOn': comp}
    if _is_fx(items[0]):
        src = int(items[0]['id'])
        target = _fx_id_from_comp(comp)
        if target is None and getattr(comp, 'name', '') == 'global_fx_panel':
            if hasattr(logic, 'move_global_fx'):
                logic.move_global_fx(src, logic._GLOBAL_FX[-1]['id'] if logic._GLOBAL_FX else src)
            return {'droppedOn': comp, 'modified': comp}
        if target is not None and src != target and hasattr(logic, 'move_global_fx'):
            logic.move_global_fx(src, target)
            return {'droppedOn': comp, 'modified': comp}
        return {'droppedOn': comp}
    path = _tox_path(items)
    if path and hasattr(logic, 'add_global_fx'):
        logic.add_global_fx(path)
        return {'droppedOn': comp, 'modified': comp}
    return {'droppedOn': comp}
'''
