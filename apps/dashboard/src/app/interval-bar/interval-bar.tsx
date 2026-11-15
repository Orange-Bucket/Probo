// SPDX-License-Identifier: Apache-2.0
import type { Proportion, Rate } from '../../generated/report';
import { renderOptional } from '../../format';
import styles from './interval-bar.module.css';

export interface IntervalBarProps {
  /** The rate or proportion; null or undefined when its denominator is 0. */
  value: Proportion | Rate | null | undefined;
  /** What the value measures, for the bar's accessible name. */
  label: string;
  /**
   * `table` (the default) prints the counts beside the rate; `card` leaves them out, for a
   * card that shows them as its headline figure, and draws a wider bar.
   */
  variant?: 'table' | 'card';
}

function percent(value: number): number {
  return Math.min(100, Math.max(0, value * 100));
}

/**
 * A rate as the report prints it (estimate, interval, n, estimand and level), its counts as
 * `x of n`, and a plain SVG bar of the interval with a tick at the estimate. An absent rate
 * is the text `absent (denominator is 0)` with no counts and no bar.
 */
export function IntervalBar({
  value,
  label,
  variant = 'table',
}: IntervalBarProps) {
  const text = renderOptional(value);
  const rateClass =
    variant === 'card' ? `${styles['rate']} ${styles['card']}` : styles['rate'];
  if (value === null || value === undefined) {
    return (
      <span className={rateClass}>
        <span className={styles['absent']} data-rate="">
          {text}
        </span>
      </span>
    );
  }
  const lower = percent(value.interval.lower);
  const upper = percent(value.interval.upper);
  const estimate = percent(value.estimate);
  return (
    <span className={rateClass}>
      <span className={styles['text']} data-rate="">
        {text}
      </span>
      {variant === 'table' && (
        <>
          {' '}
          <span className={styles['counts']} data-counts="">
            {value.successes} of {value.trials}
          </span>
        </>
      )}
      <svg
        className={styles['bar']}
        viewBox="0 0 100 12"
        preserveAspectRatio="none"
        role="img"
        aria-label={`${label}: ${text}`}
        focusable="false"
      >
        <rect className={styles['track']} x={0} y={5} width={100} height={2} />
        <rect
          className={styles['interval']}
          x={lower}
          y={3}
          width={Math.max(upper - lower, 0.5)}
          height={6}
        />
        <rect
          className={styles['estimate']}
          x={Math.min(Math.max(estimate - 0.5, 0), 99)}
          y={0}
          width={1}
          height={12}
        />
      </svg>
    </span>
  );
}

export default IntervalBar;
