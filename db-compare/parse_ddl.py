"""Doc file DDL Oracle (export tu SQL Developer) -> JSON {TABLE: [[COL, TYPE], ...]}.

Dung: python parse_ddl.py <file.sql> <out.json>
"""
import json
import re
import sys

CREATE_RE = re.compile(r'CREATE\s+TABLE\s+(?:"[^"]+"\.)?"([^"]+)"', re.I)
COL_RE = re.compile(r'^\s*(?:\(\s*)?"([^"]+)"\s+([A-Z0-9_]+(?:\s*\([^)]*\))?)', re.I)


def parse(path):
    tables = {}
    cur = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = CREATE_RE.search(line)
            if m:
                cur = m.group(1).upper()
                tables[cur] = []
                continue
            if cur is None:
                continue
            if re.search(r'^\s*\)\s|SEGMENT CREATION|^\s*\)\s*$|DEFAULT COLLATION', line) and not COL_RE.match(line):
                cur = None
                continue
            m = COL_RE.match(line)
            if m:
                tables[cur].append([m.group(1).upper(), m.group(2).upper()])
    return tables


if __name__ == "__main__":
    data = parse(sys.argv[1])
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"{len(data)} tables -> {sys.argv[2]}")
