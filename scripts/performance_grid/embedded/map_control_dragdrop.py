MAP_CONTROL_DRAGDROP = r'''# Legacy fallback: drop a parameter onto a Map Controller bind box.
import tdu


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


def _dial_index_from_comp(comp):
    p = comp
    for _ in range(8):
        if p is None:
            break
        name = getattr(p, 'name', '')
        if name.startswith('map_dial_'):
            token = name.replace('map_dial_', '')
            if token.endswith('_bind_name'):
                token = token[:-10]
            elif token.endswith('_bind_value'):
                token = token[:-11]
            elif token.endswith('_bind_label'):
                token = token[:-11]
            elif token.endswith('_bind'):
                token = token[:-5]
            if token.endswith('_knob'):
                token = token[:-5]
            if token.isdigit():
                return int(token)
        try:
            p = p.parent()
        except Exception:
            break
    return None


def _par_from_item(item):
    if item is None:
        return None
    try:
        if isinstance(item, Par):
            return item
    except NameError:
        pass
    if hasattr(item, 'owner') and hasattr(item, 'name') and hasattr(item, 'eval'):
        try:
            if item.owner is not None:
                return item
        except Exception:
            pass
    if isinstance(item, str):
        text = item.strip()
        if '.par.' in text and "op('" in text:
            try:
                return eval(text, {'op': op})
            except Exception:
                pass
        if text.startswith('par:') or text.startswith('param:'):
            root = op('/project1/performance_mode')
            logic = root.op('logic').module if root else None
            if logic is not None and hasattr(logic, '_resolve_cell_par_bind'):
                return logic._resolve_cell_par_bind(text)
    return None


def onDragStartGetItems(comp, info):
    return []


def onHoverStartGetAccept(comp, info):
    items = info.get('dragItems', [])
    if not items:
        return False
    return _par_from_item(items[0]) is not None


def onHoverEnd(comp, info):
    return


def onDropGetResults(comp, info):
    root = _root_from_comp(comp)
    logic = root.op('logic').module if root else None
    items = info.get('dragItems', [])
    if logic is None or not items:
        return {'droppedOn': comp}
    idx = _dial_index_from_comp(comp)
    if idx is None:
        return {'droppedOn': comp}
    par = _par_from_item(items[0])
    if par is None:
        return {'droppedOn': comp}
    if hasattr(logic, 'bind_map_dial'):
        logic.bind_map_dial(idx, par)
        if hasattr(logic, '_paint_map_dial'):
            logic._paint_map_dial(idx)
        return {'droppedOn': comp, 'modified': comp}
    return {'droppedOn': comp}
'''
