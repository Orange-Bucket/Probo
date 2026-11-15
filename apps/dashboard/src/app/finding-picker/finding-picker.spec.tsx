// SPDX-License-Identifier: Apache-2.0
import { fireEvent, render, screen } from '@testing-library/react';
import FindingPicker from './finding-picker';

describe('FindingPicker', () => {
  it('names the only finding without offering a choice', () => {
    render(
      <FindingPicker
        ids={['2026-01-01-a']}
        selected="2026-01-01-a"
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText('2026-01-01-a')).toBeTruthy();
    expect(screen.queryByRole('combobox')).toBeNull();
  });

  it('offers the findings in the order given and reports the choice', () => {
    const onSelect = vi.fn();
    render(
      <FindingPicker
        ids={['2026-03-01-b', '2026-01-01-a']}
        selected="2026-03-01-b"
        onSelect={onSelect}
      />,
    );
    const select = screen.getByRole('combobox', { name: 'Finding' });
    const options = screen
      .getAllByRole('option')
      .map((option) => option.textContent);
    expect(options).toEqual(['2026-03-01-b', '2026-01-01-a']);
    fireEvent.change(select, { target: { value: '2026-01-01-a' } });
    expect(onSelect).toHaveBeenCalledWith('2026-01-01-a');
  });
});
