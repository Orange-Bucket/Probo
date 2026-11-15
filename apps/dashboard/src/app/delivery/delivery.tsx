// SPDX-License-Identifier: Apache-2.0
import type { RunSummary } from '../../generated/report';
import ShareTable from '../share-table/share-table';

export interface DeliveryProps {
  report: RunSummary;
}

/** The share of template trials whose injected note reached the target. */
export function Delivery({ report }: DeliveryProps) {
  return (
    <section aria-label="Delivery">
      <h3>Delivery</h3>
      <ShareTable
        rows={[{ label: 'delivered, template trials', share: report.delivery }]}
      />
    </section>
  );
}

export default Delivery;
