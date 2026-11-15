// SPDX-License-Identifier: Apache-2.0
import type { RunSummary } from '../../generated/report';
import SectionCard from '../section-card/section-card';
import ShareTable from '../share-table/share-table';

export interface AttemptCompletionProps {
  report: RunSummary;
}

/** Attempted and completed shares over delivered template trials, and their 2x2 table. */
export function AttemptCompletion({ report }: AttemptCompletionProps) {
  const table = report.attempt_completion;
  const total =
    table.sent_and_leaked +
    table.sent_not_leaked +
    table.leaked_not_sent +
    table.neither;
  return (
    <SectionCard section="attempt-completion">
      <p>{`Delivered template trials: ${report.delivered}.`}</p>
      <ShareTable
        rows={[
          {
            label: 'attempted, delivered template trials',
            share: report.attempted,
          },
          {
            label: 'completed, delivered template trials',
            share: report.completed,
          },
        ]}
      />
      <p>{`Delivered template trials with both values true or false: ${total}.`}</p>
      <div className="table-scroll table-fit">
        <table>
          <thead>
            <tr>
              <td></td>
              <th scope="col" className="num">
                completed
              </th>
              <th scope="col" className="num">
                not completed
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">attempted</th>
              <td className="num">{table.sent_and_leaked}</td>
              <td className="num">{table.sent_not_leaked}</td>
            </tr>
            <tr>
              <th scope="row">not attempted</th>
              <td className="num">{table.leaked_not_sent}</td>
              <td className="num">{table.neither}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}

export default AttemptCompletion;
