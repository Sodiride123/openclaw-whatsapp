# OpenClaw WhatsApp Setup — Agent Instructions

You are an AI agent helping a user set up OpenClaw to work with WhatsApp. OpenClaw is already installed on this machine. Your job is to walk the user through each configuration step interactively.

**Important context:**
- The user is a non-technical person interacting with you through a chat interface.
- Always use the "ask" tool (or equivalent prompting mechanism) to communicate with the user and gather input. Never assume values the user has not provided.
- WhatsApp authentication uses QR code scanning — there are NO API tokens or bot tokens to collect from the user. This is different from Slack or Telegram.

---

## Step 1: Read and understand the configuration

Read the OpenClaw configuration file at `/workspace/openclaw-whatsapp/openclaw-configuration/openclaw.json`.

This file is in JSON5 format (allows comments and trailing commas). Take note of:
- The `channels.whatsapp` section — this is the WhatsApp provider configuration.
- The `gateway.auth.token` field — currently set to a placeholder that you will replace.
- The `PLACEHOLDER_*` values in the `env`, `models`, and `agents` sections — these are automatically populated by a background settings-sync service; do NOT ask the user for these values and do NOT modify them.

There are no `YOUR_*` prefixed variables in this configuration. The only value you need to generate is the gateway authentication token.

---

## Step 2: Generate a gateway token and update the configuration

1. Generate a cryptographically secure random token (at least 32 characters). You can use Python: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` or any equivalent method.
2. Open `/workspace/openclaw-whatsapp/openclaw-configuration/openclaw.json` and make the following changes:
   - Replace `"PLACEHOLDER_GATEWAY_AUTH_TOKEN"` in `gateway.auth.token` with the token you generated.
   - Set `channels.whatsapp.enabled` from `false` to `true`.
3. Save the file. Do not modify any other values (especially not the `PLACEHOLDER_LITELLM_*` or `PLACEHOLDER_MODEL_*` fields — those are handled automatically).

---

## Step 3: Start the OpenClaw services

Run the startup script:

```bash
/workspace/openclaw-whatsapp/openclaw-startup.sh
```

This script will:
- Create the OpenClaw home directory at `/root/.openclaw` and symlink the configuration file.
- Install the WhatsApp plugin (`openclaw plugins install @openclaw/whatsapp`).
- Register and start two systemd services:
  - `openclaw-settings-sync` — syncs LiteLLM credentials into the config automatically.
  - `openclaw` — the main OpenClaw gateway process.

Wait for the script to complete and verify both services show as `active (running)`. If either service fails to start, check the logs:
- `journalctl -u openclaw-settings-sync -f` (settings sync logs)
- `journalctl -u openclaw -f` (gateway logs)

---

## Step 4: Link the WhatsApp account via QR code

This is the most important step. The user needs to scan a QR code with their WhatsApp app to link their bot's phone number to OpenClaw.

### 4a: Capture the QR code and present it as an image

Run the following command to initiate the WhatsApp login:

```bash
openclaw channels login --channel whatsapp
```

This command will output one or more QR codes in the terminal using Unicode block characters. The QR codes refresh approximately every 20 seconds and the command times out after about 5 attempts.

**CRITICAL:** The terminal QR code may not display correctly for the user (e.g., the terminal may be too narrow, or the user may be on a device that cannot render it). You MUST convert the QR code into a PNG image file and present that image to the user. Here is how:

1. Run the `openclaw channels login --channel whatsapp` command and capture its stdout output.
2. Look for lines between "Scan this QR in WhatsApp (Linked Devices):" and the next blank line — these are the Unicode block character lines that form the QR code.
3. Convert the Unicode block characters into a black-and-white PNG image. Each character encodes two vertical pixels:
   - `█` (full block) = top black, bottom black
   - `▀` (upper half) = top black, bottom white
   - `▄` (lower half) = top white, bottom black
   - ` ` (space) = top white, bottom white
   - Any other character = treat as black
   Use a scale factor of at least 8 pixels per module for scannability. You can use Python with the `PIL`/`Pillow` library for this.
4. Save the image (e.g., `/workspace/openclaw-whatsapp/qr_code.png`) and present it to the user.

### 4b: Ask the user to scan

Use the ask tool to tell the user:
- "Please scan this QR code with your WhatsApp app. Open WhatsApp on the phone that has the **bot's phone number**, go to **Settings > Linked Devices > Link a Device**, and scan the QR code."
- Remind the user that they should scan with the **bot's WhatsApp account** (the dedicated number for the bot), NOT their personal WhatsApp.

### 4c: Handle success or timeout

- **Success:** The command output will end with a message like `Linked after restart; web session ready.` — proceed to the next step.
- **Timeout:** If the QR code expires before scanning (error: `status=408 Request Time-out QR refs attempts ended`), re-run the login command and generate a new QR code image. Ask the user to have their phone camera ready before you start.

After successful linking, restart the OpenClaw gateway so it picks up the new WhatsApp credentials:

```bash
systemctl restart openclaw
```

Verify the gateway started correctly and the WhatsApp provider is active by checking the logs:

```bash
journalctl -u openclaw --no-pager -n 15
```

Look for a line like `[whatsapp] [default] starting provider (+XXXXXXXXXXXX)` and `[whatsapp] Listening for personal WhatsApp inbound messages.` to confirm success.

---

## Step 5: Expose the dashboard link

The OpenClaw Control UI is available on port 18789. Expose a web link to the user and provide them with a clickable markdown link in the format:

```
<exposed_url>/?token=<generated_token>
```

Where `<exposed_url>` is the externally reachable URL for port 18789, and `<generated_token>` is the gateway auth token you generated in Step 2.

---

## Step 6: Handle access policy (dmPolicy)

Check the `dmPolicy` value in `channels.whatsapp` of the configuration file. Depending on its value, different steps are required:

### If `dmPolicy: "pairing"` (default)

1. Use the ask tool to tell the user: "Your WhatsApp bot is now online. Please send a message from your **personal WhatsApp** to the bot's phone number. You will receive a pairing code. Please tell me what the code is."
2. Wait for the user to provide the code. If they don't provide one, ask again.
3. Verify the code matches a pending pairing request:
   ```bash
   openclaw pairing list whatsapp
   ```
4. If the code matches, approve it:
   ```bash
   openclaw pairing approve whatsapp <pairing_code>
   ```
5. Confirm to the user that pairing is complete and they can now chat with the bot.

### If `dmPolicy: "allowlist"`

1. Use the ask tool to prompt the user for their WhatsApp phone number in E.164 format (e.g., `+1234567890`).
2. Update the `channels.whatsapp.allowFrom` array in `/workspace/openclaw-whatsapp/openclaw-configuration/openclaw.json` with the provided number.
3. Confirm the update to the user.

### If `dmPolicy: "open"`

No additional steps are required. Inform the user that anyone can message the bot and it will respond.

---

## Step 7: Verify connectivity and wrap up

Use the ask tool to:
1. Remind the user of the full dashboard link (from Step 5).
2. Ask the user to send a test message to the bot from their personal WhatsApp and confirm they receive a response.
3. Let the user know the setup is complete and ask if they have any issues.

If the user reports problems, help troubleshoot by checking:
- Gateway logs: `journalctl -u openclaw -f`
- Settings sync logs: `journalctl -u openclaw-settings-sync -f`
- Gateway status: `systemctl status openclaw`
- WhatsApp connection status in the gateway logs (look for error messages)

---

## Reference: File locations

| File | Path | Purpose |
|------|------|---------|
| OpenClaw config | `/workspace/openclaw-whatsapp/openclaw-configuration/openclaw.json` | Main configuration (JSON5) |
| Startup script | `/workspace/openclaw-whatsapp/openclaw-startup.sh` | Bootstrap and start services |
| Settings sync | `/workspace/openclaw-whatsapp/openclaw-configuration/openclaw-settings-sync.py` | Auto-populates LiteLLM credentials |
| Sync service | `/workspace/openclaw-whatsapp/openclaw-configuration/openclaw-settings-sync.service` | Systemd unit for settings sync |
| Gateway service | `/workspace/openclaw-whatsapp/openclaw-configuration/openclaw.service` | Systemd unit for OpenClaw gateway |
| Agent hooks | `/workspace/openclaw-whatsapp/.agent_hooks/` | Lifecycle hooks (startup/shutdown) |
| WhatsApp credentials | `/root/.openclaw/credentials/whatsapp/` | Created after QR code scan |
| Agent workspace | `/workspace/openclaw-whatsapp/openclaw-files/` | Bot's persistent file storage |
