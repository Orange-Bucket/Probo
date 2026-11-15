// SPDX-License-Identifier: Apache-2.0
/**
 * The colour theme. By default the page follows the system (`prefers-color-scheme`); a
 * choice made with the theme toggle is kept in localStorage and set as `data-theme` on the
 * root element. Storage may be missing or throw (private windows, blocked site data), so
 * every access is guarded and the page works without it.
 */

export type Theme = 'light' | 'dark';

export const THEME_KEY = 'probo-dashboard-theme';

const DARK_QUERY = '(prefers-color-scheme: dark)';

/** The stored choice, or null when there is none or storage is unavailable. */
export function readStoredTheme(): Theme | null {
  try {
    const value = window.localStorage.getItem(THEME_KEY);
    return value === 'light' || value === 'dark' ? value : null;
  } catch {
    return null;
  }
}

/** Stores the choice; does nothing when storage is unavailable. */
export function storeTheme(theme: Theme): void {
  try {
    window.localStorage.setItem(THEME_KEY, theme);
  } catch {
    // The choice then lasts until the page is reloaded.
  }
}

/** Sets the theme on the root element, or removes it so the system preference applies. */
export function applyTheme(theme: Theme | null): void {
  const root = document.documentElement;
  if (theme === null) {
    delete root.dataset['theme'];
  } else {
    root.dataset['theme'] = theme;
  }
}

/** The system's dark mode media query, where the browser has one. */
export function darkQuery(): MediaQueryList | null {
  try {
    return typeof window.matchMedia === 'function'
      ? window.matchMedia(DARK_QUERY)
      : null;
  } catch {
    return null;
  }
}

/** Whether the user asked the system for reduced motion. */
export function prefersReducedMotion(): boolean {
  try {
    return (
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  } catch {
    return false;
  }
}
