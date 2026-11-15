// SPDX-License-Identifier: Apache-2.0
/**
 * The published findings, bundled at build time from `findings/<id>/` at the repository
 * root. Nothing is fetched at run time: Vite inlines every matching JSON file.
 */
import type { JudgeCalibration } from './generated/calibration';
import type { RunSummary } from './generated/report';

/** `manifest.json` has no committed schema; its values are shown only as text. */
export type Manifest = Record<string, unknown>;

export interface Finding {
  /** The directory name under `findings/`. */
  id: string;
  report: RunSummary;
  /** `judge-calibration.json`, when the finding has one. */
  calibration: JudgeCalibration | null;
  manifest: Manifest | null;
}

const FINDING_FILE = /(?:^|\/)findings\/([^/]+)\/[^/]+\.json$/;

function byId<T>(files: Record<string, T>): Map<string, T> {
  const found = new Map<string, T>();
  for (const [path, value] of Object.entries(files)) {
    const match = FINDING_FILE.exec(path);
    if (match !== null) found.set(match[1], value);
  }
  return found;
}

/**
 * The findings that have a `report.json`, newest first: ids start with the run date, so
 * they sort by id in descending order. Inputs are maps from file path to parsed JSON.
 */
export function groupFindings(
  reports: Record<string, RunSummary>,
  calibrations: Record<string, JudgeCalibration>,
  manifests: Record<string, Manifest>,
): Finding[] {
  const calibrationById = byId(calibrations);
  const manifestById = byId(manifests);
  return [...byId(reports)]
    .map(([id, report]) => ({
      id,
      report,
      calibration: calibrationById.get(id) ?? null,
      manifest: manifestById.get(id) ?? null,
    }))
    .sort((a, b) => (a.id < b.id ? 1 : a.id > b.id ? -1 : 0));
}

export const FINDINGS: Finding[] = groupFindings(
  import.meta.glob<RunSummary>('../../../findings/*/report.json', {
    eager: true,
    import: 'default',
  }),
  import.meta.glob<JudgeCalibration>(
    '../../../findings/*/judge-calibration.json',
    {
      eager: true,
      import: 'default',
    },
  ),
  import.meta.glob<Manifest>('../../../findings/*/manifest.json', {
    eager: true,
    import: 'default',
  }),
);
