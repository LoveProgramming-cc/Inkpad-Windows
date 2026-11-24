# Inkpad for Windows

Inkpad 的 Windows 10 x64 发行版，使用原版 GTK 4 和 libadwaita 界面。下载页提供安装包、便携 ZIP 和 SHA-256 校验文件。[下载最新版本](https://github.com/LoveProgramming-cc/Inkpad-Windows/releases/latest)

首次安装默认使用 `D:\Inkpad`。已有旧版时，安装器沿用登记的安装位置。安装和卸载时保留程序旁的 `InkpadData`。便携版完整解压后双击 `Inkpad.exe`。Windows 包未进行公开代码签名。

## 本地一键打包

在 Windows x64 的 PowerShell 中，从本仓库根目录运行以下命令。首次运行从 Python、Microsoft 和 MSYS2 官方分发站点下载锁定版本的工具，到指定工作目录校验并解压。构建、缓存和测试均使用该目录。需要网络、可写的数据盘和数 GB 可用空间。

```powershell
.\packaging\windows\build.ps1 -WorkDir D:\InkpadBuild
```

默认构建已验证的上游提交。要用 A 当时最新的代码，使用以下命令。也可以将 `main` 替换为标签或完整提交 SHA。每个包中的 `UPSTREAM.txt` 记录这次实际使用的上游提交。

```powershell
.\packaging\windows\build.ps1 -WorkDir D:\InkpadBuild -Revision main
```

脚本从上游读取版本号，编译启动器和 Python 字节码，生成 NSIS 安装包与 ZIP，逐文件校验，并在独立中文路径进行静默安装、读写笔记、PDF 和 PNG 导出与读取、Goodnotes 往返、覆盖安装及卸载测试。当前版本的三个分发文件位于 `D:\InkpadBuild\dist`。

## 在 GitHub 重新发布

打开下方工作流，选择 **Run workflow**。在 `revision` 填入上游分支、标签或提交。勾选 `publish` 后，从本仓库 `main` 分支发起的构建通过测试即发布到本仓库的 Releases。普通构建可在该次运行的 Artifacts 中下载。推送到本仓库的 `main` 也会自动构建固定的上游版本。[Windows 打包工作流](https://github.com/LoveProgramming-cc/Inkpad-Windows/actions/workflows/windows.yml)

## Windows 适配

打包器从 Inkpad GNOME 项目只读下载源码。对当前基线，打包时在副本里的 `ptext.py` 和 `pdf.py` 接入 Windows DLL 名称解析，在 `library.py`、`prefs.py` 和 `window.py` 接入 Windows 日期格式。新增的启动入口设置包内运行库、字体与数据目录。两个包内 Python 主程序带 UTF-8 进程清单，用于中文安装路径。兼容代码、工具链清单和安装器脚本均在本仓库的 `packaging/windows` 下。[上游源码](https://github.com/LoveProgramming-cc/Inkpad-gnome)
