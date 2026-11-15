// SPDX-License-Identifier: Apache-2.0
import { render, screen } from '@testing-library/react';
import { SECTIONS } from '../../sections';
import SectionCard from './section-card';

describe('SectionCard', () => {
  it('is a region named by its heading, with the fixed id and caption', () => {
    render(
      <SectionCard section="utility">
        <p>Body.</p>
      </SectionCard>,
    );
    const region = screen.getByRole('region', { name: 'Utility' });
    expect(region.id).toBe(SECTIONS.utility.id);
    const heading = region.querySelector(':scope > h4');
    expect(heading?.textContent).toBe('Utility');
    expect(region.getAttribute('aria-describedby')).toBeTruthy();
    const caption = document.getElementById(
      region.getAttribute('aria-describedby') ?? '',
    );
    expect(caption?.textContent).toBe(SECTIONS.utility.caption);
    // The caption is not a paragraph: the section's paragraphs are the report's own.
    expect(
      Array.from(region.querySelectorAll('p')).map((p) => p.textContent),
    ).toEqual(['Body.']);
  });
});
