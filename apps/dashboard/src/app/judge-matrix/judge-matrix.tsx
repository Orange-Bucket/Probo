// SPDX-License-Identifier: Apache-2.0
import type { JudgeCalibration } from '../../generated/calibration';
import { calibrationConfig, formatLevel } from '../../format';
import {
  EXCLUSION_REASONS,
  INDEPENDENCE_NOTE,
  STATUSES,
} from '../../report-text';
import IntervalBar from '../interval-bar/interval-bar';
import SectionCard from '../section-card/section-card';

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
    <SectionCard section="judge-calibration">
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
      <div className="subgrid">
        <section aria-label="Confusion matrix" className="subsection">
          <h5>Confusion matrix</h5>
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
                  <th scope="col" className="num">
                    judge yes
                  </th>
                  <th scope="col" className="num">
                    judge no
                  </th>
                  <th scope="col" className="num">
                    judge unknown
                  </th>
                  <th scope="col" className="num">
                    total
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">reference positive</th>
                  <td className="num">{`tp ${m.tp}`}</td>
                  <td className="num">{`fn ${m.fn}`}</td>
                  <td className="num">{m.unknown_positive}</td>
                  <td className="num">{m.tp + m.fn + m.unknown_positive}</td>
                </tr>
                <tr>
                  <th scope="row">reference negative</th>
                  <td className="num">{`fp ${m.fp}`}</td>
                  <td className="num">{`tn ${m.tn}`}</td>
                  <td className="num">{m.unknown_negative}</td>
                  <td className="num">{m.fp + m.tn + m.unknown_negative}</td>
                </tr>
                <tr className="total">
                  <th scope="row">total</th>
                  <td className="num">{m.tp + m.fp}</td>
                  <td className="num">{m.fn + m.tn}</td>
                  <td className="num">{unknown}</td>
                  <td className="num">{total}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
        <section aria-label="Grader rates" className="subsection">
          <h5>Grader rates</h5>
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
        <section aria-label="Grader statuses" className="subsection">
          <h5>Grader statuses</h5>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">Status</th>
                  <th scope="col" className="num">
                    Scores
                  </th>
                </tr>
              </thead>
              <tbody>
                {STATUSES.map((status) => (
                  <tr key={status}>
                    <th scope="row">{status}</th>
                    <td className="num">{calibration.statuses[status]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section aria-label="Excluded from the pairs" className="subsection">
          <h5>Excluded from the pairs</h5>
          <p>{`excluded: ${excluded}`}</p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">Reason</th>
                  <th scope="col" className="num">
                    Trials
                  </th>
                </tr>
              </thead>
              <tbody>
                {EXCLUSION_REASONS.map((reason) => (
                  <tr key={reason}>
                    <th scope="row">{reason}</th>
                    <td className="num">{calibration.excluded[reason]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </SectionCard>
  );
}

export default JudgeMatrix;
