"""Repair every currently loaded Logo effect without reloading the project."""

fixed = []
for node in op('/').findChildren():
    logo_file = node.op('logo_file')
    logo_fit = node.op('logo_aspect_fit')
    logo_place = node.op('logo_place')
    if logo_file is None or logo_fit is None or logo_place is None:
        continue

    logo_fit.par.outputresolution = 'custom'
    logo_fit.par.fit = 'fitbest'
    logo_fit.par.resolutionw.expr = (
        "op('/settings').par.Canvaswidth if op('/settings') and "
        "hasattr(op('/settings').par, 'Canvaswidth') else "
        "(op('select_video_in').width if op('select_video_in') "
        "and op('select_video_in').width > 16 else 1920)"
    )
    logo_fit.par.resolutionh.expr = (
        "op('/settings').par.Canvasheight if op('/settings') and "
        "hasattr(op('/settings').par, 'Canvasheight') else "
        "(op('select_video_in').height if op('select_video_in') "
        "and op('select_video_in').height > 16 else 1080)"
    )
    logo_fit.par.resolutionw.mode = type(logo_fit.par.resolutionw.mode).EXPRESSION
    logo_fit.par.resolutionh.mode = type(logo_fit.par.resolutionh.mode).EXPRESSION
    logo_place.par.outputresolution = 'useinput'

    bindings = {
        'sx': 'parent().par.Logoscale',
        'sy': 'parent().par.Logoscale',
    }
    for name, expression in bindings.items():
        par = logo_place.par[name]
        par.expr = expression
        par.mode = type(par.mode).EXPRESSION

    try:
        logo_file.par.reloadpulse.pulse()
    except Exception:
        pass
    fixed.append(node.path)

print('Logo aspect repaired:', len(fixed), 'loaded instance(s)')
for path in fixed:
    print(' ', path)
