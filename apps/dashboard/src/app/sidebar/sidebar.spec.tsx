// SPDX-License-Identifier: Apache-2.0
import { fireEvent, render, screen, within } from '@testing-library/react';
import { GROUPS, SECTIONS } from '../../sections';
import { finding, report } from '../../testing/fixtures';
import Sidebar, { type SidebarProps } from './sidebar';

function renderSidebar(props: Partial<SidebarProps> = {}) {
  const handlers = {
    onSelect: vi.fn(),
    onHome: vi.fn(),
    onNavigate: vi.fn(),
    onClose: vi.fn(),
  };
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
  it('shows the name as text alone, with no logo mark', () => {
    renderSidebar();
    const name = screen.getByText('Probo');
    const brand = name.parentElement as HTMLElement;
    // The only drawing beside the name is the close button's icon.
    for (const svg of Array.from(brand.querySelectorAll('svg'))) {
      expect(svg.closest('button')?.getAttribute('aria-label')).toBe(
        'Close navigation',
      );
    }
    expect(brand.querySelector('rect, circle')).toBeNull();
  });

  it('has no visible label over the section links, which keep their name', () => {
    renderSidebar();
    const sidebar = document.getElementById('sidebar') as HTMLElement;
    expect(sidebar.textContent).not.toContain('On this page');
    expect(screen.queryByText('On this page')).toBeNull();
    expect(screen.getByRole('navigation', { name: 'Sections' })).toBeTruthy();
  });

  it('starts with Home, current only while Home is shown', () => {
    const { onHome } = renderSidebar();
    const navs = screen.getAllByRole('navigation');
    expect(navs.map((nav) => nav.getAttribute('aria-label'))).toEqual([
      'Dashboard',
      'Findings',
      'Sections',
    ]);
    const home = within(navs[0]).getByRole('button', { name: 'Home' });
    expect(home.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true');
    expect(home.getAttribute('aria-current')).toBeNull();
    fireEvent.click(home);
    expect(onHome).toHaveBeenCalledTimes(1);
  });

  it('marks Home as the current page, and no finding, on Home', () => {
    renderSidebar({ selectedId: undefined, groups: [] });
    expect(
      screen.getByRole('button', { name: 'Home' }).getAttribute('aria-current'),
    ).toBe('page');
    const findings = screen.getByRole('navigation', { name: 'Findings' });
    for (const button of within(findings).getAllByRole('button')) {
      expect(button.getAttribute('aria-current')).toBeNull();
    }
    expect(screen.queryByRole('navigation', { name: 'Sections' })).toBeNull();
  });

  it('shows the findings, the section links and the footer line', () => {
    renderSidebar();
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
