// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from 'react';
import { OUTCOMES } from '../../report-text';
import styles from './status-chip.module.css';

type Tone = 'accent' | 'neutral' | 'quiet';
type Glyph = 'dot' | 'ring' | 'dash' | 'check' | 'alert';

interface ChipStyle {
  tone: Tone;
  glyph: Glyph | null;
}

/** Unknown values: a plain neutral chip with no glyph. */
const NEUTRAL: ChipStyle = { tone: 'neutral', glyph: null };

/**
 * The known values and how they look. The text always says what the value is; tone and
 * glyph only repeat it, so nothing depends on colour alone. A Map, so that names such as
 * `constructor` or `__proto__` find nothing.
 */
const KNOWN = new Map<string, ChipStyle>([
  ...OUTCOMES.map((outcome): [string, ChipStyle] => [
    outcome,
    outcome === 'attack_succeeded'
      ? { tone: 'accent', glyph: 'dot' }
      : outcome === 'attack_failed_target_resisted'
        ? { tone: 'neutral', glyph: 'ring' }
        : { tone: 'quiet', glyph: 'dash' },
  ]),
  ['denominator', { tone: 'neutral', glyph: 'ring' }],
  ['excluded', { tone: 'quiet', glyph: 'dash' }],
  ['no outcome', { tone: 'quiet', glyph: null }],
  ['complete', { tone: 'neutral', glyph: 'check' }],
  ['incomplete', { tone: 'accent', glyph: 'alert' }],
]);

const GLYPHS: Record<Glyph, ReactNode> = {
  dot: <circle cx="6" cy="6" r="3.5" fill="currentColor" stroke="none" />,
  ring: <circle cx="6" cy="6" r="3.25" />,
  dash: <path d="M2.5 6h7" />,
  check: <path d="M2.5 6.5l2.25 2.25L9.5 3.5" />,
  alert: <path d="M6 2.5v4.25M6 9.25v.25" />,
};

export interface StatusChipProps {
  /** The value shown, as text; it also picks the chip's look when it is a known value. */
  value: string;
}

/** A value such as an outcome or a run status as a pill; unknown values look neutral. */
export function StatusChip({ value }: StatusChipProps) {
  const { tone, glyph } = KNOWN.get(value) ?? NEUTRAL;
  return (
    <span className={`${styles['chip']} ${styles[tone]}`}>
      {glyph !== null && (
        <svg
          className={styles['glyph']}
          viewBox="0 0 12 12"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.75}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          {GLYPHS[glyph]}
        </svg>
      )}
      <span>{value}</span>
    </span>
  );
}

export default StatusChip;
