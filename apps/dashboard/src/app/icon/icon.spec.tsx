// SPDX-License-Identifier: Apache-2.0
import { render } from '@testing-library/react';
import Icon from './icon';

describe('Icon', () => {
  it('draws an inline SVG that assistive technology skips and that holds no text', () => {
    const { container } = render(<Icon name="info" />);
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
    expect(svg?.getAttribute('aria-hidden')).toBe('true');
    expect(svg?.getAttribute('focusable')).toBe('false');
    expect(container.textContent).toBe('');
    expect(container.querySelector('image, use, a')).toBeNull();
  });
});

describe('the home and arrow icons', () => {
  it.each(['home', 'arrow'] as const)(
    'draw %s as stroke paths only',
    (name) => {
      const { container } = render(<Icon name={name} />);
      const svg = container.querySelector('svg');
      expect(svg?.getAttribute('viewBox')).toBe('0 0 24 24');
      expect(svg?.querySelectorAll('path').length).toBeGreaterThan(0);
      expect(container.textContent).toBe('');
    },
  );
});
