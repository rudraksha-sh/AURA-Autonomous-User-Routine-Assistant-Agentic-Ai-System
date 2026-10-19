export function dateKeyInZone(value: Date, zone: string) {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: zone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(value);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

export function shiftDate(day: string, amount: number) {
  const date = new Date(`${day}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + amount);
  return date.toISOString().slice(0, 10);
}

export function startOfWeek(day: string) {
  const date = new Date(`${day}T00:00:00Z`);
  return shiftDate(day, -date.getUTCDay());
}

export function weekDays(day: string) {
  const start = startOfWeek(day);
  return Array.from({ length: 7 }, (_, index) => shiftDate(start, index));
}

function zonedParts(value: Date, zone: string) {
  return Object.fromEntries(new Intl.DateTimeFormat("en-CA", { timeZone: zone, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(value).map((part) => [part.type, part.value]));
}

export function zonedTimeToIso(day: string, clock: string, zone: string) {
  const [year, month, date] = day.split("-").map(Number);
  const [hour, minute] = clock.split(":").map(Number);
  const target = Date.UTC(year, month - 1, date, hour, minute);
  let guess = target;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const parts = zonedParts(new Date(guess), zone);
    const represented = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day), Number(parts.hour), Number(parts.minute));
    guess += target - represented;
  }
  return new Date(guess).toISOString();
}

export function timeInZone(value: string, zone: string) {
  const parts = zonedParts(new Date(value), zone);
  return `${parts.hour}:${parts.minute}`;
}

export function dateInZone(value: string, zone: string) {
  const parts = zonedParts(new Date(value), zone);
  return `${parts.year}-${parts.month}-${parts.day}`;
}

export function minuteOfDayInZone(value: string, zone: string) {
  const parts = zonedParts(new Date(value), zone);
  return Number(parts.hour) * 60 + Number(parts.minute);
}

export function dayStartIso(day: string, zone: string) {
  return zonedTimeToIso(day, "00:00", zone);
}

export function dayEndIso(day: string, zone: string) {
  return zonedTimeToIso(shiftDate(day, 1), "00:00", zone);
}
