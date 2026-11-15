// SPDX-License-Identifier: Apache-2.0
import { useId } from 'react';
import type { Finding } from '../../findings';
import { runDate, runStatus } from '../../report-text';
import Icon from '../icon/icon';
import StatusChip from '../status-chip/status-chip';
import styles from './home.module.css';

export interface HomeProps {
  /** Every finding, newest first. */
  findings: Finding[];
  /** Opens the finding `id`. */
  onSelect: (id: string) => void;
}

/** What the count of published findings counts: `finding` for one, else `findings`. */
export function findingsNoun(count: number): string {
  return count === 1 ? 'finding' : 'findings';
}

/**
 * Home: what the dashboard offers, as feature cards. The one feature is the finding
 * reports: the number published, the newest to open, and every finding (id, model, run
 * date and status, all from its report) to open; or the empty state when none is published.
 */
export function Home({ findings, onSelect }: HomeProps) {
  const titleId = useId();
  const newest = findings[0];
  return (
    <div className={styles['home']}>
      <div className={styles['intro']}>
        <h2 className={styles['title']}>Probo dashboard</h2>
        <p className={styles['lead']}>
          The findings Probo has published, bundled into this read-only build.
        </p>
      </div>
      <div className={styles['features']}>
        <section aria-labelledby={titleId} className={styles['feature']}>
          <div className={styles['featureHeader']}>
            <Icon name="file" className={styles['tile']} />
            <div className={styles['featureText']}>
              <h3 id={titleId} className={styles['featureTitle']}>
                Finding reports
              </h3>
              <div className={styles['featureCaption']}>
                Each published finding as its run report prints it, with its
                judge calibration where it has one.
              </div>
            </div>
          </div>
          {newest === undefined ? (
            <div className={styles['empty']}>
              <Icon name="inbox" className={styles['tile']} />
              <h4 className={styles['emptyTitle']}>Nothing to show yet</h4>
              <p>No findings are published.</p>
              <p className="muted">
                A finding appears here when its report.json is in the findings
                directory at build time.
              </p>
            </div>
          ) : (
            <>
              <div className={styles['summary']}>
                <div className={styles['count']}>
                  <span className={styles['figure']}>{findings.length}</span>{' '}
                  <span className={styles['countLabel']}>
                    {findingsNoun(findings.length)} published
                  </span>
                </div>
                <button
                  type="button"
                  className={styles['action']}
                  onClick={() => onSelect(newest.id)}
                >
                  <span>Open the newest finding</span>
                  <Icon name="arrow" />
                </button>
              </div>
              <h4 className={styles['listTitle']}>Published findings</h4>
              <ul className={styles['list']}>
                {findings.map((finding) => (
                  <li key={finding.id}>
                    <button
                      type="button"
                      className={styles['entry']}
                      onClick={() => onSelect(finding.id)}
                    >
                      <span className={styles['entryText']}>
                        <span className={styles['entryId']}>{finding.id}</span>{' '}
                        <span className={styles['entryMeta']}>
                          <span className={styles['model']}>
                            {finding.report.facts.model}
                          </span>
                          <span className={styles['dot']} aria-hidden="true" />{' '}
                          <span>
                            {runDate(finding.report.facts.started_at)}
                          </span>
                        </span>
                      </span>{' '}
                      <StatusChip value={runStatus(finding.report)} />
                      <Icon name="arrow" className={styles['entryArrow']} />
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </div>
    </div>
  );
}

export default Home;
