// SPDX-License-Identifier: Apache-2.0
import { useEffect, useMemo, useRef, useState } from 'react';
import { FINDINGS, type Finding } from '../findings';
import { currentHash, findingFromHash, pushHash } from '../hash';
import AppShell from './app-shell/app-shell';
import FindingView from './finding-view/finding-view';
import Home from './home/home';

export interface AppProps {
  /** The findings to show, newest first; the published findings by default. */
  findings?: Finding[];
}

/**
 * The dashboard in the application shell: the finding the URL hash names when it names a
 * known one, else Home (which also says so when no finding is published).
 */
export function App({ findings = FINDINGS }: AppProps) {
  const ids = useMemo(() => findings.map((f) => f.id), [findings]);
  /** The id of the finding shown, or null for Home. */
  const [selectedId, setSelectedId] = useState(() =>
    findingFromHash(currentHash(), ids),
  );

  useEffect(() => {
    // Back, forward and edited URLs show the finding they name, and Home for anything else.
    const follow = () =>
      setSelectedId(findingFromHash(window.location.hash, ids));
    window.addEventListener('hashchange', follow);
    window.addEventListener('popstate', follow);
    return () => {
      window.removeEventListener('hashchange', follow);
      window.removeEventListener('popstate', follow);
    };
  }, [ids]);

  /** Set by a choice made in the page itself, whose button the new page removes. */
  const focusTitle = useRef(false);
  useEffect(() => {
    if (!focusTitle.current) return;
    focusTitle.current = false;
    document.querySelector<HTMLElement>('h1')?.focus();
  }, [selectedId]);

  const finding = findings.find((f) => f.id === selectedId);
  /** Shows the finding `id`, or Home for null, as a new history entry, from the top. */
  const show = (id: string | null) => {
    // Home chosen on Home (an unknown hash showed it) only tidies the URL.
    pushHash(id, id === null && selectedId === null);
    setSelectedId(id);
    (document.scrollingElement ?? document.documentElement).scrollTop = 0;
  };
  const select = (id: string) => {
    if (ids.includes(id)) show(id);
  };

  return (
    <AppShell
      findings={findings}
      selected={finding}
      onSelect={select}
      onHome={() => show(null)}
    >
      {finding === undefined ? (
        <Home
          findings={findings}
          onSelect={(id) => {
            focusTitle.current = ids.includes(id) && id !== selectedId;
            select(id);
          }}
        />
      ) : (
        <FindingView key={finding.id} finding={finding} />
      )}
    </AppShell>
  );
}

export default App;
