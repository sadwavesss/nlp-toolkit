#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from web_app_simple import app

    print("Запуск корпусного менеджера...")
    print("Откройте в браузере: http://localhost:5000")
    print("Для остановки нажмите Ctrl+C")

    app.run(debug=True, host='0.0.0.0', port=5000)
    
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Установите зависимости:")
    print("pip install -r requirements.txt")
    input("Нажмите Enter для выхода...")

except Exception as e:
    print(f"Ошибка запуска: {e}")
    input("Нажмите Enter для выхода...")
