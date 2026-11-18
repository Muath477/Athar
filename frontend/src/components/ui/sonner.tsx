"use client";

import { CircleCheckIcon, InfoIcon, LoaderIcon, OctagonXIcon, TriangleAlertIcon } from "lucide-react";
import type * as React from "react";
import { Toaster as Sonner, type ToasterProps } from "sonner";

function Toaster(props: ToasterProps) {
  return (
    <Sonner
      theme="light"
      dir="rtl"
      position="bottom-left"
      containerAriaLabel="الإشعارات"
      className="toaster group"
      icons={{
        success: <CircleCheckIcon className="size-4 text-sadu" />,
        info: <InfoIcon className="size-4" />,
        warning: <TriangleAlertIcon className="size-4 text-moderate" />,
        error: <OctagonXIcon className="size-4 text-urgent" />,
        loading: <LoaderIcon className="size-4 animate-spin motion-reduce:animate-none" />,
      }}
      toastOptions={{ classNames: { toast: "font-sans", description: "text-mud" } }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        } as React.CSSProperties
      }
      {...props}
    />
  );
}

export { Toaster };
