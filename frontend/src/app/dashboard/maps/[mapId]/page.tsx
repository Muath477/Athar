import { Suspense } from "react";
import { MapEditor } from "./_components/map-editor";

export default function MapPage() {
  return (
    <Suspense fallback={<p className="pt-6">…</p>}>
      <MapEditor />
    </Suspense>
  );
}
