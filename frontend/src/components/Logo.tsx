import { useId } from "react";

/** The «محور» logo mark, taken from the student's GUI design (inline SVG). */
export default function Logo({ size = 40, className }: { size?: number; className?: string }) {
  // Unique gradient ids so several logos can appear on one page.
  const id = useId().replace(/:/g, "");
  return (
    <svg
      viewBox="0 0 120 110"
      width={size}
      height={(size * 110) / 120}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="شعار محور"
    >
      <defs>
        <linearGradient id={`${id}-main`} x1="10" y1="20" x2="105" y2="85" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#1E90FF" />
          <stop offset="50%" stopColor="#2563EB" />
          <stop offset="100%" stopColor="#7C3AED" />
        </linearGradient>
        <linearGradient id={`${id}-fold`} x1="20" y1="15" x2="90" y2="55" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0284C7" />
          <stop offset="100%" stopColor="#312E81" />
        </linearGradient>
        <linearGradient id={`${id}-swoosh`} x1="5" y1="70" x2="115" y2="15" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#1E90FF" />
          <stop offset="60%" stopColor="#2563EB" />
          <stop offset="100%" stopColor="#7C3AED" />
        </linearGradient>
      </defs>
      <path d="M24 76V26C24 21 30 18 34 21L60 40V58L38 42V76H24Z" fill={`url(#${id}-main)`} />
      <path d="M60 40L86 21C90 18 96 21 96 26V86L82 78V42L60 58V40Z" fill={`url(#${id}-fold)`} />
      <rect x="44" y="64" width="7" height="12" rx="1.5" fill="#0A1931" />
      <rect x="56" y="55" width="7" height="21" rx="1.5" fill="#0A1931" />
      <rect x="68" y="67" width="7" height="9" rx="1.5" fill="#0A1931" />
      <path
        d="M12 62C8 78 32 92 65 80C86 72 100 54 107 30"
        stroke={`url(#${id}-swoosh)`}
        strokeWidth="5.5"
        strokeLinecap="round"
      />
      <path d="M98 31L110 18L114 35L98 31Z" fill="#7C3AED" />
      <circle cx="95" cy="54" r="6.5" fill="#2563EB" stroke="#FFFFFF" strokeWidth="2.5" />
    </svg>
  );
}
