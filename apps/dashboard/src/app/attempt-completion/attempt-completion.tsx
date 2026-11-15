// SPDX-License-Identifier: Apache-2.0
import type { RunSummary } from '../../generated/report';
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
    <section aria-label="Attempted and completed">
      <h3>Attempted and completed</h3>
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
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <td></td>
              <th scope="col">completed</th>
              <th scope="col">not completed</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">attempted</th>
              <td>{table.sent_and_leaked}</td>
              <td>{table.sent_not_leaked}</td>
            </tr>
            <tr>
              <th scope="row">not attempted</th>
              <td>{table.leaked_not_sent}</td>
              <td>{table.neither}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default AttemptCompletion;
