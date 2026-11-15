// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import { report, share } from '../../testing/fixtures';
import Delivery from './delivery';

describe('Delivery', () => {
  it('shows the delivered share of template trials', () => {
    render(<Delivery report={report()} />);
    const row = screen.getByRole('row', {
      name: /^delivered, template trials/,
    });
    expect(
      within(row).getByText('1.000 [0.510, 1.000] (n=4, 95% Wilson)'),
    ).toBeTruthy();
  });

  it('shows an absent share as absent', () => {
    render(<Delivery report={report({ delivery: share(null) })} />);
    expect(screen.getByText('absent (denominator is 0)')).toBeTruthy();
  });
});
