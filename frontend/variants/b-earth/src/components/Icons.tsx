// Material-style line icons (inline, no icon font).
const P: Record<string, string> = {
  search: 'M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z',
  fields: 'M3 5h8v6H3V5zm10 0h8v6h-8V5zM3 13h8v6H3v-6zm10 0h8v6h-8v-6zM5 7v2h4V7H5zm10 0v2h4V7h-4zM5 15v2h4v-2H5zm10 0v2h4v-2h-4z',
  layers: 'M12 3 2 8.5l10 5.5 10-5.5L12 3zm0 2.3 5.9 3.2L12 11.7 6.1 8.5 12 5.3zM4.1 12 2 13.2l10 5.5 10-5.5-2.1-1.2L12 16.4 4.1 12zm0 4.5L2 17.7l10 5.5 10-5.5-2.1-1.2-7.9 4.4-7.9-4.4z',
  trends: 'M3 17.5 9 11l4 4 7.5-8.5L22 8l-9 10.5-4-4-4.5 4.9L3 17.5zM3 3h2v18H3V3z',
  compare: 'M4 4h4v16H4V4zm6 6h4v10h-4V10zm6-3h4v13h-4V7z',
  brief: 'M6 2h9l5 5v15H6V2zm8 1.5V8h4.5L14 3.5zM8 11v2h8v-2H8zm0 4v2h8v-2H8zm0-8v2h4V7H8z',
  story: 'M4 5h16v11H7l-3 3V5zm2 2v7h12V7H6zm2 2h8v1.6H8V9zm0 3h5v1.6H8V12z',
  play: 'M8 5v14l11-7L8 5z',
  pause: 'M6 5h4v14H6V5zm8 0h4v14h-4V5z',
  up: 'm7 14 5-5 5 5H7z',
  down: 'm7 10 5 5 5-5H7z',
  close: 'm6.4 5 5.6 5.6L17.6 5 19 6.4 13.4 12l5.6 5.6-1.4 1.4-5.6-5.6L6.4 19 5 17.6l5.6-5.6L5 6.4 6.4 5z',
  plus: 'M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5z',
  minus: 'M5 11h14v2H5v-2z',
  cube: 'm12 2 9 5v10l-9 5-9-5V7l9-5zm0 2.3L6 7.6l6 3.3 6-3.3-6-3.3zM5 9.3v6.5l6 3.4v-6.6L5 9.3zm8 9.9 6-3.4V9.3l-6 3.3v6.6z',
  compass: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 2a8 8 0 1 1 0 16 8 8 0 0 1 0-16zm3.5 4.5-5 2-2 5 5-2 2-5z',
  home: 'M12 3 3 10.5V21h6v-6h6v6h6V10.5L12 3z',
  link: 'M14 4h6v6h-2V7.4l-7.3 7.3-1.4-1.4L16.6 6H14V4zM5 6h6v2H7v9h9v-4h2v6H5V6z',
  info: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1 5h2v2h-2V7zm0 4h2v6h-2v-6z',
  drop: 'M12 2.5S5.5 10 5.5 14.5a6.5 6.5 0 0 0 13 0C18.5 10 12 2.5 12 2.5z',
  check: 'm9.5 16.2-4-4L4 13.7l5.5 5.5L20.5 8.2 19 6.7l-9.5 9.5z',
  left: 'm14 6-6 6 6 6 1.4-1.4L10.8 12l4.6-4.6L14 6z',
  right: 'm10 6-1.4 1.4 4.6 4.6-4.6 4.6L10 18l6-6-6-6z',
  news: 'M4 4h13v3h3v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4zm2 2v12h11V6H6zm2 2h7v3H8V8zm0 5h7v1.5H8V13zm0 2.5h5V17H8v-1.5z',
  sat: 'm13.5 2.5 3 3-2.2 2.2 2 2L18.5 7.5l3 3-4.7 4.7-2-2-1.6 1.6a5 5 0 0 1-7 0l-.2-.2a5 5 0 0 1 0-7l1.6-1.6-2-2 4.7-4.7 3 3 .2.2zM3 17a4 4 0 0 0 4 4v-2a2 2 0 0 1-2-2H3z',
  warn: 'M12 3 1.5 21h21L12 3zm-1 7h2v5h-2v-5zm0 7h2v2h-2v-2z',
};
export default function Icon({ name, size = 20 }: { name: keyof typeof P | string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d={P[name]} fillRule="evenodd" clipRule="evenodd" />
    </svg>
  );
}
