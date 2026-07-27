"""Build a portable Logo TOX with a locked default image and file override."""

ROOT = r'C:/Users/ridle/OneDrive/Documents Backup/1_Cursor/TouchDesigner/SonomikaTD'
IMAGE = ROOT + '/assets/sonomika_logo.png'
TARGETS = (
    ROOT + '/tox/Factory/logo.tox',
    ROOT + '/release/tox/logo.tox',
)


def _disconnect_input(node, index=0):
    for connection in list(node.inputConnectors[index].connections):
        connection.disconnect()


def _repair(target, index):
    host = op('/project1').create('baseCOMP', '__logo_locked_{}'.format(index))
    host.allowCooking = False
    logo = host.loadTox(target)
    logo.allowCooking = False

    # Remove failed scripted/VFS fallback implementations.
    for name in (
        'logo_default', 'logo_default_callbacks', 'logo_image_watch',
        'logo_image_startup',
    ):
        node = logo.op(name)
        if node is not None:
            node.destroy()
    for item in list(logo.vfs.find(pattern='*')):
        item.destroy()

    image_par = logo.par.Imagefile
    image_par.mode = 0
    image_par.val = ''
    image_par.default = ''
    image_par.label = 'Image File (optional)'

    # Cook the bundled wordmark once and lock its pixels into the TOX.
    default_top = logo.create('moviefileinTOP', 'logo_default')
    default_top.par.file.mode = 0
    default_top.par.file.val = IMAGE
    host.allowCooking = True
    logo.allowCooking = True
    default_top.par.reloadpulse.pulse()
    default_top.cook(force=True)
    if default_top.width != 300 or default_top.height != 52:
        raise RuntimeError(
            'Default logo failed to load: {}x{} {}'.format(
                default_top.width, default_top.height, default_top.errors()))
    default_top.lock = True
    # The locked TOP retains pixels; clear the development-machine path.
    default_top.par.file.val = ''

    override = logo.op('logo_file')
    override.par.file.expr = 'parent().par.Imagefile'
    override.par.file.mode = 1

    source_switch = logo.op('logo_source')
    if source_switch is None:
        source_switch = logo.create('switchTOP', 'logo_source')
    for connector in source_switch.inputConnectors:
        for connection in list(connector.connections):
            connection.disconnect()
    default_top.outputConnectors[0].connect(source_switch.inputConnectors[0])
    override.outputConnectors[0].connect(source_switch.inputConnectors[1])
    source_switch.par.index.expr = (
        "1 if str(parent().par.Imagefile.eval()).strip() else 0"
    )
    source_switch.par.index.mode = 1

    fit = logo.op('logo_aspect_fit')
    _disconnect_input(fit)
    source_switch.outputConnectors[0].connect(fit.inputConnectors[0])

    # Reload only the optional replacement when its field changes.
    watcher = logo.create('parameterexecuteDAT', 'logo_image_watch')
    watcher.par.op = logo
    watcher.par.pars = 'Imagefile'
    watcher.par.valuechange = True
    watcher.par.onpulse = False
    watcher.par.active = True
    watcher.text = """def onValueChange(par, prev):
    movie = parent().op('logo_file')
    if movie is not None and str(par.eval()).strip():
        run("args[0].par.reloadpulse.pulse()", movie, delayFrames=1)
    return
"""

    logo.save(target)
    host.destroy()


for _index, _target in enumerate(TARGETS):
    _repair(_target, _index)

_verify_host = op('/project1').create('baseCOMP', '__logo_locked_verify')
_background = _verify_host.create('constantTOP', 'background')
_background.par.outputresolution = 'custom'
_background.par.resolutionw = 640
_background.par.resolutionh = 360
_background.par.colorr = 0.08
_background.par.colorg = 0.08
_background.par.colorb = 0.08
_verified_logo = _verify_host.loadTox(TARGETS[0])
_background.outputConnectors[0].connect(_verified_logo.inputConnectors[0])
_verified_logo.op('out1').cook(force=True)
_verified_logo.op('out1').save(ROOT + '/tmp/logo_locked_render.png')
_verify_host.destroy()

print('Locked default Sonomika logo saved in Factory and release TOX files.')
