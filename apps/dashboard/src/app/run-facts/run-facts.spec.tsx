// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import { report } from '../../testing/fixtures';
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
});
