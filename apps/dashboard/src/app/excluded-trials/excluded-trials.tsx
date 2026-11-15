// SPDX-License-Identifier: Apache-2.0
import type { RunSummary } from '../../generated/report';
import { GRADER_SENTENCE, isExcluded } from '../../report-text';

export interface ExcludedTrialsProps {
  report: RunSummary;
}

/**
 * Template trials outside the per-attempt denominator and control trials with an error
 * label, with the evidence for each label as plain text.
 */
export function ExcludedTrials({ report }: ExcludedTrialsProps) {
  const rows = report.labels.filter(
    (label) => label.outcome !== null && isExcluded(label.outcome),
  );
  return (
    <section aria-label="Excluded trials">
      <h3>Excluded trials</h3>
      <p>
        {'Template trials outside the per-attempt denominator, and control trials with an ' +
          `error label: ${rows.length}.`}
      </p>
      <p>{GRADER_SENTENCE}</p>
      {rows.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Sample</th>
                <th scope="col">Epoch</th>
                <th scope="col">Kind</th>
                <th scope="col">Outcome</th>
                <th scope="col">Evidence</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((label) => (
                <tr key={`${label.sample_id}@${label.epoch}`}>
                  <th scope="row" className="code">
                    {label.sample_id}
                  </th>
                  <td>{label.epoch}</td>
                  <td>{label.kind}</td>
                  <td>{label.outcome}</td>
                  <td className="code">{label.evidence.join('; ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default ExcludedTrials;
