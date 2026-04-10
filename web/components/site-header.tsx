import Link from 'next/link';
import { ThemeToggle } from '@/components/theme-toggle';
import { MobileNav } from '@/components/mobile-nav';

export function SiteHeader() {
  return (
    <header className="border-b bg-background">
      <div className="container flex h-16 items-center justify-between gap-3">
        {/* Left: logo + inline nav (nav hidden below sm) */}
        <div className="flex items-center gap-4 sm:gap-8 min-w-0">
          <Link href="/" className="flex items-center gap-2.5 min-w-0">
            <div className="h-9 w-9 shrink-0 rounded-md bg-gradient-to-br from-tanzu to-tanzu-light flex items-center justify-center text-white font-bold text-base shadow-sm">
              T
            </div>
            <span className="font-bold text-base sm:text-lg tracking-tight truncate">
              TanzuBench
            </span>
          </Link>
          <nav className="hidden sm:flex items-center gap-6 text-base text-muted-foreground">
            <Link href="/" className="hover:text-foreground transition-colors">
              Leaderboard
            </Link>
            <Link href="/foundations" className="hover:text-foreground transition-colors">
              Foundations
            </Link>
            <Link href="/compare" className="hover:text-foreground transition-colors">
              Compare
            </Link>
            <Link href="/about" className="hover:text-foreground transition-colors">
              About
            </Link>
          </nav>
        </div>

        {/* Right: theme toggle, GitHub (hidden on xs), mobile hamburger */}
        <div className="flex items-center gap-2 sm:gap-4">
          <ThemeToggle />
          <a
            href="https://github.com/nkuhn-vmw/tanzubench"
            target="_blank"
            rel="noreferrer"
            className="hidden sm:inline text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            GitHub
          </a>
          <MobileNav />
        </div>
      </div>
    </header>
  );
}
