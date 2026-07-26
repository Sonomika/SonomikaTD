MIDI_CALLBACKS = r'''# MIDI callbacks for Sonomika performance grid (v2).

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


def onReceiveMIDI(dat, rowIndex, message, channel, index, value, input, bytes, *args):
    try:
        mod = _perf_logic()
        if mod is not None and hasattr(mod, '_handle_midi_message'):
            mod._handle_midi_message(message, channel, index, value, input)
    except Exception as exc:
        print('MIDI mapping failed:', exc)
    return
'''
