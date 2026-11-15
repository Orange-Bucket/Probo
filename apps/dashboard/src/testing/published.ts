// SPDX-License-Identifier: Apache-2.0
/**
 * Readers for the text outputs of a published finding (`report.md`,
 * `judge-calibration.txt`), so tests take their expected strings from those files.
 */
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

/** The repository root. A string path: jsdom replaces the global URL in component tests. */
export const ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../../..',
);

export const FINDINGS_DIR = `${ROOT}/findings/`;

/** The text of `findings/<id>/<name>`, or null when the finding has no such file. */
export function publishedText(id: string, name: string): string | null {
  const file = `${FINDINGS_DIR}${id}/${name}`;
  return existsSync(file) ? readFileSync(file, 'utf8') : null;
}

/** A paragraph line or a table, as the report prints it. */
export type MarkdownBlock =
  | { kind: 'paragraph'; text: string }
  /** Rows of raw cells (Markdown escapes kept), header row first. */
  | { kind: 'table'; rows: string[][] };

export interface MarkdownSection {
  /** Heading level: 1 for the title, 2 and 3 for sections. */
  level: number;
  heading: string;
  /** The level-2 heading a level-3 section belongs to; null otherwise. */
  parent: string | null;
  /** The section's own paragraphs and tables, in order. */
  blocks: MarkdownBlock[];
}

/** The cells of a Markdown table row, split on pipes that are not escaped. */
function cells(line: string): string[] {
  return line
    .slice(2, -2)
    .split(/ (?<!\\)\| /)
    .map((cell) => cell.trim());
}

/** `report.md` split by heading, every paragraph line and table kept in order. */
export function markdownSections(markdown: string): MarkdownSection[] {
  const sections: MarkdownSection[] = [];
  let parent: string | null = null;
  let table: string[][] | null = null;
  for (const line of markdown.split('\n')) {
    const heading = /^(#{1,6}) (.*)$/.exec(line);
    if (heading) {
      const level = heading[1].length;
      if (level === 2) parent = heading[2];
      sections.push({
        level,
        heading: heading[2],
        parent: level === 3 ? parent : null,
        blocks: [],
      });
      table = null;
      continue;
    }
    const section = sections[sections.length - 1];
    if (line.startsWith('|')) {
      if (/^\|(?:---\|)+$/.test(line)) continue;
      if (table === null) {
        table = [];
        section.blocks.push({ kind: 'table', rows: table });
      }
      table.push(cells(line));
    } else {
      table = null;
      if (line.trim() !== '')
        section.blocks.push({ kind: 'paragraph', text: line });
    }
  }
  return sections;
}

/** Every table cell of the sections. */
export function tableCells(sections: MarkdownSection[]): string[] {
  return sections.flatMap((section) =>
    section.blocks.flatMap((block) =>
      block.kind === 'table' ? block.rows.flat() : [],
    ),
  );
}

/** A printed rate or proportion, or the text of an absent one. */
export const RATE_TEXT =
  /^(?:.+ \(n=\d+(?:, per-(?:attempt|trial))?, [0-9.]+% Wilson\)|absent \(denominator is 0\))$/;

/** What `probo.report.markdown._cell` makes of a text: one-spaced, pipes escaped, ASCII. */
export function markdownCell(text: string): string {
  const spaced = text
    .split(/\s+/)
    .filter(Boolean)
    .join(' ')
    .replace(/\|/g, '\\|');
  return Array.from(spaced)
    .map((char) => {
      const code = char.codePointAt(0) ?? 0;
      if (code < 0x80) return char;
      if (code < 0x100) return `\\x${code.toString(16).padStart(2, '0')}`;
      if (code < 0x10000) return `\\u${code.toString(16).padStart(4, '0')}`;
      return `\\U${code.toString(16).padStart(8, '0')}`;
    })
    .join('');
}
