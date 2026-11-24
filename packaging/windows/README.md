# Inkpad · Windows 10 x64

双击 Inkpad.exe 打开文稿库。标准安装包默认安装到 %ProgramFiles%\Inkpad，安装和卸载均由 Windows 请求管理员权限。当前用户安装包（CurrentUser-Setup.exe）默认使用 %LOCALAPPDATA%\Programs\Inkpad，适合旧版原位升级。可在 Windows「应用和功能」中卸载。便携版先完整解压。

这份程序使用 当前 GNOME 项目的 Python 代码、GTK 4 和 libadwaita。包内含原生 Windows 启动器、已编译的 Python 应用字节码、可阅读的源码、Python 运行时和 Poppler。运行所需的库随包提供。

新用户的文稿库默认为 Windows 的「文档\Inkpad」。可在设置中更改文稿库位置。设置、登录状态和缓存位于 %LOCALAPPDATA%\Inkpad。升级会沿用已有设置和笔记位置，卸载保留个人数据。旧便携副本可继续使用旁边的 InkpadData。也可通过 INKPAD_HOME 指定专用数据目录。直接打开文件时可将 .inkpad、.pdf 或 .goodnotes 文件拖到 Inkpad.exe 上。

程序许可证见 LICENSE。第三方声明见 THIRD-PARTY-NOTICES.md 和 runtime/share/licenses。
