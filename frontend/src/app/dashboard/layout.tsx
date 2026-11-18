import { Suspense } from "react";
import { DashboardNav } from "./_components/dashboard-nav";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-4">
      <Suspense fallback={<div className="h-11 border-b border-clay/40" />}>
        <DashboardNav />
      </Suspense>
      {children}
    </div>
  );
}
