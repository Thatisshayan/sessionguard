// Copies the Python backend source into src-tauri/bundled_app so Tauri's
// resource bundler ships it inside the installer. Runs from tauri.conf.json's
// build.beforeBuildCommand, after the frontend build.
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const dest = path.resolve(__dirname, "src-tauri", "bundled_app");

const SKIP_DIRS = new Set(["__pycache__", ".pytest_cache", ".venv", "storage"]);
const SKIP_FILE_SUFFIXES = [".db", ".db-wal", ".db-shm"];

function copyDir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name)) continue;
    if (SKIP_FILE_SUFFIXES.some((suf) => entry.name.endsWith(suf))) continue;
    const s = path.join(src, entry.name);
    const d = path.join(dst, entry.name);
    if (entry.isDirectory()) {
      copyDir(s, d);
    } else {
      fs.copyFileSync(s, d);
    }
  }
}

fs.rmSync(dest, { recursive: true, force: true });
fs.mkdirSync(dest, { recursive: true });

for (const dir of ["backend", "engines", "database", "config"]) {
  copyDir(path.join(root, dir), path.join(dest, dir));
}
for (const file of ["requirements.txt", "init_db.py"]) {
  fs.copyFileSync(path.join(root, file), path.join(dest, file));
}

console.log(`[stage-backend] staged backend sources into ${dest}`);
