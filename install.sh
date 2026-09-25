#!/bin/bash

# vServer Monitoring MCP Server - installation script

echo "==================================="
echo "vServer Monitoring MCP Server"
echo "Installation"
echo "==================================="
echo ""

# Check that Python 3.12 is installed
if ! command -v python3.12 &> /dev/null; then
    echo "ERROR: Python 3.12 is not installed."
    exit 1
fi

PYTHON_VERSION=$(python3.12 --version | awk '{print $2}')
echo "✓ Python found: $PYTHON_VERSION"
echo ""

# Create virtual environment
echo "Creating virtual environment (.venv)..."
python3.12 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "✓ Virtual environment created and activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
else
    echo "ERROR: Installing dependencies failed"
    exit 1
fi

echo ""
echo "==================================="
echo "Configuration"
echo "==================================="
echo ""

# Check whether config.yaml already exists
if [ -f "config.yaml" ]; then
    echo "✓ config.yaml already exists"
else
    echo "Creating config.yaml from template..."
    cp config.example.yaml config.yaml
    echo "✓ config.yaml created"
    echo ""
    echo "⚠️  IMPORTANT: Please edit config.yaml and enter your server details:"
    echo "   - SSH host"
    echo "   - SSH user name"
    echo "   - SSH key path"
    echo ""
fi

# Make the script executable
chmod +x vserver_mcp.py 2>/dev/null

echo "==================================="
echo "Installation complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Edit config.yaml with your server details"
echo "2. Test the connection: python3 test_connection.py"
echo "3. Register the server in Claude Desktop (see INTEGRATION.md)"
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo ""
echo "See README.md for details"
