// SPDX-License-Identifier: Apache-2.0
// Writes the TypeScript types of the committed JSON Schemas into apps/dashboard/src/generated/.
//
//   node apps/dashboard/scripts/generate-types.mjs           write the files
//   node apps/dashboard/scripts/generate-types.mjs --check   exit 1 if a file would change
//
// The output depends only on the schemas, json-schema-to-typescript and the workspace's
// Prettier configuration, so it is the same on every machine.
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { compile } from 'json-schema-to-typescript';
import * as prettier from 'prettier';

const ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../..',
);

const TARGETS = [
  {
    schema: 'packages/probo/schemas/report.schema.json',
    output: 'apps/dashboard/src/generated/report.ts',
  },
  {
    schema: 'packages/probo/schemas/calibration.schema.json',
    output: 'apps/dashboard/src/generated/calibration.ts',
  },
];

function banner(schema) {
  return [
    '// SPDX-License-Identifier: Apache-2.0',
    `// Generated from ${schema} by apps/dashboard/scripts/generate-types.mjs; do not edit.`,
    '// Regenerate with: pnpm nx run dashboard:generate-types',
  ].join('\n');
}

/**
 * A copy of `node` with every draft 2020-12 `prefixItems` tuple rewritten to the draft-07
 * form (`items` as an array, no additional items), which json-schema-to-typescript reads;
 * without this, a tuple such as [sample id, epoch] is typed [unknown, unknown].
 */
export function withDraft07Tuples(node) {
  if (Array.isArray(node)) return node.map(withDraft07Tuples);
  if (node === null || typeof node !== 'object') return node;
  if ('prefixItems' in node && ('items' in node || 'additionalItems' in node)) {
    // 2020-12 "items" next to "prefixItems" means the rest of the array, not the tuple;
    // there is no draft-07 form that this rewrite could give it, so stop.
    throw new Error(
      'a schema has both prefixItems and items or additionalItems',
    );
  }
  const copy = {};
  for (const [key, value] of Object.entries(node)) {
    if (key === 'prefixItems') {
      copy.items = withDraft07Tuples(value);
      copy.additionalItems = false;
    } else {
      copy[key] = withDraft07Tuples(value);
    }
  }
  return copy;
}

/** The generated files as { output path relative to the root: content }. */
async function generate() {
  const files = {};
  for (const { schema, output } of TARGETS) {
    const schemaPath = path.join(ROOT, schema);
    const parsed = withDraft07Tuples(
      JSON.parse(await readFile(schemaPath, 'utf8')),
    );
    const code = await compile(parsed, parsed.title, {
      bannerComment: banner(schema),
      cwd: path.dirname(schemaPath),
      format: false,
      strictIndexSignatures: true,
      unknownAny: true,
      unreachableDefinitions: false,
    });
    const outputPath = path.join(ROOT, output);
    const config = (await prettier.resolveConfig(outputPath)) ?? {};
    const text = await prettier.format(code, {
      ...config,
      filepath: outputPath,
    });
    if (/[^\t\n\r -~]/.test(text)) {
      throw new Error(
        `${output} would contain a character outside printable ASCII`,
      );
    }
    files[output] = text;
  }
  return files;
}

async function main() {
  const check = process.argv.includes('--check');
  const files = await generate();
  const stale = [];
  for (const [output, text] of Object.entries(files)) {
    const outputPath = path.join(ROOT, output);
    const current = await readFile(outputPath, 'utf8').catch(() => null);
    if (current === text) continue;
    if (check) {
      stale.push(output);
    } else {
      await mkdir(path.dirname(outputPath), { recursive: true });
      await writeFile(outputPath, text);
      console.log(`wrote ${output}`);
    }
  }
  if (stale.length > 0) {
    console.error(
      `out of date: ${stale.join(', ')}; run: pnpm nx run dashboard:generate-types`,
    );
    process.exitCode = 1;
  }
}

if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  await main();
}
