// SPDX-License-Identifier: Apache-2.0
// Generated from packages/probo/schemas/calibration.schema.json by apps/dashboard/scripts/generate-types.mjs; do not edit.
// Regenerate with: pnpm nx run dashboard:generate-types

/**
 * Point estimate x / n, computed from the counts.
 */
export type Estimate = number;
export type Lower = number;
export type Upper = number;
export type Level = number;
export type Successes = number;
export type Trials = number;
export type Epochs = number;
export type JudgeError = number;
export type JudgeIncomplete = number;
export type JudgeMissing = number;
export type NoFinalReply = number;
export type ReferenceMissing = number;
export type ReferenceNotApplicable = number;
export type SampleError = number;
export type FalseNegatives = [string | number, number][];
export type FalsePositives = [string | number, number][];
export type GenerateConfig = {
  [k: string]: unknown | undefined;
} | null;
export type Judge = string;
export type JudgeModel = string;
export type Level1 = number;
export type Fn = number;
export type Fp = number;
export type Tn = number;
export type Tp = number;
export type UnknownNegative = number;
export type UnknownPositive = number;
export type PromptSha256 = string;
export type PromptVersion = string;
export type Reference = string;
export type SampleIds = number;
export type EmptyReply = number;
export type Error = number;
export type Graded = number;
export type GraderIncomplete = number;
export type NoFinalReply1 = number;
export type Unknowns = [string | number, number][];

/**
 * The grader against a deterministic reference over one log; build with `calibrate`.
 */
export interface JudgeCalibration {
  /**
   * `ConfusionMatrix.base_rate` at `level`: share of pairs whose reference is positive.
   */
  base_rate: Proportion | null;
  epochs: Epochs;
  excluded: Exclusions;
  false_negatives: FalseNegatives;
  false_positives: FalsePositives;
  generate_config: GenerateConfig;
  judge: Judge;
  judge_model: JudgeModel;
  level: Level1;
  matrix: ConfusionMatrix;
  /**
   * `ConfusionMatrix.precision` at `level`: tp / (tp + fp), unknowns excluded.
   */
  precision: Proportion | null;
  prompt_sha256: PromptSha256;
  prompt_version: PromptVersion;
  /**
   * `ConfusionMatrix.recall` at `level`: tp / (tp + fn), unknowns excluded.
   */
  recall: Proportion | null;
  /**
   * `ConfusionMatrix.recall_unknown_as_miss` at `level`: unknown positives as misses.
   */
  recall_unknown_as_miss: Proportion | null;
  reference: Reference;
  sample_ids: SampleIds;
  statuses: JudgeStatuses;
  unknowns: Unknowns;
}
/**
 * A binomial proportion x / n with its two-sided Wilson interval at ``level``.
 *
 * Stores only ``successes``, ``trials`` and ``level``; ``estimate`` and ``interval`` are
 * computed from them and included in dumps. Loading accepts those derived keys only when
 * they agree with the recomputed values (see ``FrozenModel``).
 */
export interface Proportion {
  estimate: Estimate;
  interval: Interval;
  level: Level;
  successes: Successes;
  trials: Trials;
}
/**
 * ``wilson_interval(successes, trials, level)``, computed from the stored fields.
 */
export interface Interval {
  lower: Lower;
  upper: Upper;
}
/**
 * Trials left out of the pairs, by reason; each trial is counted under the first reason
 * that applies, in field order.
 */
export interface Exclusions {
  judge_error: JudgeError;
  judge_incomplete: JudgeIncomplete;
  judge_missing: JudgeMissing;
  no_final_reply: NoFinalReply;
  reference_missing: ReferenceMissing;
  reference_not_applicable: ReferenceNotApplicable;
  sample_error: SampleError;
}
/**
 * Judge predictions against deterministic-check references for one binary question.
 *
 * The reference is the deterministic check, the prediction is the judge, and the positive
 * class is "attack succeeded". A prediction of None is the judge answering "unknown"; such
 * pairs are counted apart, split by their reference so both recall variants are computable:
 *
 * - tp: reference True, prediction True      - fp: reference False, prediction True
 * - fn: reference True, prediction False     - tn: reference False, prediction False
 * - unknown_positive: reference True, None   - unknown_negative: reference False, None
 *
 * Every proportion method returns a ``Proportion`` with a Wilson interval at ``level``, or
 * None when its denominator is 0; ``level`` outside (0, 1) raises ``ValueError`` either way.
 * Accuracy is deliberately not offered: at a low base rate a judge that never flags an
 * attack scores accuracy near 1 with recall 0. Counts are checked on construction,
 * validation and ``model_copy``. Build one with ``from_pairs``.
 */
export interface ConfusionMatrix {
  fn: Fn;
  fp: Fp;
  tn: Tn;
  tp: Tp;
  unknown_negative: UnknownNegative;
  unknown_positive: UnknownPositive;
}
/**
 * Number of grader scores in a log by `JUDGE_STATUS`; one field per status in `STATUSES`.
 */
export interface JudgeStatuses {
  empty_reply: EmptyReply;
  error: Error;
  graded: Graded;
  grader_incomplete: GraderIncomplete;
  no_final_reply: NoFinalReply1;
}
