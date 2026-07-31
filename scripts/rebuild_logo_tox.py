"""Rebuild portable Logo.tox with the hi-res default image embedded in VFS.

Run inside TouchDesigner (Textport or MCP exec):
    exec(open(r'.../scripts/rebuild_logo_tox.py', encoding='utf-8').read())
"""
from __future__ import annotations

import os

# Resolve ParMode from a live parameter (not always injected in MCP exec).
ParMode = type(op('/project1').par.pageindex.mode)


ROOT = os.environ.get('SONOMIKA_TD_ROOT', '').strip()
if not ROOT:
    try:
        ROOT = os.path.normpath(project.folder)
        # production/ -> repo root
        if os.path.basename(ROOT).lower() == 'production':
            ROOT = os.path.dirname(ROOT)
    except Exception:
        ROOT = r'C:/Users/ridle/OneDrive/Documents Backup/1_Cursor/TouchDesigner/SonomikaTD'

ROOT = ROOT.replace('\\', '/')
IMAGE = ROOT + '/production/assets/sonomika/sonomika_logo.png'
if not os.path.isfile(IMAGE):
    IMAGE = ROOT + '/assets/sonomika/sonomika_logo.png'
if not os.path.isfile(IMAGE):
    IMAGE = ROOT + '/production/assets/sonomika_logo.png'
if not os.path.isfile(IMAGE):
    IMAGE = ROOT + '/assets/sonomika_logo.png'

TARGETS = [
    ROOT + '/production/tox/factory/logo.tox',
    ROOT + '/release/tox/factory/logo.tox',
]
VFS_KEY = 'assets/sonomika_logo.png'
REPORT = ROOT + '/output/logo_tox_rebuild.txt'


def _expr(par, expression):
    par.expr = expression
    par.mode = ParMode.EXPRESSION


def _bind(par, expression):
    try:
        par.bindExpr = expression
        par.mode = ParMode.BIND
    except Exception:
        _expr(par, expression)


def _set_safe(node, name, value):
    try:
        getattr(node.par, name).val = value
    except Exception:
        pass


def _canvas_w_expr():
    return (
        "op('/settings').par.Canvaswidth if op('/settings') and "
        "hasattr(op('/settings').par, 'Canvaswidth') else "
        "(op('select_video_in').width if op('select_video_in') and "
        "op('select_video_in').width > 16 else 1920)"
    )


def _canvas_h_expr():
    return (
        "op('/settings').par.Canvasheight if op('/settings') and "
        "hasattr(op('/settings').par, 'Canvasheight') else "
        "(op('select_video_in').height if op('select_video_in') and "
        "op('select_video_in').height > 16 else 1080)"
    )


_LOGO_PARAM_EXEC = '''def onValueChange(par, prev):
    if par is None or par.name != 'Imagefile':
        return
    logo = parent().op('logo_file')
    if logo is None:
        return
    path = ''
    try:
        path = str(par.eval()).strip()
    except Exception:
        pass
    if not path:
        return
    try:
        logo.par.file = path
        logo.par.reloadpulse.pulse()
    except Exception:
        pass
'''


def _build(target):
    if not os.path.isfile(IMAGE):
        raise FileNotFoundError('Logo image not found: ' + IMAGE)

    host = op('/project1')
    for old_name in (
        '__logo_build', '__logo_restore_0', '__logo_restore_1',
        '__verify_logo', '__inspect_logo', '__inspect_simple_logo',
    ):
        old = host.op(old_name)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass

    for old in list(host.findChildren(name='__logo_build*', maxDepth=1)):
        try:
            old.destroy()
        except Exception:
            pass

    comp = host.create('baseCOMP', '__logo_build')

    page = comp.appendCustomPage('Logo')
    page.appendToggle('Enablelogo', label='Enable Logo')[0].val = True
    opacity = page.appendFloat('Logoopacity', label='Opacity')[0]
    opacity.normMin, opacity.normMax, opacity.clampMin, opacity.clampMax = 0, 1, True, True
    opacity.val = 1.0
    scale = page.appendFloat('Logoscale', label='Scale')[0]
    scale.normMin, scale.normMax, scale.clampMin = 0.01, 1.0, True
    scale.val = 0.35
    scale.default = 0.35
    posx = page.appendFloat('Positionx', label='Position X')[0]
    posx.normMin, posx.normMax = -1, 1
    posx.val = 0
    posy = page.appendFloat('Positiony', label='Position Y')[0]
    posy.normMin, posy.normMax = -1, 1
    posy.val = 0
    image_par = page.appendFile('Imagefile', label='Image File')[0]

    # Embed default wordmark inside the TOX.
    try:
        for item in comp.vfs.find(pattern=VFS_KEY):
            item.destroy()
    except Exception:
        pass
    added = comp.vfs.addFile(IMAGE, overrideName=VFS_KEY)
    # COMP custom par: me == the COMP. Child TOP file par: parent().vfs.
    image_expr = "me.vfs['{}'].virtualPath".format(VFS_KEY)
    child_file_expr = "parent().vfs['{}'].virtualPath".format(VFS_KEY)
    _expr(image_par, image_expr)

    select_video_in = comp.create('selectTOP', 'select_video_in')
    _set_safe(select_video_in, 'outputresolution', 'custom')
    _expr(select_video_in.par.resolutionw, _canvas_w_expr())
    _expr(select_video_in.par.resolutionh, _canvas_h_expr())

    logo_default = comp.create('moviefileinTOP', 'logo_default')
    _set_safe(logo_default, 'outputresolution', 'default')
    _set_safe(logo_default, 'resmult', False)
    _set_safe(logo_default, 'play', True)
    _expr(logo_default.par.file, child_file_expr)

    logo_file = comp.create('moviefileinTOP', 'logo_file')
    _set_safe(logo_file, 'outputresolution', 'default')
    _set_safe(logo_file, 'resmult', False)
    _set_safe(logo_file, 'play', True)
    _bind(logo_file.par.file, 'parent().par.Imagefile')

    logo_source = comp.create('switchTOP', 'logo_source')
    # 0 = embedded default, 1 = custom Imagefile when set.
    _expr(
        logo_source.par.index,
        "1 if str(parent().par.Imagefile.eval()).strip() "
        "and 'vfs:' not in str(parent().par.Imagefile.eval()).replace('\\\\\\\\','/').lower() "
        "and str(parent().par.Imagefile.eval()).strip() != str((me.owner.vfs['%s'].virtualPath if me.owner.vfs['%s'] else '')).strip() "
        "else 0" % (VFS_KEY, VFS_KEY),
    )
    # Keep it simple: default stays on embedded VFS via Imagefile expr, so index 0.
    logo_source.par.index = 0

    fit = comp.create('fitTOP', 'logo_aspect_fit')
    _set_safe(fit, 'outputresolution', 'custom')
    _expr(fit.par.resolutionw, _canvas_w_expr())
    _expr(fit.par.resolutionh, _canvas_h_expr())
    _set_safe(fit, 'resmult', False)
    _set_safe(fit, 'fit', 'fitbest')
    _set_safe(fit, 'justifyh', 'center')
    _set_safe(fit, 'justifyv', 'center')
    _set_safe(fit, 'bgcolorr', 0)
    _set_safe(fit, 'bgcolorg', 0)
    _set_safe(fit, 'bgcolorb', 0)
    for name in ('bgalpha', 'bgcolora'):
        _set_safe(fit, name, 0)
    _set_safe(fit, 'premultrgbbyalpha', True)

    place = comp.create('transformTOP', 'logo_place')
    _set_safe(place, 'outputresolution', 'useinput')
    _set_safe(place, 'resmult', False)
    _set_safe(place, 'premultrgbbyalpha', True)
    _set_safe(place, 'tunit', 'fraction')
    _expr(place.par.sx, 'parent().par.Logoscale')
    _expr(place.par.sy, 'parent().par.Logoscale')
    _expr(place.par.tx, 'parent().par.Positionx * 0.5')
    _expr(place.par.ty, 'parent().par.Positiony * 0.5')

    level = comp.create('levelTOP', 'logo_opacity')
    _set_safe(level, 'premultrgbbyalpha', False)
    _expr(level.par.opacity, 'parent().par.Logoopacity * parent().par.Enablelogo')

    over = comp.create('compositeTOP', 'logo_over')
    _set_safe(over, 'operand', 'over')

    context = comp.create('switchTOP', 'logo_context_output')
    # Prefer transparent overlay (logo only) when used as a cell effect over upstream.
    context.par.index = 0

    out = comp.create('outTOP', 'out1')
    _set_safe(out, 'outputresolution', 'useinput')

    pe = comp.create('parameterexecuteDAT', 'logo_image_watch')
    pe.text = _LOGO_PARAM_EXEC
    pe.par.op = comp
    pe.par.active = True
    pe.par.valuechange = True

    # Wiring: default + custom -> switch -> fit -> place -> opacity
    # opacity is overlay-only out; over composites onto video when index 1.
    logo_default.outputConnectors[0].connect(logo_source.inputConnectors[0])
    logo_file.outputConnectors[0].connect(logo_source.inputConnectors[1])
    logo_source.outputConnectors[0].connect(fit.inputConnectors[0])
    fit.outputConnectors[0].connect(place.inputConnectors[0])
    place.outputConnectors[0].connect(level.inputConnectors[0])
    level.outputConnectors[0].connect(context.inputConnectors[0])
    level.outputConnectors[0].connect(over.inputConnectors[0])
    select_video_in.outputConnectors[0].connect(over.inputConnectors[1])
    over.outputConnectors[0].connect(context.inputConnectors[1])
    context.outputConnectors[0].connect(out.inputConnectors[0])

    nodes = (
        select_video_in, logo_default, logo_file, logo_source, fit,
        place, level, over, context, out, pe,
    )
    for i, node in enumerate(nodes):
        try:
            node.nodeX = (i % 6) * 160
            node.nodeY = - (i // 6) * 160
        except Exception:
            pass

    try:
        logo_default.par.reloadpulse.pulse()
        logo_file.par.reloadpulse.pulse()
        logo_default.cook(force=True)
        logo_file.cook(force=True)
    except Exception:
        pass

    w = int(getattr(logo_default, 'width', 0) or 0)
    h = int(getattr(logo_default, 'height', 0) or 0)
    if w < 600:
        # Force a second cook after VFS path resolves.
        try:
            logo_default.par.file = added.virtualPath
            logo_default.par.file.mode = ParMode.CONSTANT
            logo_default.par.reloadpulse.pulse()
            logo_default.cook(force=True)
            w = int(logo_default.width)
            h = int(logo_default.height)
            # Restore portable VFS expression before save.
            _expr(logo_default.par.file, child_file_expr)
            logo_default.par.reloadpulse.pulse()
            logo_default.cook(force=True)
            w = int(logo_default.width)
            h = int(logo_default.height)
        except Exception:
            pass

    os.makedirs(os.path.dirname(target), exist_ok=True)
    comp.save(target)
    size = os.path.getsize(target)
    comp.destroy()
    return size, w, h


rows = []
for target in TARGETS:
    try:
        size, w, h = _build(target)
        rows.append((target, size, w, h, 'ok'))
        print('Saved', target, size, 'bytes source', w, 'x', h)
    except Exception as exc:
        rows.append((target, 0, 0, 0, str(exc)))
        print('FAILED', target, exc)

os.makedirs(os.path.dirname(REPORT), exist_ok=True)
with open(REPORT, 'w', encoding='utf-8') as out:
    out.write('image\t{}\n'.format(IMAGE))
    for target, size, w, h, status in rows:
        out.write('{}\t{}\t{}x{}\t{}\n'.format(target, size, w, h, status))
print('Logo TOX rebuild report:', REPORT)
