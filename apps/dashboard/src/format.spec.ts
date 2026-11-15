// SPDX-License-Identifier: Apache-2.0
import { FINDINGS } from './findings';
import {
  ABSENT,
  formatConfig,
  formatEstimateAndInterval,
  formatLevel,
  pythonFloat,
  pythonJson,
  pythonMember,
  pythonNumber,
  renderOptional,
  renderValue,
  trialRefs,
} from './format';
import type { Proportion } from './generated/report';
import { parseJson } from './json';
import { proportion, rate } from './testing/fixtures';
import {
  RATE_TEXT,
  markdownSections,
  publishedText,
  tableCells,
} from './testing/published';

describe('formatEstimateAndInterval', () => {
  // Expected values printed by probo.stats.rate.format_estimate_and_interval.
  it.each([
    [1 / 6, 0.09313176979191455, 0.2803161316361453, '0.167 [0.093, 0.281]'],
    [0, 0, 0.061, '0.000 [0.000, 0.061]'],
    [1, 0.939, 1, '1.000 [0.938, 1.000]'],
    [0.0625, 0.0625, 0.0625, '0.062 [0.062, 0.063]'],
    [0.1875, 0.1, 0.3, '0.188 [0.100, 0.300]'],
    [0.9999, 0.9995, 0.99999, '0.999900 [0.999500, 0.999991]'],
    [0.5, 0.0005, 0.9995, '0.5000 [0.0005, 0.9996]'],
    [0.0005, 0.00049, 0.0015, '0.0005 [0.0004, 0.0016]'],
    [1e-7, 1e-8, 2e-7, '1.0E-7 [1E-8, 2.0E-7]'],
    [-0, -0, 0.1, '-0.000 [-0.000, 0.101]'],
    [0.12345, 1e-9, 0.999999999, '0.1234500000 [1.0E-9, 0.9999999991]'],
  ])('formats %s [%s, %s] as %s', (estimate, lower, upper, expected) => {
    expect(formatEstimateAndInterval(estimate, lower, upper)).toBe(expected);
  });

  it('rounds the estimate to nearest with ties to even, on the exact binary value', () => {
    // 0.0625 and 0.1875 are exact binary ties at three decimals; 0.0005 is not a tie.
    expect(formatEstimateAndInterval(0.0625, 0, 1).split(' ')[0]).toBe('0.062');
    expect(formatEstimateAndInterval(0.1875, 0, 1).split(' ')[0]).toBe('0.188');
  });

  it('rounds the lower bound down and the upper bound up', () => {
    expect(formatEstimateAndInterval(0.5, 0.1239, 0.8761)).toBe(
      '0.500 [0.123, 0.877]',
    );
  });

  it('rejects values Python cannot quantize', () => {
    expect(() => formatEstimateAndInterval(Number.NaN, 0, 1)).toThrow(
      RangeError,
    );
    expect(() => formatEstimateAndInterval(1e-70, 1e-70, 0.5)).toThrow(
      RangeError,
    );
  });
});

describe('formatLevel', () => {
  it.each([
    [0.95, '95%'],
    [0.995, '99.5%'],
    [0.9999999, '99.99999%'],
    [0.5, '50%'],
    [1e-7, '0.00001%'],
    [0.123456789, '12.3456789%'],
    [1e-20, '0.000000000000000001%'],
  ])('formats %s as %s', (level, expected) => {
    expect(formatLevel(level)).toBe(expected);
  });
});

describe('renderValue', () => {
  it('prints a proportion with n and the level', () => {
    expect(
      renderValue(proportion(8, 10, 0.4901624715366417, 0.9433178485456246)),
    ).toBe('0.800 [0.490, 0.944] (n=10, 95% Wilson)');
  });

  it('prints a rate with its estimand', () => {
    expect(renderValue(rate(6, 20, 0.1455, 0.5185, 'per_attempt'))).toBe(
      '0.300 [0.145, 0.519] (n=20, per-attempt, 95% Wilson)',
    );
    expect(renderValue(rate(6, 20, 0.1455, 0.5185, 'per_trial'))).toContain(
      'per-trial',
    );
  });

  it('uses the stored estimate and interval, not recomputed ones', () => {
    const stored: Proportion = {
      ...proportion(1, 2, 0.1005, 0.8995),
      estimate: 0.25,
    };
    expect(renderValue(stored)).toBe('0.250 [0.100, 0.900] (n=2, 95% Wilson)');
  });

  it('prints an absent value as absent, never as 0', () => {
    expect(renderOptional(null)).toBe(ABSENT);
    expect(renderOptional(undefined)).toBe('absent (denominator is 0)');
  });
});

describe('pythonFloat', () => {
  // Expected values printed by Python's repr() and str() of the same float.
  it.each([
    [1, '1.0'],
    [0, '0.0'],
    [-0, '-0.0'],
    [0.7, '0.7'],
    [100, '100.0'],
    [1e-5, '1e-05'],
    [0.0001, '0.0001'],
    [0.00012, '0.00012'],
    [1e-7, '1e-07'],
    [1e15, '1000000000000000.0'],
    [9999999999999998, '9999999999999998.0'],
    [1e16, '1e+16'],
    [1.5e16, '1.5e+16'],
    [123456789012345680, '1.2345678901234568e+17'],
    [1e22, '1e+22'],
    [0.1 + 0.2, '0.30000000000000004'],
    [-12345.678, '-12345.678'],
    [5e-324, '5e-324'],
    [1.7976931348623157e308, '1.7976931348623157e+308'],
  ])('prints %s as %s', (value, expected) => {
    expect(pythonFloat(value)).toBe(expected);
  });

  it('prints integers as integers and floats as floats', () => {
    expect(pythonNumber(1, false)).toBe('1');
    expect(pythonNumber(1, true)).toBe('1.0');
    expect(pythonNumber(0.5, false)).toBe('0.5');
    expect(pythonNumber(2 ** 60, false)).toBe('1152921504606846976');
  });
});

describe('numbers read from JSON', () => {
  it('print as Python prints them in the report and the calibration text', () => {
    const config = parseJson(
      '{"temperature": 1.0, "top_p": 0.0, "seed": 42, "eps": 1e-05, "big": 1e16, ' +
        '"neg": -0.0, "stop": [1.0, 2], "nested": {"x": 0.5, "y": 3}}',
    ) as Record<string, unknown>;
    expect(formatConfig(config)).toBe(
      'temperature=1.0, top_p=0.0, seed=42, eps=1e-05, big=1e+16, neg=-0.0, ' +
        "stop=[1.0, 2], nested={'x': 0.5, 'y': 3}",
    );
    expect(pythonJson(config)).toBe(
      '{"big": 1e+16, "eps": 1e-05, "neg": -0.0, "nested": {"x": 0.5, "y": 3}, ' +
        '"seed": 42, "stop": [1.0, 2], "temperature": 1.0, "top_p": 0.0}',
    );
    const usage = parseJson(
      '{"total_cost": 2.0, "total_tokens": 5, "reasoning": null}',
    );
    expect(pythonMember(usage as object, 'total_cost', 'not reported')).toBe(
      '2.0',
    );
    expect(pythonMember(usage as object, 'total_tokens', 'not reported')).toBe(
      '5',
    );
    expect(pythonMember(usage as object, 'reasoning', 'not reported')).toBe(
      'not reported',
    );
  });
});

describe('configuration text', () => {
  it('prints a generate config as the report does', () => {
    expect(formatConfig({})).toBe('defaults');
    expect(
      formatConfig({ a: true, b: null, c: 'x', d: 0.7, e: [1, "it's"] }),
    ).toBe('a=True, b=None, c=x, d=0.7, e=[1, "it\'s"]');
  });

  it('prints JSON as json.dumps(sort_keys=True) does', () => {
    expect(
      pythonJson({
        temperature: 0.5,
        max_tokens: 10,
        nested: { b: 1, a: [true] },
      }),
    ).toBe(
      '{"max_tokens": 10, "nested": {"a": [true], "b": 1}, "temperature": 0.5}',
    );
    expect(pythonJson({ name: 'caf\u00e9' })).toBe('{"name": "caf\\u00e9"}');
  });

  it('prints trials as sample id@epoch', () => {
    expect(trialRefs([])).toBe('none');
    expect(
      trialRefs([
        ['a/b', 1],
        [7, 2],
      ]),
    ).toBe('a/b@1, 7@2');
  });
});

/** Every Proportion or Rate object anywhere in `value`. */
function proportions(value: unknown): Proportion[] {
  if (Array.isArray(value)) return value.flatMap(proportions);
  if (value === null || typeof value !== 'object') return [];
  const record = value as Record<string, unknown>;
  if ('successes' in record && 'interval' in record)
    return [record as unknown as Proportion];
  return Object.values(record).flatMap(proportions);
}

describe.each(FINDINGS.map((finding) => [finding.id, finding] as const))(
  'the published finding %s',
  (id, finding) => {
    const markdown = publishedText(id, 'report.md');
    const text = publishedText(id, 'judge-calibration.txt');

    it('prints every rate of report.json as report.md does', () => {
      expect(markdown, `findings/${id}/report.md`).not.toBeNull();
      const printed = tableCells(markdownSections(markdown ?? '')).filter(
        (cell) => RATE_TEXT.test(cell) && cell !== ABSENT,
      );
      const rendered = proportions(finding.report).map(renderValue);
      expect(new Set(rendered)).toEqual(new Set(printed));
    });

    it.runIf(finding.calibration !== null)(
      'prints every rate of judge-calibration.json as judge-calibration.txt does',
      () => {
        expect(text, `findings/${id}/judge-calibration.txt`).not.toBeNull();
        const printed = (text ?? '')
          .split('\n')
          .map((line) => line.slice(line.indexOf(': ') + 2))
          .filter((value) => RATE_TEXT.test(value));
        const calibration = finding.calibration;
        const rendered = [
          calibration?.base_rate,
          calibration?.precision,
          calibration?.recall,
          calibration?.recall_unknown_as_miss,
        ].map(renderOptional);
        expect(rendered).toEqual(printed);
      },
    );
  },
);
