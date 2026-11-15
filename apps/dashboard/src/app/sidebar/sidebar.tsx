// SPDX-License-Identifier: Apache-2.0
import type { KeyboardEvent, MouseEvent } from 'react';
import type { Finding } from '../../findings';
import { SECTIONS, type SectionGroup, type SectionKey } from '../../sections';
import Icon from '../icon/icon';
import styles from './sidebar.module.css';

export interface SidebarProps {
  /** The element id, for the menu button's aria-controls. */
  id: string;
  /** Open as a drawer (narrow screens only; wide screens always show the sidebar). */
  open: boolean;
  /**
   * Shown as a drawer over the page: then it is a labelled modal dialog. Wide screens show
   * it as ordinary navigation beside the content, with no dialog role.
   */
  modal: boolean;
  /** Every finding, newest first. */
  findings: Finding[];
  selectedId: string | undefined;
  onSelect: (id: string) => void;
  /** The selected finding's section groups. */
  groups: SectionGroup[];
  /** The id of the section in view. */
  activeSection: string | null;
  /** Called with a section's element id when its link is followed. */
  onNavigate: (id: string) => void;
  /** Closes the drawer; its button shows on narrow screens only. */
  onClose: () => void;
  onKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
}

/** The brand mark: an orange tile with a P, drawn here. */
function brandMark() {
  return (
    <svg
      className={styles['mark']}
      viewBox="0 0 32 32"
      aria-hidden="true"
      focusable="false"
    >
      <rect width="32" height="32" rx="9" className={styles['markTile']} />
      <path
        d="M12 23V9h5.5a4.5 4.5 0 0 1 0 9H12"
        fill="none"
        stroke="#ffffff"
        strokeWidth={2.75}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="21.5" cy="22.5" r="1.75" fill="#ffffff" />
    </svg>
  );
}

/**
 * The left sidebar: brand, the findings (the selected one marked current), links to the
 * selected finding's sections (the one in view marked), and the footer line. Links point
 * only at the fixed section ids.
 */
export function Sidebar({
  id,
  open,
  modal,
  findings,
  selectedId,
  onSelect,
  groups,
  activeSection,
  onNavigate,
  onClose,
  onKeyDown,
}: SidebarProps) {
  const link = (section: SectionKey, icon?: 'grid') => {
    const info = SECTIONS[section];
    const current = activeSection === info.id;
    const follow = (event: MouseEvent<HTMLAnchorElement>) => {
      // Leave modified clicks (new tab, new window) to the browser.
      if (
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey
      )
        return;
      event.preventDefault();
      onNavigate(info.id);
    };
    return (
      <li key={section}>
        <a
          href={`#${info.id}`}
          className={styles['link']}
          aria-current={current ? 'location' : undefined}
          onClick={follow}
        >
          {icon !== undefined && <Icon name={icon} />}
          <span>{info.navTitle ?? info.title}</span>
        </a>
      </li>
    );
  };
  return (
    <div
      id={id}
      className={
        open ? `${styles['sidebar']} ${styles['open']}` : styles['sidebar']
      }
      data-open={open}
      role={modal ? 'dialog' : undefined}
      aria-modal={modal ? true : undefined}
      aria-label={modal ? 'Navigation' : undefined}
      onKeyDown={onKeyDown}
    >
      <div className={styles['brand']}>
        {brandMark()}
        <span className={styles['name']}>Probo</span>
        <button
          type="button"
          className={styles['close']}
          aria-label="Close navigation"
          onClick={onClose}
        >
          <Icon name="close" />
        </button>
      </div>
      <div className={styles['scroll']}>
        <nav aria-label="Findings" className={styles['nav']}>
          <div className={styles['label']} aria-hidden="true">
            Findings
          </div>
          {findings.length === 0 ? (
            <p className={styles['none']}>None published.</p>
          ) : (
            <ul className={styles['list']}>
              {findings.map((finding) => (
                <li key={finding.id}>
                  <button
                    type="button"
                    className={styles['finding']}
                    aria-current={
                      finding.id === selectedId ? 'true' : undefined
                    }
                    onClick={() => onSelect(finding.id)}
                  >
                    <Icon name="file" />
                    <span className={styles['findingText']}>
                      <span className={styles['findingId']}>{finding.id}</span>{' '}
                      <span className={styles['findingMeta']}>
                        {finding.report.facts.model}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </nav>
        {groups.length > 0 && (
          <nav aria-label="Sections" className={styles['nav']}>
            <div className={styles['label']} aria-hidden="true">
              On this page
            </div>
            <ul className={styles['list']}>{link('overview', 'grid')}</ul>
            {groups.map((group) => (
              <div key={group.key} className={styles['group']}>
                <div className={styles['groupLabel']}>
                  <Icon name={group.key} />
                  <span>{group.title}</span>
                </div>
                <ul className={`${styles['list']} ${styles['indented']}`}>
                  {group.sections.map((section) => link(section))}
                </ul>
              </div>
            ))}
          </nav>
        )}
      </div>
      <p className={styles['footer']}>
        <Icon name="lock" />
        <span>Static build. Read only.</span>
      </p>
    </div>
  );
}

export default Sidebar;
