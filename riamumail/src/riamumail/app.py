import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import re
import os
import sys
import json
import shutil
import logging
import tempfile
import traceback
import threading
import socket
import requests
import subprocess
import webbrowser
from pathlib import Path

CONFIG_PATH = Path.home() / ".riamumail"
CONFIG_FILE = CONFIG_PATH / "config.json"
LOG_FILE = CONFIG_PATH / "app.log"

MAIL_EXP_REPO = "https://github.com/umrashrf/mailexp.git"
MAIL_EXP_PATH = CONFIG_PATH / "mailexp"

DOCKER_IMAGE = "mailexp:latest"
DOCKER_CONTAINER = "mailexp"

API_BASE = "https://riamu.email/api"


def setup_logging():
    try:
        CONFIG_PATH.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )
        logging.info("Application started")
    except Exception:
        # Absolute last-resort fallback
        pass


class SetupApp(toga.App):

    def startup(self):
        setup_logging()
        logging.info("Startup called")

        self.check_run_id = 0
        self.check_labels = {}

        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_index = 0
        self.spinner_running = False
        self.spinning_labels = set()

        self.main_window = toga.MainWindow(title=self.formal_name, size=(800, 600))

        self.ip = ""
        self.domain_ok = False
        self.port_ok = False

        if CONFIG_FILE.exists():
            self.show_setup_screen()
        else:
            self.show_welcome_screen()

        self.main_window.show()

    # ------------------ WELCOME SCREEN ------------------

    def show_welcome_screen(self):
        title = toga.Label(
            "Welcome to Riamu Mail",
            style=Pack(
                padding=10,
                text_align="center",
                font_size=16,
            ),
        )

        subtitle = toga.Label(
            "Riamu Mail lets you setup your own email server at your own terms.",
            style=Pack(
                padding=20,
                text_align="center",
                font_size=12,
            ),
        )

        card_style = Pack(
            direction=COLUMN,
            padding=8,
            width=180,
            alignment="center",  # center content inside the box
        )

        text_style = Pack(
            font_size=11,
            padding_top=4,
        )

        button_style = Pack(
            font_size=11,
            margin_top=10,
            padding_top=10,
            padding_bottom=10,
        )

        # ---------- FREE ----------
        free_box = toga.Box(
            children=[
                toga.Label("Free", style=Pack(font_size=16, font_weight="bold")),
                toga.Label("$0", style=Pack(font_size=12)),
                toga.Label(
                    "* Always free\n"
                    "• Self-hosted\n"
                    "• PC uptime\n"
                    "• Manual updates\n"
                    "• Port forwarding\n"
                    "• Custom domain\n"
                    "• Free subdomain\n"
                    "• No backup",
                    style=text_style,
                ),
                toga.Button(
                    "Select Free",
                    on_press=lambda w: self.show_setup_screen(),
                    style=button_style,
                ),
            ],
            style=card_style,
        )

        # ---------- PRO ----------
        pro_box = toga.Box(
            children=[
                toga.Label("Pro", style=Pack(font_size=16, font_weight="bold")),
                toga.Label("$5/mo · $50/yr", style=Pack(font_size=12)),
                toga.Label(
                    "• Includes Free\n"
                    "• Cloud hosted\n"
                    "• 100% uptime\n"
                    "• Auto updates\n"
                    "• Port guaranteed\n"
                    "• Custom domain\n"
                    "• Free subdomain\n"
                    "• Email backups",
                    style=text_style,
                ),
                toga.Button(
                    "Select Pro",
                    on_press=lambda w: webbrowser.open("https://riamu.mail/pro"),
                    style=button_style,
                ),
            ],
            style=card_style,
        )

        # ---------- ENTERPRISE ----------
        enterprise_box = toga.Box(
            children=[
                toga.Label("Enterprise", style=Pack(font_size=16, font_weight="bold")),
                toga.Label("Custom", style=Pack(font_size=12)),
                toga.Label(
                    "• Free + Pro\n"
                    "• Custom infra\n"
                    "• 100% uptime\n"
                    "• Auto updates\n"
                    "• Port guaranteed\n"
                    "• Custom domain\n"
                    "• Free subdomain\n"
                    "• Email backups",
                    style=text_style,
                ),
                toga.Button(
                    "Select Enterprise",
                    on_press=lambda w: webbrowser.open("https://riamu.mail/enterprise"),
                    style=button_style,
                ),
            ],
            style=card_style,
        )

        pricing_row = toga.Box(
            children=[free_box, pro_box, enterprise_box],
            style=Pack(direction=ROW, padding=10, alignment="center"),
        )

        self.main_window.content = toga.Box(
            children=[title, subtitle, pricing_row],
            style=Pack(
                margin_top=40,
                direction=COLUMN,
                alignment="center",
            ),
        )

    # ------------------ SETUP SCREEN ------------------

    def show_setup_screen(self):
        self.loader = toga.ProgressBar(max=None, style=Pack(padding=(0, 0, 10, 0)))

        # ---------- STATUS ----------
        self.ip_label = toga.Label("IP: checking...", style=Pack(padding=(0, 0, 5, 0)))

        self.port_status = toga.Label(
            "Port: checking...", style=Pack(padding=(0, 0, 10, 0))
        )

        status_box = toga.Box(
            children=[
                self.loader,
                # self.ip_label,
                # self.port_status
            ],
            style=Pack(direction=COLUMN, padding=20),
        )

        # ---------- NETWORK ----------
        self.domain_input = toga.TextInput(style=Pack(padding=5))
        self.domain_status_label = toga.Label(
            "",
            style=Pack(padding=(4, 0, 5, 0), font_size=10),
        )

        self.port_input = toga.TextInput(
            readonly=True, value="36245", style=Pack(padding=5)
        )

        network_box = toga.Box(
            children=[
                toga.Label("Network", style=Pack(padding=(0, 0, 5, 0))),
                toga.Label("Domain"),
                self.domain_input,
                self.domain_status_label,
                toga.Label("Port"),
                self.port_input,
            ],
            style=Pack(direction=COLUMN, padding=20),
        )

        # ---------- EMAIL ----------
        self.firstname_input = toga.TextInput(
            placeholder="First Name", style=Pack(padding=5)
        )
        self.familyname_input = toga.TextInput(
            placeholder="Family Name", style=Pack(padding=5)
        )
        self.password_input = toga.TextInput(
            placeholder="password", style=Pack(padding=5)
        )

        self.email_display = toga.TextInput(readonly=True, style=Pack(padding=5))

        email_box = toga.Box(
            children=[
                toga.Label("First Name"),
                self.firstname_input,
                toga.Label("Family Name"),
                self.familyname_input,
                toga.Label("Email address", style=Pack(padding=(10, 0, 5, 0))),
                self.email_display,
                toga.Label("Password"),
                self.password_input,
            ],
            style=Pack(direction=COLUMN, padding=20),
        )

        # ---------- CHECKLIST ----------
        self.checklist_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        checks_box = toga.Box(
            children=[
                toga.Label(
                    "System Checks",
                    style=Pack(padding=(0, 0, 10, 0), font_size=16, font_weight="bold"),
                ),
                self.checklist_box,
            ],
            style=Pack(direction=COLUMN, padding=20),
        )

        # ---------- ACTIONS ----------
        save_btn = toga.Button(
            "Save", on_press=self.save_data, style=Pack(padding=(5, 10))
        )
        save_btn.style.padding = (5, 10, 5, 0)

        self.docker_btn = toga.Button(
            "Start Mail Server",
            on_press=self.toggle_container,
            style=Pack(padding=(5, 10, 5, 0)),
        )

        thunderbird_btn = toga.Button(
            "Open Thunderbird",
            on_press=self.open_thunderbird,
            style=Pack(padding=(5, 10)),
        )
        thunderbird_btn.style.padding = (5, 0)

        action_box = toga.Box(
            children=[
                toga.Box(style=Pack(flex=1)),  # spacer
                save_btn,
                self.docker_btn,
                thunderbird_btn,
            ],
            style=Pack(direction=ROW, padding=10),
        )

        # ---------- MAIN ----------
        main_box = toga.Box(
            children=[
                status_box,
                checks_box,
                email_box,
                network_box,
                action_box,
            ],
            style=Pack(direction=COLUMN, padding=5, alignment="center"),
        )

        self.domain_input.on_change = self.on_domain_change
        self.firstname_input.on_change = self.update_email
        self.familyname_input.on_change = self.update_email

        self.main_window.content = main_box

        config = self.load_config()
        self.domain_input.value = config.get("domain", "family_name.riamumail.com")
        self.firstname_input.value = config.get("username", "")
        self.familyname_input.value = config.get("familyname", "")
        self.password_input.value = config.get("password", "")
        self.update_email(None)
        self.start_checks()

    # ------------------ BACKGROUND CHECKS ------------------

    def check_domain_availability_http(self, domain):
        try:
            r = requests.get(
                API_BASE + "/domain/check",
                params={"domain": domain},
                timeout=5,
            )
            r.raise_for_status()
            data = r.json()
            return bool(data.get("available"))
        except Exception:
            logging.exception("Domain availability check failed")
            return -1

    def set_domain_status(self, status):
        if status is 1:
            self.domain_status_label.text = "✓ Domain is available"
            self.domain_status_label.style.color = "green"

        elif status is 0:
            self.domain_status_label.text = "✗ Domain is not available"
            self.domain_status_label.style.color = "red"

        elif status is None:
            self.domain_status_label.text = "⟳ Checking domain availability…"
            self.domain_status_label.style.color = "#f0ad4e"

        else:
            self.domain_status_label.text = ""
            self.domain_status_label.style.color = "#000000"

    def trigger_domain_check(self):
        domain = self.domain_input.value.strip()
        if not domain:
            return

        # Show "checking..."
        self.ui(self.set_domain_status, None)

        def worker():
            available = self.check_domain_availability_http(domain)
            self.ui(self.set_domain_status, available)

        threading.Thread(target=worker, daemon=True).start()

    def start_checks(self):
        self.spinner_running = True
        self._update_spinner()
        self.check_run_id += 1
        run_id = self.check_run_id
        self.clear_checklist()
        threading.Thread(
            target=self.run_checks_safe,
            args=(run_id,),
            daemon=True,
        ).start()

    def _start_checks_ui(self):
        self.check_run_id += 1
        run_id = self.check_run_id

        self.clear_checklist()
        self.loader.start()

        threading.Thread(
            target=self.run_checks_safe,
            args=(run_id,),
            daemon=True,
        ).start()

    def run_checks_safe(self, run_id):
        try:
            if run_id != self.check_run_id:
                return
            self.run_checks(run_id)
        except Exception:
            logging.exception("run_checks crashed")
            self.ui(self.loader.stop)

    def run_checks(self, run_id):
        logging.info("Running system checks")

        try:
            self.ip = self.get_public_ip()
            domain = self.domain_input.value
            port = int(self.port_input.value)

            self.domain_ok = self.check_domain(domain)
            self.port_ok = self.check_port(port)

            git_ok = self.git_exists()
            docker_ok = self.app_exists("docker")
            thunderbird_ok = self.app_exists("thunderbird")

            if not docker_ok or not thunderbird_ok:
                self.ensure_dependencies()

            self.app.loop.call_soon_threadsafe(
                self.update_ui, git_ok, docker_ok, thunderbird_ok, run_id
            )

        except Exception:
            logging.exception("Error during run_checks")

    def ui(self, fn, *args):
        """Safely run UI code on the main thread."""
        self.app.loop.call_soon_threadsafe(fn, *args)

    def update_ui(self, git_ok, docker_ok, thunderbird_ok, run_id):
        if run_id != self.check_run_id:
            return

        self.spinner_running = False  # stop spinner

        running = self.docker_container_running()
        self.docker_btn.text = "Stop Mail Server" if running else "Start Mail Server"

        self.add_check("Git", git_ok)
        self.add_check("Docker Desktop", docker_ok)
        self.add_check("Thunderbird", thunderbird_ok)
        self.add_check("Domain mapped to IP", self.domain_ok)
        self.add_check("Mail server running", running)
        self.add_check("Port 36245 open", self.port_ok)

        self.loader.stop()

    def _update_spinner(self):
        if not self.spinner_running:
            return

        # Update all "pending" checks with spinner symbol
        for label, widget in self.check_labels.items():
            if widget.text.startswith("⟳") or widget.text.endswith("…"):
                widget.text = f"{self.spinner_frames[self.spinner_index]} {label}…"

        # Advance spinner
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)

        # Schedule next tick
        self.app.loop.call_later(0.1, self._update_spinner)

    def clear_checklist(self):
        self.spinning_labels.clear()
        self.check_labels.clear()

        for child in list(self.checklist_box.children):
            self.checklist_box.remove(child)

    def ensure_dependencies(self):
        try:
            threading.Thread(target=self.install_missing_apps_safe, daemon=True).start()
        except Exception:
            logging.exception("Failed to start dependency installer")

    def install_missing_apps_safe(self):
        try:
            self.install_missing_apps()
        except Exception:
            logging.exception("Dependency installation crashed")

    def install_missing_apps(self):
        if not self.app_exists("docker"):
            self.ui(self.add_check, "Docker Desktop", None)
            self.install_docker()

        if not self.app_exists("thunderbird"):
            self.ui(self.add_check, "Thunderbird", None)
            self.install_thunderbird()

        git_ok = self.git_exists()
        docker_ok = self.app_exists("docker")
        thunderbird_ok = self.app_exists("thunderbird")

        self.ui(self.update_ui, git_ok, docker_ok, thunderbird_ok, self.check_run_id)

    def install_docker(self):
        try:
            logging.info("Installing Docker")
            system = sys.platform

            if system == "win32":
                url = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
                installer = self.download_file(url)
                subprocess.Popen([installer, "install", "--quiet", "--accept-license"])

            elif system == "darwin":
                url = "https://desktop.docker.com/mac/main/arm64/Docker.dmg"
                dmg = self.download_file(url)
                subprocess.Popen(["hdiutil", "attach", dmg])
                subprocess.Popen(
                    ["cp", "-R", "/Volumes/Docker/Docker.app", "/Applications"]
                )

            else:
                subprocess.Popen(["sh", "-c", "curl -fsSL https://get.docker.com | sh"])

        except Exception:
            logging.exception("Docker installation failed")

    def install_thunderbird(self):
        system = sys.platform

        if system == "win32":
            url = "https://download.mozilla.org/?product=thunderbird-latest&os=win64&lang=en-US"
            installer = self.download_file(url)

            subprocess.Popen([installer, "/S"])
        elif system == "darwin":
            url = "https://download.mozilla.org/?product=thunderbird-latest&os=osx&lang=en-US"
            dmg = self.download_file(url)

            subprocess.Popen(["hdiutil", "attach", dmg])
            subprocess.Popen(
                ["cp", "-R", "/Volumes/Thunderbird/Thunderbird.app", "/Applications"]
            )
        else:
            subprocess.Popen(["sh", "-c", "sudo apt install -y thunderbird"])

    def download_file(self, url):
        logging.info(f"Downloading: {url}")
        try:
            temp_dir = tempfile.mkdtemp()
            local_path = os.path.join(temp_dir, os.path.basename(url.split("?")[0]))

            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            return local_path

        except Exception:
            logging.exception(f"Download failed: {url}")
            raise

    # ------------------ HELPERS ------------------

    def get_public_ip(self):
        try:
            return requests.get("https://ipecho.net/plain", timeout=5).text.strip()
        except Exception:
            logging.exception("Failed to fetch public IP")
            return "Unknown"

    def check_domain(self, domain):
        if not domain:
            return False
        try:
            return socket.gethostbyname(domain) == self.ip
        except:
            return False

    def check_port(self, port):
        try:
            response = requests.post(
                "https://canyouseeme.org/",
                data={"port": port},
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://canyouseeme.org/",
                },
            )

            text = response.text.lower()

            if "success" in text and "can see your service" in text:
                return True
            return False

        except Exception:
            return False

    def app_exists(self, app_name):
        system = sys.platform

        # ---------- macOS ----------
        if system == "darwin":
            app_bundles = [
                f"/Applications/{app_name}.app",
                f"/Applications/{app_name.capitalize()}.app",
                f"/Applications/{app_name.replace(' ', '')}.app",
                f"{Path.home()}/Applications/{app_name}.app",
            ]
            return any(Path(p).exists() for p in app_bundles)

        # ---------- Windows ----------
        elif system == "win32":
            program_dirs = [
                os.environ.get("ProgramFiles", ""),
                os.environ.get("ProgramFiles(x86)", ""),
                os.environ.get("LocalAppData", ""),
            ]

            for base in program_dirs:
                if not base:
                    continue
                for root, _, files in os.walk(base):
                    if f"{app_name}.exe".lower() in (f.lower() for f in files):
                        return True
            return False

        # ---------- Linux ----------
        else:
            for path in os.environ.get("PATH", "").split(os.pathsep):
                exe = Path(path) / app_name
                if exe.exists():
                    return True
            return False

    def add_check(self, label, ok):
        if ok is True:
            icon, color, text = "✓", "green", label
            self.spinning_labels.discard(label)

        elif ok is False:
            icon, color, text = "✗", "red", label
            self.spinning_labels.discard(label)

        else:
            icon = self.spinner_frames[self.spinner_index]
            color = "#f0ad4e"
            text = f"{label}…"
            self.spinning_labels.add(label)

        if label in self.check_labels:
            lbl = self.check_labels[label]
            lbl.text = f"{icon} {text}"
            lbl.style.color = color
            return

        lbl = toga.Label(
            f"{icon} {text}",
            style=Pack(
                padding=(4, 0),
                color=color,
                font_size=16,
                font_weight="bold",
            ),
        )

        self.check_labels[label] = lbl
        self.checklist_box.add(lbl)

    # ------------------ EVENTS ------------------

    def update_email(self, widget):
        if not self.domain_input.value.startswith(self.familyname_input.value):
            domain = self.domain_input.value
            match = re.search(r"[^.]+\.[^.]+$", domain)
            if match:
                domain = match.group(0)
            self.domain_input.value = (
                f"{(self.familyname_input.value or "family_name").lower()}.{domain}"
            )

        self.email_display.value = f"{(self.firstname_input.value or "first_name").lower()}@{self.domain_input.value}"

    def on_domain_change(self, widget):
        self.email_display.value = f"{(self.firstname_input.value or "first_name").lower()}@{self.domain_input.value}"

        self.trigger_domain_check()
        self.start_checks()

    def is_first_run(self):
        return not CONFIG_FILE.exists()

    def save_data(self, widget):
        new_domain = self.domain_input.value

        # ---------- FIRST RUN ----------
        if self.is_first_run():

            def worker():
                self.reserve_domain(new_domain)
                self.save_config(self.collect_config())
                self.ui(self.start_checks)

            threading.Thread(target=worker, daemon=True).start()
            return

        # ---------- DOMAIN CHANGE ----------
        if self.domain_changed(new_domain):
            self.main_window.confirm_dialog(
                title="Confirm domain change",
                message=(
                    "You are changing your email domain.\n\n"
                    "• The new domain may take a few minutes to a few hours to activate\n"
                    "• In some cases it can take 24 hours or more\n\n"
                    "Do you want to continue?"
                ),
                on_result=lambda window, confirmed: self.on_domain_change_confirmed(
                    confirmed, new_domain
                ),
            )
            return

        if not self.is_first_run():  # ---------- SUBSEQUENT RUNS ----------
            if (
                self.docker_container_exists()
                or self.docker_container_running()
                or self.docker_image_exists()
            ):
                self.main_window.confirm_dialog(
                    title="Confirm changes",
                    message=(
                        "Are you sure? "
                        "Your have an active mail server and "
                        "saving new config will delete it and "
                        "you will lose all your emails \n\n"
                        "Do you want to continue?"
                    ),
                    on_result=self.on_save_confirmed,
                )
            else:
                self.save_config(self.collect_config())

    def on_domain_change_confirmed(self, confirmed, new_domain):
        if not confirmed:
            logging.info("User cancelled domain change")
            return

        old_domain = self.load_config().get("domain")

        def worker():
            if old_domain:
                self.release_domain(old_domain)

            self.reserve_domain(new_domain)

            self.save_config(self.collect_config())
            self.ui(self.start_checks)

        threading.Thread(target=worker, daemon=True).start()

    def on_save_confirmed(self, window, confirmed):
        if not confirmed:
            logging.info("User cancelled save")
            return  # 🚫 Do nothing

        def worker():
            # Stop container & remove image
            self.cleanup_docker_state_safe()

            # Save config
            self.save_config(self.collect_config())

            # Refresh UI checks
            self.ui(self.start_checks)

        threading.Thread(target=worker, daemon=True).start()

    def collect_config(self):
        return {
            "domain": self.domain_input.value,
            "username": self.firstname_input.value,
            "familyname": self.familyname_input.value,
            "password": self.password_input.value,
        }

    def load_config(self):
        if not CONFIG_FILE.exists():
            return {}

        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            logging.exception("Failed to load config")
            return {}

    def save_config(self, data):
        try:
            CONFIG_PATH.mkdir(exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f)
            logging.info("Config saved")
        except Exception:
            logging.exception("Failed to save config")

    def get_user_config(self):
        config = self.load_config()
        username = config.get("username", "umair")
        domain = config.get("domain", "riamuapp.com")
        password = config.get("password", "test")
        email = f"{username}@{domain}"
        return username, domain, password, email

    def domain_changed(self, new_domain):
        old_domain = self.load_config().get("domain")
        return old_domain and old_domain != new_domain

    def release_domain(self, domain):
        try:
            r = requests.post(
                API_BASE + "/domain/release",
                json={"domain": domain},
                timeout=10,
            )
            r.raise_for_status()
            logging.info(f"Released domain: {domain}")
            return True
        except Exception:
            logging.exception(f"Failed to release domain: {domain}")
            return False

    def reserve_domain(self, domain):
        try:
            r = requests.post(
                API_BASE + "/domain/reserve",
                json={"domain": domain, "ipAddress": self.ip},
                timeout=10,
            )
            r.raise_for_status()
            logging.info(f"Reserved domain: {domain}")
            return True
        except Exception:
            logging.exception(f"Failed to reserve domain: {domain}")
            return False

    def open_thunderbird(self, widget):
        try:
            subprocess.Popen(["open", "/Applications/Thunderbird.app"])  # MacOS
        except Exception:
            logging.exception("Failed to open Thunderbird")

    # ------------------ GIT HELPERS ------------------

    def git_exists(self):
        try:
            subprocess.check_output(["git", "--version"])
            return True
        except Exception:
            return False

    def clone_mailexp_repo(self):
        logging.info("Cloning mailexp repository")

        if MAIL_EXP_PATH.exists():
            return

        MAIL_EXP_PATH.parent.mkdir(parents=True, exist_ok=True)

        subprocess.check_call(["git", "clone", MAIL_EXP_REPO, str(MAIL_EXP_PATH)])

    # ------------------ DOCKER HELPERS ------------------

    def docker_image_exists(self):
        try:
            subprocess.check_output(
                ["/usr/local/bin/docker", "image", "inspect", DOCKER_IMAGE],
                stderr=subprocess.DEVNULL,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def docker_container_exists(self):
        try:
            output = subprocess.check_output(
                [
                    "/usr/local/bin/docker",
                    "ps",
                    "-a",
                    "--filter",
                    f"name={DOCKER_CONTAINER}",
                    "--format",
                    "{{.Names}}",
                ]
            ).decode()
            return DOCKER_CONTAINER in output
        except Exception:
            return False

    def docker_container_running(self):
        try:
            output = subprocess.check_output(
                [
                    "/usr/local/bin/docker",
                    "ps",
                    "--filter",
                    f"name={DOCKER_CONTAINER}",
                    "--format",
                    "{{.Names}}",
                ]
            ).decode()
            return DOCKER_CONTAINER in output
        except Exception:
            return False

    def build_docker_image(self):
        logging.info("Building Docker image")

        if not self.git_exists():
            raise RuntimeError("Git is not installed")

        if not MAIL_EXP_PATH.exists():
            self.app.loop.call_soon_threadsafe(
                self.add_check,
                "Cloning mail server repository",
                None,
            )
            self.clone_mailexp_repo()

        # Read username, domain, password, email
        username, domain, password, email = self.get_user_config()

        username = username.lower()

        # ------------------ Replace users file ------------------
        users_file = MAIL_EXP_PATH / "users"
        users_content = (
            f"{username}:{{PLAIN}}{password}:1000:1000::/home/{username}:/bin/false\n"
        )
        users_file.write_text(users_content)
        logging.info(f"Replaced users file for {username}")

        # ------------------ Replace aliases file ------------------
        aliases_file = MAIL_EXP_PATH / "postfix/aliases"
        aliases_content = f"""
#
# Generated aliases
#
{username}:          {email}

# Basic system aliases -- these MUST be present
MAILER-DAEMON:  postmaster
postmaster:     root

# General redirections for pseudo accounts
bin:            root
daemon:         root
named:          root
nobody:         root
uucp:           root
www:            root
ftp-bugs:       root
postfix:        root

# Well-known aliases
manager:        root
dumper:         root
operator:       root
abuse:          postmaster

# trap decode to catch security attacks
decode:         root
"""
        aliases_file.write_text(aliases_content)
        logging.info(f"Replaced aliases file for {username}")

        # ------------------ Replace Dockerfile ------------------
        dockerfile_path = MAIL_EXP_PATH / "Dockerfile"
        dockerfile_content = f"""
FROM alpine:latest

RUN apk update
RUN apk add busybox-extras vim
RUN apk add postfix dovecot mailutils

COPY postfix/* /etc/postfix/
COPY dovecot.conf /etc/dovecot/
COPY users /etc/dovecot/
RUN chown root:dovecot /etc/dovecot/users
RUN chmod 640 /etc/dovecot/users

RUN adduser -D {username} mail
RUN mkdir -p /home/{username}/Maildir/cur && \\
    mkdir -p /home/{username}/Maildir/new && \\
    mkdir -p /home/{username}/Maildir/tmp
RUN chown {username}:{username} -R /home/{username}/Maildir
RUN echo "{username}:{password}" | chpasswd

RUN awk '{{gsub(/smtp\\t+25/, "smtp\\t\\t36245"); print}}' /etc/services > /tmp/services
RUN cp /tmp/services /etc/ && rm /tmp/services

RUN newaliases && postfix start

ENTRYPOINT ["dovecot"]
CMD ["-F"]
"""

        dockerfile_path.write_text(dockerfile_content)
        logging.info(f"Replaced Dockerfile for {username}")

        # ------------------ Build Docker image ------------------
        try:
            self.app.loop.call_soon_threadsafe(
                self.add_check,
                "Building mail server image",
                None,
            )
            subprocess.check_call(
                ["/usr/local/bin/docker", "build", "-t", DOCKER_IMAGE, "."],
                cwd=MAIL_EXP_PATH,
            )
        except subprocess.CalledProcessError:
            self.app.loop.call_soon_threadsafe(
                self.add_check,
                "Docker build failed (see logs)",
                False,
            )
            raise

    def start_container(self):
        logging.info("Starting container")
        subprocess.check_call(
            [
                "/usr/local/bin/docker",
                "run",
                "-d",
                "--name",
                DOCKER_CONTAINER,
                "--dns",
                "8.8.8.8",
                "--hostname",
                self.domain_input.value,
                "-p",
                "36245:36245",
                "-p",
                "10143:143",
                DOCKER_IMAGE,
            ]
        )

    def stop_container(self):
        logging.info("Stopping container")
        subprocess.call(["/usr/local/bin/docker", "rm", "-f", DOCKER_CONTAINER])

    def toggle_container(self, widget):
        threading.Thread(target=self.toggle_container_safe, daemon=True).start()

    def toggle_container_safe(self):
        try:
            if not self.docker_image_exists():
                self.build_docker_image()

            if self.docker_container_running():
                self.stop_container()
            else:
                self.start_container()

        except Exception:
            logging.exception("Docker toggle failed")

        finally:
            # Instead of calling start_checks() directly, marshal to main thread
            self.ui(self.start_checks)

    def remove_docker_image(self):
        logging.info("Removing Docker image if it exists")
        subprocess.call(
            ["/usr/local/bin/docker", "rmi", "-f", DOCKER_IMAGE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def cleanup_docker_state_safe(self):
        try:
            # Stop & remove container if it exists
            if self.docker_container_exists():
                logging.info("Stopping existing mail container")
                self.stop_container()

            # Remove image if it exists
            if self.docker_image_exists():
                self.remove_docker_image()

        except Exception:
            logging.exception("Docker cleanup failed")


def main():
    return SetupApp("Setup Utility", "com.example.setup")
