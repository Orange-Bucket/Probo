// SPDX-License-Identifier: Apache-2.0
import { StrictMode } from 'react';
import * as ReactDOM from 'react-dom/client';
import App from './app/app';
import { applyTheme, readStoredTheme } from './theme';

// Apply a stored theme choice before the first render, so the page does not flash.
applyTheme(readStoredTheme());

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement,
);

root.render(
  <StrictMode>
    <App />
  </StrictMode>,
);
