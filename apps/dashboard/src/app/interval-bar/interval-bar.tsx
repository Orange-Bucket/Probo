// SPDX-License-Identifier: Apache-2.0
import type { Proportion, Rate } from '../../generated/report';
import { renderOptional } from '../../format';
import styles from './interval-bar.module.css';

export interface IntervalBarProps {
  /** The rate or proportion; null or undefined when its denominator is 0. */
  value: Proportion | Rate | null | undefined;
  /** What the value measures, for the bar's accessible name. */
  label: string;
}

function percent(value: number): number {
  return Math.min(100, Math.max(0, value * 100));
}

/**
 * A rate as the report prints it (estimate, interval, n, estimand and level), its counts as
 * `x of n`, and a plain SVG bar of the interval with a tick at the estimate. An absent rate
 * is the text `absent (denominator is 0)` with no counts and no bar.
 */
export function IntervalBar({ value, label }: IntervalBarProps) {
  const text = renderOptional(value);
  if (value === null || value === undefined) {
    return (
      <span className={styles['rate']}>
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
    <span className={styles['rate']}>
      <span data-rate="">{text}</span>{' '}
      <span className={styles['counts']}>
        {value.successes} of {value.trials}
      </span>
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
          y={2}
          width={Math.max(upper - lower, 0.5)}
          height={8}
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
