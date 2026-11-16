import { Suspense } from "react";
import { ObservationProgress } from "@/components/observation-progress";

export default function ObservationPage() {
  return (
    <Suspense fallback={<p className="pt-6">…</p>}>
      <ObservationProgress />
    </Suspense>
  );
}
