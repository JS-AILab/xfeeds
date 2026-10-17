"""Alert when Hot Aisle has 4-GPU or 8-GPU machines available.

Polls the Hot Aisle API (the same endpoints dstack/gpuhunt use) and sends a
notification when a 4x or 8x GPU VM / bare-metal box goes from unavailable to
available. State is kept in hotaisle_state.json so you get one alert per
opening, not one per poll.

Env (or put KEY=value lines in hotaisle.env next to this script):
  HOTAISLE_API_KEY       API token (Hot Aisle admin TUI: ssh admin.hotaisle.app)
  HOTAISLE_TEAM_HANDLE   your team handle
  HOTAISLE_GPU_COUNTS    GPU counts to watch, default "4,8"
  NTFY_TOPIC             ntfy.sh topic to push to (phone app: ntfy)  [optional]
  SLACK_WEBHOOK_URL / DISCORD_WEBHOOK_URL                            [optional]
  TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID                              [optional]
  WHATSAPP_PHONE + CALLMEBOT_API_KEY  WhatsApp via callmebot.com     [optional]
  MAC_ALERT=0            turn off the loud sound + pop-up on macOS (on by default)

Usage:
  python3 hotaisle_alert.py            check once (for cron / GitHub Actions)
  python3 hotaisle_alert.py --loop 120 check every 120 seconds
  python3 hotaisle_alert.py --loop 120 --for 840   same, but stop after 840 seconds
  python3 hotaisle_alert.py --test     send a test notification and exit
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(HERE, "hotaisle.env")
if os.path.exists(ENV_FILE):
    for line in open(ENV_FILE):
        k, sep, v = line.strip().partition("=")
        if sep and not k.startswith("#"):
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

API = "https://admin.hotaisle.app/api"
STATE = os.environ.get("HOTAISLE_STATE", os.path.join(HERE, "hotaisle_state.json"))
WANT = {int(n) for n in os.environ.get("HOTAISLE_GPU_COUNTS", "4,8").split(",") if n.strip()}

def get(path):
    req = urllib.request.Request(API + path, headers={
        "accept": "application/json", "Authorization": "Token " + os.environ["HOTAISLE_API_KEY"]})
    return json.load(urllib.request.urlopen(req, timeout=30))

def available():
    """Return {key: description} for every available config with a watched GPU count."""
    team, found, errors = os.environ["HOTAISLE_TEAM_HANDLE"], {}, []
    for kind in ("virtual_machines", "bare_metal"):
        try:
            items = get(f"/teams/{team}/{kind}/available/")
        except Exception as e:
            errors.append(f"{kind}: {e}")
            continue
        if isinstance(items, dict):  # tolerate a wrapped list
            items = items.get("results") or items.get("data") or list(items.values())
        for it in items or []:
            specs = it.get("Specs") or it.get("specs") or {}
            gpus = specs.get("gpus") or []
            if not gpus:
                continue
            count, model = gpus[0].get("count", 0), gpus[0].get("model", "GPU")
            if count not in WANT:
                continue
            price = it.get("OnDemandPrice", it.get("on_demand_price"))
            label = "bare metal" if kind == "bare_metal" else "VM"
            desc = f"{count}x {model} {label}"
            if price is not None:
                desc += f" @ ${price / 100:.2f}/hr"
            found[f"{kind}:{count}x{model}"] = desc
    if len(errors) == 2:
        raise RuntimeError("; ".join(errors))
    for e in errors:
        print("warning:", e, file=sys.stderr)
    return found

def post(url, payload, headers=None):
    data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    h = {"Content-Type": "application/json"} if not isinstance(payload, bytes) else {}
    urllib.request.urlopen(urllib.request.Request(url, data=data, headers={**h, **(headers or {})}), timeout=20)

def mac_alert(title, body):
    """Max volume, loud repeated sound, spoken message and a pop-up that stays until dismissed."""
    esc = lambda t: t.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    subprocess.run(["osascript", "-e", "set volume output volume 100 without output muted"], check=False)
    subprocess.run(["osascript", "-e", f'display notification "{esc(body)}" with title "{esc(title)}" sound name "Sosumi"'], check=False)
    subprocess.Popen(["osascript", "-e", f'display alert "{esc(title)}" message "{esc(body)}" as critical'])
    for _ in range(6):
        subprocess.run(["afplay", "/System/Library/Sounds/Sosumi.aiff"], check=False)
    subprocess.run(["say", title], check=False)

def notify(title, body):
    print(f"{title}\n{body}")
    sent, env = 0, os.environ.get
    channels = [
        (sys.platform == "darwin" and env("MAC_ALERT", "1") != "0", lambda: mac_alert(title, body)),
        (env("NTFY_TOPIC"), lambda: post(f"https://ntfy.sh/{env('NTFY_TOPIC')}", body.encode(),
            {"Title": title, "Priority": "high", "Tags": "rotating_light",
             "Click": "https://hotaisle.xyz"})),
        (env("SLACK_WEBHOOK_URL"), lambda: post(env("SLACK_WEBHOOK_URL"), {"text": f"*{title}*\n{body}"})),
        (env("DISCORD_WEBHOOK_URL"), lambda: post(env("DISCORD_WEBHOOK_URL"), {"content": f"**{title}**\n{body}"})),
        (env("TELEGRAM_BOT_TOKEN") and env("TELEGRAM_CHAT_ID"), lambda: post(
            f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/sendMessage",
            {"chat_id": env("TELEGRAM_CHAT_ID"), "text": f"{title}\n{body}"})),
        (env("WHATSAPP_PHONE") and env("CALLMEBOT_API_KEY"), lambda: urllib.request.urlopen(
            "https://api.callmebot.com/whatsapp.php?" + urllib.parse.urlencode(
                {"phone": env("WHATSAPP_PHONE"), "text": f"{title}\n{body}", "apikey": env("CALLMEBOT_API_KEY")}),
            timeout=30)),
    ]
    for enabled, send in channels:
        if enabled:
            try:
                send()
                sent += 1
            except Exception as e:
                print("notify failed:", e, file=sys.stderr)
    if not sent:
        print("(no notification channel configured; set NTFY_TOPIC, WhatsApp or a webhook)", file=sys.stderr)

def check():
    now = available()
    try:
        before = set(json.load(open(STATE)))
    except (OSError, ValueError):
        before = set()
    new = {k: v for k, v in now.items() if k not in before}
    if new:
        notify("Hot Aisle GPUs available", "\n".join(sorted(new.values())) + "\nhttps://hotaisle.xyz")
    else:
        print(time.strftime("%H:%M:%S"), "no new openings;", "available:", sorted(now.values()) or "none")
    json.dump(sorted(now), open(STATE, "w"))

if __name__ == "__main__":
    if "--test" in sys.argv:
        notify("Hot Aisle alert test", "Notifications are working.")
    elif "--loop" in sys.argv:
        i = sys.argv.index("--loop")
        every = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 120
        stop = time.time() + int(sys.argv[sys.argv.index("--for") + 1]) if "--for" in sys.argv else float("inf")
        while True:
            try:
                check()
            except Exception as e:
                print("check failed:", e, file=sys.stderr)
            if time.time() + every > stop:
                break
            time.sleep(every)
    else:
        check()
