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
    // Text from logs and reports is untrusted: React must render it as text, and no
    // string may become code.
    files: ['src/**/*.ts', 'src/**/*.tsx'],
    rules: {
      'react/no-danger': 'error',
      'no-restricted-syntax': [
        'error',
        ...[
          "JSXAttribute[name.name='dangerouslySetInnerHTML']",
          "Property[key.name='dangerouslySetInnerHTML']",
          "Property[key.value='dangerouslySetInnerHTML']",
          "MemberExpression[property.name='dangerouslySetInnerHTML']",
          "MemberExpression[property.value='dangerouslySetInnerHTML']",
        ].map((selector) => ({
          selector,
          message:
            'Render text from logs and reports as React text, never as HTML.',
        })),
      ],
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',
    },
  },
];
