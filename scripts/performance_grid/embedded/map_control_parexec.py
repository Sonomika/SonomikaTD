MAP_CONTROL_PAREXEC = r'''def _logic():
    r = parent()
    return r.op('logic').module if r else None


def _dial_index_from_par_name(name):
    name = str(name or '')
    if not name.startswith('Map'):
        return None
    # Longer suffixes first; Map*max must be checked before Map*min ('max'.endswith('min')).
    for suffix, tail_len in (('value', 5), ('bind', 4), ('max', 3), ('min', 3)):
        if name.endswith(suffix):
            try:
                return int(name[3:-tail_len])
            except Exception:
                return None
    return None


def _paint_dial(idx, light=False):
    logic = _logic()
    if logic is not None and hasattr(logic, '_paint_map_dial'):
        logic._paint_map_dial(idx, light=light)


def _sync_bind(par):
    logic = _logic()
    if logic is None:
        return
    idx = _dial_index_from_par_name(getattr(par, 'name', ''))
    if idx is None:
        return
    name = getattr(par, 'name', '')
    if name.endswith('value'):
        if hasattr(logic, 'map_dial_parexec_should_skip'):
            if logic.map_dial_parexec_should_skip(idx):
                return
        if hasattr(logic, 'sync_map_value_driver_from_par'):
            logic.sync_map_value_driver_from_par(idx)
        _paint_dial(idx, light=True)
    elif name.endswith('bind'):
        if hasattr(logic, 'sync_map_dial_bind_from_par'):
            logic.sync_map_dial_bind_from_par(idx)
    elif name.endswith('min') or name.endswith('max'):
        if hasattr(logic, 'on_map_dial_range_change'):
            logic.on_map_dial_range_change(idx)


def onValueChange(par, prev, *extra):
    _sync_bind(par)


def onModeChange(par, prev, *extra):
    _sync_bind(par)


def onExpressionChange(par, prev, *extra):
    _sync_bind(par)
'''
