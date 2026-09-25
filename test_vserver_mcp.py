#!/usr/bin/env python3
"""
Unit Tests für vServer Monitoring MCP Server

Verwendet das Standard unittest Framework mit Mocking für SSH-Verbindungen.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json
from pathlib import Path

from vserver_mcp import (
    # Configuration Models
    ServerConfig,
    LogConfig,
    NetworkConfig,
    ThresholdsConfig,
    SystemConfig,
    MonitoringConfig,
    Config,
    # SSH Client
    SSHClient,
    # Helper Functions
    load_config,
    format_bytes,
    parse_system_metrics,
    parse_network_info,
    format_system_metrics_markdown,
    format_network_info_markdown,
    # Input Models
    ResponseFormat,
    SystemMetricsInput,
    LogInput,
    NetworkInfoInput,
    HealthCheckInput,
)


# ============================================================================
# Test Configuration Models
# ============================================================================

class TestServerConfig(unittest.TestCase):
    """Tests für ServerConfig Model."""

    def test_server_config_minimal(self):
        """Test mit minimalen erforderlichen Feldern."""
        config = ServerConfig(
            host="example.com",
            username="root",
            ssh_key_path="~/.ssh/id_rsa"
        )
        self.assertEqual(config.host, "example.com")
        self.assertEqual(config.port, 22)  # Default
        self.assertEqual(config.username, "root")
        self.assertEqual(config.timeout, 10)  # Default
        self.assertIsNone(config.ssh_key_passphrase)

    def test_server_config_full(self):
        """Test mit allen Feldern."""
        config = ServerConfig(
            host="example.com",
            port=2222,
            username="admin",
            ssh_key_path="/path/to/key",
            ssh_key_passphrase="secret",
            timeout=30
        )
        self.assertEqual(config.port, 2222)
        self.assertEqual(config.ssh_key_passphrase, "secret")
        self.assertEqual(config.timeout, 30)


class TestLogConfig(unittest.TestCase):
    """Tests für LogConfig Model."""

    def test_log_config_minimal(self):
        """Test mit minimalen Feldern."""
        config = LogConfig(path="/var/log/syslog", name="syslog")
        self.assertEqual(config.path, "/var/log/syslog")
        self.assertEqual(config.name, "syslog")
        self.assertIsNone(config.description)

    def test_log_config_with_description(self):
        """Test mit Beschreibung."""
        config = LogConfig(
            path="/var/log/auth.log",
            name="auth",
            description="Authentifizierungs-Logs"
        )
        self.assertEqual(config.description, "Authentifizierungs-Logs")


class TestThresholdsConfig(unittest.TestCase):
    """Tests für ThresholdsConfig Model."""

    def test_default_thresholds(self):
        """Test der Default-Werte."""
        config = ThresholdsConfig()
        self.assertEqual(config.cpu_warning, 80.0)
        self.assertEqual(config.cpu_critical, 95.0)
        self.assertEqual(config.memory_warning, 80.0)
        self.assertEqual(config.memory_critical, 95.0)
        self.assertEqual(config.disk_warning, 80.0)
        self.assertEqual(config.disk_critical, 95.0)

    def test_custom_thresholds(self):
        """Test mit benutzerdefinierten Werten."""
        config = ThresholdsConfig(
            cpu_warning=70.0,
            cpu_critical=90.0
        )
        self.assertEqual(config.cpu_warning, 70.0)
        self.assertEqual(config.cpu_critical, 90.0)


class TestNetworkConfig(unittest.TestCase):
    """Tests für NetworkConfig Model."""

    def test_default_network_config(self):
        """Test der Default-Werte."""
        config = NetworkConfig()
        self.assertTrue(config.check_ports)
        self.assertTrue(config.check_connections)
        self.assertIsNone(config.monitored_ports)

    def test_network_config_with_ports(self):
        """Test mit überwachten Ports."""
        config = NetworkConfig(monitored_ports=[22, 80, 443])
        self.assertEqual(config.monitored_ports, [22, 80, 443])


class TestConfig(unittest.TestCase):
    """Tests für die Haupt-Config."""

    def test_full_config(self):
        """Test einer vollständigen Konfiguration."""
        config = Config(
            server=ServerConfig(
                host="test.example.com",
                username="testuser",
                ssh_key_path="~/.ssh/test_key"
            ),
            monitoring=MonitoringConfig(
                logs=[
                    LogConfig(path="/var/log/syslog", name="syslog")
                ]
            )
        )
        self.assertEqual(config.server.host, "test.example.com")
        self.assertEqual(len(config.monitoring.logs), 1)


# ============================================================================
# Test Helper Functions
# ============================================================================

class TestFormatBytes(unittest.TestCase):
    """Tests für format_bytes Funktion."""

    def test_bytes(self):
        """Test für Bytes."""
        self.assertEqual(format_bytes(500), "500.00 B")

    def test_kilobytes(self):
        """Test für Kilobytes."""
        self.assertEqual(format_bytes(1024), "1.00 KB")
        self.assertEqual(format_bytes(2048), "2.00 KB")

    def test_megabytes(self):
        """Test für Megabytes."""
        self.assertEqual(format_bytes(1024 * 1024), "1.00 MB")

    def test_gigabytes(self):
        """Test für Gigabytes."""
        self.assertEqual(format_bytes(1024 * 1024 * 1024), "1.00 GB")

    def test_terabytes(self):
        """Test für Terabytes."""
        self.assertEqual(format_bytes(1024 ** 4), "1.00 TB")

    def test_petabytes(self):
        """Test für Petabytes."""
        self.assertEqual(format_bytes(1024 ** 5), "1.00 PB")

    def test_zero_bytes(self):
        """Test für 0 Bytes."""
        self.assertEqual(format_bytes(0), "0.00 B")


class TestLoadConfig(unittest.TestCase):
    """Tests für load_config Funktion."""

    def test_load_valid_config(self):
        """Test mit gültiger Konfigurationsdatei."""
        config_content = """
server:
  host: test.example.com
  username: testuser
  ssh_key_path: ~/.ssh/id_rsa
monitoring:
  logs:
    - path: /var/log/syslog
      name: syslog
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            config = load_config(temp_path)
            self.assertEqual(config.server.host, "test.example.com")
            self.assertEqual(len(config.monitoring.logs), 1)
        finally:
            os.unlink(temp_path)

    def test_load_missing_config(self):
        """Test mit nicht existierender Datei."""
        with self.assertRaises(Exception) as context:
            load_config("/nonexistent/config.yaml")
        self.assertIn("nicht gefunden", str(context.exception))

    def test_load_invalid_yaml(self):
        """Test mit ungültigem YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            with self.assertRaises(Exception) as context:
                load_config(temp_path)
            self.assertIn("YAML-Fehler", str(context.exception))
        finally:
            os.unlink(temp_path)


# ============================================================================
# Test SSH Client
# ============================================================================

class TestSSHClient(unittest.TestCase):
    """Tests für SSHClient Klasse."""

    def setUp(self):
        """Setup für Tests."""
        self.server_config = ServerConfig(
            host="test.example.com",
            username="testuser",
            ssh_key_path="~/.ssh/id_rsa"
        )

    def test_expand_path(self):
        """Test für _expand_path."""
        client = SSHClient(self.server_config)
        expanded = client._expand_path("~/test")
        self.assertIn(str(Path.home()), expanded)

    def test_execute_without_connection(self):
        """Test execute_command ohne Verbindung."""
        client = SSHClient(self.server_config)
        with self.assertRaises(Exception) as context:
            client.execute_command("hostname")
        self.assertIn("Keine SSH-Verbindung", str(context.exception))

    @patch('vserver_mcp.paramiko.SSHClient')
    @patch('vserver_mcp.paramiko.Ed25519Key')
    def test_context_manager(self, mock_key_class, mock_ssh_class):
        """Test des Context Managers."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client
        mock_key_class.from_private_key_file.return_value = MagicMock()

        with SSHClient(self.server_config) as client:
            self.assertIsNotNone(client)

        mock_client.close.assert_called_once()

    @patch('vserver_mcp.paramiko.SSHClient')
    @patch('vserver_mcp.paramiko.Ed25519Key')
    def test_execute_command_success(self, mock_key_class, mock_ssh_class):
        """Test erfolgreiche Befehlsausführung."""
        mock_client = MagicMock()
        mock_ssh_class.return_value = mock_client
        mock_key_class.from_private_key_file.return_value = MagicMock()

        # Mock exec_command
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"test-hostname"
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_client.exec_command.return_value = (None, mock_stdout, mock_stderr)

        with SSHClient(self.server_config) as client:
            stdout, stderr, exit_code = client.execute_command("hostname")

        self.assertEqual(stdout, "test-hostname")
        self.assertEqual(exit_code, 0)


# ============================================================================
# Test Parsing Functions
# ============================================================================

class TestParseSystemMetrics(unittest.TestCase):
    """Tests für parse_system_metrics Funktion."""

    def _create_mock_ssh(self, loadavg="0.5 0.3 0.2 1/234 5678", nproc="4",
                         total_mem="16000000", used_mem="8000000", free_mem="4000000",
                         total_disk="100000000", used_disk="50000000", free_disk="50000000",
                         uptime="up 5 days"):
        """Erstellt einen Mock SSH Client."""
        mock_ssh = MagicMock()

        def execute_command(cmd):
            if "loadavg" in cmd:
                return (loadavg, "", 0)
            elif "nproc" in cmd:
                return (nproc, "", 0)
            elif "free" in cmd:
                # Format wie echtes free -b Output
                output = f"              total        used        free      shared  buff/cache   available\n"
                output += f"Mem:    {total_mem}  {used_mem}  {free_mem}        0        0        0"
                return (output, "", 0)
            elif "df" in cmd:
                output = f"Filesystem     1B-blocks    Used Available Use% Mounted on\n"
                output += f"/dev/sda1 {total_disk} {used_disk} {free_disk} 50% /"
                return (output, "", 0)
            elif "uptime" in cmd:
                return (uptime, "", 0)
            return ("", "", 0)

        mock_ssh.execute_command = execute_command
        return mock_ssh

    def test_parse_basic_metrics(self):
        """Test grundlegender Metriken."""
        mock_ssh = self._create_mock_ssh()
        metrics = parse_system_metrics(mock_ssh)

        self.assertIn('load_average', metrics)
        self.assertIn('cpu_cores', metrics)
        self.assertIn('memory', metrics)
        self.assertIn('disk', metrics)
        self.assertIn('uptime', metrics)

    def test_load_average_parsing(self):
        """Test Load Average Parsing."""
        mock_ssh = self._create_mock_ssh(loadavg="1.5 2.0 1.0 1/234 5678")
        metrics = parse_system_metrics(mock_ssh)

        self.assertEqual(metrics['load_average']['1min'], 1.5)
        self.assertEqual(metrics['load_average']['5min'], 2.0)
        self.assertEqual(metrics['load_average']['15min'], 1.0)

    def test_cpu_usage_calculation(self):
        """Test CPU-Auslastung Berechnung."""
        mock_ssh = self._create_mock_ssh(loadavg="2.0 1.0 0.5", nproc="4")
        metrics = parse_system_metrics(mock_ssh)

        # 2.0 / 4 * 100 = 50%
        self.assertEqual(metrics['cpu_usage_percent'], 50.0)

    def test_warnings_cpu_critical(self):
        """Test CPU Critical Warnung."""
        thresholds = ThresholdsConfig(cpu_warning=80.0, cpu_critical=95.0)
        # Load 4.0 auf 4 Cores = 100%
        mock_ssh = self._create_mock_ssh(loadavg="4.0 3.0 2.0", nproc="4")
        metrics = parse_system_metrics(mock_ssh, thresholds)

        self.assertIn('warnings', metrics)
        self.assertTrue(any('CRITICAL' in w and 'CPU' in w for w in metrics['warnings']))

    def test_warnings_cpu_warning(self):
        """Test CPU Warning Warnung."""
        thresholds = ThresholdsConfig(cpu_warning=80.0, cpu_critical=95.0)
        # Load 3.5 auf 4 Cores = 87.5%
        mock_ssh = self._create_mock_ssh(loadavg="3.5 3.0 2.0", nproc="4")
        metrics = parse_system_metrics(mock_ssh, thresholds)

        self.assertIn('warnings', metrics)
        self.assertTrue(any('WARNING' in w and 'CPU' in w for w in metrics['warnings']))

    def test_no_warnings_when_below_threshold(self):
        """Test keine Warnungen unter Schwellenwert."""
        thresholds = ThresholdsConfig()
        mock_ssh = self._create_mock_ssh(loadavg="0.5 0.3 0.2", nproc="4")
        metrics = parse_system_metrics(mock_ssh, thresholds)

        self.assertIn('warnings', metrics)
        self.assertEqual(len(metrics['warnings']), 0)


class TestParseNetworkInfo(unittest.TestCase):
    """Tests für parse_network_info Funktion."""

    def _create_mock_ssh(self, ss_output="", connections="5", ip_output=""):
        """Erstellt einen Mock SSH Client."""
        mock_ssh = MagicMock()

        def execute_command(cmd):
            if "ss -tlnp" in cmd:
                return (ss_output, "", 0)
            elif "ss -ant" in cmd:
                return (connections, "", 0)
            elif "ip -br addr" in cmd:
                return (ip_output, "", 0)
            return ("", "", 0)

        mock_ssh.execute_command = execute_command
        return mock_ssh

    def test_parse_listening_ports(self):
        """Test Parsing von Listening Ports."""
        ss_output = """State  Recv-Q Send-Q  Local Address:Port   Peer Address:Port
LISTEN 0      128           0.0.0.0:22          0.0.0.0:*
LISTEN 0      128           0.0.0.0:80          0.0.0.0:*
LISTEN 0      128           0.0.0.0:443         0.0.0.0:*"""
        mock_ssh = self._create_mock_ssh(ss_output=ss_output)
        network = parse_network_info(mock_ssh)

        self.assertIn('listening_ports', network)
        self.assertIn(22, network['listening_ports'])
        self.assertIn(80, network['listening_ports'])
        self.assertIn(443, network['listening_ports'])

    def test_parse_active_connections(self):
        """Test Parsing aktiver Verbindungen."""
        mock_ssh = self._create_mock_ssh(connections="42")
        network = parse_network_info(mock_ssh)

        self.assertEqual(network['active_connections'], 42)

    def test_parse_interfaces(self):
        """Test Parsing von Netzwerk-Interfaces."""
        ip_output = """lo               UNKNOWN        127.0.0.1/8 ::1/128
eth0             UP             192.168.1.100/24 fe80::1/64"""
        mock_ssh = self._create_mock_ssh(ip_output=ip_output)
        network = parse_network_info(mock_ssh)

        self.assertEqual(len(network['interfaces']), 2)
        self.assertEqual(network['interfaces'][0]['name'], 'lo')
        self.assertEqual(network['interfaces'][1]['name'], 'eth0')
        self.assertEqual(network['interfaces'][1]['state'], 'UP')


# ============================================================================
# Test Markdown Formatting
# ============================================================================

class TestFormatSystemMetricsMarkdown(unittest.TestCase):
    """Tests für format_system_metrics_markdown Funktion."""

    def test_basic_formatting(self):
        """Test grundlegende Formatierung."""
        metrics = {
            'uptime': 'up 5 days',
            'cpu_cores': 4,
            'cpu_usage_percent': 25.0,
            'load_average': {'1min': 1.0, '5min': 0.8, '15min': 0.5},
            'memory': {
                'total_formatted': '16.00 GB',
                'used_formatted': '8.00 GB',
                'free_formatted': '8.00 GB',
                'usage_percent': 50.0
            },
            'disk': {
                'total_formatted': '100.00 GB',
                'used_formatted': '50.00 GB',
                'free_formatted': '50.00 GB',
                'usage_percent': 50.0
            }
        }
        md = format_system_metrics_markdown(metrics)

        self.assertIn("# System-Metriken", md)
        self.assertIn("up 5 days", md)
        self.assertIn("25.0%", md)
        self.assertIn("16.00 GB", md)

    def test_formatting_with_warnings(self):
        """Test Formatierung mit Warnungen."""
        metrics = {
            'uptime': 'up 1 day',
            'cpu_cores': 2,
            'cpu_usage_percent': 95.0,
            'load_average': {'1min': 2.0, '5min': 1.5, '15min': 1.0},
            'memory': {
                'total_formatted': '8.00 GB',
                'used_formatted': '7.60 GB',
                'free_formatted': '0.40 GB',
                'usage_percent': 95.0
            },
            'disk': {
                'total_formatted': '50.00 GB',
                'used_formatted': '48.00 GB',
                'free_formatted': '2.00 GB',
                'usage_percent': 96.0
            },
            'warnings': [
                'CRITICAL: CPU-Auslastung bei 95.0%',
                'CRITICAL: RAM-Auslastung bei 95.0%'
            ]
        }
        md = format_system_metrics_markdown(metrics)

        self.assertIn("Warnungen", md)
        self.assertIn("CRITICAL", md)


class TestFormatNetworkInfoMarkdown(unittest.TestCase):
    """Tests für format_network_info_markdown Funktion."""

    def test_basic_formatting(self):
        """Test grundlegende Formatierung."""
        network = {
            'listening_ports': [22, 80, 443],
            'active_connections': 10,
            'interfaces': [
                {'name': 'eth0', 'state': 'UP', 'addresses': ['192.168.1.100/24']}
            ]
        }
        md = format_network_info_markdown(network)

        self.assertIn("# Netzwerk-Informationen", md)
        self.assertIn("Port 22", md)
        self.assertIn("Port 80", md)
        self.assertIn("10", md)
        self.assertIn("eth0", md)

    def test_empty_ports(self):
        """Test mit leerer Port-Liste."""
        network = {
            'listening_ports': [],
            'active_connections': 0,
            'interfaces': []
        }
        md = format_network_info_markdown(network)

        self.assertIn("Keine offenen Ports gefunden", md)


# ============================================================================
# Test Input Models
# ============================================================================

class TestInputModels(unittest.TestCase):
    """Tests für Input Models."""

    def test_system_metrics_input_default(self):
        """Test SystemMetricsInput mit Default-Werten."""
        input_model = SystemMetricsInput()
        self.assertEqual(input_model.response_format, ResponseFormat.MARKDOWN)

    def test_system_metrics_input_json(self):
        """Test SystemMetricsInput mit JSON-Format."""
        input_model = SystemMetricsInput(response_format=ResponseFormat.JSON)
        self.assertEqual(input_model.response_format, ResponseFormat.JSON)

    def test_log_input_validation(self):
        """Test LogInput Validierung."""
        input_model = LogInput(log_name="syslog", lines=50)
        self.assertEqual(input_model.log_name, "syslog")
        self.assertEqual(input_model.lines, 50)

    def test_log_input_lines_range(self):
        """Test LogInput Zeilen-Bereich."""
        # Minimum
        input_model = LogInput(log_name="test", lines=1)
        self.assertEqual(input_model.lines, 1)

        # Maximum
        input_model = LogInput(log_name="test", lines=10000)
        self.assertEqual(input_model.lines, 10000)

    def test_health_check_input_defaults(self):
        """Test HealthCheckInput mit Default-Werten."""
        input_model = HealthCheckInput()
        self.assertTrue(input_model.include_logs)
        self.assertEqual(input_model.log_lines, 50)

    def test_health_check_input_custom(self):
        """Test HealthCheckInput mit benutzerdefinierten Werten."""
        input_model = HealthCheckInput(include_logs=False, log_lines=100)
        self.assertFalse(input_model.include_logs)
        self.assertEqual(input_model.log_lines, 100)


# ============================================================================
# Test Response Format Enum
# ============================================================================

class TestResponseFormat(unittest.TestCase):
    """Tests für ResponseFormat Enum."""

    def test_enum_values(self):
        """Test Enum-Werte."""
        self.assertEqual(ResponseFormat.MARKDOWN.value, "markdown")
        self.assertEqual(ResponseFormat.JSON.value, "json")

    def test_enum_from_string(self):
        """Test Enum aus String."""
        self.assertEqual(ResponseFormat("markdown"), ResponseFormat.MARKDOWN)
        self.assertEqual(ResponseFormat("json"), ResponseFormat.JSON)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == '__main__':
    unittest.main(verbosity=2)
