// SPDX-License-Identifier: Apache-2.0
import { render, screen } from '@testing-library/react';
import { proportion, rate } from '../../testing/fixtures';
import IntervalBar from './interval-bar';

describe('IntervalBar', () => {
  it('prints the rate as the report does, with its counts', () => {
    render(
      <IntervalBar
        value={rate(3, 4, 0.30064, 0.9544, 'per_attempt')}
        label="rate"
      />,
    );
    expect(
      screen.getByText('0.750 [0.300, 0.955] (n=4, per-attempt, 95% Wilson)'),
    ).toBeTruthy();
    expect(screen.getByText('3 of 4')).toBeTruthy();
  });

  it('draws the interval as inline SVG with an accessible label', () => {
    const { container } = render(
      <IntervalBar value={proportion(1, 4, 0.1, 0.6)} label="share true" />,
    );
    const bar = screen.getByRole('img', {
      name: 'share true: 0.250 [0.100, 0.600] (n=4, 95% Wilson)',
    });
    expect(bar.tagName.toLowerCase()).toBe('svg');
    const rects = container.querySelectorAll('rect');
    expect(rects).toHaveLength(3);
    const interval = rects[1];
    expect(Number(interval.getAttribute('x'))).toBeCloseTo(10);
    expect(Number(interval.getAttribute('width'))).toBeCloseTo(50);
    expect(Number(rects[2].getAttribute('x'))).toBeCloseTo(24.5);
  });

  it('shows an absent rate as absent, with no bar and no zero', () => {
    const { container } = render(<IntervalBar value={null} label="rate" />);
    expect(container.textContent).toBe('absent (denominator is 0)');
    expect(container.querySelector('svg')).toBeNull();
    expect(container.textContent).not.toMatch(/0\.0/);
  });

  it('leaves the counts out in a card, keeping the printed rate and the bar', () => {
    const { container } = render(
      <IntervalBar
        value={proportion(1, 4, 0.1, 0.6)}
        label="share true"
        variant="card"
      />,
    );
    expect(container.querySelector('[data-rate]')?.textContent).toBe(
      '0.250 [0.100, 0.600] (n=4, 95% Wilson)',
    );
    expect(screen.queryByText('1 of 4')).toBeNull();
    expect(
      screen.getByRole('img', {
        name: 'share true: 0.250 [0.100, 0.600] (n=4, 95% Wilson)',
      }),
    ).toBeTruthy();
  });
});
