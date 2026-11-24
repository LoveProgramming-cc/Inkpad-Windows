Unicode true
RequestExecutionLevel user
Name "Inkpad ${VERSION}"
OutFile "${SETUP}"
InstallDir "D:\Inkpad"
Icon "${ICON}"
UninstallIcon "${ICON}"
SetCompressor zlib
ShowInstDetails show
ShowUninstDetails show
!include "MUI2.nsh"
!include "FileFunc.nsh"
!define PRODUCTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\InkpadGNOME"
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

Function .onInit
  StrCpy $registerApp 1
  ${GetParameters} $0
  ClearErrors
  ${GetOptions} $0 "/NOREG" $1
  IfErrors normal
  StrCpy $registerApp 0
  Return
normal:
  ReadRegStr $1 HKCU "${PRODUCTKEY}" "InstallLocation"
  StrCmp $1 "" +2
  StrCpy $INSTDIR "$1"
FunctionEnd

Section "Inkpad"
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
  SetOutPath "$INSTDIR"
  File /r "${PAYLOAD}\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  StrCmp $registerApp 0 done
  WriteRegStr HKCU "${PRODUCTKEY}" "DisplayName" "Inkpad"
  WriteRegStr HKCU "${PRODUCTKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${PRODUCTKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${PRODUCTKEY}" "DisplayIcon" "$INSTDIR\Inkpad.exe"
  WriteRegStr HKCU "${PRODUCTKEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
done:
SectionEnd

Section "Uninstall"
  !include "${REMOVE_FILES}"
  ReadRegStr $0 HKCU "${PRODUCTKEY}" "InstallLocation"
  StrCmp $0 "$INSTDIR" 0 +2
  DeleteRegKey HKCU "${PRODUCTKEY}"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
SectionEnd
