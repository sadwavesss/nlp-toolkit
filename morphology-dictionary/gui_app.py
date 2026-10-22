import csv
import json
import os
from typing import Dict, List

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from dictionary_model import DictionaryEntry, build_dictionary
from nlp_tools import tokenize_russian_words
from text_io import load_text_from_file


class Lab1App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ЛР1 — Словарь (TXT/RTF)")
        self.geometry("980x640")
        self.minsize(860, 520)

        self._entries: Dict[str, DictionaryEntry] = {}
        self._filtered_keys: List[str] = []

        self._make_ui()

    def _make_ui(self) -> None:
        self._make_menu()

        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=8)

        ttk.Button(top, text="Открыть TXT/RTF", command=self.open_text_file).pack(side=tk.LEFT)
        ttk.Button(top, text="Анализ", command=self.analyze_text).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(top, text="Поиск:").pack(side=tk.LEFT, padx=(20, 6))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(top, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT)
        search_entry.bind("<KeyRelease>", lambda _e: self.apply_filter())

        ttk.Button(top, text="Сброс", command=self.clear_filter).pack(side=tk.LEFT, padx=(8, 0))

        mid = ttk.PanedWindow(self, orient=tk.VERTICAL)
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        text_frame = ttk.Labelframe(mid, text="Входной текст")
        dict_frame = ttk.Labelframe(mid, text="Словарь")
        mid.add(text_frame, weight=2)
        mid.add(dict_frame, weight=3)

        self.text_widget = tk.Text(text_frame, wrap=tk.WORD)
        self.text_widget.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        table_wrap = ttk.Frame(dict_frame)
        table_wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.tree = ttk.Treeview(
            table_wrap,
            columns=("wordform", "lexeme", "freq", "morph"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("wordform", text="Словоформа")
        self.tree.heading("lexeme", text="Лексема")
        self.tree.heading("freq", text="Частота")
        self.tree.heading("morph", text="Морфология (ввод вручную)")

        self.tree.column("wordform", width=170, anchor=tk.W)
        self.tree.column("lexeme", width=170, anchor=tk.W)
        self.tree.column("freq", width=80, anchor=tk.E)
        self.tree.column("morph", width=420, anchor=tk.W)

        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_wrap.rowconfigure(0, weight=1)
        table_wrap.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._on_double_click)

        editor = ttk.Frame(dict_frame)
        editor.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Label(editor, text="Морфология для выбранной словоформы:").pack(side=tk.LEFT)
        self.morph_var = tk.StringVar()
        morph_entry = ttk.Entry(editor, textvariable=self.morph_var)
        morph_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ttk.Button(editor, text="Применить", command=self.apply_morphology).pack(side=tk.LEFT)
        self.morph_entry = morph_entry

        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(self, textvariable=self.status_var, anchor=tk.W).pack(fill=tk.X, padx=10, pady=(0, 8))

    def _make_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Открыть TXT/RTF...", command=self.open_text_file)
        file_menu.add_command(label="Сохранить словарь (JSON)...", command=self.save_dictionary_json)
        file_menu.add_command(label="Загрузить словарь (JSON)...", command=self.load_dictionary_json)
        file_menu.add_command(label="Экспорт CSV...", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.destroy)
        menubar.add_cascade(label="Файл", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Справка", command=self.show_help)
        menubar.add_cascade(label="Справка", menu=help_menu)

        self.config(menu=menubar)

    def set_status(self, text: str) -> None:
        self.status_var.set(text)
        self.update_idletasks()

    def open_text_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Открыть текстовый документ",
            filetypes=[("TXT files", "*.txt"), ("RTF files", "*.rtf"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            text = load_text_from_file(path)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")
            return

        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert(tk.END, text)
        self.set_status(f"Открыт файл: {os.path.basename(path)}")

    def analyze_text(self) -> None:
        text = self.text_widget.get("1.0", tk.END)
        words = tokenize_russian_words(text)
        existing_morph = {k: v.morph for k, v in self._entries.items()}
        self._entries = build_dictionary(words, existing_morph=existing_morph)
        self.apply_filter()
        self.set_status(f"Найдено слов: {len(words)}, уникальных форм: {len(self._entries)}")

    def apply_filter(self) -> None:
        q = self.search_var.get().strip().lower()
        keys = sorted(self._entries.keys())
        if q:
            keys = [
                k
                for k in keys
                if q in k or q in self._entries[k].lexeme.lower() or q in self._entries[k].morph.lower()
            ]
        self._filtered_keys = keys
        self._refresh_tree()

    def clear_filter(self) -> None:
        self.search_var.set("")
        self.apply_filter()

    def _refresh_tree(self) -> None:
        for item in self.tree.get_children(""):
            self.tree.delete(item)
        for wf in self._filtered_keys:
            e = self._entries[wf]
            self.tree.insert("", tk.END, iid=wf, values=(e.wordform, e.lexeme, e.freq, e.morph))

    def _on_double_click(self, _event) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        wf = sel[0]
        e = self._entries.get(wf)
        if not e:
            return
        self.morph_var.set(e.morph)
        self.morph_entry.focus_set()
        self.morph_entry.selection_range(0, tk.END)

    def apply_morphology(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Морфология", "Выберите словоформу в таблице")
            return
        wf = sel[0]
        if wf not in self._entries:
            return
        self._entries[wf].morph = self.morph_var.get()
        self.tree.set(wf, "morph", self._entries[wf].morph)
        self.set_status(f"Морфология обновлена: {wf}")

    def save_dictionary_json(self) -> None:
        if not self._entries:
            messagebox.showinfo("Сохранение", "Словарь пуст. Сначала выполните анализ текста.")
            return
        path = filedialog.asksaveasfilename(
            title="Сохранить словарь",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return

        payload = {
            "version": 1,
            "entries": [
                {
                    "wordform": e.wordform,
                    "lexeme": e.lexeme,
                    "freq": e.freq,
                    "morph": e.morph,
                }
                for e in sorted(self._entries.values(), key=lambda x: x.wordform)
            ],
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")
            return
        self.set_status(f"Словарь сохранён: {os.path.basename(path)}")

    def load_dictionary_json(self) -> None:
        path = filedialog.askopenfilename(
            title="Загрузить словарь",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            entries = payload.get("entries", [])
            new_entries: Dict[str, DictionaryEntry] = {}
            for item in entries:
                wf = str(item.get("wordform", "")).strip().lower()
                if not wf:
                    continue
                lex = str(item.get("lexeme", wf))
                freq = int(item.get("freq", 0))
                morph = str(item.get("morph", ""))
                new_entries[wf] = DictionaryEntry(wordform=wf, lexeme=lex, freq=freq, morph=morph)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить: {e}")
            return

        self._entries = new_entries
        self.apply_filter()
        self.set_status(f"Словарь загружен: {os.path.basename(path)}")

    def export_csv(self) -> None:
        if not self._entries:
            messagebox.showinfo("Экспорт", "Словарь пуст. Сначала выполните анализ текста.")
            return
        path = filedialog.asksaveasfilename(
            title="Экспорт CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["wordform", "lexeme", "freq", "morph"])
                for e in sorted(self._entries.values(), key=lambda x: x.wordform):
                    w.writerow([e.wordform, e.lexeme, e.freq, e.morph])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать: {e}")
            return
        self.set_status(f"Экспортировано: {os.path.basename(path)}")

    def show_help(self) -> None:
        text = (
            "1) Откройте TXT или RTF через меню 'Файл' или кнопку.\n"
            "2) Нажмите 'Анализ' - будет построен словарь словоформ (в нижнем регистре) с частотами.\n"
            "   Токенизация выполняется через nltk, иначе через регулярное выражение.\n"
            "3) Для ввода морфологии: выберите строку, дважды щёлкните по ней, затем введите текст и нажмите 'Применить'.\n"
            "4) Поле 'Поиск' фильтрует по словоформе, лексеме и морфологии.\n"
            "5) Словарь можно сохранить/загрузить в JSON или экспортировать в CSV."
        )
        messagebox.showinfo("Справка", text)


def main() -> None:
    app = Lab1App()
    app.mainloop()
