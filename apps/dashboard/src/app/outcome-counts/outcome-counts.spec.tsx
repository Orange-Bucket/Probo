// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import { ATTACK, counts, report } from '../../testing/fixtures';
import OutcomeCounts from './outcome-counts';

describe('OutcomeCounts', () => {
  it('counts every outcome per group and says which are excluded', () => {
    const other = {
      ...ATTACK,
      counts: counts({ attack_succeeded: 1, provider_error: 2 }),
    };
    render(
      <OutcomeCounts
        report={report({ attack_by_template: { 'tpl-1': other } })}
      />,
    );
    const cellsOf = (name: string) =>
      within(screen.getByRole('row', { name: new RegExp(`^${name} `) }))
        .getAllByRole('cell')
        .map((cell) => cell.textContent);
    expect(cellsOf('attack_succeeded')).toEqual(['denominator', '3', '1']);
    expect(cellsOf('attack_failed_target_resisted')).toEqual([
      'denominator',
      '1',
      '0',
    ]);
    expect(cellsOf('provider_error')).toEqual(['excluded', '0', '2']);
    expect(cellsOf('total')).toEqual(['', '4', '3']);
    expect(screen.getAllByRole('row')).toHaveLength(12);
  });
});
