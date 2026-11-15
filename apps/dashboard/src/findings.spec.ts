// SPDX-License-Identifier: Apache-2.0
import { existsSync, readdirSync } from 'node:fs';
import { FINDINGS, groupFindings } from './findings';
import { calibration, report } from './testing/fixtures';
import { FINDINGS_DIR } from './testing/published';

describe('groupFindings', () => {
  it('groups the files of each finding directory, newest first', () => {
    const old = report();
    const recent = report();
    const judged = calibration();
    const found = groupFindings(
      {
        '../../../findings/2026-01-01-a/report.json': old,
        '../../../findings/2026-03-01-b/report.json': recent,
      },
      { '../../../findings/2026-01-01-a/judge-calibration.json': judged },
      {
        '../../../findings/2026-03-01-b/manifest.json': {
          finding: '2026-03-01-b',
        },
      },
    );
    expect(found).toEqual([
      {
        id: '2026-03-01-b',
        report: recent,
        calibration: null,
        manifest: { finding: '2026-03-01-b' },
      },
      { id: '2026-01-01-a', report: old, calibration: judged, manifest: null },
    ]);
  });

  it('leaves out a directory without report.json', () => {
    const found = groupFindings(
      {},
      { '../../../findings/x/judge-calibration.json': calibration() },
      { '../../../findings/x/manifest.json': {} },
    );
    expect(found).toEqual([]);
  });
});

describe('FINDINGS', () => {
  it('bundles every finding directory that has a report.json', () => {
    const published = readdirSync(FINDINGS_DIR)
      .filter((name) => existsSync(`${FINDINGS_DIR}${name}/report.json`))
      .sort()
      .reverse();
    expect(published.length).toBeGreaterThan(0);
    expect(FINDINGS.map((finding) => finding.id)).toEqual(published);
  });

  it('attaches the calibration and manifest that exist on disk', () => {
    for (const finding of FINDINGS) {
      const dir = `${FINDINGS_DIR}${finding.id}/`;
      expect(finding.calibration !== null).toBe(
        existsSync(`${dir}judge-calibration.json`),
      );
      expect(finding.manifest !== null).toBe(existsSync(`${dir}manifest.json`));
    }
  });
});
