#!/usr/bin/env python3
"""
Cash Flow Intelligence - Development Server Launcher

Quick start script that:
1. Checks/installs dependencies
2. Sets up the database
3. Optionally loads demo data
4. Starts the Flask development server
5. Opens browser automatically

Usage:
    python start_dev.py              # Start with default settings
    python start_dev.py --demo       # Load demo data first
    python start_dev.py --port 8080  # Use custom port
    python start_dev.py --no-browser # Don't open browser
"""

import os
import sys
import time
import argparse
import subprocess
import webbrowser
import threading
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_banner():
    """Print startup banner"""
    banner = f"""
{Colors.GREEN}╔══════════════════════════════════════════════════════════════╗
║                                                                ║
║   {Colors.BOLD}💰 Cash Flow Intelligence{Colors.END}{Colors.GREEN}                                   ║
║   {Colors.CYAN}AI-Powered Cash Flow Analysis for SMBs{Colors.GREEN}                       ║
║                                                                ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}
"""
    print(banner)

def print_step(step_num, message, status="running"):
    """Print step with status"""
    if status == "running":
        icon = f"{Colors.YELLOW}⏳{Colors.END}"
    elif status == "done":
        icon = f"{Colors.GREEN}✓{Colors.END}"
    elif status == "skip":
        icon = f"{Colors.BLUE}→{Colors.END}"
    else:
        icon = f"{Colors.RED}✗{Colors.END}"

    print(f"  {icon} Step {step_num}: {message}")

def check_python_version():
    """Ensure Python 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"{Colors.RED}Error: Python 3.8+ required. You have {version.major}.{version.minor}{Colors.END}")
        sys.exit(1)
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required = ['flask', 'flask_sqlalchemy', 'flask_limiter', 'anthropic']
    missing = []

    for package in required:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)

    return missing

def install_dependencies():
    """Install missing dependencies from requirements.txt"""
    requirements_file = Path(__file__).parent / 'requirements.txt'

    if requirements_file.exists():
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file), '-q'
        ])
    else:
        # Install minimum required
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            'flask', 'flask-sqlalchemy', 'flask-limiter', 'anthropic', 'numpy', '-q'
        ])

def setup_environment():
    """Set up environment variables"""
    # Set default environment variables if not set
    os.environ.setdefault('FLASK_APP', 'web.app:app')
    os.environ.setdefault('FLASK_DEBUG', 'True')
    os.environ.setdefault('FLASK_ENV', 'development')

    # Database
    db_path = Path(__file__).parent / 'instance' / 'cash_flow.db'
    db_path.parent.mkdir(exist_ok=True)
    os.environ.setdefault('DATABASE_URL', f'sqlite:///{db_path}')

def load_demo_data(count=3):
    """Load demo companies into database"""
    # Import after ensuring dependencies
    sys.path.insert(0, str(Path(__file__).parent))

    from web.app import create_app
    from src.database.models import db, Company
    from src.demo_data import DemoDataGenerator, load_demo_data_to_db

    app = create_app()

    with app.app_context():
        # Check if data already exists
        existing = Company.query.count()
        if existing > 0:
            print(f"    {Colors.CYAN}Database has {existing} companies. Skipping demo data.{Colors.END}")
            return existing

        # Load demo data
        company_ids = load_demo_data_to_db(db.session, count=count)
        print(f"    {Colors.GREEN}Loaded {len(company_ids)} demo companies{Colors.END}")
        return len(company_ids)

def open_browser_delayed(url, delay=2):
    """Open browser after delay"""
    def _open():
        time.sleep(delay)
        webbrowser.open(url)

    thread = threading.Thread(target=_open, daemon=True)
    thread.start()

def run_server(port=5101, host='127.0.0.1'):
    """Run the Flask development server"""
    sys.path.insert(0, str(Path(__file__).parent))

    from web.app import create_app

    app = create_app()

    print(f"\n{Colors.GREEN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}  Server running at: {Colors.CYAN}http://{host}:{port}{Colors.END}")
    print(f"{Colors.GREEN}{'='*60}{Colors.END}\n")

    app.run(debug=True, port=port, host=host, use_reloader=True)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Cash Flow Intelligence Development Server'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Load demo data on startup'
    )
    parser.add_argument(
        '--demo-count',
        type=int,
        default=3,
        help='Number of demo companies to create (default: 3)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5101,
        help='Port to run server on (default: 5101)'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not open browser automatically'
    )
    parser.add_argument(
        '--skip-install',
        action='store_true',
        help='Skip dependency installation'
    )

    args = parser.parse_args()

    print_banner()

    # Step 1: Check Python version
    print_step(1, "Checking Python version...", "running")
    check_python_version()
    print_step(1, f"Python {sys.version_info.major}.{sys.version_info.minor} OK", "done")

    # Step 2: Check/install dependencies
    if not args.skip_install:
        print_step(2, "Checking dependencies...", "running")
        missing = check_dependencies()
        if missing:
            print_step(2, f"Installing: {', '.join(missing)}", "running")
            try:
                install_dependencies()
                print_step(2, "Dependencies installed", "done")
            except Exception as e:
                print_step(2, f"Installation failed: {e}", "error")
                sys.exit(1)
        else:
            print_step(2, "All dependencies installed", "done")
    else:
        print_step(2, "Skipping dependency check", "skip")

    # Step 3: Set up environment
    print_step(3, "Setting up environment...", "running")
    setup_environment()
    print_step(3, "Environment configured", "done")

    # Step 4: Load demo data if requested
    if args.demo:
        print_step(4, f"Loading {args.demo_count} demo companies...", "running")
        try:
            count = load_demo_data(count=args.demo_count)
            print_step(4, f"Demo data ready ({count} companies)", "done")
        except Exception as e:
            print_step(4, f"Demo data failed: {e}", "error")
            print(f"    {Colors.YELLOW}Continuing without demo data...{Colors.END}")
    else:
        print_step(4, "Demo data loading skipped (use --demo to load)", "skip")

    # Step 5: Open browser
    url = f"http://{args.host}:{args.port}"
    if not args.no_browser:
        print_step(5, f"Opening browser to {url}...", "running")
        open_browser_delayed(url, delay=2)
        print_step(5, "Browser will open shortly", "done")
    else:
        print_step(5, "Browser auto-open disabled", "skip")

    # Step 6: Start server
    print_step(6, "Starting development server...", "running")

    try:
        run_server(port=args.port, host=args.host)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Server stopped.{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Server error: {e}{Colors.END}")
        sys.exit(1)

if __name__ == '__main__':
    main()
