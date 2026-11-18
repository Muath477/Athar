import { Suspense } from "react";
import { SiteConditionView } from "./_components/site-condition";

export default function ConditionPage() {
  return (
    <Suspense fallback={<p className="pt-6">…</p>}>
      <SiteConditionView />
    </Suspense>
  );
}
