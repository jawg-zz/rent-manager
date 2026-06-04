#!/usr/bin/env python3
"""Rent Manager - Dokploy Deploy Script"""
import secrets, json, sys, os, subprocess, time, urllib.parse

API_URL = "https://main.spidmax.win/api/trpc"
API_KEY = ""
COMPOSE_NAME = "rent-manager"
ENV_ID = "WGaDZpZTZQmIHcsDH9DC1"
DOMAIN = "rent.spidmax.win"
GH_ID = "PMSAtZevjGnzHLzzgbjCR"

# Read API key from file
for p in [os.path.expanduser("~/.dokploy-token"), "/tmp/.dokploy-token"]:
    if os.path.exists(p):
        with open(p) as f:
            API_KEY = f.read().strip()
        break

if not API_KEY:
    print("ERROR: No API key found")
    sys.exit(1)


def post(endpoint, data):
    payload = {"0": {"json": data}}
    tmp = "/tmp/dp_payload.json"
    with open(tmp, "w") as f:
        json.dump(payload, f)
    r = subprocess.run([
        "curl", "-s", "-X", "POST",
        API_URL + "/" + endpoint + "?batch=1",
        "-H", "Content-Type: application/json",
        "-H", "x-api-key: " + API_KEY,
        "-d", "@" + tmp],
        capture_output=True, text=True)
    if r.returncode != 0:
        print("  curl error")
        return None
    try:
        d = json.loads(r.stdout)
        if isinstance(d, list) and d:
            item = d[0]
            if "error" in item:
                print("  API: " + item["error"]["json"]["message"][:200])
                return None
            return item.get("result", {}).get("data", {}).get("json")
    except Exception:
        print("  Bad response")
    return None


def get(endpoint, params):
    inp = urllib.parse.quote(json.dumps(params))
    url = API_URL + "/" + endpoint + "?input=" + inp
    r = subprocess.run([
        "curl", "-s", url,
        "-H", "x-api-key: " + API_KEY],
        capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        return d.get("result", {}).get("data", {}).get("json")
    except Exception:
        return None


def find_compose():
    r = get("compose.search", {"json": {"name": COMPOSE_NAME}})
    if not r or "items" not in r:
        return None
    for i in r["items"]:
        if i["name"] == COMPOSE_NAME:
            return i["composeId"]
    return None


def create_compose():
    print("Creating stack...")
    r = post("compose.create", {
        "name": COMPOSE_NAME,
        "description": "Rent Manager SaaS",
        "environmentId": ENV_ID,
        "sourceType": "github",
        "repository": COMPOSE_NAME,
        "owner": "jawg-zz",
        "branch": "main",
        "triggerType": "push",
        "autoDeploy": True,
        "githubId": GH_ID,
        "composePath": "./docker-compose.yml",
        "isolatedDeployment": True,
        "isolatedDeploymentsVolume": True,
    })
    if r:
        print("  Created: " + r["composeId"])
        return r["composeId"]
    return None


def set_domain(cid):
    print("Domain...")
    existing = get("domain.byComposeId", {"json": {"composeId": cid}})
    if existing and len(existing) > 0:
        print("  OK: " + existing[0]["host"])
        return True
    r = post("domain.create", {
        "host": DOMAIN, "port": 5000,
        "composeId": cid, "serviceName": "app",
        "https": True, "certificateType": "letsencrypt", "path": "/"
    })
    return r is not None


def set_env(cid):
    print("Setting env vars...")
    pw = secrets.token_urlsafe(24)
    sk = secrets.token_urlsafe(48)
    db_url = "postgresql://rent_user:" + pw + "@db:5432/rent_manager"
    env = "DATABASE_URL=" + db_url
    env += chr(10) + "SECRET_KEY=" + sk
    env += chr(10) + "DEMO_MODE=true"
    env += chr(10) + "DB_PASSWORD=" + pw
    r = post("compose.saveEnvironment", {"composeId": cid, "env": env})
    if r:
        print("  Saved")
        return True
    return False


def deploy(cid):
    print("Deploying...")
    r = post("compose.deploy", {"composeId": cid, "type": "deploy"})
    if r and r.get("success"):
        print("  Queued")
        return True
    return False


def wait(cid, timeout=120):
    print("Waiting...")
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = get("compose.one", {"json": {"composeId": cid}})
        if r:
            s = r.get("composeStatus", "?")
            if s == "done":
                print("  Done (" + str(int(time.time()-t0)) + "s)")
                return True
            if s == "error":
                print("  Failed!")
                return False
        time.sleep(5)
    print("  Timeout")
    return False


def verify():
    print("Verifying...")
    r = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "https://rent.spidmax.win/"],
        capture_output=True, text=True)
    c = r.stdout.strip()
    if c in ("200", "302"):
        print("  LIVE (HTTP " + c + ")")
        return True
    print("  HTTP " + c)
    return False


def main():
    print("=" * 50)
    print("Rent Manager - Dokploy Deploy")
    print("=" * 50)
    cid = os.environ.get("COMPOSE_ID")
    if not cid:
        cid = find_compose()
    if not cid:
        cid = create_compose()
        if not cid:
            sys.exit(1)
    else:
        print("Stack: " + cid)
    if not set_env(cid):
        sys.exit(1)
    set_domain(cid)
    if not deploy(cid):
        sys.exit(1)
    if not wait(cid):
        sys.exit(1)
    verify()
    print("")
    print("=" * 50)
    print("Done! https://rent.spidmax.win")
    print("=" * 50)


if __name__ == "__main__":
    main()