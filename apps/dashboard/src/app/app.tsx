// SPDX-License-Identifier: Apache-2.0
import { useEffect, useMemo, useState } from 'react';
import { FINDINGS, type Finding } from '../findings';
import { currentHash, findingFromHash, pushHash } from '../hash';
import AppShell from './app-shell/app-shell';
import FindingView from './finding-view/finding-view';
import Icon from './icon/icon';
import styles from './app.module.css';

export interface AppProps {
  /** The findings to show, newest first; the published findings by default. */
  findings?: Finding[];
}

/**
 * The dashboard: the selected finding (from the URL hash when it names a known finding,
 * else the newest) in the application shell, or an empty state when none is published.
 */
export function App({ findings = FINDINGS }: AppProps) {
  const ids = useMemo(() => findings.map((f) => f.id), [findings]);
  const [selectedId, setSelectedId] = useState(
    () => findingFromHash(currentHash(), ids) ?? ids[0],
  );

  useEffect(() => {
    // Back, forward and edited URLs select a known finding; anything else is ignored.
    const follow = () => {
      const id = findingFromHash(window.location.hash, ids);
      if (id !== null) setSelectedId(id);
    };
    window.addEventListener('hashchange', follow);
    window.addEventListener('popstate', follow);
    return () => {
      window.removeEventListener('hashchange', follow);
      window.removeEventListener('popstate', follow);
    };
  }, [ids]);

  const finding = findings.find((f) => f.id === selectedId) ?? findings[0];
  const select = (id: string) => {
    if (!ids.includes(id)) return;
    setSelectedId(id);
    pushHash(id);
    (document.scrollingElement ?? document.documentElement).scrollTop = 0;
  };

  return (
    <AppShell findings={findings} selected={finding} onSelect={select}>
      {finding === undefined ? (
        <div className={styles['empty']}>
          <Icon name="inbox" className={styles['emptyIcon']} />
          <h2 className={styles['emptyTitle']}>Nothing to show yet</h2>
          <p>No findings are published.</p>
          <p className="muted">
            A finding appears here when its report.json is in the findings
            directory at build time.
          </p>
        </div>
      ) : (
        <FindingView key={finding.id} finding={finding} />
      )}
    </AppShell>
  );
}

export default App;
