// SPDX-License-Identifier: Apache-2.0
import { findingFromHash, hashFor } from './hash';

const IDS = ['2026-11-14-qwen2.5-7b-plain-request', 'a b', '2026-01-01-a'];

describe('findingFromHash', () => {
  it('finds a known id, with or without the leading #', () => {
    expect(findingFromHash('#2026-01-01-a', IDS)).toBe('2026-01-01-a');
    expect(findingFromHash('2026-01-01-a', IDS)).toBe('2026-01-01-a');
    expect(findingFromHash('#2026-11-14-qwen2.5-7b-plain-request', IDS)).toBe(
      '2026-11-14-qwen2.5-7b-plain-request',
    );
  });

  it('decodes an escaped id and round-trips hashFor', () => {
    expect(findingFromHash('#a%20b', IDS)).toBe('a b');
    for (const id of IDS) expect(findingFromHash(hashFor(id), IDS)).toBe(id);
  });

  it.each([
    ['empty', ''],
    ['only #', '#'],
    ['unknown', '#2099-01-01-x'],
    ['a prefix of an id', '#2026-01-01'],
    ['a malformed escape', '#%E0%A4%A'],
    ['a lone percent', '#%'],
    ['markup', '#<script>alert(1)</script>'],
    ['prototype keys', '#__proto__'],
    ['too long', `#${'a'.repeat(600)}`],
  ])('returns null for %s', (_, hash) => {
    expect(findingFromHash(hash, IDS)).toBeNull();
  });
});
