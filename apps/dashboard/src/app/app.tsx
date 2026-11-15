// SPDX-License-Identifier: Apache-2.0
import { useState } from 'react';
import { FINDINGS, type Finding } from '../findings';
import {
  EVIDENCE_SENTENCE,
  INDEPENDENCE_SENTENCE,
  TERMS,
  runWarnings,
} from '../report-text';
import AttackSuccess from './attack-success/attack-success';
import AttemptCompletion from './attempt-completion/attempt-completion';
import ControlBaseRates from './control-base-rates/control-base-rates';
import Delivery from './delivery/delivery';
import Disagreements from './disagreements/disagreements';
import ExcludedTrials from './excluded-trials/excluded-trials';
import FindingPicker from './finding-picker/finding-picker';
import Items from './items/items';
import JudgeMatrix from './judge-matrix/judge-matrix';
import Limits from './limits/limits';
import OutcomeCounts from './outcome-counts/outcome-counts';
import RunFacts from './run-facts/run-facts';
import Utility from './utility/utility';
import styles from './app.module.css';

function FindingView({ finding }: { finding: Finding }) {
  const { report, calibration, manifest } = finding;
  const warnings = runWarnings(report);
  return (
    <article aria-label={`Finding ${finding.id}`}>
      <h2>{`Probo run report: ${report.facts.task}`}</h2>
      {warnings.length > 0 && (
        <div className="warnings" role="alert">
          {warnings.map((warning) => (
            <p key={warning}>
              <strong>{warning}</strong>
            </p>
          ))}
        </div>
      )}
      <div className="fixed-sentences">
        <p>{EVIDENCE_SENTENCE}</p>
        <p>{INDEPENDENCE_SENTENCE}</p>
      </div>
      <RunFacts report={report} manifest={manifest} />
      <p>{TERMS}</p>
      <AttackSuccess report={report} />
      <OutcomeCounts report={report} />
      <AttemptCompletion report={report} />
      <Utility report={report} />
      <ControlBaseRates report={report} />
      <Delivery report={report} />
      <Items report={report} />
      <Limits report={report} />
      <ExcludedTrials report={report} />
      {calibration === null ? (
        <section aria-label="Judge calibration">
          <h3>Judge calibration</h3>
          <p>This finding has no judge calibration.</p>
        </section>
      ) : (
        <>
          <JudgeMatrix calibration={calibration} />
          <Disagreements calibration={calibration} />
        </>
      )}
    </article>
  );
}

export interface AppProps {
  /** The findings to show, newest first; the published findings by default. */
  findings?: Finding[];
}

/** The page: a finding picker and the selected finding's report and calibration. */
export function App({ findings = FINDINGS }: AppProps) {
  const [selectedId, setSelectedId] = useState(findings[0]?.id ?? '');
  const finding = findings.find((f) => f.id === selectedId) ?? findings[0];
  return (
    <main className={styles['page']}>
      <header>
        <h1>Probo findings</h1>
        <p className="muted">
          Published Probo runs, bundled when the dashboard was built. Read only;
          nothing is fetched.
        </p>
        {finding !== undefined && (
          <FindingPicker
            ids={findings.map((f) => f.id)}
            selected={finding.id}
            onSelect={setSelectedId}
          />
        )}
      </header>
      {finding === undefined ? (
        <p>No findings are published.</p>
      ) : (
        <FindingView key={finding.id} finding={finding} />
      )}
    </main>
  );
}

export default App;
