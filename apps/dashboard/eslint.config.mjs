// SPDX-License-Identifier: Apache-2.0
import nx from '@nx/eslint-plugin';
import baseConfig from '../../eslint.config.mjs';

export default [
  ...nx.configs['flat/react'],
  ...baseConfig,
  {
    files: ['**/*.ts', '**/*.tsx', '**/*.js', '**/*.jsx'],
    // Override or add rules here
    rules: {},
  },
  {
    // Text from logs and reports is untrusted: React must render it as text.
    files: ['src/**/*.ts', 'src/**/*.tsx'],
    rules: {
      'react/no-danger': 'error',
    },
  },
];
