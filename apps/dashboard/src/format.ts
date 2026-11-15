// SPDX-License-Identifier: Apache-2.0
/**
 * Text of rates and proportions, mirroring `probo.stats.rate` (`format_estimate_and_interval`,
 * `format_level`, `Proportion.render`, `Rate.render`, `render_optional`) character for
 * character, so the dashboard prints the strings of `report.md` and `judge-calibration.txt`.
 *
 * The JSON stores unrounded floats. Like the Python code, rounding acts on the exact binary
 * value of each double (never on a decimal approximation of it): the estimate is rounded to
 * nearest with ties to even, the lower bound down and the upper bound up.
 */
import type { JudgeCalibration } from './generated/calibration';
import type { Proportion, Rate } from './generated/report';
import { isFloat } from './json';

/** Text printed instead of a rate whose denominator is 0 (`render_optional`). */
export const ABSENT = 'absent (denominator is 0)';

type Rounding = 'half-even' | 'floor' | 'ceiling';

/** The decimal context precision `format_estimate_and_interval` sets (`context.prec`). */
const PRECISION = 64;

const ZERO = BigInt(0);
const ONE = BigInt(1);
const TWO = BigInt(2);
const FIVE = BigInt(5);
const TEN = BigInt(10);

/** base ** exponent for a non-negative integer exponent (no `**` on bigint below ES2016). */
function power(base: bigint, exponent: number): bigint {
  let result = ONE;
  let square = base;
  for (let rest = exponent; rest > 0; rest = Math.floor(rest / 2)) {
    if (rest % 2 === 1) result *= square;
    square *= square;
  }
  return result;
}

/** A finite double as (-1)^negative * digits * 10^-scale, exactly. */
interface ExactDecimal {
  negative: boolean;
  digits: bigint;
  scale: number;
}

function exactDecimal(value: number): ExactDecimal {
  if (!Number.isFinite(value)) {
    throw new RangeError(`cannot format ${value}`);
  }
  const view = new DataView(new ArrayBuffer(8));
  view.setFloat64(0, value);
  const high = view.getUint32(0);
  const low = view.getUint32(4);
  const negative = high >>> 31 === 1;
  const biased = (high >>> 20) & 0x7ff;
  let mantissa = (BigInt(high & 0xfffff) << BigInt(32)) | BigInt(low);
  let exponent: number;
  if (biased === 0) {
    exponent = -1074;
  } else {
    mantissa |= ONE << BigInt(52);
    exponent = biased - 1075;
  }
  if (exponent >= 0) {
    return { negative, digits: mantissa << BigInt(exponent), scale: 0 };
  }
  // m * 2^e = m * 5^-e / 10^-e
  return {
    negative,
    digits: mantissa * power(FIVE, -exponent),
    scale: -exponent,
  };
}

/** round(n / d) of non-negative integers under `mode`. */
function divide(n: bigint, d: bigint, mode: Rounding): bigint {
  const quotient = n / d;
  const remainder = n % d;
  if (remainder === ZERO || mode === 'floor') return quotient;
  if (mode === 'ceiling') return quotient + ONE;
  const twice = TWO * remainder;
  if (twice > d || (twice === d && quotient % TWO === ONE))
    return quotient + ONE;
  return quotient;
}

/** Decimal(value).quantize(Decimal(10) ** -places, rounding=mode), as sign and digits. */
function quantize(value: number, places: number, mode: Rounding): ExactDecimal {
  const exact = exactDecimal(value);
  // Floor and ceiling act on the signed value; on the magnitude of a negative they swap.
  const onMagnitude: Rounding =
    exact.negative && mode !== 'half-even'
      ? mode === 'floor'
        ? 'ceiling'
        : 'floor'
      : mode;
  const digits =
    exact.scale <= places
      ? exact.digits * power(TEN, places - exact.scale)
      : divide(exact.digits, power(TEN, exact.scale - places), onMagnitude);
  if (digits.toString().length > PRECISION) {
    // Python's quantize raises InvalidOperation here; so does this.
    throw new RangeError(
      `${value} needs more than ${PRECISION} digits at ${places} places`,
    );
  }
  return { negative: exact.negative, digits, scale: places };
}

/** Python's `str()` of a `Decimal` with coefficient `digits` and exponent `-scale`. */
function decimalText({ negative, digits, scale }: ExactDecimal): string {
  const sign = negative ? '-' : '';
  const coefficient = digits.toString();
  const exponent = -scale;
  const adjusted = exponent + coefficient.length - 1;
  if (exponent <= 0 && adjusted >= -6) {
    if (exponent === 0) return sign + coefficient;
    const point = coefficient.length + exponent;
    return point > 0
      ? `${sign}${coefficient.slice(0, point)}.${coefficient.slice(point)}`
      : `${sign}0.${'0'.repeat(-point)}${coefficient}`;
  }
  const mantissa =
    coefficient.length > 1
      ? `${coefficient[0]}.${coefficient.slice(1)}`
      : coefficient;
  return `${sign}${mantissa}E${adjusted >= 0 ? '+' : ''}${adjusted}`;
}

/**
 * `E [L, U]` with E rounded to nearest, L down and U up, all with the same number of
 * decimals: 3, or more until no value that is not exactly 0 prints as 0 and no value that
 * is not exactly 1 prints as 1 (`format_estimate_and_interval`).
 */
export function formatEstimateAndInterval(
  estimate: number,
  lower: number,
  upper: number,
): string {
  const values: [number, Rounding][] = [
    [estimate, 'half-even'],
    [lower, 'floor'],
    [upper, 'ceiling'],
  ];
  for (let places = 3; ; places += 1) {
    const texts = values.map(([value, mode]) => quantize(value, places, mode));
    const one = power(TEN, places);
    const exact = texts.every(({ negative, digits }, index) => {
      const value = values[index][0];
      const isZero = digits === ZERO;
      const isOne = !negative && digits === one;
      return (!isZero || value === 0) && (!isOne || value === 1);
    });
    if (exact) {
      const [e, l, u] = texts.map(decimalText);
      return `${e} [${l}, ${u}]`;
    }
  }
}

/**
 * `level` as the exact percentage of its shortest representation, never rounded:
 * 0.95 -> `95%`, 0.995 -> `99.5%` (`format_level`).
 */
export function formatLevel(level: number): string {
  if (!Number.isFinite(level)) {
    throw new RangeError(`cannot format level ${level}`);
  }
  // String() and Python's repr() both give the shortest text that reads back as `level`.
  const match = /^(-?)(\d+)(?:\.(\d+))?(?:e([+-]\d+))?$/.exec(String(level));
  if (match === null) {
    throw new RangeError(`cannot format level ${level}`);
  }
  const [, sign, whole, fraction = '', exponentText = '0'] = match;
  // value = digits * 10^exponent; times 100 adds 2 to the exponent.
  let digits = (whole + fraction).replace(/^0+(?=\d)/, '');
  let exponent = Number(exponentText) - fraction.length + 2;
  while (digits.length > 1 && digits.endsWith('0')) {
    digits = digits.slice(0, -1);
    exponent += 1;
  }
  if (digits === '0') return `${sign}0%`;
  let text: string;
  if (exponent >= 0) {
    text = digits + '0'.repeat(exponent);
  } else {
    const point = digits.length + exponent;
    text =
      point > 0
        ? `${digits.slice(0, point)}.${digits.slice(point)}`
        : `0.${'0'.repeat(-point)}${digits}`;
  }
  return `${sign}${text}%`;
}

/** `per-attempt` or `per-trial` (`Rate.label`). */
export function estimandLabel(rate: Rate): string {
  return rate.estimand.split('_').join('-');
}

function isRate(value: Proportion | Rate): value is Rate {
  return 'estimand' in value;
}

/**
 * `0.300 [0.145, 0.519] (n=20, per-attempt, 95% Wilson)` for a rate and
 * `0.800 [0.490, 0.944] (n=10, 95% Wilson)` for a proportion, from the stored estimate and
 * interval (`Rate.render`, `Proportion.render`).
 */
export function renderValue(value: Proportion | Rate): string {
  const parts = [`n=${value.trials}`];
  if (isRate(value)) parts.push(estimandLabel(value));
  parts.push(`${formatLevel(value.level)} Wilson`);
  const numbers = formatEstimateAndInterval(
    value.estimate,
    value.interval.lower,
    value.interval.upper,
  );
  return `${numbers} (${parts.join(', ')})`;
}

/** `renderValue(value)`, or `absent (denominator is 0)` for a missing value. */
export function renderOptional(
  value: Proportion | Rate | null | undefined,
): string {
  return value === null || value === undefined ? ABSENT : renderValue(value);
}

/**
 * Python's `repr()` (and `str()`) of a float: the shortest digits that read back as `x`,
 * positional when the decimal exponent is in [-4, 16) and always with a fractional part
 * (`1.0`, `0.0001`, `-0.0`), otherwise scientific with a sign and at least two exponent
 * digits (`1e-05`, `1e+16`, `1.5e+300`).
 */
export function pythonFloat(x: number): string {
  if (Number.isNaN(x)) return 'nan';
  if (x === Infinity) return 'inf';
  if (x === -Infinity) return '-inf';
  if (x === 0) return Object.is(x, -0) ? '-0.0' : '0.0';
  // toExponential() without an argument gives the shortest round-trip digits.
  const [mantissa, exponentText] = x.toExponential().split('e');
  const sign = mantissa.startsWith('-') ? '-' : '';
  const digits = mantissa.replace('-', '').replace('.', '');
  const exponent = Number(exponentText);
  if (exponent >= -4 && exponent < 16) {
    if (exponent < 0) return `${sign}0.${'0'.repeat(-exponent - 1)}${digits}`;
    const whole = digits.slice(0, exponent + 1).padEnd(exponent + 1, '0');
    return `${sign}${whole}.${digits.slice(exponent + 1) || '0'}`;
  }
  const lead = digits.length > 1 ? `${digits[0]}.${digits.slice(1)}` : digits;
  const power = String(Math.abs(exponent)).padStart(2, '0');
  return `${sign}${lead}e${exponent < 0 ? '-' : '+'}${power}`;
}

/**
 * Python's `str()` of a number read from JSON: a float as `pythonFloat`, an integer in
 * plain digits. `float` says whether the JSON wrote it as a float (see `isFloat`); a
 * number that is not integral is a float either way.
 */
export function pythonNumber(x: number, float: boolean): string {
  if (float || !Number.isInteger(x)) return pythonFloat(x);
  return Number.isSafeInteger(x) ? String(x) : BigInt(x).toString();
}

/** `str()` of `container[key]`, a number or null read from JSON; `none` for null. */
export function pythonMember(
  container: object,
  key: string,
  none: string,
): string {
  const value = (container as Record<string, unknown>)[key];
  if (value === null || value === undefined) return none;
  return typeof value === 'number'
    ? pythonNumber(value, isFloat(container, key))
    : String(value);
}

/** Python's `repr()` of `container[key]`, a JSON value. */
function pythonRepr(value: unknown, float: boolean): string {
  if (value === null || value === undefined) return 'None';
  if (value === true) return 'True';
  if (value === false) return 'False';
  if (typeof value === 'number') return pythonNumber(value, float);
  if (typeof value === 'string') {
    // repr() quotes with ' unless the text contains ' and no ".
    const quote = value.includes("'") && !value.includes('"') ? '"' : "'";
    const escaped = value
      .replace(/\\/g, '\\\\')
      .split(quote)
      .join(`\\${quote}`);
    return `${quote}${escaped}${quote}`;
  }
  if (Array.isArray(value)) {
    return `[${value.map((item, index) => pythonRepr(item, isFloat(value, index))).join(', ')}]`;
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>).map(
      ([k, v]) =>
        `${pythonRepr(k, false)}: ${pythonRepr(v, isFloat(value, k))}`,
    );
    return `{${entries.join(', ')}}`;
  }
  return String(value);
}

/** Python's `str()` of a JSON value; `float` as for `pythonNumber`. */
export function pythonStr(value: unknown, float = false): string {
  return typeof value === 'string' ? value : pythonRepr(value, float);
}

/** `key=value, ...` of a generate config, or `defaults` when it is empty (`_config`). */
export function formatConfig(values: Record<string, unknown>): string {
  return (
    Object.entries(values)
      .map(([key, value]) => `${key}=${pythonStr(value, isFloat(values, key))}`)
      .join(', ') || 'defaults'
  );
}

/** `json.dumps(value, sort_keys=True)`: sorted keys, `, ` and `: ` separators, ASCII. */
export function pythonJson(value: unknown, float = false): string {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'number') {
    if (Number.isNaN(value)) return 'NaN';
    if (!Number.isFinite(value)) return value > 0 ? 'Infinity' : '-Infinity';
    return pythonNumber(value, float);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item, index) => pythonJson(item, isFloat(value, index))).join(', ')}]`;
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>).sort(
      ([a], [b]) => (a < b ? -1 : a > b ? 1 : 0),
    );
    return `{${entries
      .map(([k, v]) => `${pythonJson(k)}: ${pythonJson(v, isFloat(value, k))}`)
      .join(', ')}}`;
  }
  return JSON.stringify(value).replace(
    /[\u0080-\uffff]/g,
    (char) => `\\u${char.charCodeAt(0).toString(16).padStart(4, '0')}`,
  );
}

/** The grader generate config line of `JudgeCalibration.render`. */
export function calibrationConfig(calibration: JudgeCalibration): string {
  return calibration.generate_config === null
    ? 'none'
    : pythonJson(calibration.generate_config);
}

/** A trial as `<sample id>@<epoch>`. */
export function trialRef([sampleId, epoch]: [string | number, number]): string {
  return `${sampleId}@${epoch}`;
}

/** `none`, or the trials as `<sample id>@<epoch>`, comma separated. */
export function trialRefs(trials: [string | number, number][]): string {
  return trials.map(trialRef).join(', ') || 'none';
}
