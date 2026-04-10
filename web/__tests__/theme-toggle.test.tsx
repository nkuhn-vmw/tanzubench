import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider } from '@/components/theme-provider';
import { ThemeToggle } from '@/components/theme-toggle';

function renderWithTheme() {
  return render(
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <ThemeToggle />
    </ThemeProvider>,
  );
}

describe('ThemeToggle', () => {
  it('renders an accessible button', () => {
    renderWithTheme();
    expect(screen.getByRole('button', { name: /theme/i })).toBeInTheDocument();
  });

  it('toggles the dark class on the html element when clicked', async () => {
    const user = userEvent.setup();
    renderWithTheme();
    const btn = screen.getByRole('button', { name: /theme/i });
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    await user.click(btn);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });
});
