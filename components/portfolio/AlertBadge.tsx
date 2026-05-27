import { cn } from "@/lib/utils";
import { AlertTriangle, TrendingUp, TrendingDown, Info } from "lucide-react";

const alertConfig: Record<string, { icon: React.ElementType; className: string }> = {
  breakout: { icon: TrendingUp, className: "bg-success/10 text-success" },
  breakdown: { icon: TrendingDown, className: "bg-danger/10 text-danger" },
  warning: { icon: AlertTriangle, className: "bg-warning/10 text-warning" },
  info: { icon: Info, className: "bg-accent/10 text-accent" },
};

export default function AlertBadge({ alert }: { alert: string }) {
  const config = alertConfig[alert.toLowerCase()] || alertConfig.info;
  const Icon = config.icon;

  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium", config.className)}>
      <Icon className="h-3 w-3" />
      {alert}
    </span>
  );
}
