"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/demo", label: "Demo" },
  { href: "/manual", label: "Manual" },
];

export function AppNavigation() {
  const pathname = usePathname();

  return (
    <nav aria-label="Sentinel workspaces" className="workspace-nav">
      {items.map((item) => (
        <Link
          aria-current={pathname === item.href ? "page" : undefined}
          className={pathname === item.href ? "active" : undefined}
          href={item.href}
          key={item.href}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
