import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import os
import sys
import json
import shutil
import tempfile
import threading
import socket
import requests
import subprocess
from pathlib import Path

CONFIG_PATH = Path.home() / ".riamumail"
CONFIG_FILE = CONFIG_PATH / "config.json"


class SetupApp(toga.App):

    def startup(self):
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
                    on_press=lambda w: self.show_setup_screen(),
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
                    on_press=lambda w: self.show_setup_screen(),
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
        self.domain_input = toga.TextInput(
            placeholder="example.com", style=Pack(padding=5)
        )

        self.port_input = toga.TextInput(
            readonly=True, value="36245", style=Pack(padding=5)
        )

        network_box = toga.Box(
            children=[
                toga.Label("Network", style=Pack(padding=(0, 0, 10, 0))),
                toga.Label("Domain"),
                self.domain_input,
                toga.Label("Port"),
                self.port_input,
            ],
            style=Pack(direction=COLUMN, padding=20),
        )

        # ---------- EMAIL ----------
        self.user_input = toga.TextInput(placeholder="username", style=Pack(padding=5))

        self.email_display = toga.TextInput(readonly=True, style=Pack(padding=5))

        email_box = toga.Box(
            children=[
                toga.Label("Email", style=Pack(padding=(0, 0, 10, 0))),
                toga.Label("Username"),
                self.user_input,
                toga.Label("Email address"),
                self.email_display,
            ],
            style=Pack(direction=COLUMN, padding=20),
        )

        # ---------- CHECKLIST ----------
        self.checklist_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        checks_box = toga.Box(
            children=[
                toga.Label(
                    "System Checks",
                    style=Pack(padding=(0, 0, 10, 0), font_size=18, font_weight="bold"),
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
                thunderbird_btn,
            ],
            style=Pack(direction=ROW, padding=20),
        )

        # ---------- MAIN ----------
        main_box = toga.Box(
            children=[
                status_box,
                checks_box,
                network_box,
                email_box,
                action_box,
            ],
            style=Pack(direction=COLUMN, padding=10, alignment="center"),
        )

        self.domain_input.on_change = self.trigger_checks
        self.user_input.on_change = self.update_email

        self.main_window.content = main_box

        config = self.load_config()
        self.domain_input.value = config.get("domain", "")
        self.user_input.value = config.get("username", "")
        self.update_email(None)
        self.start_checks()

    # ------------------ BACKGROUND CHECKS ------------------

    def start_checks(self):
        self.loader.start()
        threading.Thread(target=self.run_checks, daemon=True).start()

    def run_checks(self):
        self.ip = self.get_public_ip()
        domain = self.domain_input.value
        port = int(self.port_input.value)

        self.domain_ok = self.check_domain(domain)
        self.port_ok = self.check_port(port)

        docker_ok = self.app_exists("docker")
        thunderbird_ok = self.app_exists("thunderbird")

        if not docker_ok or not thunderbird_ok:
            self.ensure_dependencies()

        self.app.loop.call_soon_threadsafe(self.update_ui, docker_ok, thunderbird_ok)

    def update_ui(self, docker_ok, thunderbird_ok):
        self.ip_label.text = f"IP: {self.ip}"
        self.port_status.text = f"Port 36245: {'OPENED' if self.port_ok else 'CLOSED'}"

        self.clear_checklist()

        self.add_check("Docker Desktop", docker_ok)
        self.add_check("Thunderbird", thunderbird_ok)
        self.add_check("Domain mapped to IP", self.domain_ok)
        self.add_check("Port 36245 open", self.port_ok)

        self.loader.stop()

    def clear_checklist(self):
        for child in list(self.checklist_box.children):
            self.checklist_box.remove(child)

    def ensure_dependencies(self):
        threading.Thread(target=self.install_missing_apps, daemon=True).start()

    def install_missing_apps(self):
        if not self.app_exists("docker"):
            self.add_check("Docker Desktop (installing…)", False)
            self.install_docker()

        if not self.app_exists("thunderbird"):
            self.add_check("Thunderbird (installing…)", False)
            self.install_thunderbird()

        docker_ok = self.app_exists("docker")
        thunderbird_ok = self.app_exists("thunderbird")

        self.app.loop.call_soon_threadsafe(self.update_ui, docker_ok, thunderbird_ok)

    def install_docker(self):
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
        temp_dir = tempfile.mkdtemp()
        local_path = os.path.join(temp_dir, os.path.basename(url.split("?")[0]))

        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        return local_path

    # ------------------ HELPERS ------------------

    def get_public_ip(self):
        try:
            return requests.get("https://ipecho.net/plain", timeout=5).text.strip()
        except:
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
        icon = "✓" if ok else "✗"
        color = "green" if ok else "red"

        self.checklist_box.add(
            toga.Label(
                f"{icon} {label}",
                style=Pack(
                    padding=(4, 0),
                    color=color,
                    font_size=16,  # ← increase this
                    font_weight="bold",  # optional
                ),
            )
        )

    # ------------------ EVENTS ------------------

    def update_email(self, widget):
        self.email_display.value = f"{self.user_input.value}@{self.domain_input.value}"

    def trigger_checks(self, widget):
        self.start_checks()

    def save_data(self, widget):
        self.save_config(
            {"domain": self.domain_input.value, "username": self.user_input.value}
        )

    def load_config(self):
        if not CONFIG_FILE.exists():
            return {}

        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_config(self, data):
        try:
            CONFIG_PATH.mkdir(exist_ok=False)
        except:
            pass
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)

    def open_thunderbird(self, widget):
        try:
            subprocess.Popen(["thunderbird"])
        except:
            pass


def main():
    return SetupApp("Setup Utility", "com.example.setup")
