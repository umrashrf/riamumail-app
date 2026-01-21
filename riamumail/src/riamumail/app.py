import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import os
import sys
import json
import threading
import socket
import requests
import subprocess
from pathlib import Path

CONFIG_PATH = Path.home() / ".my_toga_app"
CONFIG_FILE = CONFIG_PATH / "config.json"


class SetupApp(toga.App):

    def startup(self):
        self.main_window = toga.MainWindow(title=self.formal_name)

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
        welcome_label = toga.Label(
            "Welcome!\nThis app will help you verify your system and network setup.",
            style=Pack(padding=20, text_align="center"),
        )

        setup_btn = toga.Button(
            "Setup", on_press=lambda w: self.show_setup_screen(), style=Pack(padding=10)
        )

        box = toga.Box(
            children=[welcome_label, setup_btn],
            style=Pack(direction=COLUMN, alignment="center"),
        )

        self.main_window.content = box

    # ------------------ SETUP SCREEN ------------------

    def show_setup_screen(self):
        self.loader = toga.ProgressBar(max=None, style=Pack(padding=5))

        self.ip_label = toga.Label("IP: checking...")
        self.domain_input = toga.TextInput(placeholder="example.com")
        self.user_input = toga.TextInput(placeholder="email username")
        self.email_display = toga.TextInput(readonly=True)

        self.port_input = toga.TextInput(value="36245")
        self.port_status = toga.Label("Port: checking...")

        self.checklist_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        save_btn = toga.Button("Save", on_press=self.save_data)
        thunderbird_btn = toga.Button(
            "Open Thunderbird", on_press=self.open_thunderbird
        )

        main_box = toga.Box(
            children=[
                self.loader,
                self.ip_label,
                toga.Label("Domain:"),
                self.domain_input,
                toga.Label("Email username:"),
                self.user_input,
                toga.Label("Email address:"),
                self.email_display,
                toga.Label("Port:"),
                self.port_input,
                self.port_status,
                self.checklist_box,
                toga.Box(
                    children=[save_btn, thunderbird_btn],
                    style=Pack(direction=ROW, padding=10),
                ),
            ],
            style=Pack(direction=COLUMN, padding=10),
        )

        self.domain_input.on_change = self.trigger_checks
        self.user_input.on_change = self.update_email

        self.main_window.content = main_box

        config = self.load_config()

        if "domain" in config:
            self.domain_input.value = config["domain"]

        if "username" in config:
            self.user_input.value = config["username"]

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
        self.checklist_box.add(toga.Label(f"{icon} {label}", style=Pack(color=color)))

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
