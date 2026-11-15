// SPDX-License-Identifier: Apache-2.0
/**
 * The fixed sections of a finding's page: their element ids, titles, one-line captions and
 * the groups the page and the navigation put them in. Nothing here comes from a finding; a
 * finding only decides which of the optional sections are shown.
 */
import { manifestRows, type Finding } from './findings';

export type SectionKey =
  | 'overview'
  | 'run'
  | 'trials'
  | 'published'
  | 'attack-success'
  | 'attempt-completion'
  | 'utility'
  | 'control-base-rates'
  | 'delivery'
  | 'items'
  | 'limits'
  | 'excluded-trials'
  | 'judge-calibration'
  | 'disagreements';

export interface SectionInfo {
  /** The section element's id, the target of its navigation link. */
  id: string;
  /** The section heading, and the section's accessible name. */
  title: string;
  /** A short description shown under the heading. */
  caption: string;
  /** A shorter name for the navigation, where the title is long. */
  navTitle?: string;
}

export const SECTIONS: Readonly<Record<SectionKey, SectionInfo>> = {
  overview: {
    id: 'section-overview',
    title: 'Overview',
    caption:
      'Headline rates of this finding, as its report and judge calibration print them.',
  },
  run: {
    id: 'section-run',
    title: 'Run',
    caption: 'The log, model and corpus this finding was produced from.',
  },
  trials: {
    id: 'section-trials',
    title: 'Trials',
    caption: 'Trials in the log, and the terms the rates use.',
  },
  published: {
    id: 'section-published',
    title: 'Published finding',
    caption: 'Facts recorded when the finding was published.',
  },
  'attack-success': {
    id: 'section-attack-success',
    title: 'Attack success',
    caption:
      'How often the injected instruction succeeded, per attempt and per trial.',
  },
  'attempt-completion': {
    id: 'section-attempt-completion',
    title: 'Attempted and completed',
    caption:
      'Whether the target tried to send the record, and whether it leaked.',
  },
  utility: {
    id: 'section-utility',
    title: 'Utility',
    caption: 'How often the target completed the benign user task.',
  },
  'control-base-rates': {
    id: 'section-control-base-rates',
    title: 'Control base rates',
    caption: 'Trials without an injection: leaks and sends that happen anyway.',
  },
  delivery: {
    id: 'section-delivery',
    title: 'Delivery',
    caption: 'How often the injected note reached the target.',
  },
  items: {
    id: 'section-items',
    title: 'Items (user task x template, over epochs)',
    navTitle: 'Items',
    caption: 'Attack successes of each user task and template.',
  },
  limits: {
    id: 'section-limits',
    title: 'Limits',
    caption: 'Trials that hit a limit, by kind and outcome.',
  },
  'excluded-trials': {
    id: 'section-excluded-trials',
    title: 'Excluded trials',
    caption:
      'Template trials outside the per-attempt denominator, and control trials with an error label.',
  },
  'judge-calibration': {
    id: 'section-judge-calibration',
    title: 'Judge calibration',
    caption: 'The grader compared with the deterministic check.',
  },
  disagreements: {
    id: 'section-disagreements',
    title: 'Disagreements',
    caption: 'Trials where the grader and the check disagree.',
  },
};

export type GroupKey = 'setup' | 'results' | 'breakdown' | 'judge';

/** The sections that sit in a group: all but the overview, which is above the groups. */
export type GroupedSectionKey = Exclude<SectionKey, 'overview'>;

export interface SectionGroup {
  key: GroupKey;
  title: string;
  sections: GroupedSectionKey[];
}

/** The groups of a finding's page, in page order; every section keeps the report's order. */
export const GROUPS: readonly SectionGroup[] = [
  { key: 'setup', title: 'Setup', sections: ['run', 'trials', 'published'] },
  {
    key: 'results',
    title: 'Results',
    sections: [
      'attack-success',
      'attempt-completion',
      'utility',
      'control-base-rates',
      'delivery',
    ],
  },
  {
    key: 'breakdown',
    title: 'Breakdown',
    sections: ['items', 'limits', 'excluded-trials'],
  },
  {
    key: 'judge',
    title: 'Judge',
    sections: ['judge-calibration', 'disagreements'],
  },
];

/** Whether the page of `finding` shows the section: the optional ones depend on its files. */
export function hasSection(finding: Finding, section: SectionKey): boolean {
  if (section === 'published')
    return (
      finding.manifest !== null && manifestRows(finding.manifest).length > 0
    );
  if (section === 'disagreements') return finding.calibration !== null;
  return true;
}

/** The groups as the page of `finding` shows them, without the sections it leaves out. */
export function findingGroups(finding: Finding): SectionGroup[] {
  return GROUPS.map((group) => ({
    ...group,
    sections: group.sections.filter((section) => hasSection(finding, section)),
  })).filter((group) => group.sections.length > 0);
}

/** The element ids of the sections the page of `finding` shows, in page order. */
export function sectionIds(finding: Finding): string[] {
  return [
    SECTIONS.overview.id,
    ...findingGroups(finding).flatMap((group) =>
      group.sections.map((section) => SECTIONS[section].id),
    ),
  ];
}
