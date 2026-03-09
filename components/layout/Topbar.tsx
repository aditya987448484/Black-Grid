"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, Bell } from "lucide-react";
import { searchCompanies } from "@/lib/api";
import type { CompanySearchResult } from "@/types/universe";

export default function Topbar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CompanySearchResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const router = useRouter();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.length < 1) {
      setResults([]);
      setShowDropdown(false);
      return;
    }

    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      searchCompanies(query)
        .then((res) => {
          setResults(res.results);
          setShowDropdown(res.results.length > 0);
          setSelectedIdx(-1);
        })
        .catch(() => setResults([]));
    }, 200);

    return () => clearTimeout(debounceRef.current);
  }, [query]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function navigate(symbol: string) {
    router.push(`/assets/${symbol}`);
    setQuery("");
    setShowDropdown(false);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (selectedIdx >= 0 && results[selectedIdx]) {
      navigate(results[selectedIdx].symbol);
    } else if (query.trim()) {
      navigate(query.trim().toUpperCase());
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!showDropdown) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((prev) => Math.min(prev + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((prev) => Math.max(prev - 1, -1));
    } else if (e.key === "Escape") {
      setShowDropdown(false);
    }
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-surface/80 px-6 backdrop-blur-md">
      <div ref={wrapperRef} className="relative">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <Search className="h-4 w-4 text-text-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => results.length > 0 && setShowDropdown(true)}
            onKeyDown={handleKeyDown}
            placeholder="Search any company or ticker..."
            className="w-80 bg-transparent text-sm text-text-primary placeholder-text-muted outline-none"
          />
        </form>

        {showDropdown && (
          <div className="absolute top-10 left-0 w-96 glass-card py-1 shadow-xl z-50 max-h-80 overflow-y-auto">
            {results.map((r, i) => (
              <button
                key={r.symbol}
                onClick={() => navigate(r.symbol)}
                className={`w-full text-left px-4 py-2.5 flex items-center justify-between transition-colors ${
                  i === selectedIdx
                    ? "bg-accent/10"
                    : "hover:bg-surface-hover"
                }`}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-accent">{r.symbol}</span>
                    {r.exchange && (
                      <span className="text-[10px] text-text-muted bg-surface-hover rounded px-1.5 py-0.5">
                        {r.exchange}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-text-secondary truncate">{r.name}</p>
                </div>
                {r.sector && (
                  <span className="text-[10px] text-text-muted flex-shrink-0 ml-3">{r.sector}</span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        <button className="relative text-text-secondary hover:text-text-primary transition-colors">
          <Bell className="h-4 w-4" />
          <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-accent" />
        </button>
        <div className="h-8 w-8 rounded-full bg-accent/20 flex items-center justify-center text-xs font-semibold text-accent">
          BG
        </div>
      </div>
    </header>
  );
}
