// SPDX-License-Identifier: Apache-2.0
import type { RunSummary } from '../../generated/report';
import { OUTCOMES, countsTotal } from '../../report-text';
import SectionCard from '../section-card/section-card';
import ShareTable from '../share-table/share-table';

export interface ControlBaseRatesProps {
  report: RunSummary;
}

/** Control trials: their error labels and how often they leaked or sent anyway. */
export function ControlBaseRates({ report }: ControlBaseRatesProps) {
  const control = report.control;
  const errors = OUTCOMES.filter((o) => control.errors[o] > 0).map(
    (o) => `${o}=${control.errors[o]}`,
  );
  const summary =
    `Control trials: ${control.trials}. With an error label: ${countsTotal(control.errors)}` +
    (errors.length > 0 ? ` (${errors.join(', ')}).` : '.');
  return (
    <SectionCard section="control-base-rates">
      <p>{summary}</p>
      <ShareTable
        rows={[
          { label: 'completed, control trials', share: control.record_leaked },
          {
            label: 'attempted, control trials',
            share: control.sent_to_watched_address,
          },
        ]}
      />
    </SectionCard>
  );
}

export default ControlBaseRates;
