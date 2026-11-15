// SPDX-License-Identifier: Apache-2.0
import type { Ref } from 'react';
import type { Finding } from '../../findings';
import { orNotRecorded, runIncomplete } from '../../report-text';
import Icon from '../icon/icon';
import StatusChip from '../status-chip/status-chip';
import ThemeToggle from '../theme-toggle/theme-toggle';
import styles from './top-bar.module.css';

/** The page title when no finding is shown. */
export const EMPTY_TITLE = 'Probo findings';

const DATE = /^\d{4}-\d{2}-\d{2}/;

/** The run's start date as recorded (`YYYY-MM-DD`), or `not recorded`. */
export function runDate(startedAt: string | null): string {
  const match = startedAt === null ? null : DATE.exec(startedAt);
  return match === null ? orNotRecorded(startedAt) : match[0];
}

export interface TopBarProps {
  /** The finding shown, if any. */
  finding: Finding | undefined;
  /** The id of the navigation the menu button opens. */
  menuId: string;
  menuOpen: boolean;
  onMenuToggle: () => void;
  menuButtonRef?: Ref<HTMLButtonElement>;
  /** The header element, so the shell can measure the bar's height. */
  barRef?: Ref<HTMLElement>;
}

/** The slim bar above the content: menu button, the page's h1, run status and theme. */
export function TopBar({
  finding,
  menuId,
  menuOpen,
  onMenuToggle,
  menuButtonRef,
  barRef,
}: TopBarProps) {
  return (
    <header ref={barRef} className={styles['bar']}>
      <button
        ref={menuButtonRef}
        type="button"
        className={styles['menu']}
        aria-expanded={menuOpen}
        aria-controls={menuId}
        aria-label="Navigation"
        onClick={onMenuToggle}
      >
        <Icon name={menuOpen ? 'close' : 'menu'} />
      </button>
      <div className={styles['heading']}>
        <div className={styles['titleRow']}>
          <h1 className={styles['title']} tabIndex={-1}>
            {finding === undefined ? EMPTY_TITLE : finding.id}
          </h1>
          {finding !== undefined && (
            <StatusChip
              value={runIncomplete(finding.report) ? 'incomplete' : 'complete'}
            />
          )}
        </div>
        {finding !== undefined && (
          <div className={styles['meta']}>
            <span className={styles['model']}>
              {finding.report.facts.model}
            </span>
            <span className={styles['dot']} aria-hidden="true" />
            <span>{runDate(finding.report.facts.started_at)}</span>
          </div>
        )}
      </div>
      <div className={styles['actions']}>
        <ThemeToggle />
      </div>
    </header>
  );
}

export default TopBar;
