// Exercise the consumer API covered by our narrowly scoped development override.
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { loadNycConfig } = require('@istanbuljs/load-nyc-config');
(async () => {
  const cwd = fs.mkdtempSync(path.join(os.tmpdir(), 'disk-yaml-fixture-'));
  fs.writeFileSync(path.join(cwd, '.nycrc.yml'), 'all: true\ninclude:\n  - "frontend/**/*.js"\nreporter:\n  - text\n');
  const result = await loadNycConfig({ cwd });
  assert.equal(result.all, true);
  assert.deepEqual(result.include, ['frontend/**/*.js']);
  assert.deepEqual(result.reporter, ['text']);
  console.log('Scoped YAML consumer compatibility passed.');
})();
