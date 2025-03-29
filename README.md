# PySysdDeploy Wizard CLI

A powerful CLI tool for creating and managing Python daemon services as systemd units on Ubuntu systems.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)

## 📋 Overview

PySysdDeploy (Python Systemd Deployment) Wizard CLI is a comprehensive tool designed to simplify the process of running Python applications as system services on Ubuntu. It automates the creation, deployment, and management of systemd service units for Python scripts and web applications.

### Key Features

- 🧙‍♂️ Interactive wizard interface for easy service configuration
- 📝 Multiple service templates (standard Python scripts and Gunicorn web apps)
- ⚡ Parallel execution with Ray for improved performance
- ✅ Validation of Python scripts and virtual environments
- 🔄 Full service lifecycle management (create, deploy, start, stop, status)
- 💾 Save and load service configurations for reuse
- 🔍 Preview service files before deployment
- 🛠️ Edit configurations interactively

## ⚙️ Installation

### Prerequisites

- Ubuntu operating system
- Python 3.7 or higher
- pip package manager
- Administrative (sudo) privileges for deploying services

### Install from GitHub

```bash
# Clone the repository
git clone https://github.com/AmirHosseinMoloudi/pysysddeploy.git
cd pysysddeploy

# Create and activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Make the CLI script executable
chmod +x main.py
```

### Install with pip (TODO)

```bash
pip install pysysddeploy (TODO)
```

## 🚀 Usage

PySysdDeploy offers both an interactive wizard mode and command-line options.

### Interactive Mode

The easiest way to get started is with the interactive wizard:

```bash
./main.py create --interactive
```

The wizard will guide you through:

- Service name and description
- Template selection (Python script or Gunicorn)
- Working directory and virtual environment paths
- Script paths and arguments (for standard Python)
- Bind address and app module (for Gunicorn)
- User/group permissions
- Restart policies
- Environment variables

### Command-Line Options

For automation or scripts, you can use command-line arguments:

```bash
# Create a standard Python service
./main.py create \
  --name my_service \
  --template standard_python \
  --description "My Python Service" \
  --working-dir /path/to/app \
  --venv-path /path/to/venv \
  --script-path /path/to/app/script.py \
  --user myuser \
  --restart always

# Create a Gunicorn web application service
./main.py create \
  --name web_app \
  --template gunicorn \
  --description "My Web Application" \
  --working-dir /path/to/webapp \
  --venv-path /path/to/webapp/venv \
  --bind-address 0.0.0.0:8000 \
  --app-module app:app \
  --user webuser
```

### Service Management

```bash
# List saved service configurations
./main.py list

# Check service status
./main.py status my_service

# Start a service
./main.py start my_service

# Stop a service
./main.py stop my_service
```

## 📋 Examples

### Example 1: Deploy a Flask Application with Gunicorn

```bash
./main.py create \
  --name flask_app \
  --template gunicorn \
  --description "Flask Application" \
  --working-dir /home/user/flask_app \
  --venv-path /home/user/flask_app/venv \
  --bind-address 0.0.0.0:5000 \
  --app-module app:app \
  --env "FLASK_ENV=production FLASK_APP=app.py"
```

### Example 2: Deploy a Data Processing Script

```bash
./main.py create \
  --name data_processor \
  --template standard_python \
  --description "Data Processing Service" \
  --working-dir /home/user/data_processor \
  --venv-path /home/user/data_processor/venv \
  --script-path /home/user/data_processor/process.py \
  --script-args "--interval 300 --log-level INFO" \
  --restart on-failure \
  --env "DATABASE_URL=postgresql://user:pass@localhost/db"
```

## 🏗️ Service Templates

### Standard Python Script

Ideal for running Python scripts that need to run continuously, like:

- Data processing scripts
- Monitoring applications
- Scheduled tasks
- Background workers

### Gunicorn Web Application

Perfect for deploying web applications built with:

- Flask
- Django
- FastAPI
- Other WSGI-compatible frameworks

## 🔧 Configuration Options

| Option         | Description                                    |
| -------------- | ---------------------------------------------- |
| `name`         | Service name                                   |
| `description`  | Service description                            |
| `template`     | Service template (standard_python or gunicorn) |
| `working-dir`  | Working directory                              |
| `venv-path`    | Path to virtual environment                    |
| `script-path`  | Path to Python script (standard_python only)   |
| `script-args`  | Script arguments (standard_python only)        |
| `bind-address` | Bind address (gunicorn only)                   |
| `app-module`   | App module (gunicorn only)                     |
| `user`         | User to run the service as                     |
| `group`        | Group to run the service as                    |
| `restart`      | Restart policy                                 |
| `restart-sec`  | Restart delay in seconds                       |
| `env`          | Additional environment variables               |

## 📂 Project Structure

```
pysysddeploy/
├── main.py                    # Main CLI entry point
├── README.md                  # Project documentation
└── requirements.txt           # Dependencies list
```

## 🔍 Troubleshooting

### Common Issues

1. **Service fails to start**

   - Check the service logs: `sudo journalctl -u service_name`
   - Verify your Python script works correctly when run manually
   - Ensure the virtual environment contains all required dependencies

2. **Permission errors**

   - Ensure the user specified has adequate permissions for the working directory
   - Check that the Python script has execute permissions

3. **Configuration loading fails**
   - Verify the path to your saved configuration file
   - Check if the JSON file is properly formatted

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ✨ Acknowledgements

- [Ray](https://ray.io/) for parallel execution
- [Jinja2](https://jinja.palletsprojects.com/) for templating
- [systemd](https://systemd.io/) for service management

---

Created with ❤️ to make service deployment easier on Ubuntu systems.
