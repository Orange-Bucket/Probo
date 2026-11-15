// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import { calibration } from '../../testing/fixtures';
import Disagreements from './disagreements';

describe('Disagreements', () => {
  it('lists the disagreeing and unknown trials as sample id@epoch', () => {
    render(
      <Disagreements
        calibration={calibration({
          false_positives: [
            ['a/x', 1],
            [7, 3],
          ],
          false_negatives: [],
          unknowns: [['b/y', 2]],
        })}
      />,
    );
    const items = (name: string) =>
      within(screen.getByRole('region', { name }))
        .queryAllByRole('listitem')
        .map((item) => item.textContent);
    expect(
      screen.getByRole('heading', { name: 'false positives (2)' }),
    ).toBeTruthy();
    expect(items('false positives')).toEqual(['a/x@1', '7@3']);
    expect(items('false negatives')).toEqual([]);
    expect(
      within(screen.getByRole('region', { name: 'false negatives' })).getByText(
        'none',
      ),
    ).toBeTruthy();
    expect(items('unknown')).toEqual(['b/y@2']);
  });
});
