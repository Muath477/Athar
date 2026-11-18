import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { NearbyMissions } from "./_components/nearby-missions";

export default function Home() {
  return (
    <div className="flex flex-col gap-8 pt-6">
      <section className="flex flex-col gap-4">
        <h1 className="text-3xl font-bold leading-snug">صوّر الواجهة، واسمع حكايتها</h1>
        <p className="text-lg leading-relaxed">
          كل صورة تلتقطها تترك أثرًا يساعد في حماية مبانينا الطينية. صوّر واجهة المبنى التراثي أمامك،
          وسنقارنها بصورته المرجعية لنرصد أي ضرر جديد، ونروي لك حكايته من مصادر موثقة.
        </p>
        <Link href="/capture" className={buttonVariants({ size: "lg", className: "self-start" })}>
          ابدأ التصوير
        </Link>
      </section>

      <NearbyMissions />

      <section className="rounded-sm border border-line bg-white p-4 text-sm leading-relaxed">
        <h2 className="mb-2 font-bold">خصوصيتك</h2>
        <p>
          نطمس الوجوه ونحذف بيانات الصورة قبل حفظها. لا نستخدم موقعك أو اتجاه جوالك إلا بموافقتك، ونحذف الموقع بمجرد
          معرفة المبنى. تُحذف صورك بعد ٣٠ يومًا ما لم تكن دليلًا على ضرر، ويمكنك حذف جوازك وكل صوره في أي وقت.
        </p>
      </section>
    </div>
  );
}
