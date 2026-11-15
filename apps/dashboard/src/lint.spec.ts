// SPDX-License-Identifier: Apache-2.0
// @vitest-environment node
import { ESLint } from 'eslint';
import { fileURLToPath } from 'node:url';

const APP = fileURLToPath(new URL('..', import.meta.url));
const HEADER = '// SPDX-License-Identifier: Apache-2.0\n';

/** The rule ids and severities ESLint reports for `code` as a file in src. */
async function problems(code: string): Promise<[string | null, number][]> {
  const eslint = new ESLint({ cwd: APP });
  const [result] = await eslint.lintText(HEADER + code, {
    filePath: `${APP}src/app/unsafe.tsx`,
  });
  return result.messages.map((message) => [message.ruleId, message.severity]);
}

describe('lint rules of the dashboard', () => {
  it.each([
    [
      'dangerouslySetInnerHTML in JSX',
      'export const A = ({ h }: { h: string }) => <div dangerouslySetInnerHTML={{ __html: h }} />;\n',
      ['react/no-danger', 'no-restricted-syntax'],
    ],
    [
      'dangerouslySetInnerHTML as an object key',
      "import { createElement } from 'react';\n" +
        "export const A = (h: string) => createElement('div', { dangerouslySetInnerHTML: { __html: h } });\n",
      ['no-restricted-syntax'],
    ],
    [
      'dangerouslySetInnerHTML as a quoted key',
      "export const props = { 'dangerouslySetInnerHTML': { __html: '' } };\n",
      ['no-restricted-syntax'],
    ],
    [
      'dangerouslySetInnerHTML assigned',
      'export function set(props: Record<string, unknown>) {\n' +
        '  props.dangerouslySetInnerHTML = { __html: "" };\n' +
        "  props['dangerouslySetInnerHTML'] = null;\n" +
        '}\n',
      ['no-restricted-syntax', 'no-restricted-syntax'],
    ],
    ['eval', 'export const run = (code: string) => eval(code);\n', ['no-eval']],
    [
      'a string as setTimeout code',
      "export const later = () => setTimeout('alert(1)', 1);\n",
      ['no-implied-eval'],
    ],
    [
      'the Function constructor',
      "export const f = new Function('return 1');\n",
      ['no-new-func'],
    ],
  ])('reject %s in src', async (_, code, rules) => {
    const found = await problems(code);
    for (const rule of rules) {
      expect(found).toContainEqual([rule, 2]);
    }
    expect(
      found.filter(([rule]) => rule === 'no-restricted-syntax'),
    ).toHaveLength(
      rules.filter((rule) => rule === 'no-restricted-syntax').length,
    );
  });

  it('accept text rendered as React text', async () => {
    const code = 'export const A = ({ t }: { t: string }) => <p>{t}</p>;\n';
    expect(await problems(code)).toEqual([]);
  });
});
