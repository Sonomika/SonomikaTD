"""Report large DAT contents and locked operator estimates in the open project."""
import os

REPORT = os.path.join(project.folder, 'output', 'dat_size_audit.txt').replace('\\', '/')
nodes = [op('/')]
nodes.extend(op('/').findChildren(maxDepth=99))

dats = []
locked = []
for node in nodes:
    try:
        text = node.text
        size = len(text.encode('utf-8'))
        if size:
            dats.append((size, node.path))
    except Exception:
        pass
    try:
        if node.lock:
            estimate = 0
            try:
                estimate = int(node.width) * int(node.height) * 4
            except Exception:
                pass
            locked.append((estimate, node.path))
    except Exception:
        pass

with open(REPORT, 'w', encoding='utf-8') as out:
    out.write('DAT TEXT\n')
    for size, path in sorted(dats, reverse=True):
        out.write('{:.3f} MB\t{}\n'.format(size / 1048576.0, path))
    out.write('\nLOCKED OP ESTIMATES\n')
    for size, path in sorted(locked, reverse=True):
        out.write('{:.3f} MB\t{}\n'.format(size / 1048576.0, path))

print('DAT size audit ->', REPORT)
