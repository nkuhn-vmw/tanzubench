'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/', label: 'Leaderboard' },
  { href: '/foundations', label: 'Foundations' },
  { href: '/compare', label: 'Compare' },
  { href: '/about', label: 'About' },
];

/**
 * Mobile hamburger menu. Hidden on sm+ (the site header renders an
 * inline <nav> at those widths instead). On mobile (<sm) it shows a
 * button that toggles a dropdown panel with the nav links.
 *
 * This component owns its own open/closed state — it's a small
 * self-contained client island inside the otherwise-server SiteHeader.
 */
export function MobileNav() {
  const [open, setOpen] = useState(false);

  return (
    <div className="sm:hidden relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-border bg-background text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        aria-label={open ? 'Close menu' : 'Open menu'}
        aria-expanded={open}
      >
        {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {open && (
        <>
          {/* Click-outside backdrop */}
          <div
            className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          {/* Dropdown panel */}
          <nav
            className="absolute right-0 top-12 z-50 w-56 rounded-lg border border-border bg-popover p-2 shadow-lg"
            aria-label="Mobile navigation"
          >
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={cn(
                  'block rounded-md px-3 py-2 text-base font-medium',
                  'text-foreground hover:bg-accent hover:text-accent-foreground',
                  'transition-colors',
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </>
      )}
    </div>
  );
}
