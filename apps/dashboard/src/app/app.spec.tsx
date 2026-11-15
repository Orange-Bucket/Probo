// SPDX-License-Identifier: Apache-2.0
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import {
  CORPUS_WARNING,
  EVIDENCE_SENTENCE,
  INCOMPLETE_WARNING,
  INDEPENDENCE_SENTENCE,
  TERMS,
} from '../report-text';
import { SECTIONS, sectionIds } from '../sections';
import { finding, report } from '../testing/fixtures';
import App from './app';

const NEWER = '2026-03-01-b';
const OLDER = '2026-01-01-a';

function twoFindings() {
  return [
    finding(NEWER),
    finding(OLDER, {
      report: report({ facts: { ...report().facts, task: 'probo/older' } }),
      calibration: null,
    }),
  ];
}

function findingButton(id: string): HTMLElement {
  const nav = screen.getByRole('navigation', { name: 'Findings' });
  return within(nav).getByRole('button', { name: new RegExp(`^${id}`) });
}

function setHash(hash: string) {
  window.history.replaceState(null, '', `/${hash}`);
}

afterEach(() => setHash(''));

describe('App', () => {
  it('always shows the two fixed sentences and the terms at the top of a finding', () => {
    render(<App findings={[finding(OLDER, { calibration: null })]} />);
    const article = screen.getByRole('article');
    const evidence = screen.getByText(EVIDENCE_SENTENCE);
    const independence = screen.getByText(INDEPENDENCE_SENTENCE);
    const firstSection = article.querySelector('section');
    for (const sentence of [evidence, independence]) {
      expect(article.contains(sentence)).toBe(true);
      expect(
        firstSection !== null &&
          sentence.compareDocumentPosition(firstSection) &
            Node.DOCUMENT_POSITION_FOLLOWING,
      ).toBeTruthy();
    }
    expect(screen.getByText(TERMS)).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('shows an incomplete run warning prominently, and an incomplete chip', () => {
    const incomplete = report({
      incomplete: true,
      not_run: 2,
      warnings: [INCOMPLETE_WARNING],
    });
    render(<App findings={[finding(OLDER, { report: incomplete })]} />);
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toBe(INCOMPLETE_WARNING);
    expect(alert.querySelector('strong')?.textContent).toBe(INCOMPLETE_WARNING);
    expect(
      within(screen.getByRole('banner')).getByText('incomplete'),
    ).toBeTruthy();
  });

  it('shows a corpus mismatch warning even when the report lists none', () => {
    const base = report();
    const mixed = report({ facts: { ...base.facts, corpus_mismatch: true } });
    render(<App findings={[finding(OLDER, { report: mixed })]} />);
    expect(screen.getByRole('alert').textContent).toBe(CORPUS_WARNING);
  });

  it('shows the newest finding first and switches on choice', () => {
    render(<App findings={twoFindings()} />);
    expect(
      screen.getByRole('heading', { name: 'Probo run report: probo/example' }),
    ).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Disagreements' })).toBeTruthy();
    fireEvent.click(findingButton(OLDER));
    expect(
      screen.getByRole('heading', { name: 'Probo run report: probo/older' }),
    ).toBeTruthy();
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(OLDER);
    expect(
      screen.getByText('This finding has no judge calibration.'),
    ).toBeTruthy();
    expect(screen.queryByRole('region', { name: 'Disagreements' })).toBeNull();
  });

  it('says so when no finding is published, inside the same shell', () => {
    render(<App findings={[]} />);
    expect(screen.getByText('No findings are published.')).toBeTruthy();
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(
      'Probo findings',
    );
    expect(screen.getByRole('main')).toBeTruthy();
    expect(screen.getByRole('banner')).toBeTruthy();
    expect(screen.queryByRole('navigation', { name: 'Sections' })).toBeNull();
    expect(screen.queryByRole('article')).toBeNull();
  });
});

describe('the application shell', () => {
  it('has the landmarks, one h1, and headings that never skip a level', () => {
    render(<App findings={twoFindings()} />);
    const banner = screen.getByRole('banner');
    const main = screen.getByRole('main');
    expect(within(banner).getByRole('heading', { level: 1 }).textContent).toBe(
      NEWER,
    );
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(main.contains(screen.getByRole('article'))).toBe(true);
    expect(main.contains(banner)).toBe(false);
    expect(
      screen
        .getAllByRole('navigation')
        .map((nav) => nav.getAttribute('aria-label')),
    ).toEqual(['Findings', 'Sections']);
    let previous = 0;
    for (const heading of Array.from(
      document.querySelectorAll('h1, h2, h3, h4, h5, h6'),
    )) {
      const level = Number(heading.tagName.slice(1));
      expect(level, heading.textContent ?? '').toBeLessThanOrEqual(
        previous + 1,
      );
      previous = level;
    }
  });

  it('lists every finding, newest first, and marks the selected one', () => {
    render(<App findings={twoFindings()} />);
    const nav = screen.getByRole('navigation', { name: 'Findings' });
    const buttons = within(nav).getAllByRole('button');
    expect(buttons.map((b) => b.textContent)).toEqual([
      `${NEWER} mockllm/model`,
      `${OLDER} mockllm/model`,
    ]);
    expect(findingButton(NEWER).getAttribute('aria-current')).toBe('true');
    expect(findingButton(OLDER).getAttribute('aria-current')).toBeNull();
    fireEvent.click(findingButton(OLDER));
    expect(findingButton(OLDER).getAttribute('aria-current')).toBe('true');
    expect(findingButton(NEWER).getAttribute('aria-current')).toBeNull();
  });

  it('links every section of the shown finding, and nothing else', () => {
    render(<App findings={twoFindings()} />);
    const article = screen.getByRole('article');
    const topLevel = [
      screen.getByRole('region', { name: 'Overview' }),
      ...Array.from(article.querySelectorAll('section')).filter(
        (section) => section.querySelector(':scope > h4') !== null,
      ),
    ];
    const nav = screen.getByRole('navigation', { name: 'Sections' });
    const links = within(nav).getAllByRole('link');
    expect(links.map((link) => link.getAttribute('href'))).toEqual(
      topLevel.map((section) => `#${section.id}`),
    );
    expect(links.map((link) => link.textContent)).toEqual(
      Object.values(SECTIONS)
        .filter((info) => topLevel.some((section) => section.id === info.id))
        .map((info) => info.navTitle ?? info.title),
    );
    // The older finding has no calibration: no Disagreements link.
    fireEvent.click(findingButton(OLDER));
    expect(
      within(nav).queryByRole('link', { name: 'Disagreements' }),
    ).toBeNull();
    expect(
      within(nav).getByRole('link', { name: 'Judge calibration' }),
    ).toBeTruthy();
  });

  it('marks the followed section link as the current location and keeps the hash', () => {
    setHash(`#${NEWER}`);
    render(<App findings={twoFindings()} />);
    const nav = screen.getByRole('navigation', { name: 'Sections' });
    const overview = within(nav).getByRole('link', { name: 'Overview' });
    expect(overview.getAttribute('aria-current')).toBe('location');
    const utility = within(nav).getByRole('link', { name: 'Utility' });
    expect(fireEvent.click(utility)).toBe(false);
    expect(utility.getAttribute('aria-current')).toBe('location');
    expect(overview.getAttribute('aria-current')).toBeNull();
    expect(window.location.hash).toBe(`#${NEWER}`);
    expect(document.activeElement?.textContent).toBe('Utility');
  });
});

describe('the selected finding in the URL hash', () => {
  it('selects the finding the hash names', () => {
    setHash(`#${OLDER}`);
    render(<App findings={twoFindings()} />);
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(OLDER);
  });

  it.each([
    ['an unknown id', '#2099-01-01-nope'],
    ['a section id', `#${SECTIONS.utility.id}`],
    ['a malformed escape', '#%E0%A4%A'],
    ['markup', '#%3Cimg%20src%3Dx%3E'],
  ])('falls back to the newest finding for %s', (_, hash) => {
    setHash(hash);
    render(<App findings={twoFindings()} />);
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(NEWER);
  });

  it('records a choice in the hash and follows later hash changes to known ids only', () => {
    render(<App findings={twoFindings()} />);
    fireEvent.click(findingButton(OLDER));
    expect(window.location.hash).toBe(`#${OLDER}`);
    act(() => {
      setHash(`#${NEWER}`);
      window.dispatchEvent(new HashChangeEvent('hashchange'));
    });
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(NEWER);
    act(() => {
      setHash('#nothing-like-it');
      window.dispatchEvent(new HashChangeEvent('hashchange'));
    });
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(NEWER);
  });
});

describe('the section in view after switching findings', () => {
  type Entry = Partial<IntersectionObserverEntry>;
  interface Watcher {
    report: (entries: Entry[]) => void;
    watched: Element[];
    live: boolean;
  }
  let watchers: Watcher[] = [];

  class FakeObserver {
    private watcher: Watcher;
    constructor(report: (entries: Entry[]) => void) {
      this.watcher = { report, watched: [], live: true };
      watchers.push(this.watcher);
    }
    observe(element: Element) {
      this.watcher.watched.push(element);
    }
    disconnect() {
      this.watcher.live = false;
    }
  }

  beforeEach(() => {
    watchers = [];
    vi.stubGlobal('IntersectionObserver', FakeObserver);
  });
  afterEach(() => vi.unstubAllGlobals());

  function currentLink(): string | null | undefined {
    const nav = screen.getByRole('navigation', { name: 'Sections' });
    return within(nav)
      .getAllByRole('link')
      .find((link) => link.getAttribute('aria-current') === 'location')
      ?.textContent;
  }

  it("observes the new finding's sections and starts again at the overview", () => {
    // Both findings show the same sections, so the section ids are the same.
    const findings = [finding(NEWER), finding(OLDER)];
    expect(sectionIds(findings[0])).toEqual(sectionIds(findings[1]));
    render(<App findings={findings} />);
    const first = watchers.filter((w) => w.live);
    expect(first).toHaveLength(1);
    act(() =>
      first[0].report([
        {
          target: document.getElementById(SECTIONS.utility.id) as Element,
          isIntersecting: true,
        },
      ]),
    );
    expect(currentLink()).toBe('Utility');

    fireEvent.click(findingButton(OLDER));
    const live = watchers.filter((w) => w.live);
    expect(live).toHaveLength(1);
    expect(first[0].live).toBe(false);
    // Every observed element is in the page: none of the old finding's detached nodes.
    expect(live[0].watched.map((element) => element.id)).toEqual(
      sectionIds(findings[1]),
    );
    expect(live[0].watched.every((element) => element.isConnected)).toBe(true);
    expect(currentLink()).toBe('Overview');
    // And the new observer drives the navigation.
    act(() =>
      live[0].report([
        {
          target: document.getElementById(SECTIONS.limits.id) as Element,
          isIntersecting: true,
        },
      ]),
    );
    expect(currentLink()).toBe('Limits');
  });
});
