// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import { proportion, share } from '../../testing/fixtures';
import ShareTable from './share-table';

describe('ShareTable', () => {
  it('shows each share with its trials, not applicable and missing counts', () => {
    render(
      <ShareTable
        rows={[
          {
            label: 'present',
            share: share(proportion(1, 4, 0.0456, 0.6994), 2, 1),
          },
          { label: 'nothing to count', share: share(null, 3) },
        ]}
      />,
    );
    const present = screen.getByRole('row', { name: /^present/ });
    const cells = within(present).getAllByRole('cell');
    expect(cells.map((cell) => cell.textContent)).toEqual([
      '7',
      '0.250 [0.045, 0.700] (n=4, 95% Wilson) 1 of 4',
      '2',
      '1',
    ]);
    const absent = screen.getByRole('row', { name: /^nothing to count/ });
    expect(within(absent).getByText('absent (denominator is 0)')).toBeTruthy();
    expect(within(absent).queryByRole('img')).toBeNull();
  });
});
