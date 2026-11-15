// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import { counts, report } from '../../testing/fixtures';
import Items from './items';

describe('Items', () => {
  it('shows successes of each item over its epochs', () => {
    render(
      <Items
        report={report({
          items: [
            {
              user_task: 'task-a',
              template_id: 'tpl-1',
              counts: counts({
                attack_succeeded: 2,
                attack_failed_target_resisted: 1,
                not_delivered: 1,
              }),
            },
          ],
        })}
      />,
    );
    const row = screen.getByRole('row', { name: /^task-a/ });
    expect(
      within(row)
        .getAllByRole('cell')
        .map((cell) => cell.textContent),
    ).toEqual(['tpl-1', '2 of 4', '3', '1']);
  });
});
