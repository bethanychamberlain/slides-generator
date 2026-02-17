"""System tray icon for Slide Guide Generator.

Manages the Streamlit server process and provides quick access via tray menu.
"""

import subprocess
import webbrowser
import signal
import sys
from pathlib import Path

import pystray
from PIL import Image

APP_DIR = Path(__file__).parent
APP_URL = "http://localhost:8501"
STREAMLIT_CMD = [
    str(APP_DIR / "venv" / "bin" / "streamlit"),
    "run", str(APP_DIR / "app.py"),
    "--server.headless", "true",
]

server_process = None


def load_icon(name):
    path = APP_DIR / name
    return Image.open(path)


def is_running():
    return server_process is not None and server_process.poll() is None


def start_server(icon, item=None):
    global server_process
    if is_running():
        return
    server_process = subprocess.Popen(
        STREAMLIT_CMD,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    icon.icon = load_icon("icon.png")
    icon.notify("Slide Guide Generator started", "Server Running")


def stop_server(icon, item=None):
    global server_process
    if not is_running():
        return
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
    server_process = None
    icon.icon = load_icon("icon_stopped.png")


def open_browser(icon, item):
    if is_running():
        webbrowser.open(APP_URL)


def quit_app(icon, item):
    stop_server(icon)
    icon.stop()


def create_menu():
    return pystray.Menu(
        pystray.MenuItem("Open in Browser", open_browser, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Start Server",
            start_server,
            enabled=lambda item: not is_running(),
        ),
        pystray.MenuItem(
            "Stop Server",
            stop_server,
            enabled=lambda item: is_running(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", quit_app),
    )


def main():
    icon = pystray.Icon(
        name="slide-guide",
        icon=load_icon("icon_stopped.png"),
        title="Slide Guide Generator",
        menu=create_menu(),
    )

    # Auto-start server and open browser on launch
    def on_setup(icon):
        start_server(icon)
        webbrowser.open(APP_URL)

    # Clean shutdown on SIGTERM/SIGINT
    def handle_signal(signum, frame):
        stop_server(icon)
        icon.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    icon.run(setup=on_setup)


if __name__ == "__main__":
    main()
