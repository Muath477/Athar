"use client";

import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, type Role, type Site } from "@/lib/api";
import { MIN_PASSWORD_LENGTH, type ManagedUser, type RoleMatrixRow, createUser, seesEverySite } from "@/lib/governance";
import { RolePicker } from "./role-picker";
import { SiteChecklist } from "./site-checklist";

const ERROR_ID = "new-user-error";

export function NewUserDialog({
  matrix,
  sites,
  onCreated,
}: {
  matrix: RoleMatrixRow[];
  sites: Site[];
  onCreated: (user: ManagedUser) => void;
}) {
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState<Role>("inspector");
  const [siteIds, setSiteIds] = useState<string[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function changeOpen(next: boolean) {
    setOpen(next);
    if (next) setError(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    try {
      const created = await createUser({
        email: String(form.get("email")),
        display_name: String(form.get("display_name")),
        role,
        password: String(form.get("password")),
        site_ids: seesEverySite(role) ? [] : siteIds,
      });
      setRole("inspector");
      setSiteIds([]);
      setOpen(false);
      onCreated(created);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر إنشاء الحساب. أعد المحاولة.");
    } finally {
      setPending(false);
    }
  }

  const invalid = error !== null;

  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogTrigger asChild>
        <Button type="button">أضف حسابًا</Button>
      </DialogTrigger>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto">
        <form onSubmit={submit} className="flex flex-col gap-4">
          <DialogHeader className="pe-10">
            <DialogTitle>حساب جديد</DialogTitle>
            <DialogDescription className="text-sm">يُسجَّل إنشاء الحساب في سجل التدقيق باسمك.</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="new-user-email">البريد الإلكتروني</Label>
            <Input
              id="new-user-email"
              name="email"
              type="email"
              required
              dir="ltr"
              autoComplete="off"
              aria-invalid={invalid || undefined}
              aria-describedby={invalid ? ERROR_ID : undefined}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="new-user-name">الاسم الظاهر</Label>
            <Input id="new-user-name" name="display_name" maxLength={120} autoComplete="off" />
          </div>
          <RolePicker matrix={matrix} value={role} onChange={setRole} />
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="new-user-password">كلمة مرور مؤقتة</Label>
            <Input
              id="new-user-password"
              name="password"
              type="password"
              required
              minLength={MIN_PASSWORD_LENGTH}
              dir="ltr"
              autoComplete="new-password"
              aria-describedby="new-user-password-hint"
            />
            <p id="new-user-password-hint" className="text-xs leading-relaxed text-mud">
              {MIN_PASSWORD_LENGTH.toLocaleString("ar-SA")} حرفًا على الأقل. سلّمها لصاحب الحساب، وسيُطلب منه تغييرها
              عند أول دخول.
            </p>
          </div>
          {!seesEverySite(role) && <SiteChecklist sites={sites} selected={siteIds} onChange={setSiteIds} />}
          {error && (
            <p id={ERROR_ID} role="alert" className="text-urgent">
              {error}
            </p>
          )}
          <DialogFooter>
            <Button disabled={pending}>{pending ? "ننشئ الحساب…" : "أنشئ الحساب"}</Button>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                ألغِ
              </Button>
            </DialogClose>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
