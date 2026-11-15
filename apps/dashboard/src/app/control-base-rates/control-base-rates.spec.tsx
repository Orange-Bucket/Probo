// SPDX-License-Identifier: Apache-2.0
import { render, screen } from '@testing-library/react';
import { counts, report } from '../../testing/fixtures';
import ControlBaseRates from './control-base-rates';

describe('ControlBaseRates', () => {
  it('shows the control trials and their rates', () => {
    render(<ControlBaseRates report={report()} />);
    expect(
      screen.getByText('Control trials: 4. With an error label: 0.'),
    ).toBeTruthy();
    expect(
      screen.getByRole('row', { name: /^completed, control trials/ }),
    ).toBeTruthy();
    expect(
      screen.getByRole('row', { name: /^attempted, control trials/ }),
    ).toBeTruthy();
  });

  it('names the error labels of control trials', () => {
    const base = report();
    render(
      <ControlBaseRates
        report={report({
          control: {
            ...base.control,
            errors: counts({ provider_error: 1, harness_error: 2 }),
          },
        })}
      />,
    );
    expect(
      screen.getByText(
        'Control trials: 4. With an error label: 3 (harness_error=2, provider_error=1).',
      ),
    ).toBeTruthy();
  });
});
