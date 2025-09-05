# WellAtlas 2.9 — Classic Map (Improved)

**Start command**
```
gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
```

**Env vars**
- MAPTILER_KEY (required)
- SECRET_KEY (optional)

**Notes**
- Interactive pins → Site pages → Jobs
- Customers page + share links (customer / job)
- Public portals: /s/customer/<token>, /s/job/<token>
- Background image: static/wallpaper.jpg
- DB: data/wellatlas.db (auto) | uploads/ for images
