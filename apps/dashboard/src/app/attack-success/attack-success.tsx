// SPDX-License-Identifier: Apache-2.0
import type { RunSummary } from '../../generated/report';
import { attackGroups, countsExcluded, countsTotal } from '../../report-text';
import IntervalBar from '../interval-bar/interval-bar';
import OutcomeCounts from '../outcome-counts/outcome-counts';
import SectionCard from '../section-card/section-card';

export interface AttackSuccessProps {
  report: RunSummary;
}

/**
 * Attack success over all templates and per template, per attempt and per trial, with the
 * outcome counts as a subsection, as in the report.
 */
export function AttackSuccess({ report }: AttackSuccessProps) {
  return (
    <SectionCard section="attack-success">
      <p>Template trials only.</p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Template</th>
              <th scope="col" className="num">
                Trials
              </th>
              <th scope="col" className="num">
                Excluded
              </th>
              <th scope="col">Per-attempt rate</th>
              <th scope="col">Per-trial rate</th>
            </tr>
          </thead>
          <tbody>
            {attackGroups(report).map(([name, attack]) => (
              <tr key={name}>
                <th scope="row">{name}</th>
                <td className="num">{countsTotal(attack.counts)}</td>
                <td className="num">{countsExcluded(attack.counts)}</td>
                <td>
                  <IntervalBar
                    value={attack.per_attempt}
                    label={`${name}, per-attempt rate`}
                  />
                </td>
                <td>
                  <IntervalBar
                    value={attack.per_trial}
                    label={`${name}, per-trial rate`}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <OutcomeCounts report={report} />
    </SectionCard>
  );
}

export default AttackSuccess;
