// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from 'react';
import Icon from '../icon/icon';
import styles from './notice.module.css';

export interface NoticeProps {
  /** `info` for a calm, always visible note; `warning` for an alert read out at once. */
  tone: 'info' | 'warning';
  children: ReactNode;
}

/** A note block with an icon; a warning is an ARIA alert. */
export function Notice({ tone, children }: NoticeProps) {
  return (
    <div
      className={`${styles['notice']} ${styles[tone]}`}
      role={tone === 'warning' ? 'alert' : undefined}
    >
      <Icon
        name={tone === 'warning' ? 'alert' : 'info'}
        className={styles['icon']}
      />
      <div className={styles['body']}>{children}</div>
    </div>
  );
}

export default Notice;
