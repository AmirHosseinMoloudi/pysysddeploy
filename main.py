#!/usr/bin/env python3

# PySysdDeploy_Wizard_CLI_for_Automated_Customizable_Python_Daemon_Systemd_Service_Unit_Generation_and_Deployment_Provisioning_on_Ubuntu

"""
PySysdDeploy: Python Systemd Service Deployment Wizard using Ray
A CLI tool for creating and managing Python daemon services as systemd units on Ubuntu
"""

import os
import sys
import argparse
import getpass
import subprocess
import time
from pathlib import Path
import ray
import jinja2
import json

# Initialize Ray for parallelism
ray.init(ignore_reinit_error=True)

# Templates for systemd service files
STANDARD_PYTHON_TEMPLATE = """
[Unit]
Description={{ description }}
After=network.target

[Service]
ExecStart=/bin/bash -c "source {{ venv_path }}/bin/activate && python3 {{ script_path }} {{ script_args }}"
WorkingDirectory={{ working_directory }}
User={{ user }}
Group={{ group }}
Restart={{ restart_policy }}
RestartSec={{ restart_sec }}
Environment="PATH={{ venv_path }}/bin:$PATH"
Environment="PYTHONUNBUFFERED=1"
{% if additional_env_vars %}{% for var in additional_env_vars %}
Environment="{{ var }}"{% endfor %}{% endif %}

[Install]
WantedBy=multi-user.target
"""

GUNICORN_TEMPLATE = """
[Unit]
Description={{ description }}
After=network.target

[Service]
ExecStart=/bin/bash -c "source {{ venv_path }}/bin/activate && gunicorn --bind {{ bind_address }} {{ app_module }}"
WorkingDirectory={{ working_directory }}
User={{ user }}
Group={{ group }}
Restart={{ restart_policy }}
RestartSec={{ restart_sec }}
Environment="PATH={{ venv_path }}/bin:$PATH"
Environment="PYTHONUNBUFFERED=1"
{% if additional_env_vars %}{% for var in additional_env_vars %}
Environment="{{ var }}"{% endfor %}{% endif %}

[Install]
WantedBy=multi-user.target
"""

# Store available templates in a dictionary for easy access
TEMPLATES = {
    "standard_python": {
        "name": "Standard Python Script",
        "description": "Run a Python script in a virtual environment",
        "template": STANDARD_PYTHON_TEMPLATE
    },
    "gunicorn": {
        "name": "Gunicorn Web Application",
        "description": "Run a Flask/Django app with Gunicorn",
        "template": GUNICORN_TEMPLATE
    }
}

@ray.remote
def validate_python_script(script_path):
    """Validate if the Python script exists."""
    path = Path(script_path)
    if not path.exists():
        return False, f"Script {script_path} does not exist"
    if not path.is_file():
        return False, f"{script_path} is not a file"
    return True, "Script is valid"

@ray.remote
def validate_venv(venv_path):
    """Validate if the virtual environment exists."""
    activate_script = os.path.join(venv_path, "bin", "activate")
    if not os.path.exists(activate_script):
        return False, f"Virtual environment not found at {venv_path}"
    return True, "Virtual environment is valid"

@ray.remote
def create_service_file(service_name, template_name, context, output_dir):
    """Create a systemd service file from template."""
    try:
        if template_name not in TEMPLATES:
            return False, f"Unknown template: {template_name}"
            
        template = jinja2.Template(TEMPLATES[template_name]["template"])
        service_content = template.render(**context)
        
        # Make sure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        service_path = os.path.join(output_dir, f"{service_name}.service")
        with open(service_path, 'w') as f:
            f.write(service_content)
        return True, service_path
    except Exception as e:
        return False, str(e)

@ray.remote
def deploy_service(service_name, service_path):
    """Deploy the service to systemd."""
    try:
        # Copy to systemd directory
        subprocess.run(['sudo', 'cp', service_path, f'/etc/systemd/system/{service_name}.service'], 
                      check=True)
        
        # Reload systemd to recognize new service
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        
        return True, f"Service {service_name} deployed successfully"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to deploy service: {str(e)}"

@ray.remote
def enable_service(service_name):
    """Enable and start the systemd service."""
    try:
        # Enable service
        subprocess.run(['sudo', 'systemctl', 'enable', service_name], check=True)
        
        # Start service
        subprocess.run(['sudo', 'systemctl', 'start', service_name], check=True)
        
        # Check status
        result = subprocess.run(['systemctl', 'is-active', service_name], 
                                capture_output=True, text=True)
        if result.stdout.strip() == "active":
            return True, f"Service {service_name} is now active and enabled at boot"
        else:
            return False, f"Service {service_name} is not active, check logs with: sudo journalctl -u {service_name}"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to enable/start service: {str(e)}"

@ray.remote
def check_service_status(service_name):
    """Check the status of the deployed service."""
    try:
        result = subprocess.run(['systemctl', 'status', service_name], 
                               capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError:
        return False, f"Failed to get status for {service_name}"

def parse_env_vars(env_string):
    """Parse environment variables from string to list."""
    if not env_string:
        return []
    
    # Split by spaces, but respect quoted values
    parts = []
    current = ""
    in_quotes = False
    for char in env_string:
        if char == '"':
            in_quotes = not in_quotes
            current += char
        elif char == ' ' and not in_quotes:
            if current:
                parts.append(current)
                current = ""
        else:
            current += char
    
    if current:
        parts.append(current)
        
    return parts

def gather_service_info():
    """Interactive wizard to gather service information from user."""
    print("\n=== Python Systemd Deployment Wizard ===")
    
    service_info = {}
    
    # Get service basics
    service_info['name'] = input("Service name: ").strip()
    service_info['description'] = input("Service description: ").strip()
    
    # Choose template
    print("\nAvailable templates:")
    for i, (template_id, template_data) in enumerate(TEMPLATES.items(), 1):
        print(f"{i}) {template_data['name']} - {template_data['description']}")
    
    template_choice = input(f"Select template [1-{len(TEMPLATES)}]: ").strip()
    template_idx = 0  # Default to first template
    if template_choice and template_choice.isdigit():
        template_idx = int(template_choice) - 1 if 0 <= int(template_choice) - 1 < len(TEMPLATES) else 0
    
    template_id = list(TEMPLATES.keys())[template_idx]
    service_info['template'] = template_id
    
    # Get working directory
    default_dir = os.getcwd()
    working_dir = input(f"Working directory [default: {default_dir}]: ").strip()
    service_info['working_directory'] = working_dir if working_dir else default_dir
    
    # Get virtual environment path
    venv_path = input("Path to virtual environment (e.g., /path/to/venv): ").strip()
    service_info['venv_path'] = os.path.abspath(os.path.expanduser(venv_path))
    
    # Template-specific information
    if template_id == "standard_python":
        # Get script details
        script_path = input("Full path to Python script: ").strip()
        service_info['script_path'] = os.path.abspath(os.path.expanduser(script_path))
        
        # Get script arguments
        service_info['script_args'] = input("Script arguments (if any): ").strip()
        
    elif template_id == "gunicorn":
        # Get gunicorn specifics
        bind_address = input("Bind address (e.g., 0.0.0.0:8000): ").strip() or "0.0.0.0:8000"
        service_info['bind_address'] = bind_address
        
        app_module = input("App module (e.g., app:app for Flask or wsgi:application for Django): ").strip()
        service_info['app_module'] = app_module
    
    # Get user/group
    default_user = getpass.getuser()
    user = input(f"User to run the service [default: {default_user}]: ").strip()
    service_info['user'] = user if user else default_user
    
    default_group = default_user
    group = input(f"Group to run the service [default: {default_group}]: ").strip()
    service_info['group'] = group if group else default_group
    
    # Restart policy
    restart_options = ['no', 'always', 'on-success', 'on-failure', 'on-abnormal', 'on-abort', 'on-watchdog']
    print("\nRestart policies:")
    for i, policy in enumerate(restart_options):
        print(f"{i}) {policy}")
    
    restart_choice = input("Select restart policy [default: 1 (always)]: ").strip()
    restart_idx = 1  # Default to 'always'
    if restart_choice and restart_choice.isdigit():
        restart_idx = int(restart_choice) if 0 <= int(restart_choice) < len(restart_options) else 1
    service_info['restart_policy'] = restart_options[restart_idx]
    
    # Restart seconds
    service_info['restart_sec'] = input("Restart delay in seconds [default: 3]: ").strip() or "3"
    
    # Environment variables
    print("\nAdditional environment variables (beyond PATH and PYTHONUNBUFFERED)")
    print("Format: KEY1=VALUE1 KEY2=VALUE2 (space-separated)")
    env_vars = input("Environment variables: ").strip()
    service_info['additional_env_vars'] = parse_env_vars(env_vars)
    
    # Review and confirm
    print("\n=== Service Configuration Summary ===")
    for key, value in service_info.items():
        print(f"{key}: {value}")
    
    confirm = input("\nDoes this look correct? [Y/n]: ").strip().lower()
    if confirm == 'n':
        print("Configuration cancelled. Please run the wizard again.")
        sys.exit(0)
        
    return service_info

def save_service_config(service_info, path=None):
    """Save service configuration to a JSON file for later use."""
    if path is None:
        config_dir = os.path.expanduser("~/.config/pysysddeploy")
        os.makedirs(config_dir, exist_ok=True)
        path = os.path.join(config_dir, f"{service_info['name']}.json")
    
    with open(path, 'w') as f:
        json.dump(service_info, f, indent=2)
    
    return path

def load_service_config(name=None, path=None):
    """Load service configuration from a JSON file."""
    if path is None and name is not None:
        path = os.path.expanduser(f"~/.config/pysysddeploy/{name}.json")
    
    if not os.path.exists(path):
        return None
    
    with open(path, 'r') as f:
        return json.load(f)

def preview_service_file(template_name, context):
    """Generate and show a preview of the service file."""
    if template_name not in TEMPLATES:
        print(f"Unknown template: {template_name}")
        return
        
    template = jinja2.Template(TEMPLATES[template_name]["template"])
    service_content = template.render(**context)
    
    print("\n=== Service File Preview ===")
    print(service_content)
    print("===========================")

def edit_service_info(service_info):
    """Allow user to edit specific fields in the service info."""
    while True:
        print("\n=== Edit Service Configuration ===")
        # Display numbered list of fields
        fields = list(service_info.keys())
        for i, field in enumerate(fields, 1):
            print(f"{i}) {field}: {service_info[field]}")
        print(f"{len(fields)+1}) Done editing")
        
        choice = input(f"Select field to edit [1-{len(fields)+1}]: ").strip()
        if not choice.isdigit():
            continue
            
        choice = int(choice)
        if choice == len(fields) + 1:
            break
        elif 1 <= choice <= len(fields):
            field = fields[choice-1]
            current = service_info[field]
            
            if isinstance(current, list):
                print(f"Current value: {' '.join(current)}")
                new_value = input(f"Enter new value for {field} (space-separated list): ").strip()
                service_info[field] = parse_env_vars(new_value)
            else:
                new_value = input(f"Enter new value for {field} [current: {current}]: ").strip()
                if new_value:
                    service_info[field] = new_value
        else:
            print("Invalid choice")
            
    return service_info

def main():
    parser = argparse.ArgumentParser(description="Deploy Python scripts as systemd services using Ray")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new systemd service")
    create_parser.add_argument("--interactive", action="store_true", help="Run in interactive wizard mode")
    create_parser.add_argument("--load", help="Load service configuration from file")
    create_parser.add_argument("--name", help="Service name")
    create_parser.add_argument("--template", choices=TEMPLATES.keys(), help="Service template to use")
    create_parser.add_argument("--description", help="Service description")
    create_parser.add_argument("--working-dir", help="Working directory")
    create_parser.add_argument("--venv-path", help="Path to virtual environment")
    create_parser.add_argument("--script-path", help="Path to Python script (for standard_python template)")
    create_parser.add_argument("--script-args", help="Script arguments (for standard_python template)")
    create_parser.add_argument("--bind-address", help="Bind address (for gunicorn template)")
    create_parser.add_argument("--app-module", help="App module (for gunicorn template)")
    create_parser.add_argument("--user", help="User to run the service as")
    create_parser.add_argument("--group", help="Group to run the service as")
    create_parser.add_argument("--restart", default="always", help="Restart policy")
    create_parser.add_argument("--restart-sec", default="3", help="Restart delay in seconds")
    create_parser.add_argument("--env", help="Additional environment variables (KEY1=VALUE1 KEY2=VALUE2...)")
    create_parser.add_argument("--preview", action="store_true", help="Preview service file without deploying")
    create_parser.add_argument("--edit", action="store_true", help="Edit configuration interactively")
    create_parser.add_argument("--output", help="Output directory for service files")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available saved service configurations")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check service status")
    status_parser.add_argument("name", help="Service name")
    
    # Stop command  
    stop_parser = subparsers.add_parser("stop", help="Stop a service")
    stop_parser.add_argument("name", help="Service name")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start a service")
    start_parser.add_argument("name", help="Service name")
    
    args = parser.parse_args()
    
    if args.command == "create":
        # Load or gather service info
        service_info = None
        
        if args.load:
            service_info = load_service_config(path=args.load)
            if service_info is None:
                print(f"Error: Could not load configuration from {args.load}")
                return 1
            print(f"Loaded service configuration from {args.load}")
        
        elif args.interactive or not (args.name and args.template and args.venv_path):
            # Interactive mode
            service_info = gather_service_info()
        else:
            # Command line mode
            template = args.template
            
            if template == "standard_python" and not args.script_path:
                print("Error: --script-path is required for standard_python template")
                return 1
            elif template == "gunicorn" and not args.app_module:
                print("Error: --app-module is required for gunicorn template")
                return 1
            
            service_info = {
                'name': args.name,
                'description': args.description or f"Python service {args.name}",
                'template': template,
                'working_directory': os.path.abspath(os.path.expanduser(args.working_dir)) if args.working_dir else os.getcwd(),
                'venv_path': os.path.abspath(os.path.expanduser(args.venv_path)),
                'user': args.user or getpass.getuser(),
                'group': args.group or getpass.user or getpass.getuser(),
                'restart_policy': args.restart,
                'restart_sec': args.restart_sec,
                'additional_env_vars': parse_env_vars(args.env or "")
            }
            
            # Template-specific fields
            if template == "standard_python":
                service_info['script_path'] = os.path.abspath(os.path.expanduser(args.script_path))
                service_info['script_args'] = args.script_args or ""
            elif template == "gunicorn":
                service_info['bind_address'] = args.bind_address or "0.0.0.0:8000"
                service_info['app_module'] = args.app_module
        
        # Allow editing configuration if requested
        if args.edit and service_info:
            service_info = edit_service_info(service_info)
        
        # Validate inputs
        print(f"\nValidating virtual environment at {service_info['venv_path']}...")
        is_valid, message = ray.get(validate_venv.remote(service_info['venv_path']))
        if not is_valid:
            print(f"Warning: {message}")
            proceed = input("Virtual environment validation failed. Proceed anyway? [y/N]: ").strip().lower()
            if proceed != 'y':
                return 1
        
        if service_info['template'] == "standard_python":
            print(f"Validating script at {service_info['script_path']}...")
            is_valid, message = ray.get(validate_python_script.remote(service_info['script_path']))
            if not is_valid:
                print(f"Warning: {message}")
                proceed = input("Script validation failed. Proceed anyway? [y/N]: ").strip().lower()
                if proceed != 'y':
                    return 1
        
        # Preview service file if requested
        if args.preview:
            preview_service_file(service_info['template'], service_info)
            
            # Ask if user wants to proceed
            proceed = input("\nProceed with creation? [Y/n]: ").strip().lower()
            if proceed == 'n':
                return 0
        
        # Save configuration
        config_path = save_service_config(service_info)
        print(f"Configuration saved to: {config_path}")
        
        # Create service file
        output_dir = args.output or os.path.expanduser("~/systemd-services")
        print("Creating service file...")
        success, result = ray.get(create_service_file.remote(
            service_info['name'], 
            service_info['template'],
            service_info,
            output_dir
        ))
        
        if not success:
            print(f"Error creating service file: {result}")
            return 1
        
        print(f"Service file created at: {result}")
        
        # Preview final service file
        with open(result, 'r') as f:
            print("\n=== Service File ===")
            print(f.read())
            print("===================")
        
        # Deploy if requested
        deploy = input("Deploy service now? [y/N]: ").strip().lower()
        if deploy == 'y':
            print("Deploying service...")
            success, message = ray.get(deploy_service.remote(service_info['name'], result))
            print(message)
            
            if success:
                start = input("Start and enable service? [Y/n]: ").strip().lower()
                if start != 'n':
                    success, message = ray.get(enable_service.remote(service_info['name']))
                    print(message)
                    
                    if success:
                        time.sleep(2)  # Give service time to start
                        _, status = ray.get(check_service_status.remote(service_info['name']))
                        print("\nService Status:")
                        print(status)
    
    elif args.command == "list":
        config_dir = os.path.expanduser("~/.config/pysysddeploy")
        if not os.path.exists(config_dir):
            print("No saved service configurations found.")
            return 0
            
        configs = [f for f in os.listdir(config_dir) if f.endswith('.json')]
        if not configs:
            print("No saved service configurations found.")
            return 0
            
        print("\nSaved service configurations:")
        for i, config_file in enumerate(configs, 1):
            service_name = os.path.splitext(config_file)[0]
            config = load_service_config(name=service_name)
            template_name = TEMPLATES[config['template']]['name'] if 'template' in config else "Unknown"
            print(f"{i}) {service_name} - {template_name}")
            
        select = input("\nEnter number to view details (or press Enter to cancel): ").strip()
        if select and select.isdigit() and 1 <= int(select) <= len(configs):
            config_file = configs[int(select) - 1]
            service_name = os.path.splitext(config_file)[0]
            config = load_service_config(name=service_name)
            
            print(f"\n=== {service_name} Configuration ===")
            for key, value in config.items():
                print(f"{key}: {value}")
                
            option = input("\n[L]oad this config, [P]review service file, or [C]ancel? ").strip().lower()
            if option == 'l':
                # Re-run the command with --load
                os.execl(sys.executable, sys.executable, sys.argv[0], 
                         "create", "--load", os.path.join(config_dir, config_file))
            elif option == 'p':
                preview_service_file(config['template'], config)
        
    elif args.command == "status":
        _, status = ray.get(check_service_status.remote(args.name))
        print(status)
        
    elif args.command == "stop":
        try:
            subprocess.run(['sudo', 'systemctl', 'stop', args.name], check=True)
            print(f"Service {args.name} stopped")
        except subprocess.CalledProcessError as e:
            print(f"Failed to stop service: {e}")
            
    elif args.command == "start":
        try:
            subprocess.run(['sudo', 'systemctl', 'start', args.name], check=True)
            time.sleep(1)  # Give service time to start
            _, status = ray.get(check_service_status.remote(args.name))
            print(status)
        except subprocess.CalledProcessError as e:
            print(f"Failed to start service: {e}")
    else:
        parser.print_help()

if __name__ == "__main__":
    sys.exit(main())
