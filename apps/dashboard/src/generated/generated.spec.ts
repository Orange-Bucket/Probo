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

/** `withDraft07Tuples(schema)` of the generator, run in Node; its JSON or its error. */
function rewrite(schema: unknown): { output: unknown } | { error: string } {
  const code =
    `import { withDraft07Tuples } from ${JSON.stringify(SCRIPT)};` +
    `try { console.log(JSON.stringify({ output: withDraft07Tuples(${JSON.stringify(schema)}) })); }` +
    'catch (error) { console.log(JSON.stringify({ error: error.message })); }';
  const run = spawnSync(process.execPath, ['--input-type=module', '-e', code], {
    encoding: 'utf8',
  });
  return JSON.parse(run.stdout) as { output: unknown } | { error: string };
}

describe('the tuple rewrite of the generator', () => {
  it('turns prefixItems into draft-07 items', () => {
    expect(
      rewrite({ a: { type: 'array', prefixItems: [{ type: 'string' }] } }),
    ).toEqual({
      output: {
        a: {
          type: 'array',
          items: [{ type: 'string' }],
          additionalItems: false,
        },
      },
    });
  });

  it.each([
    { items: false },
    { items: { type: 'integer' } },
    { additionalItems: true },
  ])('refuses prefixItems next to %j', (extra) => {
    expect(rewrite({ type: 'array', prefixItems: [{}], ...extra })).toEqual({
      error: 'a schema has both prefixItems and items or additionalItems',
    });
  });
});
