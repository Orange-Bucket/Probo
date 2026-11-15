// SPDX-License-Identifier: Apache-2.0
import { findingFromHash, hashFor, pushHash } from './hash';

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

describe('pushHash', () => {
  afterEach(() => window.history.replaceState(null, '', '/'));

  it('records a finding as its hash, and Home as the URL without a hash', () => {
    window.history.replaceState(null, '', '/?x=1');
    const before = window.history.length;
    pushHash('a b');
    expect(window.location.hash).toBe('#a%20b');
    expect(window.history.length).toBe(before + 1);
    pushHash(null);
    expect(window.location.hash).toBe('');
    expect(window.location.href.endsWith('/?x=1')).toBe(true);
    expect(window.history.length).toBe(before + 2);
  });

  it('adds no history entry when the hash already says so', () => {
    const before = window.history.length;
    pushHash(null);
    expect(window.history.length).toBe(before);
    pushHash('2026-01-01-a');
    pushHash('2026-01-01-a');
    expect(window.history.length).toBe(before + 1);
  });

  it('clears an unknown hash when Home is chosen', () => {
    window.history.replaceState(null, '', '/#nothing-like-it');
    pushHash(null);
    expect(window.location.hash).toBe('');
  });

  it('replaces the entry instead of adding one when asked to', () => {
    window.history.replaceState(null, '', '/#nothing-like-it');
    const before = window.history.length;
    pushHash(null, true);
    expect(window.location.hash).toBe('');
    expect(window.history.length).toBe(before);
  });

  it('adds no entry when the hash names the finding in another encoding', () => {
    window.history.replaceState(null, '', '/#2026%2D01-01-a');
    const before = window.history.length;
    pushHash('2026-01-01-a');
    expect(window.history.length).toBe(before);
    expect(window.location.hash).toBe('#2026%2D01-01-a');
  });

  it('never throws when history refuses the change', () => {
    const push = vi
      .spyOn(window.history, 'pushState')
      .mockImplementation(() => {
        throw new DOMException('refused', 'SecurityError');
      });
    expect(() => pushHash('2026-01-01-a')).not.toThrow();
    expect(() => pushHash(null)).not.toThrow();
    push.mockRestore();
  });
});
