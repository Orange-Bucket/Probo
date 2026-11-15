// SPDX-License-Identifier: Apache-2.0
/** Small, hand-made report and calibration data for component tests. */
import type { Finding } from '../findings';
import type { JudgeCalibration } from '../generated/calibration';
import type {
  AttackSuccess,
  CheckShare,
  OutcomeCounts,
  Proportion,
  Rate,
  RunSummary,
  TrialLabel,
} from '../generated/report';

/** A proportion with the given estimate and interval (not recomputed). */
export function proportion(
  successes: number,
  trials: number,
  lower: number,
  upper: number,
): Proportion {
  return {
    successes,
    trials,
    level: 0.95,
    estimate: successes / trials,
    interval: { lower, upper },
  };
}

export function rate(
  successes: number,
  trials: number,
  lower: number,
  upper: number,
  estimand: Rate['estimand'],
): Rate {
  return { ...proportion(successes, trials, lower, upper), estimand };
}

export function share(
  value: Proportion | null,
  notApplicable = 0,
  missing = 0,
): CheckShare {
  return {
    trials: (value?.trials ?? 0) + notApplicable + missing,
    value,
    not_applicable: notApplicable,
    missing,
  };
}

export function counts(values: Partial<OutcomeCounts> = {}): OutcomeCounts {
  return {
    attack_succeeded: 0,
    attack_failed_target_resisted: 0,
    attack_failed_attacker: 0,
    not_delivered: 0,
    target_refused_task: 0,
    harness_error: 0,
    environment_error: 0,
    provider_error: 0,
    grader_error: 0,
    grader_uncertain: 0,
    ...values,
  };
}

/** 3 succeeded and 1 resisted of 4 delivered, graded attempts. */
export const ATTACK: AttackSuccess = {
  counts: counts({ attack_succeeded: 3, attack_failed_target_resisted: 1 }),
  level: 0.95,
  per_attempt: rate(3, 4, 0.30064, 0.9544, 'per_attempt'),
  per_trial: rate(3, 4, 0.30064, 0.9544, 'per_trial'),
};

/** Every template trial excluded: both rates are absent. */
export const ABSENT_ATTACK: AttackSuccess = {
  counts: counts({ not_delivered: 2 }),
  level: 0.95,
  per_attempt: null,
  per_trial: null,
};

export function label(values: Partial<TrialLabel> = {}): TrialLabel {
  return {
    sample_id: 'task-a/tpl-1',
    epoch: 1,
    user_task: 'task-a',
    template_id: 'tpl-1',
    kind: 'template',
    outcome: 'attack_succeeded',
    limit: null,
    task_completed: true,
    record_leaked: 'true',
    sent_to_watched_address: 'true',
    note_delivered: 'true',
    evidence: ['record_leaked=true'],
    ...values,
  };
}

/** A complete, successful run with four template and four control trials. */
export function report(values: Partial<RunSummary> = {}): RunSummary {
  return {
    facts: {
      task: 'probo/example',
      status: 'success',
      model: 'mockllm/model',
      model_roles: {},
      inspect_version: '0.3.0',
      probo_version: '0.1.0',
      revision: 'abc1234',
      started_at: '2026-01-01T00:00:00+00:00',
      completed_at: '2026-01-01T01:00:00+00:00',
      epochs: 2,
      corpus_version: '2026-01',
      corpus_content_hash: 'ff00',
      sample_corpus_versions: ['2026-01'],
      sample_corpus_hashes: ['ff00'],
      corpus_mismatch: false,
      seeds: [7],
      generate_config: { temperature: 0.5 },
      model_generate_config: {},
      token_usage: {
        'mockllm/model': {
          input_tokens: 10,
          output_tokens: 5,
          input_tokens_cache_read: null,
          input_tokens_cache_write: null,
          reasoning_tokens: null,
          total_tokens: 15,
          total_cost: null,
        },
      },
      role_usage: {},
      expected_trials: 8,
    },
    level: 0.95,
    warnings: [],
    incomplete: false,
    trials: 8,
    not_run: 0,
    control_trials: 4,
    template_trials: 4,
    attack: ATTACK,
    attack_by_template: { 'tpl-1': ATTACK },
    delivered: 4,
    attempted: share(proportion(4, 4, 0.51, 1)),
    completed: share(proportion(3, 4, 0.30064, 0.9544)),
    attempt_completion: {
      sent_and_leaked: 3,
      sent_not_leaked: 1,
      leaked_not_sent: 0,
      neither: 0,
    },
    utility_control: share(proportion(2, 4, 0.15, 0.85)),
    utility_template: share(proportion(1, 4, 0.0456, 0.6994)),
    utility_by_user_task: [
      {
        user_task: 'task-a',
        control: share(proportion(2, 4, 0.15, 0.85)),
        template: share(null, 4),
      },
    ],
    control: {
      trials: 4,
      errors: counts(),
      record_leaked: share(proportion(0, 4, 0, 0.49)),
      sent_to_watched_address: share(proportion(0, 4, 0, 0.49)),
    },
    delivery: share(proportion(4, 4, 0.51, 1)),
    items: [
      {
        user_task: 'task-a',
        template_id: 'tpl-1',
        counts: counts({
          attack_succeeded: 3,
          attack_failed_target_resisted: 1,
        }),
      },
    ],
    limits: [
      { kind: 'template', outcome: 'attack_succeeded', trials: 3, limits: {} },
      {
        kind: 'template',
        outcome: 'attack_failed_target_resisted',
        trials: 1,
        limits: { message: 1 },
      },
    ],
    labels: [
      label(),
      label({
        epoch: 2,
        outcome: 'attack_failed_target_resisted',
        limit: 'message',
        record_leaked: 'false',
        evidence: ['note_delivered=true', 'hit the message limit (40)'],
      }),
    ],
    ...values,
  };
}

export function calibration(
  values: Partial<JudgeCalibration> = {},
): JudgeCalibration {
  return {
    judge: 'reply_only_judge',
    reference: 'record_leaked',
    judge_model: 'mockllm/judge',
    prompt_version: '1',
    prompt_sha256: '0123456789abcdef0123',
    generate_config: { temperature: 0.5, max_tokens: 10 },
    matrix: {
      tp: 2,
      fp: 1,
      fn: 1,
      tn: 3,
      unknown_positive: 1,
      unknown_negative: 0,
    },
    sample_ids: 2,
    epochs: 4,
    statuses: {
      graded: 8,
      empty_reply: 0,
      no_final_reply: 1,
      error: 0,
      grader_incomplete: 0,
    },
    excluded: {
      sample_error: 0,
      reference_missing: 0,
      judge_missing: 0,
      reference_not_applicable: 0,
      no_final_reply: 1,
      judge_error: 0,
      judge_incomplete: 0,
    },
    false_positives: [['s1', 2]],
    false_negatives: [['s2', 3]],
    unknowns: [],
    level: 0.95,
    base_rate: proportion(4, 8, 0.2152, 0.7848),
    precision: proportion(2, 3, 0.2077, 0.9385),
    recall: proportion(2, 3, 0.2077, 0.9385),
    recall_unknown_as_miss: proportion(2, 4, 0.15, 0.85),
    ...values,
  };
}

/** A finding with the fixture report and calibration and no manifest, unless given. */
export function finding(id: string, values: Partial<Finding> = {}): Finding {
  return {
    id,
    report: report(),
    calibration: calibration(),
    manifest: null,
    ...values,
  };
}
