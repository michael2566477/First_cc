"""
Pomodoro Timer - 桌面番茄钟
A modern desktop Pomodoro timer with polished UI.
"""

import tkinter as tk
import json
import winsound
import ctypes
from datetime import datetime
import math

# ── Constants ──────────────────────────────────────────────────
CONFIG_FILE = "pomodoro_config.json"
STATS_FILE = "pomodoro_stats.json"

DEFAULT_CONFIG = {
    "work_time": 25 * 60,
    "break_time": 5 * 60,
    "long_break_time": 15 * 60,
    "pomodoros_before_long_break": 4,
    "sound_enabled": True,
}

# ── Theme ──────────────────────────────────────────────────────
class Theme:
    # Base
    bg = "#0b0b1a"
    surface = "#14142a"
    surface_light = "#1c1c38"
    border = "#28284a"
    border_light = "#383860"

    # Mode accents
    work = "#ff6b6b"
    work_dark = "#d95252"
    break_c = "#51cf66"
    break_dark = "#3db84e"
    long_break = "#4dabf7"
    long_break_dark = "#339af0"

    # Text
    text = "#eeecf4"
    text_sec = "#9290aa"
    text_muted = "#55556e"

    # Buttons
    btn_bg = "#252548"
    btn_hover = "#32325a"

    # Glow (no alpha — tkinter on Windows doesn't support RGBA hex)
    glow_work = "#ff8888"
    glow_break = "#7ed88a"
    glow_long = "#7cc2fa"


# ── Application ────────────────────────────────────────────────
class PomodoroApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("番茄钟")
        self.root.geometry("420x580")
        self.root.configure(bg=Theme.bg)
        self.root.resizable(False, False)
        self.config = self.load_config()
        self.stats = self.load_stats()

        self.state = "idle"
        self.mode = "work"
        self.time_remaining = self.config["work_time"]
        self.session_count = 0
        self._timer_id = None

        self.center_window()
        self.build_ui()
        self.bind_shortcuts()
        self.update_display()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # fade in after a short delay
        self.root.after(50, lambda: self.fade_in(self.root, 0))
        self.root.mainloop()

    # ── Accent properties ─────────────────────────────────────
    @property
    def accent(self):
        return {"work": Theme.work, "break": Theme.break_c,
                "long_break": Theme.long_break}.get(self.mode, Theme.work)

    @property
    def accent_dark(self):
        return {"work": Theme.work_dark, "break": Theme.break_dark,
                "long_break": Theme.long_break_dark}.get(self.mode, Theme.work_dark)

    @property
    def glow(self):
        return {"work": Theme.glow_work, "break": Theme.glow_break,
                "long_break": Theme.glow_long}.get(self.mode, Theme.glow_work)

    @property
    def duration(self):
        return {"work": self.config["work_time"],
                "break": self.config["break_time"],
                "long_break": self.config["long_break_time"]}.get(self.mode, 25 * 60)

    @property
    def mode_label(self):
        return {"work": "FOCUS", "break": "BREAK",
                "long_break": "LONG BREAK"}.get(self.mode, "FOCUS")

    # ── UI Build ──────────────────────────────────────────────
    def build_ui(self):
        # Background container with subtle border
        outer = tk.Frame(self.root, bg=Theme.border)
        outer.pack(fill="both", expand=True, padx=0, pady=0)

        main = tk.Frame(outer, bg=Theme.bg)
        main.pack(fill="both", expand=True, padx=1, pady=1)

        # ── Header ──
        hdr = tk.Frame(main, bg=self.accent, height=80)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="番茄钟", bg=self.accent, fg="white",
                 font=("Segoe UI", 18, "bold")).place(relx=0.5, rely=0.4, anchor="center")
        self.subtitle = tk.Label(hdr, text=self.mode_label,
                                 bg=self.accent, fg="#e0dce8",
                                 font=("Segoe UI", 9))
        self.subtitle.place(relx=0.5, rely=0.75, anchor="center")

        # ── Timer Canvas ──
        self.csize = 260
        self.canvas = tk.Canvas(main, width=self.csize, height=self.csize,
                                bg=Theme.bg, highlightthickness=0)
        self.canvas.pack(pady=(30, 0))
        self.draw_canvas()

        # ── Controls ──
        ctrl = tk.Frame(main, bg=Theme.bg)
        ctrl.pack(pady=(24, 0))

        self.btn_start = self._btn("开始 Start", self.cmd_start, filled=True)
        self.btn_start.pack(side="left", padx=5)
        self.btn_pause = self._btn("暂停", self.cmd_pause, filled=False)
        self.btn_pause.pack(side="left", padx=5)
        self.btn_reset = self._btn("重置", self.cmd_reset, filled=False)
        self.btn_reset.pack(side="left", padx=5)
        self.btn_pause.config(state="disabled")

        # ── Stats ──
        sc = tk.Frame(main, bg=Theme.surface, highlightbackground=Theme.border,
                      highlightthickness=1)
        sc.pack(pady=(24, 0), padx=40, fill="x")

        inner = tk.Frame(sc, bg=Theme.surface)
        inner.pack(pady=(14, 10), padx=20)

        self.stat_today = tk.Label(inner, text="", bg=Theme.surface,
                                   fg=Theme.text, font=("Segoe UI", 14, "bold"))
        self.stat_today.pack()
        self.stat_label = tk.Label(inner, text="今日完成番茄", bg=Theme.surface,
                                   fg=Theme.text_muted, font=("Segoe UI", 9))
        self.stat_label.pack()

        self.stat_total = tk.Label(inner, text="", bg=Theme.surface,
                                   fg=Theme.text_sec, font=("Segoe UI", 10))
        self.stat_total.pack(pady=(6, 0))

        # ── Settings ──
        settings_btn = tk.Label(main, text="设  置", bg=Theme.bg,
                                fg=Theme.text_muted, font=("Segoe UI", 9),
                                cursor="hand2")
        settings_btn.pack(pady=(14, 0))
        settings_btn.bind("<Button-1>", lambda e: self.cmd_settings())
        settings_btn.bind("<Enter>", lambda e: settings_btn.config(fg=Theme.text))
        settings_btn.bind("<Leave>", lambda e: settings_btn.config(fg=Theme.text_muted))

        self._update_stats()

    # ── Canvas ─────────────────────────────────────────────────
    def draw_canvas(self):
        self.canvas.delete("all")
        cx = cy = self.csize // 2
        r = 94

        # Outer glow
        self.canvas.create_oval(cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14,
                                outline=self.glow, width=16, tags="glow")
        # Background track
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                outline=Theme.surface_light, width=8, tags="track")
        # Progress arc
        self.prog = self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=0, outline=self.accent, width=8,
            style="arc", tags="prog"
        )
        # Time display
        self.txt_time = self.canvas.create_text(
            cx, cy - 10, text="25:00", fill=Theme.text,
            font=("Segoe UI", 46, "bold"), tags="time"
        )
        self.txt_mode = self.canvas.create_text(
            cx, cy + 38, text=self.mode_label, fill=Theme.text_sec,
            font=("Segoe UI", 10, "bold"), tags="mode"
        )

    def redraw(self):
        cx = cy = self.csize // 2
        r = 94
        total = self.duration
        progress = 1.0 - (self.time_remaining / total) if total > 0 else 0
        extent = 360 * progress

        self.canvas.itemconfig("glow", outline=self.glow)
        self.canvas.itemconfig("prog", outline=self.accent, extent=extent)

        mm, ss = divmod(self.time_remaining, 60)
        self.canvas.itemconfig(self.txt_time, text=f"{mm:02d}:{ss:02d}")
        self.canvas.itemconfig(self.txt_mode, text=self.mode_label)

        self.root.title(f"番茄钟 {mm:02d}:{ss:02d}")

    # ── Button factory ─────────────────────────────────────────
    def _btn(self, text, cmd, filled=False):
        if filled:
            bg, fg, abg, afg = self.accent, "white", self.accent_dark, "white"
        else:
            bg, fg, abg, afg = Theme.btn_bg, Theme.text, Theme.btn_hover, Theme.text

        btn = tk.Button(self.root, text=text, command=cmd,
                        bg=bg, fg=fg, font=("Segoe UI", 11, "bold"),
                        relief="flat", padx=18, pady=8, cursor="hand2",
                        activebackground=abg, activeforeground=afg)

        if not filled:
            btn.bind("<Enter>", lambda e: self._hover(btn, cmd, bg, fg, True))
            btn.bind("<Leave>", lambda e: self._hover(btn, cmd, bg, fg, False))
        else:
            btn.bind("<Enter>", lambda e: self._hover(btn, cmd, bg, fg, True))
            btn.bind("<Leave>", lambda e: self._hover(btn, cmd, bg, fg, False))
        return btn

    def _hover(self, btn, cmd, bg, fg, enter):
        if str(btn.cget("state")) == "disabled":
            return
        if enter:
            btn.config(bg=bg if bg == self.accent else Theme.btn_hover)
        else:
            btn.config(bg=bg)

    # ── Timer Logic ────────────────────────────────────────────
    def cmd_start(self):
        if self.state == "running":
            return
        if self.state == "idle":
            self.time_remaining = self.duration
        self.state = "running"
        self.btn_start.config(state="disabled")
        self.btn_pause.config(state="normal", text="暂停",
                              bg=Theme.btn_bg, fg=Theme.text,
                              command=self.cmd_pause)
        self.tick()

    def cmd_pause(self):
        if self.state != "running":
            return
        self.state = "paused"
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None
        self.btn_start.config(state="normal", text="继续",
                              bg=self.accent, fg="white",
                              command=self.cmd_start)
        self.btn_pause.config(state="disabled")

    def cmd_reset(self):
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None
        self.state = "idle"
        self.time_remaining = self.duration
        self.btn_start.config(state="normal", text="开始 Start",
                              bg=self.accent, fg="white",
                              command=self.cmd_start)
        self.btn_pause.config(state="disabled", text="暂停")
        self.redraw()

    def tick(self):
        if self.state != "running":
            return
        if self.time_remaining <= 0:
            self.timer_complete()
            return
        self.time_remaining -= 1
        self.redraw()
        self._timer_id = self.root.after(1000, self.tick)

    def timer_complete(self):
        self.state = "idle"
        self.btn_start.config(state="normal", text="开始 Start",
                              bg=self.accent, fg="white",
                              command=self.cmd_start)
        self.btn_pause.config(state="disabled")

        if self.config["sound_enabled"]:
            self._beep()
        self._flash()

        if self.mode == "work":
            self.session_count += 1
            nxt = "long_break" if self.session_count % self.config["pomodoros_before_long_break"] == 0 else "break"
            self._save_session()
        else:
            nxt = "work"

        self._dialog(nxt)

    # ── Completion Dialog ──────────────────────────────────────
    def _dialog(self, nxt):
        top = tk.Toplevel(self.root)
        top.title("")
        top.configure(bg=Theme.surface)
        top.overrideredirect(True)
        top.attributes("-topmost", True)

        w, h = 300, 180
        cx = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        cy = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        top.geometry(f"{w}x{h}+{cx}+{cy}")

        card = tk.Frame(top, bg=Theme.surface, highlightbackground=Theme.border,
                        highlightthickness=1)
        card.pack(fill="both", expand=True)

        icon = tk.Label(card, text="完成", bg=Theme.surface,
                        fg=self.accent, font=("Segoe UI", 18, "bold"))
        icon.pack(pady=(24, 4))

        msg = "工作完成，休息一下吧。" if self.mode == "work" else "休息结束，继续工作。"
        tk.Label(card, text=msg, bg=Theme.surface, fg=Theme.text_sec,
                 font=("Segoe UI", 11)).pack(pady=(0, 16))

        nxt_accent = {"work": Theme.work, "break": Theme.break_c,
                       "long_break": Theme.long_break}.get(nxt, Theme.work)

        def proceed():
            top.destroy()
            self.switch_mode(nxt)
            self.cmd_start()

        btn = tk.Button(card, text=f"开始" + {"work": "工作", "break": "休息",
                                               "long_break": "长休息"}.get(nxt, ""),
                        command=proceed,
                        bg=nxt_accent, fg="white",
                        font=("Segoe UI", 12, "bold"),
                        relief="flat", padx=28, pady=8, cursor="hand2")
        btn.pack()

        top.attributes("-alpha", 0)
        self.fade_in(top, 0)

    @staticmethod
    def fade_in(win, alpha):
        a = min(alpha + 0.1, 1.0)
        win.attributes("-alpha", a)
        if a < 1.0:
            win.after(16, lambda: PomodoroApp.fade_in(win, a))

    # ── Display sync ──────────────────────────────────────────
    def update_display(self):
        self._sync_header()
        self.redraw()
        self._update_stats()

    def _sync_header(self):
        hdr = self.root.winfo_children()[0].winfo_children()[0]  # main frame > header
        hdr.config(bg=self.accent)
        for w in hdr.winfo_children():
            w.config(bg=self.accent)

    # ── Stats ─────────────────────────────────────────────────
    def _update_stats(self):
        today = datetime.now().strftime("%Y-%m-%d")
        cnt = self.stats.get(today, 0)
        self.stat_today.config(text=f"{cnt}")
        self.stat_total.config(text=f"累计专注 {cnt * 25} 分钟 / 今日")

    # ── Mode Switching ────────────────────────────────────────
    def switch_mode(self, mode):
        if self.state == "running":
            self.cmd_pause()
        self.mode = mode
        self.time_remaining = self.duration
        self._sync_header()
        self.cmd_reset()

    # ── Shortcuts ─────────────────────────────────────────────
    def bind_shortcuts(self):
        self.root.bind("<space>", lambda e: self.cmd_start()
                       if self.state in ("idle", "paused") else self.cmd_pause())
        self.root.bind("<Escape>", lambda e: self.cmd_reset())
        self.root.bind("<r>", lambda e: self.cmd_reset())

    # ── System Helpers ────────────────────────────────────────
    @staticmethod
    def _beep():
        try:
            for _ in range(2):
                winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass

    @staticmethod
    def _flash():
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            ctypes.windll.user32.FlashWindow(hwnd, True)
        except Exception:
            pass

    def center_window(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"420x580+{(sw - 420) // 2}+{(sh - 580) // 2}")

    # ── Settings Dialog ───────────────────────────────────────
    def cmd_settings(self):
        win = tk.Toplevel(self.root)
        win.title("设置")
        win.configure(bg=Theme.surface)
        win.geometry("340x400")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        cx = self.root.winfo_x() + (self.root.winfo_width() - 340) // 2
        cy = self.root.winfo_y() + (self.root.winfo_height() - 400) // 2
        win.geometry(f"+{cx}+{cy}")

        sections = [
            ("work_time", "工作时长 (分钟)", 25),
            ("break_time", "短休息时长 (分钟)", 5),
            ("long_break_time", "长休息时长 (分钟)", 15),
            ("pomodoros_before_long_break", "长休息间隔 (番茄数)", 4),
        ]

        entries = {}
        tk.Label(win, text="计时设置", bg=Theme.surface, fg=Theme.text,
                 font=("Segoe UI", 13, "bold")).pack(pady=(20, 8), padx=30, anchor="w")
        tk.Frame(win, bg=Theme.border, height=1).pack(fill="x", padx=30)

        for k, label, default in sections:
            row = tk.Frame(win, bg=Theme.surface)
            row.pack(fill="x", padx=30, pady=(12, 0))
            tk.Label(row, text=label, bg=Theme.surface, fg=Theme.text_sec,
                     font=("Segoe UI", 10)).pack(side="left")
            var = tk.StringVar(value=str(self.config.get(k, default) // 60))
            entries[k] = var
            tk.Entry(row, textvariable=var, width=5, justify="center",
                     bg=Theme.surface_light, fg=Theme.text, relief="flat",
                     font=("Segoe UI", 10), insertbackground=Theme.text,
                     bd=6).pack(side="right")

        sf = tk.Frame(win, bg=Theme.surface)
        sf.pack(fill="x", padx=30, pady=(18, 0))
        tk.Label(sf, text="声音提示", bg=Theme.surface, fg=Theme.text_sec,
                 font=("Segoe UI", 10)).pack(side="left")
        sv = tk.BooleanVar(value=self.config.get("sound_enabled", True))
        tk.Checkbutton(sf, variable=sv, bg=Theme.surface,
                       selectcolor=Theme.surface_light,
                       activebackground=Theme.surface).pack(side="right")

        def save():
            for k, v in entries.items():
                try:
                    self.config[k] = max(1, int(v.get())) * 60
                except ValueError:
                    pass
            self.config["sound_enabled"] = sv.get()
            self.save_config()
            self.cmd_reset()
            win.destroy()

        tk.Button(win, text="保存", command=save,
                  bg=self.accent, fg="white",
                  font=("Segoe UI", 12, "bold"),
                  relief="flat", padx=28, pady=8,
                  cursor="hand2").pack(pady=(20, 0))

        tk.Button(win, text="取消", command=win.destroy,
                  bg=Theme.btn_bg, fg=Theme.text_sec,
                  font=("Segoe UI", 10),
                  relief="flat", padx=20, pady=4,
                  cursor="hand2").pack(pady=(8, 0))

    # ── Persistence ──────────────────────────────────────────
    def load_config(self):
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
                for k in DEFAULT_CONFIG:
                    cfg.setdefault(k, DEFAULT_CONFIG[k])
                return cfg
        except (FileNotFoundError, json.JSONDecodeError):
            return dict(DEFAULT_CONFIG)

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def load_stats(self):
        try:
            with open(STATS_FILE) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_stats(self):
        try:
            with open(STATS_FILE, "w") as f:
                json.dump(self.stats, f, indent=2)
        except Exception:
            pass

    def _save_session(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.stats[today] = self.stats.get(today, 0) + 1
        self.save_stats()
        self._update_stats()

    def on_close(self):
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
        self.save_config()
        self.save_stats()
        self.root.destroy()


# ── Entry Point ────────────────────────────────────────────────
if __name__ == "__main__":
    app = PomodoroApp()
