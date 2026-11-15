// SPDX-License-Identifier: Apache-2.0
import { fireEvent, render, screen, within } from '@testing-library/react';
import { GROUPS, SECTIONS } from '../../sections';
import { finding, report } from '../../testing/fixtures';
import Sidebar, { type SidebarProps } from './sidebar';

function renderSidebar(props: Partial<SidebarProps> = {}) {
  const handlers = { onSelect: vi.fn(), onNavigate: vi.fn(), onClose: vi.fn() };
  render(
    <Sidebar
      id="sidebar"
      open={false}
      modal={false}
      findings={[finding('2026-03-01-b'), finding('2026-01-01-a')]}
      selectedId="2026-03-01-b"
      groups={[...GROUPS]}
      activeSection={SECTIONS.utility.id}
      {...handlers}
      {...props}
    />,
  );
  return handlers;
}

describe('Sidebar', () => {
  it('shows the brand, the findings, the section links and the footer line', () => {
    renderSidebar();
    expect(screen.getByText('Probo')).toBeTruthy();
    expect(screen.getByText('Static build. Read only.')).toBeTruthy();
    const findings = screen.getByRole('navigation', { name: 'Findings' });
    expect(within(findings).getAllByRole('button')).toHaveLength(2);
    const sections = screen.getByRole('navigation', { name: 'Sections' });
    const hrefs = within(sections)
      .getAllByRole('link')
      .map((link) => link.getAttribute('href'));
    expect(hrefs).toEqual([
      `#${SECTIONS.overview.id}`,
      ...GROUPS.flatMap((group) =>
        group.sections.map((section) => `#${SECTIONS[section].id}`),
      ),
    ]);
  });

  it('marks the selected finding and the section in view', () => {
    renderSidebar();
    const findings = screen.getByRole('navigation', { name: 'Findings' });
    const [newer, older] = within(findings).getAllByRole('button');
    expect(newer.getAttribute('aria-current')).toBe('true');
    expect(older.getAttribute('aria-current')).toBeNull();
    const current = screen
      .getAllByRole('link')
      .filter((link) => link.getAttribute('aria-current') !== null);
    expect(current.map((link) => link.textContent)).toEqual(['Utility']);
    expect(current[0].getAttribute('aria-current')).toBe('location');
  });

  it('reports a chosen finding and a followed link', () => {
    const { onSelect, onNavigate } = renderSidebar();
    fireEvent.click(screen.getByRole('button', { name: /^2026-01-01-a/ }));
    expect(onSelect).toHaveBeenCalledWith('2026-01-01-a');
    const delivery = screen.getByRole('link', { name: 'Delivery' });
    expect(fireEvent.click(delivery)).toBe(false);
    expect(onNavigate).toHaveBeenCalledWith(SECTIONS.delivery.id);
  });

  it('leaves a modified click to the browser', () => {
    const { onNavigate } = renderSidebar();
    const delivery = screen.getByRole('link', { name: 'Delivery' });
    expect(fireEvent.click(delivery, { ctrlKey: true })).toBe(true);
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it('shows finding ids and models as text, never as markup or links', () => {
    const hostile = '<img src=x onerror=alert(1)>';
    renderSidebar({
      findings: [
        finding(hostile, {
          report: report({
            facts: { ...report().facts, model: 'javascript:alert(1)' },
          }),
        }),
      ],
      selectedId: hostile,
    });
    const findings = screen.getByRole('navigation', { name: 'Findings' });
    expect(within(findings).getByRole('button').textContent).toBe(
      `${hostile} javascript:alert(1)`,
    );
    expect(findings.querySelector('img, a')).toBeNull();
  });

  it('says so when there are no findings, and has no section links', () => {
    renderSidebar({ findings: [], selectedId: undefined, groups: [] });
    expect(screen.getByText('None published.')).toBeTruthy();
    expect(screen.queryByRole('navigation', { name: 'Sections' })).toBeNull();
  });
});
