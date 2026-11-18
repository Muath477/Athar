import { Suspense } from "react";
import { SiteWatchSkeleton } from "../_components/watch-states";
import { SiteWatch } from "./_components/site-watch";

export default function SiteWatchPage() {
  return (
    <Suspense fallback={<SiteWatchSkeleton />}>
      <SiteWatch />
    </Suspense>
  );
}
