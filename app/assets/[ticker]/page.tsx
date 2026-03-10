"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { getAssetDetail, getTechnicals, getForecast } from "@/lib/api";
import type { AssetDetail } from "@/types/asset";
import type { AssetTechnicalResponse, AssetForecastResponse } from "@/types/asset";
import AssetHeader from "@/components/asset/AssetHeader";
import ChartPanel from "@/components/asset/ChartPanel";
import IndicatorCard from "@/components/asset/IndicatorCard";
import ModelCard from "@/components/asset/ModelCard";
import FactorsPanel from "@/components/asset/FactorsPanel";
import RiskPanel from "@/components/asset/RiskPanel";
import SummaryPanel from "@/components/asset/SummaryPanel";

export default function AssetDetailPage() {
  const { ticker } = useParams<{ ticker: string }>();
  const [asset, setAsset] = useState<AssetDetail | null>(null);
  const [technicals, setTechnicals] = useState<AssetTechnicalResponse | null>(null);
  const [forecast, setForecast] = useState<AssetForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ticker) return;
    const t = ticker.toUpperCase();
    setLoading(true);

    Promise.all([
      getAssetDetail(t).catch(() => null),
      getTechnicals(t).catch(() => null),
      getForecast(t).catch(() => null),
    ]).then(([a, tech, fc]) => {
      setAsset(a);
      setTechnicals(tech);
      setForecast(fc);
      setLoading(false);
    });
  }, [ticker]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="skeleton h-20 rounded-2xl" />
        <div className="skeleton h-80 rounded-2xl" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-32 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!asset) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-text-secondary">Unable to load data for {ticker?.toUpperCase()}.</p>
        <p className="text-xs text-text-muted mt-2">Ensure the backend is running.</p>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
      <AssetHeader asset={asset} />
      <ChartPanel data={asset.priceHistory} />

      {technicals && (
        <>
          <h3 className="text-sm font-semibold text-text-secondary">Technical Indicators</h3>
          <div className="grid grid-cols-4 gap-4">
            {technicals.indicators.map((ind) => (
              <IndicatorCard key={ind.name} indicator={ind} />
            ))}
          </div>
        </>
      )}

      {forecast && (
        <>
          <h3 className="text-sm font-semibold text-text-secondary">Forecast Models</h3>
          <div className="grid grid-cols-2 gap-4">
            {forecast.models.map((m) => (
              <ModelCard key={m.modelName} model={m} />
            ))}
          </div>

          <FactorsPanel bullish={forecast.bullishFactors} bearish={forecast.bearishFactors} />

          <RiskPanel
            riskLevel={forecast.riskLevel}
            confidence={forecast.models[0]?.confidence ?? 0}
            aiSummary={forecast.aiSummary}
          />

          <SummaryPanel ticker={asset.ticker} summary={forecast.aiSummary} />
        </>
      )}
    </motion.div>
  );
}
