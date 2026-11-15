// SPDX-License-Identifier: Apache-2.0
/**
 * Renders every published finding and checks the page against the finding's own
 * report.md and judge-calibration.txt: the sections in the same order and nesting, each
 * section's paragraphs and tables in order with every row and nothing else, and every
 * line of the calibration text. The expected strings are read from those files.
 */
import { render, screen, within } from '@testing-library/react';
import { FINDINGS } from '../findings';
import {
  RATE_TEXT,
  type MarkdownBlock,
  markdownCell,
  markdownSections,
  publishedText,
} from '../testing/published';
import App from './app';

/** Sections of the page that report.md does not have: the manifest and the calibration. */
const NOT_IN_REPORT = [
  'Published finding',
  'Judge calibration',
  'Disagreements',
];

/** A cell's text as report.md prints it; for a rate, the printed rate alone. */
function cellText(cell: Element): string {
  const rate = cell.querySelector('[data-rate]');
  return markdownCell((rate ?? cell).textContent ?? '');
}

function tableRows(table: Element): string[][] {
  return Array.from(table.querySelectorAll('tr')).map((row) =>
    Array.from(row.querySelectorAll('th, td')).map(cellText),
  );
}

function rowsOf(region: HTMLElement): string[][] {
  return Array.from(region.querySelectorAll('table')).flatMap(tableRows);
}

/** A paragraph as report.md prints it: a warning in bold, other text as it is. */
function paragraphText(paragraph: Element): string {
  const text = paragraph.textContent ?? '';
  const strong = paragraph.querySelector(':scope > strong');
  if (strong !== null && strong.textContent === text)
    return `**${markdownCell(text)}**`;
  return text.split(/\s+/).filter(Boolean).join(' ');
}

/** The paragraphs and tables that belong to `region` itself, not to a subsection. */
function ownBlocks(region: Element): MarkdownBlock[] {
  return Array.from(region.querySelectorAll('p, table'))
    .filter((element) => element.closest('section, article') === region)
    .map(
      (element): MarkdownBlock =>
        element.tagName === 'TABLE'
          ? { kind: 'table', rows: tableRows(element) }
          : { kind: 'paragraph', text: paragraphText(element) },
    );
}

interface OutlineEntry {
  heading: string;
  level: number;
  parent: string | null;
}

function headingOf(section: Element): Element | null {
  return section.querySelector(':scope > h3, :scope > h4');
}

/** The report's sections on the page: h3 as level 2, h4 as level 3, with their parent. */
function pageOutline(article: Element): OutlineEntry[] {
  return Array.from(article.querySelectorAll('section'))
    .filter((section) => {
      for (
        let s: Element | null = section;
        s !== null;
        s = s.parentElement?.closest('section') ?? null
      ) {
        if (NOT_IN_REPORT.includes(s.getAttribute('aria-label') ?? ''))
          return false;
      }
      return true;
    })
    .map((section) => {
      const heading = headingOf(section);
      const parent = section.parentElement?.closest('section') ?? null;
      return {
        heading: heading?.textContent ?? '',
        level:
          heading?.tagName === 'H3' ? 2 : heading?.tagName === 'H4' ? 3 : 0,
        parent: parent === null ? null : (headingOf(parent)?.textContent ?? ''),
      };
    });
}

function rateCount(element: Element): number {
  return element.querySelectorAll('[data-rate]').length;
}

describe.each(FINDINGS.map((finding) => [finding.id, finding] as const))(
  'the published finding %s',
  (id, finding) => {
    const markdown = publishedText(id, 'report.md');
    const text = publishedText(id, 'judge-calibration.txt');
    const sections = markdownSections(markdown ?? '');

    it('has a report.md', () => {
      expect(markdown, `findings/${id}/report.md`).not.toBeNull();
    });

    it('has a judge-calibration.txt exactly when it has a judge-calibration.json', () => {
      expect(text !== null, `findings/${id}/judge-calibration.txt`).toBe(
        finding.calibration !== null,
      );
    });

    it('shows the sections of report.md in the same order and nesting', () => {
      render(<App findings={[finding]} />);
      const article = screen.getByRole('article');
      expect(screen.getByRole('heading', { level: 2 }).textContent).toBe(
        sections.find((section) => section.level === 1)?.heading,
      );
      expect(pageOutline(article)).toEqual(
        sections
          .filter((section) => section.level > 1)
          .map(({ heading, level, parent }) => ({ heading, level, parent })),
      );
    });

    it('shows the paragraphs and tables of each section of report.md in order', () => {
      expect(markdown).not.toBeNull();
      const { container } = render(<App findings={[finding]} />);
      const article = screen.getByRole('article');
      let rates = 0;
      for (const section of sections) {
        const region =
          section.level === 1
            ? article
            : screen.getByRole('region', { name: section.heading });
        expect(ownBlocks(region), section.heading).toEqual(section.blocks);
        for (const block of section.blocks) {
          if (block.kind === 'table') {
            rates += block.rows
              .flat()
              .filter((cell) => RATE_TEXT.test(cell)).length;
          }
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
    });

    it.runIf(finding.calibration !== null)(
      'shows every line of judge-calibration.txt',
      () => {
        expect(text).not.toBeNull();
        render(<App findings={[finding]} />);
        const region = screen.getByRole('region', {
          name: 'Judge calibration',
        });
        const lines = (text ?? '').trimEnd().split('\n');
        const rateNames: string[] = [];
        for (const line of lines) {
          const colon = line.indexOf(': ');
          const [name, value] = [line.slice(0, colon), line.slice(colon + 2)];
          if (RATE_TEXT.test(value)) {
            rateNames.push(name);
            const row = within(region).getByRole('row', {
              name: new RegExp(`^${name.replace(/[()]/g, '\\$&')} `),
            });
            expect(row.querySelector('[data-rate]')?.textContent).toBe(value);
          } else if (name === 'grader statuses' || name === 'excluded') {
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
            if (name === 'excluded') {
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
        // The rates in the order of the text, and no others.
        const rates = within(region).getByRole('region', {
          name: 'Grader rates',
        });
        expect(
          rowsOf(rates)
            .slice(1)
            .map(([name]) => name),
        ).toEqual(rateNames);
        expect(rateCount(region)).toBe(rateNames.length);
      },
    );
  },
);
