// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import type { RunFacts as Facts } from '../../generated/report';
import { parseJson } from '../../json';
import { report } from '../../testing/fixtures';
import { TERMS } from '../../report-text';
import RunFacts from './run-facts';

function value(fact: string): string | null {
  const row = screen.getByRole('row', { name: new RegExp(`^${fact}`) });
  return within(row).getByRole('cell').textContent;
}

describe('RunFacts', () => {
  it('shows the facts of the run as the report does', () => {
    render(<RunFacts report={report()} />);
    expect(value('Task')).toBe('probo/example');
    expect(value('Model roles')).toBe('none');
    expect(value('Inspect version')).toBe('0.3.0');
    expect(value('Started')).toBe('2026-01-01T00:00:00+00:00');
    expect(value('Epochs')).toBe('2');
    expect(value('Corpus version \\(task metadata\\)')).toBe(
      '2026-01 (samples: 2026-01)',
    );
    expect(value('Seeds')).toBe('7');
    expect(value('Generate config \\(eval\\)')).toBe('temperature=0.5');
    expect(value('Generate config \\(model\\)')).toBe('defaults');
    expect(value('Confidence level')).toBe('95%');
    expect(value('expected \\(dataset samples x epochs\\)')).toBe('8');
    expect(value('not run')).toBe('0');
  });

  it('says what was not recorded and marks a corpus mismatch', () => {
    const base = report();
    render(
      <RunFacts
        report={report({
          not_run: null,
          facts: {
            ...base.facts,
            revision: null,
            seeds: [],
            corpus_mismatch: true,
            sample_corpus_versions: ['2026-01', '2025-12'],
            token_usage: {},
            model_roles: {
              judge: [
                { model: 'mockllm/judge', generate_config: { temperature: 0 } },
              ],
            },
          },
        })}
      />,
    );
    expect(value('Revision')).toBe('not recorded');
    expect(value('Seeds')).toBe('not recorded');
    expect(value('not run')).toBe('unknown');
    expect(value('Model roles')).toBe('judge: mockllm/judge (temperature=0)');
    expect(value('Corpus version \\(task metadata\\)')).toBe(
      '2026-01 (samples: 2026-01, 2025-12) MISMATCH',
    );
    expect(screen.getAllByText('MISMATCH')).toHaveLength(2);
    expect(screen.getByText('No token usage recorded.')).toBeTruthy();
  });

  it('shows token usage with what the provider did not report', () => {
    render(<RunFacts report={report()} />);
    const row = screen.getByRole('row', { name: /^model mockllm\/model/ });
    expect(
      within(row)
        .getAllByRole('cell')
        .map((cell) => cell.textContent),
    ).toEqual([
      '10',
      'not reported',
      'not reported',
      '5',
      'not reported',
      '15',
      'not reported',
    ]);
  });

  it('shows the scalar fields of the manifest as text', () => {
    render(
      <RunFacts
        report={report()}
        manifest={{
          finding: '2026-01-01-a',
          cost: '<b>none</b>',
          files: { a: 'b' },
        }}
      />,
    );
    const published = screen.getByRole('region', { name: 'Published finding' });
    expect(within(published).getByText('<b>none</b>')).toBeTruthy();
    expect(within(published).queryByText('files')).toBeNull();
    expect(published.querySelector('b')).toBeNull();
  });

  it('prints numbers written as floats the way Python prints them', () => {
    const base = report();
    const facts = parseJson(
      '{"generate_config": {"temperature": 1.0, "max_tokens": 10, "top_p": 1e-05},' +
        ' "token_usage": {"m": {"input_tokens": 1, "output_tokens": 2,' +
        ' "input_tokens_cache_read": null, "input_tokens_cache_write": null,' +
        ' "reasoning_tokens": null, "total_tokens": 3, "total_cost": 0.0}}}',
    ) as Pick<Facts, 'generate_config' | 'token_usage'>;
    render(
      <RunFacts report={report({ facts: { ...base.facts, ...facts } })} />,
    );
    expect(value('Generate config \\(eval\\)')).toBe(
      'temperature=1.0, max_tokens=10, top_p=1e-05',
    );
    const row = screen.getByRole('row', { name: /^model m / });
    expect(
      within(row)
        .getAllByRole('cell')
        .map((cell) => cell.textContent),
    ).toEqual([
      '1',
      'not reported',
      'not reported',
      '2',
      'not reported',
      '3',
      '0.0',
    ]);
  });

  it('ends the Trials section with the terms the rates use', () => {
    render(<RunFacts report={report()} />);
    const trials = screen.getByRole('region', { name: 'Trials' });
    const last = Array.from(trials.querySelectorAll('p, table')).pop();
    expect(last?.textContent).toBe(TERMS);
  });
});
