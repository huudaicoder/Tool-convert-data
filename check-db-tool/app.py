"""Standalone C10 database conversion checker."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from types import SimpleNamespace

import engine
import mapping as M
from report import write_report

APP_TITLE = "Kiểm soát chuyển đổi dữ liệu C10"
GROUP_LABELS = {"LAI_LICH": "Thông tin lai lịch", "DIEN_BIEN": "Thông tin diễn biến", "KET_THUC": "Thông tin kết thúc"}
MENU_ORDER = {
    "LAI_LICH": ["LL01", "LL03", "LL04", "LL05", "LL02", "LL12", "LL06", "LL07", "LL08", "LL09", "LL10", "LL11"],
    "DIEN_BIEN": ["DB00", "DB01", "DB02", "DB03", "DB04", "DB05", "DB06", "DB07", "DB08", "DB09", "DB10", "DB11", "DB12", "DB13", "DB14", "DB15", "DB16", "DB17"],
    "KET_THUC": ["KT07", "KT01", "KT02", "KT06", "KT03", "KT04", "KT05"],
}
MENU_NAMES = {
    "LL01": "Lai lịch phạm nhân", "LL03": "Thi hành án", "LL04": "Thông tin tiền án", "LL05": "Thông tin tiền sự",
    "LL02": "Hành vi phạm tội", "LL12": "Trách nhiệm dân sự, HPBS", "LL06": "Bản án khác",
    "LL07": "Người thân thích", "LL08": "Con theo mẹ vào trại", "LL09": "Nhận dạng", "LL10": "Ma túy", "LL11": "Phân đội",
    "DB00": "Xếp loại", "DB01": "Giảm thời hạn", "DB02": "Phân loại", "DB03": "Chữa bệnh bắt buộc",
    "DB04": "Thông tin sức khỏe", "DB05": "Phạm tội mới", "DB06": "Ân giảm", "DB07": "Tăng giảm hình phạt",
    "DB08": "Khen thưởng", "DB09": "Kỷ luật", "DB10": "Giam riêng", "DB11": "Trốn trại", "DB12": "Trích xuất",
    "DB13": "Tạm đình chỉ", "DB14": "Hoãn thi hành án", "DB15": "Miễn hình phạt", "DB16": "Hủy án",
    "DB17": "Tiền công lao động sản xuất",
    "KT07": "Nộp lưu", "KT01": "Ra trại", "KT02": "Chết", "KT06": "Chuyển trại",
    "KT03": "Tha có điều kiện", "KT04": "Đặc xá", "KT05": "Chuyển giao",
}


def menu_prefix(code):
    if code.startswith("LL11b"):
        return "LL11"
    if code.startswith("LL06b"):
        return "LL06"
    if code.startswith("DB17b"):
        return "DB17"
    return code[:4]


def all_datasets():
    rows = list(M.SCREENS)
    # Receipt matching and legacy category mapping are being resolved from the application code.
    rows.append({"code": "LL12_BienLai", "name": "Danh sách biên lai (qua khoản TNDS/HPBS)",
                 "group": "LAI_LICH", "old_table": "PN_HPBS_THUC_HIEN", "new_table": "PN_BIENLAIES",
                 "unmapped": True})
    return rows


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        window_w = min(1380, max(1000, int(screen_w * 0.92)))
        window_h = min(850, max(500, screen_h - 100))
        self.geometry(f"{window_w}x{window_h}")
        self.minsize(900, 500)
        self.configure(bg="#f3f6fa")
        self.events = queue.Queue()
        self.busy = False
        self.cancel_event = threading.Event()
        self.datasets = all_datasets()
        self.menu_datasets = self._add_missing_menu_datasets()
        self.by_code = {s["code"]: s for s in self.menu_datasets}
        self.selected = {s["code"] for s in self.datasets if not s.get("unmapped")}
        self.result = None
        self.summary_rows = []
        self.selection_options = {}
        self.result_options = {}
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
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)
        conn = ttk.LabelFrame(outer, text="Kết nối hai CSDL Oracle", padding=8)
        conn.pack(fill="x", pady=(0, 8))
        self.fields = {side: {} for side in ("old", "new")}
        for col, side, label in ((0, "old", "DB CŨ"), (1, "new", "DB MỚI")):
            box = ttk.LabelFrame(conn, text=label, padding=8)
            box.grid(row=0, column=col, sticky="nsew", padx=5)
            conn.columnconfigure(col, weight=1)
            for row, (key, title, secret) in enumerate((("dsn", "DSN (host:port/service)", False), ("user", "User", False), ("password", "Mật khẩu", True), ("schema", "Schema (tùy chọn)", False))):
                ttk.Label(box, text=title).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
                var = tk.StringVar()
                ent = ttk.Entry(box, textvariable=var, show="*" if secret else "")
                ent.grid(row=row, column=1, sticky="ew", pady=3)
                box.columnconfigure(1, weight=1)
                self.fields[side][key] = var
            ttk.Button(box, text="Kiểm tra kết nối", command=lambda s=side: self._test_connection(s)).grid(row=4, column=1, sticky="e", pady=(6, 0))

        output_bar = ttk.LabelFrame(outer, text="File Excel xuất ra", padding=(8, 5))
        output_bar.pack(fill="x", pady=(0, 6))
        path_row = ttk.Frame(output_bar)
        path_row.pack(fill="x")
        ttk.Label(path_row, text="Đường dẫn").pack(side="left")
        self.out_var = tk.StringVar(value=str(Path.home() / "Documents" / "Bao_cao_doi_soat_C10.xlsx"))
        ttk.Entry(path_row, textvariable=self.out_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(path_row, text="Chọn nơi lưu...", command=self._pick_output).pack(side="left")
        action_row = ttk.Frame(output_bar)
        action_row.pack(fill="x", pady=(5, 0))
        self.progress = ttk.Progressbar(action_row, mode="determinate", length=180)
        self.progress.pack(side="left", padx=(0, 8))
        self.progress_label = ttk.Label(action_row, text="Sẵn sàng")
        self.progress_label.pack(side="left", fill="x", expand=True)
        self.run_button = ttk.Button(action_row, text="Chạy đối soát", command=self._run)
        self.run_button.pack(side="right", padx=(8, 0), ipadx=12)
        self.cancel_button = ttk.Button(action_row, text="Hủy", command=self.cancel_event.set, state="disabled")
        self.cancel_button.pack(side="right")

        body = ttk.Panedwindow(outer, orient="horizontal")
        body.pack(fill="both", expand=True, pady=(0, 8))
        left = ttk.LabelFrame(body, text="Chọn màn / lưới cần đối soát", padding=8)
        right = ttk.LabelFrame(body, text="Kết quả lần chạy", padding=8)
        body.add(left, weight=1)
        body.add(right, weight=3)

        ttk.Label(left, text="Cụm thông tin").pack(anchor="w")
        self.pick_group_var = tk.StringVar()
        self.pick_group = ttk.Combobox(left, textvariable=self.pick_group_var, state="readonly")
        self.pick_group.pack(fill="x", pady=(2, 8))
        self.pick_group.bind("<<ComboboxSelected>>", self._refresh_dataset_choices)
        ttk.Label(left, text="Màn hình / bảng dữ liệu").pack(anchor="w")
        self.pick_dataset_var = tk.StringVar()
        self.pick_dataset = ttk.Combobox(left, textvariable=self.pick_dataset_var, state="readonly")
        self.pick_dataset.pack(fill="x", pady=(2, 8))
        self.pick_dataset.bind("<<ComboboxSelected>>", self._update_selection_action)
        self.selection_status = ttk.Label(left, text="")
        self.selection_status.pack(anchor="w", pady=(0, 4))
        self.selection_button = ttk.Button(left, text="Chọn mapping", command=self._toggle_dataset_selection)
        self.selection_button.pack(anchor="w", pady=(0, 10))
        selected_header = ttk.Frame(left)
        selected_header.pack(fill="x")
        self.selected_count_label = ttk.Label(selected_header, text="Mapping được chọn để chạy")
        self.selected_count_label.pack(side="left", anchor="w")
        ttk.Button(selected_header, text="Chọn lại tất cả", command=self._select_all).pack(side="right")
        chosen_frame = ttk.Frame(left)
        chosen_frame.pack(fill="both", expand=True, pady=(3, 0))
        self.selected_list = tk.Listbox(chosen_frame, exportselection=False, font=("Segoe UI", 9), activestyle="none")
        chosen_scroll = ttk.Scrollbar(chosen_frame, orient="vertical", command=self.selected_list.yview)
        self.selected_list.configure(yscrollcommand=chosen_scroll.set)
        self.selected_list.pack(side="left", fill="both", expand=True)
        chosen_scroll.pack(side="right", fill="y")
        self.pick_group["values"] = [GROUP_LABELS[g] for g in ("LAI_LICH", "DIEN_BIEN", "KET_THUC")]
        self.pick_group_var.set(GROUP_LABELS["LAI_LICH"])
        self._refresh_dataset_choices()
        self._refresh_selected_list()

        result_filters = ttk.Frame(right)
        result_filters.pack(fill="x", pady=(0, 6))
        ttk.Label(result_filters, text="Cụm").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.result_group_var = tk.StringVar(value="Tất cả cụm")
        self.result_group = ttk.Combobox(result_filters, textvariable=self.result_group_var, state="readonly",
                                         values=["Tất cả cụm", *[GROUP_LABELS[g] for g in ("LAI_LICH", "DIEN_BIEN", "KET_THUC")]])
        self.result_group.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        self.result_group.bind("<<ComboboxSelected>>", self._refresh_result_dataset_choices)
        ttk.Label(result_filters, text="Màn / lưới").grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.result_dataset_var = tk.StringVar(value="Tất cả màn / lưới")
        self.result_dataset = ttk.Combobox(result_filters, textvariable=self.result_dataset_var, state="readonly")
        self.result_dataset.grid(row=0, column=3, sticky="ew")
        result_filters.columnconfigure(1, weight=1)
        result_filters.columnconfigure(3, weight=2)
        self.result_dataset.bind("<<ComboboxSelected>>", self._apply_summary_filter)

        summary_frame = ttk.Frame(right)
        summary_frame.pack(fill="both", expand=True)
        self.summary_tree = ttk.Treeview(summary_frame, columns=("group", "dataset", "oldn", "newn", "match", "diff", "oldonly", "newonly", "status"), show="headings", height=8)
        heads = [("group", "Cụm"), ("dataset", "Màn / lưới"), ("oldn", "DB cũ"), ("newn", "DB mới"), ("match", "Khớp"), ("diff", "Lệch"), ("oldonly", "Thiếu mới"), ("newonly", "Thiếu cũ"), ("status", "Trạng thái")]
        for key, title in heads:
            self.summary_tree.heading(key, text=title)
            self.summary_tree.column(key, width=90 if key not in ("dataset", "status") else (180 if key == "dataset" else 190), anchor="w")
        self.summary_scroll = ttk.Scrollbar(summary_frame, orient="horizontal", command=self.summary_tree.xview)
        self.summary_vscroll = ttk.Scrollbar(summary_frame, orient="vertical", command=self.summary_tree.yview)
        self.summary_tree.configure(xscrollcommand=self.summary_scroll.set, yscrollcommand=self.summary_vscroll.set)
        summary_frame.rowconfigure(0, weight=1)
        summary_frame.columnconfigure(0, weight=1)
        self.summary_tree.grid(row=0, column=0, sticky="nsew")
        self.summary_vscroll.grid(row=0, column=1, sticky="ns")
        self.summary_scroll.grid(row=1, column=0, sticky="ew")
        self.summary_tree.bind("<<TreeviewSelect>>", self._show_details)
        ttk.Label(right, text="Chi tiết dòng sai lệch của dataset đang chọn").pack(anchor="w", pady=(8, 3))
        detail_frame = ttk.Frame(right)
        detail_frame.pack(fill="both", expand=True)
        self.detail_tree = ttk.Treeview(detail_frame, columns=("status", "hsld", "key", "column", "old", "new"), show="headings", height=5)
        for key, title, width in (("status", "Trạng thái", 220), ("hsld", "HSLĐ", 110), ("key", "Khóa", 130), ("column", "Trường", 200), ("old", "Giá trị cũ", 210), ("new", "Giá trị mới", 210)):
            self.detail_tree.heading(key, text=title)
            self.detail_tree.column(key, width=width, anchor="w")
        self.detail_scroll = ttk.Scrollbar(detail_frame, orient="horizontal", command=self.detail_tree.xview)
        self.detail_vscroll = ttk.Scrollbar(detail_frame, orient="vertical", command=self.detail_tree.yview)
        self.detail_tree.configure(xscrollcommand=self.detail_scroll.set, yscrollcommand=self.detail_vscroll.set)
        detail_frame.rowconfigure(0, weight=1)
        detail_frame.columnconfigure(0, weight=1)
        self.detail_tree.grid(row=0, column=0, sticky="nsew")
        self.detail_vscroll.grid(row=0, column=1, sticky="ns")
        self.detail_scroll.grid(row=1, column=0, sticky="ew")

    def _add_missing_menu_datasets(self):
        datasets = list(self.datasets)
        existing = {(s.get("group"), menu_prefix(s["code"])) for s in datasets}
        for group, prefixes in MENU_ORDER.items():
            for prefix in prefixes:
                if (group, prefix) not in existing:
                    datasets.append({"code": f"{prefix}_unmapped", "name": MENU_NAMES[prefix], "group": group,
                                     "old_table": "Chưa xác định", "new_table": "", "unmapped": True})
        return datasets

    def _dataset_label(self, dataset):
        return dataset["name"]

    def _refresh_dataset_choices(self, _event=None):
        group = next((g for g, label in GROUP_LABELS.items() if label == self.pick_group_var.get()), "LAI_LICH")
        datasets = [s for s in self.menu_datasets if s.get("group") == group]
        datasets.sort(key=lambda s: (MENU_ORDER[group].index(menu_prefix(s["code"])) if menu_prefix(s["code"]) in MENU_ORDER[group] else 999, s["name"], s["code"]))
        self.selection_options = {self._dataset_label(s): s["code"] for s in datasets}
        labels = list(self.selection_options)
        self.pick_dataset["values"] = labels
        if labels and self.pick_dataset_var.get() not in self.selection_options:
            self.pick_dataset_var.set(labels[0])
        elif not labels:
            self.pick_dataset_var.set("")
        self._update_selection_action()

    def _update_selection_action(self, _event=None):
        code = self.selection_options.get(self.pick_dataset_var.get())
        dataset = self.by_code.get(code)
        if not dataset:
            self.selection_status.configure(text="Chọn màn hình hoặc lưới dữ liệu.")
            self.selection_button.configure(text="Chọn mapping", state="disabled")
        elif dataset.get("unmapped"):
            self.selection_status.configure(text="Chưa có mapping để đối soát.")
            self.selection_button.configure(text="Chưa có mapping", state="disabled")
        elif code in self.selected:
            self.selection_status.configure(text="Mapping này đang được chọn.")
            self.selection_button.configure(text="Bỏ mapping này", state="normal")
        else:
            self.selection_status.configure(text="Mapping này chưa được chọn.")
            self.selection_button.configure(text="Chọn mapping này", state="normal")

    def _toggle_dataset_selection(self):
        code = self.selection_options.get(self.pick_dataset_var.get())
        dataset = self.by_code.get(code)
        if not dataset or dataset.get("unmapped"):
            return
        if code in self.selected:
            self.selected.remove(code)
        else:
            self.selected.add(code)
        self._refresh_selected_list()
        self._update_selection_action()

    def _refresh_selected_list(self):
        self.selected_list.delete(0, "end")
        chosen = [s for s in self.datasets if s["code"] in self.selected]
        chosen.sort(key=lambda s: (("LAI_LICH", "DIEN_BIEN", "KET_THUC").index(s["group"]), s["name"], s["code"]))
        for dataset in chosen:
            self.selected_list.insert("end", f"{GROUP_LABELS.get(dataset['group'], dataset['group'])} · {dataset['name']}")
        self.selected_count_label.configure(text=f"Mapping được chọn để chạy ({len(chosen)})")

    def _select_all(self):
        self.selected = {s["code"] for s in self.datasets if not s.get("unmapped")}
        self._refresh_selected_list()
        self._update_selection_action()

    def _cfg(self, side):
        return {k: v.get().strip() if k != "password" else v.get() for k, v in self.fields[side].items()}

    def _test_connection(self, side):
        if self.busy:
            return
        cfg = self._cfg(side)
        if not cfg["dsn"] or not cfg["user"] or not cfg["password"]:
            messagebox.showwarning("Thiếu thông tin", "Nhập DSN, user và mật khẩu trước khi kiểm tra.")
            return
        self._set_busy(True, "Đang kiểm tra kết nối...")
        threading.Thread(target=self._test_worker, args=(side, cfg), daemon=True).start()

    def _test_worker(self, side, cfg):
        try:
            info = engine.test_connection(cfg)
            self.events.put(("test_ok", side, info))
        except Exception as exc:
            self.events.put(("error", f"Kiểm tra DB {'cũ' if side == 'old' else 'mới'} thất bại: {exc}"))

    def _run(self):
        if self.busy:
            return
        old_cfg, new_cfg = self._cfg("old"), self._cfg("new")
        for side, cfg in (("cũ", old_cfg), ("mới", new_cfg)):
            if not cfg["dsn"] or not cfg["user"] or not cfg["password"]:
                messagebox.showwarning("Thiếu thông tin", f"Nhập DSN, user, mật khẩu DB {side}.")
                return
            if "/" not in cfg["dsn"]:
                messagebox.showwarning("DSN chưa đủ", f"DSN DB {side} cần dạng host:port/service.")
                return
        selected = [s for s in self.datasets if (s["code"] in self.selected or s.get("unmapped"))]
        if not self.selected:
            messagebox.showwarning("Chưa chọn dataset", "Chọn ít nhất một màn/lưới có mapping.")
            return
        path = self.out_var.get().strip()
        if not path.lower().endswith(".xlsx"):
            messagebox.showwarning("File chưa đúng", "Chọn tên file có đuôi .xlsx.")
            return
        self.cancel_event.clear()
        self._set_busy(True, "Đang đối soát...")
        self.progress.configure(value=0, maximum=len(selected))
        self.progress_label.configure(text=f"Bắt đầu chạy {len(selected)} mapping; ghép hồ sơ theo HSLĐ.")
        threading.Thread(target=self._run_worker, args=(old_cfg, new_cfg, selected, path), daemon=True).start()

    def _run_worker(self, old_cfg, new_cfg, selected, path):
        try:
            result = engine.run_comparison(old_cfg, new_cfg, selected,
                progress=lambda i, n, name: self.events.put(("progress", i, n, name)), cancel=self.cancel_event)
            write_report(path, result, old_cfg, new_cfg, len(selected))
            self.events.put(("done", result, path))
        except InterruptedError:
            self.events.put(("cancelled",))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _set_busy(self, value, status):
        self.busy = value
        self.run_button.configure(state="disabled" if value else "normal")
        self.cancel_button.configure(state="normal" if value else "disabled")
        self.progress_label.configure(text=status)

    def _poll(self):
        while not self.events.empty():
            event = self.events.get()
            if event[0] == "test_ok":
                _, side, info = event
                self._set_busy(False, "Sẵn sàng")
                messagebox.showinfo("Kết nối thành công", f"DB: {info[0]}\nSchema: {info[1]}\nGiờ DB: {info[2]}")
            elif event[0] == "progress":
                _, i, n, label = event
                self.progress.configure(maximum=n, value=i)
                self.progress_label.configure(text=f"{i}/{n}: {label}")
            elif event[0] == "done":
                _, result, path = event
                self.result = result
                self._show_summary(result)
                self._set_busy(False, f"Hoàn tất • {len(result['details'])} dòng sai lệch")
                messagebox.showinfo("Đã hoàn tất", f"Đã xuất báo cáo 4 sheet:\n{path}\n\nSố dòng sai lệch: {len(result['details'])}")
            elif event[0] == "cancelled":
                self._set_busy(False, "Đã hủy")
            elif event[0] == "error":
                self._set_busy(False, "Có lỗi")
                messagebox.showerror("Không chạy được", event[1])
        self.after(120, self._poll)

    def _show_summary(self, result):
        self.result = result
        self.summary_rows = list(result["summaries"])
        self.result_group_var.set("Tất cả cụm")
        self._refresh_result_dataset_choices()

    def _refresh_result_dataset_choices(self, _event=None):
        group_label = self.result_group_var.get()
        rows = [r for r in self.summary_rows
                if group_label == "Tất cả cụm" or GROUP_LABELS.get(r.get("group"), r.get("group", "")) == group_label]
        self.result_options = {self._dataset_label({"name": r.get("name", ""), "code": r.get("code", "") }): r.get("code") for r in rows}
        self.result_dataset["values"] = ["Tất cả màn / lưới", *self.result_options.keys()]
        self.result_dataset_var.set("Tất cả màn / lưới")
        self._apply_summary_filter()

    def _apply_summary_filter(self, _event=None):
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)
        for item in self.detail_tree.get_children():
            self.detail_tree.delete(item)
        group_label = self.result_group_var.get()
        selected_code = self.result_options.get(self.result_dataset_var.get())
        rows = [r for r in self.summary_rows
                if (group_label == "Tất cả cụm" or GROUP_LABELS.get(r.get("group"), r.get("group", "")) == group_label)
                and (selected_code is None or r.get("code") == selected_code)]
        for row in rows:
            group = GROUP_LABELS.get(row.get("group"), row.get("group", ""))
            self.summary_tree.insert("", "end", iid=row.get("code"), values=(group, row.get("name"), row.get("old_total"), row.get("new_total"),
                row.get("matched"), row.get("diff"), row.get("old_only"), row.get("new_only"), row.get("status")))
        children = self.summary_tree.get_children()
        if children:
            self.summary_tree.selection_set(children[0])
            self._show_details(None)

    def _show_details(self, _event):
        if not self.result:
            return
        selection = self.summary_tree.selection()
        if not selection:
            return
        code = selection[0]
        for item in self.detail_tree.get_children():
            self.detail_tree.delete(item)
        rows = [d for d in self.result["details"] if d.get("code") == code]
        for row in rows[:10000]:
            column = row.get("old_column") or row.get("new_column") or "Bản ghi"
            self.detail_tree.insert("", "end", values=(row.get("status"), row.get("hsld"), row.get("key"), column,
                row.get("old_value"), row.get("new_value")))

    def _pick_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                            initialfile=Path(self.out_var.get()).name)
        if path:
            self.out_var.set(path)

if __name__ == "__main__":
    App().mainloop()
