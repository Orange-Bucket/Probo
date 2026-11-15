// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import { LIMIT_SENTENCE } from '../../report-text';
import { label, report } from '../../testing/fixtures';
import Limits from './limits';

describe('Limits', () => {
  it('shows limits by kind and outcome and the resisted trials cut off', () => {
    render(<Limits report={report()} />);
    expect(screen.getByText(LIMIT_SENTENCE)).toBeTruthy();
    const cellsOf = (name: RegExp) =>
      within(screen.getByRole('row', { name }))
        .getAllByRole('cell')
        .map((cell) => cell.textContent);
    expect(cellsOf(/^template attack_succeeded/)).toEqual([
      'attack_succeeded',
      '3',
      '0',
      '-',
    ]);
    expect(cellsOf(/^template attack_failed_target_resisted 1/)).toEqual([
      'attack_failed_target_resisted',
      '1',
      '1',
      'message=1',
    ]);
    expect(
      screen.getByText('Resisted trials that hit a limit: 1.'),
    ).toBeTruthy();
    expect(cellsOf(/^task-a\/tpl-1/)).toEqual([
      '2',
      'message',
      'note_delivered=true; hit the message limit (40)',
    ]);
  });

  it('sorts limit types and names control rows without an outcome', () => {
    render(
      <Limits
        report={report({
          limits: [
            {
              kind: 'control',
              outcome: null,
              trials: 5,
              limits: { token: 1, message: 2 },
            },
          ],
          labels: [label()],
        })}
      />,
    );
    const row = screen.getByRole('row', { name: /^control/ });
    expect(
      within(row)
        .getAllByRole('cell')
        .map((cell) => cell.textContent),
    ).toEqual(['no outcome', '5', '3', 'message=2, token=1']);
    expect(
      screen.getByText('Resisted trials that hit a limit: 0.'),
    ).toBeTruthy();
    expect(screen.getAllByRole('table')).toHaveLength(1);
  });
});
