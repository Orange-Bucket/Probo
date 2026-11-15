// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import { ABSENT_ATTACK, ATTACK, report } from '../../testing/fixtures';
import AttackSuccess from './attack-success';

describe('AttackSuccess', () => {
  it('shows both rates over all templates and per template', () => {
    render(<AttackSuccess report={report()} />);
    for (const name of ['all templates', 'tpl-1']) {
      const row = screen.getByRole('row', { name: new RegExp(`^${name}`) });
      const cells = within(row).getAllByRole('cell');
      expect(cells[0].textContent).toBe('4');
      expect(cells[1].textContent).toBe('0');
      expect(within(cells[2]).getByText(/per-attempt/).textContent).toBe(
        '0.750 [0.300, 0.955] (n=4, per-attempt, 95% Wilson)',
      );
      expect(within(cells[3]).getByText(/per-trial/).textContent).toBe(
        '0.750 [0.300, 0.955] (n=4, per-trial, 95% Wilson)',
      );
    }
  });

  it('shows absent rates as absent, never as 0', () => {
    render(
      <AttackSuccess
        report={report({
          attack: ABSENT_ATTACK,
          attack_by_template: { 'tpl-1': ATTACK },
        })}
      />,
    );
    const row = screen.getByRole('row', { name: /^all templates/ });
    expect(within(row).getAllByText('absent (denominator is 0)')).toHaveLength(
      2,
    );
    expect(within(row).getAllByRole('cell')[1].textContent).toBe('2');
    expect(row.textContent).not.toMatch(/0\.000/);
  });
});
