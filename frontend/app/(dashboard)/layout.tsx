import type { Metadata } from "next";
import { DashboardLayoutWrapper } from "@/components/common/DashboardLayout";

export const metadata: Metadata = {
  title: "Dashboard | Axiom Terminal",
  description: "Market overview and portfolio dashboard",
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <DashboardLayoutWrapper>{children}</DashboardLayoutWrapper>;
}
