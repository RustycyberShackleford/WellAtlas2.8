
import os, sqlite3, random, secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "wellatlas.db")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------- Constants ----------
CUSTOMERS = ["Washington","Lincoln","Jefferson","Roosevelt","Kennedy"]
MINING_TERMS = [
    "Mother Lode","Pay Dirt","Sluice Box","Stamp Mill","Placer Claim","Drift Mine","Hydraulic Pit","Gold Pan","Tailings","Bedrock",
    "Pick and Shovel","Ore Cart","Quartz Vein","Mine Shaft","Black Sand","Rocker Box","Prospect Hole","Hard Rock","Assay Office","Grubstake",
    "Lode Claim","Panning Dish","Cradle Rocker","Dust Gold","Nugget Patch","Timbering","Creek Claim","Pay Streak","Ventilation Shaft","Bucket Line",
    "Dredge Cut","Amalgam Press","Prospector’s Camp","Claim Jumper","Mining Camp","Gold Dust","Mine Portal","Crosscut Drift","Incline Shaft","Strike Zone",
    "Wash Plant","Headframe","Drill Core","Stope Chamber","Milling House","Hoist House","Smelter Works","Ore Bin","Tunnel Bore","Grizzly Screen"
]
CATEGORIES = ["Domestic","Drilling","Ag","Electrical"]
PHOTO_FILES = ["demo1.jpg","demo2.jpg","demo3.jpg","demo4.jpg","demo5.jpg"]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- Core schema (sites, jobs, notes, photos) ----------
def ensure_schema():
    conn = db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            customer TEXT,
            description TEXT,
            latitude REAL,
            longitude REAL,
            deleted INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER,
            job_number TEXT,
            job_category TEXT,
            description TEXT,
            deleted INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER,
            body TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER,
            filename TEXT,
            caption TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS job_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            body TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS job_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            filename TEXT,
            caption TEXT,
            created_at TEXT
        )
    """)
    conn.commit(); conn.close()

def seed_demo_if_empty():
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sites")
    if cur.fetchone()[0] > 0:
        conn.close(); return
    coords = [(40.385,-122.280),(40.178,-122.240),(39.927,-122.180),(39.728,-121.837),(39.747,-122.194)]
    terms = MINING_TERMS.copy(); random.shuffle(terms)
    deleted_sites = set(random.sample(range(50), 2))
    job_num = 25001
    for i in range(50):
        customer = CUSTOMERS[i // 10]
        name = terms[i]
        desc = f"Primary site for {name}. Northern California operations."
        lat, lon = random.choice(coords)
        deleted_flag = 1 if i in deleted_sites else 0
        cur.execute("INSERT INTO sites (name,customer,description,latitude,longitude,deleted,created_at) VALUES (?,?,?,?,?,?,?)",
                    (name, customer, desc, lat, lon, deleted_flag, datetime.utcnow().isoformat()))
        site_id = cur.lastrowid
        job_cat = random.choice(CATEGORIES)
        job_desc = f"Job #{job_num} at {name}."
        cur.execute("INSERT INTO jobs (site_id,job_number,job_category,description,deleted,created_at) VALUES (?,?,?,?,?,?)",
                    (site_id, str(job_num), job_cat, job_desc, 0, datetime.utcnow().isoformat()))
        job_id = cur.lastrowid
        cur.execute("INSERT INTO notes (site_id,body,created_at) VALUES (?,?,?)",
                    (site_id, "Initial site survey complete.", datetime.utcnow().isoformat()))
        cur.execute("INSERT INTO photos (site_id,filename,caption,created_at) VALUES (?,?,?,?)",
                    (site_id, random.choice(PHOTO_FILES), "Demo photo", datetime.utcnow().isoformat()))
        cur.execute("INSERT INTO job_notes (job_id,body,created_at) VALUES (?,?,?)",
                    (job_id, "Job initialized. Crew assigned.", datetime.utcnow().isoformat()))
        cur.execute("INSERT INTO job_photos (job_id,filename,caption,created_at) VALUES (?,?,?,?)",
                    (job_id, random.choice(PHOTO_FILES), "Job demo photo", datetime.utcnow().isoformat()))
        job_num += 1
    conn.commit(); conn.close()

# ---------- Customers schema ----------
def ensure_customers_schema():
    conn = db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            address TEXT,
            phone TEXT,
            email TEXT,
            notes TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            filename TEXT,
            caption TEXT,
            created_at TEXT
        )
    """)
    conn.commit(); conn.close()


def ensure_share_schema():
    conn = db(); cur = conn.cursor()
    cur.execute("""        CREATE TABLE IF NOT EXISTS share_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT,              -- 'customer' or 'job'
            target_id INTEGER,      -- customers.id or jobs.id
            token TEXT UNIQUE,
            created_at TEXT
        )
    """\)
    conn.commit(); conn.close()


def seed_customers_if_empty():
    sample = {
        "Washington": {"address":"100 Independence Ave, Washington, DC","phone":"(202) 555-0101","email":"ops@washington.example","notes":"Priority client."},
        "Lincoln": {"address":"16 Union Sq, Springfield, IL","phone":"(217) 555-0161","email":"contact@lincoln.example","notes":"Midwest projects."},
        "Jefferson": {"address":"1 Monticello Rd, Charlottesville, VA","phone":"(434) 555-0177","email":"service@jefferson.example","notes":"Historic sites focus."},
        "Roosevelt": {"address":"26 Rough Rider Way, NYC, NY","phone":"(212) 555-2600","email":"hello@roosevelt.example","notes":"Urban drilling."},
        "Kennedy": {"address":"35 Harbor Dr, Boston, MA","phone":"(617) 555-3500","email":"team@kennedy.example","notes":"Coastal/domestic."}
    }
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM customers")
    if cur.fetchone()[0] == 0:
        for name,info in sample.items():
            cur.execute("INSERT INTO customers (name,address,phone,email,notes,created_at) VALUES (?,?,?,?,?,?)",
                        (name, info.get("address",""), info.get("phone",""), info.get("email",""), info.get("notes",""), datetime.utcnow().isoformat()))
        conn.commit()
    conn.close()

# Initialize database and seeds
ensure_schema()
seed_demo_if_empty()
ensure_customers_schema()
seed_customers_if_empty()
ensure_share_schema()

# ---------- App init ----------
MAPTILER_KEY = os.environ.get("MAPTILER_KEY", "")
app = Flask(__name__, template_folder=os.path.join(BASE_DIR,"templates"), static_folder=os.path.join(BASE_DIR,"static"))
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")

# ---------- Static uploads ----------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ---------- Health ----------
@app.route("/healthz")
def healthz():
    try:
        conn = db(); conn.execute("SELECT 1"); conn.close()
        return "ok", 200
    except Exception as e:
        return f"not ok: {e}", 500

# ---------- Pages ----------
@app.route("/")
def index():
    return render_template("index.html", header_title="WellAtlas by Henry Suden", maptiler_key=MAPTILER_KEY)

@app.route("/deleted")
def deleted_sites():
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT * FROM sites WHERE deleted=1 ORDER BY datetime(created_at) DESC")
    rows = cur.fetchall(); conn.close()
    return render_template("deleted_sites.html", header_title="WellAtlas by Henry Suden", sites=rows)

@app.route("/site/<int:site_id>")
def site_detail(site_id):
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT * FROM sites WHERE id=?", (site_id,))
    site = cur.fetchone()
    if not site:
        conn.close(); return redirect(url_for("index"))
    cur.execute("SELECT * FROM jobs WHERE site_id=? AND deleted=0 ORDER BY datetime(created_at) DESC", (site_id,))
    jobs = cur.fetchall()
    cur.execute("SELECT * FROM notes WHERE site_id=? ORDER BY datetime(created_at) DESC", (site_id,))
    notes = cur.fetchall()
    cur.execute("SELECT * FROM photos WHERE site_id=? ORDER BY datetime(created_at) DESC", (site_id,))
    photos = cur.fetchall()
    conn.close()
    return render_template("site_detail.html", header_title="WellAtlas by Henry Suden", site=site, jobs=jobs, notes=notes, photos=photos, categories=CATEGORIES)

@app.route("/site/<int:site_id>/job/<int:job_id>")
def job_detail(site_id, job_id):
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT * FROM sites WHERE id=?", (site_id,)); site = cur.fetchone()
    cur.execute("SELECT * FROM jobs WHERE id=? AND site_id=?", (job_id, site_id)); job = cur.fetchone()
    if not site or not job:
        conn.close(); return redirect(url_for("site_detail", site_id=site_id))
    cur.execute("SELECT * FROM job_notes WHERE job_id=? ORDER BY datetime(created_at) DESC", (job_id,)); jnotes = cur.fetchall()
    cur.execute("SELECT * FROM job_photos WHERE job_id=? ORDER BY datetime(created_at) DESC", (job_id,)); jphotos = cur.fetchall()
    conn.close()
    return render_template("job_detail.html", header_title="WellAtlas by Henry Suden", site=site, job=job, jnotes=jnotes, jphotos=jphotos)

# ---------- Mutations ----------
@app.route("/site/<int:site_id>/edit", methods=["POST"])
def edit_site(site_id):
    name = (request.form.get("name") or "").strip()
    customer = (request.form.get("customer") or "").strip()
    description = (request.form.get("description") or "").strip()
    try:
        latitude = float(request.form.get("latitude") or 0.0)
        longitude = float(request.form.get("longitude") or 0.0)
    except ValueError:
        latitude, longitude = 0.0, 0.0
    conn = db(); cur = conn.cursor()
    cur.execute("UPDATE sites SET name=?, customer=?, description=?, latitude=?, longitude=? WHERE id=?",
                (name, customer, description, latitude, longitude, site_id))
    conn.commit(); conn.close()
    return redirect(url_for("site_detail", site_id=site_id))

@app.route("/site/<int:site_id>/delete", methods=["POST"])
def delete_site(site_id):
    conn = db(); cur = conn.cursor()
    cur.execute("UPDATE sites SET deleted=1 WHERE id=?", (site_id,))
    conn.commit(); conn.close()
    return redirect(url_for("index"))

@app.route("/site/<int:site_id>/restore", methods=["POST"])
def restore_site(site_id):
    conn = db(); cur = conn.cursor()
    cur.execute("UPDATE sites SET deleted=0 WHERE id=?", (site_id,))
    conn.commit(); conn.close()
    return redirect(url_for("deleted_sites"))

@app.route("/site/<int:site_id>/job/create", methods=["POST"])
def create_job(site_id):
    job_number = (request.form.get("job_number") or "").strip()
    job_category = (request.form.get("job_category") or "").strip()
    description = (request.form.get("description") or "").strip()
    if not job_number:
        job_number = str(int(datetime.utcnow().strftime("%y%j%H%M")) + random.randint(1,9))
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO jobs (site_id,job_number,job_category,description,created_at) VALUES (?,?,?,?,?)",
                (site_id, job_number, job_category, description, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return redirect(url_for("site_detail", site_id=site_id))

@app.route("/site/<int:site_id>/job/<int:job_id>/edit", methods=["POST"])
def edit_job(site_id, job_id):
    job_number = (request.form.get("job_number") or "").strip()
    job_category = (request.form.get("job_category") or "").strip()
    description = (request.form.get("description") or "").strip()
    conn = db(); cur = conn.cursor()
    cur.execute("UPDATE jobs SET job_number=?, job_category=?, description=? WHERE id=? AND site_id=?",
                (job_number, job_category, description, job_id, site_id))
    conn.commit(); conn.close()
    return redirect(url_for("job_detail", site_id=site_id, job_id=job_id))

@app.route("/site/<int:site_id>/job/<int:job_id>/delete", methods=["POST"])
def delete_job(site_id, job_id):
    conn = db(); cur = conn.cursor()
    cur.execute("UPDATE jobs SET deleted=1 WHERE id=? AND site_id=?", (job_id, site_id))
    conn.commit(); conn.close()
    return redirect(url_for("site_detail", site_id=site_id))

@app.route("/site/<int:site_id>/job/<int:job_id>/note", methods=["POST"])
def add_job_note(site_id, job_id):
    body = (request.form.get("body") or "").strip()
    if body:
        conn = db(); cur = conn.cursor()
        cur.execute("INSERT INTO job_notes (job_id,body,created_at) VALUES (?,?,?)",
                    (job_id, body, datetime.utcnow().isoformat()))
        conn.commit(); conn.close()
    return redirect(url_for("job_detail", site_id=site_id, job_id=job_id))

@app.route("/site/<int:site_id>/job/<int:job_id>/upload", methods=["POST"])
def upload_job_photo(site_id, job_id):
    file = request.files.get("photo")
    caption = (request.form.get("caption") or "").strip()
    if not file or file.filename == "":
        return redirect(url_for("job_detail", site_id=site_id, job_id=job_id))
    fname = file.filename
    base, ext = os.path.splitext(fname)
    uniq = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    fname = f"{base}_{uniq}{ext}"
    file.save(os.path.join(UPLOAD_DIR, fname))
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO job_photos (job_id,filename,caption,created_at) VALUES (?,?,?,?)",
                (job_id, fname, caption, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return redirect(url_for("job_detail", site_id=site_id, job_id=job_id))

# ---------- Customers pages & API ----------
@app.route("/customers")
def customers_index():
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT * FROM customers ORDER BY name ASC")
    customers = cur.fetchall(); conn.close()
    return render_template("customers.html", header_title="WellAtlas by Henry Suden", customers=customers)

@app.route("/customer/<int:cid>")
def customer_detail(cid):
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (cid,)); cust = cur.fetchone()
    if not cust:
        conn.close(); return redirect(url_for("customers_index"))
    cur.execute("SELECT * FROM sites WHERE customer=? AND deleted=0 ORDER BY name ASC", (cust["name"],))
    sites = cur.fetchall()
    cur.execute("SELECT * FROM customer_photos WHERE customer_id=? ORDER BY datetime(created_at) DESC", (cid,))
    photos = cur.fetchall()
    conn.close()
    return render_template("customer_detail.html", header_title="WellAtlas by Henry Suden",
                           customer=cust, sites=sites, photos=photos, categories=CATEGORIES)

@app.route("/customer/<int:cid>/upload", methods=["POST"])
def customer_upload(cid):
    file = request.files.get("photo")
    caption = (request.form.get("caption") or "").strip()
    if not file or file.filename == "":
        return redirect(url_for("customer_detail", cid=cid))
    fname = file.filename
    base, ext = os.path.splitext(fname)
    uniq = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    fname = f"{base}_{uniq}{ext}"
    file.save(os.path.join(UPLOAD_DIR, fname))
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO customer_photos (customer_id,filename,caption,created_at) VALUES (?,?,?,?)",
                (cid, fname, caption, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return redirect(url_for("customer_detail", cid=cid))

@app.route("/api/customers")
def api_customers():
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT id, name FROM customers ORDER BY name ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

# ---------- API: sites (search/filter) ----------
@app.route("/api/sites")
def api_sites():
    q = (request.args.get("q") or "").strip()
    job = (request.args.get("job") or "").strip()
    cust = (request.args.get("customer") or "").strip()
    conn = db(); cur = conn.cursor()
    clauses = ["s.deleted=0"]
    params = []
    if q:
        clauses.append("(s.name LIKE ? OR s.description LIKE ? OR s.id IN (SELECT site_id FROM notes WHERE body LIKE ?))")
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if job:
        clauses.append("EXISTS (SELECT 1 FROM jobs j WHERE j.site_id=s.id AND j.deleted=0 AND j.job_category=? )")
        params.append(job)
    if cust:
        clauses.append("s.customer=?")
        params.append(cust)
    sql = "SELECT s.* FROM sites s WHERE " + " AND ".join(clauses) + " ORDER BY datetime(s.created_at) DESC"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


# ---------- Share links (create) ----------
@app.route("/customer/<int:cid>/share", methods=["POST"])
def create_customer_share(cid):
    token = secrets.token_urlsafe(16)
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO share_tokens (kind,target_id,token,created_at) VALUES (?,?,?,?)",
                ("customer", cid, token, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return jsonify({"url": url_for("share_customer_view", token=token, _external=True)})

@app.route("/site/<int:site_id>/job/<int:job_id>/share", methods=["POST"])
def create_job_share(site_id, job_id):
    token = secrets.token_urlsafe(16)
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO share_tokens (kind,target_id,token,created_at) VALUES (?,?,?,?)",
                ("job", job_id, token, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return jsonify({"url": url_for("share_job_view", token=token, _external=True)})


# ---------- Share links (read-only views) ----------
@app.route("/s/customer/<token>")
def share_customer_view(token):
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT * FROM share_tokens WHERE token=? AND kind='customer'", (token,))
    t = cur.fetchone()
    if not t:
        conn.close(); return "Invalid or expired link", 404
    cur.execute("SELECT * FROM customers WHERE id=?", (t["target_id"],)); cust = cur.fetchone()
    cur.execute("SELECT * FROM sites WHERE customer=? AND deleted=0 ORDER BY name ASC", (cust["name"],))
    sites = cur.fetchall()
    # For each site, gather its jobs
    site_jobs = {}
    for s in sites:
        cur.execute("SELECT * FROM jobs WHERE site_id=? AND deleted=0 ORDER BY datetime(created_at) DESC", (s["id"],))
        site_jobs[s["id"]] = cur.fetchall()
    conn.close()
    return render_template("share_customer.html", header_title="WellAtlas by Henry Suden", customer=cust, sites=sites, site_jobs=site_jobs)

@app.route("/s/job/<token>")
def share_job_view(token):
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT * FROM share_tokens WHERE token=? AND kind='job'", (token,))
    t = cur.fetchone()
    if not t:
        conn.close(); return "Invalid or expired link", 404
    cur.execute("SELECT * FROM jobs WHERE id=?", (t["target_id"],)); job = cur.fetchone()
    cur.execute("SELECT * FROM sites WHERE id=?", (job["site_id"],)); site = cur.fetchone()
    cur.execute("SELECT * FROM job_notes WHERE job_id=? ORDER BY datetime(created_at) DESC", (job["id"],)); jnotes = cur.fetchall()
    cur.execute("SELECT * FROM job_photos WHERE job_id=? ORDER BY datetime(created_at) DESC", (job["id"],)); jphotos = cur.fetchall()
    conn.close()
    return render_template("share_job.html", header_title="WellAtlas by Henry Suden", site=site, job=job, jnotes=jnotes, jphotos=jphotos)
