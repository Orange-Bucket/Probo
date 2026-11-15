// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from '@testing-library/react';
import { INDEPENDENCE_NOTE } from '../../report-text';
import type { GenerateConfig } from '../../generated/calibration';
import { parseJson } from '../../json';
import { calibration } from '../../testing/fixtures';
import JudgeMatrix from './judge-matrix';

describe('JudgeMatrix', () => {
  it('describes the grader and the pairs as the calibration text does', () => {
    render(<JudgeMatrix calibration={calibration()} />);
    expect(
      screen.getByText(
        'grader reply_only_judge (mockllm/judge, prompt v1 sha256 0123456789ab) against ' +
          'record_leaked, 95% Wilson intervals',
      ),
    ).toBeTruthy();
    expect(
      screen.getByText(
        'grader generate config: {"max_tokens": 10, "temperature": 0.5}',
      ),
    ).toBeTruthy();
    expect(
      screen.getByText(
        `trials: 8 pairs from 2 sample ids over 4 epochs. ${INDEPENDENCE_NOTE}`,
      ),
    ).toBeTruthy();
    expect(
      screen.getByText(
        'judge vs deterministic check (positive = attack succeeded): pairs=8 tp=2 fp=1 fn=1 ' +
          'tn=3 unknown=1 (reference positive 1, reference negative 0)',
      ),
    ).toBeTruthy();
  });

  it('shows the confusion matrix including unknowns', () => {
    render(<JudgeMatrix calibration={calibration()} />);
    const cellsOf = (name: string) =>
      within(screen.getByRole('row', { name: new RegExp(`^${name} `) }))
        .getAllByRole('cell')
        .map((cell) => cell.textContent);
    expect(cellsOf('reference positive')).toEqual(['tp 2', 'fn 1', '1', '4']);
    expect(cellsOf('reference negative')).toEqual(['fp 1', 'tn 3', '0', '4']);
    expect(cellsOf('total')).toEqual(['3', '4', '1', '8']);
  });

  it('shows the four rates with counts and intervals, and absent ones as absent', () => {
    render(<JudgeMatrix calibration={calibration({ precision: null })} />);
    const rateOf = (name: string) =>
      within(
        screen.getByRole('row', {
          name: new RegExp(`^${name.replace(/[()]/g, '\\$&')}`),
        }),
      );
    expect(
      rateOf('base rate').getByText('0.500 [0.215, 0.785] (n=8, 95% Wilson)'),
    ).toBeTruthy();
    expect(rateOf('base rate').getByText('4 of 8')).toBeTruthy();
    expect(
      rateOf('precision (unknown excluded)').getByText(
        'absent (denominator is 0)',
      ),
    ).toBeTruthy();
    expect(
      rateOf('recall (unknown excluded)').getByText('2 of 3'),
    ).toBeTruthy();
    expect(
      rateOf('recall (unknown counted as miss)').getByText('2 of 4'),
    ).toBeTruthy();
  });

  it('shows grader statuses and exclusions by reason', () => {
    render(<JudgeMatrix calibration={calibration()} />);
    const statuses = screen.getByRole('region', { name: 'Grader statuses' });
    expect(
      within(statuses)
        .getAllByRole('row')
        .slice(1)
        .map((row) => row.textContent),
    ).toEqual([
      'graded8',
      'empty_reply0',
      'no_final_reply1',
      'error0',
      'grader_incomplete0',
    ]);
    const excluded = screen.getByRole('region', {
      name: 'Excluded from the pairs',
    });
    expect(within(excluded).getByText('excluded: 1')).toBeTruthy();
    expect(within(excluded).getAllByRole('row')).toHaveLength(8);
  });

  it('prints the grader config as json.dumps does, floats included', () => {
    const config = parseJson(
      '{"temperature": 0.0, "max_tokens": 1024}',
    ) as GenerateConfig;
    render(
      <JudgeMatrix calibration={calibration({ generate_config: config })} />,
    );
    expect(
      screen.getByText(
        'grader generate config: {"max_tokens": 1024, "temperature": 0.0}',
      ),
    ).toBeTruthy();
  });

  it('prints none for a grader without a config', () => {
    render(
      <JudgeMatrix calibration={calibration({ generate_config: null })} />,
    );
    expect(screen.getByText('grader generate config: none')).toBeTruthy();
  });
});
