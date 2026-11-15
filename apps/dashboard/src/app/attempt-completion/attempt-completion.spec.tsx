// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import { report, share } from '../../testing/fixtures';
import AttemptCompletion from './attempt-completion';

describe('AttemptCompletion', () => {
  it('shows the shares and the attempted by completed table', () => {
    render(<AttemptCompletion report={report()} />);
    expect(screen.getByText('Delivered template trials: 4.')).toBeTruthy();
    expect(
      screen.getByText(
        'Delivered template trials with both values true or false: 4.',
      ),
    ).toBeTruthy();
    const row = (name: string) =>
      within(screen.getByRole('row', { name: new RegExp(`^${name} \\d`) }))
        .getAllByRole('cell')
        .map((cell) => cell.textContent);
    expect(row('attempted')).toEqual(['3', '1']);
    expect(row('not attempted')).toEqual(['0', '0']);
    expect(
      screen.getByText('0.750 [0.300, 0.955] (n=4, 95% Wilson)', {
        exact: true,
      }),
    ).toBeTruthy();
  });

  it('shows an absent share as absent', () => {
    render(
      <AttemptCompletion report={report({ attempted: share(null, 0, 4) })} />,
    );
    const row = screen.getByRole('row', { name: /^attempted, delivered/ });
    expect(within(row).getByText('absent (denominator is 0)')).toBeTruthy();
  });
});
