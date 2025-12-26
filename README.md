# VersionOps Agent

<p align="center">
  <img src="https://versionops.com/logo.png" alt="VersionOps" width="300">
</p>

<p align="center">
  <strong>Lightweight agent for application version discovery and reporting</strong>
</p>

<p align="center">
  <a href="https://github.com/versionops-platform/versionops-agent/releases/latest">
    <img src="https://img.shields.io/github/v/release/versionops-platform/versionops-agent" alt="Latest Release">
  </a>
  <a href="https://github.com/versionops-platform/versionops-agent/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License">
  </a>
  <a href="https://github.com/versionops-platform/versionops-agent/releases">
    <img src="https://img.shields.io/github/downloads/versionops-platform/versionops-agent/total" alt="Downloads">
  </a>
</p>

---

## Overview

VersionOps Agent is a lightweight daemon that runs on your Linux servers to automatically discover installed applications and report their versions to [VersionOps](https://versionops.com) — a version-aware infrastructure inventory platform.

### Features

- 🔍 **Auto-discovery** — Detects installed applications using multiple methods (package managers, binaries, systemd)
- 📊 **Version tracking** — Reports versions to VersionOps dashboard
- 🔒 **Secure** — Token-based authentication, minimal permissions required
- 🪶 **Lightweight** — Single binary, ~8MB, minimal resource usage
- 🔄 **Real-time** — Configurable reporting interval (default: 5 minutes)
- 🐧 **Cross-platform** — Supports `amd64` and `arm64` Linux architectures

---

## Quick Start

### One-line Installation

```bash
curl -fsSL https://get.versionops.com | sudo bash
```

### Manual Installation

1. **Download the binary** for your architecture:

```bash
# For x86_64 (amd64)
wget https://github.com/versionops-platform/versionops-agent/releases/latest/download/versionops-agent-linux-amd64

# For ARM64 (aarch64)
wget https://github.com/versionops-platform/versionops-agent/releases/latest/download/versionops-agent-linux-arm64
```

2. **Install the binary:**

```bash
sudo mv versionops-agent-linux-* /usr/local/bin/versionops-agent
sudo chmod +x /usr/local/bin/versionops-agent
```

3. **Configure the agent:**

```bash
sudo versionops-agent config --backend=https://app.versionops.com --token=YOUR_SERVICE_TOKEN
```

4. **Install and start the systemd service:**

```bash
sudo versionops-agent install
sudo systemctl enable --now versionops-agent
```

---

## Configuration

Configuration is stored in `/etc/versionops/agent.conf` (JSON format).

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `backend_url` | VersionOps backend URL | `https://app.versionops.com` |
| `token` | Service token for authentication | (required) |
| `interval` | Reporting interval in seconds | `300` (5 min) |
| `log_level` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `enabled_plugins` | List of enabled discovery plugins | all |

### Set Configuration

```bash
# Set backend URL
sudo versionops-agent config --backend=https://your-instance.com

# Set service token
sudo versionops-agent config --token=cmdb_agent_xxx

# Set reporting interval (in seconds)
sudo versionops-agent config --interval=600
```

### View Configuration

```bash
sudo versionops-agent config --show
```

---

## Usage

### Commands

```bash
versionops-agent <command> [options]

Commands:
  config      Configure the agent
  install     Install systemd service
  run         Run the agent (--once or --daemon)
  status      Show agent status and discovered applications
  version     Show version information
```

### Examples

```bash
# Run once (manual test)
sudo versionops-agent run --once

# Run as daemon (foreground)
sudo versionops-agent run --daemon

# Check status
sudo versionops-agent status

# Show version
versionops-agent version
```

---

## Discovered Applications

The agent automatically discovers applications using:

- **Package managers**: `dpkg`, `rpm`, `apk`
- **Binary version commands**: `--version`, `-v`, `-V`
- **Systemd services**: Version extraction from service files
- **Custom plugins**: Extensible plugin system

---

## Systemd Service

After running `versionops-agent install`, the service is managed via systemd:

```bash
# Start the agent
sudo systemctl start versionops-agent

# Stop the agent
sudo systemctl stop versionops-agent

# View logs
sudo journalctl -u versionops-agent -f

# Check status
sudo systemctl status versionops-agent
```

---

## Security

- **Minimal permissions**: Agent only needs read access to discover versions
- **Token authentication**: Uses secure service tokens (not user credentials)
- **Outbound only**: Agent only makes outbound HTTPS connections
- **No root required**: Can run as non-root user (with limited discovery)

### Required Permissions

For full discovery capabilities, the agent needs:
- Read access to `/usr/bin`, `/usr/local/bin`
- Ability to run version commands (`dpkg -l`, `rpm -qa`, etc.)
- Read access to `/etc` for some application configs

---

## Troubleshooting

### Agent not reporting data

1. Check configuration:
   ```bash
   sudo versionops-agent config --show
   ```

2. Test connectivity:
   ```bash
   sudo versionops-agent run --once
   ```

3. Check logs:
   ```bash
   sudo journalctl -u versionops-agent -f
   ```

### Common Issues

| Issue | Solution |
|-------|----------|
| "Connection refused" | Check `backend_url` is correct |
| "401 Unauthorized" | Verify service token is valid |
| "No applications found" | Run with `--log-level=DEBUG` to see discovery |

---

## Building from Source

### Requirements

- Python 3.9+
- PyInstaller

### Build

```bash
# Install dependencies
pip install -r requirements.txt

# Build for current platform
./build.sh

# Build for multiple architectures (requires Docker)
./build-docker.sh
```

---

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

## Links

- 🌐 **Website**: [https://versionops.com](https://versionops.com)
- 📚 **Documentation**: [https://docs.versionops.com](https://docs.versionops.com)
- 🐛 **Issues**: [GitHub Issues](https://github.com/versionops-platform/versionops-agent/issues)
- 💬 **Support**: support@versionops.com

---

<p align="center">
  Made with ❤️ by <a href="https://versionops.com">VersionOps</a>
</p>
