// SPDX-License-Identifier: Apache-2.0
import { GROUPS, SECTIONS, findingGroups, sectionIds } from './sections';
import { finding } from './testing/fixtures';

describe('sections', () => {
  it('have unique ids and titles, and every section is in exactly one place', () => {
    const infos = Object.values(SECTIONS);
    expect(new Set(infos.map((i) => i.id)).size).toBe(infos.length);
    expect(new Set(infos.map((i) => i.title)).size).toBe(infos.length);
    const grouped = GROUPS.flatMap((group) => group.sections);
    expect(new Set(grouped).size).toBe(grouped.length);
    expect([...grouped, 'overview'].sort()).toEqual(
      Object.keys(SECTIONS).sort(),
    );
  });

  it('leave out the published finding without a manifest and the disagreements without a calibration', () => {
    const bare = finding('2026-01-01-a', { calibration: null });
    const keys = findingGroups(bare).flatMap((group) => group.sections);
    expect(keys).not.toContain('published');
    expect(keys).not.toContain('disagreements');
    expect(keys).toContain('judge-calibration');
    const full = finding('2026-01-01-a', { manifest: { finding: 'x' } });
    expect(sectionIds(full)).toEqual([
      SECTIONS.overview.id,
      ...GROUPS.flatMap((group) => group.sections).map((s) => SECTIONS[s].id),
    ]);
  });

  it('leave out the published finding when the manifest has no scalar entries', () => {
    const nested = finding('2026-01-01-a', { manifest: { files: { a: 'b' } } });
    expect(
      findingGroups(nested).flatMap((group) => group.sections),
    ).not.toContain('published');
  });
});
