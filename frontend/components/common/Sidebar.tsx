'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  TrendingUp,
  FileText,
  Zap,
  Briefcase,
  CommandIcon,
} from 'lucide-react';

const navItems = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: BarChart3,
    label: 'Overview',
  },
  {
    name: 'Assets',
    href: '/asset/AAPL',
    icon: TrendingUp,
    label: 'Analysis',
  },
  {
    name: 'Reports',
    href: '/report',
    icon: FileText,
    label: 'AI Research',
  },
  {
    name: 'Backtest',
    href: '/backtest',
    icon: Zap,
    label: 'Strategies',
  },
  {
    name: 'Portfolio',
    href: '/portfolio',
    icon: Briefcase,
    label: 'Watchlist',
  },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-gradient-to-b from-surface via-background to-background border-r border-border/50 glass-subtle backdrop-blur-2xl z-40 animate-in-left flex flex-col">
      {/* Logo Section */}
      <div className="flex items-center gap-3 px-6 py-6 border-b border-border/30">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary/30 to-cyan-500/20 flex items-center justify-center flex-shrink-0">
          <CommandIcon className="w-5 h-5 text-primary" />
        </div>
        <div className="flex flex-col min-w-0">
          <span className="text-sm font-bold text-foreground truncate">AXIOM</span>
          <span className="text-xs text-muted-foreground/70">Terminal</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-6 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname?.startsWith(item.href.split('/').slice(0, 2).join('/'));

          return (
            <Link
              key={item.name}
              href={item.href}
              className={`group relative flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 ${
                isActive
                  ? 'bg-gradient-to-r from-primary/15 to-cyan-500/5 text-primary border border-primary/30 shadow-[0_0_16px_rgba(0,200,255,0.1)]'
                  : 'text-muted-foreground hover:text-foreground hover:bg-surface-secondary/50 border border-transparent'
              }`}
            >
              {isActive && (
                <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              )}
              <Icon className="w-4.5 h-4.5 flex-shrink-0 relative z-10" />
              <div className="flex-1 relative z-10 min-w-0">
                <div className="text-sm font-medium leading-tight">{item.name}</div>
                <div className="text-xs text-muted-foreground/60 leading-tight truncate">{item.label}</div>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-border/30 px-4 py-4 space-y-3">
        <div className="px-3 py-2.5 rounded-lg bg-surface-secondary/20 border border-border/20 transition-all hover:bg-surface-secondary/30 hover:border-border/30">
          <p className="text-label text-muted-foreground/70 text-xs">API STATUS</p>
          <div className="flex items-center gap-2 mt-2">
            <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
            <span className="text-xs text-foreground/80">Connected</span>
          </div>
        </div>
        <p className="text-xs text-muted-foreground/60 text-center leading-relaxed">
          Powered by AI & Finance
        </p>
      </div>
    </aside>
  );
}
