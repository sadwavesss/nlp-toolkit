#!/usr/bin/env python3

from app import app

if __name__ == '__main__':
    print("=" * 50)
    print("СИНТАКСИЧЕСКИЙ АНАЛИЗАТОР ТЕКСТА")
    print("Лабораторная работа №3")
    print("=" * 50)
    print("\nВеб-интерфейс: http://localhost:5001")
    print("Для остановки нажмите Ctrl+C\n")
    app.run(debug=True, host='0.0.0.0', port=5001)
