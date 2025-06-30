# build_exe.py
import os
import sys
import subprocess
from pathlib import Path

def create_spec_file(main_file='main.py', app_name='OZONParser', icon_path='logo.ico'):
    """Создает .spec файл"""
    
    # Проверяем наличие иконки
    if not os.path.exists(icon_path):
        print(f"⚠️  Иконка {icon_path} не найдена, создаю без иконки")
        icon_line = ""
    else:
        print(f"✅ Иконка найдена: {icon_path}")
        icon_line = f"    icon='{icon_path}',"
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# Auto-generated spec file for {app_name}

block_cipher = None

a = Analysis(
    ['{main_file}'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'selenium', 
        'undetected_chromedriver',
        'aiogram',
        'dotenv',
        'selenium_stealth'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Без консоли - красивый GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
{icon_line}
)
'''
    
    spec_filename = f'{app_name}.spec'
    
    with open(spec_filename, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"✅ Создан файл: {spec_filename}")
    print(f"🎯 Название приложения: {app_name}")
    print(f"🖼️  Консоль: Отключена (GUI режим)")
    return spec_filename

def build_exe(main_file='main.py', app_name='OZONParser', icon_path='logo.ico'):
    """Полный процесс создания .exe"""
    
    print("🔍 Создание .spec файла...")
    spec_file = create_spec_file(main_file, app_name, icon_path)
    
    if not spec_file:
        print("❌ Не удалось создать .spec файл")
        return False
    
    print(f"🚀 Сборка {app_name}.exe...")
    try:
        # Запускаем PyInstaller
        result = subprocess.run([
            'pyinstaller', 
            '--clean',  # Очищаем кеш
            spec_file
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {app_name}.exe успешно создан!")
            print("📁 Проверьте папку dist/")
            print("🎯 Консоль отключена - приложение запускается без черного окна")
            print("🖼️  Иконка установлена (если logo.ico найдена)")
            return True
        else:
            print("❌ Ошибка при сборке:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("❌ PyInstaller не найден. Установите: pip install pyinstaller")
        return False

if __name__ == "__main__":
    print("🛠️ Сборщик OZONParser.exe")
    print("=" * 50)
    
    # Основные параметры
    main_file = "main.py"
    app_name = "OZONParser"
    icon_path = "logo.ico"
    
    print(f"📄 Главный файл: {main_file}")
    print(f"🎯 Название: {app_name}.exe")
    print(f"🖼️  Консоль: Отключена")
    print(f"🎨 Иконка: {icon_path}")
    print()
    
    # Создаем .exe
    success = build_exe(main_file, app_name, icon_path)
    
    if success:
        print()
        print("🎉 Готово! OZONParser.exe создан успешно!")
        print("📁 Файл находится в папке dist/")
        print("✨ Приложение запускается без консоли")
        print("🚀 Можете запускать на любом компьютере!")
    else:
        print()
        print("❌ Возникли проблемы при создании .exe")
        print("💡 Проверьте зависимости и настройки")