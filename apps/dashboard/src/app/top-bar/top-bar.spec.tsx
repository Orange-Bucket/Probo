// SPDX-License-Identifier: Apache-2.0
import { fireEvent, render, screen, within } from '@testing-library/react';
import { finding, report } from '../../testing/fixtures';
import TopBar, { EMPTY_TITLE, runDate } from './top-bar';

function renderBar(props: Partial<Parameters<typeof TopBar>[0]> = {}) {
  const onMenuToggle = vi.fn();
  render(
    <TopBar
      finding={finding('2026-01-01-a')}
      menuId="sidebar"
      menuOpen={false}
      onMenuToggle={onMenuToggle}
      {...props}
    />,
  );
  return { onMenuToggle, banner: screen.getByRole('banner') };
}

describe('TopBar', () => {
  it('titles the page with the finding id, its status, model and date', () => {
    const { banner } = renderBar();
    expect(within(banner).getByRole('heading', { level: 1 }).textContent).toBe(
      '2026-01-01-a',
    );
    expect(within(banner).getByText('complete')).toBeTruthy();
    expect(within(banner).getByText('mockllm/model')).toBeTruthy();
    expect(within(banner).getByText('2026-01-01')).toBeTruthy();
    expect(
      within(banner).getByRole('button', { name: 'Dark theme' }),
    ).toBeTruthy();
  });

  it('shows an incomplete run as incomplete', () => {
    renderBar({
      finding: finding('2026-01-01-a', { report: report({ not_run: 3 }) }),
    });
    expect(screen.getByText('incomplete')).toBeTruthy();
    expect(screen.queryByText('complete')).toBeNull();
  });

  it('has a menu button that says whether the navigation is open', () => {
    const { onMenuToggle } = renderBar({ menuOpen: true });
    const menu = screen.getByRole('button', { name: 'Navigation' });
    expect(menu.getAttribute('aria-expanded')).toBe('true');
    expect(menu.getAttribute('aria-controls')).toBe('sidebar');
    fireEvent.click(menu);
    expect(onMenuToggle).toHaveBeenCalledTimes(1);
  });

  it('has a plain title and no status without a finding', () => {
    renderBar({ finding: undefined });
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(
      EMPTY_TITLE,
    );
    expect(screen.queryByText('complete')).toBeNull();
  });
});

describe('runDate', () => {
  it('is the recorded date of the start time, or not recorded', () => {
    expect(runDate('2026-11-14T19:35:04+00:00')).toBe('2026-11-14');
    expect(runDate(null)).toBe('not recorded');
    expect(runDate('')).toBe('not recorded');
    expect(runDate('yesterday')).toBe('yesterday');
  });
});
