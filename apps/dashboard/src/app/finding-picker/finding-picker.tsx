// SPDX-License-Identifier: Apache-2.0
import { useId } from 'react';
import styles from './finding-picker.module.css';

export interface FindingPickerProps {
  /** Finding ids, newest first. */
  ids: string[];
  selected: string;
  onSelect: (id: string) => void;
}

/** Chooses the finding to show; with a single finding it only names it. */
export function FindingPicker({ ids, selected, onSelect }: FindingPickerProps) {
  const id = useId();
  if (ids.length <= 1) {
    return (
      <p className={styles['picker']}>
        Finding: <span className="code">{selected}</span>
      </p>
    );
  }
  return (
    <p className={styles['picker']}>
      <label htmlFor={id}>Finding</label>{' '}
      <select
        id={id}
        value={selected}
        onChange={(event) => onSelect(event.target.value)}
      >
        {ids.map((findingId) => (
          <option key={findingId} value={findingId}>
            {findingId}
          </option>
        ))}
      </select>
    </p>
  );
}

export default FindingPicker;
