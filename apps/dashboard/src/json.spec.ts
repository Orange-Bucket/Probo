// SPDX-License-Identifier: Apache-2.0
import { readdirSync } from 'node:fs';
import { isFloat, parseJson } from './json';
import { FINDINGS_DIR, publishedText } from './testing/published';

describe('parseJson', () => {
  it.each([
    '0',
    '-0',
    '1.5e+16',
    '"a\\u00e9\\ud83d\\ude00\\n\\"\\\\\\/\\b\\f\\r\\t"',
    'true',
    'null',
    ' [1, 2.0, {"a": [], "b": {}}, "x"] ',
    '{"a": 1, "a": "last wins"}',
    '{"__proto__": {"polluted": true}, "constructor": 1}',
  ])('returns what JSON.parse returns for %s', (text) => {
    expect(parseJson(text)).toStrictEqual(JSON.parse(text));
  });

  it('keeps "__proto__" as an own key, as JSON.parse does', () => {
    const value = parseJson('{"__proto__": {"polluted": true}}') as Record<
      string,
      unknown
    >;
    expect(Object.getPrototypeOf(value)).toBe(Object.prototype);
    expect(Object.keys(value)).toEqual(['__proto__']);
    expect(({} as Record<string, unknown>)['polluted']).toBeUndefined();
  });

  it.each([
    '',
    '01',
    '1.',
    '.5',
    '+1',
    '-',
    '1e',
    'NaN',
    'Infinity',
    '[1,]',
    '{"a": 1,}',
    "{'a': 1}",
    '"\\x41"',
    '"\\u12"',
    '"tab\there"',
    '"open',
    '[1] 2',
    'tru',
  ])('rejects %j as JSON.parse does', (text) => {
    expect(() => JSON.parse(text)).toThrow(SyntaxError);
    expect(() => parseJson(text)).toThrow(SyntaxError);
  });

  it('records which numbers were written as floats', () => {
    const value = parseJson(
      '{"f": 1.0, "e": 1e16, "E": 2E-5, "small": 0.00001, "i": 1, "n": -3, "s": "1.0",' +
        ' "list": [1, 1.0, 0e0], "again": 1.0, "again": 2}',
    ) as Record<string, unknown>;
    const floats = ['f', 'e', 'E', 'small'].map((key) => isFloat(value, key));
    expect(floats).toEqual([true, true, true, true]);
    expect(
      ['i', 'n', 's', 'again', 'missing'].map((key) => isFloat(value, key)),
    ).toEqual([false, false, false, false, false]);
    const list = value['list'] as unknown[];
    expect([0, 1, 2].map((index) => isFloat(list, index))).toEqual([
      false,
      true,
      true,
    ]);
    expect(isFloat({ f: 1.0 }, 'f')).toBe(false);
  });

  it('parses every published JSON file as JSON.parse does', () => {
    const files = readdirSync(FINDINGS_DIR).flatMap((id) =>
      ['report.json', 'judge-calibration.json', 'manifest.json'].map(
        (name) => publishedText(id, name) ?? 'null',
      ),
    );
    expect(files.length).toBeGreaterThan(0);
    for (const text of files)
      expect(parseJson(text)).toStrictEqual(JSON.parse(text));
  });
});
