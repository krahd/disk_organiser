"""Synchronise the read-only viewer's bundled contract/example from repo sources.

Only repository-owned synthetic assets are read or written. No scanner is called.
Run with --write after an intentional producer update, format bundled.js, then
run without flags to check parity. Update the pinned provenance deliberately.
"""
from pathlib import Path
import argparse
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PRODUCER_COMMIT = '96c58ba41a0bc0a61196c490e60cdc551164f7a7'
PAIRS = {
    'disk-model-v1.schema.json': 'docs/disk-model-v1.schema.json',
    'disk-model-v1.example.json': 'backend/tests/fixtures/disk-model-v1.json',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    target = ROOT / 'frontend' / 'model-assets'
    texts = {name: (ROOT / path).read_text() for name, path in PAIRS.items()}
    if args.write:
        target.mkdir(parents=True, exist_ok=True)
        for name, text in texts.items():
            (target / name).write_text(text)
        source = '''/* Published model contract and synthetic fixture; no disk reads or network calls. */
((root, factory) => {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.DiskMapAssets = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, () => ({
  producerCommit: PRODUCER,
  schema: JSON.parse(SCHEMA_TEXT),
  exampleText: EXAMPLE_TEXT,
}));
'''
        source = source.replace('PRODUCER', json.dumps(PRODUCER_COMMIT))
        source = source.replace('SCHEMA_TEXT', json.dumps(texts['disk-model-v1.schema.json']))
        source = source.replace('EXAMPLE_TEXT', json.dumps(texts['disk-model-v1.example.json']))
        (target / 'bundled.js').write_text(source)
        print('Synthetic viewer assets written; format bundled.js, then run this check again.')
        return
    for name, original in PAIRS.items():
        if (target / name).read_bytes() != (ROOT / original).read_bytes():
            raise SystemExit(f'Viewer asset is stale: {name}')
    subprocess.run(['node', '-e', '''
const fs = require('fs'), assert = require('assert');
const assets = require('./frontend/model-assets/bundled.js');
assert.equal(assets.producerCommit, process.argv[1]);
assert.deepStrictEqual(assets.schema, JSON.parse(fs.readFileSync('./docs/disk-model-v1.schema.json','utf8')));
assert.equal(assets.exampleText, fs.readFileSync('./backend/tests/fixtures/disk-model-v1.json','utf8'));
require('./frontend/disk-map-model.js').parse(assets.exampleText, assets.schema);
console.log('Canonical schema, synthetic example and browser bundle match.');
''', PRODUCER_COMMIT], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
