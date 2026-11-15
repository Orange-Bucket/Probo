// SPDX-License-Identifier: Apache-2.0
import { fireEvent, render, screen } from '@testing-library/react';
import { THEME_KEY } from '../../theme';
import ThemeToggle from './theme-toggle';

function toggle(): HTMLElement {
  return screen.getByRole('button', { name: 'Dark theme' });
}

afterEach(() => {
  vi.restoreAllMocks();
  try {
    window.localStorage.clear();
  } catch {
    // A test replaced storage.
  }
  delete document.documentElement.dataset['theme'];
});

describe('ThemeToggle', () => {
  it('follows the system until used: no data-theme attribute', () => {
    render(<ThemeToggle />);
    expect(document.documentElement.dataset['theme']).toBeUndefined();
    // jsdom has no matchMedia: the system counts as light.
    expect(toggle().getAttribute('aria-pressed')).toBe('false');
  });

  it('sets data-theme on the root and remembers the choice', () => {
    render(<ThemeToggle />);
    fireEvent.click(toggle());
    expect(document.documentElement.dataset['theme']).toBe('dark');
    expect(toggle().getAttribute('aria-pressed')).toBe('true');
    expect(window.localStorage.getItem(THEME_KEY)).toBe('dark');
    fireEvent.click(toggle());
    expect(document.documentElement.dataset['theme']).toBe('light');
    expect(window.localStorage.getItem(THEME_KEY)).toBe('light');
  });

  it('starts from a stored choice and ignores a stored value it does not know', () => {
    window.localStorage.setItem(THEME_KEY, 'dark');
    const { unmount } = render(<ThemeToggle />);
    expect(document.documentElement.dataset['theme']).toBe('dark');
    expect(toggle().getAttribute('aria-pressed')).toBe('true');
    unmount();
    delete document.documentElement.dataset['theme'];
    window.localStorage.setItem(THEME_KEY, 'url(x); color: red');
    render(<ThemeToggle />);
    expect(document.documentElement.dataset['theme']).toBeUndefined();
  });

  it('follows a dark system preference until used', () => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn((query: string) => ({
        matches: query.includes('dark'),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    );
    render(<ThemeToggle />);
    expect(toggle().getAttribute('aria-pressed')).toBe('true');
    expect(document.documentElement.dataset['theme']).toBeUndefined();
    fireEvent.click(toggle());
    expect(document.documentElement.dataset['theme']).toBe('light');
    vi.unstubAllGlobals();
  });

  it('still works when localStorage throws on every access', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('SecurityError');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    render(<ThemeToggle />);
    fireEvent.click(toggle());
    expect(document.documentElement.dataset['theme']).toBe('dark');
    expect(toggle().getAttribute('aria-pressed')).toBe('true');
  });

  it('still works when the localStorage property itself throws', () => {
    vi.spyOn(window, 'localStorage', 'get').mockImplementation(() => {
      throw new Error('SecurityError');
    });
    render(<ThemeToggle />);
    fireEvent.click(toggle());
    expect(document.documentElement.dataset['theme']).toBe('dark');
  });
});
