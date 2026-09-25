#!/usr/bin/env python3
"""
vServer Monitoring MCP Server

Ein MCP Server für SSH-basiertes vServer-Monitoring.
Bietet Tools für System-Metriken, Log-Dateien und Netzwerk-Überwachung.
"""

import os
import json
import yaml
import paramiko
from pathlib import Path
from typing import Any
from enum import Enum
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ============================================================================
# Configuration Models
# ============================================================================

class ServerConfig(BaseModel):
    """
    SSH Server configuration model.

    This class defines the configuration parameters required to establish
    an SSH connection to a remote server.

    Attributes:
        host (str): The hostname or IP address of the SSH server.
        port (int): The SSH port number. Defaults to 22.
        username (str): The username for SSH authentication.
        ssh_key_path (str): The file path to the SSH private key.
        ssh_key_passphrase (Optional[str]): The passphrase for the SSH private key,
            if it is encrypted. Defaults to None.
        timeout (int): The connection timeout in seconds. Defaults to 10.
    """
    """SSH Server Konfiguration."""
    host: str
    port: int = 22
    username: str
    ssh_key_path: str
    ssh_key_passphrase: str | None = None
    timeout: int = 10

class LogConfig(BaseModel):
    """Log-Datei Konfiguration."""
    path: str
    name: str
    description: str | None = None

class NetworkConfig(BaseModel):
    """Netzwerk-Monitoring Konfiguration."""
    check_ports: bool = True
    check_connections: bool = True
    monitored_ports: list[int] | None = None

class ThresholdsConfig(BaseModel):
    """Schwellenwerte für Warnungen."""
    cpu_warning: float = 80.0
    cpu_critical: float = 95.0
    memory_warning: float = 80.0
    memory_critical: float = 95.0
    disk_warning: float = 80.0
    disk_critical: float = 95.0

class SystemConfig(BaseModel):
    """System-Monitoring Konfiguration."""
    thresholds: ThresholdsConfig | None = None

class MonitoringConfig(BaseModel):
    """Monitoring Konfiguration."""
    logs: list[LogConfig]
    network: NetworkConfig = NetworkConfig()
    system: SystemConfig | None = None

class Config(BaseModel):
    """Haupt-Konfiguration."""
    server: ServerConfig
    monitoring: MonitoringConfig


# ============================================================================
# SSH Client Helper
# ============================================================================

class SSHClient:
    """Helper-Klasse für SSH-Verbindungen."""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.client = None
    
    def _expand_path(self, path: str) -> str:
        """Expandiert ~ zu Home-Verzeichnis."""
        return str(Path(path).expanduser())
    
    def connect(self) -> None:
        """Stellt SSH-Verbindung her."""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # SSH-Key laden (unterstützt Ed25519, RSA, ECDSA)
            key_path = self._expand_path(self.config.ssh_key_path)
            private_key = None
            key_classes = [
                paramiko.Ed25519Key,
                paramiko.RSAKey,
                paramiko.ECDSAKey,
            ]

            for key_class in key_classes:
                try:
                    private_key = key_class.from_private_key_file(
                        key_path,
                        password=self.config.ssh_key_passphrase
                    )
                    break
                except paramiko.SSHException:
                    continue

            if private_key is None:
                raise Exception(f"SSH-Key konnte nicht geladen werden: {key_path}")
            
            # Verbindung aufbauen
            self.client.connect(
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                pkey=private_key,
                timeout=self.config.timeout
            )
        except FileNotFoundError:
            raise Exception(f"SSH-Key nicht gefunden: {key_path}")
        except paramiko.AuthenticationException:
            raise Exception("SSH-Authentifizierung fehlgeschlagen. Prüfe Key und Passphrase.")
        except paramiko.SSHException as e:
            raise Exception(f"SSH-Fehler: {str(e)}")
        except Exception as e:
            raise Exception(f"Verbindungsfehler: {str(e)}")
    
    def execute_command(self, command: str) -> tuple[str, str, int]:
        """
        Führt Kommando auf Server aus.
        
        Returns:
            tuple: (stdout, stderr, exit_code)
        """
        if not self.client:
            raise Exception("Keine SSH-Verbindung. Rufe zuerst connect() auf.")
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            
            return (
                stdout.read().decode('utf-8'),
                stderr.read().decode('utf-8'),
                exit_code
            )
        except Exception as e:
            raise Exception(f"Fehler beim Ausführen des Kommandos: {str(e)}")
    
    def close(self) -> None:
        """Schließt SSH-Verbindung."""
        if self.client:
            self.client.close()
            self.client = None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ============================================================================
# Helper Functions
# ============================================================================

def load_config(config_path: str = "config.yaml") -> Config:
    """Lädt Konfiguration aus YAML-Datei."""
    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        return Config(**config_data)
    except FileNotFoundError:
        raise Exception(f"Konfigurationsdatei nicht gefunden: {config_path}")
    except yaml.YAMLError as e:
        raise Exception(f"YAML-Fehler in Konfigurationsdatei: {str(e)}")
    except Exception as e:
        raise Exception(f"Fehler beim Laden der Konfiguration: {str(e)}")


def format_bytes(bytes_value: int) -> str:
    """Formatiert Bytes in menschenlesbare Größe."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def parse_system_metrics(ssh_client: SSHClient, thresholds: ThresholdsConfig | None = None) -> dict[str, Any]:
    """Sammelt System-Metriken vom Server."""
    metrics = {}
    
    # CPU-Auslastung (1 min, 5 min, 15 min Load Average)
    stdout, _, _ = ssh_client.execute_command("cat /proc/loadavg")
    load_avg = stdout.strip().split()[:3]
    metrics['load_average'] = {
        '1min': float(load_avg[0]),
        '5min': float(load_avg[1]),
        '15min': float(load_avg[2])
    }
    
    # CPU-Kerne zählen
    stdout, _, _ = ssh_client.execute_command("nproc")
    cpu_cores = int(stdout.strip())
    metrics['cpu_cores'] = cpu_cores
    
    # CPU-Auslastung in Prozent
    cpu_usage = (metrics['load_average']['1min'] / cpu_cores) * 100
    metrics['cpu_usage_percent'] = round(cpu_usage, 2)
    
    # RAM-Nutzung
    stdout, _, _ = ssh_client.execute_command("free -b")
    lines = stdout.strip().split('\n')
    mem_line = lines[1].split()
    total_mem = int(mem_line[1])
    used_mem = int(mem_line[2])
    free_mem = int(mem_line[3])
    
    metrics['memory'] = {
        'total': total_mem,
        'used': used_mem,
        'free': free_mem,
        'usage_percent': round((used_mem / total_mem) * 100, 2),
        'total_formatted': format_bytes(total_mem),
        'used_formatted': format_bytes(used_mem),
        'free_formatted': format_bytes(free_mem)
    }
    
    # Disk-Nutzung (Root-Partition)
    stdout, _, _ = ssh_client.execute_command("df -B1 /")
    lines = stdout.strip().split('\n')
    disk_line = lines[1].split()
    total_disk = int(disk_line[1])
    used_disk = int(disk_line[2])
    free_disk = int(disk_line[3])
    
    metrics['disk'] = {
        'total': total_disk,
        'used': used_disk,
        'free': free_disk,
        'usage_percent': round((used_disk / total_disk) * 100, 2),
        'total_formatted': format_bytes(total_disk),
        'used_formatted': format_bytes(used_disk),
        'free_formatted': format_bytes(free_disk)
    }
    
    # Uptime
    stdout, _, _ = ssh_client.execute_command("uptime -p")
    metrics['uptime'] = stdout.strip()
    
    # Warnungen hinzufügen wenn Schwellenwerte überschritten
    if thresholds:
        metrics['warnings'] = []
        
        if cpu_usage >= thresholds.cpu_critical:
            metrics['warnings'].append(f"CRITICAL: CPU-Auslastung bei {cpu_usage:.1f}%")
        elif cpu_usage >= thresholds.cpu_warning:
            metrics['warnings'].append(f"WARNING: CPU-Auslastung bei {cpu_usage:.1f}%")
        
        mem_usage = metrics['memory']['usage_percent']
        if mem_usage >= thresholds.memory_critical:
            metrics['warnings'].append(f"CRITICAL: RAM-Auslastung bei {mem_usage:.1f}%")
        elif mem_usage >= thresholds.memory_warning:
            metrics['warnings'].append(f"WARNING: RAM-Auslastung bei {mem_usage:.1f}%")
        
        disk_usage = metrics['disk']['usage_percent']
        if disk_usage >= thresholds.disk_critical:
            metrics['warnings'].append(f"CRITICAL: Disk-Auslastung bei {disk_usage:.1f}%")
        elif disk_usage >= thresholds.disk_warning:
            metrics['warnings'].append(f"WARNING: Disk-Auslastung bei {disk_usage:.1f}%")
    
    return metrics


def parse_network_info(ssh_client: SSHClient) -> dict[str, Any]:
    """Sammelt Netzwerk-Informationen vom Server."""
    network = {}
    
    # Offene Ports (Listening Services)
    stdout, _, _ = ssh_client.execute_command(
        "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null | grep LISTEN"
    )
    
    listening_ports = []
    for line in stdout.strip().split('\n'):
        if line and 'LISTEN' in line:
            parts = line.split()
            if len(parts) >= 4:
                local_addr = parts[3] if 'ss' in line else parts[3]
                # Port extrahieren
                if ':' in local_addr:
                    port = local_addr.split(':')[-1]
                    if port.isdigit():
                        listening_ports.append(int(port))
    
    network['listening_ports'] = sorted(set(listening_ports))
    
    # Aktive Verbindungen zählen
    stdout, _, _ = ssh_client.execute_command("ss -ant | grep ESTAB | wc -l")
    network['active_connections'] = int(stdout.strip())
    
    # Netzwerk-Interfaces
    stdout, _, _ = ssh_client.execute_command("ip -br addr")
    interfaces = []
    for line in stdout.strip().split('\n'):
        if line:
            parts = line.split()
            if len(parts) >= 3:
                interfaces.append({
                    'name': parts[0],
                    'state': parts[1],
                    'addresses': parts[2:] if len(parts) > 2 else []
                })
    network['interfaces'] = interfaces
    
    return network


def format_system_metrics_markdown(metrics: dict[str, Any]) -> str:
    """Formatiert System-Metriken als Markdown."""
    md = "# System-Metriken\n\n"
    
    # Warnungen zuerst anzeigen
    if 'warnings' in metrics and metrics['warnings']:
        md += "## ⚠️ Warnungen\n\n"
        for warning in metrics['warnings']:
            md += f"- {warning}\n"
        md += "\n"
    
    # Uptime
    md += f"**Uptime:** {metrics['uptime']}\n\n"
    
    # CPU
    md += "## CPU\n\n"
    md += f"- **Kerne:** {metrics['cpu_cores']}\n"
    md += f"- **Auslastung:** {metrics['cpu_usage_percent']}%\n"
    md += f"- **Load Average:** {metrics['load_average']['1min']} (1min), "
    md += f"{metrics['load_average']['5min']} (5min), "
    md += f"{metrics['load_average']['15min']} (15min)\n\n"
    
    # RAM
    mem = metrics['memory']
    md += "## RAM\n\n"
    md += f"- **Total:** {mem['total_formatted']}\n"
    md += f"- **Verwendet:** {mem['used_formatted']} ({mem['usage_percent']}%)\n"
    md += f"- **Frei:** {mem['free_formatted']}\n\n"
    
    # Disk
    disk = metrics['disk']
    md += "## Disk (Root)\n\n"
    md += f"- **Total:** {disk['total_formatted']}\n"
    md += f"- **Verwendet:** {disk['used_formatted']} ({disk['usage_percent']}%)\n"
    md += f"- **Frei:** {disk['free_formatted']}\n"
    
    return md


def format_network_info_markdown(network: dict[str, Any]) -> str:
    """Formatiert Netzwerk-Informationen als Markdown."""
    md = "# Netzwerk-Informationen\n\n"
    
    # Listening Ports
    md += "## Offene Ports (Listening)\n\n"
    if network['listening_ports']:
        for port in network['listening_ports']:
            md += f"- Port {port}\n"
    else:
        md += "Keine offenen Ports gefunden.\n"
    md += "\n"
    
    # Aktive Verbindungen
    md += f"**Aktive Verbindungen:** {network['active_connections']}\n\n"
    
    # Netzwerk-Interfaces
    md += "## Netzwerk-Interfaces\n\n"
    for iface in network['interfaces']:
        md += f"### {iface['name']}\n"
        md += f"- **Status:** {iface['state']}\n"
        if iface['addresses']:
            md += f"- **Adressen:** {', '.join(iface['addresses'])}\n"
        md += "\n"
    
    return md


# ============================================================================
# Lifespan Management
# ============================================================================

@asynccontextmanager
async def app_lifespan(_app):
    """Lädt Konfiguration beim Server-Start."""
    config = load_config()
    yield {"config": config}


# ============================================================================
# MCP Server Initialization
# ============================================================================

mcp = FastMCP("vserver_monitoring_mcp", lifespan=app_lifespan)


# ============================================================================
# Response Format Enum
# ============================================================================

class ResponseFormat(str, Enum):
    """Ausgabeformat für Tool-Antworten."""
    MARKDOWN = "markdown"
    JSON = "json"


# ============================================================================
# Tool Input Models
# ============================================================================

class SystemMetricsInput(BaseModel):
    """Input für System-Metriken Tool."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' für lesbare Darstellung oder 'json' für strukturierte Daten"
    )


class LogInput(BaseModel):
    """Input für Log-Abruf Tool."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    log_name: str = Field(
        ...,
        description="Name der Log-Datei wie in config.yaml definiert (z.B. 'syslog', 'auth')",
        min_length=1
    )
    
    lines: int = Field(
        default=100,
        description="Anzahl der letzten Zeilen, die abgerufen werden sollen",
        ge=1,
        le=10000
    )
    
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' für lesbare Darstellung oder 'json' für strukturierte Daten"
    )


class NetworkInfoInput(BaseModel):
    """Input für Netzwerk-Info Tool."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' für lesbare Darstellung oder 'json' für strukturierte Daten"
    )


class HealthCheckInput(BaseModel):
    """Input für vollständigen Health Check."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    include_logs: bool = Field(
        default=True,
        description="Sollen kritische Log-Einträge inkludiert werden?"
    )
    
    log_lines: int = Field(
        default=50,
        description="Anzahl der Log-Zeilen pro Log-Datei",
        ge=1,
        le=1000
    )


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool(
    name="vserver_get_system_metrics",
    annotations={
        "title": "System-Metriken vom vServer abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_system_metrics(params: SystemMetricsInput, ctx: Context) -> str:
    """
    Ruft System-Metriken vom vServer ab.
    
    Sammelt folgende Informationen:
    - CPU-Auslastung und Load Average
    - RAM-Nutzung (total, verwendet, frei)
    - Disk-Nutzung der Root-Partition
    - System-Uptime
    - Warnungen bei Überschreitung von Schwellenwerten
    
    Args:
        params (SystemMetricsInput): Eingabeparameter mit:
            - response_format: Ausgabeformat (markdown oder json)
    
    Returns:
        str: System-Metriken im gewünschten Format
    """
    config: Config = ctx.request_context.lifespan_context["config"]
    
    try:
        with SSHClient(config.server) as ssh:
            thresholds = None
            if config.monitoring.system and config.monitoring.system.thresholds:
                thresholds = config.monitoring.system.thresholds
            
            metrics = parse_system_metrics(ssh, thresholds)
            
            if params.response_format == ResponseFormat.JSON:
                return json.dumps(metrics, indent=2)
            else:
                return format_system_metrics_markdown(metrics)
    
    except Exception as e:
        return f"Fehler beim Abrufen der System-Metriken: {str(e)}"


@mcp.tool(
    name="vserver_get_logs",
    annotations={
        "title": "Log-Dateien vom vServer abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_logs(params: LogInput, ctx: Context) -> str:
    """
    Lädt Log-Dateien vom vServer herunter.
    
    Ruft die letzten N Zeilen einer konfigurierten Log-Datei ab.
    Die verfügbaren Log-Dateien sind in der config.yaml unter 'monitoring.logs' definiert.
    
    Args:
        params (LogInput): Eingabeparameter mit:
            - log_name: Name der Log-Datei (aus config.yaml)
            - lines: Anzahl der letzten Zeilen (Standard: 100)
            - response_format: Ausgabeformat (markdown oder json)
    
    Returns:
        str: Log-Inhalt im gewünschten Format
    """
    config: Config = ctx.request_context.lifespan_context["config"]
    
    # Log-Datei in Konfiguration finden
    log_config = None
    for log in config.monitoring.logs:
        if log.name == params.log_name:
            log_config = log
            break
    
    if not log_config:
        available_logs = [log.name for log in config.monitoring.logs]
        return f"Fehler: Log '{params.log_name}' nicht gefunden. Verfügbare Logs: {', '.join(available_logs)}"
    
    try:
        with SSHClient(config.server) as ssh:
            # Letzte N Zeilen der Log-Datei abrufen
            command = f"tail -n {params.lines} {log_config.path}"
            stdout, stderr, exit_code = ssh.execute_command(command)
            
            if exit_code != 0:
                return f"Fehler beim Lesen der Log-Datei: {stderr}"
            
            if params.response_format == ResponseFormat.JSON:
                return json.dumps({
                    "log_name": log_config.name,
                    "log_path": log_config.path,
                    "description": log_config.description,
                    "lines_requested": params.lines,
                    "content": stdout
                }, indent=2)
            else:
                md = f"# Log: {log_config.name}\n\n"
                if log_config.description:
                    md += f"**Beschreibung:** {log_config.description}\n"
                md += f"**Pfad:** {log_config.path}\n"
                md += f"**Zeilen:** Letzte {params.lines}\n\n"
                md += "## Inhalt\n\n```\n"
                md += stdout
                md += "\n```"
                return md
    
    except Exception as e:
        return f"Fehler beim Abrufen der Logs: {str(e)}"


@mcp.tool(
    name="vserver_get_network_info",
    annotations={
        "title": "Netzwerk-Informationen vom vServer abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_network_info(params: NetworkInfoInput, ctx: Context) -> str:
    """
    Ruft Netzwerk-Informationen vom vServer ab.
    
    Sammelt folgende Informationen:
    - Offene Ports (Listening Services)
    - Anzahl aktiver Verbindungen
    - Netzwerk-Interfaces mit Status und IP-Adressen
    
    Args:
        params (NetworkInfoInput): Eingabeparameter mit:
            - response_format: Ausgabeformat (markdown oder json)
    
    Returns:
        str: Netzwerk-Informationen im gewünschten Format
    """
    config: Config = ctx.request_context.lifespan_context["config"]
    
    try:
        with SSHClient(config.server) as ssh:
            network = parse_network_info(ssh)
            
            if params.response_format == ResponseFormat.JSON:
                return json.dumps(network, indent=2)
            else:
                return format_network_info_markdown(network)
    
    except Exception as e:
        return f"Fehler beim Abrufen der Netzwerk-Informationen: {str(e)}"


@mcp.tool(
    name="vserver_health_check",
    annotations={
        "title": "Vollständiger Gesundheitscheck des vServers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def health_check(params: HealthCheckInput, ctx: Context) -> str:
    """
    Führt einen vollständigen Gesundheitscheck des vServers durch.
    
    Kombiniert System-Metriken, Netzwerk-Informationen und optional kritische
    Log-Einträge zu einem umfassenden Überblick über den Server-Zustand.
    
    Args:
        params (HealthCheckInput): Eingabeparameter mit:
            - include_logs: Sollen Log-Einträge inkludiert werden? (Standard: true)
            - log_lines: Anzahl der Log-Zeilen pro Datei (Standard: 50)
    
    Returns:
        str: Vollständiger Health-Check Report im Markdown-Format
    """
    config: Config = ctx.request_context.lifespan_context["config"]
    
    try:
        report = "# vServer Health Check Report\n\n"
        report += f"**Server:** {config.server.host}\n"
        report += f"**Zeitpunkt:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += "---\n\n"
        
        with SSHClient(config.server) as ssh:
            # System-Metriken
            thresholds = None
            if config.monitoring.system and config.monitoring.system.thresholds:
                thresholds = config.monitoring.system.thresholds
            
            metrics = parse_system_metrics(ssh, thresholds)
            report += format_system_metrics_markdown(metrics)
            report += "\n---\n\n"
            
            # Netzwerk-Informationen
            network = parse_network_info(ssh)
            report += format_network_info_markdown(network)
            
            # Logs (optional)
            if params.include_logs and config.monitoring.logs:
                report += "\n---\n\n# Log-Auszüge\n\n"
                
                for log_config in config.monitoring.logs:
                    command = f"tail -n {params.log_lines} {log_config.path}"
                    stdout, stderr, exit_code = ssh.execute_command(command)
                    
                    if exit_code == 0:
                        report += f"## {log_config.name}\n"
                        if log_config.description:
                            report += f"*{log_config.description}*\n"
                        report += f"\nLetzte {params.log_lines} Zeilen:\n\n```\n"
                        report += stdout
                        report += "\n```\n\n"
                    else:
                        report += f"## {log_config.name}\n"
                        report += f"⚠️ Fehler beim Lesen: {stderr}\n\n"
        
        return report
    
    except Exception as e:
        return f"Fehler beim Health Check: {str(e)}"


@mcp.tool(
    name="vserver_list_available_logs",
    annotations={
        "title": "Liste aller konfigurierten Log-Dateien",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def list_available_logs(ctx: Context) -> str:
    """
    Listet alle in der Konfiguration definierten Log-Dateien auf.
    
    Zeigt verfügbare Log-Dateien mit ihren Namen, Pfaden und Beschreibungen.
    Diese Namen können mit dem 'vserver_get_logs' Tool verwendet werden.
    
    Returns:
        str: Liste der verfügbaren Log-Dateien im Markdown-Format
    """
    config: Config = ctx.request_context.lifespan_context["config"]
    
    md = "# Verfügbare Log-Dateien\n\n"
    
    if not config.monitoring.logs:
        return "Keine Log-Dateien in der Konfiguration definiert."
    
    for log in config.monitoring.logs:
        md += f"## {log.name}\n"
        md += f"- **Pfad:** `{log.path}`\n"
        if log.description:
            md += f"- **Beschreibung:** {log.description}\n"
        md += "\n"
    
    return md


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import sys

    # Wechsle ins Verzeichnis des Skripts, damit config.yaml gefunden wird
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)

    # Prüfe ob config.yaml existiert
    if not os.path.exists("config.yaml"):
        # WICHTIG: Fehler auf stderr ausgeben, da stdout für MCP-Protokoll reserviert ist
        print("FEHLER: config.yaml nicht gefunden!", file=sys.stderr)
        print(f"Erwartet in: {script_dir}/config.yaml", file=sys.stderr)
        print("Bitte erstelle eine config.yaml basierend auf config.example.yaml", file=sys.stderr)
        sys.exit(1)

    # Server starten
    mcp.run()
