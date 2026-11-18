"use client";

import { useEffect, useRef, useState } from "react";
import { Button, buttonVariants } from "@/components/ui/button";

const JPEG_QUALITY = 0.9;

type Props = {
  overlayUrl: string | null;
  onPhoto: (photo: Blob) => void;
};

export function Camera({ overlayUrl, onPhoto }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [live, setLive] = useState<"starting" | "on" | "unavailable">("starting");

  useEffect(() => {
    let stream: MediaStream | null = null;
    let cancelled = false;
    const media = navigator.mediaDevices
      ? navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment", width: { ideal: 1920 } }, audio: false })
      : Promise.reject(new Error("camera_unavailable"));
    media
      .then((s) => {
        if (cancelled) {
          s.getTracks().forEach((t) => t.stop());
          return;
        }
        stream = s;
        if (videoRef.current) videoRef.current.srcObject = s;
        setLive("on");
      })
      .catch(() => setLive("unavailable"));
    return () => {
      cancelled = true;
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  function shoot() {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    canvas.toBlob((blob) => blob && onPhoto(blob), "image/jpeg", JPEG_QUALITY);
  }

  return (
    <div className="flex flex-col gap-3">
      {live !== "unavailable" && (
        <div className="relative overflow-hidden rounded-xl bg-ink">
          <video ref={videoRef} autoPlay playsInline muted className="block w-full" />
          {overlayUrl && (
            <img src={overlayUrl} alt="" className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-35" />
          )}
        </div>
      )}
      {live === "on" && (
        <Button type="button" size="lg" onClick={shoot} className="self-center px-10">
          التقط الصورة
        </Button>
      )}
      {live === "unavailable" && (
        <p className="rounded-sm border border-line bg-white p-4 text-sm leading-relaxed">
          لم نتمكن من فتح الكاميرا. اسمح بالوصول إليها من إعدادات المتصفح، أو التقط صورة بكاميرا الجوال.
        </p>
      )}
      <label
        className={buttonVariants({
          variant: live === "unavailable" ? "default" : "outline",
          size: live === "unavailable" ? "lg" : "default",
          className:
            "self-center has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px] has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-sadu",
        })}
      >
        {live === "on" ? "أو اختر صورة من الجوال" : "افتح الكاميرا"}
        <input
          type="file"
          accept="image/jpeg,image/png"
          capture="environment"
          className="sr-only"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onPhoto(file);
          }}
        />
      </label>
    </div>
  );
}
