"""Dispatch Google consent to the Windows HTTPS handler from the OAuth worker."""
import os
from urllib.parse import urlsplit

from gi.repository import Adw, GLib
from . import i18n


def localized(zh, en, ja):
    return {"en": en, "ja": ja}.get(i18n.LANG, zh)


class WindowsDriveLogin:
    def __init__(self, window):
        self.window = window
        self.toast = None
        self.finished = False

    def open_url(self, url):
        if not url.startswith("https://") or not urlsplit(url).hostname:
            raise ValueError(localized("Google 登录地址必须使用 HTTPS", "Google sign-in requires an HTTPS URL",
                                       "Google ログインには HTTPS の URL が必要です"))
        try:
            os.startfile(url, "open")
            title = i18n.tr("请在浏览器中登录 Google 并授权")
        except OSError:
            title = localized("无法打开默认浏览器，请复制登录链接后打开",
                              "Copy the sign-in link and open it in your browser",
                              "ログインリンクをコピーしてブラウザーで開いてください")
        GLib.idle_add(self.show_link, title, url)

    def show_link(self, title, url):
        if not self.finished:
            self.toast = Adw.Toast(title=title, timeout=0,
                                  button_label=localized("复制登录链接", "Copy sign-in link", "ログインリンクをコピー"))
            self.toast.connect("button-clicked", lambda *_: self.window.get_clipboard().set(url))
            self.window.toasts.add_toast(self.toast)
        return GLib.SOURCE_REMOVE

    def finish(self):
        self.finished = True
        if self.toast is not None:
            self.toast.dismiss()
            self.toast = None
