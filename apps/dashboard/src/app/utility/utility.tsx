// SPDX-License-Identifier: Apache-2.0
import type { RunSummary } from '../../generated/report';
import ShareTable, { type ShareRow } from '../share-table/share-table';

export interface UtilityProps {
  report: RunSummary;
}

/** task_completed for control and template trials, overall and per user task. */
export function Utility({ report }: UtilityProps) {
  const rows: ShareRow[] = [
    {
      label: 'task_completed true, control trials',
      share: report.utility_control,
    },
    {
      label: 'task_completed true, template trials',
      share: report.utility_template,
    },
  ];
  for (const task of report.utility_by_user_task) {
    rows.push(
      {
        label: `task_completed true, control trials, ${task.user_task}`,
        share: task.control,
      },
      {
        label: `task_completed true, template trials, ${task.user_task}`,
        share: task.template,
      },
    );
  }
  return (
    <section aria-label="Utility">
      <h3>Utility</h3>
      <ShareTable rows={rows} />
    </section>
  );
}

export default Utility;
