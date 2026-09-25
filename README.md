# vServer Monitoring MCP Server

An MCP server (Model Context Protocol) that gives Claude SSH-based, read-only access to a Linux vServer. Claude can query system metrics, read log files, collect network information and produce complete health check reports.

## Purpose

Monitoring a Linux server usually requires SSH access and knowing the relevant commands and log locations. This MCP server hides that complexity: it connects to the server over SSH and returns structured monitoring data. You can simply ask "How is my server doing?" in a chat and get a complete health check report, including automatic warnings when configured thresholds are exceeded.

## Available tools

| Tool | Description |
|---|---|
| `vserver_get_system_metrics` | CPU load, RAM usage, disk usage and uptime; warnings based on configured thresholds |
| `vserver_get_logs` | Last N lines of a configured log file (e.g. syslog, auth.log, nginx logs) |
| `vserver_get_network_info` | Open ports (listening services), active connections and network interfaces with IP addresses |
| `vserver_health_check` | Full health check: combines system metrics, network information and log excerpts in one report |
| `vserver_list_available_logs` | Lists all log files configured in `config.yaml` (name, path, description) |

All tools support the output formats `markdown` (readable, default) and `json` (structured, for further processing).

## Requirements

- Python 3.12+
- SSH access to the target server with an SSH key (RSA, Ed25519 or ECDSA)
- The public key must be listed in `~/.ssh/authorized_keys` on the target server
- Standard Linux tools on the target server (`cat`, `free`, `df`, `ss`, `ip`, `tail`, `uptime`)

## Installation

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Alternatively, use the install script:

```bash
./install.sh
```

## Configuration

Copy `config.example.yaml` to `config.yaml` and adjust the values:

```yaml
server:
  host: "your-server.example.com"
  port: 22
  username: "monitoring"
  ssh_key_path: "~/.ssh/id_ed25519"
  # ssh_key_passphrase: "passphrase-if-encrypted"
  timeout: 10

monitoring:
  logs:
    - path: "/var/log/syslog"
      name: "syslog"
      description: "System log with general system messages"
    - path: "/var/log/auth.log"
      name: "auth"
      description: "Authentication and authorization log"
    # Add more logs as needed:
    # - path: "/var/log/nginx/error.log"
    #   name: "nginx-error"

  network:
    check_ports: true
    check_connections: true

  system:
    thresholds:
      cpu_warning: 80
      cpu_critical: 95
      memory_warning: 80
      memory_critical: 95
      disk_warning: 80
      disk_critical: 95
```

`config.yaml` must be located in the same directory as `vserver_mcp.py`. It contains your server details and is excluded from version control via `.gitignore`.

## Testing the connection

```bash
python3 test_connection.py
```

This script connects to the server configured in `config.yaml`. The unit tests in `test_vserver_mcp.py` run without a server:

```bash
python -m unittest test_vserver_mcp -v
```

## Claude Desktop integration

```json
{
  "mcpServers": {
    "vserver-monitoring": {
      "command": "/path/to/vserver_monitoring_mcp/.venv/bin/python",
      "args": [
        "/path/to/vserver_monitoring_mcp/vserver_mcp.py"
      ]
    }
  }
}
```

The configuration file is located at:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Important:** The path in `args` must be absolute. On startup the server changes into the directory of the script, so that `config.yaml` is found.

See [QUICKSTART.md](QUICKSTART.md) and [INTEGRATION.md](INTEGRATION.md) for details.

## Example prompts

```
Show me the current system metrics of my server.
```

```
Run a full health check and report any potential problems.
```

```
Show me the last 50 lines of the auth log.
```

```
Which ports are open on my server?
```

## Security

The server executes read-only monitoring commands on the target host over SSH (for example `free`, `df`, `ss`, `tail`). It does not change anything on the server. Even so, it holds a working SSH key, so:

- Use a dedicated, unprivileged user instead of `root`, with read access only to the log files you want to expose.
- Use a dedicated SSH key for this purpose. Consider restricting it in `authorized_keys` (for example with `from="..."`, `no-port-forwarding`, `no-agent-forwarding`, `no-pty`).
- Only list log files in `config.yaml` that you are comfortable sharing with the AI assistant.

## Status

Beta. Usable for standard Linux servers (Debian/Ubuntu).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT, see [LICENSE](LICENSE). The name is not covered by the license.
