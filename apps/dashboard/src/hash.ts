// SPDX-License-Identifier: Apache-2.0
/**
 * The selected finding in the URL hash (`#<finding id>`). The hash is read defensively: it
 * selects a finding only when it decodes to one of the known ids, and is never used for
 * anything else.
 */

/** The longest hash looked at; finding ids are short directory names. */
const MAX_HASH = 512;

/** The known finding id the hash names, or null for anything else. */
export function findingFromHash(
  hash: string,
  ids: readonly string[],
): string | null {
  const raw = hash.startsWith('#') ? hash.slice(1) : hash;
  if (raw === '' || raw.length > MAX_HASH) return null;
  let decoded: string;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    return null;
  }
  return ids.includes(decoded) ? decoded : null;
}

/** The hash that selects the finding `id`. */
export function hashFor(id: string): string {
  return `#${encodeURIComponent(id)}`;
}

/** The current hash, or an empty string where there is no window. */
export function currentHash(): string {
  return typeof window === 'undefined' ? '' : window.location.hash;
}

/** Records the selected finding in the hash as a new history entry; never throws. */
export function pushHash(id: string): void {
  try {
    if (window.location.hash !== hashFor(id)) {
      window.history.pushState(null, '', hashFor(id));
    }
  } catch {
    // A sandboxed page may refuse history changes; the selection still works.
  }
}
