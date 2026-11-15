// SPDX-License-Identifier: Apache-2.0
/**
 * Renders every published finding and checks the page against the finding's own
 * report.md and judge-calibration.txt: every table row, every sentence and every rate.
 * The expected strings are read from those files, not written here.
 */
import { render, screen, within } from '@testing-library/react';
import { FINDINGS } from '../findings';
import {
  RATE_TEXT,
  markdownCell,
  markdownSections,
  publishedText,
} from '../testing/published';
import App from './app';

/** A cell's text as report.md prints it; for a rate, the printed rate alone. */
function cellText(cell: Element): string {
  const rate = cell.querySelector('[data-rate]');
  return markdownCell((rate ?? cell).textContent ?? '');
}

function rowsOf(region: HTMLElement): string[][] {
  return within(region)
    .queryAllByRole('row')
    .map((row) => Array.from(row.querySelectorAll('th, td')).map(cellText));
}

function rateCount(element: Element): number {
  return element.querySelectorAll('[data-rate]').length;
}

describe.each(FINDINGS.map((finding) => [finding.id, finding] as const))(
  'the published finding %s',
  (id, finding) => {
    const markdown = publishedText(id, 'report.md');
    const text = publishedText(id, 'judge-calibration.txt');

    it.runIf(markdown !== null)(
      'shows every row and sentence of report.md',
      () => {
        const { container } = render(<App findings={[finding]} />);
        const sections = markdownSections(markdown ?? '');
        const article = screen.getByRole('article');
        let rates = 0;
        for (const section of sections) {
          const region =
            section.level === 1
              ? article
              : screen.getByRole('region', { name: section.heading });
          if (section.level === 1) {
            expect(screen.getByRole('heading', { level: 2 }).textContent).toBe(
              section.heading,
            );
          }
          const shown = rowsOf(region);
          for (const table of section.tables) {
            for (const row of table) {
              expect(shown).toContainEqual(row);
              rates += row.filter((cell) => RATE_TEXT.test(cell)).length;
            }
          }
          for (const line of section.paragraphs) {
            // The terms follow the Trials table in report.md and the run facts on the page.
            const sentence = line.replace(/^\*\*(.*)\*\*$/, '$1');
            expect(
              within(article).getAllByText(sentence).length,
            ).toBeGreaterThan(0);
          }
        }
        // Every rate on the page outside the calibration is one of the report's rates.
        const calibration = screen.queryByRole('region', {
          name: 'Judge calibration',
        });
        expect(
          rateCount(container) - (calibration ? rateCount(calibration) : 0),
        ).toBe(rates);
        // Nothing from the data becomes a link or markup.
        expect(container.querySelector('a, img, script, iframe')).toBeNull();
      },
    );

    it.runIf(text !== null)('shows every line of judge-calibration.txt', () => {
      render(<App findings={[finding]} />);
      const region = screen.getByRole('region', { name: 'Judge calibration' });
      const lines = (text ?? '').trimEnd().split('\n');
      let rates = 0;
      for (const line of lines) {
        const colon = line.indexOf(': ');
        const [name, value] = [line.slice(0, colon), line.slice(colon + 2)];
        if (RATE_TEXT.test(value)) {
          rates += 1;
          const row = within(region).getByRole('row', {
            name: new RegExp(`^${name.replace(/[()]/g, '\\$&')} `),
          });
          expect(row.querySelector('[data-rate]')?.textContent).toBe(value);
        } else if (name === 'grader generate config') {
          // The same settings; JSON.parse cannot tell 0.0 from 0, so compare as data.
          const shown =
            within(region).getByText(/^grader generate config: /).textContent ??
            '';
          const settings = shown.slice(shown.indexOf(': ') + 2);
          expect(value === 'none' ? value : JSON.parse(value)).toEqual(
            settings === 'none' ? settings : JSON.parse(settings),
          );
        } else if (name === 'grader statuses' || name.startsWith('excluded')) {
          const table = within(region).getByRole('region', {
            name:
              name === 'grader statuses'
                ? 'Grader statuses'
                : 'Excluded from the pairs',
          });
          const listed =
            name === 'grader statuses'
              ? value
              : value.slice(value.indexOf('(') + 1, -1);
          const pairs = listed.split(', ').map((pair) => pair.split(' '));
          expect(rowsOf(table).slice(1)).toEqual(pairs);
          if (name !== 'grader statuses') {
            expect(
              within(table).getByText(`excluded: ${value.split(' ')[0]}`),
            ).toBeTruthy();
          }
        } else if (
          /^(false positives|false negatives|unknown) \(\d+\)$/.test(name)
        ) {
          const list = screen.getByRole('region', {
            name: name.replace(/ \(\d+\)$/, ''),
          });
          expect(within(list).getByRole('heading').textContent).toBe(name);
          const shown = within(list)
            .queryAllByRole('listitem')
            .map((item) => item.textContent);
          expect(shown.join(', ') || 'none').toBe(value);
        } else {
          expect(within(region).getByText(line)).toBeTruthy();
        }
        if (line.startsWith('judge vs deterministic check')) {
          // The confusion matrix table holds the counts of this line.
          const [tp, fp, fn, tn] = (
            /tp=(\d+) fp=(\d+) fn=(\d+) tn=(\d+)/.exec(line) ?? []
          )
            .slice(1)
            .map(Number);
          const [up, un] = (
            /reference positive (\d+), reference negative (\d+)/.exec(line) ??
            []
          )
            .slice(1)
            .map(Number);
          const matrix = within(region).getByRole('region', {
            name: 'Confusion matrix',
          });
          expect(rowsOf(matrix).slice(1, 3)).toEqual([
            [
              'reference positive',
              `tp ${tp}`,
              `fn ${fn}`,
              `${up}`,
              `${tp + fn + up}`,
            ],
            [
              'reference negative',
              `fp ${fp}`,
              `tn ${tn}`,
              `${un}`,
              `${fp + tn + un}`,
            ],
          ]);
        }
      }
      expect(rateCount(region)).toBe(rates);
    });
  },
);
