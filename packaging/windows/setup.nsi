Unicode true
!define PRODUCTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\InkpadGNOME"
!ifdef MACHINE
RequestExecutionLevel admin
!define REGROOT HKLM
!define SHELLSCOPE all
InstallDir "$PROGRAMFILES64\Inkpad"
!else
RequestExecutionLevel user
!define REGROOT HKCU
!define SHELLSCOPE current
InstallDir "$LOCALAPPDATA\Programs\Inkpad"
!endif
Name "Inkpad ${VERSION}"
OutFile "${SETUP}"
InstallDirRegKey ${REGROOT} "${PRODUCTKEY}" "InstallLocation"
AllowSkipFiles off
Icon "${ICON}"
UninstallIcon "${ICON}"
SetCompressor zlib
ShowInstDetails show
ShowUninstDetails show
!include "MUI2.nsh"
!include "FileFunc.nsh"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"
VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=2052 "ProductName" "Inkpad"
VIAddVersionKey /LANG=2052 "FileDescription" "Inkpad Windows 安装程序"
VIAddVersionKey /LANG=2052 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=2052 "LegalCopyright" "Inkpad contributors"
Var registerApp
Var desktopDir
Var programsDir

!macro ShortcutFolders
  SetShellVarContext ${SHELLSCOPE}
  ${If} $registerApp == 1
    StrCpy $desktopDir "$DESKTOP"
    StrCpy $programsDir "$SMPROGRAMS"
  ${Else}
    StrCpy $desktopDir "$INSTDIR\.test-shell\Desktop"
    StrCpy $programsDir "$INSTDIR\.test-shell\Programs"
  ${EndIf}
!macroend

Function .onInit
  StrCpy $registerApp 1
!ifndef MACHINE
  ${GetParameters} $0
  ClearErrors
  ${GetOptions} $0 "/NOREG" $1
  IfErrors +2
  StrCpy $registerApp 0
!endif
FunctionEnd

; Catch a running launcher or GUI host before replacing files or unregistering.
!macro CheckFileAvailable relative
  !define lockLabel ${__LINE__}
  IfFileExists "$INSTDIR\${relative}" 0 available${lockLabel}
  check${lockLabel}:
    System::Call 'kernel32::CreateFileW(w "$INSTDIR\${relative}", i 0x40000000, i 0, p 0, i 3, i 0x80, p 0) p.r0'
    ${If} $0 = -1
      MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "无法写入 $INSTDIR\${relative}。请保存笔记并退出正在运行的 Inkpad，再重试。" /SD IDCANCEL IDRETRY check${lockLabel}
      SetErrorLevel 32
      Quit
    ${EndIf}
    System::Call 'kernel32::CloseHandle(p r0)'
  available${lockLabel}:
  !undef lockLabel
!macroend

Section "Inkpad"
!ifdef MACHINE
  ReadRegStr $0 HKCU "${PRODUCTKEY}" "InstallLocation"
!else
  ReadRegStr $0 HKLM "${PRODUCTKEY}" "InstallLocation"
!endif
  StrCmp $0 "$INSTDIR" 0 scopeOK
  MessageBox MB_ICONSTOP|MB_OK "此目录已登记为另一安装范围。请使用原安装范围的安装包升级，或先卸载旧程序。" /SD IDOK
  SetErrorLevel 2
  Quit
scopeOK:
  IfFileExists "$INSTDIR\app\inkpad\__init__.py" 0 inspect
  IfFileExists "$INSTDIR\Uninstall.exe" accept inspect
inspect:
  ; A previous uninstall can leave the user's notebook directory here.
  ClearErrors
  FindFirst $0 $1 "$INSTDIR\*.*"
  IfErrors accept
next:
  StrCmp $1 "." advance
  StrCmp $1 ".." advance
  StrCmp $1 "InkpadData" advance
  FindClose $0
  Goto reject
advance:
  ClearErrors
  FindNext $0 $1
  IfErrors scanned next
scanned:
  FindClose $0
  Goto accept
reject:
  MessageBox MB_ICONSTOP|MB_OK "请选择空目录或现有的 Inkpad 安装目录。" /SD IDOK
  SetErrorLevel 2
  Quit
accept:
  ClearErrors
  CreateDirectory "$INSTDIR"
  IfErrors noWrite
  GetTempFileName $0 "$INSTDIR"
  IfErrors noWrite
  Delete "$0"
  Goto writable
noWrite:
!ifdef MACHINE
  MessageBox MB_ICONSTOP|MB_OK "无法写入所选安装目录。请检查目录权限或选择其他目录。" /SD IDOK
!else
  MessageBox MB_ICONSTOP|MB_OK "当前用户无法写入所选目录。安装到 Program Files 时请运行标准 Setup 安装包，并允许 Windows 提权。" /SD IDOK
!endif
  SetErrorLevel 5
  Quit
writable:
  !insertmacro CheckFileAvailable "Inkpad.exe"
  !insertmacro CheckFileAvailable "runtime\bin\python3.14w.exe"
  SetOutPath "$INSTDIR"
  File /r "${PAYLOAD}\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  !insertmacro ShortcutFolders
  ClearErrors
  CreateDirectory "$desktopDir"
  CreateDirectory "$programsDir"
  CreateShortCut "$desktopDir\Inkpad.lnk" "$INSTDIR\Inkpad.exe" "" "$INSTDIR\Inkpad.exe" 0
  CreateShortCut "$programsDir\Inkpad.lnk" "$INSTDIR\Inkpad.exe" "" "$INSTDIR\Inkpad.exe" 0
  IfErrors 0 linksReady
  MessageBox MB_ICONSTOP|MB_OK "无法创建 Inkpad 桌面或开始菜单快捷方式。" /SD IDOK
  SetErrorLevel 3
  Quit
linksReady:
  StrCmp $registerApp 0 done
  ReadRegStr $1 ${REGROOT} "${PRODUCTKEY}" "InstallLocation"
  ${If} $1 != ""
  ${AndIf} ${FileExists} "$1\InkpadData\*.*"
    WriteRegStr ${REGROOT} "${PRODUCTKEY}" "LegacyDataDir" "$1\InkpadData"
  ${EndIf}
  WriteRegStr ${REGROOT} "${PRODUCTKEY}" "DisplayName" "Inkpad"
  WriteRegStr ${REGROOT} "${PRODUCTKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr ${REGROOT} "${PRODUCTKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr ${REGROOT} "${PRODUCTKEY}" "DisplayIcon" "$INSTDIR\Inkpad.exe"
  WriteRegStr ${REGROOT} "${PRODUCTKEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
done:
SectionEnd

Section "Uninstall"
  !insertmacro CheckFileAvailable "Inkpad.exe"
  !insertmacro CheckFileAvailable "runtime\bin\python3.14w.exe"
  !include "${REMOVE_FILES}"
  ReadRegStr $0 ${REGROOT} "${PRODUCTKEY}" "InstallLocation"
  StrCpy $registerApp 0
  ${If} $0 == "$INSTDIR"
    StrCpy $registerApp 1
    DeleteRegKey ${REGROOT} "${PRODUCTKEY}"
  ${EndIf}
  !insertmacro ShortcutFolders
  Delete "$desktopDir\Inkpad.lnk"
  Delete "$programsDir\Inkpad.lnk"
  ${If} $registerApp == 0
    RMDir "$desktopDir"
    RMDir "$programsDir"
    RMDir "$INSTDIR\.test-shell"
  ${EndIf}
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  Goto complete
removeFailed:
  MessageBox MB_OK|MB_ICONSTOP "无法删除全部程序文件，请关闭 Inkpad 后再次运行卸载程序。" /SD IDOK
  SetErrorLevel 5
complete:
SectionEnd
