// SPDX-License-Identifier: GPL-3.0-or-later
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shellapi.h>
#include <filesystem>
#include <string>
#include <vector>

static std::wstring quote(const std::wstring& value) {
    std::wstring out = L"\"";
    size_t slashes = 0;
    for (wchar_t c : value) {
        if (c == L'\\') { ++slashes; continue; }
        out.append(c == L'"' ? 2 * slashes + 1 : slashes, L'\\');
        out += c;
        slashes = 0;
    }
    out.append(2 * slashes, L'\\');
    return out + L"\"";
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    wchar_t image[32768]{};
    DWORD length = GetModuleFileNameW(nullptr, image, ARRAYSIZE(image));
    if (!length || length == ARRAYSIZE(image)) return 1;
    auto root = std::filesystem::path(image).parent_path();
    auto python = root / L"runtime/bin/python3.14w.exe";
    auto entry = root / L"app/start.pyc";
    std::wstring cmd = quote(python.wstring()) + L" -I -B -X utf8 " + quote(entry.wstring());
    int count = 0;
    auto args = CommandLineToArgvW(GetCommandLineW(), &count);
    if (!args) return 1;
    for (int i = 1; i < count; ++i) cmd += L" " + quote(args[i]);
    LocalFree(args);
    STARTUPINFOW si{sizeof(si)};
    PROCESS_INFORMATION pi{};
    if (!CreateProcessW(python.c_str(), cmd.data(), nullptr, nullptr, FALSE, 0,
                        nullptr, nullptr, &si, &pi)) {
        MessageBoxW(nullptr, L"无法启动随包运行库。请从安装目录运行，或先完整解压便携包。", L"Inkpad", MB_ICONERROR);
        return 1;
    }
    CloseHandle(pi.hThread);
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code = 1;
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hProcess);
    return static_cast<int>(code);
}
