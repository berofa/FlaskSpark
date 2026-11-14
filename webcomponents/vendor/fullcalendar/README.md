# FullCalendar

FullCalendar (Vanilla JS) **v7.1.3**, MIT (`LICENSE.md`), from the npm package `fullcalendar`, unchanged:

- `fullcalendar.global.js`: `all/global.js` (core, Preact and all free plugins: daygrid, timegrid, list,
  multimonth, interaction; sets `window.FullCalendar`)
- `themes/classic/global.js`, `themes/classic/theme.css`: theme "classic" (`ui-calendar` sets the colours itself,
  `palette.css` is not needed)
- `locales/de/global.js`: German
- `skeleton.css`: base layout

Used by `modules/calendar/ui-calendar`. Update: fetch the new package from `registry.npmjs.org/fullcalendar`,
replace the same files, bump the version here.
