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
2. Pick a notification channel. The easiest is [ntfy](https://ntfy.sh): install the app, subscribe to a hard-to-guess topic name, and set `NTFY_TOPIC` to it. Slack, Discord, Telegram and WhatsApp (via [CallMeBot](https://www.callmebot.com/blog/free-api-whatsapp-messages/): set `WHATSAPP_PHONE` like `+15551234567` and `CALLMEBOT_API_KEY`) also work (see the script header).
3. Put your settings in `hotaisle.env` next to the script (it is git-ignored, so it never gets committed):
   ```
   HOTAISLE_API_KEY=...
   HOTAISLE_TEAM_HANDLE=...
   WHATSAPP_PHONE=+15551234567
   CALLMEBOT_API_KEY=...
   ```
4. Run it on a machine that stays on: `python3 hotaisle_alert.py --loop 120` checks every 2 minutes. To keep it running after you close the terminal: `nohup python3 hotaisle_alert.py --loop 120 > hotaisle.log 2>&1 &`.

The GitHub Actions workflow (`.github/workflows/hotaisle-alert.yml`) is manual-only, because a 2-minute schedule would use more Actions minutes than a private repo's free plan includes.

`python3 hotaisle_alert.py --test` sends a test notification. Set `HOTAISLE_GPU_COUNTS` (default `4,8`) to watch other sizes.
