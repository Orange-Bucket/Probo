// SPDX-License-Identifier: Apache-2.0
// @vitest-environment node
import { ESLint } from 'eslint';
import { fileURLToPath } from 'node:url';

const APP = fileURLToPath(new URL('..', import.meta.url));

describe('lint rules of the dashboard', () => {
  it('reject dangerouslySetInnerHTML in src', async () => {
    const eslint = new ESLint({ cwd: APP });
    const code =
      '// SPDX-License-Identifier: Apache-2.0\n' +
      'export function Unsafe({ html }: { html: string }) {\n' +
      '  return <div dangerouslySetInnerHTML={{ __html: html }} />;\n' +
      '}\n';
    const [result] = await eslint.lintText(code, {
      filePath: `${APP}src/app/unsafe.tsx`,
    });
    expect(result.messages).toContainEqual(
      expect.objectContaining({ ruleId: 'react/no-danger', severity: 2 }),
    );
  });
});
