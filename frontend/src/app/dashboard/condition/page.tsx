import { Suspense } from "react";
import { ConditionSkeleton, SiteConditionView } from "./_components/site-condition";

export default function ConditionPage() {
  return (
    <Suspense fallback={<ConditionSkeleton />}>
      <SiteConditionView />
    </Suspense>
  );
}
