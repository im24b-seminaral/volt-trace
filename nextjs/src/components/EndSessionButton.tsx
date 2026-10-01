"use client";

import { useState } from "react";
import { LogOut } from "lucide-react";
import { clearSession } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export default function EndSessionButton() {
  const [open, setOpen] = useState(false);

  return <>
    <Button type="button" variant="ghost" className="ml-auto text-muted-foreground" onClick={() => setOpen(true)}>
      <LogOut aria-hidden="true" /> Sitzung beenden
    </Button>
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Sitzung beenden?</DialogTitle>
          <DialogDescription>Die hochgeladenen Daten werden gelöscht.</DialogDescription>
        </DialogHeader>
        <form action={clearSession}>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Abbrechen</Button>
            <Button type="submit" variant="destructive">Sitzung beenden</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  </>;
}
