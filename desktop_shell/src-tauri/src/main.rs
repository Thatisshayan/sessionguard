// src-tauri/src/main.rs
// ---------------------
// SessionGuard native desktop application.
//
// On launch:
//   1. Starts the Python FastAPI backend (uvicorn) as a sidecar process.
//   2. Opens the main window loading the React frontend.
//   3. Shows a system tray icon with quick actions.
//   4. Gracefully stops the backend when the app closes.
//
// Maturity: Production-ready shell. Backend/frontend still served locally.
// Future:   Bundle Python as a sidecar binary (V11), bundle Node (V12).

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"   // No console window in release builds
)]

use std::{
    process::{Child, Command},
    sync::{Arc, Mutex},
    thread,
    time::Duration,
};
use tauri::{
    AppHandle, CustomMenuItem, Manager, SystemTray, SystemTrayEvent,
    SystemTrayMenu, SystemTrayMenuItem, WindowEvent,
};

// ── Backend process manager ────────────────────────────────────────────────────

struct BackendProcess(Arc<Mutex<Option<Child>>>);

fn start_backend(app_dir: &str) -> Option<Child> {
    // Resolve Python executable — try venv first, then system
    let python = if cfg!(target_os = "windows") {
        let venv = format!("{}\\..\\venv\\Scripts\\python.exe", app_dir);
        if std::path::Path::new(&venv).exists() {
            venv
        } else {
            "python".to_string()
        }
    } else {
        let venv = format!("{}/../venv/bin/python3", app_dir);
        if std::path::Path::new(&venv).exists() {
            venv
        } else {
            "python3".to_string()
        }
    };

    let root = format!("{}/..", app_dir);

    println!("[Tauri] Starting backend: {} -m uvicorn backend.main:app ...", python);

    let result = Command::new(&python)
        .args([
            "-m", "uvicorn",
            "backend.main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--app-dir", ".",
        ])
        .current_dir(&root)
        .env("PYTHONPATH", &root)
        .spawn();

    match result {
        Ok(child) => {
            println!("[Tauri] Backend started (PID {})", child.id());
            Some(child)
        }
        Err(e) => {
            eprintln!("[Tauri] Failed to start backend: {}", e);
            None
        }
    }
}

// ── Tauri commands (callable from frontend via invoke) ────────────────────────

#[tauri::command]
fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[tauri::command]
fn open_logs_folder(app: AppHandle) {
    if let Some(log_dir) = app.path_resolver().app_log_dir() {
        let _ = opener::open(log_dir);
    }
}

#[tauri::command]
fn restart_backend(state: tauri::State<BackendProcess>, app: AppHandle) -> bool {
    let mut guard = state.0.lock().unwrap();
    // Kill existing
    if let Some(ref mut child) = *guard {
        let _ = child.kill();
    }
    // Restart
    let app_dir = app.path_resolver()
        .resource_dir()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default();
    *guard = start_backend(&app_dir);
    guard.is_some()
}

// ── System tray ────────────────────────────────────────────────────────────────

fn build_tray() -> SystemTray {
    let open      = CustomMenuItem::new("open",     "Open Dashboard");
    let api_docs  = CustomMenuItem::new("api_docs", "API Docs");
    let separator = SystemTrayMenuItem::Separator;
    let restart   = CustomMenuItem::new("restart",  "Restart Backend");
    let quit      = CustomMenuItem::new("quit",     "Quit SessionGuard");

    let menu = SystemTrayMenu::new()
        .add_item(open)
        .add_item(api_docs)
        .add_native_item(separator.clone())
        .add_item(restart)
        .add_native_item(separator)
        .add_item(quit);

    SystemTray::new().with_menu(menu)
}

fn handle_tray_event(app: &AppHandle, event: SystemTrayEvent) {
    match event {
        SystemTrayEvent::LeftClick { .. } => {
            if let Some(window) = app.get_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }
        SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
            "open" => {
                if let Some(window) = app.get_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
            "api_docs" => {
                let _ = tauri::api::shell::open(
                    &app.shell_scope(),
                    "http://127.0.0.1:8000/docs",
                    None,
                );
            }
            "restart" => {
                let state    = app.state::<BackendProcess>();
                let app_dir  = app.path_resolver()
                    .resource_dir()
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_default();
                let process  = state.0.clone();
                thread::spawn(move || {
                    let mut guard = process.lock().unwrap();
                    if let Some(ref mut child) = *guard {
                        let _ = child.kill();
                    }
                    thread::sleep(Duration::from_secs(1));
                    *guard = start_backend(&app_dir);
                });
            }
            "quit" => {
                app.exit(0);
            }
            _ => {}
        },
        _ => {}
    }
}

// ── Main ───────────────────────────────────────────────────────────────────────

fn main() {
    let backend_state = BackendProcess(Arc::new(Mutex::new(None)));

    tauri::Builder::default()
        .manage(backend_state)
        .system_tray(build_tray())
        .on_system_tray_event(handle_tray_event)
        .setup(|app| {
            // Start Python backend immediately
            let app_dir = app
                .path_resolver()
                .resource_dir()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_else(|| ".".to_string());

            let state = app.state::<BackendProcess>();
            let mut guard = state.0.lock().unwrap();
            *guard = start_backend(&app_dir);

            // Wait for backend to be ready (max 10s)
            let backend_ready = (0..20).any(|_| {
                thread::sleep(Duration::from_millis(500));
                reqwest::blocking::get("http://127.0.0.1:8000/health")
                    .map(|r| r.status().is_success())
                    .unwrap_or(false)
            });

            if !backend_ready {
                eprintln!("[Tauri] Warning: backend did not respond within 10s");
            } else {
                println!("[Tauri] Backend is ready.");
            }

            Ok(())
        })
        .on_window_event(|event| {
            // Hide to tray instead of closing (keep backend running)
            if let WindowEvent::CloseRequested { api, .. } = event.event() {
                let window = event.window();
                if window.label() == "main" {
                    window.hide().unwrap();
                    api.prevent_close();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_app_version,
            open_logs_folder,
            restart_backend,
        ])
        .run(tauri::generate_context!())
        .expect("error while running SessionGuard");
}
