// All timestamps displayed in the UI are formatted in Mountain Time
// (America/Denver) for consistency with the Boob Bus's Utah-based operations.

const TZ = "America/Denver";

// The backend mixes two timestamp formats:
//   - Python isoformat: "2026-04-15T04:20:00+00:00" (has offset, parses correctly)
//   - SQLite DEFAULT CURRENT_TIMESTAMP: "2026-04-15 04:20:00" (no offset, UTC)
//
// JavaScript's Date constructor parses the second form as LOCAL time, which
// silently shifts every date by the viewer's timezone offset. We normalize
// naive timestamps by treating them as UTC.
function parseAsUTC(s) {
  if (s == null) return null;
  if (typeof s !== "string") return new Date(s);
  // Already has a timezone indicator — trust it.
  if (/Z$|[+-]\d{2}:?\d{2}$/.test(s)) return new Date(s);
  // SQLite-style "YYYY-MM-DD HH:MM:SS[.fff]" → promote to ISO UTC.
  const isoish = s.includes("T") ? s : s.replace(" ", "T");
  return new Date(isoish + "Z");
}

export function formatDateTime(iso) {
  if (!iso) return "—";
  const d = parseAsUTC(iso);
  if (!d || Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-US", {
    timeZone: TZ,
    month: "numeric",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

export function formatDate(iso) {
  if (!iso) return "—";
  const d = parseAsUTC(iso);
  if (!d || Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", {
    timeZone: TZ,
    month: "numeric",
    day: "numeric",
    year: "numeric",
  });
}

// Next follow-up display: the DB stores the EARLIEST eligible timestamp, but
// the daily follow-up cron only fires at 17:00 UTC (11 AM MDT / 10 AM MST).
// Round the eligibility time up to the next 17:00 UTC tick so the UI shows
// the actual send time the user can expect.
const FOLLOW_UP_CRON_HOUR_UTC = 17;

export function formatNextFollowUp(iso) {
  if (!iso) return "—";
  const d = parseAsUTC(iso);
  if (!d || Number.isNaN(d.getTime())) return "—";

  // Compute next 17:00 UTC tick at or after d.
  const cron = new Date(Date.UTC(
    d.getUTCFullYear(),
    d.getUTCMonth(),
    d.getUTCDate(),
    FOLLOW_UP_CRON_HOUR_UTC, 0, 0, 0,
  ));
  if (cron < d) cron.setUTCDate(cron.getUTCDate() + 1);

  return cron.toLocaleString("en-US", {
    timeZone: TZ,
    month: "numeric",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}
