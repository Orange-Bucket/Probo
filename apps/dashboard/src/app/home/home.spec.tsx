// SPDX-License-Identifier: Apache-2.0
import { fireEvent, render, screen, within } from '@testing-library/react';
import { FINDINGS } from '../../findings';
import { runDate, runStatus } from '../../report-text';
import { finding, report } from '../../testing/fixtures';
import Home, { findingsNoun } from './home';

const NEWER = '2026-03-01-b';
const OLDER = '2026-01-01-a';

function twoFindings() {
  const base = report();
  return [
    finding(NEWER, {
      report: report({
        not_run: 2,
        facts: {
          ...base.facts,
          model: 'ollama/newer',
          started_at: '2026-03-01T08:00:00+00:00',
        },
      }),
    }),
    finding(OLDER),
  ];
}

function renderHome(findings = twoFindings()) {
  const onSelect = vi.fn();
  render(<Home findings={findings} onSelect={onSelect} />);
  return {
    onSelect,
    card: screen.getByRole('region', { name: 'Finding reports' }),
  };
}

function entries(card: HTMLElement): HTMLElement[] {
  return within(within(card).getByRole('list')).getAllByRole('button');
}

describe('Home', () => {
  it('introduces the dashboard and has one feature card: the finding reports', () => {
    renderHome();
    expect(screen.getByRole('heading', { level: 2 }).textContent).toBe(
      'Probo dashboard',
    );
    expect(
      screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent),
    ).toEqual(['Finding reports']);
    expect(screen.getAllByRole('region')).toHaveLength(1);
  });

  it('counts the published findings', () => {
    const { card } = renderHome();
    expect(card.textContent).toContain('2 findings published');
    expect(findingsNoun(1)).toBe('finding');
    expect(findingsNoun(2)).toBe('findings');
  });

  it('opens the newest finding from its action', () => {
    const { card, onSelect } = renderHome();
    fireEvent.click(
      within(card).getByRole('button', { name: 'Open the newest finding' }),
    );
    expect(onSelect).toHaveBeenCalledWith(NEWER);
  });

  it("lists every finding, newest first, with its report's model, date and status", () => {
    const { card, onSelect } = renderHome();
    const [newer, older] = entries(card);
    expect(newer.textContent).toBe(
      `${NEWER} ollama/newer 2026-03-01 incomplete`,
    );
    expect(older.textContent).toBe(
      `${OLDER} mockllm/model 2026-01-01 complete`,
    );
    fireEvent.click(older);
    expect(onSelect).toHaveBeenCalledWith(OLDER);
  });

  it('shows the published findings as their reports say', () => {
    const { card } = renderHome(FINDINGS);
    expect(entries(card).map((entry) => entry.textContent)).toEqual(
      FINDINGS.map(
        ({ id, report: r }) =>
          `${id} ${r.facts.model} ${runDate(r.facts.started_at)} ${runStatus(r)}`,
      ),
    );
  });

  it('shows ids and models as text, never as markup or links', () => {
    const hostile = '<img src=x onerror=alert(1)>';
    const { card } = renderHome([
      finding(hostile, {
        report: report({
          facts: { ...report().facts, model: 'javascript:alert(1)' },
        }),
      }),
    ]);
    expect(entries(card)[0].textContent).toBe(
      `${hostile} javascript:alert(1) 2026-01-01 complete`,
    );
    expect(card.querySelector('img, a')).toBeNull();
  });

  it('shows the empty state, and nothing to open, when no finding is published', () => {
    const { card } = renderHome([]);
    expect(within(card).getByText('Nothing to show yet')).toBeTruthy();
    expect(within(card).getByText('No findings are published.')).toBeTruthy();
    expect(
      within(card).getByText(
        'A finding appears here when its report.json is in the findings directory at build time.',
      ),
    ).toBeTruthy();
    expect(within(card).queryByRole('button')).toBeNull();
    expect(within(card).queryByRole('list')).toBeNull();
    expect(card.textContent).not.toContain('published findings');
  });
});
