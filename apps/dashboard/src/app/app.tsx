// SPDX-License-Identifier: Apache-2.0
// Uncomment this line to use CSS modules
// import styles from './app.module.css';

export function App() {
  return (
    <main>
      <h1>Probo findings</h1>
      <p>This dashboard is under construction.</p>
    </main>
  );
}

export default App;

if (import.meta.vitest) {
  const { it, expect, beforeEach, afterEach } = import.meta.vitest;
  let render: typeof import('@testing-library/react').render;
  let cleanup: typeof import('@testing-library/react').cleanup;

  beforeEach(async () => {
    ({ render, cleanup } = await import('@testing-library/react'));
  });

  // Testing Library is imported lazily, so its automatic cleanup is not
  // registered; unmount explicitly so each test starts from an empty document.
  afterEach(() => {
    cleanup();
  });

  it('should render successfully', () => {
    const { baseElement } = render(<App />);
    expect(baseElement).toBeTruthy();
  });

  it('should have "Probo findings" as the heading', () => {
    const { getByRole } = render(<App />);
    expect(
      getByRole('heading', { level: 1, name: 'Probo findings' }),
    ).toBeTruthy();
  });
}
