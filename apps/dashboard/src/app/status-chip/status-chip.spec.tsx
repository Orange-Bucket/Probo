// SPDX-License-Identifier: Apache-2.0
import { render } from '@testing-library/react';
import { OUTCOMES } from '../../report-text';
import StatusChip from './status-chip';

function chipOf(value: string): HTMLElement {
  const { container } = render(<StatusChip value={value} />);
  return container.firstElementChild as HTMLElement;
}

describe('StatusChip', () => {
  it.each(['attack_succeeded', 'incomplete'])(
    'gives %s the accent tone and a glyph',
    (value) => {
      const chip = chipOf(value);
      expect(chip.textContent).toBe(value);
      expect(chip.className).toMatch(/accent/);
      expect(chip.querySelector('svg')?.getAttribute('aria-hidden')).toBe(
        'true',
      );
    },
  );

  it('gives every outcome a known tone and a glyph, with its text unchanged', () => {
    for (const outcome of OUTCOMES) {
      const chip = chipOf(outcome);
      expect(chip.textContent).toBe(outcome);
      expect(chip.className).toMatch(/accent|neutral|quiet/);
      expect(chip.querySelector('svg')).not.toBeNull();
    }
  });

  it('marks success and failure by glyph shape, not by colour alone', () => {
    const succeeded = chipOf('attack_succeeded').querySelector('svg');
    const resisted = chipOf('attack_failed_target_resisted').querySelector(
      'svg',
    );
    expect(succeeded?.innerHTML).not.toBe(resisted?.innerHTML);
    expect(chipOf('complete').querySelector('svg')?.innerHTML).not.toBe(
      chipOf('incomplete').querySelector('svg')?.innerHTML,
    );
  });

  it.each(['something_new', 'constructor', '__proto__', 'toString'])(
    'gives the unknown value %s the neutral style and no glyph',
    (value) => {
      const chip = chipOf(value);
      expect(chip.textContent).toBe(value);
      expect(chip.className).toMatch(/neutral/);
      expect(chip.className).not.toMatch(/accent|quiet|undefined/);
      expect(chip.querySelector('svg')).toBeNull();
    },
  );

  it('keeps hostile strings as text', () => {
    const hostile = '<img src=x onerror="alert(1)"><script>alert(2)</script>';
    const chip = chipOf(hostile);
    expect(chip.textContent).toBe(hostile);
    expect(chip.querySelector('img, script')).toBeNull();
    expect(chip.className).toMatch(/neutral/);
    expect(chip.className).not.toContain('<');
  });
});
