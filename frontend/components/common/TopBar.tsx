'use client';

import { Bell, Settings, User, Search } from 'lucide-react';

export function TopBar() {
  return (
    <header className="fixed top-0 right-0 left-64 h-16 border-b border-border/30 glass glass-subtle backdrop-blur-3xl z-30 animate-in-down shadow-premium">
      <div className="h-full px-8 flex items-center justify-between">
        {/* Search Bar */}
        <div className="relative max-w-md w-full">
          <input
            type="text"
            placeholder="Search assets, strategies..."
            className="w-full px-4 py-2.5 pl-10 rounded-lg bg-input border border-border/40 text-foreground placeholder-muted-foreground/50 transition-all duration-200 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 focus:bg-input text-sm shadow-[inset_0_2px_4px_rgba(0,0,0,0.05)]"
          />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/60" />
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-4">
          {/* Notification Bell */}
          <button className="relative p-2.5 rounded-lg transition-all duration-200 text-muted-foreground/70 hover:text-foreground hover:bg-surface-secondary/50 active:bg-surface-secondary/70 group">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary rounded-full animate-pulse" />
          </button>

          {/* Settings */}
          <button className="p-2.5 rounded-lg transition-all duration-200 text-muted-foreground/70 hover:text-foreground hover:bg-surface-secondary/50 active:bg-surface-secondary/70">
            <Settings className="w-5 h-5" />
          </button>

          {/* User Profile */}
          <div className="flex items-center gap-3 pl-4 border-l border-border/30">
            <div className="flex flex-col items-end">
              <p className="text-sm font-medium text-foreground leading-tight">Trader</p>
              <p className="text-xs text-muted-foreground/70 leading-tight">Pro Account</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary/30 to-cyan-500/20 flex items-center justify-center flex-shrink-0 shadow-[0_2px_8px_rgba(0,200,255,0.1)]">
              <User className="w-5 h-5 text-primary" />
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
