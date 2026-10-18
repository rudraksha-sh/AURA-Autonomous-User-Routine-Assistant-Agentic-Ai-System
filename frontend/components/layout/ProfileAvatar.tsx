"use client";

import * as React from "react";
import Image from "next/image";
import { UserRound } from "lucide-react";
import { fetchProfilePhoto } from "@/services/profile";

export function ProfileAvatar() {
  const [src, setSrc] = React.useState<string | null>(null);
  React.useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    const load = async () => {
      try {
        const next = await fetchProfilePhoto();
        if (active) {
          if (objectUrl) URL.revokeObjectURL(objectUrl);
          objectUrl = next;
          setSrc(next);
        } else if (next) URL.revokeObjectURL(next);
      } catch { if (active) setSrc(null); }
    };
    const update = () => { void load(); };
    void load();
    window.addEventListener("aura:profile-updated", update);
    return () => {
      active = false;
      window.removeEventListener("aura:profile-updated", update);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, []);
  return <span aria-hidden="true" className="flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-slate-100 text-slate-600">
    {src ? <Image src={src} alt="" width={36} height={36} unoptimized className="size-full object-cover" /> : <UserRound className="size-5" />}
  </span>;
}
