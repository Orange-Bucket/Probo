// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from 'react';
import type { Finding } from '../../findings';
import {
  EVIDENCE_SENTENCE,
  INDEPENDENCE_SENTENCE,
  runWarnings,
} from '../../report-text';
import { findingGroups, type GroupKey } from '../../sections';
import AttackSuccess from '../attack-success/attack-success';
import AttemptCompletion from '../attempt-completion/attempt-completion';
import ControlBaseRates from '../control-base-rates/control-base-rates';
import Delivery from '../delivery/delivery';
import Disagreements from '../disagreements/disagreements';
import ExcludedTrials from '../excluded-trials/excluded-trials';
import Icon from '../icon/icon';
import Items from '../items/items';
import JudgeMatrix from '../judge-matrix/judge-matrix';
import Limits from '../limits/limits';
import Notice from '../notice/notice';
import Overview from '../overview/overview';
import RunFacts from '../run-facts/run-facts';
import SectionCard from '../section-card/section-card';
import Utility from '../utility/utility';
import styles from './finding-view.module.css';

export interface FindingViewProps {
  finding: Finding;
}

/**
 * One finding: its title, warnings and the two fixed sentences, the overview cards, and
 * every section of the report and calibration, grouped under plain headings. Every section
 * is always in the document; the navigation only scrolls to it.
 */
export function FindingView({ finding }: FindingViewProps) {
  const { report, calibration, manifest } = finding;
  const warnings = runWarnings(report);
  const title = `Probo run report: ${report.facts.task}`;
  const content: Record<GroupKey, ReactNode> = {
    setup: <RunFacts report={report} manifest={manifest} />,
    results: (
      <>
        <AttackSuccess report={report} />
        <AttemptCompletion report={report} />
        <Utility report={report} />
        <ControlBaseRates report={report} />
        <Delivery report={report} />
      </>
    ),
    breakdown: (
      <>
        <Items report={report} />
        <Limits report={report} />
        <ExcludedTrials report={report} />
      </>
    ),
    judge:
      calibration === null ? (
        <SectionCard section="judge-calibration">
          <p>This finding has no judge calibration.</p>
        </SectionCard>
      ) : (
        <>
          <JudgeMatrix calibration={calibration} />
          <Disagreements calibration={calibration} />
        </>
      ),
  };
  return (
    <article aria-label={`Finding ${finding.id}`} className={styles['finding']}>
      <h2 className={styles['title']}>{title}</h2>
      {warnings.length > 0 && (
        <Notice tone="warning">
          {warnings.map((warning) => (
            <p key={warning}>
              <strong>{warning}</strong>
            </p>
          ))}
        </Notice>
      )}
      <Notice tone="info">
        <p>{EVIDENCE_SENTENCE}</p>
        <p>{INDEPENDENCE_SENTENCE}</p>
      </Notice>
      <Overview report={report} calibration={calibration} />
      {findingGroups(finding).map((group) => (
        <div key={group.key} className={styles['group']}>
          <h3 className={styles['groupTitle']}>
            <Icon name={group.key} className={styles['groupIcon']} />
            {group.title}
          </h3>
          <div className={styles['stack']}>{content[group.key]}</div>
        </div>
      ))}
    </article>
  );
}

export default FindingView;
