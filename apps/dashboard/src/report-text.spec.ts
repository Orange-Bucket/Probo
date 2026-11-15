// SPDX-License-Identifier: Apache-2.0
import { readFileSync } from 'node:fs';
import { FINDINGS } from './findings';
import * as text from './report-text';
import { counts, report } from './testing/fixtures';
import { ROOT } from './testing/published';

const PACKAGE = `${ROOT}/packages/probo/`;
const SOURCE = `${PACKAGE}src/probo/`;

interface Schema {
  $defs: Record<
    string,
    { enum?: string[]; properties?: Record<string, unknown> }
  >;
}

function schema(name: string): Schema {
  return JSON.parse(
    readFileSync(`${PACKAGE}schemas/${name}`, 'utf8'),
  ) as Schema;
}

/** The value of the string constant `name: Final = ...` in a Python module of probo. */
function pythonConstant(module: string, name: string): string {
  const source = readFileSync(`${SOURCE}${module}`, 'utf8');
  const start = source.indexOf(`\n${name}: Final = `);
  expect(start).toBeGreaterThan(-1);
  const definition = source.slice(start, source.indexOf('\n"""', start + 1));
  return [...definition.matchAll(/"((?:[^"\\]|\\.)*)"/g)]
    .map((m) => m[1])
    .join('');
}

describe('fixed text', () => {
  it.each([
    ['report/markdown.py', 'EVIDENCE_SENTENCE', text.EVIDENCE_SENTENCE],
    ['report/markdown.py', 'INDEPENDENCE_SENTENCE', text.INDEPENDENCE_SENTENCE],
    ['report/markdown.py', 'LIMIT_SENTENCE', text.LIMIT_SENTENCE],
    ['report/markdown.py', 'GRADER_SENTENCE', text.GRADER_SENTENCE],
    ['report/markdown.py', 'TERMS', text.TERMS],
    ['report/summary.py', 'INCOMPLETE_WARNING', text.INCOMPLETE_WARNING],
    ['report/summary.py', 'CORPUS_WARNING', text.CORPUS_WARNING],
    ['judges/calibration.py', 'INDEPENDENCE_NOTE', text.INDEPENDENCE_NOTE],
  ])('%s %s is the same sentence', (module, name, value) => {
    expect(value).toBe(pythonConstant(module, name));
  });
});

describe('orderings', () => {
  it('lists the outcomes in the order of the schema', () => {
    expect(text.OUTCOMES).toEqual(
      schema('report.schema.json').$defs['Outcome'].enum,
    );
  });

  it('lists the grader statuses and exclusions in the order of the calibration data', () => {
    const defs = schema('calibration.schema.json').$defs;
    expect([...text.STATUSES].sort()).toEqual(
      Object.keys(defs['JudgeStatuses'].properties ?? {}).sort(),
    );
    expect([...text.EXCLUSION_REASONS].sort()).toEqual(
      Object.keys(defs['Exclusions'].properties ?? {}).sort(),
    );
    for (const { calibration } of FINDINGS) {
      if (calibration === null) continue;
      expect(Object.keys(calibration.statuses)).toEqual(text.STATUSES);
      expect(Object.keys(calibration.excluded)).toEqual(text.EXCLUSION_REASONS);
    }
  });

  it('counts only succeeded and resisted trials in the per-attempt denominator', () => {
    const all = counts(Object.fromEntries(text.OUTCOMES.map((o) => [o, 1])));
    expect(text.countsTotal(all)).toBe(10);
    expect(text.countsExcluded(all)).toBe(8);
  });
});

describe('runWarnings', () => {
  it('is empty for a complete run with one corpus', () => {
    expect(text.runWarnings(report())).toEqual([]);
  });

  it('keeps the warnings stored in the report', () => {
    const stored = report({
      warnings: [text.INCOMPLETE_WARNING],
      incomplete: true,
    });
    expect(text.runWarnings(stored)).toEqual([text.INCOMPLETE_WARNING]);
  });

  it('adds the fixed warnings that the flags call for', () => {
    const base = report();
    const flagged = report({
      incomplete: true,
      not_run: 3,
      facts: { ...base.facts, corpus_mismatch: true },
    });
    expect(text.runWarnings(flagged)).toEqual([
      text.INCOMPLETE_WARNING,
      text.CORPUS_WARNING,
    ]);
  });
});

describe('runStatus', () => {
  it('is incomplete exactly when the run is incomplete', () => {
    const base = report();
    expect(text.runStatus(base)).toBe('complete');
    expect(text.runStatus(report({ incomplete: true }))).toBe('incomplete');
    expect(text.runStatus(report({ not_run: 1 }))).toBe('incomplete');
    expect(
      text.runStatus(report({ facts: { ...base.facts, status: 'error' } })),
    ).toBe('incomplete');
  });
});

describe('runDate', () => {
  it('is the recorded date of the start time, or not recorded', () => {
    expect(text.runDate('2026-11-14T19:35:04+00:00')).toBe('2026-11-14');
    expect(text.runDate(null)).toBe('not recorded');
    expect(text.runDate('')).toBe('not recorded');
    expect(text.runDate('yesterday')).toBe('yesterday');
  });
});
