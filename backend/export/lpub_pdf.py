# backend/export/lpub_pdf.py
import os, subprocess, shutil

def _resolve_lpub3d_exe() -> str:
    exe_env = os.getenv("LPUB3D_EXE")
    if exe_env and os.path.isfile(exe_env):
        return exe_env
    exe = shutil.which("LPub3D")
    if exe:
        return exe
    guess = r"C:\Program Files\LPub3D\LPub3D.exe"
    if os.path.isfile(guess):
        return guess
    raise FileNotFoundError("LPub3D executable not found. Set LPUB3D_EXE or add to PATH.")

def _resolve_ldraw_dir() -> str | None:
    d = os.getenv("LDRAW_DIR")
    if d and os.path.isdir(d):
        return d
    d = os.path.join(os.getenv("LOCALAPPDATA", ""), "LPub3D Software", "LDraw")
    return d if os.path.isdir(d) else None

def make_pdf(model_path: str, outdir: str, timeout_s: int = 45) -> str | None:
    os.makedirs(outdir, exist_ok=True)
    pdf_path = os.path.join(outdir, "instructions.pdf")
    exe = _resolve_lpub3d_exe()
    ldraw_dir = _resolve_ldraw_dir()

    cmd = [exe, os.path.abspath(model_path), "-o", os.path.abspath(pdf_path)]
    if ldraw_dir:
        cmd.extend(["-l", os.path.abspath(ldraw_dir)])

    print("LPub3D command:", cmd)
    try:
        subprocess.run(cmd, check=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        print(f"LPub3D timed out after {timeout_s}s — skipping.")
        return None
    except Exception as e:
        print("LPub3D PDF generation failed:", e)
        return None

    return pdf_path if os.path.isfile(pdf_path) else None
