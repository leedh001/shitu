# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['vl_gui.py'],
    pathex=[],
    binaries=[
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\llama.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\mtmd.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-base.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-alderlake.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-cannonlake.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-cascadelake.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-cooperlake.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-haswell.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-icelake.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-ivybridge.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-piledriver.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-sandybridge.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-sapphirerapids.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-skylakex.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-sse42.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-x64.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cpu-zen4.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\ggml-cuda.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\libomp140.x86_64.dll', 'llama_cpp/lib'),
        ('D:\\anaconda3\\envs\\shitu2\\Lib\\site-packages\\llama_cpp\\lib\\llama-common.dll', 'llama_cpp/lib'),
    ],
    datas=[('model', 'model')],
    hiddenimports=[
        'chromadb.api.rust',
        'chromadb.telemetry.product.posthog'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='vl_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='vl_gui',
)
