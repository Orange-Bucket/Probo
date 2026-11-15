// SPDX-License-Identifier: Apache-2.0
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
} from 'react';
import type { Finding } from '../../findings';
import { useActiveSection, useScrollOffset } from '../../scroll-spy';
import { findingGroups, sectionIds } from '../../sections';
import { prefersReducedMotion } from '../../theme';
import Sidebar from '../sidebar/sidebar';
import TopBar from '../top-bar/top-bar';
import styles from './app-shell.module.css';

export const SIDEBAR_ID = 'sidebar';
export const MAIN_ID = 'main';

/**
 * Wide screens show the sidebar beside the content; narrow ones behind the menu button.
 * The stylesheets use the complementary `(width < 64rem)`, so no width is in neither.
 */
export const WIDE_QUERY = '(width >= 64rem)';

function focusables(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>('a[href], button:not([disabled])'),
  );
}

export interface AppShellProps {
  /** Every finding, newest first. */
  findings: Finding[];
  /** The finding shown, or undefined on Home. */
  selected: Finding | undefined;
  onSelect: (id: string) => void;
  /** Shows Home. */
  onHome: () => void;
  /** The content of the main landmark. */
  children: ReactNode;
}

/**
 * The application frame: a skip link, the sidebar (a drawer on narrow screens, opened by
 * the top bar's menu button and closed by Escape, the backdrop or a choice), the top bar
 * and the main landmark. Sidebar and top bar are one frame around the main panel.
 */
export function AppShell({
  findings,
  selected,
  onSelect,
  onHome,
  children,
}: AppShellProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const topBar = useRef<HTMLElement>(null);
  /** What to focus once the drawer has closed and the content is no longer inert. */
  const afterClose = useRef<(() => void) | null>(null);
  const groups = selected === undefined ? [] : findingGroups(selected);
  const offset = useScrollOffset(topBar);
  const [active, activate] = useActiveSection(
    selected === undefined ? [] : sectionIds(selected),
    selected?.id ?? '',
    offset,
  );

  /** Closes the drawer, then runs `then` (by default: focus the menu button). */
  const closeMenu = useCallback(
    (then: () => void = () => menuButton.current?.focus()) => {
      afterClose.current = then;
      setMenuOpen(false);
    },
    [],
  );

  useEffect(() => {
    if (menuOpen || afterClose.current === null) return;
    const then = afterClose.current;
    afterClose.current = null;
    then();
  }, [menuOpen]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const sidebar = document.getElementById(SIDEBAR_ID);
    if (sidebar !== null) {
      // The page shown: the selected finding, or Home.
      const current = sidebar.querySelector<HTMLElement>(
        '[aria-current="true"], [aria-current="page"]',
      );
      (current ?? focusables(sidebar)[0])?.focus();
    }
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        closeMenu();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [menuOpen, closeMenu]);

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return undefined;
    const wide = window.matchMedia(WIDE_QUERY);
    if (typeof wide.addEventListener !== 'function') return undefined;
    const update = (event: MediaQueryListEvent) => {
      if (event.matches) setMenuOpen(false);
    };
    wide.addEventListener('change', update);
    return () => wide.removeEventListener('change', update);
  }, []);

  /** While the drawer is open, Tab and Shift+Tab stay inside it. */
  const trapFocus = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!menuOpen || event.key !== 'Tab') return;
    const items = focusables(event.currentTarget);
    if (items.length === 0) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const navigate = (id: string) => {
    const go = () => {
      const target = document.getElementById(id);
      if (target === null) return;
      target
        .querySelector<HTMLElement>('h3, h4')
        ?.focus({ preventScroll: true });
      target.scrollIntoView?.({
        behavior: prefersReducedMotion() ? 'auto' : 'smooth',
        block: 'start',
      });
    };
    activate(id);
    if (menuOpen) closeMenu(go);
    else go();
  };

  /** Shows another page; a choice in the open drawer closes it and focuses the h1. */
  const show = (go: () => void) => {
    go();
    if (menuOpen)
      closeMenu(() => document.querySelector<HTMLElement>('h1')?.focus());
  };

  const skip = (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    document.getElementById(MAIN_ID)?.focus();
  };

  return (
    <div className={styles['shell']}>
      <a
        className={styles['skip']}
        href={`#${MAIN_ID}`}
        onClick={skip}
        inert={menuOpen}
      >
        Skip to content
      </a>
      <Sidebar
        id={SIDEBAR_ID}
        open={menuOpen}
        modal={menuOpen}
        findings={findings}
        selectedId={selected?.id}
        onSelect={(id) => show(() => onSelect(id))}
        onHome={() => show(onHome)}
        groups={groups}
        activeSection={active}
        onNavigate={navigate}
        onClose={() => closeMenu()}
        onKeyDown={trapFocus}
      />
      {menuOpen && (
        <div
          className={styles['backdrop']}
          aria-hidden="true"
          onClick={() => closeMenu()}
        />
      )}
      {/* While the drawer is open it is a modal dialog: the rest of the page is inert. */}
      <div className={styles['content']} inert={menuOpen}>
        <TopBar
          barRef={topBar}
          finding={selected}
          menuId={SIDEBAR_ID}
          menuOpen={menuOpen}
          onMenuToggle={() => (menuOpen ? closeMenu() : setMenuOpen(true))}
          menuButtonRef={menuButton}
        />
        <main id={MAIN_ID} tabIndex={-1} className={styles['main']}>
          {children}
        </main>
      </div>
    </div>
  );
}

export default AppShell;
