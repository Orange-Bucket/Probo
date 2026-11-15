// SPDX-License-Identifier: Apache-2.0
import type { JudgeCalibration } from '../../generated/calibration';
import { calibrationConfig, formatLevel } from '../../format';
import {
  EXCLUSION_REASONS,
  INDEPENDENCE_NOTE,
  STATUSES,
} from '../../report-text';
import IntervalBar from '../interval-bar/interval-bar';

export interface JudgeMatrixProps {
  calibration: JudgeCalibration;
}

/**
 * The grader against the deterministic check: its confusion matrix with unknowns, base
 * rate, precision and both recalls, grader statuses and the trials left out, by reason.
 */
export function JudgeMatrix({ calibration }: JudgeMatrixProps) {
  const m = calibration.matrix;
  const unknown = m.unknown_positive + m.unknown_negative;
  const total = m.tp + m.fp + m.fn + m.tn + unknown;
  const excluded = EXCLUSION_REASONS.reduce(
    (sum, r) => sum + calibration.excluded[r],
    0,
  );
  const rates = [
    ['base rate', calibration.base_rate],
    ['precision (unknown excluded)', calibration.precision],
    ['recall (unknown excluded)', calibration.recall],
    ['recall (unknown counted as miss)', calibration.recall_unknown_as_miss],
  ] as const;
  return (
    <section aria-label="Judge calibration">
      <h3>Judge calibration</h3>
      <p className="code">
        {`grader ${calibration.judge} (${calibration.judge_model}, prompt ` +
          `v${calibration.prompt_version} sha256 ${calibration.prompt_sha256.slice(0, 12)}) ` +
          `against ${calibration.reference}, ${formatLevel(calibration.level)} Wilson intervals`}
      </p>
      <p className="code">{`grader generate config: ${calibrationConfig(calibration)}`}</p>
      <p>
        {`trials: ${total} pairs from ${calibration.sample_ids} sample ids over ` +
          `${calibration.epochs} epochs. ${INDEPENDENCE_NOTE}`}
      </p>
      <section aria-label="Confusion matrix">
        <h4>Confusion matrix</h4>
        <p className="code">
          {'judge vs deterministic check (positive = attack succeeded): ' +
            `pairs=${total} tp=${m.tp} fp=${m.fp} fn=${m.fn} tn=${m.tn} ` +
            `unknown=${unknown} (reference positive ${m.unknown_positive}, ` +
            `reference negative ${m.unknown_negative})`}
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <td></td>
                <th scope="col">judge yes</th>
                <th scope="col">judge no</th>
                <th scope="col">judge unknown</th>
                <th scope="col">total</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">reference positive</th>
                <td>{`tp ${m.tp}`}</td>
                <td>{`fn ${m.fn}`}</td>
                <td>{m.unknown_positive}</td>
                <td>{m.tp + m.fn + m.unknown_positive}</td>
              </tr>
              <tr>
                <th scope="row">reference negative</th>
                <td>{`fp ${m.fp}`}</td>
                <td>{`tn ${m.tn}`}</td>
                <td>{m.unknown_negative}</td>
                <td>{m.fp + m.tn + m.unknown_negative}</td>
              </tr>
              <tr>
                <th scope="row">total</th>
                <td>{m.tp + m.fp}</td>
                <td>{m.fn + m.tn}</td>
                <td>{unknown}</td>
                <td>{total}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
      <section aria-label="Grader rates">
        <h4>Grader rates</h4>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Rate</th>
                <th scope="col">Value</th>
              </tr>
            </thead>
            <tbody>
              {rates.map(([name, value]) => (
                <tr key={name}>
                  <th scope="row">{name}</th>
                  <td>
                    <IntervalBar value={value} label={name} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section aria-label="Grader statuses">
        <h4>Grader statuses</h4>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Status</th>
                <th scope="col">Scores</th>
              </tr>
            </thead>
            <tbody>
              {STATUSES.map((status) => (
                <tr key={status}>
                  <th scope="row">{status}</th>
                  <td>{calibration.statuses[status]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section aria-label="Excluded from the pairs">
        <h4>Excluded from the pairs</h4>
        <p>{`excluded: ${excluded}`}</p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Reason</th>
                <th scope="col">Trials</th>
              </tr>
            </thead>
            <tbody>
              {EXCLUSION_REASONS.map((reason) => (
                <tr key={reason}>
                  <th scope="row">{reason}</th>
                  <td>{calibration.excluded[reason]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}

export default JudgeMatrix;
