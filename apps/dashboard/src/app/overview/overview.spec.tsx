// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import { FINDINGS } from '../../findings';
import {
  markdownCell,
  markdownSections,
  publishedText,
} from '../../testing/published';
import { ABSENT_ATTACK, calibration, report } from '../../testing/fixtures';
import Overview from './overview';

interface Card {
  name: string;
  figure: string;
  rate: string;
}

function cards(): Card[] {
  const region = screen.getByRole('region', { name: 'Overview' });
  return within(region)
    .getAllByRole('group')
    .map((card) => ({
      name: card.querySelector('h4')?.textContent ?? '',
      figure: card.querySelector('h4 + div')?.textContent ?? '',
      rate: card.querySelector('[data-rate]')?.textContent ?? '',
    }));
}

/** The cell of report.md's table row whose first cell is `row`, in the column `column`. */
function reportCell(markdown: string, row: string, column: string): string {
  for (const section of markdownSections(markdown)) {
    for (const block of section.blocks) {
      if (block.kind !== 'table') continue;
      const index = block.rows[0].indexOf(column);
      const found = block.rows.find((cells) => cells[0] === row);
      if (index >= 0 && found !== undefined) return found[index];
    }
  }
  throw new Error(`no row ${row} with a column ${column}`);
}

/** The value of the line `name: value` of judge-calibration.txt. */
function calibrationValue(text: string, name: string): string {
  const line = text.split('\n').find((l) => l.startsWith(`${name}: `));
  if (line === undefined) throw new Error(`no line ${name}`);
  return line.slice(name.length + 2);
}

describe.each(FINDINGS.map((finding) => [finding.id, finding] as const))(
  'the overview of the published finding %s',
  (id, finding) => {
    it('shows the rates exactly as report.md and judge-calibration.txt print them', () => {
      const markdown = publishedText(id, 'report.md') ?? '';
      const text = publishedText(id, 'judge-calibration.txt');
      render(
        <Overview report={finding.report} calibration={finding.calibration} />,
      );
      const expected = [
        reportCell(markdown, 'all templates', 'Per-attempt rate'),
        reportCell(
          markdown,
          'attempted, delivered template trials',
          'Share true',
        ),
        reportCell(
          markdown,
          'task_completed true, control trials',
          'Share true',
        ),
        reportCell(
          markdown,
          'task_completed true, template trials',
          'Share true',
        ),
        ...(text === null
          ? []
          : [
              calibrationValue(text, 'precision (unknown excluded)'),
              calibrationValue(text, 'recall (unknown excluded)'),
            ]),
      ];
      const shown = cards();
      expect(shown.map((card) => markdownCell(card.rate))).toEqual(expected);
      // Each headline is `successes of n`, with the n its printed rate names.
      for (const card of shown) {
        const [, n] = /\(n=(\d+)/.exec(card.rate) ?? [];
        expect(card.figure).toMatch(new RegExp(`^\\d+ of ${n}$`));
      }
    });
  },
);

describe('Overview', () => {
  it('shows the counts of the stored values as headlines', () => {
    render(<Overview report={report()} calibration={calibration()} />);
    expect(cards().map((card) => card.figure)).toEqual([
      '3 of 4',
      '4 of 4',
      '2 of 4',
      '1 of 4',
      '2 of 3',
      '2 of 3',
    ]);
    expect(cards().map((card) => card.name)).toEqual([
      'Attack success per attempt, all templates',
      'Attempted delivered template trials',
      'Benign utility control trials',
      'Benign utility template trials',
      'Judge precision unknown excluded',
      'Judge recall unknown excluded',
    ]);
  });

  it('leaves the judge cards out when there is no calibration', () => {
    render(<Overview report={report()} calibration={null} />);
    expect(cards()).toHaveLength(4);
    expect(cards().some((card) => card.name.startsWith('Judge'))).toBe(false);
  });

  it('shows an absent rate as absent, never 0', () => {
    render(
      <Overview
        report={report({ attack: ABSENT_ATTACK })}
        calibration={calibration({ precision: null })}
      />,
    );
    const [attack, , , , precision] = cards();
    for (const card of [attack, precision]) {
      expect(card.figure).toBe('absent');
      expect(card.rate).toBe('absent (denominator is 0)');
    }
  });
});
