// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from 'react';
import {
  applyTheme,
  darkQuery,
  readStoredTheme,
  storeTheme,
  type Theme,
} from '../../theme';
import Icon from '../icon/icon';
import styles from './theme-toggle.module.css';

/**
 * Switches between the light and dark theme. Until it is used the page follows the system;
 * the choice is then kept (when storage works) and set as `data-theme` on the root.
 */
export function ThemeToggle() {
  const [choice, setChoice] = useState<Theme | null>(readStoredTheme);
  const [systemDark, setSystemDark] = useState(
    () => darkQuery()?.matches ?? false,
  );

  useEffect(() => {
    const query = darkQuery();
    if (query === null || typeof query.addEventListener !== 'function')
      return undefined;
    const update = (event: MediaQueryListEvent) => setSystemDark(event.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);

  useEffect(() => applyTheme(choice), [choice]);

  const dark = choice === null ? systemDark : choice === 'dark';
  const toggle = () => {
    const next: Theme = dark ? 'light' : 'dark';
    setChoice(next);
    storeTheme(next);
  };
  return (
    <button
      type="button"
      className={styles['toggle']}
      aria-pressed={dark}
      aria-label="Dark theme"
      title={dark ? 'Switch to the light theme' : 'Switch to the dark theme'}
      onClick={toggle}
    >
      <Icon name={dark ? 'moon' : 'sun'} />
    </button>
  );
}

export default ThemeToggle;
