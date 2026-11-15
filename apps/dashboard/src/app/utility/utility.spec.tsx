// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import { report } from '../../testing/fixtures';
import Utility from './utility';

describe('Utility', () => {
  it('shows control and template utility, overall and per user task', () => {
    render(<Utility report={report()} />);
    const labels = screen
      .getAllByRole('rowheader')
      .map((header) => header.textContent);
    expect(labels).toEqual([
      'task_completed true, control trials',
      'task_completed true, template trials',
      'task_completed true, control trials, task-a',
      'task_completed true, template trials, task-a',
    ]);
    const absent = screen.getByRole('row', { name: /template trials, task-a/ });
    expect(within(absent).getByText('absent (denominator is 0)')).toBeTruthy();
    expect(within(absent).getAllByRole('cell')[2].textContent).toBe('4');
  });
});
