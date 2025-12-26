#!/usr/bin/env python3
"""
VersionOps Linux Agent
Automatically discovers and reports application versions to the VersionOps platform
"""

import re
import os
import sys
import json
import time
import socket
import logging
import platform
import subprocess
import argparse
import shlex
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

try:
    import requests
except ImportError:
    print("Error: 'requests' module not found. Install with: pip install requests")
    sys.exit(1)

# Agent version
VERSION = "1.0.0"

# Default configuration
DEFAULT_CONFIG = {
    "backend_url": "",
    "service_token": "",
    "hostname": socket.gethostname(),
    "collection_interval": 300,  # 5 minutes
    "log_level": "INFO",
    "log_file": "/var/log/versionops-agent.log",
    "config_file": "/etc/versionops-agent/config.json",
}

# Systemd service template
SYSTEMD_SERVICE = """[Unit]
Description=VersionOps Agent
After=network.target

[Service]
Type=simple
ExecStart={agent_path} --daemon --config {config_path}
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
"""

@dataclass
class ApplicationInfo:
    """Application information structure"""
    name: str
    version: str
    path: str
    detection_method: str = "auto"
    detected_at: str = None
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.utcnow().isoformat()


class VersionOpsAgent:
    """Main VersionOps Agent class"""
    
    def __init__(self, config_file: str = None):
        self.config = DEFAULT_CONFIG.copy()
        self.config_file = config_file or DEFAULT_CONFIG["config_file"]
        self.logger = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"VersionOps-Agent/{VERSION}"
        })
        self.running = False
        self.host_id = None
        self.plugins = {}
        
        # Load configuration
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                self.config.update(file_config)
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            config_dir = os.path.dirname(self.config_file)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"Configuration saved to {self.config_file}")
            return True
        except PermissionError:
            print(f"Error: Permission denied. Run with sudo to save to {self.config_file}")
            return False
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config["log_level"].upper(), logging.INFO)
        
        handlers = [logging.StreamHandler(sys.stdout)]
        
        # Try to add file handler
        try:
            log_dir = os.path.dirname(self.config["log_file"])
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            handlers.append(logging.FileHandler(self.config["log_file"]))
        except PermissionError:
            print(f"Warning: Cannot write to {self.config['log_file']}, logging to stdout only")
        except Exception as e:
            print(f"Warning: Log file error: {e}")
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers,
            force=True
        )
        
        self.logger = logging.getLogger("versionops-agent")
        self.logger.setLevel(log_level)
    
    def validate_config(self) -> bool:
        """Validate that required configuration is present"""
        if not self.config.get("backend_url"):
            print("Error: Backend URL not configured. Run: versionops-agent config --backend=URL")
            return False
        if not self.config.get("service_token"):
            print("Error: Service token not configured. Run: versionops-agent config --token=TOKEN")
            return False
        return True
    
    def authenticate(self) -> bool:
        """Authenticate with VersionOps server using service token"""
        if not self.config.get("service_token"):
            self.logger.error("No service token configured")
            return False
        
        try:
            self.session.headers.update({
                "Authorization": f"Bearer {self.config['service_token']}"
            })
            
            # Test the token
            test_url = f"{self.config['backend_url']}/api/agent/application-configs"
            response = self.session.get(test_url, timeout=10)
            
            if response.status_code == 200:
                self.logger.info("Successfully authenticated")
                return True
            elif response.status_code == 401:
                self.logger.error("Authentication failed - invalid or inactive token")
                return False
            elif response.status_code == 403:
                self.logger.error("Authentication failed - insufficient permissions")
                return False
            else:
                self.logger.error(f"Authentication failed: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Cannot connect to {self.config['backend_url']}")
            return False
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False

    def load_plugins(self):
        """Load discovery plugins from server configuration"""
        try:
            config_url = f"{self.config['backend_url']}/api/agent/application-configs"
            response = self.session.get(config_url, timeout=30)
            
            if response.status_code == 200:
                app_configs = response.json()
                self.logger.info(f"Loaded {len(app_configs)} application configurations")
                
                for config in app_configs:
                    plugin_name = config["name"]
                    try:
                        plugin = DynamicPlugin(config, self.config, self.logger)
                        self.plugins[plugin_name] = plugin
                        self.logger.debug(f"Created plugin: {plugin_name}")
                    except Exception as e:
                        self.logger.error(f"Failed to create plugin {plugin_name}: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to load configurations from server: {e}")

    def register_host(self) -> bool:
        """Register this host with the VersionOps server"""
        try:
            register_url = f"{self.config['backend_url']}/api/agent/register"
            
            host_data = {
                "hostname": self.config["hostname"],
                "ip_address": self.get_ip_address(),
                "os_type": platform.system().lower(),
                "agent_version": VERSION
            }
            
            response = self.session.post(register_url, json=host_data, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.host_id = data.get("host_id")
                self.logger.info(f"Host registered with ID: {self.host_id}")
                return True
            else:
                self.logger.error(f"Host registration failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Host registration error: {e}")
            return False
    
    def get_ip_address(self) -> str:
        """Get the primary IP address of this host"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def discover_applications(self) -> List[ApplicationInfo]:
        """Discover applications using plugins"""
        discovered_apps = []
        
        for plugin_name, plugin in self.plugins.items():
            try:
                self.logger.debug(f"Running plugin: {plugin_name}")
                apps = plugin.discover()
                discovered_apps.extend(apps)
                if apps:
                    self.logger.info(f"Plugin {plugin_name} found {len(apps)} applications")
            except Exception as e:
                self.logger.error(f"Plugin {plugin_name} failed: {e}")
        
        return discovered_apps
    
    def report_applications(self, applications: List[ApplicationInfo]) -> bool:
        """Report discovered applications to VersionOps server"""
        if not self.host_id:
            self.logger.error("No host ID available")
            return False
        
        try:
            for app in applications:
                app_url = f"{self.config['backend_url']}/api/hosts/{self.host_id}/applications"
                response = self.session.post(app_url, json=asdict(app), timeout=30)
                
                if response.status_code == 200:
                    self.logger.info(f"Reported: {app.name} v{app.version}")
                else:
                    self.logger.error(f"Failed to report {app.name}: {response.status_code}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error reporting applications: {e}")
            return False
    
    def collection_cycle(self):
        """Perform one collection cycle"""
        self.logger.info("Starting discovery cycle")
        
        applications = self.discover_applications()
        
        if applications:
            self.logger.info(f"Discovered {len(applications)} applications")
            self.report_applications(applications)
        else:
            self.logger.info("No applications discovered")
    
    def run_daemon(self):
        """Run as daemon with periodic collection"""
        self.setup_logging()
        self.logger.info(f"Starting VersionOps Agent v{VERSION}")
        self.running = True
        
        if not self.authenticate():
            self.logger.error("Authentication failed, exiting")
            return 1
        
        self.load_plugins()
        
        if not self.register_host():
            self.logger.error("Host registration failed, exiting")
            return 1
        
        while self.running:
            try:
                self.collection_cycle()
                self.logger.debug(f"Sleeping for {self.config['collection_interval']}s")
                time.sleep(self.config['collection_interval'])
            except KeyboardInterrupt:
                self.logger.info("Shutting down")
                self.running = False
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(60)
        
        return 0
    
    def run_once(self) -> int:
        """Run collection once and exit"""
        self.setup_logging()
        self.logger.info(f"VersionOps Agent v{VERSION} - one-shot mode")
        
        if not self.authenticate():
            return 1
        
        self.load_plugins()
        
        if not self.register_host():
            return 1
        
        self.collection_cycle()
        return 0
    
    def stop(self):
        """Stop the agent"""
        self.running = False


class DynamicPlugin:
    """Dynamic plugin for application discovery based on server configuration"""
    
    def __init__(self, app_config: Dict, agent_config: Dict, logger: logging.Logger):
        self.app_config = app_config
        self.agent_config = agent_config
        self.logger = logger
        
    def run_command(self, cmd) -> Tuple[str, str, int]:
        """Run a system command"""
        try:
            if isinstance(cmd, list):
                cmd_str = ' '.join(cmd)
            else:
                cmd_str = cmd
            
            if '|' in cmd_str:
                result = subprocess.run(cmd_str, capture_output=True, text=True, timeout=30, shell=True)
            else:
                if isinstance(cmd, str):
                    cmd = shlex.split(cmd)
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timeout", 1
        except Exception as e:
            return "", str(e), 1
    
    def discover(self) -> List[ApplicationInfo]:
        """Discover application based on configuration"""
        apps = []
        
        try:
            paths = self.app_config.get("default_paths", [])
            
            for path in paths:
                if os.path.exists(path):
                    version = self.get_version(path)
                    if version:
                        app = ApplicationInfo(
                            name=self.app_config["name"],
                            version=version,
                            path=path,
                            detection_method="dynamic_plugin"
                        )
                        apps.append(app)
                        self.logger.info(f"Found {self.app_config.get('display_name', self.app_config['name'])} v{version}")
            
            return apps
        except Exception as e:
            self.logger.error(f"Discovery error for {self.app_config.get('name')}: {e}")
            return []
        
    def get_version(self, path: str) -> Optional[str]:
        """Get application version using configured method"""
        try:
            version_cmd = self.app_config.get("version_command", "--version")
            
            if isinstance(version_cmd, str) and '|' in version_cmd:
                if '{path}' in version_cmd:
                    cmd = version_cmd.replace('{path}', path)
                else:
                    cmd = version_cmd
            elif isinstance(version_cmd, str):
                if version_cmd.startswith('--') or version_cmd.startswith('-'):
                    cmd = [path, version_cmd]
                else:
                    cmd_parts = shlex.split(version_cmd)
                    cmd = [path] + cmd_parts[1:] if len(cmd_parts) > 1 else [path, "--version"]
            else:
                cmd = [path] + version_cmd
                
            stdout, stderr, exit_code = self.run_command(cmd)
            
            if exit_code == 0:
                pattern = self.app_config.get("version_regex", r'(\d+\.\d+\.\d+)')
                
                version_match = re.search(pattern, stdout)
                if version_match:
                    return version_match.group(1)
                
                version_match = re.search(pattern, stderr)
                if version_match:
                    return version_match.group(1)
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting version from {path}: {e}")
            return None


def cmd_config(args):
    """Handle config command"""
    agent = VersionOpsAgent(config_file=args.config)
    
    if args.backend:
        agent.config['backend_url'] = args.backend.rstrip('/')
        print(f"Backend URL set to: {agent.config['backend_url']}")
    
    if args.token:
        agent.config['service_token'] = args.token
        print("Service token configured")
    
    if args.hostname:
        agent.config['hostname'] = args.hostname
        print(f"Hostname set to: {args.hostname}")
    
    if args.interval:
        agent.config['collection_interval'] = args.interval
        print(f"Collection interval set to: {args.interval}s")
    
    if args.backend or args.token or args.hostname or args.interval:
        if agent.save_config():
            return 0
        return 1
    
    # Show current config
    print("\nCurrent configuration:")
    print(f"  Config file: {agent.config_file}")
    print(f"  Backend URL: {agent.config.get('backend_url') or '(not set)'}")
    print(f"  Token: {'***configured***' if agent.config.get('service_token') else '(not set)'}")
    print(f"  Hostname: {agent.config.get('hostname')}")
    print(f"  Interval: {agent.config.get('collection_interval')}s")
    return 0


def cmd_install(args):
    """Install systemd service"""
    agent_path = os.path.abspath(sys.argv[0])
    config_path = args.config or DEFAULT_CONFIG["config_file"]
    
    service_content = SYSTEMD_SERVICE.format(
        agent_path=agent_path,
        config_path=config_path
    )
    
    service_file = "/etc/systemd/system/versionops-agent.service"
    
    try:
        with open(service_file, 'w') as f:
            f.write(service_content)
        print(f"Service file created: {service_file}")
        
        # Reload systemd
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        print("Systemd reloaded")
        
        print("\nTo start the agent:")
        print("  sudo systemctl enable --now versionops-agent")
        print("\nTo check status:")
        print("  sudo systemctl status versionops-agent")
        return 0
    except PermissionError:
        print("Error: Permission denied. Run with sudo")
        return 1
    except Exception as e:
        print(f"Error installing service: {e}")
        return 1


def cmd_run(args):
    """Run the agent"""
    agent = VersionOpsAgent(config_file=args.config)
    
    if args.token:
        agent.config['service_token'] = args.token
    if args.backend:
        agent.config['backend_url'] = args.backend.rstrip('/')
    
    if args.verbose:
        agent.config["log_level"] = "DEBUG"
    
    if not agent.validate_config():
        return 1
    
    if args.daemon:
        return agent.run_daemon()
    else:
        return agent.run_once()


def cmd_status(args):
    """Check agent status"""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "versionops-agent"],
            capture_output=True, text=True
        )
        status = result.stdout.strip()
        
        if status == "active":
            print("✅ VersionOps Agent is running")
        else:
            print(f"⚠️  VersionOps Agent is {status}")
        
        # Show recent logs
        print("\nRecent logs:")
        subprocess.run(["journalctl", "-u", "versionops-agent", "-n", "5", "--no-pager"])
        return 0
    except Exception as e:
        print(f"Error checking status: {e}")
        return 1


def cmd_version(args):
    """Show version"""
    print(f"VersionOps Agent v{VERSION}")
    print(f"Platform: {platform.system()} {platform.machine()}")
    return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='VersionOps Agent - Application version discovery and reporting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  versionops-agent config --backend=https://app.versionops.io --token=YOUR_TOKEN
  versionops-agent install
  versionops-agent run --once
  versionops-agent run --daemon
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configure the agent')
    config_parser.add_argument('--backend', '-b', help='Backend URL')
    config_parser.add_argument('--token', '-t', help='Service token')
    config_parser.add_argument('--hostname', help='Override hostname')
    config_parser.add_argument('--interval', type=int, help='Collection interval in seconds')
    config_parser.add_argument('--config', '-c', help='Config file path')
    config_parser.set_defaults(func=cmd_config)
    
    # Install command
    install_parser = subparsers.add_parser('install', help='Install systemd service')
    install_parser.add_argument('--config', '-c', help='Config file path')
    install_parser.set_defaults(func=cmd_install)
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run the agent')
    run_parser.add_argument('--daemon', '-d', action='store_true', help='Run as daemon')
    run_parser.add_argument('--once', '-o', action='store_true', help='Run once and exit')
    run_parser.add_argument('--config', '-c', help='Config file path')
    run_parser.add_argument('--token', '-t', help='Override service token')
    run_parser.add_argument('--backend', '-b', help='Override backend URL')
    run_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    run_parser.set_defaults(func=cmd_run)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check agent status')
    status_parser.set_defaults(func=cmd_status)
    
    # Version command
    version_parser = subparsers.add_parser('version', help='Show version')
    version_parser.set_defaults(func=cmd_version)
    
    # Parse args
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
