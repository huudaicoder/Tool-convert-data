"""Desktop utility to copy missing lookup IDs from *_OLD tables."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from datetime import date, datetime
from decimal import Decimal
from tkinter import messagebox, ttk

import dm_mapping_engine as engine


class MappingTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Đồng bộ danh mục theo ID")
        self.geometry("1450x780")
        self.minsize(1000, 600)
        self.events = queue.Queue()
        self.busy = False
        self.preview_rows = None
        self._build()
        self.after(120, self._poll)

    def _build(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("TButton", padding=(10, 5))

        outer = ttk.Frame(self, padding=8)
        outer.pack(fill="both", expand=True)
        connection = ttk.LabelFrame(outer, text="Kết nối DB hiện tại (Oracle)", padding=8)
        connection.pack(fill="x", pady=(0, 6))
        self.fields = {}
        fields = (("dsn", "DSN (host:port/service)", "", 30), ("user", "User", "", 16),
                  ("password", "Mật khẩu", "*", 16), ("schema", "Schema", "QLPN", 12))
        for index, (key, title, default, width) in enumerate(fields):
            ttk.Label(connection, text=title).grid(row=0, column=index * 2, sticky="w", padx=(0, 4))
            var = tk.StringVar(value=default)
            ttk.Entry(connection, textvariable=var, width=width,
                      show="*" if key == "password" else "").grid(
                row=0, column=index * 2 + 1, sticky="ew", padx=(0, 10))
            self.fields[key] = var
        for col in (1, 3, 5, 7):
            connection.columnconfigure(col, weight=1)

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 6))
        ttk.Button(actions, text="Kiểm tra kết nối", command=self._check_connection).pack(side="left")
        self.preview_button = ttk.Button(actions, text="Lấy preview ID thiếu", command=self._preview)
        self.preview_button.pack(side="left", padx=6)
        self.insert_button = ttk.Button(actions, text="Chèn tất cả ID thiếu", command=self._insert, state="disabled")
        self.insert_button.pack(side="left")
        self.status = ttk.Label(actions, text="Chưa preview.")
        self.status.pack(side="left", padx=10)

        self.summary = ttk.Label(outer, text="Chọn preview để xem các dòng sẽ được thêm.", font=("Segoe UI", 10, "bold"))
        self.summary.pack(anchor="w", pady=(2, 6))
        tabs = ttk.Notebook(outer)
        tabs.pack(fill="both", expand=True)
        self.trees = {}
        for label, cols in (("Dân tộc", ("ID", "Mã", "Tên", "Trạng thái", "Mô tả")),
                            ("Tôn giáo", ("ID", "Mã", "Tên", "Trạng thái", "Mô tả"))):
            page = ttk.Frame(tabs, padding=6)
            tabs.add(page, text=label)
            tree = ttk.Treeview(page, columns=cols, show="headings")
            widths = (75, 145, 240, 95, 300)
            for col, width in zip(cols, widths):
                tree.heading(col, text=col)
                tree.column(col, width=width, anchor="w")
            ybar = ttk.Scrollbar(page, orient="vertical", command=tree.yview)
            xbar = ttk.Scrollbar(page, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
            page.rowconfigure(0, weight=1)
            page.columnconfigure(0, weight=1)
            tree.grid(row=0, column=0, sticky="nsew")
            ybar.grid(row=0, column=1, sticky="ns")
            xbar.grid(row=1, column=0, sticky="ew")
            self.trees[label] = tree


    def _check_connection(self):
        if self.busy:
            return
        try:
            cfg = self._cfg()
        except ValueError as exc:
            messagebox.showwarning("Thiếu thông tin", str(exc))
            return
        self._start("Đang kiểm tra kết nối...", self._connection_worker, cfg)

    def _connection_worker(self, cfg):
        try:
            info = engine.check_connection(cfg)
            self.events.put(("connection", info))
        except Exception as exc:
            self.events.put(("error", f"Kiểm tra kết nối thất bại: {exc}"))

    def _cfg(self):
        cfg = {key: var.get().strip() for key, var in self.fields.items()}
        if not all(cfg[key] for key in ("dsn", "user", "password")):
            raise ValueError("Nhập DSN, user và mật khẩu trước.")
        if "/" not in cfg["dsn"]:
            raise ValueError("DSN cần dạng host:port/service.")
        cfg["schema"] = cfg["schema"] or "QLPN"
        return cfg

    def _preview(self):
        if self.busy:
            return
        try:
            cfg = self._cfg()
        except ValueError as exc:
            messagebox.showwarning("Thiếu thông tin", str(exc))
            return
        self._start("Đang kiểm tra hai cặp bảng...", self._preview_worker, cfg)

    def _preview_worker(self, cfg):
        try:
            info = engine.check_connection(cfg)
            rows = engine.preview(cfg)
            self.events.put(("preview", info, rows))
        except Exception as exc:
            self.events.put(("error", f"Không kiểm tra được schema/bảng: {exc}"))

    def _insert(self):
        if self.busy or self.preview_rows is None:
            return
        counts = {name: len(rows) for name, rows in self.preview_rows.items()}
        total = sum(counts.values())
        if not total:
            messagebox.showinfo("Không có dòng cần thêm", "Hai bảng hiện tại đã có đủ ID trong bảng *_OLD.")
            return
        prompt = (f"Sẽ chèn {total} dòng theo ID đang thiếu:\n"
                  f"• Dân tộc: {counts['Dân tộc']}\n• Tôn giáo: {counts['Tôn giáo']}\n\n"
                  "Dữ liệu và ID lấy nguyên từ bảng *_OLD. Các ID đã có sẽ không bị cập nhật. Tiếp tục?")
        if not messagebox.askyesno("Xác nhận ghi dữ liệu", prompt, icon="warning"):
            return
        try:
            cfg = self._cfg()
        except ValueError as exc:
            messagebox.showwarning("Thiếu thông tin", str(exc))
            return
        self._start("Đang chèn trong một transaction...", self._insert_worker, cfg)

    def _insert_worker(self, cfg):
        try:
            expected_ids = {name: [row[0] for row in rows]
                            for name, rows in self.preview_rows.items()}
            counts = engine.synchronize(cfg, expected_ids)
            try:
                rows = engine.preview(cfg)
                self.events.put(("inserted", counts, rows))
            except Exception as exc:
                self.events.put(("inserted_refresh_error", counts, str(exc)))
        except Exception as exc:
            self.events.put(("error", f"Đã rollback, không hoàn tất đồng bộ: {exc}"))

    def _start(self, status, target, cfg):
        self.busy = True
        self.preview_button.configure(state="disabled")
        self.insert_button.configure(state="disabled")
        self.status.configure(text=status)
        threading.Thread(target=target, args=(cfg,), daemon=True).start()

    @staticmethod
    def _display(value):
        if value is None:
            return ""
        if isinstance(value, (datetime, date)):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, Decimal):
            return format(value, "f")
        return str(value)

    def _show_rows(self, rows):
        for label, tree in self.trees.items():
            tree.delete(*tree.get_children())
            for row in rows[label]:
                # Show the business columns; audit values are copied as well.
                tree.insert("", "end", values=tuple(self._display(v) for v in row[:5]))
        counts = {name: len(values) for name, values in rows.items()}
        total = sum(counts.values())
        self.summary.configure(text=(f"Còn thiếu {total} ID  •  Dân tộc: {counts['Dân tộc']}  •  "
                                     f"Tôn giáo: {counts['Tôn giáo']}"))
        self.preview_rows = rows
        self.insert_button.configure(state="normal" if total else "disabled")

    def _poll(self):
        while not self.events.empty():
            event = self.events.get()
            self.busy = False
            self.preview_button.configure(state="normal")
            if event[0] == "connection":
                _, info = event
                self.status.configure(text=f"Kết nối OK • DB {info[0]} • Schema {info[1]} • Giờ DB {info[2]}")
            elif event[0] == "preview":
                _, info, rows = event
                self._show_rows(rows)
                self.status.configure(text=f"Đã preview • DB {info[0]} • Schema {info[1]} • Giờ DB {info[2]}")
            elif event[0] == "inserted":
                _, counts, rows = event
                self._show_rows(rows)
                self.status.configure(text=(f"Đã commit • Dân tộc: {counts['Dân tộc']} • "
                                            f"Tôn giáo: {counts['Tôn giáo']} • Còn thiếu: {sum(map(len, rows.values()))}"))
                messagebox.showinfo("Đồng bộ hoàn tất", self.status.cget("text"))
            elif event[0] == "inserted_refresh_error":
                _, counts, error = event
                self.preview_rows = None
                self.insert_button.configure(state="disabled")
                self.status.configure(text=(f"Đã commit • Dân tộc: {counts['Dân tộc']} • "
                                            f"Tôn giáo: {counts['Tôn giáo']} • Chưa tải lại được preview"))
                messagebox.showwarning("Đã ghi dữ liệu", self.status.cget("text") + f"\n\nLỗi tải lại: {error}")
            elif event[0] == "error":
                self.status.configure(text="Có lỗi")
                messagebox.showerror("Không hoàn tất được", event[1])
        self.after(120, self._poll)


if __name__ == "__main__":
    MappingTool().mainloop()
