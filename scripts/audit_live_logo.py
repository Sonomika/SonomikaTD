"""Write the dimensions and scaling state of loaded Logo effects."""

import os

report_path = r'C:/Users/ridle/OneDrive/Documents Backup/1_Cursor/TouchDesigner/SonomikaTD/output/live_logo_audit.txt'
lines = []

for node in op('/').findChildren():
    logo_file = node.op('logo_file')
    logo_fit = node.op('logo_aspect_fit')
    logo_place = node.op('logo_place')
    if logo_file is None or logo_place is None:
        continue

    lines.append('COMP ' + node.path)
    for child in (logo_file, logo_fit, logo_place, node.op('out1')):
        if child is None:
            continue
        lines.append(
            '  {} {}x{} aspect={:.6f}'.format(
                child.name,
                child.width,
                child.height,
                child.width / max(1, child.height),
            )
        )
    for name in ('Logoscale', 'Logowidth', 'Logoheight', 'Imagefile'):
        if hasattr(node.par, name):
            p = node.par[name]
            lines.append(
                '  par {} val={!r} expr={!r} mode={!s}'.format(
                    name, p.eval(), p.expr, p.mode
                )
            )
    for name in ('sx', 'sy', 'outputresolution', 'resolutionw', 'resolutionh', 'fit'):
        if hasattr(logo_place.par, name):
            p = logo_place.par[name]
            lines.append(
                '  logo_place.{} val={!r} expr={!r} mode={!s}'.format(
                    name, p.eval(), p.expr, p.mode
                )
            )
    if logo_fit is not None:
        for name in ('fit', 'outputresolution', 'resolutionw', 'resolutionh'):
            if hasattr(logo_fit.par, name):
                p = logo_fit.par[name]
                lines.append(
                    '  logo_fit.{} val={!r} expr={!r} mode={!s}'.format(
                        name, p.eval(), p.expr, p.mode
                    )
                )

os.makedirs(os.path.dirname(report_path), exist_ok=True)
with open(report_path, 'w', encoding='utf-8') as report:
    report.write('\n'.join(lines) if lines else 'NO LOADED LOGO EFFECT FOUND')

print('Live logo audit:', report_path)
