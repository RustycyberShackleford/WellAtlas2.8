# WellAtlas by Henry Suden

- 2.6-style UI, interactive pins → Site → Jobs
- Customers directory & customer pages (address/phone/email/notes/photos)
- Search + job category + customer filter
- MapTiler support via `MAPTILER_KEY` env var
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120`
