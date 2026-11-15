// SPDX-License-Identifier: Apache-2.0
import { render, screen } from '@testing-library/react';
import { EVIDENCE_SENTENCE, INDEPENDENCE_SENTENCE } from '../../report-text';
import { GROUPS, SECTIONS } from '../../sections';
import { finding } from '../../testing/fixtures';
import FindingView from './finding-view';

describe('FindingView', () => {
  it('groups every section under the group headings, all in the document', () => {
    render(<FindingView finding={finding('2026-01-01-a')} />);
    expect(
      screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent),
    ).toEqual(['Overview', ...GROUPS.map((group) => group.title)]);
    for (const group of GROUPS) {
      for (const section of group.sections) {
        if (section === 'published') continue;
        const region = screen.getByRole('region', {
          name: SECTIONS[section].title,
        });
        expect(region.id).toBe(SECTIONS[section].id);
      }
    }
  });

  it('shows the two fixed sentences as a visible note, not an alert', () => {
    render(<FindingView finding={finding('2026-01-01-a')} />);
    expect(screen.getByText(EVIDENCE_SENTENCE)).toBeTruthy();
    expect(screen.getByText(INDEPENDENCE_SENTENCE)).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('shows the published finding section only with a manifest', () => {
    const { unmount } = render(
      <FindingView finding={finding('2026-01-01-a')} />,
    );
    expect(
      screen.queryByRole('region', { name: 'Published finding' }),
    ).toBeNull();
    unmount();
    render(
      <FindingView
        finding={finding('2026-01-01-a', { manifest: { finding: 'x' } })}
      />,
    );
    expect(screen.getByRole('region', { name: 'Published finding' }).id).toBe(
      SECTIONS.published.id,
    );
  });
});
