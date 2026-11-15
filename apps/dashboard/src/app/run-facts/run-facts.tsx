// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from 'react';
import type { RunSummary, TokenUsage } from '../../generated/report';
import { manifestRows, type Manifest } from '../../findings';
import { formatConfig, formatLevel, pythonMember } from '../../format';
import { NOT_RECORDED, TERMS, orNotRecorded } from '../../report-text';
import SectionCard from '../section-card/section-card';

export interface RunFactsProps {
  report: RunSummary;
  /** The finding's `manifest.json`, when it has one. */
  manifest?: Manifest | null;
}

const USAGE_FIELDS: (keyof TokenUsage)[] = [
  'input_tokens',
  'input_tokens_cache_read',
  'input_tokens_cache_write',
  'output_tokens',
  'reasoning_tokens',
  'total_tokens',
  'total_cost',
];

/** A token usage row; each value as Python's `str()` prints it, or `not reported`. */
function usageRow(name: string, usage: TokenUsage): string[] {
  return [
    name,
    ...USAGE_FIELDS.map((field) => pythonMember(usage, field, 'not reported')),
  ];
}

/**
 * The Run, Token usage and Trials sections of the report (Trials ends with the terms the
 * rates use), and the finding's manifest.
 */
export function RunFacts({ report, manifest }: RunFactsProps) {
  const facts = report.facts;
  const roles = Object.entries(facts.model_roles)
    .map(
      ([role, models]) =>
        `${role}: ` +
        (models ?? [])
          .map((m) => `${m.model} (${formatConfig(m.generate_config)})`)
          .join(', '),
    )
    .join('; ');
  const corpus = (task: string | null, seen: string[]): ReactNode => (
    <>
      {`${orNotRecorded(task)} (samples: ${seen.join(', ') || NOT_RECORDED})`}
      {facts.corpus_mismatch && (
        <>
          {' '}
          <strong className="mismatch">MISMATCH</strong>
        </>
      )}
    </>
  );
  const rows: [string, ReactNode][] = [
    ['Task', facts.task],
    ['Log status', facts.status],
    ['Model', facts.model],
    ['Model roles', roles || 'none'],
    ['Inspect version', orNotRecorded(facts.inspect_version)],
    ['Probo version', orNotRecorded(facts.probo_version)],
    ['Revision', orNotRecorded(facts.revision)],
    ['Started', orNotRecorded(facts.started_at)],
    ['Completed', orNotRecorded(facts.completed_at)],
    ['Epochs', orNotRecorded(facts.epochs)],
    [
      'Corpus version (task metadata)',
      corpus(facts.corpus_version, facts.sample_corpus_versions),
    ],
    [
      'Corpus content hash (task metadata)',
      corpus(facts.corpus_content_hash, facts.sample_corpus_hashes),
    ],
    ['Seeds', orNotRecorded(facts.seeds.join(', '))],
    ['Generate config (eval)', formatConfig(facts.generate_config)],
    ['Generate config (model)', formatConfig(facts.model_generate_config)],
    ['Confidence level', formatLevel(report.level)],
  ];
  const usage = [
    ...Object.entries(facts.token_usage).map(([m, u]) =>
      u ? usageRow(`model ${m}`, u) : [],
    ),
    ...Object.entries(facts.role_usage).map(([r, u]) =>
      u ? usageRow(`role ${r}`, u) : [],
    ),
  ].filter((row) => row.length > 0);
  const notRun = report.not_run === null ? 'unknown' : String(report.not_run);
  const trials: [string, string][] = [
    [
      'expected (dataset samples x epochs)',
      orNotRecorded(facts.expected_trials),
    ],
    ['in the log', String(report.trials)],
    ['not run', notRun],
    ['control', String(report.control_trials)],
    ['template', String(report.template_trials)],
  ];
  const published = manifest ? manifestRows(manifest) : [];
  return (
    <>
      <SectionCard section="run">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Fact</th>
                <th scope="col">Value</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([fact, value]) => (
                <tr key={fact}>
                  <th scope="row">{fact}</th>
                  <td className="code">{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <section aria-label="Token usage" className="subsection">
          <h5>Token usage</h5>
          {usage.length === 0 ? (
            <p>No token usage recorded.</p>
          ) : (
            <>
              <p>
                Input excludes cache reads and writes; totals are as Inspect
                reports them.
              </p>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      {[
                        'Usage',
                        'Input (excl. cache)',
                        'Cache read',
                        'Cache write',
                        'Output',
                        'Reasoning',
                        'Total',
                        'Cost',
                      ].map((name, index) => (
                        <th
                          scope="col"
                          key={name}
                          className={index > 0 ? 'num' : undefined}
                        >
                          {name}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {usage.map(([name, ...cells]) => (
                      <tr key={name}>
                        <th scope="row">{name}</th>
                        {cells.map((cell, index) => (
                          <td key={index} className="num">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      </SectionCard>
      <SectionCard section="trials">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Group</th>
                <th scope="col" className="num">
                  Trials
                </th>
              </tr>
            </thead>
            <tbody>
              {trials.map(([group, count]) => (
                <tr key={group}>
                  <th scope="row">{group}</th>
                  <td className="num">{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>{TERMS}</p>
      </SectionCard>
      {published.length > 0 && (
        <SectionCard section="published">
          <p className="muted">From the finding&apos;s manifest.json.</p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">Field</th>
                  <th scope="col">Value</th>
                </tr>
              </thead>
              <tbody>
                {published.map(([key, value]) => (
                  <tr key={key}>
                    <th scope="row">{key}</th>
                    <td className="code">{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      )}
    </>
  );
}

export default RunFacts;
