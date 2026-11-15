// SPDX-License-Identifier: Apache-2.0
import { useId } from 'react';
import type { Proportion, Rate } from '../../generated/report';
import IntervalBar from '../interval-bar/interval-bar';
import styles from './kpi-card.module.css';

/** The headline of a card whose value is absent (its denominator is 0): never 0. */
export const ABSENT_FIGURE = 'absent';

export interface KpiCardProps {
  /** What the card measures, as a short name. */
  label: string;
  /** What it is measured over, shown beside the name. */
  detail: string;
  /** The rate or proportion; null or undefined when its denominator is 0. */
  value: Proportion | Rate | null | undefined;
  /** Draws the headline figure in the accent colour. */
  emphasis?: boolean;
}

/**
 * One headline figure: `successes of trials` from the stored counts, the rate exactly as the
 * reports print it, and its interval bar. Nothing is computed beyond what the report has.
 */
export function KpiCard({ label, detail, value, emphasis }: KpiCardProps) {
  const labelId = useId();
  const absent = value === null || value === undefined;
  const figureClass = [
    styles['figure'],
    emphasis ? styles['emphasis'] : '',
    absent ? styles['absent'] : '',
  ]
    .filter(Boolean)
    .join(' ');
  return (
    <div role="group" aria-labelledby={labelId} className={styles['card']}>
      <h4 id={labelId} className={styles['label']}>
        {label} <span className={styles['detail']}>{detail}</span>
      </h4>
      <div className={figureClass}>
        {absent ? ABSENT_FIGURE : `${value.successes} of ${value.trials}`}
      </div>
      <IntervalBar value={value} label={`${label}, ${detail}`} variant="card" />
    </div>
  );
}

export default KpiCard;
