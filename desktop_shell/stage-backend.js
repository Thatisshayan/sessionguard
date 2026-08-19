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

function removeResidue(dir) {
  if (!fs.existsSync(dir)) {
    return;
  }
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (SKIP_DIRS.has(entry.name)) {
        fs.rmSync(fullPath, { recursive: true, force: true });
        continue;
      }
      removeResidue(fullPath);
      continue;
    }
    if (SKIP_FILE_SUFFIXES.some((suffix) => entry.name.endsWith(suffix))) {
      fs.rmSync(fullPath, { force: true });
    }
  }
}

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

function getRuntimeCheckPath(runtime, dir) {
  if (runtime === "python_win") {
    const pth = fs.readdirSync(dir).find((name) => name.endsWith("._pth"));
    if (pth) {
      return path.join(dir, pth);
    }
  }
  const checkFile = RUNTIME_CHECKS[runtime];
  return checkFile ? path.join(dir, checkFile) : null;
}

function getMissingBundledPythonModules(pythonRoot) {
  const pythonExe = path.join(pythonRoot, "python.exe");
  if (!fs.existsSync(pythonExe)) {
    return ["python.exe"];
  }
  const probe = [
    "import importlib.util, sys",
    "mods = ['uvicorn','fastapi','multipart','jwt','structlog','dotenv','cv2','numpy','pandas','openpyxl','reportlab','pytesseract','aiosqlite','httpx']",
    "missing = [m for m in mods if importlib.util.find_spec(m) is None]",
    "print(','.join(missing))",
    "sys.exit(1 if missing else 0)",
  ].join("; ");

  const res = spawnSync(pythonExe, ["-c", probe], {
    cwd: pythonRoot,
    encoding: "utf8",
    env: {
      ...process.env,
      PYTHONDONTWRITEBYTECODE: "1",
    },
  });
  const output = (res.stdout || res.stderr || "").trim();
  if (res.status === 0) {
    return [];
  }
  return output ? output.split(",").filter(Boolean) : ["unknown"];
}

function verifyBundledPython(destRoot) {
  const missing = getMissingBundledPythonModules(path.join(destRoot, "python_win"));
  if (!missing.length) {
    return;
  }
  throw new Error(
    `bundled python runtime is missing required modules: ${missing.join(",")}. ` +
    `Re-stage desktop_shell/bundle/python_win with all backend dependencies before building.`
  );
}

for (const runtime of ["python_win", "tesseract_win", "ffmpeg_win"]) {
  const srcDir = path.join(root, "desktop_shell", "bundle", runtime);
  const dstDir = path.join(dest, runtime);

  if (fs.existsSync(srcDir) && fs.readdirSync(srcDir).length > 0) {
    const srcCheck = getRuntimeCheckPath(runtime, srcDir);
    const dstCheck = getRuntimeCheckPath(runtime, dstDir);
    const pythonDstMissing = runtime === "python_win"
      ? getMissingBundledPythonModules(dstDir)
      : [];

    if (
      srcCheck &&
      dstCheck &&
      fs.existsSync(dstCheck) &&
      fs.existsSync(srcCheck) &&
      pythonDstMissing.length === 0 &&
      fs.statSync(srcCheck).mtimeMs <= fs.statSync(dstCheck).mtimeMs
    ) {
      console.log(`[stage-backend] runtime ${runtime} is up-to-date in ${dstDir}, skipping full re-copy.`);
      continue;
    }
    console.log(`[stage-backend] staging runtime: ${runtime}`);
    copyDir(srcDir, dstDir);
  }
}

removeResidue(dest);
verifyBundledPython(dest);

console.log(`[stage-backend] staged backend sources into ${dest}`);
