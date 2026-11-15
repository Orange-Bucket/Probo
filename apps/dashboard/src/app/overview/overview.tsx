// SPDX-License-Identifier: Apache-2.0
import type { JudgeCalibration } from '../../generated/calibration';
import type { RunSummary } from '../../generated/report';
import { SECTIONS } from '../../sections';
import KpiCard, { type KpiCardProps } from '../kpi-card/kpi-card';
import styles from './overview.module.css';

export interface OverviewProps {
  report: RunSummary;
  calibration: JudgeCalibration | null;
}

/** The headline cards of a finding; every value is one the report or calibration prints. */
export function overviewCards(
  report: RunSummary,
  calibration: JudgeCalibration | null,
): KpiCardProps[] {
  const cards: KpiCardProps[] = [
    {
      label: 'Attack success',
      detail: 'per attempt, all templates',
      value: report.attack.per_attempt,
      emphasis: true,
    },
    {
      label: 'Attempted',
      detail: 'delivered template trials',
      value: report.attempted.value,
    },
    {
      label: 'Benign utility',
      detail: 'control trials',
      value: report.utility_control.value,
    },
    {
      label: 'Benign utility',
      detail: 'template trials',
      value: report.utility_template.value,
    },
  ];
  if (calibration !== null) {
    cards.push(
      {
        label: 'Judge precision',
        detail: 'unknown excluded',
        value: calibration.precision,
      },
      {
        label: 'Judge recall',
        detail: 'unknown excluded',
        value: calibration.recall,
      },
    );
  }
  return cards;
}

/** The overview region at the top of a finding: a grid of headline cards. */
export function Overview({ report, calibration }: OverviewProps) {
  const { id, title, caption } = SECTIONS.overview;
  const cards = overviewCards(report, calibration);
  return (
    <section id={id} aria-label={title} className={styles['overview']}>
      <div className={styles['header']}>
        <h3 className={styles['title']} tabIndex={-1}>
          {title}
        </h3>
        <div className={styles['caption']}>{caption}</div>
      </div>
      <div
        className={`${styles['grid']} ${calibration === null ? styles['four'] : styles['six']}`}
      >
        {cards.map((card) => (
          <KpiCard key={`${card.label}\n${card.detail}`} {...card} />
        ))}
      </div>
    </section>
  );
}

export default Overview;
