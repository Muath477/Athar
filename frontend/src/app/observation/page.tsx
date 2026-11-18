import { Suspense } from "react";
import { PageSkeleton } from "@/app/_components/page-status";
import { ObservationProgress } from "./_components/observation-progress";

export default function ObservationPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <ObservationProgress />
    </Suspense>
  );
}
