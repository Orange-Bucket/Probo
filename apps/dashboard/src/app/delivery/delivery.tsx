// SPDX-License-Identifier: Apache-2.0
import type { RunSummary } from '../../generated/report';
import SectionCard from '../section-card/section-card';
import ShareTable from '../share-table/share-table';

export interface DeliveryProps {
  report: RunSummary;
}

/** The share of template trials whose injected note reached the target. */
export function Delivery({ report }: DeliveryProps) {
  return (
    <SectionCard section="delivery">
      <ShareTable
        rows={[{ label: 'delivered, template trials', share: report.delivery }]}
      />
    </SectionCard>
  );
}

export default Delivery;
