import { type VariantProps, cva } from "class-variance-authority";
import { Slot } from "radix-ui";
import type * as React from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex min-h-11 shrink-0 cursor-pointer items-center justify-center gap-2 rounded-sm text-sm font-bold whitespace-nowrap transition-colors duration-150 ease-quill disabled:cursor-not-allowed disabled:opacity-45 aria-invalid:border-destructive [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-ink active:bg-ink/90",
        outline: "border border-ink bg-transparent text-ink hover:bg-ink hover:text-sand",
        secondary: "border border-mud/50 bg-white text-ink hover:border-ink hover:bg-accent",
        ghost: "font-normal text-ink hover:bg-accent",
        segment:
          "font-normal text-ink hover:bg-accent aria-pressed:bg-ink aria-pressed:font-bold aria-pressed:text-sand aria-checked:bg-ink aria-checked:font-bold aria-checked:text-sand",
        destructive: "bg-destructive text-on-accent hover:bg-ink",
        "destructive-outline": "border border-urgent bg-transparent text-urgent hover:bg-urgent hover:text-on-accent",
        link: "min-h-0 font-bold text-primary underline underline-offset-4 hover:text-ink",
      },
      size: {
        default: "px-5",
        sm: "px-3",
        lg: "px-7 text-base",
        icon: "size-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "button";
  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
