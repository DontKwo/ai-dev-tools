"""UI toolkit adapter registry and discovery."""

from pathlib import Path
from scripts.ui_adapters.android import AndroidAdapter
from scripts.ui_adapters.base import UiAdapter
from scripts.ui_adapters.dotnet import DotNetAdapter
from scripts.ui_adapters.electron import ElectronAdapter
from scripts.ui_adapters.flutter import FlutterAdapter
from scripts.ui_adapters.ios import IosAdapter
from scripts.ui_adapters.kivy import KivyAdapter
from scripts.ui_adapters.pyqt import PyQtAdapter
from scripts.ui_adapters.pywebview import PywebviewAdapter
from scripts.ui_adapters.tauri import TauriAdapter
from scripts.ui_adapters.textual import TextualAdapter
from scripts.ui_adapters.tkinter_adapter import TkinterAdapter
from scripts.ui_adapters.web import WebAdapter
from scripts.ui_adapters.wxpython import WxPythonAdapter

ADAPTERS: list[UiAdapter] = [
    PyQtAdapter(),
    WebAdapter(),
    PywebviewAdapter(),
    ElectronAdapter(),
    TauriAdapter(),
    AndroidAdapter(),
    FlutterAdapter(),
    IosAdapter(),
    TkinterAdapter(),
    WxPythonAdapter(),
    KivyAdapter(),
    TextualAdapter(),
    DotNetAdapter(),
]


def get_all_adapters() -> list[UiAdapter]:
    return list(ADAPTERS)


def get_adapter(name: str) -> UiAdapter | None:
    for ad in ADAPTERS:
        if ad.name == name:
            return ad
    return None


def detect_adapters(root: Path) -> list[UiAdapter]:
    return [ad for ad in ADAPTERS if ad.detect(root)]
