import psutil, json, subprocess, time, os

DATA="data/bots.json"

while True:
    if not os.path.exists(DATA):
        time.sleep(5); continue
    bots=json.load(open(DATA))
    for b in bots:
        if bots[b]["status"]=="running":
            pid=bots[b]["pid"]
            if not psutil.pid_exists(pid):
                logfile=f"bots/{b.replace('/','_')}.log"
                with open(logfile,"a") as lg:
                    p=subprocess.Popen(["python3","bots/"+b], stdout=lg, stderr=lg)
                bots[b]["pid"]=p.pid
                json.dump(bots,open(DATA,"w"),indent=2)
    time.sleep(10)
