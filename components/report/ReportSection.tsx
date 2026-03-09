"use client";

import { motion } from "framer-motion";

interface Props {
  title: string;
  content: string;
  index: number;
}

export default function ReportSection({ title, content, index }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="glass-card p-5"
    >
      <h3 className="text-sm font-semibold text-accent mb-3">{title}</h3>
      <div className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">
        {content}
      </div>
    </motion.div>
  );
}
