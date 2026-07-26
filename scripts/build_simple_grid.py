# Run inside TouchDesigner:
#   exec(open(r'.../SonomikaTD/scripts/build_simple_grid.py', encoding='utf-8').read())
#   build_simple_grid(open_perform=True)
#
# Implementation lives in performance_grid/ (modular package).

import os
import sys

try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _HERE = None

if _HERE is None:
    try:
        from performance_grid.td_runtime import discover_scripts_dir

        _HERE = discover_scripts_dir()
    except Exception:
        _HERE = None

if _HERE and _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from performance_grid.entry import *  # noqa: F401,F403

try:
    from performance_grid.td_runtime import inject_td_op_into_performance_grid

    inject_td_op_into_performance_grid()
except Exception:
    # Outside TouchDesigner there is no global op(); importing this wrapper should still work.
    pass
