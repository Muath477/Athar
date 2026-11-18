"use client";

import { useEffect, useState } from "react";
import { request, type Story } from "@/lib/api";
import { claimLabelAr } from "@/lib/labels";

export function StoryView({ storyId }: { storyId: string | null }) {
  const [story, setStory] = useState<Story | null>(null);

  useEffect(() => {
    if (!storyId) return;
    request<Story>(`/stories/${storyId}`).then(setStory, () => setStory(null));
  }, [storyId]);

  if (!storyId) {
    return (
      <section className="rounded-xl bg-white/75 p-4">
        <p>ليس لدينا مصدر موثّق عن هذا المعلم بعد، لذلك لن نروي حكاية غير مؤكدة.</p>
      </section>
    );
  }
  if (!story) return <p>نحضّر الحكاية…</p>;

  return (
    <section className="flex flex-col gap-3 rounded-xl bg-white/75 p-4">
      <h2 className="text-xl font-bold">حكاية المكان</h2>
      {story.audio_url && <audio controls src={story.audio_url} className="w-full" />}
      <ol className="flex flex-col gap-3 leading-loose">
        {story.claims.map((claim) => (
          <li key={claim.claim_id}>
            <p>{claim.text}</p>
            <p className="text-xs text-mud">
              <span className="rounded bg-sand px-1.5 py-0.5">{claimLabelAr[claim.label]}</span>
              {claim.source && (
                <>
                  {" · المصدر: "}
                  {claim.source.url ? (
                    <a href={claim.source.url} className="underline" target="_blank" rel="noreferrer">
                      {claim.source.title}
                    </a>
                  ) : (
                    claim.source.title
                  )}
                  {claim.source.narrator_name && ` (رواية ${claim.source.narrator_name})`}
                </>
              )}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
