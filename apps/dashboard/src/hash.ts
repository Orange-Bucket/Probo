// SPDX-License-Identifier: Apache-2.0
/**
 * The page in the URL hash: `#<finding id>` shows that finding, and no hash shows Home. The
 * hash is read defensively: it selects a finding only when it decodes to one of the known
 * ids, and is never used for anything else; any other hash shows Home.
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

/**
 * Records the page shown in the URL: the finding `id` as its hash, or Home (`null`) as the
 * same URL without a hash. It is a new history entry unless `replace` is set, and nothing
 * is recorded when the URL already says so; never throws.
 */
export function pushHash(id: string | null, replace = false): void {
  try {
    const { hash, pathname, search } = window.location;
    const already =
      id === null ? hash === '' : findingFromHash(hash, [id]) === id;
    if (already) return;
    const url = id === null ? pathname + search : hashFor(id);
    if (replace) window.history.replaceState(null, '', url);
    else window.history.pushState(null, '', url);
  } catch {
    // A sandboxed page may refuse history changes; the selection still works.
  }
}
