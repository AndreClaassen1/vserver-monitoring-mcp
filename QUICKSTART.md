# Quick Start Guide

Get started in five minutes.

## 1. Installation

```bash
# Change into the project directory
cd /path/to/vserver_monitoring_mcp

# Automatic installation
./install.sh

# Or manually:
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Configuration

```bash
# Copy the example configuration
cp config.example.yaml config.yaml

# Edit the configuration
nano config.yaml  # or your preferred editor
```

Fill in at least these fields:

- `server.host`: your server address
- `server.username`: SSH user name (preferably an unprivileged user, see the security note in the README)
- `server.ssh_key_path`: path to your SSH key (e.g. `~/.ssh/id_ed25519`)

## 3. Test the connection

```bash
python3 test_connection.py
```

All checks should pass with ✓.

## 4. Claude Desktop integration

### Open the config file

**macOS:**
```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Linux:**
```bash
nano ~/.config/Claude/claude_desktop_config.json
```

### Add the MCP server

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

**Important:** Replace `/path/to/` with the real, absolute path.

### Restart Claude Desktop

1. Quit Claude Desktop
2. Start it again
3. The tools are now available

## 5. Try it in Claude

In a chat, try:

```
Show me the system metrics of my vServer
```

or

```
Run a health check
```

## Common problems

### "SSH key not found"
- Check the path in `config.yaml`
- Make sure the key exists: `ls -la ~/.ssh/id_ed25519`

### "SSH authentication failed"
- Test manually: `ssh -i ~/.ssh/id_ed25519 username@your-server.example.com`
- Check key permissions: `chmod 600 ~/.ssh/id_ed25519`
- If the key is encrypted: add `ssh_key_passphrase` to `config.yaml`

### "config.yaml not found"
- Make sure the file is in the same directory as `vserver_mcp.py`
- The file must be named `config.yaml` (not `config.example.yaml`)

### Tools do not show up in Claude
- Check that the path in `claude_desktop_config.json` is absolute
- Look at the Claude Desktop logs (see INTEGRATION.md)
- Restart Claude Desktop completely

## Next steps

- Read the [README.md](README.md) for details on all features
- See [INTEGRATION.md](INTEGRATION.md) for advanced integration
- Adapt `config.yaml` to your needs (more logs, thresholds, etc.)

## Troubleshooting checklist

1. Run `python3 test_connection.py`
2. Check the output for error messages
3. Look at the Claude Desktop logs
