import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { canonicalLocale, firstDayOf } from "./locale.js";

/**
 * <ui-calendar>: calendar with the views month, week, day and agenda (a list of the coming days), built on
 * FullCalendar (vendor/fullcalendar, loaded once on first use) and themed with Bootstrap 6's tokens through its own
 * --ui-calendar-* tokens (documented in the docs app).
 *
 * Events come from the host: set `source` to an async function ({start, end}) => [event, …]; it is called for
 * every range the calendar shows (and again on refetch()). An event: {id, title, start, end?, allDay?, color?,
 * textColor?, display? ("auto", "block", "list-item"), muted? (struck through and faded, e.g. done), subtitle?
 * (with soft: shown below the title, e.g. a place), resizable? (false: to drag, not to resize), editable?
 * (false: not to drag), data? (any value, handed back in the events below)}; start/end as Date or ISO text, a date without time is all day.
 *
 * Attributes:
 * - view: "month" (default), "week", "day" or "agenda". Kept in sync when the user switches views.
 * - date: ISO date the calendar shows (default today); the user's navigation updates it.
 * - agenda-days: days the agenda covers (default 30).
 * - scroll-time: hour the week and day views start scrolled to (default 7).
 * - locale: language tag (default: the nearest lang attribute, i.e. the page's <html lang>, else "en"). Its language
 *   gives the texts (bundled: de and en, another one falls back to English), the full tag the date formats (e.g.
 *   "en-CH" or "en-GB": day before month, 04/11, not the US order; "de-CH": 04.11.) and the first day of the week.
 * - first-day: first day of the week, 0 (Sunday) … 6 (Saturday) or an English weekday name ("monday"); default
 *   from the locale (Monday for de, de-CH, en-GB, en-CH; Sunday for en and en-US).
 * - month-label, week-label, day-label, agenda-label, today-label: the toolbar's texts (default in the calendar's
 *   language: "Month", "Week", "Day", "Agenda", "Today" or "Monat", "Woche", "Tag", "Agenda", "Heute"); a page sets
 *   them with its translations like every component's labels (e.g. month-label="{{ _('Month') }}").
 * - toolbar: "none" hides the built-in toolbar (navigate with the methods instead).
 * - selectable: a click on a free spot or dragging over several (time slots, days) selects that range and fires
 *   ui-calendar:select (e.g. to create an event there); the selection stays until unselect().
 * - editable: events can be dragged to another time and resized at their end (not those with editable: false);
 *   fires ui-calendar:event-change, the host saves it or calls detail.revert().
 * - full-day: week and day show all 24 hours without scrolling (one row per hour, dragging snaps to 15 minutes).
 *   In week and day every event is at least one line of its title high, however short.
 * - soft: events tinted in their colour (light background, the title bold in a strong shade of it, no frame),
 *   below the title the time and the event's subtitle (e.g. a place); events that are over are faded. A line never
 *   shows only in part: what does not fit is left out, the last line shown ends with «…».
 *
 * Methods: refetch(), today(), prev(), next(), gotoDate(date), unselect(), eventOf(element) (the event an element of
 * the calendar shows, e.g. for a context menu: {id, data, start, end, allDay} as with a click, null for none).
 * Property title: the shown range as text (for a toolbar of the host, with toolbar="none"; ui-calendar:range brings it
 * on every change).
 *
 * Events (bubble, composed):
 * - ui-calendar:range: the shown range changed; detail {view, start, end, title}.
 * - ui-calendar:event-click: detail {id, data, start, end, allDay}.
 * - ui-calendar:date-click: a free spot was clicked; detail {date, allDay}.
 * - ui-calendar:select (with selectable): a range was selected; detail {start, end (exclusive), allDay}.
 * - ui-calendar:event-change (with editable): an event was moved or resized; detail {id, data, start, end, allDay,
 *   oldStart, oldEnd, oldAllDay, revert()}.
 *
 * Custom properties: --ui-calendar-* (see ui-calendar.css), e.g. --ui-calendar-height (default max(30rem, 75vh)).
 */
const VIEWS = ["month", "week", "day", "agenda"]; // FullCalendar views of these names, see afterRender()
/** The toolbar's texts per bundled language (FullCalendar's English ones are lowercase). */
const LABELS = {
  en: { month: "Month", week: "Week", day: "Day", agenda: "Agenda", today: "Today" },
  de: { month: "Monat", week: "Woche", day: "Tag", agenda: "Agenda", today: "Heute" },
};
const BUNDLED = Object.keys(LABELS);
const VENDOR = ["fullcalendar.global.js", "themes/classic/global.js", "locales/de/global.js"]
  .map((f) => new URL(`../../../vendor/fullcalendar/${f}`, import.meta.url).href);

let vendorLoaded = null;

/** A CSS colour ("#RRGGBB", "#RGB" or "rgb(r, g, b)") as [r, g, b], or null. */
function rgbOf(color) {
  const c = String(color || "").trim();
  let m = /^#([0-9a-f]{6})$/i.exec(c);
  if (m) return [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16));
  m = /^#([0-9a-f]{3})$/i.exec(c);
  if (m) return [...m[1]].map((h) => parseInt(h + h, 16));
  m = /^rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)/i.exec(c);
  return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null;
}

/** A computed colour (rgb(), oklch(), color(), …) as [r, g, b] through a 1×1 canvas; null when transparent. */
function canvasRgb(color) {
  canvasRgb.context ??= document.createElement("canvas").getContext("2d", { willReadFrequently: true });
  const context = canvasRgb.context;
  context.clearRect(0, 0, 1, 1);
  context.fillStyle = "rgba(0, 0, 0, 0)";
  context.fillStyle = color;
  context.fillRect(0, 0, 1, 1);
  const [r, g, b, alpha] = context.getImageData(0, 0, 1, 1).data;
  return alpha ? [r, g, b] : null;
}

/** `share` of colour a mixed with b, as "#RRGGBB" (FullCalendar takes no color-mix()). */
function mix(a, b, share) {
  return `#${a.map((v, i) => Math.round(v * share + b[i] * (1 - share)).toString(16).padStart(2, "0")).join("")}`;
}

/** With soft: an event's text cut so that every line it shows fits whole in its height, the last one ending
 *  with «…» (the subtitle first, then the title): the longest beginning of «title, time and subtitle» that fits
 *  (binary search, a few layouts per event). */
function fitLines(el) {
  const box = el.querySelector(".ui-calendar-soft.is-lines");
  if (!box) return;
  const title = box.querySelector(".ui-calendar-soft__title");
  const meta = box.querySelector(".ui-calendar-soft__meta");
  const full = [box.dataset.title ?? (box.dataset.title = title.textContent),
    meta ? (box.dataset.meta ?? (box.dataset.meta = meta.textContent)) : ""];
  const show = (n) => { // the first n characters (title, then subtitle), «…» if cut
    const cut = n < full[0].length + full[1].length;
    title.textContent = full[0].slice(0, n) + (cut && n <= full[0].length ? "…" : "");
    if (meta) {
      const rest = Math.max(0, n - full[0].length);
      meta.textContent = rest ? full[1].slice(0, rest).trimEnd() + (cut ? "…" : "") : "";
      meta.hidden = !rest;
      meta.previousElementSibling?.toggleAttribute("hidden", !rest); // the <br>
    }
  };
  const fits = () => box.scrollHeight <= box.clientHeight + 1;
  const total = full[0].length + full[1].length;
  show(total);
  if (fits()) return;
  let lo = 0;
  let hi = total - 1;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    show(mid);
    if (fits()) lo = mid;
    else hi = mid - 1;
  }
  show(lo);
}

/** With soft: events that are over (FullCalendar's render prop isPast) are faded. */
function joinPast(info) {
  return info?.isPast ? "ui-calendar-event--past" : "";
}

/** Class for Saturday and Sunday (FullCalendar's day render props: dow 0 = Sunday). */
function weekend(info) {
  return info && (info.dow === 0 || info.dow === 6) && !info.isToday ? "ui-calendar-weekend" : "";
}

/** FullCalendar's scripts, once per page, in order (the theme and the locale register with the core). */
function loadVendor() {
  vendorLoaded ??= VENDOR.reduce((done, src) => done.then(() => new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`FullCalendar could not be loaded: ${src}`));
    document.head.append(script);
  })), Promise.resolve()).catch((error) => {
    vendorLoaded = null;  // a later calendar tries again
    throw error;
  });
  return vendorLoaded;
}

function isoDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export class UiCalendar extends ShadowComponentElement {
  // FullCalendar's own stylesheets first (they style its markup in the shadow tree), then the theme on Bootstrap's tokens.
  static stylesheets = [
    new URL("../../../vendor/fullcalendar/skeleton.css", import.meta.url).href,
    new URL("../../../vendor/fullcalendar/themes/classic/theme.css", import.meta.url).href,
    new URL("./ui-calendar.css", import.meta.url).href,
  ];
  static observedAttributes = ["view", "date", "agenda-days", "scroll-time", "locale", "first-day", "toolbar", "selectable", "editable", "full-day",
    "soft", "month-label", "week-label", "day-label", "agenda-label", "today-label"];

  #calendar = null;
  #shown = new WeakMap(); // element of an event -> the event (eventOf)
  #probe = null; // with soft: a hidden element that resolves colour tokens (#resolve)
  #fitting = null; // with soft: a ResizeObserver that fits the lines of the events to their height
  #source = null;
  #syncing = false; // attribute updates made by the calendar itself

  get source() {
    return this.#source;
  }

  set source(fn) {
    this.#source = typeof fn === "function" ? fn : null;
    this.refetch();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue || this.#syncing) return;
    const cal = this.#calendar;
    if (cal && name === "view" && VIEWS.includes(newValue)) cal.changeView(newValue);
    else if (cal && name === "date" && newValue) cal.gotoDate(newValue);
    else super.attributeChangedCallback(name, oldValue, newValue);  // everything else: build it again
  }

  disconnectedCallback() {
    this.#fitting?.disconnect();
    this.#fitting = null;
    this.#calendar?.destroy();
    this.#calendar = null;
  }

  refetch() {
    this.#calendar?.refetchEvents();
  }

  today() {
    this.#calendar?.today();
  }

  prev() {
    this.#calendar?.prev();
  }

  next() {
    this.#calendar?.next();
  }

  gotoDate(date) {
    this.#calendar?.gotoDate(date);
  }

  unselect() {
    this.#calendar?.unselect();
  }

  get title() {
    return this.#calendar?.view?.title || "";
  }

  /** The full language tag: the attribute locale, else the nearest lang (the page's), else "en"; e.g. "en-CH". */
  get localeTag() {
    return canonicalLocale(this.getAttribute("locale") || this.closest("[lang]")?.getAttribute("lang")
      || document.documentElement.lang || "en");
  }

  /** The calendar's language (its texts): that of localeTag if bundled, else "en"; "de-CH" -> "de". */
  get locale() {
    const wanted = this.localeTag.toLowerCase();
    return BUNDLED.includes(wanted) ? wanted : (BUNDLED.find((code) => wanted.startsWith(`${code}-`)) || "en");
  }

  /** The first day of the week (0 = Sunday): the attribute first-day, else that of localeTag. */
  get firstDay() {
    return firstDayOf(this.getAttribute("first-day"), this.localeTag);
  }

  /** The toolbar's texts: the *-label attributes, else those of the calendar's language. */
  get toolbarLabels() {
    const defaults = LABELS[this.locale] || LABELS.en;
    return Object.fromEntries(Object.entries(defaults).map(([key, text]) => [key, this.getAttribute(`${key}-label`) || text]));
  }

  render() {
    return '<div class="ui-calendar__error" data-error hidden></div><div class="ui-calendar" part="calendar" data-calendar></div>';
  }

  async afterRender() {
    this.#calendar?.destroy();
    this.#calendar = null;
    const el = this.shadowRoot.querySelector("[data-calendar]");
    try {
      await loadVendor();
    } catch (error) {
      this.#error(error.message);
      return;
    }
    if (!el.isConnected) return;  // rendered again meanwhile
    const FC = window.FullCalendar;
    const view = VIEWS.includes(this.getAttribute("view")) ? this.getAttribute("view") : "month";
    const hour = Math.max(0, Math.min(23, Number(this.getAttribute("scroll-time") ?? 7) || 0));
    const fullDay = this.hasAttribute("full-day")
      ? { slotDuration: "01:00:00", snapDuration: "00:15:00", expandRows: true }
      : {};
    // times as 08:00, also in ranges («10:00–11:00»; the browser's own range format adds «Uhr» in German), days in
    // week and day as «Mittwoch, 04.11.»
    const clock = { hour: "2-digit", minute: "2-digit", hour12: false, omitZeroMinute: false, meridiem: false };
    const hhmm = (d) => `${String(d.hour).padStart(2, "0")}:${String(d.minute).padStart(2, "0")}`;
    const times = (arg) => (arg.end ? `${hhmm(arg.start)}–${hhmm(arg.end)}` : hhmm(arg.start));
    const dayHeader = { dayHeaderFormat: { weekday: "long", day: "2-digit", month: "2-digit", omitCommas: false } };
    // week and day: an event at least one line of its title high (a 15-minute one is too low for it otherwise);
    // the line as in the styles (font 0.75rem, line height 1.3) plus a little for the frame
    const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    const eventMinHeight = Math.ceil(rem * 0.75 * 1.3) + 4;
    const soft = this.hasAttribute("soft");
    const labels = this.toolbarLabels;
    // FullCalendar takes its texts from the language and formats the dates with the full tag (Intl); a language
    // not bundled is English throughout (texts and formats alike)
    const language = this.locale;
    const cal = new FC.Calendar(el, {
      locale: this.localeTag.toLowerCase().startsWith(language) ? this.localeTag : language,
      firstDay: this.firstDay,
      initialView: view,
      initialDate: this.getAttribute("date") || undefined,
      height: "100%",
      headerToolbar: this.getAttribute("toolbar") === "none" ? false
        : { start: "prev,next today", center: "title", end: "agenda,day,week,month" },
      views: {
        month: { type: "dayGridMonth" },
        week: { type: "timeGridWeek", ...fullDay, ...dayHeader },
        day: { type: "timeGridDay", ...fullDay, ...dayHeader },
        agenda: { type: "list", duration: { days: Math.max(1, Number(this.getAttribute("agenda-days")) || 30) } },
      },
      // the toolbar's texts (FullCalendar 7: `buttons`, per view name and «today»)
      buttons: Object.fromEntries(Object.entries(labels).map(([name, text]) => [name, { text }])),
      dayMaxEvents: true,
      eventMinHeight,
      slotHeaderFormat: clock,
      eventTimeFormat: times,
      nowIndicator: true,
      navLinks: true,
      weekNumbers: true,
      scrollTime: `${String(hour).padStart(2, "0")}:00:00`,
      events: (info, success, failure) => {
        if (!this.#source) {
          success([]);
          return;
        }
        Promise.resolve(this.#source({ start: info.start, end: info.end }))
          .then((events) => {
            this.#error("");
            success((events || []).map((e) => this.#toFc(e)));
          })
          .catch((error) => {
            this.#error(error?.message || String(error));
            failure(error);
          });
      },
      datesSet: (info) => {
        this.#reflect(info.view.type, isoDate(cal.getDate()));
        this.#emit("ui-calendar:range", { view: info.view.type, start: info.start, end: info.end, title: info.view.title });
      },
      eventClick: (info) => {
        info.jsEvent?.preventDefault();
        const e = info.event;
        this.#emit("ui-calendar:event-click", { id: e.id, data: e.extendedProps?.data, start: e.start, end: e.end, allDay: e.allDay });
      },
      dateClick: (info) => this.#emit("ui-calendar:date-click", { date: info.date, allDay: info.allDay }),
      selectable: this.hasAttribute("selectable"),
      selectMirror: true,
      selectMinDistance: 0,
      unselectAuto: false,
      select: (info) => this.#emit("ui-calendar:select", { start: info.start, end: info.end, allDay: info.allDay }),
      // weekends a shade darker (FullCalendar joins these with the theme's own classes)
      dayCellClass: weekend,
      dayLaneClass: weekend,
      dayHeaderClass: weekend,
      // every event's element knows its event (eventOf()); soft: its lines fit the box
      eventDidMount: (info) => {
        this.#shown.set(info.el, info.event);
        if (soft) this.#watch(info.el, true);
      },
      eventWillUnmount: (info) => {
        this.#shown.delete(info.el);
        if (soft) this.#watch(info.el, false);
      },
      ...(soft ? {
        eventContent: (info) => this.#content(info),
        eventClass: (info) => joinPast(info),
      } : {}),
      editable: this.hasAttribute("editable"),
      eventDrop: (info) => this.#changed(info),
      eventResize: (info) => this.#changed(info),
    });
    cal.render();
    this.#calendar = cal;
  }

  /** The event the element `el` of the calendar (or an element inside it) shows: {id, data, start, end, allDay}. */
  eventOf(el) {
    for (let n = el; n; n = n.parentNode || n.host) {
      const e = this.#shown.get(n);
      if (e) return { id: e.id, data: e.extendedProps?.data, start: e.start, end: e.end, allDay: e.allDay };
      if (n === this) break;
    }
    return null;
  }

  #changed(info) {
    const e = info.event;
    const old = info.oldEvent;
    this.#emit("ui-calendar:event-change", {
      id: e.id, data: e.extendedProps?.data, start: e.start, end: e.end, allDay: e.allDay,
      oldStart: old?.start, oldEnd: old?.end, oldAllDay: old?.allDay, revert: () => info.revert(),
    });
  }

  /** With soft: {color, contrastColor} of a colour: mixed with the calendar's background (light) and its strongest text
   *  colour (a dark shade; in dark mode a light one), as the page shows them now. */
  #tint(color) {
    const c = rgbOf(color) || this.#resolve(color);
    if (!c) return null;
    // Tokens hold var(), light-dark() or oklch(): the browser resolves them where the calendar is (its colour mode).
    const bg = this.#resolve("var(--ui-calendar-bg)") || this.#resolve("var(--bs-bg-body, #fff)") || [255, 255, 255];
    const fg = this.#resolve("var(--bs-fg-body, #000)") || [0, 0, 0];
    return { color: mix(c, bg, 0.18), contrastColor: mix(c, fg, 0.62) };
  }

  /** A CSS colour (also var(), light-dark()) as [r, g, b], computed inside the calendar (its colour mode); null if
   *  transparent or invalid. A background, as it does not inherit: an undefined var() gives transparent. */
  #resolve(css) {
    this.#probe ??= Object.assign(document.createElement("span"), { hidden: true });
    if (!this.#probe.isConnected) (this.shadowRoot || this).append(this.#probe);
    this.#probe.style.backgroundColor = "";
    this.#probe.style.backgroundColor = css;
    return this.#probe.style.backgroundColor ? canvasRgb(getComputedStyle(this.#probe).backgroundColor) : null;
  }


  /** With soft: in day and week the title bold and below it time and subtitle; elsewhere FullCalendar's own
   *  content (dots in the month, the agenda's rows). */
  #content(info) {
    const view = info.view?.type;
    const e = info.event;
    if (view === "agenda" || (view === "month" && !e.allDay)) return true;
    const sub = e.extendedProps?.subtitle;
    const title = escapeHtml(e.title || "");
    // short events (under 45 minutes, a single line high): title and time in one line, cut off with «…»
    if (!e.allDay && e.end && e.end - e.start < 45 * 60000) {
      return { html: `<div class="ui-calendar-soft is-short"><span class="ui-calendar-soft__title">${title}</span>${
        info.timeText ? ` <span class="ui-calendar-soft__meta">${escapeHtml(info.timeText)}</span>` : ""}</div>` };
    }
    const meta = [!e.allDay && info.timeText, sub].filter(Boolean).map((t) => escapeHtml(String(t))).join(" | ");
    // one block of lines (title, then time and subtitle), cut by fitLines to what fits whole
    return { html: `<div class="ui-calendar-soft is-lines"><span class="ui-calendar-soft__title">${title}</span>${
      meta ? `<br><span class="ui-calendar-soft__meta">${meta}</span>` : ""}</div>` };
  }

  /** With soft: an event's element watched for its size (mounted) or no longer (unmounted). */
  #watch(el, on) {
    if (!on) {
      this.#fitting?.unobserve(el);
      return;
    }
    this.#fitting ||= new ResizeObserver((entries) => entries.forEach((entry) => fitLines(entry.target)));
    this.#fitting.observe(el);
    fitLines(el);
  }

  /** An event for FullCalendar. Only keys with a value: FullCalendar refines every key present (editable:
   *  undefined would become false and override the calendar's own editable). */
  #toFc(e) {
    const out = { title: e.title ?? "", start: e.start, extendedProps: { data: e.data, subtitle: e.subtitle } };
    if (e.id != null) out.id = String(e.id);
    if (e.end) out.end = e.end;
    if (e.allDay != null) out.allDay = Boolean(e.allDay);
    // FullCalendar v7: color (the area) and contrastColor (its text), classes in className
    const tint = this.hasAttribute("soft") && e.display !== "list-item" && this.#tint(e.color);
    if (tint) Object.assign(out, tint);
    else if (e.color) out.color = e.color;
    if (e.textColor) out.contrastColor = e.textColor;
    if (e.display) out.display = e.display;
    if (e.editable === false) out.editable = false;
    else if (e.resizable === false) out.durationEditable = false; // to drag, not to resize (e.g. a task)
    // every event is clickable (ui-calendar:event-click), also those not to drag
    out.className = e.muted ? "ui-calendar-event ui-calendar-event--muted" : "ui-calendar-event";
    return out;
  }

  #reflect(view, date) {
    this.#syncing = true;
    try {
      if (view && this.getAttribute("view") !== view) this.setAttribute("view", view);
      if (date && this.getAttribute("date") !== date) this.setAttribute("date", date);
    } finally {
      this.#syncing = false;
    }
  }

  #emit(type, detail) {
    this.dispatchEvent(new CustomEvent(type, { detail, bubbles: true, composed: true }));
  }

  #error(message) {
    const box = this.shadowRoot?.querySelector("[data-error]");
    if (!box) return;
    box.hidden = !message;
    box.innerHTML = message ? escapeHtml(message) : "";
  }
}

registerComponent("ui-calendar", UiCalendar);
