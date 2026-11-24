// Inspect the shortcut through the Unicode Windows Shell interface used by Explorer.
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shobjidl.h>
#include <wrl/client.h>
#include <filesystem>
#include <cstdio>

using Microsoft::WRL::ComPtr;
namespace fs = std::filesystem;

static bool matches(PCWSTR actual, const fs::path& expected) {
    std::error_code error;
    if (fs::equivalent(actual, expected, error)) return true;
    std::fwprintf(stderr, L"Shortcut path mismatch: %ls, expected %ls\n", actual, expected.c_str());
    return false;
}

int wmain(int count, wchar_t** args) {
    if (count != 3 || FAILED(CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED))) return 1;
    ComPtr<IShellLinkW> link;
    ComPtr<IPersistFile> file;
    if (FAILED(CoCreateInstance(CLSID_ShellLink, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&link)))
        || FAILED(link.As(&file)) || FAILED(file->Load(args[1], STGM_READ))) return 2;
    if (FAILED(link->Resolve(nullptr, SLR_NO_UI | SLR_NOSEARCH | SLR_NOTRACK | SLR_NOUPDATE))) return 3;
    wchar_t path[32768]{};
    const fs::path folder(args[2]);
    const auto exe = folder / L"Inkpad.exe";
    if (FAILED(link->GetPath(path, ARRAYSIZE(path), nullptr, 0)) || !matches(path, exe)) return 4;
    if (FAILED(link->GetWorkingDirectory(path, ARRAYSIZE(path))) || !matches(path, folder)) return 5;
    int index = -1;
    if (FAILED(link->GetIconLocation(path, ARRAYSIZE(path), &index)) || index != 0 || !matches(path, exe)) return 6;
    return 0;
}
