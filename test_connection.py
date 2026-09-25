#!/usr/bin/env python3
"""
Test-Skript für vServer Monitoring MCP Server

Testet die SSH-Verbindung und grundlegende Funktionen ohne MCP.
"""

import sys
import yaml
from pathlib import Path

# Füge den aktuellen Pfad zum Python-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent))

from vserver_mcp import (
    load_config,
    SSHClient,
    parse_system_metrics,
    parse_network_info,
    format_system_metrics_markdown,
    format_network_info_markdown
)


def test_config_loading():
    """Testet das Laden der Konfiguration."""
    print("=" * 60)
    print("TEST 1: Konfiguration laden")
    print("=" * 60)
    
    try:
        config = load_config()
        print("✓ Konfiguration erfolgreich geladen")
        print(f"  Server: {config.server.host}")
        print(f"  Port: {config.server.port}")
        print(f"  Username: {config.server.username}")
        print(f"  SSH-Key: {config.server.ssh_key_path}")
        print(f"  Anzahl Log-Dateien: {len(config.monitoring.logs)}")
        return config
    except Exception as e:
        print(f"✗ FEHLER: {str(e)}")
        return None


def test_ssh_connection(config):
    """Testet die SSH-Verbindung."""
    print("\n" + "=" * 60)
    print("TEST 2: SSH-Verbindung")
    print("=" * 60)
    
    try:
        with SSHClient(config.server) as ssh:
            print("✓ SSH-Verbindung erfolgreich")
            
            # Teste einfachen Befehl
            stdout, stderr, exit_code = ssh.execute_command("hostname")
            if exit_code == 0:
                print(f"✓ Kommando ausgeführt: hostname = {stdout.strip()}")
            else:
                print(f"✗ Kommando fehlgeschlagen: {stderr}")
                return False
        
        return True
    except Exception as e:
        print(f"✗ FEHLER: {str(e)}")
        return False


def test_system_metrics(config):
    """Testet das Abrufen von System-Metriken."""
    print("\n" + "=" * 60)
    print("TEST 3: System-Metriken")
    print("=" * 60)
    
    try:
        with SSHClient(config.server) as ssh:
            thresholds = None
            if config.monitoring.system and config.monitoring.system.thresholds:
                thresholds = config.monitoring.system.thresholds
            
            metrics = parse_system_metrics(ssh, thresholds)
            print("✓ System-Metriken erfolgreich abgerufen")
            print(f"  CPU-Auslastung: {metrics['cpu_usage_percent']}%")
            print(f"  RAM-Auslastung: {metrics['memory']['usage_percent']}%")
            print(f"  Disk-Auslastung: {metrics['disk']['usage_percent']}%")
            print(f"  Uptime: {metrics['uptime']}")
            
            if 'warnings' in metrics and metrics['warnings']:
                print(f"  ⚠️  Warnungen: {len(metrics['warnings'])}")
                for warning in metrics['warnings']:
                    print(f"    - {warning}")
        
        return True
    except Exception as e:
        print(f"✗ FEHLER: {str(e)}")
        return False


def test_network_info(config):
    """Testet das Abrufen von Netzwerk-Informationen."""
    print("\n" + "=" * 60)
    print("TEST 4: Netzwerk-Informationen")
    print("=" * 60)
    
    try:
        with SSHClient(config.server) as ssh:
            network = parse_network_info(ssh)
            print("✓ Netzwerk-Informationen erfolgreich abgerufen")
            print(f"  Offene Ports: {len(network['listening_ports'])}")
            print(f"  Aktive Verbindungen: {network['active_connections']}")
            print(f"  Netzwerk-Interfaces: {len(network['interfaces'])}")
            
            if network['listening_ports']:
                print(f"  Beispiel-Ports: {network['listening_ports'][:5]}")
        
        return True
    except Exception as e:
        print(f"✗ FEHLER: {str(e)}")
        return False


def test_log_access(config):
    """Testet den Zugriff auf Log-Dateien."""
    print("\n" + "=" * 60)
    print("TEST 5: Log-Datei-Zugriff")
    print("=" * 60)
    
    if not config.monitoring.logs:
        print("⚠ Keine Log-Dateien konfiguriert")
        return True
    
    try:
        with SSHClient(config.server) as ssh:
            for log in config.monitoring.logs[:3]:  # Teste nur erste 3 Logs
                command = f"tail -n 5 {log.path}"
                stdout, stderr, exit_code = ssh.execute_command(command)
                
                if exit_code == 0:
                    lines = len(stdout.strip().split('\n'))
                    print(f"✓ {log.name}: {lines} Zeilen gelesen")
                else:
                    print(f"✗ {log.name}: Fehler - {stderr.strip()}")
        
        return True
    except Exception as e:
        print(f"✗ FEHLER: {str(e)}")
        return False


def test_markdown_formatting(config):
    """Testet die Markdown-Formatierung."""
    print("\n" + "=" * 60)
    print("TEST 6: Markdown-Formatierung")
    print("=" * 60)
    
    try:
        with SSHClient(config.server) as ssh:
            metrics = parse_system_metrics(ssh)
            md = format_system_metrics_markdown(metrics)
            
            if md and len(md) > 0:
                print("✓ Markdown-Formatierung erfolgreich")
                print(f"  Länge: {len(md)} Zeichen")
                
                # Zeige ersten Teil
                preview = md[:200]
                print(f"  Preview:\n{preview}...")
            else:
                print("✗ Markdown-Formatierung fehlgeschlagen")
                return False
        
        return True
    except Exception as e:
        print(f"✗ FEHLER: {str(e)}")
        return False


def main():
    """Führt alle Tests aus."""
    print("\n" + "=" * 60)
    print("vServer Monitoring MCP Server - Verbindungstest")
    print("=" * 60 + "\n")
    
    # Test 1: Konfiguration laden
    config = test_config_loading()
    if not config:
        print("\n❌ Tests abgebrochen - Konfiguration konnte nicht geladen werden")
        return False
    
    # Test 2: SSH-Verbindung
    if not test_ssh_connection(config):
        print("\n❌ Tests abgebrochen - SSH-Verbindung fehlgeschlagen")
        return False
    
    # Test 3: System-Metriken
    test_system_metrics(config)
    
    # Test 4: Netzwerk-Info
    test_network_info(config)
    
    # Test 5: Log-Zugriff
    test_log_access(config)
    
    # Test 6: Markdown-Formatierung
    test_markdown_formatting(config)
    
    print("\n" + "=" * 60)
    print("✓ Alle Tests abgeschlossen!")
    print("=" * 60)
    print("\nDer MCP Server ist bereit für die Integration mit Claude Desktop.")
    print("Siehe INTEGRATION.md für weitere Schritte.")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests abgebrochen.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unerwarteter Fehler: {str(e)}")
        sys.exit(1)
