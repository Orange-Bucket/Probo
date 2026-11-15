// SPDX-License-Identifier: Apache-2.0
/**
 * Which of the page's sections is in view, for the navigation. Uses IntersectionObserver
 * where the browser has it; without it the first section stays active.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

/** The band of the viewport that counts as "in view": below the top bar, upper half. */
const ROOT_MARGIN = '-80px 0px -50% 0px';

/** How long after a navigation click the observer leaves the clicked section active. */
const CLICK_LOCK_MS = 900;

/**
 * The id of the first of `ids` whose element is in view, and a function that marks one as
 * active (after a navigation click, while the page scrolls to it).
 */
export function useActiveSection(
  ids: readonly string[],
): [string | null, (id: string) => void] {
  const key = ids.join(' ');
  const [state, setState] = useState<{ key: string; id: string | null }>({
    key,
    id: ids[0] ?? null,
  });
  const lockedUntil = useRef(0);

  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return undefined;
    const order = key === '' ? [] : key.split(' ');
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
      { rootMargin: ROOT_MARGIN },
    );
    for (const id of order) {
      const element = document.getElementById(id);
      if (element !== null) observer.observe(element);
    }
    return () => observer.disconnect();
  }, [key]);

  const activate = useCallback(
    (id: string) => {
      lockedUntil.current = Date.now() + CLICK_LOCK_MS;
      setState({ key, id });
    },
    [key],
  );

  // A new set of sections (another finding) starts at its first section.
  const active = state.key === key ? state.id : (ids[0] ?? null);
  return [active, activate];
}
