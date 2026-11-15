// SPDX-License-Identifier: Apache-2.0
import type { RunSummary } from '../../generated/report';
import {
  OUTCOMES,
  attackGroups,
  countsTotal,
  isExcluded,
} from '../../report-text';

export interface OutcomeCountsProps {
  report: RunSummary;
}

/** Template trials by outcome, over all templates and per template. */
export function OutcomeCounts({ report }: OutcomeCountsProps) {
  const groups = attackGroups(report);
  return (
    <section aria-label="Outcome counts (template trials)">
      <h3>Outcome counts (template trials)</h3>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Outcome</th>
              <th scope="col">Per-attempt</th>
              {groups.map(([name]) => (
                <th scope="col" key={name}>
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {OUTCOMES.map((outcome) => (
              <tr key={outcome}>
                <th scope="row">{outcome}</th>
                <td>{isExcluded(outcome) ? 'excluded' : 'denominator'}</td>
                {groups.map(([name, attack]) => (
                  <td key={name}>{attack.counts[outcome]}</td>
                ))}
              </tr>
            ))}
            <tr>
              <th scope="row">total</th>
              <td></td>
              {groups.map(([name, attack]) => (
                <td key={name}>{countsTotal(attack.counts)}</td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default OutcomeCounts;
