import { cn } from "@/lib/utils";

const ratingColors: Record<string, string> = {
  "Strong Buy": "bg-success/20 text-success border-success/30",
  Buy: "bg-success/10 text-success border-success/20",
  Hold: "bg-warning/10 text-warning border-warning/20",
  Sell: "bg-danger/10 text-danger border-danger/20",
  "Strong Sell": "bg-danger/20 text-danger border-danger/30",
};

export default function RatingBadge({ rating }: { rating: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-lg border px-4 py-1.5 text-sm font-bold",
        ratingColors[rating] || "bg-accent/10 text-accent border-accent/20"
      )}
    >
      {rating}
    </span>
  );
}
