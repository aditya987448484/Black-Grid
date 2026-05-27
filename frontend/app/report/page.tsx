'use client';

import { useState, useCallback } from 'react';
import {
  Star, RefreshCw, Download, Share2,
  TrendingUp, TrendingDown, AlertCircle, Target,
  Search, Loader, AlertTriangle, Zap as Spark,
  BarChart2, Activity, Building2, Globe,
} from 'lucide-react';
import { GlassCard } from '@/components/common/Card';
import { DashboardLayoutWrapper } from '@/components/common/DashboardLayout';
import { useApi } from '@/lib/hooks/useApi';
import { report } from '@/lib/api/client';
import type { AnalystReport, FundamentalSnapshot, MacroContext } from '@/lib/types';

// ---------------------------------------------------------------------------
// Small reusable atoms
// ---------------------------------------------------------------------------

function SeverityBadge({ severity }: { severity: string }) {
  const cls = {
    High: 'bg-destructive/10 text-destructive border-destructive/30',
    Medium: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    Low: 'bg-success/10 text-success border-success/30',
  }[severity] ?? 'bg-surface-secondary/20 text-muted-foreground/70 border-border/20';
  return (
    <span className={`px-2 py-0.5 text-[10px] font-bold rounded border uppercase tracking-wider ${cls}`}>
      {severity}
    </span>
  );
}

function RecommendationBadge({ recommendation }: { recommendation: string }) {
  const cls = {
    BUY: 'bg-success/10 text-success border-success/30',
    HOLD: 'bg-primary/10 text-primary border-primary/30',
    SELL: 'bg-destructive/10 text-destructive border-destructive/30',
  }[recommendation] ?? 'bg-surface-secondary/20 text-muted-foreground/70 border-border/20';
  return (
    <span className={`px-3 py-2 text-sm font-bold rounded border tracking-wider ${cls}`}>
      {recommendation}
    </span>
  );
}

function OutlookBadge({ outlook }: { outlook: string }) {
  const cls = {
    Positive: 'bg-success/10 text-success border-success/25',
    Neutral: 'bg-primary/10 text-primary border-primary/25',
    Negative: 'bg-destructive/10 text-destructive border-destructive/25',
  }[outlook] ?? 'bg-surface-secondary/20 text-muted-foreground/60 border-border/20';
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-bold rounded-full border ${cls}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {outlook}
    </span>
  );
}

function ValuationBadge({ assessment }: { assessment: string }) {
  const cls = assessment.toLowerCase().includes('under')
    ? 'bg-success/10 text-success border-success/25'
    : assessment.toLowerCase().includes('over')
    ? 'bg-destructive/10 text-destructive border-destructive/25'
    : 'bg-primary/10 text-primary border-primary/25';
  return (
    <span className={`inline-flex items-center px-2.5 py-1 text-xs font-bold rounded-full border ${cls}`}>
      {assessment}
    </span>
  );
}

/** Compact labeled stat cell */
function Stat({
  label,
  value,
  sub,
  color = 'text-foreground',
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  color?: string;
}) {
  return (
    <div className="px-4 py-3.5 rounded-lg bg-surface-secondary/25 border border-border/15 hover:border-border/30 transition-colors duration-200">
      <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-2">{label}</p>
      <p className={`text-xl font-bold tracking-tight ${color}`}>{value}</p>
      {sub && <p className="text-[11px] text-muted-foreground/50 mt-1">{sub}</p>}
    </div>
  );
}

/** Horizontal quality bar */
function QualityBar({ score }: { score: number }) {
  const color =
    score >= 75 ? 'bg-success' : score >= 50 ? 'bg-amber-400' : 'bg-destructive';
  return (
    <div className="px-4 py-3.5 rounded-lg bg-surface-secondary/25 border border-border/15 hover:border-border/30 transition-colors duration-200">
      <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-2">Quality Score</p>
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 rounded-full bg-surface-secondary/60">
          <div className={`h-full rounded-full ${color} transition-all duration-700`} style={{ width: `${score}%` }} />
        </div>
        <span className="text-sm font-bold text-foreground tracking-tight">{score.toFixed(0)}</span>
      </div>
    </div>
  );
}

/** Section separator with icon + title */
function SectionHeader({
  icon,
  title,
  badge,
}: {
  icon: React.ReactNode;
  title: string;
  badge?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2.5 mb-5">
      <span className="text-primary/80">{icon}</span>
      <h3 className="text-base font-bold text-foreground tracking-tight">{title}</h3>
      {badge}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Fundamentals section
// ---------------------------------------------------------------------------

function FundamentalsSection({ snap }: { snap: FundamentalSnapshot }) {
  // Derive debt risk level from D/E
  const de = snap.debt_to_equity;
  const deColor =
    de === null ? 'text-foreground'
    : de < 1.0 ? 'text-success'
    : de < 2.0 ? 'text-amber-400'
    : 'text-destructive';
  const deLabel =
    de === null ? '—'
    : de < 1.0 ? 'Low leverage'
    : de < 2.0 ? 'Moderate leverage'
    : 'High leverage';

  return (
    <div className="space-y-4">
      <SectionHeader
        icon={<BarChart2 className="w-4.5 h-4.5" />}
        title="Fundamental Snapshot"
        badge={<ValuationBadge assessment={snap.valuation_assessment} />}
      />

      {/* Income metrics row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {snap.eps !== null && (
          <Stat
            label="EPS (Diluted)"
            value={`$${snap.eps.toFixed(2)}`}
            sub="Most recent annual"
          />
        )}
        {snap.revenue_growth !== null && (
          <Stat
            label="Revenue Growth"
            value={`${snap.revenue_growth >= 0 ? '+' : ''}${snap.revenue_growth.toFixed(1)}%`}
            color={snap.revenue_growth >= 0 ? 'text-success' : 'text-destructive'}
            sub="Year-over-year"
          />
        )}
        {snap.profit_margin !== null && (
          <Stat
            label="Profit Margin"
            value={`${snap.profit_margin.toFixed(1)}%`}
            color={snap.profit_margin >= 15 ? 'text-success' : snap.profit_margin >= 5 ? 'text-amber-400' : 'text-destructive'}
            sub="Net income / revenue"
          />
        )}
        {snap.roe !== null && (
          <Stat
            label="ROE"
            value={`${snap.roe.toFixed(1)}%`}
            color={snap.roe >= 20 ? 'text-success' : snap.roe >= 10 ? 'text-amber-400' : 'text-destructive'}
            sub="Return on equity"
          />
        )}
      </div>

      {/* Balance sheet + quality row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {de !== null && (
          <Stat
            label="Debt / Equity"
            value={de.toFixed(2)}
            color={deColor}
            sub={deLabel}
          />
        )}
        <QualityBar score={snap.quality_score} />
        <div className="px-4 py-3.5 rounded-lg bg-surface-secondary/25 border border-border/15">
          <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-2">Valuation</p>
          <ValuationBadge assessment={snap.valuation_assessment} />
          <p className="text-[11px] text-muted-foreground/50 mt-2">vs. sector peers</p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Macro context section
// ---------------------------------------------------------------------------

function MacroSection({ macro }: { macro: MacroContext }) {
  const correlationLabel =
    macro.correlation_market >= 0.8 ? 'High'
    : macro.correlation_market >= 0.5 ? 'Moderate'
    : 'Low';
  const correlationColor =
    macro.correlation_market >= 0.8 ? 'text-amber-400'
    : macro.correlation_market >= 0.5 ? 'text-primary'
    : 'text-success';

  return (
    <div className="space-y-4">
      <SectionHeader
        icon={<Globe className="w-4.5 h-4.5" />}
        title="Macro & Rate Environment"
        badge={<OutlookBadge outlook={macro.macro_outlook} />}
      />

      {/* Summary stats row */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <div className="px-4 py-3.5 rounded-lg bg-surface-secondary/25 border border-border/15">
          <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-2">Sector vs. Market</p>
          <p className="text-base font-bold text-foreground">{macro.sector_performance}</p>
        </div>
        <div className="px-4 py-3.5 rounded-lg bg-surface-secondary/25 border border-border/15">
          <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-2">Market Correlation</p>
          <p className={`text-base font-bold ${correlationColor}`}>{macro.correlation_market.toFixed(2)}</p>
          <p className="text-[11px] text-muted-foreground/50 mt-1">{correlationLabel} β sensitivity</p>
        </div>
        <div className="px-4 py-3.5 rounded-lg bg-surface-secondary/25 border border-border/15 flex items-center gap-3">
          <div>
            <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-2">Overall Outlook</p>
            <OutlookBadge outlook={macro.macro_outlook} />
          </div>
        </div>
      </div>

      {/* Tailwinds / headwinds */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="p-4 rounded-lg bg-success/5 border border-success/15">
          <p className="text-[10px] font-bold text-success uppercase tracking-widest mb-3 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-success inline-block" />
            Tailwinds
          </p>
          <ul className="space-y-2.5">
            {macro.industry_tailwinds.map((t, i) => (
              <li key={i} className="text-sm text-foreground/85 leading-snug flex items-start gap-2">
                <span className="text-success/70 mt-0.5 flex-shrink-0">+</span>
                {t}
              </li>
            ))}
          </ul>
        </div>
        <div className="p-4 rounded-lg bg-destructive/5 border border-destructive/15">
          <p className="text-[10px] font-bold text-destructive uppercase tracking-widest mb-3 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-destructive inline-block" />
            Headwinds
          </p>
          <ul className="space-y-2.5">
            {macro.macro_headwinds.map((h, i) => (
              <li key={i} className="text-sm text-foreground/85 leading-snug flex items-start gap-2">
                <span className="text-destructive/70 mt-0.5 flex-shrink-0">−</span>
                {h}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* FRED data source note */}
      <p className="text-[11px] text-muted-foreground/40 font-medium">
        Macro analysis incorporates real-time FRED indicators: 10-Year Treasury, Fed Funds Rate, CPI, and unemployment data.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ReportPage() {
  const [searchTicker, setSearchTicker] = useState('AAPL');
  const [selectedTicker, setSelectedTicker] = useState('AAPL');

  const reportRequest = useCallback(() => report.getAnalystReport(selectedTicker), [selectedTicker]);
  const { data: reportData, status } = useApi<AnalystReport>(reportRequest, !!selectedTicker);

  const isLoading = status === 'pending';
  const hasError = status === 'error';

  const handleSearch = () => {
    if (searchTicker.trim()) setSelectedTicker(searchTicker.trim().toUpperCase());
  };

  const upsideColor =
    reportData?.final_rating?.price_upside != null && reportData.final_rating.price_upside >= 0
      ? 'text-success'
      : 'text-destructive';

  return (
    <DashboardLayoutWrapper>
      <div className="min-h-screen section-padding py-6">
        {/* Page header */}
        <div className="animate-in mb-8">
          <h1 className="text-5xl font-bold tracking-tight text-foreground leading-tight">
            Institutional Research Reports
          </h1>
          <p className="text-sm text-muted-foreground/70 mt-2 font-medium">
            AI-generated analyst reports — fundamentals, macro context &amp; price targets
          </p>
        </div>

        {/* Ticker search */}
        <GlassCard className="animate-in-up mb-8" style={{ animationDelay: '80ms' }}>
          <div className="flex items-center gap-4">
            <input
              type="text"
              placeholder="Enter ticker (e.g. AAPL, MSFT, NVDA)…"
              value={searchTicker}
              onChange={(e) => setSearchTicker(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="flex-1 px-4 py-2.5 rounded-lg bg-input border border-border/40 text-foreground placeholder-muted-foreground/40 text-sm transition-smooth focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
            />
            <button
              onClick={handleSearch}
              disabled={isLoading}
              className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-primary to-cyan-500 text-primary-foreground font-semibold text-sm hover:shadow-premium-lg active:opacity-95 transition-smooth duration-200 whitespace-nowrap disabled:opacity-60 flex items-center gap-2"
            >
              {isLoading ? <Loader className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              {isLoading ? 'Generating…' : 'Get Report'}
            </button>
          </div>
        </GlassCard>

        {/* Error */}
        {hasError && (
          <div className="flex items-start gap-4 px-4 py-4 rounded-lg bg-destructive/10 border border-destructive/20 mb-8">
            <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-destructive">Failed to generate report</p>
              <p className="text-xs text-destructive/70 mt-1">Check the ticker and try again</p>
            </div>
          </div>
        )}

        {/* Report card */}
        <GlassCard className="animate-in-up" style={{ animationDelay: '140ms' }}>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-20 rounded-lg bg-surface-secondary/40 animate-pulse" />
              ))}
            </div>
          ) : reportData ? (
            <div className="space-y-10">

              {/* ── Report header ──────────────────────────────────────────── */}
              <div className="border-b border-border/20 pb-8 space-y-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-baseline gap-3 mb-1.5">
                      <h2 className="text-4xl font-bold tracking-tight text-foreground">{reportData.ticker}</h2>
                      <span className="text-base text-muted-foreground/70 font-medium">{reportData.company_name}</span>
                    </div>
                    <p className="text-xs text-muted-foreground/50 font-medium">
                      Research Report &bull; {new Date(reportData.report_date).toLocaleDateString('en-US', { dateStyle: 'long' })}
                    </p>
                  </div>
                  <div className="flex gap-1.5 flex-shrink-0">
                    {[
                      { icon: <RefreshCw className="w-4 h-4" />, label: 'Refresh' },
                      { icon: <Download className="w-4 h-4" />, label: 'Export' },
                      { icon: <Share2 className="w-4 h-4" />, label: 'Share' },
                    ].map(({ icon, label }) => (
                      <button
                        key={label}
                        title={label}
                        className="p-2 rounded-lg hover:bg-surface-secondary/50 text-muted-foreground/60 hover:text-foreground transition-smooth duration-200"
                      >
                        {icon}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Rating strip */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="px-4 py-3.5 rounded-lg bg-surface-secondary/30 border border-border/20">
                    <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-2.5">Recommendation</p>
                    <RecommendationBadge recommendation={reportData.final_rating?.recommendation ?? 'HOLD'} />
                  </div>
                  <div className="px-4 py-3.5 rounded-lg bg-surface-secondary/30 border border-border/20">
                    <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-2.5">Current Price</p>
                    <p className="text-2xl font-bold text-foreground tracking-tight">${reportData.current_price.toFixed(2)}</p>
                  </div>
                  <div className="px-4 py-3.5 rounded-lg bg-surface-secondary/30 border border-border/20">
                    <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-2.5">12-Month Target</p>
                    <div className="flex items-baseline gap-2">
                      <p className="text-2xl font-bold text-foreground tracking-tight">${(reportData.final_rating?.target_price ?? 0).toFixed(2)}</p>
                      <p className={`text-sm font-bold ${upsideColor}`}>
                        {(reportData.final_rating?.price_upside ?? 0) >= 0 ? '+' : ''}{(reportData.final_rating?.price_upside ?? 0).toFixed(1)}%
                      </p>
                    </div>
                  </div>
                  <div className="px-4 py-3.5 rounded-lg bg-surface-secondary/30 border border-border/20">
                    <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-2.5">AI Confidence</p>
                    <div className="flex items-center gap-2">
                      <p className="text-2xl font-bold text-primary tracking-tight">{reportData.confidence_score.toFixed(0)}%</p>
                      <Star className="w-4.5 h-4.5 fill-primary text-primary" />
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Investment thesis ──────────────────────────────────────── */}
              <div className="space-y-5">
                <div className="px-4 py-4 rounded-lg bg-primary/6 border-l-4 border-primary">
                  <p className="text-[10px] font-bold text-primary/80 uppercase tracking-widest mb-2">Investment Highlight</p>
                  <p className="text-base text-foreground/90 leading-relaxed">{reportData.investment_highlight}</p>
                </div>
                <div>
                  <h3 className="text-base font-bold text-foreground tracking-tight mb-3">Executive Summary</h3>
                  <p className="text-sm text-foreground/85 leading-relaxed">{reportData.executive_summary}</p>
                </div>
              </div>

              {/* ── Technical view ─────────────────────────────────────────── */}
              <div className="space-y-4 border-t border-border/10 pt-8">
                <SectionHeader
                  icon={<Activity className="w-4.5 h-4.5" />}
                  title="Technical Analysis"
                />
                <p className="text-sm text-foreground/80 leading-relaxed">{reportData.technical_view.summary}</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <Stat label="Trend" value={reportData.technical_view.trend} />
                  <Stat label="Momentum" value={reportData.technical_view.momentum} />
                  <Stat
                    label="Signal Strength"
                    value={`${reportData.technical_view.signal_strength.toFixed(0)}/100`}
                    color={reportData.technical_view.signal_strength >= 65 ? 'text-success' : reportData.technical_view.signal_strength >= 40 ? 'text-amber-400' : 'text-destructive'}
                  />
                  <Stat label="MA Alignment" value={reportData.technical_view.ma_alignment} />
                </div>
                {reportData.technical_view.key_levels.length > 0 && (
                  <div className="px-4 py-3 rounded-lg bg-surface-secondary/20 border border-border/10">
                    <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-1.5">Key Price Levels</p>
                    <p className="text-sm font-semibold text-foreground/80">
                      {reportData.technical_view.key_levels.map((l) => `$${l.toFixed(2)}`).join(' · ')}
                    </p>
                  </div>
                )}
              </div>

              {/* ── Fundamentals ───────────────────────────────────────────── */}
              <div className="border-t border-border/10 pt-8">
                <FundamentalsSection snap={reportData.fundamental_snapshot} />
              </div>

              {/* ── Macro & rate environment ───────────────────────────────── */}
              <div className="border-t border-border/10 pt-8">
                <MacroSection macro={reportData.macro_context} />
              </div>

              {/* ── Investment cases ───────────────────────────────────────── */}
              <div className="border-t border-border/10 pt-8 space-y-4">
                <SectionHeader
                  icon={<TrendingUp className="w-4.5 h-4.5" />}
                  title="Investment Cases"
                />
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {/* Bull */}
                  <div className="p-5 rounded-lg bg-success/5 border border-success/15 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-success" />
                        <h4 className="text-sm font-bold text-foreground">Bull Case</h4>
                      </div>
                      <span className="text-xs font-bold text-success">{reportData.bull_case.probability.toFixed(0)}%</span>
                    </div>
                    <p className="text-sm text-foreground/85 leading-relaxed">{reportData.bull_case.thesis}</p>
                    {reportData.bull_case.key_catalysts.length > 0 && (
                      <ul className="space-y-1.5 border-t border-border/10 pt-3">
                        {reportData.bull_case.key_catalysts.map((c, i) => (
                          <li key={i} className="text-xs text-foreground/75 flex items-start gap-2">
                            <span className="text-success/60 flex-shrink-0 mt-0.5">+</span>{c}
                          </li>
                        ))}
                      </ul>
                    )}
                    <p className="text-[11px] text-muted-foreground/50">{reportData.bull_case.timeline}</p>
                  </div>

                  {/* Bear */}
                  <div className="p-5 rounded-lg bg-destructive/5 border border-destructive/15 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <TrendingDown className="w-4 h-4 text-destructive" />
                        <h4 className="text-sm font-bold text-foreground">Bear Case</h4>
                      </div>
                      <span className="text-xs font-bold text-destructive">{reportData.bear_case.probability.toFixed(0)}%</span>
                    </div>
                    <p className="text-sm text-foreground/85 leading-relaxed">{reportData.bear_case.thesis}</p>
                    {reportData.bear_case.key_catalysts.length > 0 && (
                      <ul className="space-y-1.5 border-t border-border/10 pt-3">
                        {reportData.bear_case.key_catalysts.map((c, i) => (
                          <li key={i} className="text-xs text-foreground/75 flex items-start gap-2">
                            <span className="text-destructive/60 flex-shrink-0 mt-0.5">−</span>{c}
                          </li>
                        ))}
                      </ul>
                    )}
                    <p className="text-[11px] text-muted-foreground/50">{reportData.bear_case.timeline}</p>
                  </div>
                </div>
              </div>

              {/* ── Final rating ───────────────────────────────────────────── */}
              <div className="border-t border-border/10 pt-8">
                <div className="p-5 rounded-lg bg-primary/6 border border-primary/15 space-y-5">
                  <div className="flex items-center gap-2 mb-1">
                    <Target className="w-4.5 h-4.5 text-primary" />
                    <h3 className="text-base font-bold text-foreground tracking-tight">Final Rating &amp; Price Target</h3>
                  </div>
                  <p className="text-sm text-foreground/80 leading-relaxed">{reportData.final_rating?.rationale ?? ''}</p>
                  <div className="grid grid-cols-3 gap-4 pt-2 border-t border-border/10">
                    <div>
                      <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-2">Conviction</p>
                      <p className="text-xl font-bold text-foreground">{reportData.final_rating?.conviction ?? '—'}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-2">Target Price</p>
                      <p className="text-xl font-bold text-foreground">${(reportData.final_rating?.target_price ?? 0).toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-2">Upside</p>
                      <p className={`text-xl font-bold ${upsideColor}`}>
                        {(reportData.final_rating?.price_upside ?? 0) >= 0 ? '+' : ''}{(reportData.final_rating?.price_upside ?? 0).toFixed(1)}%
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Risks ─────────────────────────────────────────────────── */}
              {reportData.risks.length > 0 && (
                <div className="border-t border-border/10 pt-8 space-y-4">
                  <SectionHeader
                    icon={<AlertTriangle className="w-4.5 h-4.5 text-amber-400" />}
                    title="Key Risk Factors"
                  />
                  <div className="space-y-2.5">
                    {reportData.risks.map((risk, i) => (
                      <div key={i} className="p-4 rounded-lg bg-surface-secondary/20 border border-border/15">
                        <div className="flex items-start justify-between gap-4 mb-1.5">
                          <p className="text-sm font-semibold text-foreground leading-snug flex-1">{risk.description}</p>
                          <SeverityBadge severity={risk.severity} />
                        </div>
                        {risk.mitigation && (
                          <p className="text-xs text-muted-foreground/60 leading-snug">
                            <span className="font-semibold text-muted-foreground/70">Mitigation: </span>
                            {risk.mitigation}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── Catalysts ─────────────────────────────────────────────── */}
              {reportData.catalysts.length > 0 && (
                <div className="border-t border-border/10 pt-8 space-y-4">
                  <SectionHeader
                    icon={<Spark className="w-4.5 h-4.5 text-primary" />}
                    title="Near-Term Catalysts"
                  />
                  <div className="space-y-2.5">
                    {reportData.catalysts.map((c, i) => (
                      <div key={i} className="p-4 rounded-lg bg-primary/5 border border-primary/15">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="text-sm font-semibold text-foreground">{c.description}</p>
                            {c.mitigation && (
                              <p className="text-xs text-muted-foreground/60 mt-1.5 leading-snug">{c.mitigation}</p>
                            )}
                          </div>
                          <SeverityBadge severity={c.severity} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── Footer ────────────────────────────────────────────────── */}
              <div className="border-t border-border/15 pt-6 flex items-center justify-between gap-4">
                <p className="text-[11px] text-muted-foreground/40 leading-relaxed">
                  Generated by Axiom Terminal AI &bull; For informational purposes only &bull; Not investment advice.
                  Fundamentals sourced from SEC EDGAR; macro data from FRED.
                </p>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="px-2 py-0.5 text-[9px] font-bold text-muted-foreground/40 border border-border/20 rounded uppercase tracking-wider">SEC EDGAR</span>
                  <span className="px-2 py-0.5 text-[9px] font-bold text-muted-foreground/40 border border-border/20 rounded uppercase tracking-wider">FRED</span>
                  <span className="px-2 py-0.5 text-[9px] font-bold text-muted-foreground/40 border border-border/20 rounded uppercase tracking-wider">AI</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-16">
              <Building2 className="w-10 h-10 text-muted-foreground/20 mx-auto mb-4" />
              <p className="text-sm text-muted-foreground/60 font-medium">Enter a ticker to generate an institutional report</p>
              <p className="text-xs text-muted-foreground/40 mt-1">Powered by SEC EDGAR, FRED, and AI synthesis</p>
            </div>
          )}
        </GlassCard>
      </div>
    </DashboardLayoutWrapper>
  );
}
