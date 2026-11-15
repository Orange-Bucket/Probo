// SPDX-License-Identifier: Apache-2.0
import type { JudgeCalibration } from '../../generated/calibration';
import { trialRef } from '../../format';
import SectionCard from '../section-card/section-card';
import styles from './disagreements.module.css';

export interface DisagreementsProps {
  calibration: JudgeCalibration;
}

/** The trials where the grader and the check disagree, or the grader said unknown. */
export function Disagreements({ calibration }: DisagreementsProps) {
  const lists = [
    ['false positives', calibration.false_positives],
    ['false negatives', calibration.false_negatives],
    ['unknown', calibration.unknowns],
  ] as const;
  return (
    <SectionCard section="disagreements">
      <p className="muted">Trials as sample id@epoch, in log order.</p>
      {lists.map(([name, trials]) => (
        <section key={name} aria-label={name} className="subsection">
          <h5>{`${name} (${trials.length})`}</h5>
          {trials.length === 0 ? (
            <p>none</p>
          ) : (
            <ul className={styles['trials']}>
              {trials.map((trial) => (
                <li key={trialRef(trial)} className={`code ${styles['trial']}`}>
                  {trialRef(trial)}
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
    </SectionCard>
  );
}

export default Disagreements;
