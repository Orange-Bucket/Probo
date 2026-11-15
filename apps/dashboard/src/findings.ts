// SPDX-License-Identifier: Apache-2.0
/**
 * The published findings, bundled at build time from `findings/<id>/` at the repository
 * root. Nothing is fetched at run time: Vite inlines the text of every matching JSON file.
 * A calibration or manifest without a report.json beside it is bundled too (a static glob
 * cannot depend on other files) but never shown.
 */
import type { JudgeCalibration } from './generated/calibration';
import type { RunSummary } from './generated/report';
import { parseJson } from './json';

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

/**
 * The parsed JSON files, by path. They are bundled as text and parsed with `parseJson`, so
 * that numbers written as floats (`1.0`) stay distinguishable from integers (`1`).
 */
function parsed<T>(files: Record<string, string>): Record<string, T> {
  return Object.fromEntries(
    Object.entries(files).map(([path, text]) => [path, parseJson(text) as T]),
  );
}

export const FINDINGS: Finding[] = groupFindings(
  parsed<RunSummary>(
    import.meta.glob<string>('../../../findings/*/report.json', {
      query: '?raw',
      import: 'default',
      eager: true,
    }),
  ),
  parsed<JudgeCalibration>(
    import.meta.glob<string>('../../../findings/*/judge-calibration.json', {
      query: '?raw',
      import: 'default',
      eager: true,
    }),
  ),
  parsed<Manifest>(
    import.meta.glob<string>('../../../findings/*/manifest.json', {
      query: '?raw',
      import: 'default',
      eager: true,
    }),
  ),
);
