// SPDX-License-Identifier: Apache-2.0
import type { RunSummary } from '../../generated/report';
import {
  OUTCOMES,
  attackGroups,
  countsTotal,
  isExcluded,
} from '../../report-text';
import StatusChip from '../status-chip/status-chip';

export interface OutcomeCountsProps {
  report: RunSummary;
}

/** Template trials by outcome, over all templates and per template (a subsection). */
export function OutcomeCounts({ report }: OutcomeCountsProps) {
  const groups = attackGroups(report);
  return (
    <section
      aria-label="Outcome counts (template trials)"
      className="subsection"
    >
      <h5>Outcome counts (template trials)</h5>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Outcome</th>
              <th scope="col">Per-attempt</th>
              {groups.map(([name]) => (
                <th scope="col" key={name} className="num">
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {OUTCOMES.map((outcome) => (
              <tr key={outcome}>
                <th scope="row">
                  <StatusChip value={outcome} />
                </th>
                <td>
                  <StatusChip
                    value={isExcluded(outcome) ? 'excluded' : 'denominator'}
                  />
                </td>
                {groups.map(([name, attack]) => (
                  <td key={name} className="num">
                    {attack.counts[outcome]}
                  </td>
                ))}
              </tr>
            ))}
            <tr className="total">
              <th scope="row">total</th>
              <td></td>
              {groups.map(([name, attack]) => (
                <td key={name} className="num">
                  {countsTotal(attack.counts)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default OutcomeCounts;
