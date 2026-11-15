// SPDX-License-Identifier: Apache-2.0
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { finding } from '../../testing/fixtures';
import AppShell, { MAIN_ID, SIDEBAR_ID, WIDE_QUERY } from './app-shell';

const FINDINGS = [finding('2026-03-01-b'), finding('2026-01-01-a')];

/** Renders the shell around a finding, or around Home with `{ home: true }`. */
function renderShell({ home = false } = {}) {
  const selected = home ? undefined : FINDINGS[0];
  const onSelect = vi.fn();
  const onHome = vi.fn();
  render(
    <AppShell
      findings={FINDINGS}
      selected={selected}
      onSelect={onSelect}
      onHome={onHome}
    >
      <p>Content.</p>
    </AppShell>,
  );
  return {
    menu: screen.getByRole('button', { name: 'Navigation' }),
    sidebar: document.getElementById(SIDEBAR_ID) as HTMLElement,
    onSelect,
    onHome,
  };
}

describe('AppShell', () => {
  it('puts the children in the main landmark, after a skip link to it', () => {
    renderShell();
    const main = screen.getByRole('main');
    expect(main.id).toBe(MAIN_ID);
    expect(within(main).getByText('Content.')).toBeTruthy();
    const skip = screen.getByRole('link', { name: 'Skip to content' });
    expect(skip.getAttribute('href')).toBe(`#${MAIN_ID}`);
    fireEvent.click(skip);
    expect(document.activeElement).toBe(main);
  });

  it('opens the navigation drawer from the menu button and moves focus into it', () => {
    const { menu, sidebar } = renderShell();
    expect(menu.getAttribute('aria-expanded')).toBe('false');
    expect(menu.getAttribute('aria-controls')).toBe(SIDEBAR_ID);
    expect(sidebar.dataset['open']).toBe('false');
    fireEvent.click(menu);
    expect(menu.getAttribute('aria-expanded')).toBe('true');
    expect(sidebar.dataset['open']).toBe('true');
    // Focus goes to the selected finding.
    expect(document.activeElement?.getAttribute('aria-current')).toBe('true');
    expect(sidebar.contains(document.activeElement)).toBe(true);
  });

  it('closes the drawer on Escape and returns focus to the menu button', () => {
    const { menu, sidebar } = renderShell();
    fireEvent.click(menu);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(menu.getAttribute('aria-expanded')).toBe('false');
    expect(sidebar.dataset['open']).toBe('false');
    expect(document.activeElement).toBe(menu);
  });

  it('closes the drawer with its own close button and with the menu button', () => {
    const { menu } = renderShell();
    fireEvent.click(menu);
    fireEvent.click(screen.getByRole('button', { name: 'Close navigation' }));
    expect(menu.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(menu);
    fireEvent.click(menu);
    fireEvent.click(menu);
    expect(menu.getAttribute('aria-expanded')).toBe('false');
  });

  it('closes the drawer when a finding is chosen and focuses the page title', () => {
    const { menu, onSelect } = renderShell();
    fireEvent.click(menu);
    const nav = screen.getByRole('navigation', { name: 'Findings' });
    fireEvent.click(within(nav).getByRole('button', { name: /^2026-01-01-a/ }));
    expect(onSelect).toHaveBeenCalledWith('2026-01-01-a');
    expect(menu.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement?.tagName).toBe('H1');
  });

  it('closes the drawer when Home is chosen and focuses the page title', () => {
    const { menu, onHome, onSelect } = renderShell();
    fireEvent.click(menu);
    fireEvent.click(screen.getByRole('button', { name: 'Home' }));
    expect(onHome).toHaveBeenCalledTimes(1);
    expect(onSelect).not.toHaveBeenCalled();
    expect(menu.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement?.tagName).toBe('H1');
  });

  it('on Home, is titled Home and opens the drawer with focus on Home', () => {
    const { menu, sidebar } = renderShell({ home: true });
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Home');
    expect(screen.queryByRole('navigation', { name: 'Sections' })).toBeNull();
    fireEvent.click(menu);
    const home = within(sidebar).getByRole('button', { name: 'Home' });
    expect(home.getAttribute('aria-current')).toBe('page');
    expect(document.activeElement).toBe(home);
  });

  it('keeps Tab inside the open drawer', () => {
    const { menu, sidebar } = renderShell();
    fireEvent.click(menu);
    const items = Array.from(
      sidebar.querySelectorAll<HTMLElement>('a[href], button'),
    );
    const first = items[0];
    const last = items[items.length - 1];
    last.focus();
    fireEvent.keyDown(last, { key: 'Tab' });
    expect(document.activeElement).toBe(first);
    fireEvent.keyDown(first, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(last);
  });

  it('ignores Escape while the drawer is closed', () => {
    const { menu } = renderShell();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(menu.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).not.toBe(menu);
  });

  it('is ordinary navigation while closed: no dialog, nothing inert', () => {
    const { sidebar } = renderShell();
    expect(sidebar.getAttribute('role')).toBeNull();
    expect(sidebar.hasAttribute('aria-modal')).toBe(false);
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(screen.getAllByRole('navigation')).toHaveLength(3);
    expect(screen.getByRole('main').closest('[inert]')).toBeNull();
    expect(
      screen
        .getByRole('link', { name: 'Skip to content' })
        .hasAttribute('inert'),
    ).toBe(false);
  });

  it('is a labelled modal dialog while open, with the rest of the page inert', () => {
    const { menu, sidebar } = renderShell();
    fireEvent.click(menu);
    const dialog = screen.getByRole('dialog', { name: 'Navigation' });
    expect(dialog).toBe(sidebar);
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    const main = document.getElementById(MAIN_ID) as HTMLElement;
    const banner = document.querySelector('header') as HTMLElement;
    expect(main.closest('[inert]')).not.toBeNull();
    expect(banner.closest('[inert]')).not.toBeNull();
    expect(
      document.querySelector('a[href="#main"]')?.hasAttribute('inert'),
    ).toBe(true);
    expect(sidebar.closest('[inert]')).toBeNull();
    // Closing restores both, and focus goes back to the menu button once it can.
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(sidebar.getAttribute('role')).toBeNull();
    expect(main.closest('[inert]')).toBeNull();
    expect(document.activeElement).toBe(menu);
  });

  it('closes when the screen becomes wide, where the sidebar is not a dialog', () => {
    let notify: (event: { matches: boolean }) => void = () => undefined;
    vi.stubGlobal(
      'matchMedia',
      vi.fn((query: string) => ({
        matches: false,
        media: query,
        addEventListener: (_: string, listener: typeof notify) => {
          if (query === WIDE_QUERY) notify = listener;
        },
        removeEventListener: vi.fn(),
      })),
    );
    const { menu, sidebar } = renderShell();
    fireEvent.click(menu);
    expect(sidebar.getAttribute('role')).toBe('dialog');
    act(() => notify({ matches: true }));
    expect(sidebar.getAttribute('role')).toBeNull();
    expect(screen.getByRole('main').closest('[inert]')).toBeNull();
    vi.unstubAllGlobals();
  });
});
