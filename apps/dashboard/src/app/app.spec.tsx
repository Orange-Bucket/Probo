// SPDX-License-Identifier: Apache-2.0
import { fireEvent, render, screen } from '@testing-library/react';
import type { Finding } from '../findings';
import {
  CORPUS_WARNING,
  EVIDENCE_SENTENCE,
  INCOMPLETE_WARNING,
  INDEPENDENCE_SENTENCE,
  TERMS,
} from '../report-text';
import { calibration, report } from '../testing/fixtures';
import App from './app';

function finding(id: string, values: Partial<Finding> = {}): Finding {
  return {
    id,
    report: report(),
    calibration: calibration(),
    manifest: null,
    ...values,
  };
}

describe('App', () => {
  it('always shows the two fixed sentences and the terms at the top of a finding', () => {
    render(<App findings={[finding('2026-01-01-a', { calibration: null })]} />);
    const article = screen.getByRole('article');
    const evidence = screen.getByText(EVIDENCE_SENTENCE);
    const independence = screen.getByText(INDEPENDENCE_SENTENCE);
    const firstSection = article.querySelector('section');
    for (const sentence of [evidence, independence]) {
      expect(article.contains(sentence)).toBe(true);
      expect(
        firstSection !== null &&
          sentence.compareDocumentPosition(firstSection) &
            Node.DOCUMENT_POSITION_FOLLOWING,
      ).toBeTruthy();
    }
    expect(screen.getByText(TERMS)).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('shows an incomplete run warning prominently', () => {
    const incomplete = report({
      incomplete: true,
      not_run: 2,
      warnings: [INCOMPLETE_WARNING],
    });
    render(
      <App findings={[finding('2026-01-01-a', { report: incomplete })]} />,
    );
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toBe(INCOMPLETE_WARNING);
    expect(alert.querySelector('strong')?.textContent).toBe(INCOMPLETE_WARNING);
  });

  it('shows a corpus mismatch warning even when the report lists none', () => {
    const base = report();
    const mixed = report({ facts: { ...base.facts, corpus_mismatch: true } });
    render(<App findings={[finding('2026-01-01-a', { report: mixed })]} />);
    expect(screen.getByRole('alert').textContent).toBe(CORPUS_WARNING);
  });

  it('shows the newest finding first and switches on choice', () => {
    const newer = finding('2026-03-01-b');
    const older = finding('2026-01-01-a', {
      report: report({ facts: { ...report().facts, task: 'probo/older' } }),
      calibration: null,
    });
    render(<App findings={[newer, older]} />);
    expect(
      screen.getByRole('heading', { name: 'Probo run report: probo/example' }),
    ).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Disagreements' })).toBeTruthy();
    fireEvent.change(screen.getByRole('combobox', { name: 'Finding' }), {
      target: { value: '2026-01-01-a' },
    });
    expect(
      screen.getByRole('heading', { name: 'Probo run report: probo/older' }),
    ).toBeTruthy();
    expect(
      screen.getByText('This finding has no judge calibration.'),
    ).toBeTruthy();
  });

  it('says so when no finding is published', () => {
    render(<App findings={[]} />);
    expect(screen.getByText('No findings are published.')).toBeTruthy();
  });
});
