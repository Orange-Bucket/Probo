// SPDX-License-Identifier: Apache-2.0
import type { RunSummary } from '../../generated/report';
import { countsExcluded, countsTotal } from '../../report-text';

export interface ItemsProps {
  report: RunSummary;
}

const TITLE = 'Items (user task x template, over epochs)';

/** Attack successes of each item (user task x template) over its epochs. */
export function Items({ report }: ItemsProps) {
  return (
    <section aria-label={TITLE}>
      <h3>{TITLE}</h3>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">User task</th>
              <th scope="col">Template</th>
              <th scope="col">attack_succeeded</th>
              <th scope="col">In per-attempt denominator</th>
              <th scope="col">Excluded</th>
            </tr>
          </thead>
          <tbody>
            {report.items.map((item) => {
              const trials = countsTotal(item.counts);
              const excluded = countsExcluded(item.counts);
              return (
                <tr key={`${item.user_task}\n${item.template_id}`}>
                  <th scope="row">{item.user_task}</th>
                  <td>{item.template_id}</td>
                  <td>{`${item.counts.attack_succeeded} of ${trials}`}</td>
                  <td>{trials - excluded}</td>
                  <td>{excluded}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default Items;
