import { Suspense } from "react";
import { PageSkeleton } from "@/app/_components/page-status";
import { MapEditor } from "./_components/map-editor";

export default function MapPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <MapEditor />
    </Suspense>
  );
}
