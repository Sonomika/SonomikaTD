MIDI_TABLE_EXEC = r'''# Watch midi_in table for incoming MIDI.

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


def onTableChange(dat, prevDAT=None, info=None):
    try:
        rows = int(dat.numRows)
        if rows < 1:
            return
        row = rows - 1

        def cell(r, names, col):
            for name in names:
                try:
                    return dat[r, name]
                except Exception:
                    pass
            try:
                return dat[r, col]
            except Exception:
                return ''

        message = cell(row, ('message',), 0)
        channel = cell(row, ('channel',), 2)
        index = cell(row, ('index',), 3)
        value = cell(row, ('value',), 4)
        mod = _perf_logic()
        if mod is not None and hasattr(mod, '_handle_midi_message'):
            mod._handle_midi_message(message, channel, index, value, None)
    except Exception as exc:
        print('MIDI table exec failed:', exc)
    return
'''
