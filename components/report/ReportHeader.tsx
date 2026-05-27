"use client";

import { motion } from "framer-motion";
import { FileText, Calendar, User, Building2 } from "lucide-react";
import RatingBadge from "./RatingBadge";
import ConfidenceMeter from "./ConfidenceMeter";

interface Props {
  ticker: string;
  name: string;
  rating: string;
  confidence: number;
  generatedAt: string;
  sector?: string;
  analystName?: string;
}

export default function ReportHeader({ ticker, name, rating, confidence, generatedAt, sector, analystName }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6"
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <FileText className="h-5 w-5 text-accent" />
            <h1 className="text-2xl font-bold">{ticker} Equity Research</h1>
          </div>
          <p className="text-sm text-text-secondary">{name}</p>
          <div className="flex items-center gap-4 mt-2 text-xs text-text-muted">
            {sector && (
              <span className="flex items-center gap-1">
                <Building2 className="h-3 w-3" />
                {sector}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {new Date(generatedAt).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
            </span>
            {analystName && (
              <span className="flex items-center gap-1">
                <User className="h-3 w-3" />
                {analystName}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-3">
          <RatingBadge rating={rating} />
          <ConfidenceMeter value={confidence} />
        </div>
      </div>
    </motion.div>
  );
}
