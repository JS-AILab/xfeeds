# xfeeds

Tools for watching the CLS Telegraph (财联社电报) feed for AI, chips, indium phosphide, photonics and lithography news.

- `fetch_cls.py`: the original script. It calls the CLS roll API directly. In sandboxes that block www.cls.cn it fails with a proxy 403.
- `sign_url.py`: builds signed CLS API URLs (`python3 sign_url.py <unix_time|now> [rows]`). The `category` parameter must be left out entirely; sending it empty gives errno 10012 (签名错误). These URLs can be read with a web-fetch tool when direct connections are blocked.
- `merge.py`: merges the per-time-slice results and checks the pages overlap with no gaps.
- `build.py`: renders the report and the `sent_alerts.md` log (expects `entries_*.py` with the written-up posts).
- `instructions/`: the step-by-step instructions given to the collection and verification passes.

Limits: the feed only goes back a few days through this API, and it does not include CLS paid-column content.

## Hot Aisle GPU alert

`hotaisle_alert.py` alerts when Hot Aisle has a 4-GPU or 8-GPU machine (VM or bare metal) available. It polls `admin.hotaisle.app/api/teams/<team>/{virtual_machines,bare_metal}/available/` and notifies once each time a config opens up.

1. Get an API token and team handle from Hot Aisle (`ssh admin.hotaisle.app`).
2. Pick a notification channel. The easiest is [ntfy](https://ntfy.sh): install the app, subscribe to a hard-to-guess topic name, and set `NTFY_TOPIC` to it. Slack, Discord and Telegram also work (see the script header).
3. Run it:
   - Locally: `HOTAISLE_API_KEY=... HOTAISLE_TEAM_HANDLE=... NTFY_TOPIC=... python3 hotaisle_alert.py --loop 120`
   - On GitHub Actions: add those values as repo secrets. `.github/workflows/hotaisle-alert.yml` checks every 2 minutes (each scheduled run loops for ~14 minutes, since GitHub's minimum schedule is 5 minutes); trigger it by hand once from the Actions tab to check it works.

`python3 hotaisle_alert.py --test` sends a test notification. Set `HOTAISLE_GPU_COUNTS` (default `4,8`) to watch other sizes.
