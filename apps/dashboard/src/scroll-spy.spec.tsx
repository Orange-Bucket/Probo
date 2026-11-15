// SPDX-License-Identifier: Apache-2.0
import { act, render, renderHook } from '@testing-library/react';
import { useRef } from 'react';
import {
  DEFAULT_OFFSET,
  SCROLL_GAP,
  useActiveSection,
  useScrollOffset,
} from './scroll-spy';

type Callback = (entries: Partial<IntersectionObserverEntry>[]) => void;

let observed: Element[] = [];
let callback: Callback = () => undefined;
let margins: string[] = [];

class FakeObserver {
  constructor(cb: Callback, options?: IntersectionObserverInit) {
    callback = cb;
    margins.push(options?.rootMargin ?? '');
  }
  observe(element: Element) {
    observed.push(element);
  }
  disconnect() {
    observed = [];
  }
}

function entry(id: string, isIntersecting: boolean) {
  return { target: document.getElementById(id) as Element, isIntersecting };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  observed = [];
  margins = [];
});

describe('useActiveSection', () => {
  it('starts at the first section without IntersectionObserver', () => {
    const { result } = renderHook(() => useActiveSection(['a', 'b'], 'x'));
    expect(result.current[0]).toBe('a');
  });

  it('follows the first section in view, and a click for a moment', () => {
    vi.stubGlobal('IntersectionObserver', FakeObserver);
    render(
      <>
        <section id="a" />
        <section id="b" />
        <section id="c" />
      </>,
    );
    const { result, rerender } = renderHook(
      ({ ids, scope }) => useActiveSection(ids, scope),
      { initialProps: { ids: ['a', 'b', 'c'], scope: 'one' } },
    );
    expect(observed.map((e) => e.id)).toEqual(['a', 'b', 'c']);
    expect(margins).toEqual([`-${DEFAULT_OFFSET}px 0px -50% 0px`]);
    act(() =>
      callback([entry('a', false), entry('b', true), entry('c', true)]),
    );
    expect(result.current[0]).toBe('b');
    vi.useFakeTimers();
    act(() => result.current[1]('c'));
    expect(result.current[0]).toBe('c');
    act(() => callback([entry('b', true)]));
    expect(result.current[0]).toBe('c');
    vi.advanceTimersByTime(2000);
    act(() => callback([entry('b', true)]));
    expect(result.current[0]).toBe('b');
    // Another scope with the same ids observes again and starts at its first section.
    rerender({ ids: ['a', 'b', 'c'], scope: 'two' });
    expect(result.current[0]).toBe('a');
    expect(margins).toHaveLength(2);
    expect(observed.map((e) => e.id)).toEqual(['a', 'b', 'c']);
  });

  it('uses the offset as the top of the band', () => {
    vi.stubGlobal('IntersectionObserver', FakeObserver);
    renderHook(() => useActiveSection(['a'], 'x', 136.4));
    expect(margins).toEqual(['-136px 0px -50% 0px']);
  });
});

describe('useScrollOffset', () => {
  afterEach(() =>
    document.documentElement.style.removeProperty('--scroll-offset'),
  );

  it('is the default without ResizeObserver, and leaves the CSS default alone', () => {
    const { result } = renderHook(() => {
      const bar = useRef<HTMLElement>(document.createElement('header'));
      return useScrollOffset(bar);
    });
    expect(result.current).toBe(DEFAULT_OFFSET);
    expect(
      document.documentElement.style.getPropertyValue('--scroll-offset'),
    ).toBe('');
  });

  it('is the bar height plus the gap, also as --scroll-offset, and follows resizes', () => {
    let resized: () => void = () => undefined;
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(cb: () => void) {
          resized = cb;
        }
        observe() {
          return undefined;
        }
        disconnect() {
          return undefined;
        }
      },
    );
    const header = document.createElement('header');
    let height = 112.2;
    header.getBoundingClientRect = () => ({ height }) as DOMRect;
    const { result, unmount } = renderHook(() => {
      const bar = useRef<HTMLElement>(header);
      return useScrollOffset(bar);
    });
    expect(result.current).toBe(113 + SCROLL_GAP);
    const root = document.documentElement.style;
    expect(root.getPropertyValue('--scroll-offset')).toBe(
      `${113 + SCROLL_GAP}px`,
    );
    height = 64;
    act(() => resized());
    expect(result.current).toBe(64 + SCROLL_GAP);
    unmount();
    expect(root.getPropertyValue('--scroll-offset')).toBe('');
  });
});
