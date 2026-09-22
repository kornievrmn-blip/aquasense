#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AquaSense — трекер збереженої води.

Показує, скільки води ви зекономили сьогодні (кільцева діаграма),
дозволяє розрахувати економію для типових дій (чищення зубів,
миття посуду з вимкненим краном, коротший душ тощо) і зберігає
історію по днях у локальному файлі water_data.json поруч зі скриптом.

Запуск:  python3 aquasense.py
Потрібен лише стандартний tkinter (входить у більшість збірок Python).
"""

import json
import os
import datetime
import tkinter as tk
from tkinter import simpledialog, messagebox

# ----------------------------------------------------------------------
# Палітра та константи оформлення
# ----------------------------------------------------------------------
DEEPBLUE = "#065A82"
TEAL = "#1C7293"
MIDNIGHT = "#21295C"
OFFWHITE = "#F4F8FA"
WHITE = "#FFFFFF"
INK = "#1B2B34"
MUTED = "#7488A6"
CARD = "#FFFFFF"
RING_BG = "#DCE7EC"
DANGER = "#C0455A"

FONT_H1 = ("Calibri", 22, "bold")
FONT_H2 = ("Calibri", 14, "bold")
FONT_BODY = ("Calibri", 11)
FONT_BODY_B = ("Calibri", 11, "bold")
FONT_BIG = ("Calibri", 38, "bold")
FONT_SMALL = ("Calibri", 9)

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "water_data.json")
DAILY_GOAL_DEFAULT = 50  # літрів на день — орієнтовна мета

PRESETS = [
    {"name": "Чищення зубів\nіз закритим краном", "short": "Чищення зубів", "icon": "🦷", "rate": 6, "default_min": 0},
    {"name": "Миття посуду\nз вимкненим краном", "short": "Миття посуду", "icon": "🍽", "rate": 9, "default_min": 0},
    {"name": "Коротший душ", "short": "Коротший душ", "icon": "🚿", "rate": 10, "default_min": 0},
    {"name": "Полив рослин з відра\nзамість шланга", "short": "Полив рослин", "icon": "🪴", "rate": 4, "default_min": 0},
]


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def today_key():
    return datetime.date.today().isoformat()


def round_rect_points(x1, y1, x2, y2, r):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, bg, fg=WHITE, width=220, height=46,
                 radius=16, font=FONT_BODY_B, hover_bg=None, parent_bg=None):
        super().__init__(parent, width=width, height=height,
                          bg=parent_bg or parent["bg"], highlightthickness=0, bd=0)
        self.command = command
        self.bg = bg
        self.hover_bg = hover_bg or self._shade(bg, -14)
        self.fg = fg
        self.radius = radius
        self.w = width
        self.h = height
        self.text = text
        self.font = font
        self._render(self.bg)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda e: self._render(self.hover_bg))
        self.bind("<Leave>", lambda e: self._render(self.bg))
        self.configure(cursor="hand2")

    @staticmethod
    def _shade(hex_color, amount):
        hex_color = hex_color.lstrip("#")
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        r = max(0, min(255, r + amount))
        g = max(0, min(255, g + amount))
        b = max(0, min(255, b + amount))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _render(self, color):
        self.delete("all")
        pts = round_rect_points(1, 1, self.w - 1, self.h - 1, self.radius)
        self.create_polygon(pts, smooth=True, fill=color, outline=color)
        self.create_text(self.w / 2, self.h / 2, text=self.text, fill=self.fg, font=self.font)

    def _on_click(self, _event):
        if self.command:
            self.command()


class Card(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=CARD, highlightbackground="#E1E9ED",
                          highlightthickness=1, bd=0, **kwargs)


class AquaSenseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AquaSense — трекер збереженої води")
        self.geometry("480x800")
        self.minsize(420, 720)
        self.configure(bg=OFFWHITE)

        self.data = load_data()
        self.goal = DAILY_GOAL_DEFAULT

        footer = tk.Frame(self, bg=OFFWHITE)
        footer.pack(side="bottom", fill="x")
        tk.Label(footer, text="designed by chekunetz and claude",
                 font=("Calibri", 8), bg=OFFWHITE, fg="#B7C4CC").pack(pady=6)

        self.container = tk.Frame(self, bg=OFFWHITE)
        self.container.pack(side="top", fill="both", expand=True)

        self.current_view = None
        self.show_main()

    def today_total(self):
        return float(self.data.get(today_key(), 0))

    def add_liters(self, amount):
        if amount == 0:
            return
        key = today_key()
        new_val = round(self.data.get(key, 0) + amount, 1)
        if new_val <= 0:
            if key in self.data:
                del self.data[key]
        else:
            self.data[key] = new_val
        save_data(self.data)
        self.show_main()

    def reset_today(self):
        key = today_key()
        if key in self.data:
            del self.data[key]
            save_data(self.data)
            self.show_main()

    def _clear_container(self):
        if self.current_view is not None:
            self.current_view.destroy()
            self.current_view = None

    def show_main(self):
        self._clear_container()

        f = tk.Frame(self.container, bg=OFFWHITE)
        f.pack(fill="both", expand=True)
        self.current_view = f

        header = tk.Frame(f, bg=MIDNIGHT, height=150)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="💧 AquaSense", font=("Calibri", 20, "bold"),
                 bg=MIDNIGHT, fg=WHITE).pack(anchor="w", padx=24, pady=(22, 2))
        tk.Label(header, text="Ваш трекер збереженої води",
                 font=FONT_BODY, bg=MIDNIGHT, fg="#9FC6DA").pack(anchor="w", padx=24)

        body = tk.Frame(f, bg=OFFWHITE)
        body.pack(fill="both", expand=True, padx=24, pady=20)

        ring_card = Card(body)
        ring_card.pack(fill="x", pady=(0, 16))
        
        top_ring_frame = tk.Frame(ring_card, bg=CARD)
        top_ring_frame.pack(fill="x", padx=16, pady=(14, 0))
        tk.Label(top_ring_frame, text="ЗЕКОНОМЛЕНО СЬОГОДНІ", font=("Calibri", 10, "bold"),
                 bg=CARD, fg=TEAL).pack(side="left")
        
        reset_btn = tk.Label(top_ring_frame, text="🔄 Скинути", font=("Calibri", 9, "bold"),
                             bg=CARD, fg=DANGER, cursor="hand2")
        reset_btn.pack(side="right")
        reset_btn.bind("<Button-1>", lambda e: self.reset_today())

        today = self.today_total()
        canvas = tk.Canvas(ring_card, width=220, height=220, bg=CARD, highlightthickness=0)
        canvas.pack(pady=4)
        self._draw_ring(canvas, today, self.goal)

        goal_left = max(self.goal - today, 0)
        if today >= self.goal:
            status = f"🎉 Денну мету досягнуто! (ціль {self.goal:g} л)"
        else:
            status = f"Ще {goal_left:g} л до денної мети ({self.goal:g} л)"
        tk.Label(ring_card, text=status, font=FONT_BODY, bg=CARD, fg=MUTED).pack(pady=(4, 18))

        actions = tk.Frame(body, bg=OFFWHITE)
        actions.pack(fill="x", pady=(0, 16))
        RoundedButton(actions, "＋ Розрахувати економію", self.open_calculator,
                      bg=DEEPBLUE, width=432, height=48, parent_bg=OFFWHITE).pack(pady=(0, 10))

        row = tk.Frame(actions, bg=OFFWHITE)
        row.pack(fill="x")
        RoundedButton(row, "✎ Додати вручну", self.open_manual_add,
                      bg=TEAL, width=210, height=42, parent_bg=OFFWHITE).pack(side="left")
        RoundedButton(row, "📅 Історія", self.show_history,
                      bg=MIDNIGHT, width=210, height=42, parent_bg=OFFWHITE).pack(side="right")

        tk.Label(body, text="ШВИДКО ДОДАТИ", font=("Calibri", 10, "bold"),
                 bg=OFFWHITE, fg=MUTED).pack(anchor="w", pady=(4, 8))

        quick = tk.Frame(body, bg=OFFWHITE)
        quick.pack(fill="x")
        for preset in PRESETS[:2]:
            self._quick_chip(quick, preset)

    def _quick_chip(self, parent, preset):
        chip = Card(parent)
        chip.pack(side="left", expand=True, fill="both",
                   padx=(0, 10) if preset is PRESETS[0] else (0, 0))
        chip.configure(cursor="hand2")
        inner = tk.Frame(chip, bg=CARD)
        inner.pack(fill="both", expand=True, padx=10, pady=(14, 14))
        tk.Label(inner, text=preset["icon"], font=("Calibri", 16), bg=CARD).pack()
        tk.Label(inner, text=preset["short"], font=("Calibri", 10, "bold"), bg=CARD, fg=INK,
                 justify="center").pack(pady=(6, 0))

        def open_this(_e=None, p=preset):
            self.open_calculator(preselect=p)

        for widget in (chip, inner) + tuple(inner.winfo_children()):
            widget.bind("<Button-1>", open_this)

    def _draw_ring(self, canvas, value, goal):
        cx, cy, r, w = 110, 110, 88, 16
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=RING_BG, width=w)
        pct = 0 if goal <= 0 else min(value / goal, 1)
        if pct > 0:
            extent = -359.9 * pct if pct >= 1 else -360 * pct
            canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=90, extent=extent,
                               style="arc", outline=TEAL, width=w)
        canvas.create_text(cx, cy - 10, text=f"{value:g}", font=FONT_BIG, fill=DEEPBLUE)
        canvas.create_text(cx, cy + 26, text="літрів", font=FONT_BODY, fill=MUTED)

    def open_calculator(self, preselect=None):
        CalculatorDialog(self, preselect=preselect)

    def open_manual_add(self):
        value = simpledialog.askfloat(
            "Додати вручну", "Скільки літрів ви зекономили?",
            minvalue=-5000, maxvalue=5000, parent=self,
        )
        if value is not None:
            self.add_liters(value)

    def delete_day(self, date_str):
        if date_str in self.data:
            del self.data[date_str]
            save_data(self.data)
            self.show_history()

    def show_history(self):
        self._clear_container()

        f = tk.Frame(self.container, bg=OFFWHITE)
        f.pack(fill="both", expand=True)
        self.current_view = f

        header = tk.Frame(f, bg=MIDNIGHT, height=110)
        header.pack(fill="x")
        header.pack_propagate(False)
        top_row = tk.Frame(header, bg=MIDNIGHT)
        top_row.pack(fill="x", padx=16, pady=(18, 0))
        RoundedButton(top_row, "←", self.show_main, bg=TEAL, width=42, height=36,
                      radius=10, parent_bg=MIDNIGHT).pack(side="left")
        tk.Label(top_row, text="Історія збереження", font=("Calibri", 16, "bold"),
                 bg=MIDNIGHT, fg=WHITE).pack(side="left", padx=12)

        body = tk.Frame(f, bg=OFFWHITE)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        days_sorted = sorted(self.data.items(), key=lambda kv: kv[0], reverse=True)
        total = sum(self.data.values())

        stat_card = Card(body)
        stat_card.pack(fill="x", pady=(0, 14))
        tk.Label(stat_card, text=f"{total:g} л", font=("Cambria", 26, "bold"),
                 bg=CARD, fg=DEEPBLUE).pack(pady=(14, 0))
        tk.Label(stat_card, text="зекономлено всього за весь час", font=FONT_BODY,
                 bg=CARD, fg=MUTED).pack(pady=(0, 14))

        last7 = days_sorted[:7][::-1]
        if last7:
            chart_card = Card(body)
            chart_card.pack(fill="x", pady=(0, 14))
            tk.Label(chart_card, text="ОСТАННІ ДНІ", font=("Calibri", 10, "bold"),
                     bg=CARD, fg=TEAL).pack(anchor="w", padx=16, pady=(12, 4))
            chart = tk.Canvas(chart_card, height=140, bg=CARD, highlightthickness=0)
            chart.pack(fill="x", padx=16, pady=(0, 14))
            chart.update_idletasks()
            self.after(10, lambda: self._draw_bars(chart, last7))
        else:
            empty = Card(body)
            empty.pack(fill="x", pady=(0, 14))
            tk.Label(empty, text="Поки що немає записів.\nПочніть із розрахунку на головному екрані!",
                     font=FONT_BODY, bg=CARD, fg=MUTED, justify="center").pack(pady=24)

        if days_sorted:
            tk.Label(body, text="ВСІ ЗАПИСИ", font=("Calibri", 10, "bold"),
                     bg=OFFWHITE, fg=MUTED).pack(anchor="w", pady=(4, 8))
            list_wrap = tk.Frame(body, bg=OFFWHITE)
            list_wrap.pack(fill="both", expand=True)

            canvas_l = tk.Canvas(list_wrap, bg=OFFWHITE, highlightthickness=0)
            scrollbar = tk.Scrollbar(list_wrap, orient="vertical", command=canvas_l.yview)
            inner = tk.Frame(canvas_l, bg=OFFWHITE)
            inner.bind("<Configure>", lambda e: canvas_l.configure(scrollregion=canvas_l.bbox("all")))
            canvas_l.create_window((0, 0), window=inner, anchor="nw")
            canvas_l.configure(yscrollcommand=scrollbar.set)
            canvas_l.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            for date_str, liters in days_sorted:
                self._history_row(inner, date_str, liters)

    def _draw_bars(self, chart, days):
        chart.delete("all")
        w = max(chart.winfo_width(), 300)
        h = 140
        n = len(days)
        max_val = max((v for _, v in days), default=1) or 1
        bar_w = min(46, (w - 20) / max(n, 1) - 16)
        gap = (w - bar_w * n) / (n + 1)
        base_y = h - 34
        for i, (date_str, liters) in enumerate(days):
            x = gap + i * (bar_w + gap)
            bar_h = 0 if max_val == 0 else (liters / max_val) * 74
            y = base_y - bar_h
            chart.create_rectangle(x, base_y, x + bar_w, base_y + 2, fill=RING_BG, outline="")
            chart.create_rectangle(x, y, x + bar_w, base_y, fill=TEAL, outline="")
            chart.create_text(x + bar_w / 2, y - 10, text=f"{liters:g}", font=FONT_SMALL, fill=DEEPBLUE)
            label = datetime.date.fromisoformat(date_str).strftime("%d.%m")
            chart.create_text(x + bar_w / 2, base_y + 16, text=label, font=FONT_SMALL, fill=MUTED)

    def _history_row(self, parent, date_str, liters):
        row = Card(parent)
        row.pack(fill="x", pady=5)
        inner = tk.Frame(row, bg=CARD)
        inner.pack(fill="x", padx=14, pady=10)

        date_fmt = datetime.date.fromisoformat(date_str).strftime("%d.%m.%Y")
        weekday = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"][
            datetime.date.fromisoformat(date_str).weekday()
        ]
        
        left = tk.Frame(inner, bg=CARD)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=f"💧 {date_fmt}", font=FONT_BODY_B, bg=CARD, fg=INK).pack(anchor="w")
        tk.Label(left, text=weekday, font=FONT_SMALL, bg=CARD, fg=MUTED).pack(anchor="w")

        right_frame = tk.Frame(inner, bg=CARD)
        right_frame.pack(side="right")

        tk.Label(right_frame, text=f"{liters:g} л", font=("Calibri", 14, "bold"),
                 bg=CARD, fg=DEEPBLUE).pack(side="left", padx=(0, 12))

        del_btn = tk.Label(right_frame, text="✕", font=("Calibri", 12, "bold"),
                           bg=CARD, fg=DANGER, cursor="hand2")
        del_btn.pack(side="left")
        del_btn.bind("<Button-1>", lambda e, ds=date_str: self.delete_day(ds))


class CalculatorDialog(tk.Toplevel):
    def __init__(self, app: AquaSenseApp, preselect=None):
        super().__init__(app)
        self.app = app
        self.title("Розрахувати економію")
        self.geometry("380x570")
        self.configure(bg=OFFWHITE)
        self.resizable(False, False)
        self.transient(app)
        self.grab_set()

        self.selected = tk.IntVar(value=PRESETS.index(preselect) if preselect in PRESETS else 0)
        
        self.minutes_str = tk.StringVar(value="0")
        self.minutes_str.trace_add("write", lambda *args: self._refresh())

        self.preset_frames = []

        tk.Label(self, text="Скільки води ви зекономили?", font=FONT_H2,
                 bg=OFFWHITE, fg=MIDNIGHT).pack(pady=(18, 4), padx=20, anchor="w")
        tk.Label(self, text="Оберіть дію та вкажіть кількість хвилин\n(можна змінити кнопками або ввести своє число)",
                 font=FONT_BODY, bg=OFFWHITE, fg=MUTED, justify="left").pack(padx=20, anchor="w")

        options = tk.Frame(self, bg=OFFWHITE)
        options.pack(fill="x", padx=20, pady=10)
        for i, preset in enumerate(PRESETS):
            self._preset_row(options, i, preset)

        minutes_card = Card(self)
        minutes_card.pack(fill="x", padx=20, pady=(2, 8))
        tk.Label(minutes_card, text="Хвилин із закритим краном:", font=FONT_BODY_B,
                 bg=CARD, fg=INK).pack(anchor="w", padx=14, pady=(10, 2))

        ctrl = tk.Frame(minutes_card, bg=CARD)
        ctrl.pack(padx=14, pady=(0, 10))
        
        RoundedButton(ctrl, "−", lambda: self._step(-0.5), bg=TEAL, width=40, height=36,
                      radius=10, parent_bg=CARD).pack(side="left")
        
        self.minutes_entry = tk.Entry(ctrl, textvariable=self.minutes_str, font=("Cambria", 18, "bold"),
                                      fg=DEEPBLUE, bg="#F4F8FA", justify="center", width=6, relief="flat")
        self.minutes_entry.pack(side="left", padx=10, ipady=4)
        
        RoundedButton(ctrl, "＋", lambda: self._step(0.5), bg=TEAL, width=40, height=36,
                      radius=10, parent_bg=CARD).pack(side="left")

        self.result_label = tk.Label(self, text="", font=("Cambria", 16, "bold"),
                                      bg=OFFWHITE, fg=DEEPBLUE)
        self.result_label.pack(pady=(2, 8))

        RoundedButton(self, "Економити", self._confirm, bg=DEEPBLUE,
                      width=336, height=44, parent_bg=OFFWHITE).pack(pady=(0, 12))

        self._refresh()

    def _preset_row(self, parent, index, preset):
        row = Card(parent)
        row.pack(fill="x", pady=3)
        row.configure(cursor="hand2")
        inner = tk.Frame(row, bg=CARD)
        inner.pack(fill="x", padx=10, pady=6)
        tk.Label(inner, text=preset["icon"], font=("Calibri", 14), bg=CARD).pack(side="left")
        tk.Label(inner, text=preset["name"].replace("\n", " "), font=FONT_BODY, bg=CARD,
                 fg=INK, wraplength=240, justify="left").pack(side="left", padx=10)
        self.preset_frames.append((row, inner))

        def select(_e=None, i=index):
            self.selected.set(i)
            self.minutes_str.set("0")
            self._refresh()

        for w in (row, inner) + tuple(inner.winfo_children()):
            w.bind("<Button-1>", select)

    def _step(self, delta):
        try:
            curr = float(self.minutes_str.get())
        except ValueError:
            curr = 0.0
        new_val = max(0.0, round(curr + delta, 1))
        if new_val.is_integer():
            self.minutes_str.set(str(int(new_val)))
        else:
            self.minutes_str.set(str(new_val))

    def _refresh(self):
        idx = self.selected.get()
        for i, (row, inner) in enumerate(self.preset_frames):
            active = i == idx
            color = "#E7F1F5" if active else CARD
            row.configure(bg=color, highlightbackground=TEAL if active else "#E1E9ED",
                          highlightthickness=2 if active else 1)
            inner.configure(bg=color)
            for w in inner.winfo_children():
                w.configure(bg=color)

        try:
            mins = float(self.minutes_str.get())
        except ValueError:
            mins = 0.0

        rate = PRESETS[idx]["rate"]
        liters = round(rate * mins, 1)
        self.result_label.configure(text=f"≈ {liters:g} л заощаджено")

    def _confirm(self):
        try:
            mins = float(self.minutes_str.get())
        except ValueError:
            mins = 0.0
        if mins <= 0:
            self.destroy()
            return
        idx = self.selected.get()
        rate = PRESETS[idx]["rate"]
        liters = round(rate * mins, 1)
        self.app.add_liters(liters)
        self.destroy()


if __name__ == "__main__":
    app = AquaSenseApp()
    app.mainloop()