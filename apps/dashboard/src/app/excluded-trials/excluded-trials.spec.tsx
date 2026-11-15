// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import { GRADER_SENTENCE } from '../../report-text';
import { label, report } from '../../testing/fixtures';
import ExcludedTrials from './excluded-trials';

describe('ExcludedTrials', () => {
  it('lists excluded trials with their evidence', () => {
    render(
      <ExcludedTrials
        report={report({
          labels: [
            label(),
            label({
              epoch: 2,
              outcome: 'provider_error',
              evidence: ['RateLimitError', 'retry'],
            }),
            label({ kind: 'control', outcome: null }),
          ],
        })}
      />,
    );
    expect(
      screen.getByText(
        'Template trials outside the per-attempt denominator, and control trials with an ' +
          'error label: 1.',
      ),
    ).toBeTruthy();
    expect(screen.getByText(GRADER_SENTENCE)).toBeTruthy();
    const row = screen.getByRole('row', { name: /^task-a\/tpl-1 2/ });
    expect(
      within(row)
        .getAllByRole('cell')
        .map((cell) => cell.textContent),
    ).toEqual(['2', 'template', 'provider_error', 'RateLimitError; retry']);
  });

  it('renders evidence from logs as text, never as markup', () => {
    const hostile =
      '<img src=x onerror="alert(1)"><a href="https://example.test">x</a>';
    const { container } = render(
      <ExcludedTrials
        report={report({
          labels: [label({ outcome: 'grader_error', evidence: [hostile] })],
        })}
      />,
    );
    expect(screen.getByText(hostile)).toBeTruthy();
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('a')).toBeNull();
  });

  it('shows no table when nothing is excluded', () => {
    render(<ExcludedTrials report={report()} />);
    expect(screen.queryByRole('table')).toBeNull();
  });
});
