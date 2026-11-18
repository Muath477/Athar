"use client";

import { useEffect, useState } from "react";
import { ApiError, forgetPassportLocally, type Passport, passportToken, request } from "@/lib/api";

export function PassportView() {
  const [passport, setPassport] = useState<Passport | null | "none">(null);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    const load: Promise<Passport | "none"> = passportToken() ? request<Passport>("/passport") : Promise.resolve("none");
    load.then(setPassport, (e) => {
      if (e instanceof ApiError && e.status === 401) forgetPassportLocally();
      setPassport("none");
    });
  }, []);

  async function deleteAll() {
    await request("/passport", { method: "DELETE" });
    forgetPassportLocally();
    setPassport("none");
    setConfirming(false);
  }

  if (passport === null) return <p className="pt-6">…</p>;
  if (passport === "none") {
    return <p className="pt-6">ليس لديك جواز بعد. يُنشأ جوازك تلقائيًا مع أول صورة ترسلها.</p>;
  }

  return (
    <div className="flex flex-col gap-5 pt-4">
      <h1 className="text-2xl font-bold">جواز أثر</h1>
      {passport.stamps.length === 0 ? (
        <p>لا أختام بعد. صوّر واجهة مبنى تراثي لتحصل على أول ختم.</p>
      ) : (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {passport.stamps.map((s) => (
            <li key={s.site_id} className="flex flex-col items-center gap-1 rounded-xl border-2 border-sadu p-4 text-center">
              <span className="font-bold">{s.site_name_ar}</span>
              <time className="text-xs" dateTime={s.stamped_at}>
                {new Date(s.stamped_at).toLocaleDateString("ar-SA")}
              </time>
            </li>
          ))}
        </ul>
      )}
      <section className="mt-6 flex flex-col gap-2 border-t border-clay/40 pt-4 text-sm">
        {confirming ? (
          <>
            <p>سيُحذف جوازك وأختامه وصورك التي لم تصبح دليلًا على ضرر. لا يمكن التراجع.</p>
            <div className="flex gap-3">
              <button onClick={deleteAll} className="rounded-full bg-urgent px-4 py-1.5 text-white">
                احذف نهائيًا
              </button>
              <button onClick={() => setConfirming(false)} className="underline">
                إلغاء
              </button>
            </div>
          </>
        ) : (
          <button onClick={() => setConfirming(true)} className="self-start underline">
            احذف جوازي وصوري
          </button>
        )}
      </section>
    </div>
  );
}
