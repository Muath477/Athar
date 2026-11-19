import Link from "next/link";
import { BookOpenTextIcon, CameraIcon, LibraryBigIcon, PenLineIcon, ScanSearchIcon, ShieldCheckIcon } from "lucide-react";
import { MarginNote } from "@/components/brand/margin-note";
import { buttonVariants } from "@/components/ui/button";
import { NearbyMissions } from "./_components/nearby-missions";

const STEPS = [
  {
    icon: CameraIcon,
    title: "صوّر الواجهة",
    body: "قف أمام أي واجهة تراثية وصوّرها من زاوية واضحة. نطمس أي وجه يظهر معك تلقائيًا قبل الحفظ.",
  },
  {
    icon: ScanSearchIcon,
    title: "نقارنها بالمرجع",
    body: "نقارن صورتك بآخر صورة مرجعية لنفس الواجهة، ونرصد أي تشقق أو فقد لياسة أو تآكل جديد.",
  },
  {
    icon: BookOpenTextIcon,
    title: "اسمع حكايتها",
    body: "نروي لك حالة الواجهة من مصادر موثقة ومؤرَّخة، موقّعة باسم من كتبها، لا من تخمين.",
  },
];

const FEATURES = [
  {
    icon: ShieldCheckIcon,
    title: "خصوصيتك محفوظة",
    body: "نطمس الوجوه ونحذف بيانات الصورة قبل حفظها. لا نستخدم موقعك أو اتجاه جوالك إلا بموافقتك، ونحذفه بمجرد معرفة المبنى. صورك تُحذف بعد ٣٠ يومًا ما لم تكن دليلًا على ضرر، ويمكنك حذف جوازك وكل صوره في أي وقت.",
  },
  {
    icon: PenLineIcon,
    title: "كل حكم موقّع ومؤرَّخ",
    body: "ملاحظة المختص أو نتيجة التحليل تُكتب حاشية بجانب الواجهة، لا نافذة منبثقة تختفي، وتبقى معروفة المصدر والتاريخ.",
  },
  {
    icon: LibraryBigIcon,
    title: "مصادر موثقة لا تأليف",
    body: "حكاية كل واجهة مبنية على مصادر تراثية موثقة ومذكورة دائمًا، لا على تاريخ نختلقه.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-col gap-10 pt-6 pb-4">
      <section className="flex flex-col gap-4 border-b border-line pb-8">
        <h1 className="text-3xl leading-snug font-bold text-balance md:text-4xl">صوّر الواجهة، واسمع حكايتها</h1>
        <p className="max-w-prose text-lg leading-relaxed">
          كل صورة تلتقطها تترك أثرًا يساعد في حماية مبانينا الطينية. صوّر واجهة المبنى التراثي أمامك،
          وسنقارنها بصورته المرجعية لنرصد أي ضرر جديد، ونروي لك حكايته من مصادر موثقة.
        </p>
        <div className="flex flex-wrap items-center gap-3 pt-1">
          <Link href="/capture" className={buttonVariants({ size: "lg" })}>
            ابدأ التصوير
          </Link>
          <Link href="/passport" className={buttonVariants({ variant: "outline", size: "lg" })}>
            جوازي وصوري السابقة
          </Link>
        </div>
      </section>

      <section aria-labelledby="how-title" className="flex flex-col gap-5">
        <h2 id="how-title" className="text-xl font-bold">
          كيف تساهم في ثلاث خطوات
        </h2>
        <ol className="grid gap-6 sm:grid-cols-3">
          {STEPS.map((step, index) => (
            <li key={step.title} className="flex flex-col gap-2">
              <div className="flex items-center gap-2 text-sadu">
                <step.icon className="size-5 shrink-0" aria-hidden="true" />
                <span className="text-sm font-bold">{(index + 1).toLocaleString("ar-SA")}</span>
              </div>
              <h3 className="font-bold">{step.title}</h3>
              <p className="text-sm leading-relaxed text-mud">{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <NearbyMissions />

      <section aria-labelledby="features-title" className="flex flex-col gap-5">
        <h2 id="features-title" className="text-xl font-bold">
          لماذا أثر
        </h2>
        <ul className="flex flex-col divide-y divide-line border-t border-line">
          {FEATURES.map((feature) => (
            <li key={feature.title} className="flex items-start gap-3 py-4">
              <feature.icon className="mt-1 size-5 shrink-0 text-sadu" aria-hidden="true" />
              <div className="flex flex-col gap-1">
                <h3 className="font-bold">{feature.title}</h3>
                <p className="text-sm leading-relaxed">{feature.body}</p>
              </div>
            </li>
          ))}
        </ul>
        <MarginNote label="مثال: حاشية مختص">
          هذا شكل الحاشية كما تظهر بجانب الواجهة: موقّعة، مؤرَّخة، ولا تختفي كنافذة منبثقة.
        </MarginNote>
      </section>
    </div>
  );
}
