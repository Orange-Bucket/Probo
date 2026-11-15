// SPDX-License-Identifier: Apache-2.0
import { fireEvent, render, screen, within } from '@testing-library/react';
import { finding } from '../../testing/fixtures';
import AppShell, { MAIN_ID, SIDEBAR_ID } from './app-shell';

const FINDINGS = [finding('2026-03-01-b'), finding('2026-01-01-a')];

function renderShell(onSelect = vi.fn()) {
  render(
    <AppShell findings={FINDINGS} selected={FINDINGS[0]} onSelect={onSelect}>
      <p>Content.</p>
    </AppShell>,
  );
  return {
    menu: screen.getByRole('button', { name: 'Navigation' }),
    sidebar: document.getElementById(SIDEBAR_ID) as HTMLElement,
    onSelect,
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
});
