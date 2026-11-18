import { Suspense } from "react";
import { CaptureFlow } from "./_components/capture-flow";

export default function CapturePage() {
  return (
    <Suspense fallback={<p className="pt-6">جارٍ تجهيز الكاميرا…</p>}>
      <CaptureFlow />
    </Suspense>
  );
}
