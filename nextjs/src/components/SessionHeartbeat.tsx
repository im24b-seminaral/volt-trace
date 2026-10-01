"use client";

import { useEffect } from "react";

export default function SessionHeartbeat() {
  useEffect(() => {
    const heartbeat = () => {
      void fetch("/api/session/heartbeat", { method: "POST", cache: "no-store" }).catch(() => {});
    };
    heartbeat();
    const timer = setInterval(heartbeat, 30_000);
    return () => {
      clearInterval(timer);
    };
  }, []);
  return null;
}
