#!/usr/bin/env python3

from app import app

if __name__ == '__main__':
    print("=" * 55)
    print("СЕМАНТИКО-СИНТАКСИЧЕСКИЙ АНАЛИЗАТОР ТЕКСТА")
    print("Лабораторная работа №4")
    print("=" * 55)
    print("\nВеб-интерфейс: http://localhost:5002")
    print("Для остановки нажмите Ctrl+C\n")
    app.run(debug=True, host='0.0.0.0', port=5002)
