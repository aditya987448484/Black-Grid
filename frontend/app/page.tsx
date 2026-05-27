'use client';

import Link from 'next/link';
import { ArrowRight, TrendingUp, Zap, BarChart3, Sparkles } from 'lucide-react';
import { GlassCard } from '@/components/common/Card';

export default function Page() {
  return (
    <main className="min-h-screen bg-background overflow-hidden">
      {/* Animated gradient background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-primary/20 to-cyan-500/10 rounded-full blur-3xl opacity-30 animate-pulse" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-tr from-primary/20 to-blue-500/10 rounded-full blur-3xl opacity-30 animate-pulse" style={{ animationDelay: '1s' }} />
      </div>

      <div className="relative z-10">
        {/* Navigation */}
        <nav className="fixed top-0 left-0 right-0 glass backdrop-blur-2xl border-b border-border z-50">
          <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/40 to-cyan-500/30 flex items-center justify-center">
                <TrendingUp className="w-4 h-4 text-primary" />
              </div>
              <span className="text-lg font-bold">AXIOM Terminal</span>
            </div>
            <Link
              href="/dashboard"
              className="px-6 py-2 rounded-lg bg-gradient-to-r from-primary to-cyan-500 text-primary-foreground font-semibold hover:shadow-lg hover:shadow-primary/30 transition-smooth"
            >
              Launch App
            </Link>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="pt-32 pb-20 px-6 sm:px-8">
          <div className="max-w-4xl mx-auto text-center space-y-8 animate-in">
            <h1 className="text-5xl sm:text-6xl font-bold text-foreground leading-tight">
              AI-Powered Financial Intelligence
            </h1>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
              Professional-grade research tools, AI analyst reports, strategy backtesting, and real-time market monitoring in one powerful platform.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
              <Link
                href="/dashboard"
                className="flex items-center gap-2 px-8 py-3 rounded-lg bg-gradient-to-r from-primary to-cyan-500 text-primary-foreground font-semibold hover:shadow-lg hover:shadow-primary/30 transition-smooth group"
              >
                Get Started
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <button className="px-8 py-3 rounded-lg border border-border text-foreground font-semibold hover:bg-surface-secondary transition-smooth">
                View Demo
              </button>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="py-20 px-6 sm:px-8">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-3xl font-bold text-center mb-16">Institutional-Grade Tools</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-in-up">
              {[
                {
                  icon: BarChart3,
                  title: 'Real-Time Dashboard',
                  description: 'Live market data, portfolio metrics, and customizable widgets',
                },
                {
                  icon: Sparkles,
                  title: 'AI Analyst Reports',
                  description: 'Automated sentiment analysis and price target recommendations',
                },
                {
                  icon: Zap,
                  title: 'Backtest Lab',
                  description: 'Test strategies with historical data and performance metrics',
                },
                {
                  icon: TrendingUp,
                  title: 'Asset Analysis',
                  description: 'Technical indicators, forecasts, and comprehensive fundamentals',
                },
              ].map((feature, i) => {
                const Icon = feature.icon;
                return (
                  <GlassCard
                    key={i}
                    className="relative group overflow-hidden"
                    style={{ animationDelay: `${i * 100}ms` }}
                  >
                    <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative space-y-3">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary/30 to-cyan-500/20 flex items-center justify-center">
                        <Icon className="w-5 h-5 text-primary" />
                      </div>
                      <h3 className="font-semibold text-foreground">{feature.title}</h3>
                      <p className="text-sm text-muted-foreground">{feature.description}</p>
                    </div>
                  </GlassCard>
                );
              })}
            </div>
          </div>
        </section>

        {/* Stats */}
        <section className="py-20 px-6 sm:px-8 border-y border-border">
          <div className="max-w-6xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
              {[
                { label: 'AI-generated analyst reports with real SEC & FRED data', value: 'Live Reports' },
                { label: 'Strategy backtesting with configurable parameters', value: 'Backtest Lab' },
                { label: 'Macro & fundamental context in every analysis', value: 'Deep Research' },
              ].map((stat, i) => (
                <div key={i} className="space-y-2">
                  <p className="text-2xl font-bold text-primary">{stat.value}</p>
                  <p className="text-muted-foreground text-sm">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 px-6 sm:px-8 animate-in-up">
          <div className="max-w-2xl mx-auto text-center space-y-8">
            <div className="space-y-4">
              <h2 className="text-3xl font-bold">Ready to transform your trading?</h2>
              <p className="text-muted-foreground text-lg">
                Access professional financial research tools and AI-powered insights.
              </p>
            </div>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-lg bg-gradient-to-r from-primary to-cyan-500 text-primary-foreground font-semibold hover:shadow-lg hover:shadow-primary/30 transition-smooth group text-lg"
            >
              Launch Axiom Terminal
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-border py-8 px-6 text-center text-sm text-muted-foreground">
          <p>© 2026 Axiom Terminal. Powered by AI and data science.</p>
        </footer>
      </div>
    </main>
  );
}
