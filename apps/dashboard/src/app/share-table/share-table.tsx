// SPDX-License-Identifier: Apache-2.0
import type { CheckShare } from '../../generated/report';
import IntervalBar from '../interval-bar/interval-bar';

export interface ShareRow {
  /** The row's quantity, as the report labels it. */
  label: string;
  share: CheckShare;
}

export interface ShareTableProps {
  rows: ShareRow[];
}

/** Shares of trials whose value is true, with not applicable and missing counted apart. */
export function ShareTable({ rows }: ShareTableProps) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th scope="col">Quantity</th>
            <th scope="col" className="num">
              Trials
            </th>
            <th scope="col">Share true</th>
            <th scope="col" className="num">
              Not applicable
            </th>
            <th scope="col" className="num">
              Missing
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ label, share }) => (
            <tr key={label}>
              <th scope="row">{label}</th>
              <td className="num">{share.trials}</td>
              <td>
                <IntervalBar value={share.value} label={label} />
              </td>
              <td className="num">{share.not_applicable}</td>
              <td className="num">{share.missing}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ShareTable;
