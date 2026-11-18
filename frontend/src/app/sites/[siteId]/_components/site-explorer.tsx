"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { request, type Site } from "@/lib/api";
import type { TravelMode } from "@/lib/directions";
import { DirectionsPanel } from "./directions-panel";
import { Place3D } from "./place-3d";
import { type View, ViewSwitch } from "./view-switch";
import { VIEWPORT_CLASS } from "./viewport";

const SiteModel = dynamic(() => import("@/components/site-model").then((m) => m.SiteModel), {
  ssr: false,
  loading: () => <div className="size-full animate-pulse rounded-xl bg-clay/20" />,
});

type Props = { siteId: string; mapsApiKey: string | null };

export function SiteExplorer({ siteId, mapsApiKey }: Props) {
  const [site, setSite] = useState<Site | null>(null);
  const [failed, setFailed] = useState(false);
  const [view, setView] = useState<View>(mapsApiKey ? "place" : "model");
  const [mode, setMode] = useState<TravelMode>("walking");

  useEffect(() => {
    request<Site>(`/sites/${siteId}`).then(setSite, () => setFailed(true));
  }, [siteId]);

  if (failed) return <p className="pt-6">لم نجد هذا المكان. تأكد من الرابط أو ارجع إلى جوازك.</p>;
  if (!site) return <ExplorerSkeleton />;

  return (
    <div className="flex flex-col gap-5 pt-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold leading-snug">{site.name_ar}</h1>
        <p lang="en" dir="ltr" className="self-start text-sm text-mud">
          {site.name_en}
        </p>
      </header>

      {mapsApiKey && <ViewSwitch value={view} onChange={setView} />}

      {mapsApiKey && (
        <div id="view-place" role="tabpanel" aria-labelledby="tab-place" hidden={view !== "place"}>
          <Place3D site={site} apiKey={mapsApiKey} mode={mode} />
        </div>
      )}
      <div id="view-model" role="tabpanel" aria-labelledby="tab-model" hidden={view !== "model"} className={VIEWPORT_CLASS}>
        {view === "model" && <SiteModel facades={site.facades} />}
      </div>

      <DirectionsPanel site={site} mode={mode} onModeChange={setMode} />
    </div>
  );
}

function ExplorerSkeleton() {
  return (
    <div className="flex flex-col gap-5 pt-4" aria-busy>
      <div className="h-9 w-2/3 animate-pulse rounded bg-clay/20" />
      <div className={`${VIEWPORT_CLASS} animate-pulse bg-clay/20`} />
      <div className="h-40 animate-pulse rounded-xl bg-clay/20" />
    </div>
  );
}
