// SPDX-License-Identifier: Apache-2.0
import { render, screen } from '@testing-library/react';
import { proportion, rate } from '../../testing/fixtures';
import KpiCard from './kpi-card';

describe('KpiCard', () => {
  it('shows the stored counts as the headline, the printed rate and its bar', () => {
    const { container } = render(
      <KpiCard
        label="Attack success"
        detail="per attempt"
        value={rate(3, 4, 0.30064, 0.9544, 'per_attempt')}
      />,
    );
    const card = screen.getByRole('group', { name: /^Attack success/ });
    expect(card.textContent).toContain('3 of 4');
    expect(container.querySelector('[data-rate]')?.textContent).toBe(
      '0.750 [0.300, 0.955] (n=4, per-attempt, 95% Wilson)',
    );
    expect(
      screen.getByRole('img', {
        name: 'Attack success, per attempt: 0.750 [0.300, 0.955] (n=4, per-attempt, 95% Wilson)',
      }),
    ).toBeTruthy();
    // The counts appear once, as the headline.
    expect(card.textContent?.split('3 of 4')).toHaveLength(2);
  });

  it.each([null, undefined])(
    'shows an absent value (%s) as absent, never 0',
    (value) => {
      const { container } = render(
        <KpiCard
          label="Judge recall"
          detail="unknown excluded"
          value={value}
        />,
      );
      const card = screen.getByRole('group', { name: /^Judge recall/ });
      expect(card.textContent).toBe(
        'Judge recall unknown excludedabsentabsent (denominator is 0)',
      );
      expect(card.textContent).not.toMatch(/\b0 of|0\.0/);
      expect(container.querySelector('svg')).toBeNull();
    },
  );

  it('keeps a proportion of 0 as the stored count, not absent', () => {
    render(
      <KpiCard
        label="Attempted"
        detail="control"
        value={proportion(0, 4, 0, 0.49)}
      />,
    );
    expect(
      screen.getByRole('group', { name: /^Attempted/ }).textContent,
    ).toContain('0 of 4');
  });
});
