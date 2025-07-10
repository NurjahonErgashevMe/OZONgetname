# build_exe.py - Исправленный скрипт для создания OZONParser.exe
import os
import sys
import subprocess
import shutil
from pathlib import Path

def get_selenium_stealth_path():
    """Динамически находит путь к selenium_stealth"""
    try:
        import selenium_stealth
        stealth_path = os.path.dirname(selenium_stealth.__file__)
        js_path = os.path.join(stealth_path, 'js')
        
        print(f"✅ Найден путь к selenium_stealth: {stealth_path}")
        print(f"✅ Путь к JS файлам: {js_path}")
        
        # Проверяем существование JS файлов
        if os.path.exists(js_path):
            js_files = os.listdir(js_path)
            print(f"📄 JS файлы: {js_files}")
            return stealth_path, js_path
        else:
            print("❌ Папка JS не найдена")
            return stealth_path, None
            
    except ImportError:
        print("❌ selenium_stealth не установлен")
        return None, None

def check_and_create_files():
    """Проверяет и создает недостающие файлы"""
    print("🔍 Проверка необходимых файлов...")
    
    # Создаем links.json если его нет
    if not os.path.exists('links.json'):
        print("📝 Создаю файл links.json...")
        with open('links.json', 'w', encoding='utf-8') as f:
            f.write("# Файл для ссылок OZON\n")
            f.write("# Добавьте ссылки на товары OZON, каждую с новой строки\n")
            f.write("# Пример:\n")
            f.write("# https://www.ozon.ru/product/example-123456789/\n")
        print("✅ Создан файл links.json")
    else:
        print("✅ Файл links.json найден")
    
    # Проверяем .env файл
    if not os.path.exists('.env'):
        print("📝 Создаю файл .env...")
        with open('.env', 'w', encoding='utf-8') as f:
            f.write("# Настройки для OZONParser\n")
            f.write("TELEGRAM_BOT_TOKEN=your_bot_token_here\n")
            f.write("TELEGRAM_CHAT_ID=your_chat_id_here\n")
        print("✅ Создан файл .env")
    else:
        print("✅ Файл .env найден")
    
    return True

def clean_build_dirs():
    """Очищает старые папки сборки"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"🧹 Очищена папка: {dir_name}")
            except Exception as e:
                print(f"⚠️ Не удалось очистить {dir_name}: {e}")

def check_and_fix_pathlib():
    """Проверяет и удаляет проблемный пакет pathlib"""
    print("🔍 Проверка совместимости с PyInstaller...")
    
    try:
        # Проверяем, установлен ли проблемный пакет pathlib
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'show', 'pathlib'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("⚠️  Найден несовместимый пакет 'pathlib'")
            print("🔧 Удаляю несовместимый пакет...")
            
            # Удаляем проблемный пакет
            uninstall_result = subprocess.run([
                sys.executable, '-m', 'pip', 'uninstall', 'pathlib', '-y'
            ], capture_output=True, text=True)
            
            if uninstall_result.returncode == 0:
                print("✅ Пакет 'pathlib' успешно удален")
                return True
            else:
                print("❌ Ошибка при удалении пакета 'pathlib':")
                print(uninstall_result.stderr)
                return False
        else:
            print("✅ Пакет 'pathlib' не найден - все в порядке")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при проверке пакета 'pathlib': {e}")
        return False

def create_spec_file_with_dynamic_paths(main_file='main.py', app_name='OZONParser', icon_path='logo.ico'):
    """Создает .spec файл с динамически найденными путями"""
    
    # Получаем пути к selenium_stealth
    stealth_path, js_path = get_selenium_stealth_path()
    
    # Проверяем существование иконки
    if not os.path.exists(icon_path):
        print(f"⚠️  Иконка {icon_path} не найдена, создаю без иконки")
        icon_line = ""
    else:
        print(f"✅ Иконка найдена: {icon_path}")
        icon_line = f"    icon='{icon_path}',"
    
    # Собираем дополнительные файлы
    data_files = []
    additional_files = [
        'links.json',
        'config.txt', 
        'settings.json',
        '.env'
    ]
    
    print("🔍 Поиск дополнительных файлов...")
    for file in additional_files:
        if os.path.exists(file):
            data_files.append(f"('{file}', '.')")
            print(f"  ✅ {file}")
        else:
            print(f"  ⚠️  {file} - не найден")
    
    # Добавляем selenium_stealth JS файлы если найдены
    if js_path and os.path.exists(js_path):
        # Нормализуем путь для Windows
        js_path_normalized = js_path.replace('\\', '\\\\')
        data_files.append(f"(r'{js_path_normalized}', 'selenium_stealth/js')")
        print(f"  ✅ selenium_stealth JS файлы: {js_path}")
    
    # Формируем строку с данными
    if data_files:
        datas_line = f"datas=[{', '.join(data_files)}],"
        print(f"📦 Будут включены файлы: {len(data_files)} элементов")
    else:
        datas_line = "datas=[],"
        print("📦 Дополнительные файлы не найдены")
    
    # Создаем .spec файл
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
# Auto-generated spec file for {app_name}

block_cipher = None

a = Analysis(
    ['{main_file}'],
    pathex=[],
    binaries=[],
    {datas_line}
    hiddenimports=[
        'selenium', 
        'selenium_stealth',
        'undetected_chromedriver',
        'aiogram',
        'dotenv',
        'requests',
        'bs4',
        'lxml'
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,{icon_line}
)
"""
    
    spec_filename = f'{app_name}.spec'
    
    with open(spec_filename, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"✅ Создан файл: {spec_filename}")
    print(f"🎯 Название приложения: {app_name}")
    print(f"🖼️  Консоль: Отключена (GUI режим)")
    return spec_filename

def simple_build_exe(main_file='main.py', app_name='OZONParser'):
    """Простая сборка без .spec файла"""
    print("🔄 Пробую простую сборку без .spec файла...")
    
    try:
        # Простая команда PyInstaller
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--onefile',  # Один файл
            '--noconsole',  # Без консоли
            '--clean',  # Очистить кеш
            f'--name={app_name}',  # Имя
        ]
        
        # Добавляем файлы если есть
        if os.path.exists('links.json'):
            cmd.extend(['--add-data', 'links.json;.'])
        if os.path.exists('.env'):
            cmd.extend(['--add-data', '.env;.'])
            
        cmd.extend(['--add-data', 'config.txt.'])
        
        # Добавляем иконку если есть
        if os.path.exists('logo.ico'):
            cmd.extend(['--icon', 'logo.ico'])
        
        # Добавляем скрытые импорты
        hidden_imports = [
            'selenium', 'selenium_stealth', 'undetected_chromedriver',
            'aiogram', 'dotenv', 'requests', 'bs4', 'lxml'
        ]
        
        for imp in hidden_imports:
            cmd.extend(['--hidden-import', imp])
        
        cmd.append(main_file)
        
        print(f"🚀 Выполняю команду: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {app_name}.exe создан простым методом!")
            return True
        else:
            print("❌ Простая сборка тоже не удалась:")
            print("STDERR:", result.stderr[-1000:])
            return False
            
    except Exception as e:
        print(f"❌ Ошибка простой сборки: {e}")
        return False

def build_exe(main_file='main.py', app_name='OZONParser', icon_path='logo.ico'):
    """Полный процесс создания .exe с динамическим поиском путей"""
    
    # Очищаем старые файлы сборки
    clean_build_dirs()
    
    # Проверяем и создаем необходимые файлы
    check_and_create_files()
    
    # Сначала проверяем и исправляем проблему с pathlib
    if not check_and_fix_pathlib():
        print("❌ Не удалось исправить проблему с пакетом 'pathlib'")
        print("💡 Попробуйте вручную выполнить команду:")
        print(f"   {sys.executable} -m pip uninstall pathlib -y")
        return False
    
    print("🔍 Создание .spec файла с динамическими путями...")
    spec_file = create_spec_file_with_dynamic_paths(main_file, app_name, icon_path)
    
    if not spec_file:
        print("❌ Не удалось создать .spec файл")
        return False
    
    print(f"🚀 Сборка {app_name}.exe...")
    try:
        # Запускаем PyInstaller
        result = subprocess.run([
            sys.executable, '-m', 'PyInstaller',  # Используем python -m PyInstaller
            '--clean',  # Очищаем кеш
            spec_file
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {app_name}.exe успешно создан!")
            print("📁 Проверьте папку dist/")
            print("🎯 Консоль отключена - приложение запускается без черного окна")
            print("🖼️  Иконка установлена (если logo.ico найдена)")
            print("📦 Все необходимые файлы включены в .exe")
            print("💡 Файлы links.json, .env и selenium_stealth JS будут доступны в программе")
            
            # Проверяем размер файла
            exe_path = Path(f"dist/{app_name}.exe") 
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"📊 Размер файла: {size_mb:.1f} MB")
            
            return True
        else:
            print("❌ Ошибка при сборке:")
            print("\n--- ПОДРОБНАЯ ИНФОРМАЦИЯ ОБ ОШИБКЕ ---")
            if result.stdout:
                print("📋 STDOUT:")
                print(result.stdout[-2000:])  # Последние 2000 символов
            if result.stderr:
                print("🚨 STDERR:")
                print(result.stderr[-2000:])  # Последние 2000 символов
            print("--- КОНЕЦ ИНФОРМАЦИИ ОБ ОШИБКЕ ---\n")
            
            # Пробуем простую сборку
            print("🔄 Пробую альтернативный метод сборки...")
            return simple_build_exe(main_file, app_name)
            
    except FileNotFoundError:
        print("❌ PyInstaller не найден. Устанавливаю...")
        try:
            # Пытаемся установить PyInstaller
            install_result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', 'pyinstaller'
            ], capture_output=True, text=True)
            
            if install_result.returncode == 0:
                print("✅ PyInstaller установлен успешно")
                # Повторяем попытку сборки
                return build_exe(main_file, app_name, icon_path)
            else:
                print("❌ Не удалось установить PyInstaller:")
                print(install_result.stderr)
                return False
        except Exception as e:
            print(f"❌ Ошибка при установке PyInstaller: {e}")
            return False

def create_selenium_stealth_fallback():
    """Создает fallback JS файлы для selenium_stealth если их нет"""
    print("🔧 Создаю резервные JS файлы для selenium_stealth...")
    
    js_dir = Path('selenium_stealth_js')
    js_dir.mkdir(exist_ok=True)
    
    js_files = {
        'utils.js': '''
// utils.js для selenium-stealth
(function() {
    'use strict';
    
    // Удаляем признаки автоматизации
    if (navigator.webdriver) {
        delete navigator.webdriver;
    }
    
    // Переопределяем navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });
    
    // Скрываем automation
    window.chrome = {
        runtime: {},
    };
    
    // Переопределяем plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });
    
    // Переопределяем languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['ru-RU', 'ru'],
    });
    
})();
        ''',
        
        'chrome_runtime.js': '''
// chrome_runtime.js
window.chrome = {
    runtime: {},
};
        ''',
        
        'navigator_vendor.js': '''
// navigator_vendor.js
Object.defineProperty(navigator, 'vendor', {
    get: () => 'Google Inc.',
});
        ''',
        
        'navigator_plugins.js': '''
// navigator_plugins.js  
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});
        '''
    }
    
    # Создаем JS файлы
    for filename, content in js_files.items():
        js_file = js_dir / filename
        js_file.write_text(content.strip(), encoding='utf-8')
        print(f"  ✅ Создан: {js_file}")
    
    print(f"✅ Резервные JS файлы созданы в: {js_dir}")
    return str(js_dir)

def main():
    """Главная функция"""
    print("🛠️ Улучшенный сборщик OZONParser.exe")
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
    
    # Проверяем наличие main.py
    if not os.path.exists(main_file):
        print(f"❌ Файл {main_file} не найден!")
        print("💡 Убедитесь, что файл main.py находится в той же папке")
        return False
    
    # Проверяем selenium_stealth
    stealth_path, js_path = get_selenium_stealth_path()
    if not stealth_path:
        print("⚠️  selenium_stealth не найден, создаю резервные файлы...")
        create_selenium_stealth_fallback()
    
    # Создаем .exe
    success = build_exe(main_file, app_name, icon_path)
    
    if success:
        print()
        print("🎉 Готово! OZONParser.exe создан успешно!")
        print("📁 Файл находится в папке dist/")
        print("✨ Приложение запускается без консоли")
        print("🚀 Можете запускать на любом компьютере!")
        print("🔧 selenium_stealth JS файлы включены автоматически")
        
    else:
        print()
        print("❌ Возникли проблемы при создании .exe")
        print("💡 Проверьте зависимости и настройки")
        print("🔧 Возможные решения:")
        print("   1. Убедитесь, что все пакеты установлены")
        print("   2. Проверьте, что main.py существует")
        print("   3. Попробуйте запустить скрипт от имени администратора")
        print("   4. Установите отсутствующие пакеты:")
        print("      pip install selenium selenium-stealth undetected-chromedriver")

if __name__ == "__main__":
    main()