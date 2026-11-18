import { Suspense } from "react";
import { AssistantSkeleton, AssistantView } from "./_components/assistant-view";

export default function AssistantPage() {
  return (
    <Suspense fallback={<AssistantSkeleton />}>
      <AssistantView />
    </Suspense>
  );
}
