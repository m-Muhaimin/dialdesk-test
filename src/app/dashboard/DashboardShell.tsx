'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { logout } from '@/app/actions/auth';

const NAV = [
  { href: '/dashboard', label: 'Overview', mark: 'O' },
  { href: '/dashboard/appointments', label: 'Appointments', mark: 'A' },
  { href: '/dashboard/calls', label: 'Calls', mark: 'C' },
  { href: '/dashboard/leads', label: 'Leads', mark: 'L' },
  { href: '/dashboard/agent', label: 'Agent settings', mark: 'S' },
  { href: '/dashboard/billing', label: 'Billing', mark: 'B' },
  { href: '/dashboard/profile', label: 'Profile settings', mark: 'P' },
];

function pageTitle(pathname: string) {
  return NAV.find(({ href }) => href === pathname)?.label ?? 'Dashboard';
}

function initials(name: string) {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('') || 'U';
}

export default function DashboardShell({
  children,
  businessName,
  userName,
  email,
}: {
  children: React.ReactNode;
  businessName: string;
  userName: string;
  email: string;
}) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-paper text-ink md:flex">
      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-ink/40 md:hidden"
          aria-label="Close navigation menu"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-[min(84vw,280px)] flex-col border-r border-mist bg-white transition-[transform,width] duration-200 md:sticky md:top-0 md:h-screen md:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        } ${collapsed ? 'md:w-[84px]' : 'md:w-[248px]'}`}
      >
        <div className={`flex h-[72px] items-center justify-between border-b border-mist px-5 ${collapsed ? 'md:px-2' : ''}`}>
          <Link
            href="/dashboard"
            className="whitespace-nowrap text-lg font-bold tracking-tight"
            onClick={() => setMobileOpen(false)}
          >
            <span className={collapsed ? 'md:hidden' : ''}>
              Dial<span className="text-lamp">Desk</span>
            </span>
            {collapsed && <span className="hidden text-lamp md:inline">D</span>}
          </Link>
          <button
            type="button"
            className="hidden h-9 w-9 items-center justify-center rounded-lg text-slate2 hover:bg-paper hover:text-ink md:inline-flex"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-expanded={!collapsed}
            onClick={() => setCollapsed((value) => !value)}
          >
            <span aria-hidden="true">{collapsed ? '›' : '‹'}</span>
          </button>
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate2 hover:bg-paper md:hidden"
            aria-label="Close navigation menu"
            onClick={() => setMobileOpen(false)}
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>

        <div className={`truncate px-5 py-4 text-xs font-medium text-slate2 ${collapsed ? 'md:px-0 md:text-center' : ''}`}>
          <span className={collapsed ? 'md:sr-only' : ''}>{businessName}</span>
          {collapsed && (
            <span className="hidden md:inline" title={businessName}>
              {businessName.slice(0, 1).toUpperCase()}
            </span>
          )}
        </div>

        <nav className="flex-1 space-y-1 px-3" aria-label="Dashboard">
          {NAV.map(({ href, label, mark }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? 'page' : undefined}
                title={collapsed ? label : undefined}
                onClick={() => setMobileOpen(false)}
                className={`flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors ${
                  active
                    ? 'bg-ink text-white'
                    : 'text-slate2 hover:bg-paper hover:text-ink'
                } ${collapsed ? 'md:justify-center md:px-0' : ''}`}
              >
                <span
                  className={`grid h-7 w-7 shrink-0 place-items-center rounded-md text-xs font-bold ${
                    active ? 'bg-white/15 text-white' : 'bg-paper text-slate2'
                  }`}
                  aria-hidden="true"
                >
                  {mark}
                </span>
                <span className={collapsed ? 'md:sr-only' : ''}>{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-mist p-4">
          <p className={`truncate text-xs text-slate2 ${collapsed ? 'md:sr-only' : ''}`}>{email}</p>
          <form action={logout} className="mt-2">
            <button
              type="submit"
              title={collapsed ? 'Sign out' : undefined}
              className={`w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-slate2 hover:bg-paper hover:text-ink ${
                collapsed ? 'md:px-0 md:text-center' : ''
              }`}
            >
              <span className={collapsed ? 'md:sr-only' : ''}>Sign out</span>
              {collapsed && <span className="hidden md:inline" aria-hidden="true">↗</span>}
            </button>
          </form>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-mist bg-white/95 px-4 backdrop-blur md:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-mist text-ink hover:bg-paper md:hidden"
              aria-label="Open navigation menu"
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen(true)}
            >
              <span aria-hidden="true">☰</span>
            </button>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{pageTitle(pathname)}</p>
              <p className="hidden truncate text-xs text-slate2 sm:block">{businessName}</p>
            </div>
          </div>

          <details className="group relative shrink-0">
            <summary className="flex cursor-pointer list-none items-center gap-2 rounded-lg p-1.5 hover:bg-paper focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink">
              <span className="grid h-9 w-9 place-items-center rounded-full bg-ink text-xs font-semibold text-white">
                {initials(userName)}
              </span>
              <span className="hidden max-w-40 truncate text-sm font-medium sm:block">{userName}</span>
              <span className="pr-1 text-xs text-slate2" aria-hidden="true">⌄</span>
              <span className="sr-only">Open user menu</span>
            </summary>
            <div className="absolute right-0 top-full mt-2 w-64 rounded-xl border border-mist bg-white p-2 shadow-lg">
              <div className="border-b border-mist px-3 py-2">
                <p className="truncate text-sm font-semibold">{userName}</p>
                <p className="truncate text-xs text-slate2">{email}</p>
              </div>
              <Link
                href="/dashboard/profile"
                onClick={(event) => event.currentTarget.closest('details')?.removeAttribute('open')}
                className="mt-1 block rounded-lg px-3 py-2 text-sm text-ink hover:bg-paper"
              >
                Profile settings
              </Link>
              <form action={logout}>
                <button
                  type="submit"
                  className="w-full rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-paper"
                >
                  Sign out
                </button>
              </form>
            </div>
          </details>
        </header>

        <main className="mx-auto w-full max-w-[1440px] p-4 md:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
