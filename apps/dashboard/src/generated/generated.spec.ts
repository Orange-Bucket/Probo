// SPDX-License-Identifier: Apache-2.0
// @vitest-environment node
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const SCRIPT = fileURLToPath(
  new URL('../../scripts/generate-types.mjs', import.meta.url),
);

describe('generated types', () => {
  it('match what the committed schemas generate', () => {
    // Regenerates in memory and compares with the files; writes nothing.
    const run = spawnSync(process.execPath, [SCRIPT, '--check'], {
      encoding: 'utf8',
    });
    expect(run.stderr).toBe('');
    expect(run.status).toBe(0);
  });
});
