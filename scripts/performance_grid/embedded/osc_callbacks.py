OSC_CALLBACKS = r'''# OSC callbacks for Sonomika performance grid.

def _perf_logic():
    pm = op('/project1/performance_mode')
    if pm is None:
        try:
            pm = op('/performance_mode')
        except Exception:
            pm = None
    if pm is None:
        return None
    logic = pm.op('logic')
    if logic is None or not hasattr(logic, 'module'):
        return None
    return logic.module


def onReceiveOSC(dat, rowIndex, message, bytes, timeStamp, address, args, peer):
    try:
        mod = _perf_logic()
        if mod is not None and hasattr(mod, '_handle_osc_message'):
            mod._handle_osc_message(str(address), list(args))
    except Exception as exc:
        print('OSC mapping failed:', exc)
    return
'''
