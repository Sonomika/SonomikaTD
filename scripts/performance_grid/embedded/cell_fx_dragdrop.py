CELL_FX_DRAGDROP = r'''# Drop .tox on Cell tab; drag row headers to reorder cell FX.
import os
import tdu

CELL_FX_TAG = '__perf_cell_fx__'


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


def _selected_cell(root):
    try:
        layer = int(float(root.par.Selectedlayer.eval()))
        col = int(float(root.par.Selectedcol.eval()))
        return layer, col
    except Exception:
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
    path = path.replace('\\\\', '/')
    if os.name == 'nt' and len(path) > 2 and path[0] == '/' and path[2] == '/':
        path = path[1] + ':' + path[2:]
    return os.path.normpath(path).replace('\\\\', '/')


def _tox_path(items):
    for item in items or []:
        if isinstance(item, dict) and item.get(CELL_FX_TAG):
            continue
        path = None
        if isinstance(item, str):
            path = _normalize_drag_path(item)
        elif isinstance(item, tdu.FileInfo):
            try:
                path = _normalize_drag_path(str(item.path))
            except Exception:
                pass
        elif hasattr(item, 'path'):
            try:
                path = _normalize_drag_path(str(item.path))
            except Exception:
                pass
        if path and os.path.isfile(path) and path.lower().endswith('.tox'):
            return path
    return ''


def _fx_id_from_comp(comp):
    p = comp
    for _ in range(8):
        if p is None:
            break
        name = getattr(p, 'name', '')
        if name.startswith('lfx_row_hdr_'):
            sfx = name.replace('lfx_row_hdr_', '')
            if sfx == 'source':
                return 0
            try:
                return int(sfx)
            except Exception:
                return None
        if name.startswith('lfx_row_') and not name.startswith('lfx_row_hdr_'):
            sfx = name.replace('lfx_row_', '')
            if sfx == 'source':
                return 0
            try:
                return int(sfx)
            except Exception:
                return None
        try:
            p = p.parent()
        except Exception:
            break
    return None


def _fx_item(layer, col, fx_id):
    return {CELL_FX_TAG: True, 'layer': int(layer), 'col': int(col), 'id': int(fx_id)}


def _is_fx(item):
    return isinstance(item, dict) and item.get(CELL_FX_TAG)


def onDragStartGetItems(comp, info):
    if not getattr(comp, 'name', '').startswith('lfx_drag_'):
        return []
    root = _root_from_comp(comp)
    if root is None:
        return []
    layer, col = _selected_cell(root)
    fx_id = _fx_id_from_comp(comp)
    if layer is None or fx_id is None:
        return []
    return [_fx_item(layer, col, fx_id)]


def onHoverStartGetAccept(comp, info):
    items = info.get('dragItems', [])
    if not items:
        return False
    root = _root_from_comp(comp)
    if root is None:
        return False
    layer, col = _selected_cell(root)
    if layer is None:
        return False
    if _is_fx(items[0]):
        if int(items[0].get('layer', -1)) != layer or int(items[0].get('col', -1)) != col:
            return False
        target = _fx_id_from_comp(comp)
        if target is None:
            return getattr(comp, 'name', '') == 'layer_fx_panel'
        return int(items[0]['id']) != int(target)
    if not _tox_path(items):
        return False
    logic = root.op('logic').module if root else None
    if logic is not None and hasattr(logic, '_cell_accepts_tox_fx_drop'):
        return bool(logic._cell_accepts_tox_fx_drop(layer, col))
    ctype, src = logic.get_cell(layer, col) if logic is not None else ('', '')
    if src and str(ctype).strip().lower() != 'tox':
        return False
    return True


def onHoverEnd(comp, info):
    return


def onDropGetResults(comp, info):
    root = _root_from_comp(comp)
    logic = root.op('logic').module if root else None
    items = info.get('dragItems', [])
    if logic is None or root is None or not items:
        return {'droppedOn': comp}
    layer, col = _selected_cell(root)
    if layer is None:
        return {'droppedOn': comp}
    if _is_fx(items[0]):
        src = int(items[0]['id'])
        if int(items[0].get('layer', -1)) != layer or int(items[0].get('col', -1)) != col:
            return {'droppedOn': comp}
        target = _fx_id_from_comp(comp)
        if target is not None and src != target:
            if 0 in (src, target) and hasattr(logic, 'swap_cell_fx_with_source'):
                logic.swap_cell_fx_with_source(layer, col, target if src == 0 else src)
            elif hasattr(logic, 'move_cell_fx'):
                logic.move_cell_fx(layer, col, src, target)
            return {'droppedOn': comp, 'modified': comp}
        if target is None and getattr(comp, 'name', '') == 'layer_fx_panel':
            fx_list = logic._cell_fx_list(layer, col) if hasattr(logic, '_cell_fx_list') else []
            if fx_list and hasattr(logic, 'move_cell_fx'):
                logic.move_cell_fx(layer, col, src, fx_list[-1]['id'])
            return {'droppedOn': comp, 'modified': comp}
        return {'droppedOn': comp}
    path = _tox_path(items)
    if path and hasattr(logic, 'add_cell_fx'):
        if hasattr(logic, '_cell_accepts_tox_fx_drop'):
            if not logic._cell_accepts_tox_fx_drop(layer, col):
                return {'droppedOn': comp}
        else:
            ctype, src = logic.get_cell(layer, col)
            if src and str(ctype).strip().lower() != 'tox':
                return {'droppedOn': comp}
        logic.add_cell_fx(layer, col, path)
        return {'droppedOn': comp, 'modified': comp}
    return {'droppedOn': comp}
'''
