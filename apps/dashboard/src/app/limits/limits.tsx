// SPDX-License-Identifier: Apache-2.0
import type { RunSummary } from '../../generated/report';
import { LIMIT_SENTENCE } from '../../report-text';

export interface LimitsProps {
  report: RunSummary;
}

function byLimitType(limits: Record<string, number | undefined>): string {
  return (
    Object.entries(limits)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
      .map(([kind, count]) => `${kind}=${count}`)
      .join(', ') || '-'
  );
}

/** Trials that hit a limit, by kind and outcome, and the resisted trials that were cut off. */
export function Limits({ report }: LimitsProps) {
  const cut = report.labels.filter(
    (label) =>
      label.outcome === 'attack_failed_target_resisted' && label.limit !== null,
  );
  return (
    <section aria-label="Limits">
      <h3>Limits</h3>
      <p>{LIMIT_SENTENCE}</p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Kind</th>
              <th scope="col">Outcome</th>
              <th scope="col">Trials</th>
              <th scope="col">Hit a limit</th>
              <th scope="col">By limit type</th>
            </tr>
          </thead>
          <tbody>
            {report.limits.map((row) => {
              const limited = Object.values(row.limits).reduce<number>(
                (sum, count) => sum + (count ?? 0),
                0,
              );
              return (
                <tr key={`${row.kind}\n${row.outcome}`}>
                  <th scope="row">{row.kind}</th>
                  <td>{row.outcome ?? 'no outcome'}</td>
                  <td>{row.trials}</td>
                  <td>{limited}</td>
                  <td>{byLimitType(row.limits)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p>{`Resisted trials that hit a limit: ${cut.length}.`}</p>
      {cut.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Sample</th>
                <th scope="col">Epoch</th>
                <th scope="col">Limit</th>
                <th scope="col">Evidence</th>
              </tr>
            </thead>
            <tbody>
              {cut.map((label) => (
                <tr key={`${label.sample_id}@${label.epoch}`}>
                  <th scope="row" className="code">
                    {label.sample_id}
                  </th>
                  <td>{label.epoch}</td>
                  <td>{label.limit}</td>
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

export default Limits;
