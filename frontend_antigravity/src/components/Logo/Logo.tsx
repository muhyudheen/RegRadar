interface LogoProps {
  /** Applied to the <svg> — existing brand classes set width/height + color. */
  className?: string;
  /** Fallback pixel size when no className sizing is provided. */
  size?: number;
}

/**
 * Lawhook brand mark — a hook "J" curve with a green accent dot.
 *
 * Both the hook stroke and the dot use `currentColor`, so the whole mark
 * inherits the surrounding text color the same way the old lucide icon did
 * (brand classes set `color: var(--text)`).
 */
export default function Logo({ className, size = 24 }: LogoProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="22.5 18.5 26 26"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M29 22 v13 a6.5 6.5 0 0 0 13 0"
        stroke="currentColor"
        strokeWidth="3.75"
        strokeLinecap="round"
      />
      <circle cx="42" cy="27.5" r="2.25" fill="currentColor" />
    </svg>
  );
}
