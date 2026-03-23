#!/usr/bin/env python3
"""
openclaw-settings-sync: Reads /dev/shm/claude_settings.json (and optionally
/dev/shm/sandbox_metadata.json) and populates the LiteLLM base URL, API key,
and model into the OpenClaw configuration file.

Runs agressively on start, then every 30 seconds.
"""

import json
import re
import time
import hashlib

SERVICE_NAME = "openclaw-settings-sync"
CLAUDE_SETTINGS_PATH = "/dev/shm/claude_settings.json"
SANDBOX_METADATA_PATH = "/dev/shm/sandbox_metadata.json"
OPENCLAW_CONFIG_PATH = "/workspace/openclaw-whatsapp/openclaw-configuration/openclaw.json"
POLL_INTERVAL = 30
STARTUP_POLL_INTERVAL = 1
STARTUP_TIMEOUT = 60


def read_json_file(path, quiet=False):
    """Read and parse a JSON file, returning None on failure."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        if not quiet:
            print(f"[{SERVICE_NAME}] Warning: File not found: {path}", flush=True)
        return None
    except (json.JSONDecodeError, PermissionError) as e:
        if not quiet:
            print(f"[{SERVICE_NAME}] Warning: Could not read {path}: {e}", flush=True)
        return None


def file_hash(path):
    """Return SHA256 hash of file contents, or None if unreadable."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (FileNotFoundError, PermissionError):
        return None


def get_settings(quiet=False):
    """
    Extract LiteLLM settings from claude_settings.json and sandbox_metadata.json.
    Returns a dict with keys: base_url, api_key, model_id, or None if unavailable.
    When quiet=True, suppresses warnings for missing files (used during startup polling).
    """
    claude = read_json_file(CLAUDE_SETTINGS_PATH, quiet=quiet)
    if not claude:
        return None

    env = claude.get("env", {})
    api_key = env.get("ANTHROPIC_AUTH_TOKEN")
    base_url = env.get("ANTHROPIC_BASE_URL")
    model_id = env.get("ANTHROPIC_MODEL")

    if not all([api_key, base_url, model_id]):
        if not quiet:
            print(f"[{SERVICE_NAME}] Warning: Missing required fields in claude_settings.json", flush=True)
        return None

    # Check for model override in sandbox_metadata.json
    metadata = read_json_file(SANDBOX_METADATA_PATH, quiet=quiet)
    if metadata and metadata.get("litellm_selected_model"):
        override_model = metadata["litellm_selected_model"]
        print(f"[{SERVICE_NAME}] Using model override from sandbox_metadata.json: {override_model}", flush=True)
        model_id = override_model

    return {
        "base_url": base_url,
        "api_key": api_key,
        "model_id": model_id,
    }


def replace_json5_value(content, pattern, replacement):
    """
    Replace a value in JSON5 content using a regex pattern.
    The pattern should capture everything before the value to replace.
    """
    return re.sub(pattern, replacement, content)


def update_config(settings):
    """
    Update the OpenClaw configuration file with the provided settings.
    Uses regex-based replacement to preserve JSON5 comments and formatting.
    """
    try:
        with open(OPENCLAW_CONFIG_PATH, "r") as f:
            content = f.read()
    except (FileNotFoundError, PermissionError) as e:
        print(f"[{SERVICE_NAME}] Error: Could not read config: {e}", flush=True)
        return False

    original_content = content
    base_url = settings["base_url"]
    api_key = settings["api_key"]
    model_id = settings["model_id"]

    # 1. Update env.LITELLM_API_KEY
    content = re.sub(
        r'(LITELLM_API_KEY:\s*)"[^"]*"',
        rf'\1"{api_key}"',
        content,
    )

    # 2. Update models.providers.litellm.baseUrl
    content = re.sub(
        r'(baseUrl:\s*)"[^"]*"',
        rf'\1"{base_url}"',
        content,
        count=1,  # Only the first occurrence (litellm provider)
    )

    # 3. Update models.providers.litellm.models[0].id
    content = re.sub(
        r'(models:\s*\[\s*\{[^}]*?id:\s*)"[^"]*"',
        rf'\1"{model_id}"',
        content,
        count=1,
    )

    # 4. Update models.providers.litellm.models[0].name
    content = re.sub(
        r'(models:\s*\[\s*\{[^}]*?name:\s*)"[^"]*"',
        rf'\1"{model_id}"',
        content,
        count=1,
    )

    # 5. Update agents.defaults.model.primary
    content = re.sub(
        r'(primary:\s*)"[^"]*"',
        rf'\1"litellm/{model_id}"',
        content,
        count=1,
    )

    if content == original_content:
        print(f"[{SERVICE_NAME}] No changes needed in config.", flush=True)
        return False

    try:
        with open(OPENCLAW_CONFIG_PATH, "w") as f:
            f.write(content)
        print(f"[{SERVICE_NAME}] Config updated: base_url={base_url}, model={model_id}", flush=True)
        return True
    except (PermissionError, OSError) as e:
        print(f"[{SERVICE_NAME}] Error: Could not write config: {e}", flush=True)
        return False


def sync_once():
    """Perform a single sync cycle. Returns True if config was updated."""
    settings = get_settings()
    if not settings:
        print(f"[{SERVICE_NAME}] No valid settings found, skipping.", flush=True)
        return False
    return update_config(settings)


def wait_for_settings():
    """
    Aggressively poll for settings files every 1 second at startup.
    Returns True if settings were found and synced within the timeout,
    False if the timeout was reached without finding valid settings.
    """
    print(f"[{SERVICE_NAME}] Waiting for source files (polling every {STARTUP_POLL_INTERVAL}s, "
          f"timeout {STARTUP_TIMEOUT}s)...", flush=True)

    elapsed = 0
    while elapsed < STARTUP_TIMEOUT:
        settings = get_settings(quiet=True)
        if settings:
            print(f"[{SERVICE_NAME}] Source files found after {elapsed}s.", flush=True)
            update_config(settings)
            return True
        time.sleep(STARTUP_POLL_INTERVAL)
        elapsed += STARTUP_POLL_INTERVAL

    print(f"[{SERVICE_NAME}] Timeout reached ({STARTUP_TIMEOUT}s) — source files not found. "
          f"Continuing with normal polling.", flush=True)
    return False


def main():
    print(f"[{SERVICE_NAME}] Starting openclaw-settings-sync service.", flush=True)
    print(f"[{SERVICE_NAME}] Watching: {CLAUDE_SETTINGS_PATH}", flush=True)
    print(f"[{SERVICE_NAME}] Watching: {SANDBOX_METADATA_PATH}", flush=True)
    print(f"[{SERVICE_NAME}] Target:   {OPENCLAW_CONFIG_PATH}", flush=True)
    print(f"[{SERVICE_NAME}] Interval: {POLL_INTERVAL}s (startup: {STARTUP_POLL_INTERVAL}s)", flush=True)

    # Startup phase: aggressively poll until settings are available or timeout
    settings = get_settings(quiet=True)
    if settings:
        print(f"[{SERVICE_NAME}] Source files already available, syncing immediately.", flush=True)
        update_config(settings)
    else:
        wait_for_settings()

    # Track file hashes to detect changes
    last_claude_hash = file_hash(CLAUDE_SETTINGS_PATH)
    last_metadata_hash = file_hash(SANDBOX_METADATA_PATH)

    # Normal poll loop
    print(f"[{SERVICE_NAME}] Entering normal polling mode (every {POLL_INTERVAL}s).", flush=True)
    while True:
        time.sleep(POLL_INTERVAL)

        current_claude_hash = file_hash(CLAUDE_SETTINGS_PATH)
        current_metadata_hash = file_hash(SANDBOX_METADATA_PATH)

        if (current_claude_hash != last_claude_hash or
                current_metadata_hash != last_metadata_hash):
            print(f"[{SERVICE_NAME}] Source file change detected, syncing...", flush=True)
            sync_once()
            last_claude_hash = current_claude_hash
            last_metadata_hash = current_metadata_hash


if __name__ == "__main__":
    main()
