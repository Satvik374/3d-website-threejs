// ==WindhawkMod==
// @id              explorer-translucent-filelist
// @name            File Explorer Translucent File List
// @description     Makes the black file-list area of Windows 11 File Explorer translucent (acrylic blur), matching the rest of the window chrome.
// @version         0.1
// @author          You
// @include         explorer.exe
// @compilerOptions -ldwmapi
// @license         MIT
// ==/WindhawkMod==

// ==WindhawkModReadme==
/*
# File Explorer Translucent File List

In Windows 11 the File Explorer title bar, address bar and navigation pane all
get the Mica/Acrylic treatment from the OS, but the **file listing area** in
the middle stays a solid black/white rectangle. This mod tries to make that
area translucent so the whole window has a consistent translucent look.

## How it works

`explorer.exe` hosts the file list inside a child window (commonly
`DirectUIHWND` inside `SHELLDLL_DefView`, plus, on newer builds, XAML island
content-bridge windows). The mod:

1. Hooks `CreateWindowExW` to detect those windows as Explorer creates them.
2. Applies an Acrylic accent policy via the undocumented
   `SetWindowCompositionAttribute` API.
3. Optionally subclasses the window to discard `WM_ERASEBKGND`, so the opaque
   background doesn't paint on top of the blur.
4. Walks already-existing windows when the mod loads, so it works without
   restarting Explorer.

## Settings

- **Tint color / opacity** — color drawn behind the blur. Set opacity to 0 for
  pure blur with no tint.
- **Aggressive mode** — also intercept `WM_ERASEBKGND`. Turn this on if the
  section still looks opaque with the default settings.

## Caveats

The new tabbed File Explorer renders parts of its UI through DirectComposition
/ XAML surfaces that *cannot* be made translucent through accent policy alone.
If the area is still opaque after enabling Aggressive mode, that view is being
painted by the XAML compositor and a different hook (e.g. into the XAML
backdrop brushes) would be required.
*/
// ==/WindhawkModReadme==

// ==WindhawkModSettings==
/*
- tint:
  - red: 0
  - green: 0
  - blue: 0
  $name: Tint color
  $description: RGB tint drawn behind the blur (0-255 each).
- opacity: 80
  $name: Tint opacity (0-255)
  $description: 0 = no tint (pure blur), 255 = solid tint color.
- aggressive: false
  $name: Aggressive mode
  $description: Also swallow WM_ERASEBKGND so the opaque background doesn't repaint over the blur. Try this if the section is still solid.
*/
// ==/WindhawkModSettings==

#include <windows.h>
#include <dwmapi.h>
#include <mutex>
#include <unordered_map>

// ---------- Undocumented accent-policy API ----------
enum ACCENT_STATE {
    ACCENT_DISABLED                   = 0,
    ACCENT_ENABLE_GRADIENT            = 1,
    ACCENT_ENABLE_TRANSPARENTGRADIENT = 2,
    ACCENT_ENABLE_BLURBEHIND          = 3,
    ACCENT_ENABLE_ACRYLICBLURBEHIND   = 4,
    ACCENT_ENABLE_HOSTBACKDROP        = 5,
};

struct ACCENT_POLICY {
    DWORD AccentState;
    DWORD AccentFlags;
    DWORD GradientColor;   // 0xAABBGGRR
    DWORD AnimationId;
};

enum WINDOWCOMPOSITIONATTRIB {
    WCA_ACCENT_POLICY = 19,
};

struct WINDOWCOMPOSITIONATTRIBDATA {
    DWORD  Attribute;
    PVOID  pData;
    SIZE_T cbData;
};

using SetWindowCompositionAttribute_t =
    BOOL(WINAPI*)(HWND, WINDOWCOMPOSITIONATTRIBDATA*);

static SetWindowCompositionAttribute_t g_SetWindowCompositionAttribute = nullptr;

// ---------- Settings ----------
static struct {
    BYTE r, g, b;
    BYTE opacity;
    bool aggressive;
} g_settings;

// ---------- State ----------
static std::mutex g_mutex;
static std::unordered_map<HWND, WNDPROC> g_subclassed;

// ---------- Helpers ----------
static bool IsTargetClass(LPCWSTR className) {
    if (!className) return false;
    return _wcsicmp(className, L"DirectUIHWND") == 0 ||
           _wcsicmp(className, L"SHELLDLL_DefView") == 0 ||
           _wcsicmp(className, L"Microsoft.UI.Content.DesktopChildSiteBridge") == 0 ||
           _wcsicmp(className, L"Windows.UI.Composition.DesktopWindowContentBridge") == 0;
}

static void ApplyAcrylic(HWND hwnd) {
    if (!g_SetWindowCompositionAttribute || !IsWindow(hwnd)) return;

    // 0xAABBGGRR
    DWORD color = (DWORD(g_settings.opacity) << 24) |
                  (DWORD(g_settings.b)       << 16) |
                  (DWORD(g_settings.g)       <<  8) |
                  (DWORD(g_settings.r));

    ACCENT_POLICY policy{};
    policy.AccentState   = ACCENT_ENABLE_ACRYLICBLURBEHIND;
    policy.AccentFlags   = 0;
    policy.GradientColor = color;
    policy.AnimationId   = 0;

    WINDOWCOMPOSITIONATTRIBDATA data{};
    data.Attribute = WCA_ACCENT_POLICY;
    data.pData     = &policy;
    data.cbData    = sizeof(policy);

    g_SetWindowCompositionAttribute(hwnd, &data);
}

static LRESULT CALLBACK SubclassProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    WNDPROC orig = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        auto it = g_subclassed.find(hwnd);
        if (it != g_subclassed.end()) orig = it->second;
    }
    if (!orig) return DefWindowProcW(hwnd, msg, wParam, lParam);

    if (g_settings.aggressive && msg == WM_ERASEBKGND) {
        // Tell the system the background is already erased — let blur show through.
        return 1;
    }

    if (msg == WM_NCDESTROY) {
        std::lock_guard<std::mutex> lock(g_mutex);
        g_subclassed.erase(hwnd);
        SetWindowLongPtrW(hwnd, GWLP_WNDPROC, (LONG_PTR)orig);
    }

    return CallWindowProcW(orig, hwnd, msg, wParam, lParam);
}

static void Subclass(HWND hwnd) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_subclassed.count(hwnd)) return;
    WNDPROC oldProc = (WNDPROC)SetWindowLongPtrW(hwnd, GWLP_WNDPROC, (LONG_PTR)SubclassProc);
    if (oldProc) g_subclassed.emplace(hwnd, oldProc);
}

static void TryProcessWindow(HWND hwnd, LPCWSTR className) {
    Wh_Log(L"Translucenting window class=%s hwnd=%p", className, hwnd);
    ApplyAcrylic(hwnd);
    Subclass(hwnd);
    InvalidateRect(hwnd, nullptr, TRUE);
}

// ---------- Hook: CreateWindowExW ----------
using CreateWindowExW_t = decltype(&CreateWindowExW);
static CreateWindowExW_t CreateWindowExW_Original;

static HWND WINAPI CreateWindowExW_Hook(DWORD dwExStyle, LPCWSTR lpClassName,
        LPCWSTR lpWindowName, DWORD dwStyle, int X, int Y, int nWidth,
        int nHeight, HWND hWndParent, HMENU hMenu, HINSTANCE hInstance,
        LPVOID lpParam) {
    HWND hwnd = CreateWindowExW_Original(dwExStyle, lpClassName, lpWindowName,
        dwStyle, X, Y, nWidth, nHeight, hWndParent, hMenu, hInstance, lpParam);

    if (hwnd && lpClassName && !IS_INTRESOURCE(lpClassName) && IsTargetClass(lpClassName)) {
        TryProcessWindow(hwnd, lpClassName);
    }
    return hwnd;
}

// ---------- Walk pre-existing windows ----------
static BOOL CALLBACK EnumChildProc(HWND hwnd, LPARAM) {
    wchar_t cls[128] = {};
    if (GetClassNameW(hwnd, cls, _countof(cls)) && IsTargetClass(cls)) {
        TryProcessWindow(hwnd, cls);
    }
    return TRUE;
}

static BOOL CALLBACK EnumTopProc(HWND hwnd, LPARAM) {
    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    if (pid == GetCurrentProcessId()) {
        EnumChildWindows(hwnd, EnumChildProc, 0);
    }
    return TRUE;
}

// ---------- Settings ----------
static void LoadSettings() {
    g_settings.r          = (BYTE)Wh_GetIntSetting(L"tint.red");
    g_settings.g          = (BYTE)Wh_GetIntSetting(L"tint.green");
    g_settings.b          = (BYTE)Wh_GetIntSetting(L"tint.blue");
    g_settings.opacity    = (BYTE)Wh_GetIntSetting(L"opacity");
    g_settings.aggressive = Wh_GetIntSetting(L"aggressive") != 0;
}

// ---------- Lifecycle ----------
BOOL Wh_ModInit() {
    Wh_Log(L"Init");
    LoadSettings();

    HMODULE hUser = GetModuleHandleW(L"user32.dll");
    if (hUser) {
        g_SetWindowCompositionAttribute =
            (SetWindowCompositionAttribute_t)GetProcAddress(
                hUser, "SetWindowCompositionAttribute");
    }
    if (!g_SetWindowCompositionAttribute) {
        Wh_Log(L"SetWindowCompositionAttribute not available — accent policy will be skipped.");
    }

    Wh_SetFunctionHook((void*)CreateWindowExW,
                       (void*)CreateWindowExW_Hook,
                       (void**)&CreateWindowExW_Original);
    return TRUE;
}

void Wh_ModAfterInit() {
    // Run after hooks are committed so we don't miss anything.
    EnumWindows(EnumTopProc, 0);
}

void Wh_ModUninit() {
    Wh_Log(L"Uninit");
    std::lock_guard<std::mutex> lock(g_mutex);
    for (auto& kv : g_subclassed) {
        if (IsWindow(kv.first)) {
            SetWindowLongPtrW(kv.first, GWLP_WNDPROC, (LONG_PTR)kv.second);

            // Disable the accent policy on unload.
            if (g_SetWindowCompositionAttribute) {
                ACCENT_POLICY policy{ ACCENT_DISABLED, 0, 0, 0 };
                WINDOWCOMPOSITIONATTRIBDATA data{ WCA_ACCENT_POLICY, &policy, sizeof(policy) };
                g_SetWindowCompositionAttribute(kv.first, &data);
            }
            InvalidateRect(kv.first, nullptr, TRUE);
        }
    }
    g_subclassed.clear();
}

void Wh_ModSettingsChanged() {
    Wh_Log(L"SettingsChanged");
    LoadSettings();
    std::lock_guard<std::mutex> lock(g_mutex);
    for (auto& kv : g_subclassed) {
        if (IsWindow(kv.first)) {
            ApplyAcrylic(kv.first);
            InvalidateRect(kv.first, nullptr, TRUE);
        }
    }
}
