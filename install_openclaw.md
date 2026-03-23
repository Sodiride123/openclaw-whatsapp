# Install OpenClaw — Prerequisites

Before running the WhatsApp setup, OpenClaw must be installed on the machine. OpenClaw requires **Node.js v22 or later**.

## 1. Ensure Node.js v22+ is installed

Check the current Node.js version:

```bash
node --version
```

If Node.js is not installed, or the version is below v22, install Node.js v22:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs
```

Verify after installation:

```bash
node --version
npm --version
```

`node --version` must show `v22.x.x` or higher before proceeding.

## 2. Install OpenClaw via npm

```bash
npm install -g openclaw@latest
```

This is a large package (~1.4 GB) and may take a few minutes to install.

## 3. Verify the installation

```bash
openclaw --version
```

You should see output like `OpenClaw 2026.x.x`. If the `openclaw` command is not found after installation, try running it with the full path:

```bash
/usr/lib/node_modules/openclaw/openclaw.mjs --version
```

If that works but `openclaw` doesn't, create a symlink:

```bash
ln -sf /usr/lib/node_modules/openclaw/openclaw.mjs /usr/bin/openclaw
```

echo "Installing WhatsApp plugin..."
```bash
openclaw plugins install @openclaw/whatsapp
```

Once `openclaw --version` returns successfully, proceed to `first_prompt_to_agent.md` for the WhatsApp setup steps.
