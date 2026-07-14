from pathlib import Path
import os


ROOT = Path(os.environ["WIZARD_REPOSITORY_ROOT"]).resolve()
ENTRYPOINT = ROOT / "tools" / "run_wizard_avatar_server.py"

if not ENTRYPOINT.is_file():
    raise SystemExit(f"missing sidecar entrypoint: {ENTRYPOINT}")

datas = [
    (str(ROOT / "wizard_avatar" / "definitions"), "wizard_avatar/definitions"),
    (str(ROOT / "web" / "avatar"), "web/avatar"),
    (
        str(ROOT / "assets" / "reference" / "motion_sources" / "manifest.json"),
        "assets/reference/motion_sources",
    ),
]

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
]

a = Analysis(
    [str(ENTRYPOINT)],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="wizard-joe-engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory="_internal",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="wizard-joe-engine",
)
