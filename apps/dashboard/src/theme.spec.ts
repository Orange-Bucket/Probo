// SPDX-License-Identifier: Apache-2.0
import {
  THEME_KEY,
  applyTheme,
  darkQuery,
  prefersReducedMotion,
  readStoredTheme,
  storeTheme,
} from './theme';

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  delete document.documentElement.dataset['theme'];
});

function throwingStorage() {
  vi.spyOn(window, 'localStorage', 'get').mockImplementation(() => {
    throw new Error('SecurityError');
  });
}

describe('readStoredTheme and storeTheme', () => {
  it('round-trip light and dark', () => {
    expect(readStoredTheme()).toBeNull();
    storeTheme('dark');
    expect(window.localStorage.getItem(THEME_KEY)).toBe('dark');
    expect(readStoredTheme()).toBe('dark');
    storeTheme('light');
    expect(readStoredTheme()).toBe('light');
  });

  it.each(['', 'Dark', 'system', 'url(x)', '{"theme":"dark"}'])(
    'ignore the stored value %j',
    (value) => {
      window.localStorage.setItem(THEME_KEY, value);
      expect(readStoredTheme()).toBeNull();
    },
  );

  it('never throw when storage throws', () => {
    throwingStorage();
    expect(readStoredTheme()).toBeNull();
    expect(() => storeTheme('dark')).not.toThrow();
  });

  it('never throw when a write is refused', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    expect(() => storeTheme('dark')).not.toThrow();
  });
});

describe('applyTheme', () => {
  it('sets data-theme, and removes it for the system preference', () => {
    applyTheme('dark');
    expect(document.documentElement.dataset['theme']).toBe('dark');
    applyTheme('light');
    expect(document.documentElement.dataset['theme']).toBe('light');
    applyTheme(null);
    expect(document.documentElement.hasAttribute('data-theme')).toBe(false);
  });
});

describe('darkQuery and prefersReducedMotion', () => {
  it('are null and false where the browser has no matchMedia', () => {
    expect(darkQuery()).toBeNull();
    expect(prefersReducedMotion()).toBe(false);
  });

  it('read the media queries where it has one', () => {
    const matchMedia = vi.fn((query: string) => ({
      matches: true,
      media: query,
    }));
    vi.stubGlobal('matchMedia', matchMedia);
    expect(darkQuery()?.media).toBe('(prefers-color-scheme: dark)');
    expect(prefersReducedMotion()).toBe(true);
    expect(matchMedia).toHaveBeenCalledWith('(prefers-reduced-motion: reduce)');
  });

  it('are null and false when matchMedia throws', () => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn(() => {
        throw new Error('no');
      }),
    );
    expect(darkQuery()).toBeNull();
    expect(prefersReducedMotion()).toBe(false);
  });
});
