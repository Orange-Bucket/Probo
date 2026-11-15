// SPDX-License-Identifier: Apache-2.0
import { Fragment, type ReactNode } from 'react';
import type { Finding } from '../../findings';
import {
  EVIDENCE_SENTENCE,
  INDEPENDENCE_SENTENCE,
  runWarnings,
} from '../../report-text';
import { findingGroups, type GroupedSectionKey } from '../../sections';
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
 * What each section of a finding renders: a fixed map, so the page places sections exactly
 * where `GROUPS` (which the navigation also reads) puts them. The overview is not here: it
 * sits above the groups.
 */
const SECTION_VIEWS: Record<
  GroupedSectionKey,
  (finding: Finding) => ReactNode
> = {
  run: ({ report, manifest }) => (
    <RunFacts report={report} manifest={manifest} part="run" />
  ),
  trials: ({ report, manifest }) => (
    <RunFacts report={report} manifest={manifest} part="trials" />
  ),
  published: ({ report, manifest }) => (
    <RunFacts report={report} manifest={manifest} part="published" />
  ),
  'attack-success': ({ report }) => <AttackSuccess report={report} />,
  'attempt-completion': ({ report }) => <AttemptCompletion report={report} />,
  utility: ({ report }) => <Utility report={report} />,
  'control-base-rates': ({ report }) => <ControlBaseRates report={report} />,
  delivery: ({ report }) => <Delivery report={report} />,
  items: ({ report }) => <Items report={report} />,
  limits: ({ report }) => <Limits report={report} />,
  'excluded-trials': ({ report }) => <ExcludedTrials report={report} />,
  'judge-calibration': ({ calibration }) =>
    calibration === null ? (
      <SectionCard section="judge-calibration">
        <p>This finding has no judge calibration.</p>
      </SectionCard>
    ) : (
      <JudgeMatrix calibration={calibration} />
    ),
  disagreements: ({ calibration }) =>
    calibration === null ? null : <Disagreements calibration={calibration} />,
};

/**
 * One finding: its title, warnings and the two fixed sentences, the overview cards, and
 * every section of the report and calibration, grouped under plain headings as `GROUPS`
 * lists them. Every section is always in the document; the navigation only scrolls to it.
 */
export function FindingView({ finding }: FindingViewProps) {
  const { report, calibration } = finding;
  const warnings = runWarnings(report);
  const title = `Probo run report: ${report.facts.task}`;
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
          <div className={styles['stack']}>
            {group.sections.map((section) => (
              <Fragment key={section}>
                {SECTION_VIEWS[section](finding)}
              </Fragment>
            ))}
          </div>
        </div>
      ))}
    </article>
  );
}

export default FindingView;
