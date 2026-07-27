"""Rebuild portable, aspect-safe Logo.tox with live custom controls."""
import os

ROOT = r'C:/Users/ridle/OneDrive/Documents Backup/1_Cursor/TouchDesigner/SonomikaTD'
IMAGE = ROOT + '/assets/sonomika_logo.png'
TARGETS = [ROOT + '/tox/Factory/logo.tox', ROOT + '/release/tox/logo.tox']
VFS_KEY = 'assets/sonomika_logo.png'
REPORT = ROOT + '/output/logo_tox_rebuild.txt'


def _expr(par, expression):
    par.expr = expression
    par.mode = type(par.mode).EXPRESSION


def _set_safe(node, name, value):
    try:
        getattr(node.par, name).val = value
    except Exception:
        pass


def _build(target, index):
    host = op('/project1')
    for old_name in ('__logo_build', '__logo_restore_0', '__logo_restore_1', '__logo_audit'):
        old = host.op(old_name)
        if old is not None:
            old.destroy()
    comp = host.create('baseCOMP', '__logo_build')

    page = comp.appendCustomPage('Logo')
    page.appendToggle('Enablelogo', label='Enable Logo')[0].val = True
    opacity = page.appendFloat('Logoopacity', label='Opacity')[0]
    opacity.normMin, opacity.normMax, opacity.clampMin, opacity.clampMax = 0, 1, True, True
    opacity.val = 1.0
    scale = page.appendFloat('Logoscale', label='Scale')[0]
    scale.normMin, scale.normMax, scale.clampMin = 0.01, 1.0, True
    scale.val = 0.25
    posx = page.appendFloat('Positionx', label='Position X')[0]
    posx.normMin, posx.normMax = -1, 1
    posx.val = 0
    posy = page.appendFloat('Positiony', label='Position Y')[0]
    posy.normMin, posy.normMax = -1, 1
    posy.val = 0
    image_par = page.appendFile('Imagefile', label='Image File')[0]

    comp.vfs.addFile(IMAGE, overrideName=VFS_KEY)
    _expr(image_par, "me.owner.vfs['{}'].virtualPath".format(VFS_KEY))

    source = comp.create('inTOP', 'select_video_in')
    logo_file = comp.create('moviefileinTOP', 'logo_file')
    _expr(logo_file.par.file, "parent().par.Imagefile")
    _set_safe(logo_file, 'outputresolution', 'default')

    fit = comp.create('fitTOP', 'logo_aspect_fit')
    _set_safe(fit, 'outputresolution', 'custom')
    _expr(
        fit.par.resolutionw,
        "op('/settings').par.Canvaswidth if op('/settings') and "
        "hasattr(op('/settings').par, 'Canvaswidth') else "
        "(op('select_video_in').width if op('select_video_in') and "
        "op('select_video_in').width > 16 else 1920)",
    )
    _expr(
        fit.par.resolutionh,
        "op('/settings').par.Canvasheight if op('/settings') and "
        "hasattr(op('/settings').par, 'Canvasheight') else "
        "(op('select_video_in').height if op('select_video_in') and "
        "op('select_video_in').height > 16 else 1080)",
    )
    _set_safe(fit, 'resmult', False)
    # Preserve the complete image aspect on the transparent output canvas.
    # logo_place then applies one uniform user-controlled scale.
    _set_safe(fit, 'fit', 'fitbest')
    _set_safe(fit, 'justifyh', 'center')
    _set_safe(fit, 'justifyv', 'center')
    _set_safe(fit, 'bgcolorr', 0)
    _set_safe(fit, 'bgcolorg', 0)
    _set_safe(fit, 'bgcolorb', 0)
    for name in ('bgalpha', 'bgcolora'):
        _set_safe(fit, name, 0)

    place = comp.create('transformTOP', 'logo_place')
    _set_safe(place, 'outputresolution', 'useinput')
    _set_safe(place, 'resmult', False)
    _set_safe(place, 'tunit', 'fraction')
    _expr(place.par.sx, 'parent().par.Logoscale')
    _expr(place.par.sy, 'parent().par.Logoscale')
    _expr(place.par.tx, 'parent().par.Positionx * 0.5')
    _expr(place.par.ty, 'parent().par.Positiony * 0.5')

    level = comp.create('levelTOP', 'logo_opacity')
    _expr(level.par.opacity, 'parent().par.Logoopacity * parent().par.Enablelogo')

    over = comp.create('compositeTOP', 'logo_over')
    _set_safe(over, 'operand', 'over')
    out = comp.create('outTOP', 'out1')

    logo_file.outputConnectors[0].connect(fit.inputConnectors[0])
    fit.outputConnectors[0].connect(place.inputConnectors[0])
    place.outputConnectors[0].connect(level.inputConnectors[0])
    source.outputConnectors[0].connect(over.inputConnectors[0])
    level.outputConnectors[0].connect(over.inputConnectors[1])
    over.outputConnectors[0].connect(out.inputConnectors[0])

    for i, node in enumerate((source, logo_file, fit, place, level, over, out)):
        node.nodeX = i * 150
        node.nodeY = 0

    logo_file.par.reloadpulse.pulse()
    comp.save(target)
    size = os.path.getsize(target)
    comp.destroy()
    return size


rows = [(target, _build(target, i)) for i, target in enumerate(TARGETS)]
with open(REPORT, 'w', encoding='utf-8') as out:
    for target, size in rows:
        out.write('{}\t{} bytes\n'.format(target, size))
print('Logo TOX rebuilt:', REPORT)
