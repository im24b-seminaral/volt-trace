"use client";

import { useTransition, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function ChartForm({ children, chart }: { children: ReactNode; chart: ReactNode }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return <>
    <form action="/" onSubmit={(event) => {
      event.preventDefault();
      const query = new URLSearchParams();
      new FormData(event.currentTarget).forEach((value, key) => query.set(key, String(value)));
      startTransition(() => router.push(`/?${query}`, { scroll: false }));
    }}>
      <fieldset disabled={pending} className="space-y-3">{children}</fieldset>
    </form>
    <Card><CardContent className="pt-6" aria-busy={pending}>
      {pending ? <div role="status" aria-label="Diagramm wird geladen" className="space-y-2">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-80 w-full" />
      </div> : chart}
    </CardContent></Card>
  </>;
}
