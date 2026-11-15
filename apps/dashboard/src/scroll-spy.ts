// SPDX-License-Identifier: Apache-2.0
/**
 * Which of the page's sections is in view, for the navigation, and how far below the top
 * of the viewport a section counts as reached. One value serves both: the measured height
 * of the top bar plus a gap. It is the band the observer watches and, as the CSS variable
 * `--scroll-offset`, the `scroll-margin-top` of every section, so a section scrolled to
 * lands exactly where the observer starts counting it as in view.
 */
import {
  useCallback,
  useEffect,
  useState,
  useRef,
  type RefObject,
} from 'react';

/** Space between the bottom of the top bar and a section scrolled to it, in px. */
export const SCROLL_GAP = 16;

/** The offset until the top bar is measured: the CSS default of `--scroll-offset` (5rem). */
export const DEFAULT_OFFSET = 80;

/** How long after a navigation click the observer leaves the clicked section active. */
const CLICK_LOCK_MS = 900;

/**
 * The scroll offset in px, kept equal to the height of `bar` plus `SCROLL_GAP` and written
 * to `--scroll-offset` on the root element. Without ResizeObserver it stays the default.
 */
export function useScrollOffset(bar: RefObject<HTMLElement | null>): number {
  const [offset, setOffset] = useState(DEFAULT_OFFSET);
  useEffect(() => {
    const element = bar.current;
    if (element === null || typeof ResizeObserver === 'undefined')
      return undefined;
    const root = document.documentElement;
    const update = () => {
      const next =
        Math.ceil(element.getBoundingClientRect().height) + SCROLL_GAP;
      root.style.setProperty('--scroll-offset', `${next}px`);
      setOffset(next);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => {
      observer.disconnect();
      root.style.removeProperty('--scroll-offset');
    };
  }, [bar]);
  return offset;
}

/**
 * The id of the first of `ids` whose element is in view, and a function that marks one as
 * active (after a navigation click, while the page scrolls to it).
 *
 * `scope` names what the ids belong to (the finding shown). Section ids are the same for
 * every finding, so a new scope re-observes the new elements and starts again at the
 * first section even when the ids are unchanged. `offset` is the top of the band that
 * counts as in view, in px below the viewport top; the band reaches down to the middle.
 */
export function useActiveSection(
  ids: readonly string[],
  scope: string,
  offset: number = DEFAULT_OFFSET,
): [string | null, (id: string) => void] {
  const key = `${scope}\n${ids.join(' ')}`;
  const [state, setState] = useState<{ key: string; id: string | null }>({
    key,
    id: ids[0] ?? null,
  });
  const lockedUntil = useRef(0);

  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return undefined;
    const order = key
      .slice(key.indexOf('\n') + 1)
      .split(' ')
      .filter(Boolean);
    const visible = new Set<string>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) visible.add(entry.target.id);
          else visible.delete(entry.target.id);
        }
        if (Date.now() < lockedUntil.current) return;
        const first = order.find((id) => visible.has(id));
        if (first !== undefined) setState({ key, id: first });
      },
      { rootMargin: `-${Math.round(offset)}px 0px -50% 0px` },
    );
    for (const id of order) {
      const element = document.getElementById(id);
      if (element !== null) observer.observe(element);
    }
    return () => observer.disconnect();
  }, [key, offset]);

  const activate = useCallback(
    (id: string) => {
      lockedUntil.current = Date.now() + CLICK_LOCK_MS;
      setState({ key, id });
    },
    [key],
  );

  // Another scope (another finding) starts at its first section.
  const active = state.key === key ? state.id : (ids[0] ?? null);
  return [active, activate];
}
