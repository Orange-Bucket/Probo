// SPDX-License-Identifier: Apache-2.0
import { useId, type ReactNode } from 'react';
import { SECTIONS, type SectionKey } from '../../sections';
import styles from './section-card.module.css';

export interface SectionCardProps {
  /** Which fixed section this is: it gives the id, heading and caption. */
  section: SectionKey;
  children: ReactNode;
}

/**
 * A top-level section of a finding as a card: a region named by its heading, with a
 * one-line caption, and an id the navigation links to. The caption is not a paragraph, so
 * the section's paragraphs stay exactly those of the report.
 */
export function SectionCard({ section, children }: SectionCardProps) {
  const { id, title, caption } = SECTIONS[section];
  const captionId = useId();
  return (
    <section
      id={id}
      aria-label={title}
      aria-describedby={captionId}
      className={styles['card']}
    >
      <h4 className={styles['title']} tabIndex={-1}>
        {title}
      </h4>
      <div id={captionId} className={styles['caption']}>
        {caption}
      </div>
      <div className={styles['body']}>{children}</div>
    </section>
  );
}

export default SectionCard;
