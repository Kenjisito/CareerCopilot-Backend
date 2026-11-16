import type { ReactNode } from "react";
import type { IconName } from "./types";

const iconPaths: Record<IconName, ReactNode> = {
  arrow: (
    <>
      <path d="M5 12h14M14 7l5 5-5 5" />
    </>
  ),
  bell: (
    <>
      <path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  chevron: <path d="m9 18 6-6-6-6" />,
  clipboard: (
    <>
      <rect x="5" y="4" width="14" height="17" rx="2" />
      <path d="M9 4.5V3h6v1.5M9 9h6M9 13h6M9 17h4" />
    </>
  ),
  copy: (
    <>
      <rect x="8" y="8" width="11" height="11" rx="2" />
      <path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" />
    </>
  ),
  document: (
    <>
      <path d="M7 3h7l4 4v14H7z" />
      <path d="M14 3v5h5M10 13h5M10 17h5" />
    </>
  ),
  download: (
    <>
      <path d="M12 3v12m0 0 4-4m-4 4-4-4M5 20h14" />
    </>
  ),
  edit: (
    <>
      <path d="m4 20 4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10z" />
      <path d="m14 7 3 3" />
    </>
  ),
  eye: (
    <>
      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  eyeOff: (
    <>
      <path d="m3 3 18 18" />
      <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
      <path d="M9.9 5.2A10.8 10.8 0 0 1 12 5c6.4 0 10 7 10 7a15.7 15.7 0 0 1-3.1 3.8" />
      <path d="M6.6 6.7C3.8 8.3 2 12 2 12s3.6 7 10 7a10.5 10.5 0 0 0 4.2-.9" />
    </>
  ),
  gmail: (
    <>
      <path d="M4 7v10.5" stroke="#4285f4" strokeWidth="2.4" />
      <path d="m4 7 8 6 8-6" stroke="#ea4335" strokeWidth="2.4" />
      <path d="M20 7v10.5" stroke="#34a853" strokeWidth="2.4" />
      <path d="M6 19h12" stroke="#fbbc04" strokeWidth="2.4" />
    </>
  ),
  history: (
    <>
      <path d="M4 6v5h5" />
      <path d="M5.5 16a8 8 0 1 0 .5-9l-2 4M12 8v5l3 2" />
    </>
  ),
  mail: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m4 7 8 6 8-6" />
    </>
  ),
  map: (
    <>
      <path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3zM9 3v15M15 6v15" />
    </>
  ),
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  message: (
    <path d="M20 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h9a4 4 0 0 1 4 4z" />
  ),
  astronaut: (
    <>
      <path d="M12 3a9 9 0 0 0-9 9v3a3 3 0 0 0 3 3h2v-5a4 4 0 0 1 8 0v5h2a3 3 0 0 0 3-3v-3a9 9 0 0 0-9-9Z" />
      <path d="M8 13h8M8 18v1a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-1" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  play: <path d="m8 5 11 7-11 7z" />,
  rocket: (
    <>
      <path d="M14 5c3-3 6-2 6-2s1 3-2 6l-5 5-4-4z" />
      <path d="m9 10-4 1-2 3 6 1M13 14l-1 4-3 3-1-6M6 18l-3 3" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-4-4" />
    </>
  ),
  send: (
    <>
      <path d="m3 11 18-8-8 18-2-8z" />
      <path d="m11 13 4-4" />
    </>
  ),
  spark: (
    <>
      <path d="m12 3 1.4 4.6L18 9l-4.6 1.4L12 15l-1.4-4.6L6 9l4.6-1.4z" />
      <path d="m19 15 .7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7z" />
    </>
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="4" />
      <path d="M12 3v3M21 12h-3M12 21v-3M3 12h3" />
    </>
  ),
  trash: (
    <>
      <path d="M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6M14 11v6" />
    </>
  ),
  upload: (
    <>
      <path d="M12 16V4m0 0L8 8m4-4 4 4M5 15v5h14v-5" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </>
  ),
  x: <path d="m6 6 12 12M18 6 6 18" />,
}

export function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {iconPaths[name]}
    </svg>
  )
}

type AstroPose =
  | "neutral"
  | "wave"
  | "think"
  | "celebrate"
  | "read"
  | "coach"
  | "interviewer"
  | "peek"

export function Astro({
  size = "large",
  pose = "neutral",
}: {
  size?: "small" | "medium" | "large"
  pose?: AstroPose
}) {
  const suitArm = {
    fill: "url(#suit)",
    stroke: "#aab7eb",
    strokeWidth: 5,
    strokeLinejoin: "round" as const,
  }

  return (
    <div
      className={`astro-character astro-${size} astro-pose-${pose}`}
      aria-label="Astro, tu copiloto de carrera"
    >
      <svg viewBox="0 0 320 320" role="img">
        <defs>
          <linearGradient id="suit" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="#fff" />
            <stop offset="1" stopColor="#dfe6ff" />
          </linearGradient>
          <linearGradient id="visor" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="#182563" />
            <stop offset=".55" stopColor="#4c36bd" />
            <stop offset="1" stopColor="#8c6dff" />
          </linearGradient>
        </defs>
        <path
          className="astro-orbit"
          d="M35 180c35 70 195 94 250 5 45-74-47-145-149-125"
          fill="none"
        />
        <circle className="astro-star star-one" cx="52" cy="90" r="5" />
        <circle className="astro-star star-two" cx="267" cy="93" r="8" />
        <path className="astro-shadow" d="M89 268c37 22 118 22 147-3" />
        {pose === "celebrate" ? (
          <>
            <path className="astro-arm" d="M116 177C91 165 76 140 67 107c-3-11-13-16-22-11-8 5-7 15-3 24 14 37 34 66 65 78z" {...suitArm} />
            <path className="astro-arm" d="M208 177c25-12 40-37 49-70 3-11 13-16 22-11 8 5 7 15 3 24-14 37-34 66-65 78z" {...suitArm} />
          </>
        ) : pose === "wave" ? (
          <>
            <path className="astro-arm" d="M107 168c-16 7-28 24-35 45-3 10 1 18 10 20 8 2 13-3 17-12l17-39z" {...suitArm} />
            <path className="astro-arm astro-arm-wave" d="M211 177c20-9 27-24 27-45l-1-27c0-10 7-17 15-16 9 1 12 9 11 18l-2 35c-2 31-18 52-43 62z" {...suitArm} />
            <path className="astro-wave-lines" d="M269 78c9 5 15 13 17 23M270 63c15 6 27 18 31 33" />
          </>
        ) : pose === "think" ? (
          <>
            <path className="astro-arm" d="M107 168c-18 8-30 26-33 47-2 10 3 18 12 19 8 1 13-5 16-14l14-38z" {...suitArm} />
            <path className="astro-arm" d="M210 177c18 4 31-1 38-13l11-18c5-8 2-17-6-21-8-3-14 1-18 8l-10 17-16-2z" {...suitArm} />
            <circle className="astro-thought" cx="253" cy="74" r="5" />
            <circle className="astro-thought thought-two" cx="270" cy="56" r="8" />
          </>
        ) : pose === "read" ? (
          <>
            <path className="astro-arm" d="M110 173c-20 8-28 25-26 47 1 10 8 15 17 12l31-18-8-20-19 9z" {...suitArm} />
            <path className="astro-arm" d="M214 173c20 8 28 25 26 47-1 10-8 15-17 12l-31-18 8-20 19 9z" {...suitArm} />
          </>
        ) : pose === "interviewer" ? (
          <>
            <path className="astro-arm" d="M109 172c-20 6-31 21-34 42-2 10 3 18 12 19 8 1 13-5 16-14l12-20 22 13 10-19z" {...suitArm} />
            <path className="astro-arm astro-arm-interview" d="M211 176c19-1 32-10 43-25l11-15c6-8 15-9 21-3 6 7 3 15-4 22l-15 17c-15 17-32 27-53 28z" {...suitArm} />
            <path className="astro-interview-lines" d="M278 122l7-8M288 131l10-3" />
          </>
        ) : pose === "coach" ? (
          <>
            <path className="astro-arm" d="M108 170c-19 8-29 27-31 47-1 10 5 17 14 17 8 0 12-7 15-16l11-37z" {...suitArm} />
            <path className="astro-arm astro-arm-point" d="M211 177c20 1 36-4 51-17l17-14c7-6 16-5 20 2 5 8 0 15-7 20l-22 16c-20 14-38 18-58 16z" {...suitArm} />
          </>
        ) : pose === "peek" ? (
          <>
            <path className="astro-arm" d="M108 169c-19 9-31 27-34 47-2 10 3 18 12 19 8 1 13-5 16-14l15-39z" {...suitArm} />
            <path className="astro-arm" d="M216 169c14 5 24 18 29 32 3 9-1 17-9 19-8 2-13-3-17-11l-12-27z" {...suitArm} />
          </>
        ) : (
          <>
            <path className="astro-arm" d="M107 168c-16 7-28 24-35 45-3 10 1 18 10 20 8 2 13-3 17-12l17-39z" {...suitArm} />
            <path className="astro-arm" d="M217 168c16 7 28 24 35 45 3 10-1 18-10 20-8 2-13-3-17-12l-17-39z" {...suitArm} />
          </>
        )}
        <path
          d="M112 159h99c15 28 17 69 4 104-26 13-80 13-107 0-13-35-11-76 4-104z"
          fill="url(#suit)"
          stroke="#aab7eb"
          strokeWidth="6"
        />
        <rect
          x="135"
          y="196"
          width="55"
          height="36"
          rx="12"
          fill="#f8f9ff"
          stroke="#c0c9ef"
          strokeWidth="4"
        />
        <circle cx="149" cy="210" r="4" fill="#7558ec" />
        <circle cx="162" cy="210" r="4" fill="#30c4aa" />
        <path
          d="M146 222h33"
          stroke="#aab7eb"
          strokeWidth="4"
          strokeLinecap="round"
        />
        {(pose === "read" || pose === "interviewer") && (
          <g className="astro-tablet">
            <rect
              x={pose === "interviewer" ? 105 : 122}
              y={pose === "interviewer" ? 194 : 199}
              width={pose === "interviewer" ? 60 : 80}
              height={pose === "interviewer" ? 70 : 57}
              rx="9"
              fill="#27346e"
              stroke="#aab7eb"
              strokeWidth="4"
              transform={pose === "interviewer" ? "rotate(-7 135 229)" : undefined}
            />
            <path
              d={pose === "interviewer" ? "M118 212h34M116 224h31M114 236h26" : "M138 217h48M138 229h37M138 241h42"}
              stroke="#b9adff"
              strokeWidth="4"
              strokeLinecap="round"
            />
          </g>
        )}
        <path
          d="M117 264v19c0 9 8 15 18 15h7v-31M207 264v19c0 9-8 15-18 15h-7v-31"
          fill="url(#suit)"
          stroke="#aab7eb"
          strokeWidth="6"
        />
        <circle
          cx="162"
          cy="124"
          r="72"
          fill="url(#suit)"
          stroke="#aab7eb"
          strokeWidth="7"
        />
        <path
          d="M109 116c4-42 24-61 53-61s50 19 54 61c3 31-18 54-54 54s-56-23-53-54z"
          fill="url(#visor)"
        />
        <path
          d="M130 88c17-16 47-20 67-2"
          fill="none"
          stroke="#b9adff"
          strokeWidth="8"
          strokeLinecap="round"
          opacity=".72"
        />
        <circle className="astro-eye astro-eye-left" cx="140" cy="121" r="7" fill="#fff" />
        <circle className="astro-eye astro-eye-right" cx="184" cy="121" r="7" fill="#fff" />
        <path
          className="astro-smile"
          d="M143 143c12 9 26 9 38 0"
          fill="none"
          stroke="#fff"
          strokeWidth="5"
          strokeLinecap="round"
        />
        <path
          d="M96 105c-8 5-12 15-9 25 2 7 7 12 15 14M228 105c8 5 12 15 9 25-2 7-7 12-15 14"
          fill="#e9edff"
          stroke="#aab7eb"
          strokeWidth="5"
        />
      </svg>
    </div>
  )
}

export function Brand({ light = false }: { light?: boolean }) {
  return (
    <div className={`brand ${light ? "brand-light" : ""}`}>
      <span className="brand-mark">
        <Icon name="rocket" size={18} />
      </span>
      <span>
        Career <strong>Copilot</strong>
      </span>
    </div>
  )
}

export function Button({
  children,
  variant = "primary",
  icon,
  onClick,
  type = "button",
  disabled = false,
}: {
  children: ReactNode
  variant?: "primary" | "secondary" | "ghost" | "danger"
  icon?: IconName
  onClick?: () => void
  type?: "button" | "submit"
  disabled?: boolean
}) {
  return (
    <button
      className={`btn btn-${variant}`}
      onClick={onClick}
      type={type}
      disabled={disabled}
    >
      {children}
      {icon && <Icon name={icon} size={18} />}
    </button>
  )
}
