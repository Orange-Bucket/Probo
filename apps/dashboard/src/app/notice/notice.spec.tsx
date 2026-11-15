// SPDX-License-Identifier: Apache-2.0
import { render, screen } from '@testing-library/react';
import Notice from './notice';

describe('Notice', () => {
  it('shows an info note as plain, visible text that is not an alert', () => {
    render(
      <Notice tone="info">
        <p>One.</p>
        <p>Two.</p>
      </Notice>,
    );
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByText('One.')).toBeTruthy();
    expect(screen.getByText('Two.')).toBeTruthy();
  });

  it('makes a warning an alert whose text is only the warning', () => {
    render(
      <Notice tone="warning">
        <p>
          <strong>WARNING: x</strong>
        </p>
      </Notice>,
    );
    expect(screen.getByRole('alert').textContent).toBe('WARNING: x');
  });
});
