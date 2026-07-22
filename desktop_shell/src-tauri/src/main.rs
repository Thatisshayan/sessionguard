#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::{
    process::{Child, Command},
    sync::{Arc, Mutex},
    thread,
    time::Duration,
};
use tauri::{
    AppHandle, CustomMenuItem, GlobalShortcutManager, Manager, SystemTray, SystemTrayEvent,
    SystemTrayMenu, SystemTrayMenuItem, WindowEvent,
};

#[cfg(windows)]
use std::os::windows::process::CommandExt;
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

struct BackendProcess(Arc<Mutex<Option<Child>>>);

fn find_python() -> String {
    // Check bundled Python first (for distributed builds)
    if let Some(exe) = std::env::current_exe().ok() {
        if let Some(dir) = exe.parent() {
            let bundled = dir.join("bundled").join("python").join("python.exe");
            if bundled.exists() {
                return bundled.to_string_lossy().to_string();
            }
        }
    }

    let candidates = vec![
        r"C:\Users\Shaya\AppData\Local\Programs\Python\Python312\python.exe".to_string(),
        r"C:\Users\Shaya\AppData\Local\Programs\Python\Python311\python.exe".to_string(),
        r"C:\Python312\python.exe".to_string(),
        r"C:\Python311\python.exe".to_string(),
        r"C:\Python310\python.exe".to_string(),
    ];
    for path in &candidates {
        if std::path::Path::new(path).exists() {
            println!("[Tauri] Found Python at: {}", path);
            return path.clone();
        }
    }
    println!("[Tauri] Falling back to system python");
    "python".to_string()
}

fn find_project_root() -> String {
    // Check bundled location
    if let Some(exe) = std::env::current_exe().ok() {
        if let Some(dir) = exe.parent() {
            let bundled = dir.join("bundled").join("sessionguard");
            if bundled.exists() {
                return bundled.to_string_lossy().to_string();
            }
        }
    }

    let known = r"C:\Projects\SessionGuard\sessionguard";
    if std::path::Path::new(known).exists() {
        return known.to_string();
    }
    let exe = std::env::current_exe().unwrap_or_default();
    exe.parent()
        .and_then(|p| p.parent())
        .and_then(|p| p.parent())
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|| ".".to_string())
}

fn start_backend() -> Option<Child> {
    let python = find_python();
    let root   = find_project_root();

    println!("[Tauri] Starting backend from: {}", root);

    #[cfg(windows)]
    let result = Command::new(&python)
        .args([
            "-m", "uvicorn",
            "backend.main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--no-access-log",
        ])
        .current_dir(&root)
        .env("PYTHONPATH", &root)
        .creation_flags(CREATE_NO_WINDOW)
        .spawn();

    #[cfg(not(windows))]
    let result = Command::new(&python)
        .args([
            "-m", "uvicorn",
            "backend.main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--no-access-log",
        ])
        .current_dir(&root)
        .env("PYTHONPATH", &root)
        .spawn();

    match result {
        Ok(child)  => { println!("[Tauri] Backend PID {}", child.id()); Some(child) }
        Err(e)     => { eprintln!("[Tauri] Backend failed to start: {}", e); None }
    }
}

fn wait_for_backend(max_secs: u64) -> bool {
    for _ in 0..(max_secs * 2) {
        thread::sleep(Duration::from_millis(500));
        if reqwest::blocking::get("http://127.0.0.1:8000/health")
            .map(|r| r.status().is_success())
            .unwrap_or(false)
        {
            println!("[Tauri] Backend ready.");
            return true;
        }
    }
    eprintln!("[Tauri] Backend did not respond in {}s", max_secs);
    false
}

#[tauri::command]
fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[tauri::command]
fn restart_backend(state: tauri::State<BackendProcess>) -> bool {
    let mut guard = state.0.lock().unwrap();
    if let Some(ref mut child) = *guard {
        let _ = child.kill();
    }
    *guard = start_backend();
    guard.is_some()
}

fn build_tray() -> SystemTray {
    let open     = CustomMenuItem::new("open",    "Open SessionGuard");
    let docs     = CustomMenuItem::new("docs",    "API Docs");
    let restart  = CustomMenuItem::new("restart", "Restart Backend");
    let sep      = SystemTrayMenuItem::Separator;
    let quit     = CustomMenuItem::new("quit",    "Quit");

    let menu = SystemTrayMenu::new()
        .add_item(open)
        .add_item(docs)
        .add_native_item(sep.clone())
        .add_item(restart)
        .add_native_item(sep)
        .add_item(quit);

    SystemTray::new().with_menu(menu)
}

fn handle_tray(app: &AppHandle, event: SystemTrayEvent) {
    match event {
        SystemTrayEvent::LeftClick { .. } => {
            if let Some(w) = app.get_window("main") {
                let _ = w.show(); let _ = w.set_focus();
            }
        }
        SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
            "open" => {
                if let Some(w) = app.get_window("main") {
                    let _ = w.show(); let _ = w.set_focus();
                }
            }
            "docs" => {
                let _ = tauri::api::shell::open(
                    &app.shell_scope(), "http://127.0.0.1:8000/docs", None
                );
            }
            "restart" => {
                let state = app.state::<BackendProcess>();
                let proc  = state.0.clone();
                thread::spawn(move || {
                    let mut g = proc.lock().unwrap();
                    if let Some(ref mut c) = *g { let _ = c.kill(); }
                    thread::sleep(Duration::from_secs(1));
                    *g = start_backend();
                });
            }
            "quit" => { app.exit(0); }
            _ => {}
        },
        _ => {}
    }
}

fn main() {
    // ── Portable mode detection ─────────────────────────────────────────────
    let args: Vec<String> = std::env::args().collect();
    let portable_mode = args.iter().any(|a| a == "--portable");

    if portable_mode {
        if let Some(exe_path) = std::env::current_exe().ok() {
            if let Some(exe_dir) = exe_path.parent() {
                let data_dir = exe_dir.join("data");
                std::env::set_var("SG_DATA_DIR", data_dir.to_string_lossy().to_string());
                println!("[Tauri] Portable mode ON — data at: {}", data_dir.display());
            }
        }
    }

    tauri::Builder::default()
        .manage(BackendProcess(Arc::new(Mutex::new(None))))
        .system_tray(build_tray())
        .on_system_tray_event(handle_tray)
        .setup(|app| {
            let state = app.state::<BackendProcess>();
            let mut guard = state.0.lock().unwrap();
            *guard = start_backend();
            drop(guard);

            // Wait up to 12 seconds for backend
            wait_for_backend(12);

            // Register global shortcuts
            let handle = app.handle();
            let mut gs = handle.global_shortcut_manager();
            let _ = gs.register("Ctrl+Shift+S", move || {
                if let Some(w) = handle.get_window("main") {
                    let _ = w.show();
                    let _ = w.set_focus();
                    // Emit screenshot event to frontend
                    let _ = w.emit("global-screenshot", ());
                }
            });

            Ok(())
        })
        .on_window_event(|event| {
            // X button hides to tray instead of closing
            if let WindowEvent::CloseRequested { api, .. } = event.event() {
                if event.window().label() == "main" {
                    event.window().hide().unwrap();
                    api.prevent_close();
                }
            }
        })
        .on_window_event(|event| {
            // Kill backend when app fully exits
            if let WindowEvent::Destroyed = event.event() {}
        })
        .invoke_handler(tauri::generate_handler![get_app_version, restart_backend])
        .run(tauri::generate_context!())
        .expect("SessionGuard failed to start");
}
