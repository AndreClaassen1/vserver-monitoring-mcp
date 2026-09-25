# Integration with Claude Desktop

This guide shows how to connect the vServer Monitoring MCP server to Claude Desktop.

## Requirements

- Claude Desktop installed
- vServer Monitoring MCP server installed and configured
- `config.yaml` filled in with your server details

## Step 1: Find the Claude Desktop configuration

The Claude Desktop configuration file is located here:

### macOS
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

### Windows
```
%APPDATA%\Claude\claude_desktop_config.json
```

### Linux
```
~/.config/Claude/claude_desktop_config.json
```

## Step 2: Register the MCP server

Open `claude_desktop_config.json` and add the vServer Monitoring server. Use the Python interpreter from the project's virtual environment:

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

**Important:** Replace `/path/to/` with the actual absolute path to your installation, for example `/home/alice/vserver_monitoring_mcp` on Linux or `/Users/alice/vserver_monitoring_mcp` on macOS.

If the dependencies are installed globally, `"command": "python3"` works as well.

## Step 3: Restart Claude Desktop

1. Quit Claude Desktop completely
2. Start Claude Desktop again
3. The MCP server should now be available

## Step 4: Test the server

Open a chat in Claude Desktop and try the tools:

```
Show me the system metrics of my vServer
```

or

```
Run a health check on my server
```

## Available tools

After a successful integration you can use prompts like these:

### System metrics
```
Show me the CPU and RAM usage of my server
```

### Logs
```
Show me the last 100 lines of the syslog
```

or

```
Are there errors in the auth.log?
```

### Network information
```
Which ports are open on my server?
```

### Full health check
```
Run a full health check
```

### List available logs
```
Which log files can I fetch?
```

## Troubleshooting

### Server does not start

1. **Check the configuration:**
   ```bash
   cd /path/to/vserver_monitoring_mcp
   .venv/bin/python vserver_mcp.py --help
   ```

2. **Check config.yaml:**
   - Does the file exist?
   - Are all required fields filled in?
   - Is the SSH key path correct?

3. **Test the SSH connection manually:**
   ```bash
   ssh -i ~/.ssh/id_ed25519 username@your-server.example.com
   ```

### Tools do not show up

1. **Check the Claude Desktop logs:**
   - macOS: `~/Library/Logs/Claude/`
   - Windows: `%APPDATA%\Claude\logs\`
   - Linux: `~/.config/Claude/logs/`

2. **Check the paths in claude_desktop_config.json:**
   - Are the paths absolute (not relative)?
   - Do the files exist at those locations?

### SSH connection fails

1. **Check the SSH key:**
   ```bash
   ls -la ~/.ssh/id_ed25519
   ```

2. **Test key authentication:**
   ```bash
   ssh -i ~/.ssh/id_ed25519 username@your-server.example.com
   ```

3. **Check permissions:**
   ```bash
   chmod 600 ~/.ssh/id_ed25519
   ```

## Advanced configuration

### Multiple servers

The server always reads `config.yaml` from its own directory. Selecting a config file via an environment variable is **not built in**. There are two ways to monitor several servers:

**Option A: one installation per server.** Clone the project once per server, each with its own `config.yaml`, and register each installation separately:

```json
{
  "mcpServers": {
    "vserver-prod": {
      "command": "/path/to/vserver-prod/.venv/bin/python",
      "args": ["/path/to/vserver-prod/vserver_mcp.py"]
    },
    "vserver-staging": {
      "command": "/path/to/vserver-staging/.venv/bin/python",
      "args": ["/path/to/vserver-staging/vserver_mcp.py"]
    }
  }
}
```

**Option B: add a `CONFIG_FILE` environment variable yourself.** Adapt the startup code in `vserver_mcp.py` so that it reads the config path from the environment, for example:

```python
config_path = os.getenv("CONFIG_FILE", "config.yaml")
```

Then pass `"env": {"CONFIG_FILE": "config-prod.yaml"}` in each server entry.

## Getting help

If something does not work:

1. Check the README.md
2. Look at the Claude Desktop logs
3. Test the SSH connection manually
4. Verify all paths in the configuration
