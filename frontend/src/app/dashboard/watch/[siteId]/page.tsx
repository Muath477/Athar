import { Suspense } from "react";
import { SiteWatch } from "./_components/site-watch";

export default function SiteWatchPage() {
  return (
    <Suspense fallback={<p className="pt-6">…</p>}>
      <SiteWatch />
    </Suspense>
  );
}
