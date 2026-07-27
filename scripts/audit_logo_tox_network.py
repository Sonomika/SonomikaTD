"""Report Logo.tox network structure and custom parameter bindings."""
import os

ROOT = r'C:/Users/ridle/OneDrive/Documents Backup/1_Cursor/TouchDesigner/SonomikaTD'
TARGET = ROOT + '/release/tox/logo.tox'
REPORT = ROOT + '/output/logo_tox_network.txt'

host = op('/project1')
wrapper = host.create('baseCOMP', '__logo_audit')
wrapper.loadTox(TARGET)
comps = [node for node in wrapper.children if getattr(node, 'isCOMP', False)]
actual = comps[0] if len(comps) == 1 else wrapper

with open(REPORT, 'w', encoding='utf-8') as out:
    out.write('ROOT {}\n'.format(actual.path))
    out.write('CUSTOM PARAMETERS\n')
    for page in actual.customPages:
        for par in page.pars:
            out.write('{}\t{}\t{}\t{}\t{}\n'.format(
                page.name, par.name, par.eval(), par.expr, getattr(par, 'bindExpr', ''),
            ))
    out.write('\nOPERATORS\n')
    for node in [actual] + list(actual.findChildren(maxDepth=5)):
        out.write('{}\t{}\n'.format(node.path, getattr(node, 'OPType', '')))
        for par in node.pars():
            expr = str(getattr(par, 'expr', '') or '').strip()
            bind = str(getattr(par, 'bindExpr', '') or '').strip()
            if expr or bind or par.name in (
                'file', 'top', 'opacity', 'sx', 'sy', 'tx', 'ty',
                'outputresolution', 'resolutionw', 'resolutionh', 'fit',
            ):
                try:
                    val = par.eval()
                except Exception:
                    val = ''
                out.write('  {}\t{}\texpr={}\tbind={}\n'.format(par.name, val, expr, bind))
        try:
            inputs = [conn.owner.path for conn in node.inputConnectors[0].connections]
            if inputs:
                out.write('  INPUT {}\n'.format(', '.join(inputs)))
        except Exception:
            pass

wrapper.destroy()
print('Logo TOX audit ->', REPORT)
