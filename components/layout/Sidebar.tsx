"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  LineChart,
  Brain,
  FlaskConical,
  Briefcase,
  Globe,
  Terminal,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/assets/AAPL", label: "Asset Detail", icon: LineChart },
  { href: "/ai-analyst", label: "AI Analyst", icon: Brain },
  { href: "/backtests", label: "Backtest Lab", icon: FlaskConical },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/world-hub", label: "World Hub", icon: Globe },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-60 flex-col border-r border-border bg-surface">
      <div className="flex h-14 items-center gap-2 border-b border-border px-5">
        <Terminal className="h-5 w-5 text-accent" />
        <span className="text-lg font-semibold tracking-tight text-text-primary">
          BlackGrid
        </span>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href.split("/").slice(0, 2).join("/")));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
                isActive
                  ? "bg-accent/10 text-accent"
                  : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border px-5 py-4">
        <p className="text-xs text-text-muted">Research tool only.</p>
        <p className="text-xs text-text-muted">Not financial advice.</p>
      </div>
    </aside>
  );
}
