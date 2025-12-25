from flask import *
import os, json, subprocess, zipfile, psutil, time

app = Flask(__name__)
app.secret_key = "devil-cloud"

DATA = "data/bots.json"
os.makedirs("bots", exist_ok=True)
os.makedirs("data", exist_ok=True)
if not os.path.exists(DATA): open(DATA,"w").write("{}")

def load(): return json.load(open(DATA))
def save(d): json.dump(d,open(DATA,"w"),indent=2)

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form.get("password")=="admin":
            session["admin"]=True
            return redirect("/dashboard")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("admin"): return redirect("/")
    return render_template("dashboard.html", bots=load())

@app.route("/upload", methods=["POST"])
def upload():
    if not session.get("admin"): return redirect("/")
    f=request.files["bot"]
    name=f.filename.replace(" ","_")
    path="bots/"+name
    f.save(path)

    runfile=name
    if name.endswith(".zip"):
        folder=name.replace(".zip","")
        os.makedirs("bots/"+folder, exist_ok=True)
        with zipfile.ZipFile(path) as z: z.extractall("bots/"+folder)
        os.remove(path)
        runfile=folder+"/main.py"

    bots=load()
    bots[runfile]={"status":"stopped","pid":None,"logs":[]}
    save(bots)
    return redirect("/dashboard")

@app.route("/start/<path:name>")
def start(name):
    bots=load()
    logfile=f"bots/{name.replace('/','_')}.log"
    with open(logfile,"a") as lg:
        p=subprocess.Popen(["python3","bots/"+name], stdout=lg, stderr=lg)
    bots[name]["pid"]=p.pid
    bots[name]["status"]="running"
    save(bots)
    return redirect("/dashboard")

@app.route("/stop/<path:name>")
def stop(name):
    bots=load()
    try: psutil.Process(bots[name]["pid"]).kill()
    except: pass
    bots[name]["status"]="stopped"
    save(bots)
    return redirect("/dashboard")

@app.route("/logs/<path:name>")
def logs(name):
    logfile=f"bots/{name.replace('/','_')}.log"
    text=""
    if os.path.exists(logfile):
        text=open(logfile).read()[-5000:]
    return render_template("logs.html", name=name, logs=text)

app.run(host="0.0.0.0", port=10000)
