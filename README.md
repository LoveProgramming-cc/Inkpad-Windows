# Inkpad for Windows

Inkpad 的 Windows 10 x64 发行版，使用原版 GTK 4 和 libadwaita 界面。下载页提供安装包、便携 ZIP 和 SHA-256 校验文件。[下载最新版本](https://github.com/LoveProgramming-cc/Inkpad-Windows/releases/latest)

标准安装包 `*-x64-Setup.exe` 为所有用户安装到 `%ProgramFiles%\Inkpad`。安装、更新和卸载均向 Windows 请求管理员权限。也可在安装向导选择 `C:\Program Files (x86)\Inkpad`。Inkpad 日常运行使用普通用户权限。

原先使用当前用户版的用户可用 `*-CurrentUser-Setup.exe` 原位升级。此包默认安装到 `%LOCALAPPDATA%\Programs\Inkpad`，安装和卸载均使用当前用户权限。两种安装范围分别登记在 Windows「应用和功能」中，并在对应的桌面和开始菜单创建快捷方式。

新用户的笔记保存在 Windows 的 **文档\Inkpad** 中，包括已通过 OneDrive 或系统设置重定向的文档目录。可在应用设置里更改文稿库。设置、登录状态和运行缓存放在 `%LOCALAPPDATA%\Inkpad`。

覆盖安装沿用已选安装位置。首次升级会沿用旧设置和已有笔记的位置。卸载移除程序与快捷方式，保留文稿库和个人设置。便携 ZIP 完整解压后双击 `Inkpad.exe`；带有旧版 `InkpadData` 的便携副本继续使用原数据。Windows 包未进行公开代码签名。

## 本地一键打包

在 Windows x64 的 PowerShell 中，从本仓库根目录运行以下命令。首次运行从 Python、Microsoft 和 MSYS2 官方分发站点下载锁定版本的工具，到指定工作目录校验并解压。构建、缓存和测试均使用该目录。需要网络、可写的数据盘和数 GB 可用空间。

```powershell
.\packaging\windows\build.ps1 -WorkDir D:\InkpadBuild
```

默认构建已验证的上游提交。要用 A 当时最新的代码，使用以下命令。也可以将 `main` 替换为标签或完整提交 SHA。每个包中的 `UPSTREAM.txt` 记录这次实际使用的上游提交。

```powershell
.\packaging\windows\build.ps1 -WorkDir D:\InkpadBuild -Revision main
```

脚本从上游读取版本号，编译启动器和 Python 字节码，生成两种安装包、便携 ZIP 和 SHA-256 文件到 `D:\InkpadBuild\dist`。本地测试使用隔离目录；云端还会验证 EXE 的权限清单、两种 Program Files 路径的实际安装、文件占用、覆盖安装、卸载和笔记保留。

## 在 GitHub 重新发布

打开下方工作流，选择 **Run workflow**。在 `revision` 填入上游分支、标签或提交。勾选 `publish` 后，从本仓库 `main` 分支发起的构建通过测试即发布到本仓库的 Releases。普通构建可在该次运行的 Artifacts 中下载。推送到本仓库的 `main` 也会自动构建固定的上游版本。[Windows 打包工作流](https://github.com/LoveProgramming-cc/Inkpad-Windows/actions/workflows/windows.yml)

## Windows 适配

打包器从 Inkpad GNOME 项目只读下载源码。对当前基线，打包时在副本里的 `ptext.py` 和 `pdf.py` 接入 Windows DLL 名称解析，在 `library.py`、`prefs.py` 和 `window.py` 接入 Windows 日期格式。新增的启动入口设置包内运行库、字体与数据目录。两个包内 Python 主程序带 UTF-8 进程清单，用于中文安装路径。兼容代码、工具链清单和安装器脚本均在本仓库的 `packaging/windows` 下。[上游源码](https://github.com/LoveProgramming-cc/Inkpad-gnome)

大白板书写时，小地图按新增笔迹更新。自动保存会在界面线程固定当前版本，再在后台生成文件和封面。侧栏打开时，大白板缩略图也在后台生成。相关改动由打包器应用到源码副本；上游改动与补丁不匹配时，打包会提示人工复核。回归测试会在自动保存期间继续书写，并重新打开文稿核对内容。
