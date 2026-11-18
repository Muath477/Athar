import { buttonVariants } from "@/components/ui/button";
import type { Site } from "@/lib/api";
import { placeUrl } from "@/lib/directions";
import { FootprintSketch } from "./footprint-sketch";
import { VIEWPORT_CLASS } from "./viewport";

export function SiteOutline({ site }: { site: Site }) {
  return (
    <div className={`${VIEWPORT_CLASS} flex flex-col items-center justify-center gap-3 bg-white/60 p-6 text-center`}>
      <FootprintSketch boundary={site.boundary} />
      <p className="max-w-sm">موقع {site.name_ar}. شاهده بالأقمار الصناعية في Google Maps.</p>
      <a href={placeUrl(site.location)} target="_blank" rel="noreferrer" className={buttonVariants({ variant: "outline" })}>
        افتح في Google Maps
      </a>
    </div>
  );
}
