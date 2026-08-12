// Copies the Python backend source into src-tauri/bundled_app so Tauri's
// resource bundler ships it inside the installer. Runs from tauri.conf.json's
// build.beforeBuildCommand, after the frontend build.
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const root = path.resolve(__dirname, "..");
const dest = path.resolve(__dirname, "src-tauri", "bundled_app");

const SKIP_DIRS = new Set(["__pycache__", ".pytest_cache", ".venv", "storage"]);
const SKIP_FILE_SUFFIXES = [".db", ".db-wal", ".db-shm"];

function copyDir(src, dst) {
  if (process.platform === "win32") {
    const args = [
      src,
      dst,
      "/E",
      "/MT:16",
      "/XD",
      ...Array.from(SKIP_DIRS),
      "/XF",
      "*.db",
      "*.db-wal",
      "*.db-shm",
      "/NFL",
      "/NDL",
      "/NJH",
      "/NJS",
      "/NC",
      "/NS",
      "/NP",
    ];
    const res = spawnSync("robocopy.exe", args, { stdio: "ignore" });
    if (res.status !== null && res.status >= 8) {
      throw new Error(`robocopy failed with status ${res.status}`);
    }
  } else {
    fs.cpSync(src, dst, {
      recursive: true,
      filter: (source) => {
        const base = path.basename(source);
        if (SKIP_DIRS.has(base)) return false;
        if (SKIP_FILE_SUFFIXES.some((suf) => base.endsWith(suf))) return false;
        return true;
      },
    });
  }
}

// 1. Clean source code folders in dest (backend, engines, database, config) without deleting bundled runtimes
fs.mkdirSync(dest, { recursive: true });
for (const dir of ["backend", "engines", "database", "config"]) {
  const targetDir = path.join(dest, dir);
  if (fs.existsSync(targetDir)) {
    fs.rmSync(targetDir, { recursive: true, force: true });
  }
  copyDir(path.join(root, dir), targetDir);
}

for (const file of ["requirements.txt", "init_db.py"]) {
  fs.copyFileSync(path.join(root, file), path.join(dest, file));
}

// 2. Stage Bundled Runtimes (if present and not already staged)
const RUNTIME_CHECKS = {
  python_win: "python.exe",
  tesseract_win: "tesseract.exe",
  ffmpeg_win: "ffmpeg.exe",
};

for (const runtime of ["python_win", "tesseract_win", "ffmpeg_win"]) {
  const srcDir = path.join(root, "desktop_shell", "bundle", runtime);
  const dstDir = path.join(dest, runtime);
  const checkFile = RUNTIME_CHECKS[runtime];

  if (fs.existsSync(srcDir) && fs.readdirSync(srcDir).length > 0) {
    const srcCheck = checkFile ? path.join(srcDir, checkFile) : null;
    const dstCheck = checkFile ? path.join(dstDir, checkFile) : null;

    if (
      srcCheck &&
      dstCheck &&
      fs.existsSync(dstCheck) &&
      fs.existsSync(srcCheck) &&
      fs.statSync(srcCheck).mtimeMs <= fs.statSync(dstCheck).mtimeMs
    ) {
      console.log(`[stage-backend] runtime ${runtime} is up-to-date in ${dstDir}, skipping full re-copy.`);
      continue;
    }
    console.log(`[stage-backend] staging runtime: ${runtime}`);
    copyDir(srcDir, dstDir);
  }
}

console.log(`[stage-backend] staged backend sources into ${dest}`);
