from flask import *
import os, json, subprocess, zipfile, psutil, re

app = Flask(__name__)
app.secret_key = "devil-cloud"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOTS_DIR = os.path.join(BASE_DIR, "bots")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "bots.json")

os.makedirs(BOTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(DATA_FILE):
    open(DATA_FILE, "w").write("{}")

def load():
    try:
        return json.load(open(DATA_FILE))
    except:
        return {}

def save(d):
    json.dump(d, open(DATA_FILE, "w"), indent=2)

# -------------------------------
# AUTO DEPENDENCY INSTALLER
# -------------------------------
def auto_install(runfile):
    path = os.path.join(BOTS_DIR, runfile)
    if not os.path.exists(path): 
        return
    try:
        text = open(path, "r", encoding="utf-8", errors="ignore").read()
    except:
        return

    libs = set()
    for line in text.splitlines():
        line = line.strip()
        # import x, y as z
        if line.startswith("import "):
            parts = re.split(r"[ ,]+", line.replace("import ", ""))
            for p in parts:
                if p and p not in ("as",):
                    libs.add(p.split(".")[0])
        # from x.y import a
        if line.startswith("from "):
            m = re.match(r"from\s+([a-zA-Z0-9_\.]+)\s+import", line)
            if m:
                libs.add(m.group(1).split(".")[0])

    # blacklist builtins
    blacklist = {"os","sys","time","json","re","math","random","subprocess","threading","asyncio"}
    libs = {l for l in libs if l and l not in blacklist}

    for lib in libs:
        os.system(f"pip install -q {lib}")

# -------------------------------
# ROUTES
# -------------------------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == "admin":
            session["admin"] = True
            return redirect("/dashboard")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("admin"): 
        return redirect("/")
    return render_template("dashboard.html", bots=load())

@app.route("/upload", methods=["POST"])
def upload():
    if not session.get("admin"): 
        return redirect("/")
    f = request.files.get("bot")
    if not f: 
        return redirect("/dashboard")

    name = f.filename.replace(" ", "_")
    save_path = os.path.join(BOTS_DIR, name)
    f.save(save_path)

    runfile = name
    # ZIP SUPPORT (expects main.py inside)
    if name.lower().endswith(".zip"):
        folder = name[:-4]
        extract_dir = os.path.join(BOTS_DIR, folder)
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(save_path) as z:
            z.extractall(extract_dir)
        os.remove(save_path)
        runfile = f"{folder}/main.py"

    # auto install dependencies from code
    auto_install(runfile)

    bots = load()
    bots[runfile] = {"status":"stopped","pid":None}
    save(bots)
    return redirect("/dashboard")

@app.route("/start/<path:name>")
def start(name):
    if not session.get("admin"): 
        return redirect("/")
    bots = load()
    logfile = os.path.join(BOTS_DIR, name.replace("/","_") + ".log")
    os.makedirs(os.path.dirname(logfile), exist_ok=True)
    with open(logfile, "a") as lg:
        p = subprocess.Popen(
            ["python3", os.path.join(BOTS_DIR, name)],
            stdout=lg, stderr=lg
        )
    bots[name]["pid"] = p.pid
    bots[name]["status"] = "running"
    save(bots)
    return redirect("/dashboard")

@app.route("/stop/<path:name>")
def stop(name):
    if not session.get("admin"): 
        return redirect("/")
    bots = load()
    try:
        psutil.Process(bots[name]["pid"]).kill()
    except:
        pass
    bots[name]["status"] = "stopped"
    save(bots)
    return redirect("/dashboard")

@app.route("/logs/<path:name>")
def logs(name):
    if not session.get("admin"): 
        return redirect("/")
    logfile = os.path.join(BOTS_DIR, name.replace("/","_") + ".log")
    text = ""
    if os.path.exists(logfile):
        try:
            text = open(logfile, "r", errors="ignore").read()[-8000:]
        except:
            text = ""
    return render_template("logs.html", name=name, logs=text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
