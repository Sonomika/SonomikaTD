"""Export performance_mode branches to estimate serialized size contributors."""
import os

OUT = os.path.join(project.folder, 'output', 'performance_mode_size').replace('\\', '/')
REPORT = os.path.join(project.folder, 'output', 'performance_mode_size.txt').replace('\\', '/')
os.makedirs(OUT, exist_ok=True)


def safe_name(path):
    return path.strip('/').replace('/', '__') + '.tox'


targets = []
pm = op('/project1/performance_mode')
if pm is not None:
    targets.extend([node for node in pm.children if getattr(node, 'isCOMP', False)])
slots = op('/project1/performance_mode/slots')
if slots is not None:
    for layer in slots.children:
        if getattr(layer, 'isCOMP', False):
            targets.append(layer)
            for slot in layer.children:
                if getattr(slot, 'isCOMP', False):
                    targets.append(slot)

rows = []
seen = set()
for node in targets:
    if node.path in seen:
        continue
    seen.add(node.path)
    path = os.path.join(OUT, safe_name(node.path)).replace('\\', '/')
    try:
        node.save(path)
        rows.append((os.path.getsize(path), node.path))
    except Exception as exc:
        rows.append((-1, node.path + ' ERROR ' + str(exc)))

rows.sort(reverse=True)
with open(REPORT, 'w', encoding='utf-8') as out:
    for size, path in rows:
        out.write('{:.3f} MB\t{}\n'.format(size / 1048576.0, path))

print('Performance mode size audit ->', REPORT)
