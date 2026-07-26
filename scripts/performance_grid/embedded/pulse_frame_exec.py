PULSE_FRAME_EXEC = r'''# BPM pulse engine — frame tick on /settings.

def _logic_module():
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


def onFrameStart(frame):
    mod = _logic_module()
    if mod is None:
        return
    if hasattr(mod, 'update_pulse_engine'):
        mod.update_pulse_engine(int(frame))
    return
'''
