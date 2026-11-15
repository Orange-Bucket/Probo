// SPDX-License-Identifier: Apache-2.0
import type { RunSummary } from '../../generated/report';
import { countsExcluded, countsTotal } from '../../report-text';
import SectionCard from '../section-card/section-card';

export interface ItemsProps {
  report: RunSummary;
}

/** Attack successes of each item (user task x template) over its epochs. */
export function Items({ report }: ItemsProps) {
  return (
    <SectionCard section="items">
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">User task</th>
              <th scope="col">Template</th>
              <th scope="col" className="num">
                attack_succeeded
              </th>
              <th scope="col" className="num">
                In per-attempt denominator
              </th>
              <th scope="col" className="num">
                Excluded
              </th>
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
                  <td className="num">{`${item.counts.attack_succeeded} of ${trials}`}</td>
                  <td className="num">{trials - excluded}</td>
                  <td className="num">{excluded}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}

export default Items;
