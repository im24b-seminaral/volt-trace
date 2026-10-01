import Image from "next/image";
import Link from "next/link";

export default function Header() {
  return <header className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur">
    <div className="mx-auto flex max-w-5xl items-center gap-2.5 p-4 sm:px-8">
      <Link href="/" className="flex items-center gap-2.5 rounded-md outline-ring/50 focus-visible:outline-2">
        <Image src="/android-chrome-192x192.png" alt="" width={28} height={28} priority className="size-7 dark:invert" />
        <span className="text-lg font-semibold tracking-tight">VoltTrace</span>
      </Link>
    </div>
  </header>;
}
