# Feature Overview

## Core features

### System monitoring
- **CPU load**: load average for 1, 5 and 15 minutes plus percentage load
- **RAM**: total, used, free (in bytes and formatted)
- **Disk space**: root partition usage with warnings
- **Uptime**: how long the server has been running
- **Threshold warnings**: configurable warnings when limits are exceeded

### Log management
- **Flexible log files**: any log file can be configured in YAML
- **Default logs**: syslog and auth.log preconfigured
- **Tail**: fetch the last N lines of each log file
- **Descriptions**: optional description for each log file

### Network monitoring
- **Open ports**: list of all listening ports
- **Active connections**: number of ESTABLISHED connections
- **Network interfaces**: overview of all interfaces with state and IPs

### Health checks
- **Comprehensive check**: combines all metrics in one report
- **Optional logs**: the health check can include log excerpts
- **Markdown report**: clear presentation of all information

## MCP tools

### `vserver_get_system_metrics`
Fetches system metrics (CPU, RAM, disk, load).

**Options:**
- `response_format`: markdown or json

**Example:**
```
Show me the system metrics
```

### `vserver_get_logs`
Fetches log files from the server.

**Parameters:**
- `log_name`: name of the log file (e.g. "syslog", "auth")
- `lines`: number of lines (default: 100, max: 10000)
- `response_format`: markdown or json

**Example:**
```
Show me the last 200 lines of the syslog
```

### `vserver_get_network_info`
Shows network information.

**Options:**
- `response_format`: markdown or json

**Example:**
```
Which ports are open?
```

### `vserver_health_check`
Full health check.

**Parameters:**
- `include_logs`: include logs? (default: true)
- `log_lines`: lines per log (default: 50, max: 1000)

**Example:**
```
Run a health check
```

### `vserver_list_available_logs`
Lists all configured log files.

**Example:**
```
Which logs can I fetch?
```

## Security

- **SSH key authentication**: no plain-text passwords
- **Read-only**: all tools only read
- **No destructive operations**: the server is not modified
- **Tool annotations**: correct hints for Claude (readOnly, nonDestructive, etc.)

See the security section in the [README](README.md) for recommendations on restricting the SSH user and key.

## Configuration

### YAML-based
All settings live in a single `config.yaml`:

```yaml
server:
  host: "your-server.example.com"
  port: 22
  username: "monitoring"
  ssh_key_path: "~/.ssh/id_ed25519"

monitoring:
  logs:
    - path: "/var/log/syslog"
      name: "syslog"
      description: "System log"

  system:
    thresholds:
      cpu_warning: 80
      cpu_critical: 95
      memory_warning: 80
      memory_critical: 95
      disk_warning: 80
      disk_critical: 95
```

### Extensible
- Add any log files
- Adjust thresholds
- Multiple servers via separate installations (see INTEGRATION.md)

## Output formats

### Markdown (default)
- Human-readable
- Formatted with headings and lists
- Ideal for chat answers

### JSON
- Structured data
- Machine-readable
- For further processing

## Performance

- **Efficient SSH connections**: context manager for clean connections
- **Minimal server load**: read-only operations only
- **Fast responses**: direct SSH commands without overhead
- **Async-ready**: FastMCP with async/await support

## Extensibility

### Modular architecture
- Helper functions for SSH access
- Reusable parsers
- Separate formatting functions

### Adding features
1. New function in `vserver_mcp.py`
2. New Pydantic input model
3. New tool with the `@mcp.tool` decorator

### Code quality
- Type hints throughout
- Pydantic validation
- Detailed docstrings
- Error handling

## Installation

### Dependencies
- Python 3.12+
- `mcp`: Model Context Protocol
- `pydantic`: data validation
- `PyYAML`: YAML parser
- `paramiko`: SSH client

### One-line install
```bash
./install.sh
```

## Testing

### Unit tests (no server needed)
```bash
python -m unittest test_vserver_mcp -v
```

### Connection test (needs a configured server)
```bash
python3 test_connection.py
```

The connection test covers:
- ✓ Config loading
- ✓ SSH connection
- ✓ System metrics
- ✓ Network info
- ✓ Log access
- ✓ Markdown formatting

## Use cases

### Proactive monitoring
```
What is the current server load?
```

### Troubleshooting
```
Show me the latest auth.log entries. Are there failed login attempts?
```

### Capacity planning
```
How much disk space is left?
```

### Security
```
Which ports are open and are there unusual connections?
```

### Documentation
```
Create a health check report for the team meeting
```

## Best practices

### Adjust thresholds
```yaml
system:
  thresholds:
    disk_warning: 70  # warn earlier about disk space
```

### Additional logs
```yaml
logs:
  - path: "/var/log/nginx/error.log"
    name: "nginx-error"
  - path: "/var/log/application.log"
    name: "app-log"
```

## Future ideas

- [ ] Service status (systemd)
- [ ] Docker container monitoring
- [ ] Process monitoring
- [ ] Alerting via e-mail/webhook
- [ ] Multi-server support in one MCP server
- [ ] Grafana integration
- [ ] Historical data
