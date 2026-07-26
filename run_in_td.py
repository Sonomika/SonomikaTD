# SonomikaTD — TouchDesigner bootstrap
# Run from TD Textport (use your actual path):
#   exec(open(r'C:/path/to/SonomikaTD/run_in_td.py').read())

import os

# Folder containing this file; override with SONOMIKA_TD_ROOT env if needed.
SONOMIKA_ROOT = os.path.dirname(os.path.abspath(__file__))

os.environ['SONOMIKA_TD_ROOT'] = SONOMIKA_ROOT.replace('\\', '/')
_script = os.path.join(SONOMIKA_ROOT, 'scripts', 'build_simple_grid.py').replace('\\', '/')
exec(open(_script, encoding='utf-8').read())

print('SonomikaTD loaded from', SONOMIKA_ROOT)
print('  build_simple_grid(open_perform=True)')
print('  repair_performance_drops()  # once, if auto-reload did not run')
print('  reload_performance_scripts()  # after editing .py files')
