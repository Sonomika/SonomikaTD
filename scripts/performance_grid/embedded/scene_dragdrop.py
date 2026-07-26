SCENE_DRAGDROP = r'''# Drag scene buttons to reorder scenes.
SCENE_TAG = '__perf_scene__'


def _root_from_scene_btn(comp):
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


def _scene_index(comp):
    p = comp
    for _ in range(8):
        if p is None:
            break
        name = getattr(p, 'name', '')
        if name.startswith('scene_btn_'):
            try:
                return int(name.split('_')[2])
            except Exception:
                return None
        try:
            p = p.parent()
        except Exception:
            break
    return None


def _scene_item(scene_idx):
    return {SCENE_TAG: True, 'scene': int(scene_idx)}


def _is_scene(item):
    return isinstance(item, dict) and item.get(SCENE_TAG)


def onDragStartGetItems(comp, info):
    scene = _scene_index(comp)
    if scene is None:
        return []
    return [_scene_item(scene)]


def onHoverStartGetAccept(comp, info):
    items = info.get('dragItems', [])
    if not items or not _is_scene(items[0]):
        return False
    target = _scene_index(comp)
    if target is None:
        return False
    return int(items[0]['scene']) != int(target)


def onHoverEnd(comp, info):
    return


def onDropGetResults(comp, info):
    root = _root_from_scene_btn(comp)
    logic = root.op('logic').module if root else None
    target = _scene_index(comp)
    items = info.get('dragItems', [])
    if logic is None or target is None or not items or not _is_scene(items[0]):
        return {'droppedOn': comp}
    src = int(items[0]['scene'])
    if src == target:
        return {'droppedOn': comp}
    logic.move_scene(src, target)
    return {'droppedOn': comp, 'modified': comp}
'''
