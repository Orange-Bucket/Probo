// SPDX-License-Identifier: Apache-2.0
// Generated from packages/probo/schemas/report.schema.json by apps/dashboard/scripts/generate-types.mjs; do not edit.
// Regenerate with: pnpm nx run dashboard:generate-types

export type AttackFailedAttacker = number;
export type AttackFailedTargetResisted = number;
export type AttackSucceeded = number;
export type EnvironmentError = number;
export type GraderError = number;
export type GraderUncertain = number;
export type HarnessError = number;
export type NotDelivered = number;
export type ProviderError = number;
export type TargetRefusedTask = number;
export type Level = number;
/**
 * What an attack success rate estimates.
 *
 * s = #attack_succeeded, r = #attack_failed_target_resisted, N = all trials
 * (see ``probo.schema.Outcome``).
 */
export type Estimand = 'per_attempt' | 'per_trial';
/**
 * Point estimate x / n, computed from the counts.
 */
export type Estimate = number;
export type Lower = number;
export type Upper = number;
export type Level1 = number;
export type Successes = number;
export type Trials = number;
export type LeakedNotSent = number;
export type Neither = number;
export type SentAndLeaked = number;
export type SentNotLeaked = number;
export type Missing = number;
export type NotApplicable = number;
export type Trials1 = number;
/**
 * Point estimate x / n, computed from the counts.
 */
export type Estimate1 = number;
export type Level2 = number;
export type Successes1 = number;
export type Trials2 = number;
export type Trials3 = number;
export type ControlTrials = number;
export type Delivered = number;
export type CompletedAt = string | null;
export type CorpusContentHash = string | null;
export type CorpusMismatch = boolean;
export type CorpusVersion = string | null;
export type Epochs = number | null;
export type ExpectedTrials = number | null;
export type JsonValue = unknown;
export type InspectVersion = string | null;
export type Model = string;
export type Model1 = string;
export type ProboVersion = string | null;
export type Revision = string | null;
export type InputTokens = number;
export type InputTokensCacheRead = number | null;
export type InputTokensCacheWrite = number | null;
export type OutputTokens = number;
export type ReasoningTokens = number | null;
export type TotalCost = number | null;
export type TotalTokens = number;
export type SampleCorpusHashes = string[];
export type SampleCorpusVersions = string[];
export type Seeds = number[];
export type StartedAt = string | null;
export type Status = string;
export type Task = string;
export type Incomplete = boolean;
export type TemplateId = string;
export type UserTask = string;
export type Items = ItemResult[];
export type Epoch = number;
export type Evidence = string[];
export type Kind = 'control' | 'template';
export type Limit = string | null;
/**
 * The outcome of one check on one sample.
 */
export type CheckResult = 'true' | 'false' | 'not_applicable';
/**
 * The terminal label of one trial. Every trial receives exactly one label.
 *
 * Only ``ATTACK_SUCCEEDED`` and ``ATTACK_FAILED_TARGET_RESISTED`` describe a trial in which
 * the attack was delivered and graded; every other label marks a trial that says nothing
 * about the target's resistance (see ``DENOMINATOR_OUTCOMES`` and ``EXCLUDED_OUTCOMES``).
 */
export type Outcome =
  | 'attack_succeeded'
  | 'attack_failed_target_resisted'
  | 'attack_failed_attacker'
  | 'not_delivered'
  | 'target_refused_task'
  | 'harness_error'
  | 'environment_error'
  | 'provider_error'
  | 'grader_error'
  | 'grader_uncertain';
export type SampleId = number | string;
export type TaskCompleted = boolean | null;
export type TemplateId1 = string | null;
export type UserTask1 = string;
export type Labels = TrialLabel[];
export type Level3 = number;
export type Kind1 = 'control' | 'template';
export type Trials4 = number;
export type Limits = LimitRow[];
export type NotRun = number | null;
export type TemplateTrials = number;
export type Trials5 = number;
export type UserTask2 = string;
export type UtilityByUserTask = UserTaskUtility[];
export type Warnings = string[];

/**
 * Everything `render_markdown` prints, as data. `model_dump_json` round-trips.
 */
export interface RunSummary {
  attack: AttackSuccess;
  attack_by_template: AttackByTemplate;
  attempt_completion: AttemptCompletion;
  attempted: CheckShare;
  completed: CheckShare;
  control: ControlSummary;
  control_trials: ControlTrials;
  delivered: Delivered;
  delivery: CheckShare;
  facts: RunFacts;
  incomplete: Incomplete;
  items: Items;
  labels: Labels;
  level: Level3;
  limits: Limits;
  not_run: NotRun;
  template_trials: TemplateTrials;
  trials: Trials5;
  utility_by_user_task: UtilityByUserTask;
  utility_control: CheckShare;
  utility_template: CheckShare;
  warnings: Warnings;
}
/**
 * Attack success for one set of trials, per delivered attempt and per trial.
 *
 * With s = #attack_succeeded, r = #attack_failed_target_resisted and N = all trials:
 *
 * - ``per_attempt`` = s / (s + r), estimand ``Estimand.PER_ATTEMPT``: success among
 *   delivered, graded attempts. Every outcome in ``EXCLUDED_OUTCOMES`` is left out.
 * - ``per_trial`` = s / N, estimand ``Estimand.PER_TRIAL``: success among all trials, every
 *   excluded trial counted as a failure.
 *
 * Each is a ``Rate`` with a Wilson interval at ``level``, or None when its denominator is 0
 * (never 0.0 or NaN). per_trial <= per_attempt whenever both exist, so per_trial is the
 * conservative figure for a claim that an attack works and the flattering figure for a
 * claim that a target is robust; report both, with the counts.
 *
 * Known limits:
 *
 * - Informative missingness. Excluded outcomes such as ``target_refused_task`` or
 *   ``grader_uncertain`` can be caused by the injection itself, so excluding them is not
 *   neutral: 5 attack_succeeded and 95 target_refused_task give per_attempt 5/5 = 1.000
 *   and per_trial 5/100 = 0.050. Neither rate alone is the truth; read the counts.
 * - Independence. The Wilson interval assumes independent trials with one common success
 *   probability. Pooling trials across scenarios, templates or models, or counting
 *   correlated repeats of the same sample, makes the interval too narrow.
 *
 * Stores only ``counts`` and ``level``; both rates are computed from them and included in
 * dumps. Loading accepts the ``per_attempt`` and ``per_trial`` keys only when they equal
 * the recomputed rates (see ``FrozenModel``). Build one with ``from_counts``.
 */
export interface AttackSuccess {
  counts: OutcomeCounts;
  level: Level;
  /**
   * s / (s + r) labelled ``PER_ATTEMPT``, or None when s + r = 0.
   */
  per_attempt: Rate | null;
  /**
   * s / N labelled ``PER_TRIAL``, or None when N = 0.
   */
  per_trial: Rate | null;
}
/**
 * Number of trials with each ``Outcome``; one non-negative int field per outcome value.
 *
 * Counts are checked on construction, validation and ``model_copy``.
 */
export interface OutcomeCounts {
  attack_failed_attacker: AttackFailedAttacker;
  attack_failed_target_resisted: AttackFailedTargetResisted;
  attack_succeeded: AttackSucceeded;
  environment_error: EnvironmentError;
  grader_error: GraderError;
  grader_uncertain: GraderUncertain;
  harness_error: HarnessError;
  not_delivered: NotDelivered;
  provider_error: ProviderError;
  target_refused_task: TargetRefusedTask;
}
/**
 * An attack success rate: a binomial proportion labelled with what it estimates.
 *
 * Stores ``successes``, ``trials``, ``level`` and ``estimand``; ``estimate = successes /
 * trials`` and ``interval = wilson_interval(successes, trials, level)`` are computed and
 * included in dumps. Loading accepts those derived keys only when they agree with the
 * recomputed values (see ``FrozenModel``).
 */
export interface Rate {
  estimand: Estimand;
  estimate: Estimate;
  interval: Interval;
  level: Level1;
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
export interface AttackByTemplate {
  [k: string]: AttackSuccess | undefined;
}
/**
 * Attempted against completed over delivered template trials with both values.
 */
export interface AttemptCompletion {
  leaked_not_sent: LeakedNotSent;
  neither: Neither;
  sent_and_leaked: SentAndLeaked;
  sent_not_leaked: SentNotLeaked;
}
/**
 * Share of a group of trials whose value is true, every other trial counted.
 *
 * `trials` = `value.trials` (0 when `value` is None) + `not_applicable` + `missing`.
 */
export interface CheckShare {
  missing: Missing;
  not_applicable: NotApplicable;
  trials: Trials1;
  value: Proportion | null;
}
/**
 * A binomial proportion x / n with its two-sided Wilson interval at ``level``.
 *
 * Stores only ``successes``, ``trials`` and ``level``; ``estimate`` and ``interval`` are
 * computed from them and included in dumps. Loading accepts those derived keys only when
 * they agree with the recomputed values (see ``FrozenModel``).
 */
export interface Proportion {
  estimate: Estimate1;
  interval: Interval1;
  level: Level2;
  successes: Successes1;
  trials: Trials2;
}
/**
 * ``wilson_interval(successes, trials, level)``, computed from the stored fields.
 */
export interface Interval1 {
  lower: Lower;
  upper: Upper;
}
/**
 * Control trials: their error labels and base rates.
 */
export interface ControlSummary {
  errors: OutcomeCounts;
  record_leaked: CheckShare;
  sent_to_watched_address: CheckShare;
  trials: Trials3;
}
/**
 * Facts about the run, read from the log; None where the log does not record one.
 */
export interface RunFacts {
  completed_at: CompletedAt;
  corpus_content_hash: CorpusContentHash;
  corpus_mismatch: CorpusMismatch;
  corpus_version: CorpusVersion;
  epochs: Epochs;
  expected_trials: ExpectedTrials;
  generate_config: GenerateConfig;
  inspect_version: InspectVersion;
  model: Model;
  model_generate_config: ModelGenerateConfig;
  model_roles: ModelRoles;
  probo_version: ProboVersion;
  revision: Revision;
  role_usage: RoleUsage;
  sample_corpus_hashes: SampleCorpusHashes;
  sample_corpus_versions: SampleCorpusVersions;
  seeds: Seeds;
  started_at: StartedAt;
  status: Status;
  task: Task;
  token_usage: TokenUsage1;
}
export interface GenerateConfig {
  [k: string]: JsonValue | undefined;
}
export interface ModelGenerateConfig {
  [k: string]: JsonValue | undefined;
}
export interface ModelRoles {
  [k: string]: RoleModel[] | undefined;
}
/**
 * A model bound to a role, with its own generate config (unset fields left out).
 */
export interface RoleModel {
  generate_config: GenerateConfig1;
  model: Model1;
}
export interface GenerateConfig1 {
  [k: string]: JsonValue | undefined;
}
export interface RoleUsage {
  [k: string]: TokenUsage | undefined;
}
/**
 * Token usage as Inspect reports it; None where the provider reported nothing.
 *
 * `input_tokens` excludes cache reads and writes, so it need not add up to `total_tokens`
 * with `output_tokens` alone.
 */
export interface TokenUsage {
  input_tokens: InputTokens;
  input_tokens_cache_read: InputTokensCacheRead;
  input_tokens_cache_write: InputTokensCacheWrite;
  output_tokens: OutputTokens;
  reasoning_tokens: ReasoningTokens;
  total_cost: TotalCost;
  total_tokens: TotalTokens;
}
export interface TokenUsage1 {
  [k: string]: TokenUsage | undefined;
}
/**
 * Outcomes of one item (user task x template) over its epochs.
 */
export interface ItemResult {
  counts: OutcomeCounts;
  template_id: TemplateId;
  user_task: UserTask;
}
/**
 * The outcome label of one trial and the facts that decided it.
 *
 * The check values are None when they were not read (an errored sample, or a limit hit
 * while the model API was failing) or are missing or invalid (a grader error).
 */
export interface TrialLabel {
  epoch: Epoch;
  evidence: Evidence;
  kind: Kind;
  limit: Limit;
  note_delivered: CheckResult | null;
  outcome: Outcome | null;
  record_leaked: CheckResult | null;
  sample_id: SampleId;
  sent_to_watched_address: CheckResult | null;
  task_completed: TaskCompleted;
  template_id: TemplateId1;
  user_task: UserTask1;
}
/**
 * How many trials of one kind and outcome hit a limit, by limit type.
 */
export interface LimitRow {
  kind: Kind1;
  limits: Limits1;
  outcome: Outcome | null;
  trials: Trials4;
}
export interface Limits1 {
  [k: string]: number | undefined;
}
/**
 * `task_completed` shares of one user task, control and template trials apart.
 */
export interface UserTaskUtility {
  control: CheckShare;
  template: CheckShare;
  user_task: UserTask2;
}
