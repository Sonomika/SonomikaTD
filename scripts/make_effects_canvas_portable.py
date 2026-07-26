# Run inside TouchDesigner (MCP execute_python_script or Textport).
# Makes effect_library TOX exports resolution-independent.
#
# Each effect gets Canvaswidth / Canvasheight custom parameters (default 1080 x 1920).
# Full-frame TOPs inside the effect bind to parent().par.Canvaswidth/height.
#
# Run before export_effect_tox():
#   make_effects_canvas_portable()
#   export_effect_tox()

CANVAS_W_EXPR = 'parent().par.Canvaswidth'
CANVAS_H_EXPR = 'parent().par.Canvasheight'

SUPPORT_NODES = {'effect_catalog', 'library_parexec', 'readme'}
SKIP_NAME_PARTS = {
    'downsample', 'analysis', 'thumbnail', 'moviefilein', 'info',
}


def _library():
    return op('/project1/effect_library')


def _ensure_canvas_pars(comp, w=1080, h=1920):
    page = None
    for pg in comp.customPages:
        if pg.name == 'Canvas':
            page = pg
            break
    if page is None:
        page = comp.appendCustomPage('Canvas')

    if getattr(comp.par, 'Canvaswidth', None) is None:
        p = page.appendInt('Canvaswidth', label='Canvas Width')
        try:
            p.default = w
            p.normMin = 16
            p.normMax = 7680
        except Exception:
            pass
    if getattr(comp.par, 'Canvasheight', None) is None:
        p = page.appendInt('Canvasheight', label='Canvas Height')
        try:
            p.default = h
            p.normMin = 16
            p.normMax = 4320
        except Exception:
            pass

    try:
        if not str(comp.par.Canvaswidth.expr).strip():
            comp.par.Canvaswidth = w
        if not str(comp.par.Canvasheight.expr).strip():
            comp.par.Canvasheight = h
    except Exception:
        pass


def _should_bind_top(top):
    if top is None or not top.isTOP:
        return False
    low = top.name.lower()
    if any(part in low for part in SKIP_NAME_PARTS):
        return False
    if not (hasattr(top.par, 'resolutionw') and hasattr(top.par, 'resolutionh')):
        return False
    try:
        if top.par.outputresolution.eval() not in ('custom', 'useinput', '9'):
            return False
    except Exception:
        pass
    try:
        w = int(top.par.resolutionw.eval())
        h = int(top.par.resolutionh.eval())
    except Exception:
        return False
    # Full-frame or near canvas outputs — skip tiny utility tops.
    return w >= 480 and h >= 480


def _bind_top_to_parent_canvas(top):
    try:
        top.par.outputresolution = 'custom'
        top.par.resolutionw.expr = CANVAS_W_EXPR
        top.par.resolutionh.expr = CANVAS_H_EXPR
        return True
    except Exception:
        return False


def make_effects_canvas_portable(comp=None):
    lib = _library()
    if lib is None:
        raise RuntimeError('Missing /project1/effect_library')

    settings = op('/project1/settings')
    w, h = 1080, 1920
    if settings is not None:
        try:
            w = int(settings.par.Canvaswidth.eval())
            h = int(settings.par.Canvasheight.eval())
        except Exception:
            pass

    targets = [comp] if comp is not None else [
        c for c in lib.children if c.isCOMP and c.name not in SUPPORT_NODES
    ]

    bound = 0
    for effect in targets:
        if effect is None:
            continue
        _ensure_canvas_pars(effect, w, h)
        for top in effect.findChildren(depth=1):
            if not top.isTOP:
                continue
            if _should_bind_top(top):
                if _bind_top_to_parent_canvas(top):
                    bound += 1

    print('Canvas portable bind: {} TOPs across {} effect(s)'.format(bound, len(targets)))
    return bound


def sync_library_canvas_from_settings():
    settings = op('/project1/settings')
    lib = _library()
    if settings is None or lib is None:
        return
    try:
        w = int(settings.par.Canvaswidth.eval())
        h = int(settings.par.Canvasheight.eval())
    except Exception:
        return
    for comp in lib.children:
        if not comp.isCOMP or comp.name in SUPPORT_NODES:
            continue
        if getattr(comp.par, 'Canvaswidth', None) is None:
            continue
        try:
            comp.par.Canvaswidth = w
            comp.par.Canvasheight = h
        except Exception:
            pass


def main():
    make_effects_canvas_portable()
    sync_library_canvas_from_settings()
    return True


if __name__ == '__main__':
    main()
