import { connection } from "next/server";
import { Suspense } from "react";
import { PageSkeleton } from "@/app/_components/page-status";
import { SiteExplorer } from "./_components/site-explorer";

type Params = Promise<{ siteId: string }>;

export default function SitePage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <SiteExplorerWithMapsKey params={params} />
    </Suspense>
  );
}

async function SiteExplorerWithMapsKey({ params }: { params: Params }) {
  await connection();
  const { siteId } = await params;
  return <SiteExplorer siteId={siteId} mapsApiKey={process.env.GOOGLE_MAPS_API_KEY || null} />;
}
