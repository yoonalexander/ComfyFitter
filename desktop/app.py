"""A persistent WebView2 desktop window around the local fitting room."""
import json
import os
import threading
import time
from pathlib import Path

from .runtime import APP_URL, ROOT, Services


class Bridge:
    def __init__(self, services):
        self._services = services

    def status(self):
        return self._services.status()

    def repair(self):
        return self._services.ensure()

    def ready(self):
        # Called by the actual React UI after its local health check succeeds.
        (ROOT / '.local/desktop/native-ready.json').write_text(json.dumps({
            'application': 'comfyfitter', 'engine': 'WebView2', 'local_url': APP_URL,
            'desktop_pid': os.getpid(), 'ready_at': time.time(), 'services': self.status(),
        }, indent=2) + '\n')
        return True


def main():
    if os.name != 'nt':
        raise RuntimeError('This desktop launcher is for the evaluated Windows GPU PC.')
    import msvcrt
    import webview
    directory = ROOT / '.local/desktop'
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'window.lock').open('a+b') as lock:
        lock.seek(0)
        if lock.read(1) == b'':
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, 'ComfyFitter is already open. Use its existing desktop window.', 'ComfyFitter', 0)
            return
        services = Services()
        bridge = Bridge(services)
        webview.settings['ALLOW_DOWNLOADS'] = True
        webview.settings['ALLOW_FILE_URLS'] = False
        window = webview.create_window('ComfyFitter', html=(ROOT / 'desktop/startup.html').read_text(),
            js_api=bridge, width=1180, height=820, min_size=(440, 600), background_color='#E7EDF1', text_select=True)
        closed = threading.Event()
        window.events.closed += closed.set

        def start():
            threading.Thread(target=services.ensure, daemon=True).start()
            while not closed.wait(.25):
                if services.status()['state'] == 'ready':
                    window.load_url(APP_URL)
                    return

        try:
            webview.start(start, gui='edgechromium', private_mode=False, storage_path=str(directory / 'profile'))
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    main()
