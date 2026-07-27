"""Estimate serialized OP storage values that can inflate a .toe."""
import os
import pickle

REPORT = os.path.join(project.folder, 'output', 'storage_size_audit.txt').replace('\\', '/')
nodes = [op('/')]
nodes.extend(op('/').findChildren(maxDepth=99))
rows = []
for node in nodes:
    try:
        values = node.storage
    except Exception:
        continue
    for key, value in values.items():
        try:
            size = len(pickle.dumps(value, protocol=4))
        except Exception:
            try:
                size = len(repr(value).encode('utf-8'))
            except Exception:
                size = 0
        if size:
            rows.append((size, node.path, str(key)))

with open(REPORT, 'w', encoding='utf-8') as out:
    for size, path, key in sorted(rows, reverse=True):
        out.write('{:.3f} MB\t{}\t{}\n'.format(size / 1048576.0, path, key))

print('Storage size audit ->', REPORT)
