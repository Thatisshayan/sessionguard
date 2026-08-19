#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::{
    env,
    fs,
    path::PathBuf,
    process::{Child, Command},
    sync::{Arc, Mutex},
    thread,
    time::Duration,
};
use rand::RngCore;
use sentry::{init, types::Dsn, Level};
use tauri::{
    AppHandle, CustomMenuItem, GlobalShortcutManager, Manager, SystemTray, SystemTrayEvent,
    SystemTrayMenu, SystemTrayMenuItem, WindowEvent,
};

#[cfg(windows)]
use std::os::windows::process::CommandExt;
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

fn setup_sentry() {
    let dsn_str = std::env::var("SENTRY_DSN").unwrap_or_default();
    if dsn_str.is_empty() {
        println!("[Sentry] No SENTRY_DSN — crash reporting disabled");
        return;
    }

    let dsn: Dsn = dsn_str.parse().expect("Invalid Sentry DSN");
    let _ = init(dsn);

    println!("[Sentry] Crash reporting enabled — DSN: {}", dsn_str.split('@').last().unwrap_or("***"));
}

struct BackendProcess(Arc<Mutex<Option<Child>>>);

fn log_line(msg: &str) {
    println!("{msg}");
    if let Some(exe) = std::env::current_exe().ok() {
        if let Some(dir) = exe.parent() {
            let log_path = dir.join("sessionguard.log");
            if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(log_path) {
                use std::io::Write;
                let _ = writeln!(f, "{msg}");
            }
        }
    }
}

fn show_fatal_error(app: &AppHandle, msg: &str) {
    log_line(&format!("[Tauri] FATAL: {msg}"));
    if let Some(w) = app.get_window("main") {
        let escaped = msg.replace('\\', "\\\\").replace('\'', "\\'").replace('\n', "\\n");
        let _ = w.eval(&format!("alert('SessionGuard: {escaped}')"));
    }
}

fn resolve_bundled_app_root(app: &AppHandle) -> Option<PathBuf> {
    app.path_resolver().resolve_resource("bundled_app")
}

fn find_bundled_python(app: &AppHandle) -> Option<PathBuf> {
    let bundled_root = resolve_bundled_app_root(app)?;
    for folder in ["python_win", "python"] {
        let candidate = bundled_root.join(folder).join("python.exe");
        if candidate.exists() {
            return Some(candidate);
        }
    }
    None
}

fn resolve_data_dir(app: &AppHandle, portable_mode: bool) -> Result<PathBuf, String> {
    if portable_mode {
        let exe = std::env::current_exe().map_err(|e| format!("current_exe failed: {e}"))?;
        let dir = exe
            .parent()
            .ok_or_else(|| "failed to resolve executable directory".to_string())?;
        return Ok(dir.join("data"));
    }

    app.path_resolver()
        .app_local_data_dir()
        .or_else(|| app.path_resolver().app_data_dir())
        .ok_or_else(|| "failed to resolve app data directory".to_string())
}

fn generate_secret_key() -> String {
    let mut bytes = [0u8; 32];
    rand::thread_rng().fill_bytes(&mut bytes);
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn ensure_secret_key(data_dir: &std::path::Path) -> Result<String, String> {
    if let Ok(secret) = std::env::var("SECRET_KEY") {
        let trimmed = secret.trim();
        if !trimmed.is_empty() {
            return Ok(trimmed.to_string());
        }
    }

    let config_dir = data_dir.join("config");
    fs::create_dir_all(&config_dir)
        .map_err(|e| format!("failed to create config directory {}: {e}", config_dir.display()))?;
    let secret_path = config_dir.join("sessionguard.secret");

    if secret_path.exists() {
        let existing = fs::read_to_string(&secret_path)
            .map_err(|e| format!("failed to read {}: {e}", secret_path.display()))?;
        let trimmed = existing.trim();
        if !trimmed.is_empty() {
            return Ok(trimmed.to_string());
        }
    }

    let generated = generate_secret_key();
    fs::write(&secret_path, format!("{generated}\n"))
        .map_err(|e| format!("failed to write {}: {e}", secret_path.display()))?;
    log_line(&format!(
        "[Tauri] Generated local SECRET_KEY at {}",
        secret_path.display()
    ));
    Ok(generated)
}

/// Resolves the backend source directory. Checks, in order: the resources
/// bundled into the installer (the normal path for an installed app), then
/// SESSIONGUARD_ROOT (for pointing a dev build at a specific checkout).
/// Returns None rather than guessing at a directory that might not actually
/// contain the backend — silently running the wrong code is worse than
/// failing loudly.
fn find_project_root(app: &AppHandle) -> Option<String> {
    if let Some(resource_path) = resolve_bundled_app_root(app) {
        if resource_path.join("backend").join("main.py").exists() {
            return Some(resource_path.to_string_lossy().to_string());
        }
        log_line(&format!(
            "[Tauri] bundled_app resolved to {} but backend/main.py is missing",
            resource_path.display()
        ));
    }

    if let Ok(dev_root) = std::env::var("SESSIONGUARD_ROOT") {
        if std::path::Path::new(&dev_root).join("backend").join("main.py").exists() {
            log_line(&format!("[Tauri] Using SESSIONGUARD_ROOT override: {dev_root}"));
            return Some(dev_root);
        }
        log_line(&format!("[Tauri] SESSIONGUARD_ROOT is set but doesn't contain backend/main.py: {dev_root}"));
    }

    None
}

fn start_backend(app: &AppHandle) -> Option<Child> {
    let root = match find_project_root(app) {
        Some(r) => r,
        None => {
            show_fatal_error(
                app,
                "Backend source files were not found in the install. Try reinstalling the app; for development, set the SESSIONGUARD_ROOT environment variable to your checkout path.",
            );
            return None;
        }
    };

    log_line(&format!("[Tauri] Starting backend from: {}", root));
    let root_path = PathBuf::from(&root);
    let bundled_root = resolve_bundled_app_root(app);
    let using_bundled_backend = bundled_root
        .as_ref()
        .map(|p| p == &root_path)
        .unwrap_or(false);
    let portable_mode = std::env::args().any(|a| a == "--portable");

    let data_dir = match resolve_data_dir(app, portable_mode) {
        Ok(path) => path,
        Err(err) => {
            show_fatal_error(app, &format!("Failed to resolve writable app data directory: {err}"));
            return None;
        }
    };
    if let Err(err) = fs::create_dir_all(&data_dir) {
        show_fatal_error(app, &format!("Failed to create app data directory {}: {err}", data_dir.display()));
        return None;
    }

    let secret_key = match ensure_secret_key(&data_dir) {
        Ok(secret) => secret,
        Err(err) => {
            show_fatal_error(app, &format!("Failed to provision local SECRET_KEY: {err}"));
            return None;
        }
    };

    let python = if using_bundled_backend {
        match find_bundled_python(app) {
            Some(path) => path.to_string_lossy().to_string(),
            None => {
                show_fatal_error(
                    app,
                    "Bundled Python runtime is missing from the installed app. Reinstall the app or rebuild the installer with desktop_shell/bundle/python_win staged.",
                );
                return None;
            }
        }
    } else {
        log_line("[Tauri] No bundled Python found for this launch context — relying on system `python` from PATH");
        "python".to_string()
    };

    #[cfg(windows)]
    let result = {
        let mut cmd = Command::new(&python);
        cmd.args([
                "-m", "uvicorn",
                "backend.main:app",
                "--host", "127.0.0.1",
                "--port", "8000",
                "--no-access-log",
            ])
            .current_dir(&root)
            .env("PYTHONPATH", &root)
            .env("SG_DATA_DIR", &data_dir)
            .env("SECRET_KEY", &secret_key);

        let mut extra_paths: Vec<String> = Vec::new();
        for folder in ["ffmpeg_win", "tesseract_win"] {
            let candidate = root_path.join(folder);
            if candidate.exists() {
                extra_paths.push(candidate.to_string_lossy().to_string());
            }
        }
        if !extra_paths.is_empty() {
            let current_path = env::var("PATH").unwrap_or_default();
            let mut combined = extra_paths.join(";");
            if !current_path.is_empty() {
                combined.push(';');
                combined.push_str(&current_path);
            }
            cmd.env("PATH", combined);
        }

        let tess_exe = root_path.join("tesseract_win").join("tesseract.exe");
        if tess_exe.exists() {
            cmd.env("SESSIONGUARD_TESSERACT_CMD", tess_exe.to_string_lossy().to_string());
        }
        let tessdata = root_path.join("tesseract_win").join("tessdata");
        if tessdata.exists() {
            cmd.env("TESSDATA_PREFIX", tessdata.to_string_lossy().to_string());
        }

        cmd.creation_flags(CREATE_NO_WINDOW).spawn()
    };

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
        .env("SG_DATA_DIR", &data_dir)
        .env("SECRET_KEY", &secret_key)
        .spawn();

    match result {
        Ok(child) => {
            log_line(&format!(
                "[Tauri] Backend PID {} | data dir {}{}",
                child.id(),
                data_dir.display(),
                if portable_mode { " (portable)" } else { "" }
            ));
            Some(child)
        }
        Err(e) => {
            show_fatal_error(app, &format!("Backend failed to start: {e}. Is Python installed and on PATH?"));
            None
        }
    }
}

fn wait_for_backend(app: &AppHandle, max_secs: u64) -> bool {
    for _ in 0..(max_secs * 2) {
        thread::sleep(Duration::from_millis(500));
        if reqwest::blocking::get("http://127.0.0.1:8000/health")
            .map(|r| r.status().is_success())
            .unwrap_or(false)
        {
            log_line("[Tauri] Backend ready.");
            return true;
        }
    }
    show_fatal_error(app, &format!("Backend did not respond within {max_secs}s. Check sessionguard.log next to the app executable."));
    false
}

#[tauri::command]
fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[tauri::command]
fn restart_backend(app: AppHandle, state: tauri::State<BackendProcess>) -> bool {
    let mut guard = state.0.lock().unwrap();
    if let Some(ref mut child) = *guard {
        let _ = child.kill();
    }
    *guard = start_backend(&app);
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
                let state  = app.state::<BackendProcess>();
                let proc   = state.0.clone();
                let handle = app.clone();
                thread::spawn(move || {
                    let mut g = proc.lock().unwrap();
                    if let Some(ref mut c) = *g { let _ = c.kill(); }
                    thread::sleep(Duration::from_secs(1));
                    *g = start_backend(&handle);
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
        println!("[Tauri] Portable mode requested.");
    }

    // ── Sentry (after portable mode, before backend) ─────────────────────────
    setup_sentry();

    // Sentry panic hook
    std::panic::set_hook(Box::new(|panic_info| {
        let msg = panic_info.to_string();
        println!("[PANIC] {}", msg);
        sentry::capture_message(&msg, Level::Error);
    }));

    tauri::Builder::default()
        .manage(BackendProcess(Arc::new(Mutex::new(None))))
        .system_tray(build_tray())
        .on_system_tray_event(handle_tray)
        .setup(|app| {
            let handle = app.handle();
            let state = app.state::<BackendProcess>();
            let mut guard = state.0.lock().unwrap();
            *guard = start_backend(&handle);
            drop(guard);

            // First-run bundled backends can take noticeably longer to import
            // and initialize than dev-mode host Python launches.
            wait_for_backend(&handle, 60);

            // Register global shortcuts
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
