"""Exercise the packaged settings login action, including its actual loopback listener."""
import base64
import hashlib
import http.client
import os
from pathlib import Path
import socket
import sys
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

sys.path.insert(0, sys.argv[1])
from start import configure
home, dlls = configure()
from gi.repository import GLib
from inkpad import gdrive
from inkpad.window import Window


def exercise(manual):
    loop = GLib.MainLoop()
    errors = []
    auth = {}

    def consent(url):
        try:
            parsed = urlsplit(url)
            assert parsed.hostname == "accounts.google.com"
            fields = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            assert fields["scope"] == gdrive.SCOPE and fields["code_challenge_method"] == "S256"
            auth.update(fields)
            callback = urlsplit(fields["redirect_uri"])
            assert callback.hostname == "127.0.0.1"
            connection = http.client.HTTPConnection(callback.hostname,callback.port,timeout=5)
            try:
                connection.request("GET","/?"+urlencode({"code":"test-code","state":fields["state"]}))
                response = connection.getresponse()
                assert response.status == 200
                response.read()
            finally:
                connection.close()
        except Exception as exc:
            errors.append(exc)
            loop.quit()
        return GLib.SOURCE_REMOVE

    class TestWindow:
        def __init__(self):
            self.toasts = self
            self.synced = False
        def add_toast(self, toast):
            if manual:
                toast.emit("button-clicked")
        def get_clipboard(self):
            return self
        def set(self, url):
            assert manual
            GLib.idle_add(consent,url)
        def toast(self, *args):
            pass
        def _error(self, title, error):
            errors.append(error)
            loop.quit()
        def sync_now(self):
            self.synced = True
            loop.quit()

    def open_browser(url,verb):
        assert verb == "open"
        if manual:
            raise OSError("Test system has no default browser")
        GLib.idle_add(consent,url)

    def exchange(endpoint, fields):
        assert endpoint == "https://oauth2.googleapis.com/token" and fields["code"] == "test-code"
        assert fields["redirect_uri"] == auth["redirect_uri"]
        challenge = hashlib.sha256(fields["code_verifier"].encode()).digest()
        assert base64.urlsafe_b64encode(challenge).decode().rstrip("=") == auth["code_challenge"]
        return {"refresh_token":"fixture","access_token":"fixture"}

    def timeout():
        errors.append(TimeoutError("No callback from the simulated consent page"))
        loop.quit()
        return GLib.SOURCE_REMOVE

    assert Path(gdrive.CONFIG).resolve().is_relative_to(home)
    Path(gdrive.TOKEN_PATH).unlink(missing_ok=True)
    gdrive.save_client("test.apps.googleusercontent.com","fixture")
    window = TestWindow()
    with patch.object(os,"startfile",side_effect=open_browser) as dispatch, patch.object(gdrive,"_post",side_effect=exchange):
        timer = GLib.timeout_add_seconds(15,timeout)
        Window._drive_connect(window)
        loop.run()
        if errors:
            raise errors[0]
        GLib.source_remove(timer)
        dispatch.assert_called_once()
    assert window.synced and gdrive.connected()


exercise(False)
exercise(True)
print("Verified native browser dispatch, manual sign-in link, loopback callback and PKCE exchange")

# Only the disposable Windows CI desktop opens a real browser. A local listener
# observes its TLS ClientHello before any HTTP request or account interaction.
if os.environ.get("INKPAD_VERIFY_REAL_SHELL") == "1":
    from inkpad.windows_drive_login import WindowsDriveLogin
    with socket.socket() as listener:
        listener.bind(("127.0.0.1",0))
        listener.listen()
        listener.settimeout(45)
        login = WindowsDriveLogin(None)
        login.open_url(f"https://127.0.0.1:{listener.getsockname()[1]}/")
        login.finish()
        with listener.accept()[0] as client:
            client.settimeout(10)
            assert client.recv(1) == b"\x16", "Expected a browser TLS handshake"
    print("Verified a real Windows HTTPS browser connected to the test listener")
