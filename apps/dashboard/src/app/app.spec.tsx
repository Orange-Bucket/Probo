// SPDX-License-Identifier: Apache-2.0
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
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

/** The title in the top bar: the finding id, or Home. */
function pageTitle(): string | null {
  return screen.getByRole('heading', { level: 1 }).textContent;
}

function homeButton(): HTMLElement {
  const nav = screen.getByRole('navigation', { name: 'Dashboard' });
  return within(nav).getByRole('button', { name: 'Home' });
}

/** Renders the app with the hash naming `id`, so that it opens on that finding. */
function renderAt(id: string, findings = twoFindings()) {
  setHash(`#${encodeURIComponent(id)}`);
  return render(<App findings={findings} />);
}

afterEach(() => setHash(''));

describe('App', () => {
  it('always shows the two fixed sentences and the terms at the top of a finding', () => {
    renderAt(OLDER, [finding(OLDER, { calibration: null })]);
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
    renderAt(OLDER, [finding(OLDER, { report: incomplete })]);
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
    renderAt(OLDER, [finding(OLDER, { report: mixed })]);
    expect(screen.getByRole('alert').textContent).toBe(CORPUS_WARNING);
  });

  it('shows the finding the hash names and switches on choice', () => {
    renderAt(NEWER);
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

  it('says so on Home when no finding is published, inside the same shell', () => {
    render(<App findings={[]} />);
    expect(screen.getByText('No findings are published.')).toBeTruthy();
    expect(screen.getByText('Nothing to show yet')).toBeTruthy();
    expect(pageTitle()).toBe('Home');
    expect(homeButton().getAttribute('aria-current')).toBe('page');
    expect(screen.getByRole('main')).toBeTruthy();
    expect(screen.getByRole('banner')).toBeTruthy();
    expect(screen.queryByRole('navigation', { name: 'Sections' })).toBeNull();
    expect(screen.queryByRole('article')).toBeNull();
  });
});

describe('the application shell', () => {
  it('has the landmarks, one h1, and headings that never skip a level', () => {
    renderAt(NEWER);
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
    ).toEqual(['Dashboard', 'Findings', 'Sections']);
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
    renderAt(NEWER);
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
    expect(homeButton().getAttribute('aria-current')).toBeNull();
  });

  it('links every section of the shown finding, and nothing else', () => {
    renderAt(NEWER);
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

describe('the page in the URL hash', () => {
  it('shows Home when there is no hash', () => {
    render(<App findings={twoFindings()} />);
    expect(pageTitle()).toBe('Home');
    expect(screen.queryByRole('article')).toBeNull();
    expect(
      screen.getByRole('region', { name: 'Finding reports' }),
    ).toBeTruthy();
  });

  it('selects the finding the hash names', () => {
    setHash(`#${OLDER}`);
    render(<App findings={twoFindings()} />);
    expect(pageTitle()).toBe(OLDER);
    expect(screen.getByRole('article')).toBeTruthy();
  });

  it.each([
    ['only #', '#'],
    ['an unknown id', '#2099-01-01-nope'],
    ['a section id', `#${SECTIONS.utility.id}`],
    ['a malformed escape', '#%E0%A4%A'],
    ['markup', '#%3Cimg%20src%3Dx%3E'],
  ])('shows Home for %s', (_, hash) => {
    setHash(hash);
    render(<App findings={twoFindings()} />);
    expect(pageTitle()).toBe('Home');
    expect(screen.queryByRole('article')).toBeNull();
  });

  it('records a choice in the hash and follows later hash changes', () => {
    render(<App findings={twoFindings()} />);
    fireEvent.click(findingButton(OLDER));
    expect(window.location.hash).toBe(`#${OLDER}`);
    act(() => {
      setHash(`#${NEWER}`);
      window.dispatchEvent(new HashChangeEvent('hashchange'));
    });
    expect(pageTitle()).toBe(NEWER);
    // A hash that names no finding shows Home.
    act(() => {
      setHash('#nothing-like-it');
      window.dispatchEvent(new HashChangeEvent('hashchange'));
    });
    expect(pageTitle()).toBe('Home');
  });

  it('shows Home when Home is chosen, and clears the hash', () => {
    renderAt(OLDER);
    fireEvent.click(homeButton());
    expect(pageTitle()).toBe('Home');
    expect(window.location.hash).toBe('');
    expect(homeButton().getAttribute('aria-current')).toBe('page');
    const nav = screen.getByRole('navigation', { name: 'Findings' });
    for (const button of within(nav).getAllByRole('button')) {
      expect(button.getAttribute('aria-current')).toBeNull();
    }
    expect(screen.queryByRole('navigation', { name: 'Sections' })).toBeNull();
    expect(screen.queryByRole('article')).toBeNull();
    // No status, model or date in the top bar on Home.
    const banner = screen.getByRole('banner');
    expect(within(banner).queryByText('complete')).toBeNull();
    expect(within(banner).queryByText('mockllm/model')).toBeNull();
  });

  it('goes back and forward between Home and findings', async () => {
    render(<App findings={twoFindings()} />);
    expect(pageTitle()).toBe('Home');
    fireEvent.click(findingButton(OLDER));
    fireEvent.click(homeButton());
    fireEvent.click(findingButton(NEWER));
    expect(pageTitle()).toBe(NEWER);
    act(() => window.history.back());
    await waitFor(() => expect(pageTitle()).toBe('Home'));
    expect(window.location.hash).toBe('');
    act(() => window.history.back());
    await waitFor(() => expect(pageTitle()).toBe(OLDER));
    act(() => window.history.back());
    await waitFor(() => expect(pageTitle()).toBe('Home'));
    act(() => window.history.forward());
    await waitFor(() => expect(pageTitle()).toBe(OLDER));
    act(() => window.history.forward());
    await waitFor(() => expect(pageTitle()).toBe('Home'));
    expect(homeButton().getAttribute('aria-current')).toBe('page');
  });
});

describe('Home', () => {
  it('has the landmarks, one h1, and headings that never skip a level', () => {
    render(<App findings={twoFindings()} />);
    const banner = screen.getByRole('banner');
    expect(within(banner).getByRole('heading', { level: 1 }).textContent).toBe(
      'Home',
    );
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(
      screen
        .getAllByRole('navigation')
        .map((nav) => nav.getAttribute('aria-label')),
    ).toEqual(['Dashboard', 'Findings']);
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

  it('opens the newest finding, and any finding of its list', () => {
    render(<App findings={twoFindings()} />);
    const main = screen.getByRole('main');
    fireEvent.click(
      within(main).getByRole('button', { name: 'Open the newest finding' }),
    );
    expect(pageTitle()).toBe(NEWER);
    expect(window.location.hash).toBe(`#${NEWER}`);
    fireEvent.click(homeButton());
    fireEvent.click(
      within(screen.getByRole('main')).getByRole('button', {
        name: new RegExp(`^${OLDER} `),
      }),
    );
    expect(pageTitle()).toBe(OLDER);
    expect(findingButton(OLDER).getAttribute('aria-current')).toBe('true');
  });

  it('moves focus to the title when a finding is opened from the page', () => {
    render(<App findings={twoFindings()} />);
    const open = within(screen.getByRole('main')).getByRole('button', {
      name: 'Open the newest finding',
    });
    open.focus();
    fireEvent.click(open);
    expect(document.activeElement).toBe(
      screen.getByRole('heading', { level: 1 }),
    );
  });

  it('replaces an unknown hash, adding no history entry, when Home is chosen on Home', () => {
    window.history.replaceState(null, '', '/#nothing-like-it');
    render(<App findings={twoFindings()} />);
    const before = window.history.length;
    fireEvent.click(homeButton());
    expect(window.location.hash).toBe('');
    expect(window.history.length).toBe(before);
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
    renderAt(NEWER, findings);
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

    // Through Home and back, the same finding starts again at the overview too.
    fireEvent.click(homeButton());
    fireEvent.click(findingButton(NEWER));
    expect(currentLink()).toBe('Overview');

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
