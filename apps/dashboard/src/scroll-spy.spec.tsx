// SPDX-License-Identifier: Apache-2.0
import { act, render, renderHook } from '@testing-library/react';
import { useActiveSection } from './scroll-spy';

type Callback = (entries: Partial<IntersectionObserverEntry>[]) => void;

let observed: Element[] = [];
let callback: Callback = () => undefined;

class FakeObserver {
  constructor(cb: Callback) {
    callback = cb;
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
});

describe('useActiveSection', () => {
  it('starts at the first section without IntersectionObserver', () => {
    const { result } = renderHook(() => useActiveSection(['a', 'b']));
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
      ({ ids }) => useActiveSection(ids),
      { initialProps: { ids: ['a', 'b', 'c'] } },
    );
    expect(observed.map((e) => e.id)).toEqual(['a', 'b', 'c']);
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
    // Another finding's sections start at its first.
    rerender({ ids: ['c', 'a'] });
    expect(result.current[0]).toBe('c');
  });
});
