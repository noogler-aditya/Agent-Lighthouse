function IconBase({ children, className = '', ...props }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

export function Bot(props) {
  return (
    <IconBase {...props}>
      <rect x="5" y="8" width="14" height="12" rx="2" />
      <path d="M12 4v4" />
      <path d="M8 12h.01" />
      <path d="M16 12h.01" />
      <path d="M9 16h6" />
    </IconBase>
  );
}

export function Cpu(props) {
  return (
    <IconBase {...props}>
      <rect x="8" y="8" width="8" height="8" rx="1" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
      <path d="M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1" />
    </IconBase>
  );
}

export function RefreshCcw(props) {
  return (
    <IconBase {...props}>
      <path d="M3 2v6h6" />
      <path d="M21 22v-6h-6" />
      <path d="M21 9a9 9 0 0 0-15-5L3 8" />
      <path d="M3 15a9 9 0 0 0 15 5l3-4" />
    </IconBase>
  );
}

export function Trash2(props) {
  return (
    <IconBase {...props}>
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2" />
      <path d="M6 6l1 14h10l1-14" />
      <path d="M10 11v6M14 11v6" />
    </IconBase>
  );
}

export function Wrench(props) {
  return (
    <IconBase {...props}>
      <path d="M21 7.5a5.5 5.5 0 0 1-7.7 5L6 20l-2-2 7.5-7.3A5.5 5.5 0 0 1 17 3" />
    </IconBase>
  );
}

export function Radar(props) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <path d="m12 12 6-3" />
      <circle cx="12" cy="12" r="1" />
    </IconBase>
  );
}

export function Coins(props) {
  return (
    <IconBase {...props}>
      <ellipse cx="12" cy="6" rx="7" ry="3" />
      <path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6" />
      <path d="M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />
    </IconBase>
  );
}

export function SearchCode(props) {
  return (
    <IconBase {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" />
      <path d="m9 10-2 1 2 1" />
      <path d="m13 10 2 1-2 1" />
    </IconBase>
  );
}

export function TriangleAlert(props) {
  return (
    <IconBase {...props}>
      <path d="m12 3 10 18H2L12 3z" />
      <path d="M12 9v5" />
      <path d="M12 17h.01" />
    </IconBase>
  );
}

export function Pause(props) {
  return (
    <IconBase {...props}>
      <rect x="6" y="5" width="4" height="14" rx="1" />
      <rect x="14" y="5" width="4" height="14" rx="1" />
    </IconBase>
  );
}

export function Pencil(props) {
  return (
    <IconBase {...props}>
      <path d="M12 20h9" />
      <path d="m16.5 3.5 4 4L7 21H3v-4L16.5 3.5z" />
    </IconBase>
  );
}

export function Play(props) {
  return (
    <IconBase {...props}>
      <path d="m8 5 11 7-11 7V5z" />
    </IconBase>
  );
}

export function SkipForward(props) {
  return (
    <IconBase {...props}>
      <path d="m5 5 10 7-10 7V5z" />
      <path d="M19 5v14" />
    </IconBase>
  );
}

export function Hash(props) {
  return (
    <IconBase {...props}>
      <path d="M4 9h16M4 15h16M10 3 8 21M16 3l-2 18" />
    </IconBase>
  );
}

export function Search(props) {
  return (
    <IconBase {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" />
    </IconBase>
  );
}
