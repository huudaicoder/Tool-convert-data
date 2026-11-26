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
import location_converter
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
REDUCTION_FIELD_GROUPS = [
    ("SO_QUYET_DINH", "Số QĐ"),
    ("NGAY_QUYET_DINH", "Ngày QĐ"),
    ("MUC_GIAM_ID", "Mức giảm"),
    ("TOA_QUYET_DINH_ID", "Tòa"),
    ("DIA_PHUONG_ID", "Địa phương"),
    ("NGAY_THA_GIAM_HET_AN", "Ngày hết hạn"),
]
REDUCTION_INSERT_FIELD_GROUPS = [
    ("MUC_DE_NGHI_ID", "Mức đề nghị"),
    ("CAP_TREN_DUYET_ID", "Mức BCA duyệt"),
    ("DA_CHAP_HANH", "Đã chấp hành"),
    ("CON_LAI", "Còn lại"),
    ("SO_QUYET_DINH", "Số QĐ"),
    ("NGAY_QUYET_DINH", "Ngày QĐ"),
    ("MUC_GIAM_ID", "Mức Tòa giảm"),
    ("TOA_QUYET_DINH_ID", "Tòa"),
    ("DIA_PHUONG_ID", "Địa phương"),
    ("NGAY_THA_GIAM_HET_AN", "Ngày hết hạn"),
    ("NHAN_XET", "Nhận xét"),
    ("KQCT_PHIEU", "KQCT phiếu"),
    ("KQCT_DANHSACH", "KQCT danh sách"),
]
BIOGRAPHY_FIELD_GROUPS = [
    ("LL_TOM_TAT_HV", "Tóm tắt hành vi"),
    ("LL_CHI_TIET_HV", "Hành vi vi phạm"),
    ("LL_SO_TIEN_AN", "Số tiền án"),
    ("LL_NHAN_THAN", "Nhân thân"),
    ("LL_TAI_PHAM", "Tái phạm"),
    ("LL_DM_DAN_TOC_ID", "Dân tộc"),
    ("LL_DM_TON_GIAO_ID", "Tôn giáo"),
    ("LL_PHAN_DOI_ID", "Phân đội"),
    ("LL_PHAN_TRAI_ID", "Phân trại (theo phân đội)"),
]
EXECUTION_DURATION_FIELD_GROUPS = [
    ("THA_THOI_GIAN_TAM_GIAM", "Thời gian tạm giam"),
    ("THA_THOI_GIAN_TAM_GIU", "Thời gian tạm giữ"),
]


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
        self.result = None
        self.reduction_plan = None
        self.reduction_item_ids = {}
        self.reduction_checked_items = set()
        self.reduction_supplement_plan = None
        self.reduction_supplement_item_ids = {}
        self.reduction_supplement_checked_items = set()
        self.biography_plan = None
        self.biography_item_ids = {}
        self.biography_checked_items = set()
        self.biography_field_vars = {}
        self.execution_plan = None
        self.execution_item_ids = {}
        self.execution_checked_items = set()
        self.execution_field_vars = {}
        self.classification_plan = None
        self.classification_item_ids = {}
        self.classification_checked_items = set()
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
            button_row = 4
            if side == "new":
                ttk.Label(box, text="Mã trại DB mới (TG_MA)").grid(row=4, column=0, sticky="w", padx=(0, 8), pady=3)
                prison_var = tk.StringVar()
                ttk.Entry(box, textvariable=prison_var).grid(row=4, column=1, sticky="ew", pady=3)
                self.fields[side]["prison_code"] = prison_var
                button_row = 5
            ttk.Button(box, text="Kiểm tra kết nối", command=lambda s=side: self._test_connection(s)).grid(row=button_row, column=1, sticky="e", pady=(6, 0))

        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True)
        compare_tab = ttk.Frame(notebook, padding=8)
        reduction_tab = ttk.Frame(notebook, padding=8)
        biography_tab = ttk.Frame(notebook, padding=8)
        execution_tab = ttk.Frame(notebook, padding=8)
        classification_tab = ttk.Frame(notebook, padding=8)
        province_audit_tab = ttk.Frame(notebook, padding=8)
        ward_catalog_tab = ttk.Frame(notebook, padding=8)
        same_schema_tab = ttk.Frame(notebook, padding=8)
        location_tab = ttk.Frame(notebook, padding=8)
        notebook.add(compare_tab, text="Đối soát")
        notebook.add(reduction_tab, text="Cập nhật giảm thời hạn")
        notebook.add(biography_tab, text="Cập nhật lai lịch")
        notebook.add(execution_tab, text="Cập nhật thi hành án")
        notebook.add(classification_tab, text="Cập nhật xếp loại")
        notebook.add(province_audit_tab, text="Đối chiếu danh mục tỉnh/thành phố")
        notebook.add(ward_catalog_tab, text="Đối chiếu xã/phường")
        notebook.add(same_schema_tab, text="Lai lịch không chuyển đổi")
        notebook.add(location_tab, text="Convert địa phương")

        output_bar = ttk.Frame(compare_tab, padding=(0, 0, 0, 5))
        output_bar.pack(fill="x", pady=(0, 6))
        path_row = ttk.Frame(output_bar)
        path_row.pack(fill="x")
        ttk.Label(path_row, text="File kết quả").pack(side="left")
        self.out_var = tk.StringVar(value=str(Path.home() / "Documents" / "Bao_cao_doi_soat_C10.xlsx"))
        ttk.Entry(path_row, textvariable=self.out_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(path_row, text="Chọn nơi lưu...", command=self._pick_output).pack(side="left")
        self.cancel_button = ttk.Button(path_row, text="Hủy", command=self.cancel_event.set, state="disabled")
        self.cancel_button.pack(side="right", padx=(8, 0))
        self.run_button = ttk.Button(path_row, text="Chạy đối soát", command=self._run)
        self.run_button.pack(side="right", padx=(8, 0), ipadx=12)
        action_row = ttk.Frame(output_bar)
        action_row.pack(fill="x", pady=(5, 0))
        self.progress_label = ttk.Label(action_row, text="")
        self.progress_label.pack(side="left", fill="x", expand=True)

        body = ttk.Panedwindow(compare_tab, orient="horizontal")
        body.pack(fill="both", expand=True, pady=(0, 8))
        left = ttk.LabelFrame(body, text="Chọn màn cần đối soát", padding=8)
        right = ttk.LabelFrame(body, text="Kết quả lần chạy", padding=8)
        body.add(left, weight=1)
        body.add(right, weight=3)

        ttk.Label(left, text="Cụm thông tin").pack(anchor="w")
        self.pick_group_var = tk.StringVar(value="Tất cả cụm")
        self.pick_group = ttk.Combobox(left, textvariable=self.pick_group_var, state="readonly")
        self.pick_group.pack(fill="x", pady=(2, 8))
        self.pick_group.bind("<<ComboboxSelected>>", self._refresh_dataset_choices)
        ttk.Label(left, text="Màn hình").pack(anchor="w")
        self.pick_dataset_var = tk.StringVar(value="Tất cả màn hình")
        self.pick_dataset = ttk.Combobox(left, textvariable=self.pick_dataset_var, state="readonly")
        self.pick_dataset.pack(fill="x", pady=(2, 8))
        self.pick_dataset.bind("<<ComboboxSelected>>", self._refresh_selected_list)
        selected_header = ttk.Frame(left)
        selected_header.pack(fill="x")
        self.selected_count_label = ttk.Label(selected_header, text="Bảng dữ liệu sẽ đối soát")
        self.selected_count_label.pack(side="left", anchor="w")
        chosen_frame = ttk.Frame(left)
        chosen_frame.pack(fill="both", expand=True, pady=(3, 0))
        self.selected_list = tk.Listbox(chosen_frame, exportselection=False, font=("Segoe UI", 9), activestyle="none")
        chosen_scroll = ttk.Scrollbar(chosen_frame, orient="vertical", command=self.selected_list.yview)
        self.selected_list.configure(yscrollcommand=chosen_scroll.set)
        self.selected_list.pack(side="left", fill="both", expand=True)
        chosen_scroll.pack(side="right", fill="y")
        self.pick_group["values"] = ["Tất cả cụm", *[GROUP_LABELS[g] for g in ("LAI_LICH", "DIEN_BIEN", "KET_THUC")]]
        self._refresh_dataset_choices()

        result_filters = ttk.Frame(right)
        result_filters.pack(fill="x", pady=(0, 6))
        ttk.Label(result_filters, text="Cụm").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.result_group_var = tk.StringVar(value="Tất cả cụm")
        self.result_group = ttk.Combobox(result_filters, textvariable=self.result_group_var, state="readonly",
                                         values=["Tất cả cụm", *[GROUP_LABELS[g] for g in ("LAI_LICH", "DIEN_BIEN", "KET_THUC")]])
        self.result_group.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        self.result_group.bind("<<ComboboxSelected>>", self._refresh_result_dataset_choices)
        ttk.Label(result_filters, text="Màn").grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.result_dataset_var = tk.StringVar(value="Tất cả màn")
        self.result_dataset = ttk.Combobox(result_filters, textvariable=self.result_dataset_var, state="readonly")
        self.result_dataset.grid(row=0, column=3, sticky="ew")
        result_filters.columnconfigure(1, weight=1)
        result_filters.columnconfigure(3, weight=2)
        self.result_dataset.bind("<<ComboboxSelected>>", self._apply_summary_filter)

        summary_frame = ttk.Frame(right)
        summary_frame.pack(fill="both", expand=True)
        self.summary_tree = ttk.Treeview(summary_frame, columns=("group", "dataset", "oldn", "newn", "match", "diff", "oldonly", "newonly", "status"), show="headings", height=8)
        heads = [("group", "Cụm"), ("dataset", "Màn"), ("oldn", "DB cũ"), ("newn", "DB mới"), ("match", "Khớp"), ("diff", "Lệch"), ("oldonly", "Thiếu mới"), ("newonly", "Thiếu cũ"), ("status", "Trạng thái")]
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
        self._build_reduction_tab(reduction_tab)
        self._build_biography_tab(biography_tab)
        self._build_execution_tab(execution_tab)
        self._build_classification_tab(classification_tab)
        self._build_province_audit_tab(province_audit_tab)
        self._build_ward_catalog_tab(ward_catalog_tab)
        self._build_same_schema_tab(same_schema_tab)
        self._build_location_tab(location_tab)
    def _build_same_schema_tab(self, parent):
        ttk.Label(parent, text="So sánh hai CSDL cùng kiến trúc theo mã trại nhập ở DB mới (TG_MA); chỉ lấy phạm vi phạm nhân của trại đó ở hai DB, ghép theo HSLĐ. Chỉ phân đội và phân trại khác nhau mới được đưa vào xem trước cập nhật.",
                  wraplength=1100).pack(anchor="w", pady=(0, 8))
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(0, 6))
        self.location_actions_frame = actions
        self.same_schema_preview_button = ttk.Button(actions, text="Lấy xem trước", command=self._preview_same_schema)
        self.same_schema_preview_button.pack(side="left")
        self.same_schema_apply_button = ttk.Button(actions, text="Cập nhật dòng đã chọn", command=lambda: self._apply_same_schema(True), state="disabled")
        self.same_schema_apply_button.pack(side="left", padx=(8, 0))
        self.same_schema_all_button = ttk.Button(actions, text="Cập nhật toàn bộ", command=lambda: self._apply_same_schema(False), state="disabled")
        self.same_schema_all_button.pack(side="left", padx=(8, 0))
        self.same_schema_selected_label = ttk.Label(actions, text="Đã chọn: 0 hồ sơ")
        self.same_schema_selected_label.pack(side="left", padx=(12, 0))
        self.same_schema_status = ttk.Label(parent, text="Chưa tải xem trước.", wraplength=1100)
        self.same_schema_status.pack(anchor="w", pady=(0, 6))
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        columns = ("select", "hsld", "status", "target_id", "team_old", "team_new", "branch_old", "branch_new")
        self.same_schema_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="none")
        for key, title, width in (("select", "Chọn", 55), ("hsld", "HSLĐ", 135), ("status", "Trạng thái", 260),
                                  ("target_id", "ID lai lịch DB mới", 130), ("team_old", "Phân đội cũ: ID · mã · tên", 270),
                                  ("team_new", "Phân đội mới: hiện tại → đích", 380), ("branch_old", "Phân trại cũ: ID · mã · tên", 270),
                                  ("branch_new", "Phân trại mới: hiện tại → đích", 380)):
            self.same_schema_tree.heading(key, text=title)
            self.same_schema_tree.column(key, width=width, anchor="center" if key == "select" else "w")
        self.same_schema_tree.bind("<Button-1>", self._toggle_same_schema_row)
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.same_schema_tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.same_schema_tree.xview)
        self.same_schema_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        frame.rowconfigure(0, weight=1); frame.columnconfigure(0, weight=1)
        self.same_schema_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns"); xscroll.grid(row=1, column=0, sticky="ew")
        self.same_schema_plan = None
        self.same_schema_item_ids = {}
        self.same_schema_checked_items = set()

    def _preview_same_schema(self):
        if self.busy:
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        self.same_schema_plan = None
        self.same_schema_item_ids.clear(); self.same_schema_checked_items.clear()
        self.same_schema_status.configure(text="Đang so sánh hai CSDL ở chế độ chỉ đọc...")
        self._set_busy(True, "Đang so sánh lai lịch cùng kiến trúc...")
        threading.Thread(target=self._preview_same_schema_worker, args=(*configs,), daemon=True).start()

    def _preview_same_schema_worker(self, old_cfg, new_cfg):
        try:
            self.events.put(("same_schema_preview", engine.preview_same_schema_units(old_cfg, new_cfg)))
        except Exception as exc:
            self.events.put(("error", f"Không so sánh được lai lịch không chuyển đổi: {exc}"))

    def _toggle_same_schema_row(self, event):
        if self.same_schema_tree.identify_column(event.x) != "#1":
            return
        item = self.same_schema_tree.identify_row(event.y)
        if not item or self.same_schema_item_ids.get(item) is None:
            return
        if item in self.same_schema_checked_items:
            self.same_schema_checked_items.remove(item); mark = "☐"
        else:
            self.same_schema_checked_items.add(item); mark = "☑"
        self.same_schema_tree.set(item, "select", mark)
        self.same_schema_selected_label.configure(text=f"Đã chọn: {len(self.same_schema_checked_items):,} hồ sơ")
        self._refresh_same_schema_buttons()

    def _refresh_same_schema_buttons(self):
        enabled = not self.busy and bool(self.same_schema_plan and self.same_schema_plan.get("updates"))
        if hasattr(self, "same_schema_apply_button"):
            self.same_schema_apply_button.configure(state="normal" if enabled and self.same_schema_checked_items else "disabled")
            self.same_schema_all_button.configure(state="normal" if enabled else "disabled")

    def _apply_same_schema(self, selected_only):
        if self.busy or not self.same_schema_plan or not self.same_schema_plan.get("updates"):
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        selected_ids = ({self.same_schema_item_ids[i] for i in self.same_schema_checked_items
                         if self.same_schema_item_ids.get(i) is not None} if selected_only else None)
        if selected_only and not selected_ids:
            messagebox.showwarning("Chưa chọn hồ sơ", "Hãy chọn ít nhất một hồ sơ trong xem trước."); return
        rows = [r for r in self.same_schema_plan["updates"] if selected_ids is None or r["id"] in selected_ids]
        scope = self.same_schema_plan["prison_scope"]["code"]
        if not messagebox.askyesno("Xác nhận cập nhật", f"Sẽ cập nhật phân đội/phân trại cho {len(rows):,} hồ sơ của trại {scope} theo DB cũ. Tiếp tục ghi DB mới?"):
            return
        self._set_busy(True, "Đang cập nhật phân đội/phân trại...")
        self.same_schema_status.configure(text="Đang ghi DB mới; nếu dữ liệu thay đổi so với xem trước, transaction sẽ rollback.")
        threading.Thread(target=self._apply_same_schema_worker, args=(*configs, self.same_schema_plan, selected_ids), daemon=True).start()

    def _apply_same_schema_worker(self, old_cfg, new_cfg, plan, selected_ids):
        try:
            self.events.put(("same_schema_done", engine.apply_same_schema_units(old_cfg, new_cfg, plan, selected_ids)))
        except Exception as exc:
            self.events.put(("error", f"Không cập nhật được lai lịch không chuyển đổi: {exc}"))

    def _build_province_audit_tab(self, parent):
        ttk.Label(parent,
                  text="So trực tiếp MA_DP.MA với DM_TINH_THANH_PHO.TTP_MA (giữ nguyên số 0 đầu mã). "
                       "Preview chỉ hiện mã cũ không có đúng mã ở DB mới, cùng mã nhưng khác tên, "
                       "và mã bị trùng ở DB mới. Chỉ đọc, không cập nhật hai CSDL.",
                  wraplength=1100).pack(anchor="w", pady=(0, 8))
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(0, 6))
        self.province_audit_button = ttk.Button(actions, text="Lấy xem trước", command=self._preview_province_audit)
        self.province_audit_button.pack(side="left")
        self.province_audit_status = ttk.Label(actions, text="Chưa kiểm tra.", wraplength=1000)
        self.province_audit_status.pack(side="left", padx=(12, 0))
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        columns = ("old_code", "old_name", "new_code", "new_name", "status")
        self.province_audit_tree = ttk.Treeview(frame, columns=columns, show="headings")
        for key, title, width in (
                ("old_code", "Mã MA_DP DB cũ", 140), ("old_name", "Tên địa phương DB cũ", 260),
                ("new_code", "Mã TTP DB mới", 150), ("new_name", "Tên tỉnh/thành phố DB mới", 260),
                ("status", "Kết quả đối chiếu", 310)):
            self.province_audit_tree.heading(key, text=title)
            self.province_audit_tree.column(key, width=width, anchor="w")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.province_audit_tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.province_audit_tree.xview)
        self.province_audit_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.province_audit_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

    def _build_ward_catalog_tab(self, parent):
        ttk.Label(parent,
                  text="Preview chỉ liệt kê mã MA_DP_XA_PHUONG có ở DB cũ mà XP_MA chưa có ở DB mới, kèm toàn bộ giá trị dự kiến insert. Insert tất cả sẽ bỏ qua mã được thêm sau preview; dòng thiếu thông tin bắt buộc sẽ được báo và không ghi.",
                  wraplength=1150, justify="left").pack(anchor="w", pady=(0, 8))
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(0, 6))
        self.ward_catalog_preview_button = ttk.Button(actions, text="Preview", command=self._preview_ward_catalog)
        self.ward_catalog_preview_button.pack(side="left")
        self.ward_catalog_insert_button = ttk.Button(actions, text="Insert tất cả", command=self._insert_ward_catalog, state="disabled")
        self.ward_catalog_insert_button.pack(side="left", padx=(8, 0))
        self.ward_catalog_status = ttk.Label(actions, text="Chưa preview.", wraplength=950)
        self.ward_catalog_status.pack(side="left", padx=(12, 0))
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        columns = ("old_code", "province_code", "name", "status", "created", "deleted", "result")
        self.ward_catalog_tree = ttk.Treeview(frame, columns=columns, show="headings")
        for key, title, width in (
                ("old_code", "XP_MA ← MA", 135), ("province_code", "XP_MA_TINH_THANH_PHO ← MA_QH", 220),
                ("name", "XP_TEN ← ND", 300),
                ("status", "XP_TRANG_THAI", 110), ("created", "CREATION_TIME", 180),
                ("deleted", "IS_DELETED", 100), ("result", "Trạng thái", 220)):
            self.ward_catalog_tree.heading(key, text=title)
            self.ward_catalog_tree.column(key, width=width, anchor="w")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.ward_catalog_tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.ward_catalog_tree.xview)
        self.ward_catalog_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.ward_catalog_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.ward_catalog_plan = None

    def _preview_ward_catalog(self):
        if self.busy:
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        self.ward_catalog_plan = None
        self.ward_catalog_insert_button.configure(state="disabled")
        for item in self.ward_catalog_tree.get_children():
            self.ward_catalog_tree.delete(item)
        self.ward_catalog_status.configure(text="Đang so sánh danh mục xã/phường ở chế độ chỉ đọc...")
        self._set_busy(True, "Đang preview mã xã/phường còn thiếu...")
        threading.Thread(target=self._preview_ward_catalog_worker, args=configs, daemon=True).start()

    def _preview_ward_catalog_worker(self, old_cfg, new_cfg):
        try:
            self.events.put(("ward_catalog_preview", engine.preview_ward_catalog_sync(old_cfg, new_cfg)))
        except Exception as exc:
            self.events.put(("error", f"Không preview được danh mục xã/phường: {exc}"))

    def _insert_ward_catalog(self):
        if self.busy or not self.ward_catalog_plan:
            return
        rows = self.ward_catalog_plan["rows"]
        ready = [row for row in rows if row["insertable"]]
        if not ready:
            messagebox.showinfo("Không có dòng hợp lệ", "Không có dòng nào đủ thông tin để insert.")
            return
        province_warnings = sum(row.get("province_warning", False) for row in ready)
        province_nulls = sum(row.get("province_null", False) for row in ready)
        warning = f"\nCó {province_warnings:,} dòng MA_QH không thấy trong TTP_MA." if province_warnings else ""
        if province_nulls:
            warning += f"\nCó {province_nulls:,} dòng MA_QH NULL/rỗng; XP_MA_TINH_THANH_PHO sẽ được ghi mã 00."
        if not messagebox.askyesno("Xác nhận insert", f"Sẽ insert tối đa {len(ready):,} xã/phường còn thiếu vào DM_XA_PHUONG. Các mã đã có sẽ tự bỏ qua.{warning}\nTiếp tục?"):
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        self._set_busy(True, "Đang insert danh mục xã/phường...")
        self.ward_catalog_status.configure(text="Đang kiểm tra lại DB và ghi trong một transaction...")
        threading.Thread(target=self._insert_ward_catalog_worker,
                         args=(*configs, self.ward_catalog_plan), daemon=True).start()

    def _insert_ward_catalog_worker(self, old_cfg, new_cfg, plan):
        try:
            self.events.put(("ward_catalog_done", engine.insert_ward_catalog_missing(old_cfg, new_cfg, plan)))
        except Exception as exc:
            self.events.put(("error", f"Không insert được danh mục xã/phường: {exc}"))

    def _build_location_tab(self, parent):
        self.location_instruction = ttk.Label(parent,
            text=("Tool convert địa phương từ DB cũ sang DB mới. Gộp mã tỉnh trong DB hiện tại dùng "
                  "chương trình riêng GopMaTinhThanh.exe."),
            wraplength=1150, justify="left")
        self.location_instruction.pack(anchor="w", pady=(0, 4))
        self.location_mapping_label = ttk.Label(parent, text=f"File mapping: {location_converter.mapping_file_path()}", wraplength=1150)
        self.location_mapping_label.pack(anchor="w", pady=(0, 8))
        top = ttk.Frame(parent)
        top.pack(fill="x", pady=(0, 6))
        ttk.Button(top, text="Chọn tất cả màn có mapping", command=lambda: self._set_location_checks(True)).pack(side="left")
        ttk.Button(top, text="Bỏ chọn", command=lambda: self._set_location_checks(False)).pack(side="left", padx=6)
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(0, 6))
        self.location_actions_frame = actions
        self.location_preview_button = ttk.Button(actions, text="Lấy preview", command=self._preview_location)
        self.location_preview_button.pack(side="left")
        self.location_apply_selected_button = ttk.Button(actions, text="Cập nhật dòng chọn", command=lambda: self._apply_location(True), state="disabled")
        self.location_apply_selected_button.pack(side="left", padx=(8, 0))
        self.location_apply_all_button = ttk.Button(actions, text="Cập nhật tất cả dòng hợp lệ", command=lambda: self._apply_location(False), state="disabled")
        self.location_apply_all_button.pack(side="left", padx=(8, 0))
        self.location_selected_label = ttk.Label(actions, text="Đã chọn: 0 dòng")
        self.location_selected_label.pack(side="left", padx=(12, 0))
        self.location_status = ttk.Label(parent, text="Chưa preview. Cập nhật sẽ ghi DB mới.", wraplength=1150)
        self.location_status.pack(anchor="w", pady=(0, 6))
        columns = ("select", "screen", "hsld", "key", "source", "old_code", "target_code", "target", "current_id", "new_id", "new_name", "status")
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        self.location_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="none")
        for key, title, width in (
            ("select", "Chọn", 48), ("screen", "Màn", 180), ("hsld", "HSLĐ", 100),
            ("key", "Khóa sự kiện", 150), ("source", "Cột nguồn", 180), ("old_code", "Mã cũ", 90),
            ("target_code", "Mã TTP đích", 105),
            ("target", "Cột đích", 230), ("current_id", "ID hiện tại", 100), ("new_id", "TTP ID dự kiến", 110), ("new_name", "Tên tỉnh lịch sử", 180),
            ("status", "Trạng thái", 230)):
            self.location_tree.heading(key, text=title)
            self.location_tree.column(key, width=width, anchor="w")
        self.location_tree.bind("<Button-1>", self._toggle_location_row)
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.location_tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.location_tree.xview)
        self.location_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        frame.rowconfigure(0, weight=1); frame.columnconfigure(0, weight=1)
        self.location_tree.grid(row=0, column=0, sticky="nsew"); yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.location_plan = None
        self.location_screen_vars = {}
        self.location_item_update_index = {}
        self.location_checked_items = set()
        self._render_location_screen_checks(parent)

    def _render_location_screen_checks(self, parent):
        box = ttk.LabelFrame(parent, text="Chọn màn/bảng cần convert", padding=5)
        box.pack(fill="x", before=self.location_actions_frame, pady=(0, 6))
        self.location_screen_box = box
        screens = [s for s in M.SCREENS if any(isinstance(k, tuple) and k[0] in {"province", "province_text_id"} for _, _, k in s["cols"])]
        self.location_screen_vars = {s["code"]: tk.BooleanVar(value=True) for s in screens}
        for index, screen in enumerate(screens):
            ttk.Checkbutton(box, text=screen["name"], variable=self.location_screen_vars[screen["code"]]).grid(
                row=index // 4, column=index % 4, sticky="w", padx=4, pady=2)
            box.columnconfigure(index % 4, weight=1)

    def _set_location_checks(self, checked):
        for var in self.location_screen_vars.values():
            var.set(checked)

    def _toggle_location_row(self, event):
        if self.location_tree.identify_column(event.x) != "#1":
            return
        item = self.location_tree.identify_row(event.y)
        if not item or item not in self.location_item_update_index:
            return
        index = self.location_item_update_index[item]
        if item in self.location_checked_items:
            self.location_checked_items.remove(item)
            self.location_tree.set(item, "select", "☐")
        else:
            self.location_checked_items.add(item)
            self.location_tree.set(item, "select", "☑")
        self.location_selected_label.configure(text=f"Đã chọn: {len(self.location_checked_items):,} dòng")
        self._refresh_location_buttons()

    def _refresh_location_buttons(self):
        has_updates = bool(self.location_plan and self.location_plan.get("updates"))
        self.location_apply_selected_button.configure(state="normal" if not self.busy and has_updates and self.location_checked_items else "disabled")
        self.location_apply_all_button.configure(state="normal" if not self.busy and has_updates else "disabled")

    def _preview_location(self):
        if self.busy:
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        selected = [code for code, var in self.location_screen_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("Chưa chọn màn", "Hãy chọn ít nhất một màn/bảng.")
            return
        self.location_plan = None
        self.location_checked_items.clear()
        self.location_item_update_index.clear()
        for item in self.location_tree.get_children(): self.location_tree.delete(item)
        self.location_preview_button.configure(state="disabled")
        self.cancel_event.clear()
        self._set_busy(True, "Đang đọc mapping và lập preview...")
        threading.Thread(target=self._preview_location_worker, args=(*configs, selected), daemon=True).start()

    def _preview_location_worker(self, old_cfg, new_cfg, selected):
        try:
            plan = location_converter.preview(old_cfg, new_cfg, selected, self.cancel_event)
            self.events.put(("location_preview", plan))
        except InterruptedError:
            self.events.put(("cancelled",))
        except Exception as exc:
            self.events.put(("error", f"Không preview được convert địa phương: {exc}"))

    def _apply_location(self, selected_only):
        if self.busy or not self.location_plan:
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        new_cfg = configs[1]
        selected = {self.location_item_update_index[item] for item in self.location_checked_items
                    if item in self.location_item_update_index} if selected_only else None
        if selected_only and not selected:
            messagebox.showwarning("Chưa chọn dòng", "Chọn ít nhất một dòng READY trong preview.")
            return
        updates = self.location_plan["updates"]
        rows = [u for i, u in enumerate(updates) if selected is None or i in selected]
        if not rows:
            messagebox.showinfo("Không có dòng hợp lệ", "Không có dòng READY để cập nhật.")
            return
        confirmation = (f'Sẽ cập nhật {len(rows):,} trường tỉnh/thành trong {len({r["screen"] for r in rows})} màn '
                        f'của trại {self.location_plan["prison_scope"]["code"]}. Tiếp tục?')
        if not messagebox.askyesno("Xác nhận cập nhật", confirmation):
            return
        self._set_busy(True, "Đang cập nhật địa phương...")
        threading.Thread(target=self._apply_location_worker, args=(new_cfg, self.location_plan, selected), daemon=True).start()

    def _apply_location_worker(self, new_cfg, plan, selected):
        try:
            result = location_converter.apply(new_cfg, plan, selected)
            self.events.put(("location_done", result))
        except Exception as exc:
            self.events.put(("error", f"Không cập nhật được địa phương: {exc}"))

    def _preview_province_audit(self):
        if self.busy:
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        self.province_audit_button.configure(state="disabled")
        self._set_busy(True, "Đang đối chiếu MA_DP với danh mục tỉnh/thành phố...")
        threading.Thread(target=self._province_audit_worker, args=configs, daemon=True).start()

    def _province_audit_worker(self, old_cfg, new_cfg):
        try:
            result = engine.preview_province_catalog_audit(old_cfg, new_cfg)
            self.events.put(("province_audit_preview", result))
        except Exception as exc:
            self.events.put(("error", f"Không đối chiếu được danh mục tỉnh/thành phố: {exc}"))

    def _build_reduction_tab(self, parent):
        ttk.Label(parent, text="Dùng kết nối và mã trại phía trên. Cập nhật dòng đã có hoặc bổ sung dòng còn thiếu sau khi xem trước.",
                  wraplength=1000).pack(anchor="w", pady=(0, 8))
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True)
        update_tab = ttk.Frame(notebook, padding=6)
        supplement_tab = ttk.Frame(notebook, padding=6)
        notebook.add(update_tab, text="Cập nhật")
        notebook.add(supplement_tab, text="Bổ sung")

        ttk.Label(update_tab, text="Điền trường trống trong sáu trường; sửa MUC_GIAM_ID và DIA_PHUONG_ID nếu mapping khác.",
                  wraplength=1000).pack(anchor="w", pady=(0, 6))
        actions = ttk.Frame(update_tab)
        actions.pack(fill="x", pady=(0, 6))
        self.reduction_preview_button = ttk.Button(actions, text="Lấy xem trước", command=self._preview_reduction_update)
        self.reduction_preview_button.pack(side="left")
        self.reduction_apply_button = ttk.Button(actions, text="Cập nhật dòng đã chọn",
                                                 command=lambda: self._apply_reduction_update(selected_only=True), state="disabled")
        self.reduction_apply_button.pack(side="left", padx=(8, 0))
        self.reduction_all_button = ttk.Button(actions, text="Cập nhật toàn bộ",
                                               command=lambda: self._apply_reduction_update(selected_only=False), state="disabled")
        self.reduction_all_button.pack(side="left", padx=(8, 0))
        self.reduction_selected_label = ttk.Label(actions, text="Đã chọn: 0 dòng")
        self.reduction_selected_label.pack(side="left", padx=(12, 0))
        self.reduction_status = ttk.Label(update_tab, text="Chưa tải xem trước.", wraplength=1000)
        self.reduction_status.pack(anchor="w", pady=(0, 6))
        frame = ttk.Frame(update_tab)
        frame.pack(fill="both", expand=True)
        columns = ["select", "hsld", "date", "target_id"]
        headings = [("select", "Chọn", 55), ("hsld", "HSLĐ", 130),
                    ("date", "Ngày xét", 105), ("target_id", "ID giảm thời hạn", 115)]
        for target_col, label in REDUCTION_FIELD_GROUPS:
            old_col = f"{target_col}_old"
            new_col = f"{target_col}_new"
            columns.extend((old_col, new_col))
            headings.extend(((old_col, f"{label} (cũ)", 145), (new_col, f"{label} (mới)", 145)))
        columns.append("status")
        headings.append(("status", "Trạng thái", 200))
        self.reduction_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="none")
        for key, title, width in headings:
            self.reduction_tree.heading(key, text=title)
            self.reduction_tree.column(key, width=width, anchor="center" if key == "select" else "w")
        self.reduction_tree.bind("<Button-1>", self._toggle_reduction_row_check)
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.reduction_tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.reduction_tree.xview)
        self.reduction_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.reduction_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        ttk.Label(supplement_tab, text="Tạo dòng mới từ các trường DB cũ có mapping xác định. Mức đề nghị, mức BCA và mức Tòa được ánh xạ riêng.",
                  wraplength=1000).pack(anchor="w", pady=(0, 6))
        supplement_actions = ttk.Frame(supplement_tab)
        supplement_actions.pack(fill="x", pady=(0, 6))
        self.reduction_supplement_preview_button = ttk.Button(
            supplement_actions, text="Lấy xem trước", command=self._preview_reduction_supplement)
        self.reduction_supplement_preview_button.pack(side="left")
        self.reduction_supplement_apply_button = ttk.Button(
            supplement_actions, text="Bổ sung dòng đã chọn",
            command=lambda: self._apply_reduction_supplement(selected_only=True), state="disabled")
        self.reduction_supplement_apply_button.pack(side="left", padx=(8, 0))
        self.reduction_supplement_all_button = ttk.Button(
            supplement_actions, text="Bổ sung toàn bộ",
            command=lambda: self._apply_reduction_supplement(selected_only=False), state="disabled")
        self.reduction_supplement_all_button.pack(side="left", padx=(8, 0))
        self.reduction_supplement_selected_label = ttk.Label(supplement_actions, text="Đã chọn: 0 dòng")
        self.reduction_supplement_selected_label.pack(side="left", padx=(12, 0))
        self.reduction_supplement_status = ttk.Label(supplement_tab, text="Chưa tải xem trước.", wraplength=1000)
        self.reduction_supplement_status.pack(anchor="w", pady=(0, 6))
        supplement_frame = ttk.Frame(supplement_tab)
        supplement_frame.pack(fill="both", expand=True)
        supplement_columns = ["select", "hsld", "date", "status"]
        supplement_headings = [("select", "Chọn", 55), ("hsld", "HSLĐ", 120),
                               ("date", "Ngày xét", 105), ("status", "Trạng thái", 190)]
        for target_col, label in REDUCTION_INSERT_FIELD_GROUPS:
            old_col, new_col = f"{target_col}_old", f"{target_col}_new"
            supplement_columns.extend((old_col, new_col))
            supplement_headings.extend(((old_col, f"{label} (cũ)", 150), (new_col, f"{label} (mới)", 165)))
        self.reduction_supplement_tree = ttk.Treeview(
            supplement_frame, columns=supplement_columns, show="headings", selectmode="none")
        for key, title, width in supplement_headings:
            self.reduction_supplement_tree.heading(key, text=title)
            self.reduction_supplement_tree.column(key, width=width, anchor="center" if key == "select" else "w")
        self.reduction_supplement_tree.bind("<Button-1>", self._toggle_reduction_supplement_row_check)
        supplement_yscroll = ttk.Scrollbar(supplement_frame, orient="vertical", command=self.reduction_supplement_tree.yview)
        supplement_xscroll = ttk.Scrollbar(supplement_frame, orient="horizontal", command=self.reduction_supplement_tree.xview)
        self.reduction_supplement_tree.configure(yscrollcommand=supplement_yscroll.set,
                                                 xscrollcommand=supplement_xscroll.set)
        supplement_frame.rowconfigure(0, weight=1)
        supplement_frame.columnconfigure(0, weight=1)
        self.reduction_supplement_tree.grid(row=0, column=0, sticky="nsew")
        supplement_yscroll.grid(row=0, column=1, sticky="ns")
        supplement_xscroll.grid(row=1, column=0, sticky="ew")

    def _build_biography_tab(self, parent):
        ttk.Label(parent, text="Đối chiếu tóm tắt/hành vi vi phạm, số tiền án, tái phạm, nhân thân, phân đội và phân trại giữa hai DB. "
                  "Dân tộc/tôn giáo tra mã trong danh mục *_OLD, rồi nối cùng ID sang danh mục hiện hành. "
                  "Số tiền án và tái phạm lấy DB cũ làm chuẩn: DB cũ có thì điền/ghi đè khi DB mới khác; DB cũ trống thì giữ DB mới. Tái phạm dò MA_TAI_PHAM.MA sang DM_TAI_PHAMS.TP_MA để lấy ID. "
                  "Nhân thân được cập nhật theo DB cũ khi khác. Mã phân trại lấy từ 3 ký tự đầu MA_PHAN_DOI "
                  "và đối chiếu PT_MA trong trại; sau đó PD_MA được đối chiếu trong đúng phân trại cha. "
                  "phân trại được suy ra từ phân đội cha trong danh mục DB mới; phân đội/phân trại sẽ được cập nhật "
                  "nếu đang trống hoặc khác kết quả ánh xạ. "
                  "Dùng kết nối và mã trại phía trên; ghép theo HSLĐ, không tạo hồ sơ mới.",
                  wraplength=1000).pack(anchor="w", pady=(0, 8))
        field_options = ttk.LabelFrame(parent, text="Chọn cột cần kiểm tra và xử lý", padding=(8, 4))
        field_options.pack(fill="x", pady=(0, 6))
        for index, (column, label) in enumerate(BIOGRAPHY_FIELD_GROUPS):
            variable = tk.BooleanVar(value=True)
            self.biography_field_vars[column] = variable
            ttk.Checkbutton(field_options, text=label, variable=variable,
                            command=self._biography_options_changed).grid(
                                row=index // 3, column=index % 3, sticky="w", padx=(0, 18), pady=2)
        for column in range(3):
            field_options.columnconfigure(column, weight=1)
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(0, 6))
        self.biography_preview_button = ttk.Button(actions, text="Lấy xem trước", command=self._preview_biography_update)
        self.biography_preview_button.pack(side="left")
        self.biography_apply_button = ttk.Button(actions, text="Cập nhật dòng đã chọn",
                                                 command=lambda: self._apply_biography_update(selected_only=True), state="disabled")
        self.biography_apply_button.pack(side="left", padx=(8, 0))
        self.biography_all_button = ttk.Button(actions, text="Cập nhật toàn bộ",
                                               command=lambda: self._apply_biography_update(selected_only=False), state="disabled")
        self.biography_all_button.pack(side="left", padx=(8, 0))
        self.biography_selected_label = ttk.Label(actions, text="Đã chọn: 0 hồ sơ")
        self.biography_selected_label.pack(side="left", padx=(12, 0))
        self.biography_status = ttk.Label(parent, text="Chưa tải xem trước.", wraplength=1000)
        self.biography_status.pack(anchor="w", pady=(0, 6))
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        columns = ["select", "hsld", "status", "target_id"]
        headings = [("select", "Chọn", 55), ("hsld", "HSLĐ", 125),
                    ("status", "Trạng thái", 190), ("target_id", "ID lai lịch DB mới", 110)]
        for target_col, label in BIOGRAPHY_FIELD_GROUPS:
            old_col, new_col = f"{target_col}_old", f"{target_col}_new"
            columns.extend((old_col, new_col))
            headings.extend(((old_col, f"{label} (cũ)", 190), (new_col, f"{label} (mới)", 190)))
        self.biography_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="none")
        for key, title, width in headings:
            self.biography_tree.heading(key, text=title)
            self.biography_tree.column(key, width=width, anchor="center" if key == "select" else "w")
        self.biography_tree.bind("<Button-1>", self._toggle_biography_row_check)
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.biography_tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.biography_tree.xview)
        self.biography_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.biography_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

    def _build_execution_tab(self, parent):
        ttk.Label(parent, text="Đối chiếu thời gian tạm giam/tạm giữ trong lai lịch DB cũ với bản ghi thi hành án DB mới. "
                  "Ghép phạm nhân theo HSLĐ và lọc theo mã trại đã nhập. Giá trị DB mới chỉ được cập nhật khi khác với giá trị đã ánh xạ từ DB cũ.",
                  wraplength=1100).pack(anchor="w", pady=(0, 8))
        field_options = ttk.LabelFrame(parent, text="Chọn cột cần kiểm tra và xử lý", padding=(8, 4))
        field_options.pack(fill="x", pady=(0, 6))
        for index, (column, label) in enumerate(EXECUTION_DURATION_FIELD_GROUPS):
            variable = tk.BooleanVar(value=True)
            self.execution_field_vars[column] = variable
            ttk.Checkbutton(field_options, text=label, variable=variable,
                            command=self._execution_options_changed).grid(
                                row=0, column=index, sticky="w", padx=(0, 18), pady=2)
            field_options.columnconfigure(index, weight=1)
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(0, 6))
        self.execution_preview_button = ttk.Button(actions, text="Lấy xem trước", command=self._preview_execution_update)
        self.execution_preview_button.pack(side="left")
        self.execution_apply_button = ttk.Button(
            actions, text="Cập nhật dòng đã chọn",
            command=lambda: self._apply_execution_update(selected_only=True), state="disabled")
        self.execution_apply_button.pack(side="left", padx=(8, 0))
        self.execution_all_button = ttk.Button(
            actions, text="Cập nhật toàn bộ",
            command=lambda: self._apply_execution_update(selected_only=False), state="disabled")
        self.execution_all_button.pack(side="left", padx=(8, 0))
        self.execution_selected_label = ttk.Label(actions, text="Đã chọn: 0 hồ sơ")
        self.execution_selected_label.pack(side="left", padx=(12, 0))
        self.execution_status = ttk.Label(parent, text="Chưa tải xem trước.", wraplength=1100)
        self.execution_status.pack(anchor="w", pady=(0, 6))
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        columns = ["select", "hsld", "status", "target_id"]
        headings = [("select", "Chọn", 55), ("hsld", "HSLĐ", 125),
                    ("status", "Trạng thái", 240), ("target_id", "ID thi hành án DB mới", 140)]
        for target_col, label in EXECUTION_DURATION_FIELD_GROUPS:
            old_col, new_col = f"{target_col}_old", f"{target_col}_new"
            columns.extend((old_col, new_col))
            headings.extend(((old_col, f"{label} (cũ)", 180), (new_col, f"{label} (mới)", 180)))
        self.execution_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="none")
        for key, title, width in headings:
            self.execution_tree.heading(key, text=title)
            self.execution_tree.column(key, width=width, anchor="center" if key == "select" else "w")
        self.execution_tree.bind("<Button-1>", self._toggle_execution_row_check)
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.execution_tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.execution_tree.xview)
        self.execution_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.execution_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

    def _build_classification_tab(self, parent):
        ttk.Label(parent, text="Bổ sung xếp loại quý III và quý IV/2026 từ DB cũ vào các cột tương ứng đang trống "
                  "trên bản ghi năm 2026 ở DB mới. "
                  "Dùng kết nối và mã trại phía trên; ghép theo HSLĐ, không tạo bản ghi xếp loại mới.",
                  wraplength=1100).pack(anchor="w", pady=(0, 8))
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(0, 6))
        self.classification_preview_button = ttk.Button(
            actions, text="Lấy xem trước", command=self._preview_classification_update)
        self.classification_preview_button.pack(side="left")
        self.classification_apply_button = ttk.Button(
            actions, text="Cập nhật dòng đã chọn",
            command=lambda: self._apply_classification_update(selected_only=True), state="disabled")
        self.classification_apply_button.pack(side="left", padx=(8, 0))
        self.classification_all_button = ttk.Button(
            actions, text="Cập nhật toàn bộ",
            command=lambda: self._apply_classification_update(selected_only=False), state="disabled")
        self.classification_all_button.pack(side="left", padx=(8, 0))
        self.classification_selected_label = ttk.Label(actions, text="Đã chọn: 0 dòng")
        self.classification_selected_label.pack(side="left", padx=(12, 0))
        self.classification_status = ttk.Label(parent, text="Chưa tải xem trước.", wraplength=1100)
        self.classification_status.pack(anchor="w", pady=(0, 6))

        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        columns = ("select", "hsld", "status", "target_id", "old_code", "old_title", "new_value", "new_code", "new_title")
        self.classification_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="none")
        for key, title, width in (
                ("select", "Chọn", 55), ("hsld", "HSLĐ", 125), ("status", "Trạng thái", 290),
                ("target_id", "ID bản ghi DB mới", 125), ("old_code", "Mã xếp loại DB cũ", 130),
                ("old_title", "Xếp loại DB cũ", 200), ("new_value", "ID xếp loại DB mới", 140),
                ("new_code", "Mã danh mục mới", 130), ("new_title", "Tên xếp loại DB mới", 220)):
            self.classification_tree.heading(key, text=title)
            self.classification_tree.column(key, width=width, anchor="center" if key == "select" else "w")
        self.classification_tree.bind("<Button-1>", self._toggle_classification_row_check)
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.classification_tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.classification_tree.xview)
        self.classification_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.classification_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

    def _preview_classification_update(self):
        if self.busy:
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        self.classification_plan = None
        self.classification_item_ids.clear()
        self.classification_checked_items.clear()
        self._refresh_classification_apply_buttons()
        self.classification_status.configure(text="Đang đọc dữ liệu xếp loại DB cũ và DB mới ở chế độ chỉ đọc...")
        self._set_busy(True, "Đang lấy xem trước xếp loại quý III và quý IV...")
        threading.Thread(target=self._preview_classification_worker, args=configs, daemon=True).start()

    def _preview_classification_worker(self, old_cfg, new_cfg):
        try:
            plan = engine.preview_classification_update(old_cfg, new_cfg)
            self.events.put(("classification_preview", plan))
        except Exception as exc:
            self.events.put(("error", f"Không lấy được xem trước xếp loại: {exc}"))

    def _toggle_classification_row_check(self, event):
        if self.classification_tree.identify_column(event.x) != "#1":
            return
        item = self.classification_tree.identify_row(event.y)
        if not item or self.classification_item_ids.get(item) is None:
            return
        if item in self.classification_checked_items:
            self.classification_checked_items.remove(item)
            mark = "☐"
        else:
            self.classification_checked_items.add(item)
            mark = "☑"
        self.classification_tree.set(item, "select", mark)
        self._update_classification_selection_count()

    def _update_classification_selection_count(self):
        count = sum(1 for item in self.classification_checked_items
                    if self.classification_item_ids.get(item) is not None)
        self.classification_selected_label.configure(text=f"Đã chọn: {count:,} dòng")
        self._refresh_classification_apply_buttons()

    def _refresh_classification_apply_buttons(self):
        has_plan = bool(self.classification_plan and self.classification_plan.get("updates"))
        enabled = not self.busy and has_plan
        if hasattr(self, "classification_apply_button"):
            has_selection = any(self.classification_item_ids.get(item) is not None
                                for item in self.classification_checked_items)
            self.classification_apply_button.configure(state="normal" if enabled and has_selection else "disabled")
            self.classification_all_button.configure(state="normal" if enabled else "disabled")

    def _apply_classification_update(self, selected_only):
        if self.busy or not self.classification_plan or not self.classification_plan.get("updates"):
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        selected_ids = ({self.classification_item_ids[item] for item in self.classification_checked_items
                         if self.classification_item_ids.get(item) is not None} if selected_only else None)
        if selected_only and not selected_ids:
            messagebox.showwarning("Chưa chọn dòng", "Hãy tick ít nhất một dòng trong bảng xem trước.")
            return
        rows = [row for row in self.classification_plan["updates"]
                if selected_ids is None or (row["id"], row["quarter"]) in selected_ids]
        prison_code = self.classification_plan["prison_scope"]["code"]
        scope = "các dòng đã chọn" if selected_only else "toàn bộ dòng hợp lệ trong xem trước"
        if not messagebox.askyesno(
                "Xác nhận cập nhật xếp loại",
                f"Sẽ điền xếp loại quý III/quý IV năm 2026 vào {len(rows):,} ô xếp loại ({scope}) của trại {prison_code}. "
                "Chỉ cập nhật bản ghi năm 2026 đang trống; giá trị đã có được giữ nguyên. Tiếp tục ghi DB mới?"):
            return
        old_cfg, new_cfg = configs
        plan = self.classification_plan
        self._set_busy(True, "Đang cập nhật xếp loại quý III và quý IV...")
        self.classification_status.configure(text="Đang ghi DB mới. Nếu dữ liệu khác xem trước hoặc phát sinh lỗi, transaction sẽ rollback.")
        threading.Thread(target=self._apply_classification_worker,
                         args=(old_cfg, new_cfg, plan, selected_ids), daemon=True).start()

    def _apply_classification_worker(self, old_cfg, new_cfg, plan, selected_ids):
        try:
            result = engine.apply_classification_update(old_cfg, new_cfg, plan, selected_ids)
            self.events.put(("classification_done", result))
        except Exception as exc:
            self.events.put(("error", f"Không cập nhật được xếp loại quý III/quý IV: {exc}"))

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
        group_label = self.pick_group_var.get()
        groups = {g for g, label in GROUP_LABELS.items() if group_label == "Tất cả cụm" or label == group_label}
        prefixes = set()
        for dataset in self.menu_datasets:
            if dataset.get("group") in groups:
                prefixes.add((dataset["group"], menu_prefix(dataset["code"])))
        ordered = []
        for group in ("LAI_LICH", "DIEN_BIEN", "KET_THUC"):
            if group not in groups:
                continue
            ordered.extend((group, prefix) for prefix in MENU_ORDER[group] if (group, prefix) in prefixes)
        name_counts = {}
        for group, prefix in ordered:
            name = MENU_NAMES.get(prefix, prefix)
            name_counts[name] = name_counts.get(name, 0) + 1
        self.selection_options = {
            (f"{GROUP_LABELS[group]} · {MENU_NAMES.get(prefix, prefix)}"
             if name_counts[MENU_NAMES.get(prefix, prefix)] > 1 else MENU_NAMES.get(prefix, prefix)): (group, prefix)
            for group, prefix in ordered
        }
        labels = ["Tất cả màn hình", *self.selection_options.keys()]
        self.pick_dataset["values"] = labels
        if self.pick_dataset_var.get() not in labels:
            self.pick_dataset_var.set("Tất cả màn hình")
        self._refresh_selected_list()

    def _refresh_selected_list(self, _event=None):
        self.selected_list.delete(0, "end")
        selected_group = self.pick_group_var.get()
        groups = {g for g, label in GROUP_LABELS.items() if selected_group == "Tất cả cụm" or label == selected_group}
        selected_screen = self.pick_dataset_var.get()
        selected_scope = self.selection_options.get(selected_screen)
        chosen = [s for s in self.menu_datasets if s.get("group") in groups
                  and (selected_scope is None or (s.get("group"), menu_prefix(s["code"])) == selected_scope)]
        group_order = {g: i for i, g in enumerate(("LAI_LICH", "DIEN_BIEN", "KET_THUC"))}
        chosen.sort(key=lambda s: (group_order.get(s["group"], 9),
                                   MENU_ORDER.get(s["group"], []).index(menu_prefix(s["code"])) if menu_prefix(s["code"]) in MENU_ORDER.get(s["group"], []) else 999,
                                   s["name"], s["code"]))
        for dataset in chosen:
            self.selected_list.insert("end", f"{GROUP_LABELS.get(dataset['group'], dataset['group'])} · {dataset['name']}")
        self.selected_count_label.configure(text=f"Bảng dữ liệu trong phạm vi chạy ({len(chosen)})")
        self.scope_datasets = chosen

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
        selected = list(getattr(self, "scope_datasets", []))
        if not selected:
            messagebox.showwarning("Chưa có màn hình", "Phạm vi chọn hiện không có màn hình để đối soát.")
            return
        path = self.out_var.get().strip()
        if not path.lower().endswith(".xlsx"):
            messagebox.showwarning("File chưa đúng", "Chọn tên file có đuôi .xlsx.")
            return
        self.cancel_event.clear()
        self._set_busy(True, "Đang đối soát...")
        scope_hint = f"; phạm vi trại {new_cfg['prison_code']}" if new_cfg.get("prison_code") else "; tự nhận diện mã trại từ DB cũ"
        self.progress_label.configure(text=f"Bắt đầu chạy {len(selected)} mapping; ghép hồ sơ theo HSLĐ{scope_hint}.")
        threading.Thread(target=self._run_worker, args=(old_cfg, new_cfg, selected, path), daemon=True).start()

    def _run_worker(self, old_cfg, new_cfg, selected, path):
        try:
            result = engine.run_comparison(old_cfg, new_cfg, selected,
                progress=lambda i, n, name: self.events.put(("progress", i, n, name)), cancel=self.cancel_event)
            report_path, spill_paths = write_report(path, result, old_cfg, new_cfg, len(selected))
            self.events.put(("done", result, report_path, spill_paths))
        except InterruptedError:
            self.events.put(("cancelled",))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _valid_connection_inputs(self):
        old_cfg, new_cfg = self._cfg("old"), self._cfg("new")
        for label, cfg in (("cũ", old_cfg), ("mới", new_cfg)):
            if not cfg["dsn"] or not cfg["user"] or not cfg["password"]:
                messagebox.showwarning("Thiếu thông tin", f"Nhập DSN, user, mật khẩu DB {label}.")
                return None
            if "/" not in cfg["dsn"]:
                messagebox.showwarning("DSN chưa đủ", f"DSN DB {label} cần dạng host:port/service.")
                return None
        return old_cfg, new_cfg

    def _preview_reduction_update(self):
        if self.busy:
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        old_cfg, new_cfg = configs
        self.reduction_plan = None
        self._set_busy(True, "Đang tải xem trước giảm thời hạn...")
        self.cancel_button.configure(state="disabled")
        self.reduction_status.configure(text="Đang đọc DB cũ và DB mới ở chế độ chỉ đọc...")
        threading.Thread(target=self._preview_reduction_worker, args=(old_cfg, new_cfg), daemon=True).start()

    def _preview_reduction_worker(self, old_cfg, new_cfg):
        try:
            self.events.put(("reduction_preview", engine.preview_reduction_update(old_cfg, new_cfg)))
        except Exception as exc:
            self.events.put(("error", f"Không lấy được xem trước giảm thời hạn: {exc}"))

    def _toggle_reduction_row_check(self, event):
        if self.reduction_tree.identify_column(event.x) != "#1":
            return
        item = self.reduction_tree.identify_row(event.y)
        if not item or self.reduction_item_ids.get(item) is None:
            return
        if item in self.reduction_checked_items:
            self.reduction_checked_items.remove(item)
            mark = "☐"
        else:
            self.reduction_checked_items.add(item)
            mark = "☑"
        self.reduction_tree.set(item, "select", mark)
        self._update_reduction_selection_count()

    def _update_reduction_selection_count(self):
        count = sum(1 for item in self.reduction_checked_items if self.reduction_item_ids.get(item) is not None)
        self.reduction_selected_label.configure(text=f"Đã chọn: {count:,} dòng")
        self._refresh_reduction_apply_buttons()

    def _refresh_reduction_apply_buttons(self):
        has_plan = bool(self.reduction_plan and self.reduction_plan.get("updates"))
        enabled = not self.busy and has_plan
        if hasattr(self, "reduction_apply_button"):
            self.reduction_apply_button.configure(
                state="normal" if enabled and any(self.reduction_item_ids.get(i) is not None for i in self.reduction_checked_items) else "disabled")
            self.reduction_all_button.configure(state="normal" if enabled else "disabled")

    def _apply_reduction_update(self, selected_only):
        if self.busy or not self.reduction_plan or not self.reduction_plan.get("updates"):
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        selected_ids = ({self.reduction_item_ids[item] for item in self.reduction_checked_items
                         if self.reduction_item_ids.get(item) is not None} if selected_only else None)
        if selected_only and not selected_ids:
            messagebox.showwarning("Chưa chọn dòng", "Hãy chọn ít nhất một dòng trong bảng xem trước.")
            return
        selected_fields = {(row["id"], column) for row in self.reduction_plan["updates"]
                           if selected_ids is None or row["id"] in selected_ids
                           for column in row["fields"]}
        if not selected_fields:
            messagebox.showwarning("Không có trường để cập nhật", "Các dòng đã chọn không có trường trống hoặc MUC_GIAM_ID/DIA_PHUONG_ID sai cần sửa.")
            return
        if not selected_only:
            selected_fields = None
            field_count = self.reduction_plan["field_count"]
            row_count = len(self.reduction_plan["updates"])
        else:
            field_count = len(selected_fields)
            row_count = len({target_id for target_id, _ in selected_fields})
        prison_code = self.reduction_plan["prison_scope"]["code"]
        scope = "các dòng đã chọn" if selected_only else "toàn bộ dòng trong xem trước"
        if not messagebox.askyesno("Xác nhận cập nhật",
                                   f"Sẽ cập nhật {field_count:,} trường trên {row_count:,} dòng giảm thời hạn "
                                   f"({scope}) của trại {prison_code}. Các trường đã có được giữ nguyên, "
                                   "ngoại trừ MUC_GIAM_ID và DIA_PHUONG_ID khác mapping sẽ được sửa. "
                                   "Tiếp tục ghi DB mới?"):
            return
        old_cfg, new_cfg = configs
        plan = self.reduction_plan
        self._set_busy(True, "Đang cập nhật giảm thời hạn...")
        self.cancel_button.configure(state="disabled")
        self.reduction_status.configure(text="Đang ghi dữ liệu. Nếu có dòng không còn khớp xem trước, toàn bộ transaction sẽ rollback.")
        threading.Thread(target=self._apply_reduction_worker,
                         args=(old_cfg, new_cfg, plan, selected_fields), daemon=True).start()

    def _apply_reduction_worker(self, old_cfg, new_cfg, plan, selected_fields):
        try:
            result = engine.apply_reduction_update(old_cfg, new_cfg, plan, selected_fields)
            self.events.put(("reduction_done", result))
        except Exception as exc:
            self.events.put(("error", f"Không cập nhật được giảm thời hạn: {exc}"))

    def _preview_reduction_supplement(self):
        if self.busy:
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        old_cfg, new_cfg = configs
        self.reduction_supplement_plan = None
        self.reduction_supplement_item_ids.clear()
        self.reduction_supplement_checked_items.clear()
        self.reduction_supplement_selected_label.configure(text="Đã chọn: 0 dòng")
        for item in self.reduction_supplement_tree.get_children():
            self.reduction_supplement_tree.delete(item)
        self._set_busy(True, "Đang tải xem trước dòng giảm thời hạn cần bổ sung...")
        self.reduction_supplement_status.configure(text="Đang đọc DB cũ và DB mới ở chế độ chỉ đọc...")
        threading.Thread(target=self._preview_reduction_supplement_worker,
                         args=(old_cfg, new_cfg), daemon=True).start()

    def _preview_reduction_supplement_worker(self, old_cfg, new_cfg):
        try:
            self.events.put(("reduction_supplement_preview",
                             engine.preview_reduction_supplement(old_cfg, new_cfg)))
        except Exception as exc:
            self.events.put(("error", f"Không lấy được xem trước bổ sung giảm thời hạn: {exc}"))

    def _toggle_reduction_supplement_row_check(self, event):
        if self.reduction_supplement_tree.identify_column(event.x) != "#1":
            return
        item = self.reduction_supplement_tree.identify_row(event.y)
        if not item or self.reduction_supplement_item_ids.get(item) is None:
            return
        if item in self.reduction_supplement_checked_items:
            self.reduction_supplement_checked_items.remove(item)
            mark = "☐"
        else:
            self.reduction_supplement_checked_items.add(item)
            mark = "☑"
        self.reduction_supplement_tree.set(item, "select", mark)
        self._update_reduction_supplement_selection_count()

    def _update_reduction_supplement_selection_count(self):
        count = sum(1 for item in self.reduction_supplement_checked_items
                    if self.reduction_supplement_item_ids.get(item) is not None)
        self.reduction_supplement_selected_label.configure(text=f"Đã chọn: {count:,} dòng")
        self._refresh_reduction_supplement_buttons()

    def _refresh_reduction_supplement_buttons(self):
        has_rows = bool(self.reduction_supplement_plan and self.reduction_supplement_plan.get("inserts"))
        enabled = not self.busy and has_rows
        if hasattr(self, "reduction_supplement_preview_button"):
            self.reduction_supplement_preview_button.configure(state="disabled" if self.busy else "normal")
            self.reduction_supplement_apply_button.configure(
                state="normal" if enabled and any(
                    self.reduction_supplement_item_ids.get(item) is not None
                    for item in self.reduction_supplement_checked_items) else "disabled")
            self.reduction_supplement_all_button.configure(state="normal" if enabled else "disabled")

    def _apply_reduction_supplement(self, selected_only):
        if self.busy or not self.reduction_supplement_plan or not self.reduction_supplement_plan.get("inserts"):
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        selected_keys = ({self.reduction_supplement_item_ids[item]
                          for item in self.reduction_supplement_checked_items
                          if self.reduction_supplement_item_ids.get(item) is not None}
                         if selected_only else None)
        if selected_only and not selected_keys:
            messagebox.showwarning("Chưa chọn dòng", "Hãy chọn ít nhất một dòng cần bổ sung trong bảng xem trước.")
            return
        if selected_only:
            row_count = sum(1 for row in self.reduction_supplement_plan["inserts"]
                            if row["insert_key"] in selected_keys)
        else:
            row_count = len(self.reduction_supplement_plan["inserts"])
        prison_code = self.reduction_supplement_plan["prison_scope"]["code"]
        scope = "các dòng đã chọn" if selected_only else "toàn bộ dòng trong xem trước"
        if not messagebox.askyesno(
                "Xác nhận bổ sung",
                f"Sẽ tạo {row_count:,} dòng giảm thời hạn mới ({scope}) cho trại {prison_code}. "
                "Các mức đề nghị, BCA duyệt và Tòa quyết định được ánh xạ riêng; "
                "dòng có mapping không duy nhất đã bị loại khỏi danh sách bổ sung. Tiếp tục ghi DB mới?"):
            return
        old_cfg, new_cfg = configs
        plan = self.reduction_supplement_plan
        self._set_busy(True, "Đang bổ sung dòng giảm thời hạn...")
        self.reduction_supplement_status.configure(
            text="Đang ghi dữ liệu. Nếu dữ liệu lệch preview hoặc có lỗi, toàn bộ transaction sẽ rollback.")
        threading.Thread(target=self._apply_reduction_supplement_worker,
                         args=(old_cfg, new_cfg, plan, selected_keys), daemon=True).start()

    def _apply_reduction_supplement_worker(self, old_cfg, new_cfg, plan, selected_keys):
        try:
            result = engine.apply_reduction_supplement(old_cfg, new_cfg, plan, selected_keys)
            self.events.put(("reduction_supplement_done", result))
        except Exception as exc:
            self.events.put(("error", f"Không bổ sung được giảm thời hạn: {exc}"))

    def _preview_biography_update(self):
        if self.busy:
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        self.biography_plan = None
        self.biography_item_ids.clear()
        self.biography_checked_items.clear()
        self._refresh_biography_apply_buttons()
        self.biography_status.configure(text="Đang đọc lai lịch DB cũ và DB mới ở chế độ chỉ đọc...")
        selected_fields = self._selected_biography_fields()
        if not selected_fields:
            messagebox.showwarning("Chưa chọn cột", "Hãy tick ít nhất một cột cần kiểm tra.")
            return
        self._set_busy(True, "Đang lấy xem trước cập nhật lai lịch...")
        threading.Thread(target=self._preview_biography_worker,
                         args=(*configs, selected_fields), daemon=True).start()

    def _selected_biography_fields(self):
        return {column for column, variable in self.biography_field_vars.items() if variable.get()}

    def _biography_options_changed(self):
        # A preview is bound to its exact field selection; require a new preview
        # after the user changes options so an old plan cannot be applied.
        self.biography_plan = None
        self.biography_item_ids.clear()
        self.biography_checked_items.clear()
        for item in self.biography_tree.get_children():
            self.biography_tree.delete(item)
        self.biography_selected_label.configure(text="Đã chọn: 0 hồ sơ")
        if hasattr(self, "biography_status"):
            self.biography_status.configure(text="Tùy chọn cột đã đổi. Hãy lấy xem trước lại.")
        self._refresh_biography_apply_buttons()

    def _preview_biography_worker(self, old_cfg, new_cfg, selected_fields):
        try:
            self.events.put(("biography_preview", engine.preview_biography_update(old_cfg, new_cfg, selected_fields)))
        except Exception as exc:
            self.events.put(("error", f"Không lấy được xem trước cập nhật lai lịch: {exc}"))

    def _toggle_biography_row_check(self, event):
        if self.biography_tree.identify_column(event.x) != "#1":
            return
        item = self.biography_tree.identify_row(event.y)
        if not item or self.biography_item_ids.get(item) is None:
            return
        if item in self.biography_checked_items:
            self.biography_checked_items.remove(item)
            mark = "☐"
        else:
            self.biography_checked_items.add(item)
            mark = "☑"
        self.biography_tree.set(item, "select", mark)
        self._update_biography_selection_count()

    def _update_biography_selection_count(self):
        count = sum(1 for item in self.biography_checked_items if self.biography_item_ids.get(item) is not None)
        self.biography_selected_label.configure(text=f"Đã chọn: {count:,} hồ sơ")
        self._refresh_biography_apply_buttons()

    def _refresh_biography_apply_buttons(self):
        has_plan = bool(self.biography_plan and self.biography_plan.get("updates"))
        enabled = not self.busy and has_plan
        if hasattr(self, "biography_apply_button"):
            self.biography_apply_button.configure(
                state="normal" if enabled and any(self.biography_item_ids.get(i) is not None for i in self.biography_checked_items) else "disabled")
            self.biography_all_button.configure(state="normal" if enabled else "disabled")

    def _apply_biography_update(self, selected_only):
        if self.busy or not self.biography_plan or not self.biography_plan.get("updates"):
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        selected_ids = ({self.biography_item_ids[item] for item in self.biography_checked_items
                         if self.biography_item_ids.get(item) is not None} if selected_only else None)
        if selected_only and not selected_ids:
            messagebox.showwarning("Chưa chọn hồ sơ", "Hãy tick ít nhất một hồ sơ trong bảng xem trước.")
            return
        rows = [row for row in self.biography_plan["updates"]
                if selected_ids is None or row["id"] in selected_ids]
        field_count = sum(len(row["fields"]) + len(row.get("unit_fields", {}))
                          + len(row.get("tha_fields", {})) for row in rows)
        if not field_count:
            messagebox.showwarning("Không có trường để cập nhật", "Hồ sơ đã chọn không có trường nào cần cập nhật.")
            return
        prison_code = self.biography_plan["prison_scope"]["code"]
        scope = "các hồ sơ đã chọn" if selected_only else "toàn bộ hồ sơ trong xem trước"
        if not messagebox.askyesno("Xác nhận cập nhật",
                                   f"Sẽ cập nhật {field_count:,} trường trên {len(rows):,} hồ sơ ({scope}) của trại {prison_code}. "
                                   "Tóm tắt/hành vi chỉ điền khi DB mới đang trống; phân đội/phân trại chỉ điền khi DB mới đang trống. Tiếp tục ghi DB mới?"):
            return
        old_cfg, new_cfg = configs
        plan = self.biography_plan
        self._set_busy(True, "Đang cập nhật lai lịch...")
        self.cancel_button.configure(state="disabled")
        self.biography_status.configure(text="Đang ghi dữ liệu. Nếu hồ sơ thay đổi so với xem trước, toàn bộ transaction sẽ rollback.")
        threading.Thread(target=self._apply_biography_worker,
                         args=(old_cfg, new_cfg, plan, selected_ids, plan["selected_fields"]), daemon=True).start()

    def _apply_biography_worker(self, old_cfg, new_cfg, plan, selected_ids, selected_fields):
        try:
            result = engine.apply_biography_update(old_cfg, new_cfg, plan, selected_ids, selected_fields)
            self.events.put(("biography_done", result))
        except Exception as exc:
            self.events.put(("error", f"Không cập nhật được lai lịch: {exc}"))

    def _selected_execution_fields(self):
        return {column for column, variable in self.execution_field_vars.items() if variable.get()}

    def _execution_options_changed(self):
        self.execution_plan = None
        self.execution_item_ids.clear()
        self.execution_checked_items.clear()
        for item in self.execution_tree.get_children():
            self.execution_tree.delete(item)
        self.execution_selected_label.configure(text="Đã chọn: 0 hồ sơ")
        self.execution_status.configure(text="Tùy chọn cột đã đổi. Hãy lấy xem trước lại.")
        self._refresh_execution_apply_buttons()

    def _preview_execution_update(self):
        if self.busy:
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        selected_fields = self._selected_execution_fields()
        if not selected_fields:
            messagebox.showwarning("Chưa chọn cột", "Hãy tick ít nhất một cột thời gian cần kiểm tra.")
            return
        self.execution_plan = None
        self.execution_item_ids.clear()
        self.execution_checked_items.clear()
        self._refresh_execution_apply_buttons()
        self.execution_status.configure(text="Đang đối chiếu lai lịch DB cũ với thi hành án DB mới ở chế độ chỉ đọc...")
        self._set_busy(True, "Đang lấy xem trước cập nhật thi hành án...")
        threading.Thread(target=self._preview_execution_worker,
                         args=(*configs, selected_fields), daemon=True).start()

    def _preview_execution_worker(self, old_cfg, new_cfg, selected_fields):
        try:
            plan = engine.preview_biography_update(old_cfg, new_cfg, selected_fields)
            self.events.put(("execution_preview", plan))
        except Exception as exc:
            self.events.put(("error", f"Không lấy được xem trước thi hành án: {exc}"))

    def _toggle_execution_row_check(self, event):
        if self.execution_tree.identify_column(event.x) != "#1":
            return
        item = self.execution_tree.identify_row(event.y)
        if not item or self.execution_item_ids.get(item) is None:
            return
        if item in self.execution_checked_items:
            self.execution_checked_items.remove(item)
            mark = "☐"
        else:
            self.execution_checked_items.add(item)
            mark = "☑"
        self.execution_tree.set(item, "select", mark)
        self._update_execution_selection_count()

    def _update_execution_selection_count(self):
        count = sum(1 for item in self.execution_checked_items if self.execution_item_ids.get(item) is not None)
        self.execution_selected_label.configure(text=f"Đã chọn: {count:,} hồ sơ")
        self._refresh_execution_apply_buttons()

    def _refresh_execution_apply_buttons(self):
        enabled = not self.busy and bool(self.execution_plan and self.execution_plan.get("updates"))
        if hasattr(self, "execution_apply_button"):
            has_selected = any(self.execution_item_ids.get(item) is not None
                               for item in self.execution_checked_items)
            self.execution_apply_button.configure(state="normal" if enabled and has_selected else "disabled")
            self.execution_all_button.configure(state="normal" if enabled else "disabled")

    def _apply_execution_update(self, selected_only):
        if self.busy or not self.execution_plan or not self.execution_plan.get("updates"):
            return
        configs = self._valid_connection_inputs()
        if not configs:
            return
        selected_ids = ({self.execution_item_ids[item] for item in self.execution_checked_items
                         if self.execution_item_ids.get(item) is not None} if selected_only else None)
        if selected_only and not selected_ids:
            messagebox.showwarning("Chưa chọn hồ sơ", "Hãy tick ít nhất một hồ sơ trong bảng xem trước.")
            return
        rows = [row for row in self.execution_plan["updates"]
                if selected_ids is None or row["id"] in selected_ids]
        field_count = sum(len(row.get("tha_fields", {})) for row in rows)
        if not field_count:
            messagebox.showwarning("Không có trường để cập nhật", "Hồ sơ đã chọn không có cột thời gian cần cập nhật.")
            return
        prison_code = self.execution_plan["prison_scope"]["code"]
        scope = "các hồ sơ đã chọn" if selected_only else "toàn bộ hồ sơ trong xem trước"
        if not messagebox.askyesno(
                "Xác nhận cập nhật",
                f"Sẽ cập nhật {field_count:,} trường thời gian trên {len(rows):,} hồ sơ ({scope}) của trại {prison_code}. "
                "Chỉ các cột đã tick mới được xử lý; giá trị được lấy từ DB cũ sau khi ánh xạ. Tiếp tục ghi DB mới?"):
            return
        old_cfg, new_cfg = configs
        plan = self.execution_plan
        selected_fields = plan["selected_fields"]
        self._set_busy(True, "Đang cập nhật thi hành án...")
        self.cancel_button.configure(state="disabled")
        self.execution_status.configure(text="Đang ghi dữ liệu. Nếu dữ liệu thay đổi so với preview, toàn bộ transaction sẽ rollback.")
        threading.Thread(target=self._apply_execution_worker,
                         args=(old_cfg, new_cfg, plan, selected_ids, selected_fields), daemon=True).start()

    def _apply_execution_worker(self, old_cfg, new_cfg, plan, selected_ids, selected_fields):
        try:
            result = engine.apply_biography_update(old_cfg, new_cfg, plan, selected_ids, selected_fields)
            self.events.put(("execution_done", result))
        except Exception as exc:
            self.events.put(("error", f"Không cập nhật được thi hành án: {exc}"))

    def _set_busy(self, value, status):
        self.busy = value
        self.run_button.configure(state="disabled" if value else "normal")
        self.cancel_button.configure(state="normal" if value else "disabled")
        if hasattr(self, "reduction_preview_button"):
            self.reduction_preview_button.configure(state="disabled" if value else "normal")
            self._refresh_reduction_apply_buttons()
        if hasattr(self, "reduction_supplement_preview_button"):
            self.reduction_supplement_preview_button.configure(state="disabled" if value else "normal")
            self._refresh_reduction_supplement_buttons()
        if hasattr(self, "biography_preview_button"):
            self.biography_preview_button.configure(state="disabled" if value else "normal")
            self._refresh_biography_apply_buttons()
        if hasattr(self, "same_schema_preview_button"):
            self.same_schema_preview_button.configure(state="disabled" if value else "normal")
            self._refresh_same_schema_buttons()
        if hasattr(self, "execution_preview_button"):
            self.execution_preview_button.configure(state="disabled" if value else "normal")
            self._refresh_execution_apply_buttons()
        if hasattr(self, "classification_preview_button"):
            self.classification_preview_button.configure(state="disabled" if value else "normal")
            self._refresh_classification_apply_buttons()
        if hasattr(self, "province_audit_button"):
            self.province_audit_button.configure(state="disabled" if value else "normal")
        if hasattr(self, "ward_catalog_preview_button"):
            self.ward_catalog_preview_button.configure(state="disabled" if value else "normal")
            self.ward_catalog_insert_button.configure(state="disabled" if value or not self.ward_catalog_plan or not any(r["insertable"] for r in self.ward_catalog_plan["rows"]) else "normal")
        if hasattr(self, "location_preview_button"):
            self.location_preview_button.configure(state="disabled" if value else "normal")
            self._refresh_location_buttons()
        self.progress_label.configure(text=status)

    def _poll(self):
        while not self.events.empty():
            event = self.events.get()
            if event[0] == "test_ok":
                _, side, info = event
                self._set_busy(False, "")
                messagebox.showinfo("Kết nối thành công", f"DB: {info[0]}\nSchema: {info[1]}\nGiờ DB: {info[2]}")
            elif event[0] == "progress":
                _, i, n, label = event
                self.progress_label.configure(text=f"{i}/{n}: {label}")
            elif event[0] == "done":
                _, result, path, spill_paths = event
                self.result = result
                self._show_summary(result)
                affected_people = {(row.get("code"), row.get("hsld"), row.get("old_person_id"), row.get("new_person_id"))
                                   for row in result.get("details", [])}
                detail_count = len(affected_people)
                self._set_busy(False, f"Hoàn tất • {detail_count} phạm nhân/bảng cần rà soát")
                extra = "\n\nMột số sheet vượt giới hạn Excel; dữ liệu đầy đủ nằm trong file CSV:\n" + "\n".join(spill_paths) if spill_paths else ""
                prison_scope = result.get("prison_scope", {})
                prison_code = prison_scope.get("code", "")
                prison_name = prison_scope.get("name", "")
                scope_label = f"{prison_name} - {prison_code}".strip(" -")
                scope = f"\nPhạm vi trại: {scope_label}" if scope_label else ""
                messagebox.showinfo("Đã hoàn tất", f"Đã xuất báo cáo 3 sheet (Tổng quan, Đối soát số lượng, Chi tiết sai lệch):\n{path}{scope}\n\nSố phạm nhân/bảng cần rà soát: {detail_count}{extra}")
            elif event[0] == "reduction_preview":
                _, plan = event
                self.reduction_plan = plan
                self.reduction_item_ids.clear()
                self.reduction_checked_items.clear()
                self.reduction_selected_label.configure(text="Đã chọn: 0 dòng")
                for item in self.reduction_tree.get_children():
                    self.reduction_tree.delete(item)
                preview_rows = []
                issues_by_target = {}
                for issue in plan["issues"]:
                    target_id = issue.get("target_id")
                    if target_id is not None:
                        issues_by_target.setdefault(target_id, []).append(issue)
                update_ids = set()
                for row in plan["updates"]:
                    values = {"hsld": row["hsld"], "date": row["ngay_xet"], "target_id": row["id"]}
                    for field in row["display"]:
                        values[f"{field['field']}_old"] = field["old"]
                        values[f"{field['field']}_new"] = field["new"]
                    for column, _label in REDUCTION_FIELD_GROUPS:
                        values.setdefault(f"{column}_old", "")
                        values.setdefault(f"{column}_new", "")
                    row_issues = issues_by_target.get(row["id"], [])
                    for issue in row_issues:
                        field = issue.get("field")
                        if field:
                            values[f"{field}_old"] = issue.get("source_value", "")
                            values[f"{field}_new"] = issue.get("target_value", "")
                    status_parts = [f"Sẽ cập nhật {len(row['fields'])} trường"]
                    status_parts.extend(issue["status"] for issue in row_issues)
                    values["status"] = " • ".join(status_parts)
                    values["row_id"] = row["id"]
                    preview_rows.append(values)
                    update_ids.add(row["id"])
                for issue in plan["issues"]:
                    # A matched reduction record with other eligible fields stays
                    # on one preview row; attach its mapping warning there.
                    if issue.get("target_id") in update_ids:
                        continue
                    values = {"hsld": issue.get("hsld", ""), "date": issue.get("ngay_xet", ""),
                              "target_id": issue.get("target_id", ""), "status": issue["status"], "row_id": None}
                    for column, _label in REDUCTION_FIELD_GROUPS:
                        values[f"{column}_old"] = ""
                        values[f"{column}_new"] = ""
                    field = issue.get("field")
                    if field:
                        values[f"{field}_old"] = issue.get("source_value", "")
                        values[f"{field}_new"] = issue.get("target_value", "")
                    preview_rows.append(values)
                preview_rows.sort(key=lambda row: (not bool(row["hsld"]), str(row["hsld"] or "").casefold(),
                                                   str(row["date"]), str(row["target_id"])))
                shown = min(5000, len(preview_rows))
                for row in preview_rows[:shown]:
                    row_values = {column: row.get(column, "") for column in self.reduction_tree["columns"]}
                    row_values["select"] = "☐" if row["row_id"] is not None else ""
                    item = self.reduction_tree.insert("", "end", values=tuple(row_values.get(column, "") for column in self.reduction_tree["columns"]))
                    self.reduction_item_ids[item] = row["row_id"]
                extra = " (chỉ hiện 5.000 dòng đầu trong lưới)" if len(preview_rows) > 5000 else ""
                self.reduction_status.configure(text=(
                    f"Trại {plan['prison_scope']['code']} • {len(plan['updates']):,} dòng đích, "
                    f"{plan['field_count']:,} trường sẽ được cập nhật • {len(plan['issues']):,} vấn đề cần rà soát{extra}. "
                    "Chưa ghi dữ liệu."
                ))
                self._set_busy(False, "Đã tải xem trước giảm thời hạn.")
            elif event[0] == "reduction_done":
                _, result = event
                self.reduction_plan = None
                self.reduction_item_ids.clear()
                self.reduction_checked_items.clear()
                self.reduction_selected_label.configure(text="Đã chọn: 0 dòng")
                self.reduction_status.configure(text=(
                    f"Đã cập nhật {result['updated_fields']:,} trường trên {result['updated_rows']:,} dòng "
                    f"của trại {result['prison_scope']['code']}."
                ))
                self._set_busy(False, "Cập nhật giảm thời hạn hoàn tất.")
                messagebox.showinfo("Cập nhật hoàn tất", self.reduction_status.cget("text"))
            elif event[0] == "reduction_supplement_preview":
                _, plan = event
                self.reduction_supplement_plan = plan
                self.reduction_supplement_item_ids.clear()
                self.reduction_supplement_checked_items.clear()
                self.reduction_supplement_selected_label.configure(text="Đã chọn: 0 dòng")
                for item in self.reduction_supplement_tree.get_children():
                    self.reduction_supplement_tree.delete(item)
                preview_rows = []
                for row in plan["inserts"]:
                    values = {"hsld": row["hsld"], "date": row["ngay_xet"],
                              "status": "Sẽ tạo dòng mới", "row_id": row["insert_key"]}
                    for field in row["display"]:
                        values[f"{field['field']}_old"] = field["old"]
                        values[f"{field['field']}_new"] = field["new"]
                    for column, _label in REDUCTION_INSERT_FIELD_GROUPS:
                        values.setdefault(f"{column}_old", "")
                        values.setdefault(f"{column}_new", "")
                    preview_rows.append(values)
                for issue in plan["issues"]:
                    values = {"hsld": issue.get("hsld", ""), "date": issue.get("ngay_xet", ""),
                              "status": issue["status"], "row_id": None}
                    for column, _label in REDUCTION_INSERT_FIELD_GROUPS:
                        values[f"{column}_old"] = ""
                        values[f"{column}_new"] = ""
                    preview_rows.append(values)
                preview_rows.sort(key=lambda row: (row["row_id"] is None,
                                                   str(row["hsld"] or "").casefold(),
                                                   str(row["date"]), row["status"]))
                shown = min(5000, len(preview_rows))
                for row in preview_rows[:shown]:
                    row_values = {column: row.get(column, "")
                                  for column in self.reduction_supplement_tree["columns"]}
                    row_values["select"] = "☐" if row["row_id"] is not None else ""
                    item = self.reduction_supplement_tree.insert(
                        "", "end", values=tuple(row_values.get(column, "")
                                                 for column in self.reduction_supplement_tree["columns"]))
                    self.reduction_supplement_item_ids[item] = row["row_id"]
                extra = " (chỉ hiện 5.000 dòng đầu trong lưới)" if len(preview_rows) > 5000 else ""
                self.reduction_supplement_status.configure(text=(
                    f"Trại {plan['prison_scope']['code']} • {len(plan['inserts']):,} dòng sẽ bổ sung • "
                    f"{len(plan['issues']):,} dòng cần rà soát/không thể bổ sung{extra}. Chưa ghi dữ liệu."))
                self._set_busy(False, "Đã tải xem trước bổ sung giảm thời hạn.")
            elif event[0] == "reduction_supplement_done":
                _, result = event
                self.reduction_supplement_plan = None
                self.reduction_supplement_item_ids.clear()
                self.reduction_supplement_checked_items.clear()
                for item in self.reduction_supplement_tree.get_children():
                    self.reduction_supplement_tree.delete(item)
                self.reduction_supplement_selected_label.configure(text="Đã chọn: 0 dòng")
                self.reduction_supplement_status.configure(text=(
                    f"Đã bổ sung {result['inserted_rows']:,} dòng giảm thời hạn cho trại "
                    f"{result['prison_scope']['code']}."))
                self._set_busy(False, "Bổ sung giảm thời hạn hoàn tất.")
                messagebox.showinfo("Bổ sung hoàn tất", self.reduction_supplement_status.cget("text"))
            elif event[0] == "biography_preview":
                _, plan = event
                if self._selected_biography_fields() != set(plan.get("selected_fields", [])):
                    self.biography_status.configure(text="Tùy chọn cột đã đổi trong lúc tải. Hãy lấy xem trước lại.")
                    self._set_busy(False, "Preview cũ đã bỏ vì tùy chọn cột thay đổi.")
                    continue
                self.biography_plan = plan
                self.biography_item_ids.clear()
                self.biography_checked_items.clear()
                self.biography_selected_label.configure(text="Đã chọn: 0 hồ sơ")
                for item in self.biography_tree.get_children():
                    self.biography_tree.delete(item)
                preview_rows = []
                for row in plan["updates"]:
                    field_labels = {
                        "LL_TOM_TAT_HV": "Tóm tắt hành vi",
                        "LL_CHI_TIET_HV": "Hành vi vi phạm",
                        "LL_SO_TIEN_AN": "Số tiền án",
                        "LL_NHAN_THAN": "Nhân thân",
                        "LL_TAI_PHAM": "Tái phạm",
                        "LL_PHAN_DOI_ID": "Phân đội",
                        "LL_PHAN_TRAI_ID": "Phân trại",
                    }
                    update_columns = [*row["fields"], *row.get("unit_fields", {}), *row.get("tha_fields", {})]
                    update_names = [field_labels.get(column, column) for column in update_columns]
                    status = f"Sẽ cập nhật {len(update_names)} trường: {', '.join(update_names)}"
                    if row.get("warnings"):
                        status += " • " + "; ".join(row["warnings"])
                    values = {"hsld": row["hsld"], "target_id": row["id"], "status": status}
                    for field in row["display"]:
                        values[f"{field['field']}_old"] = field["old"]
                        values[f"{field['field']}_new"] = field["new"]
                    values["row_id"] = row["id"]
                    preview_rows.append(values)
                for issue in plan["issues"]:
                    values = {"hsld": issue.get("hsld", ""), "target_id": "", "status": issue["status"], "row_id": None}
                    for column, _label in BIOGRAPHY_FIELD_GROUPS:
                        values[f"{column}_old"] = ""
                        values[f"{column}_new"] = ""
                    for field in issue.get("display", []):
                        values[f"{field['field']}_old"] = field.get("old", "")
                        values[f"{field['field']}_new"] = field.get("new", "")
                    preview_rows.append(values)
                # Show actionable rows first; unmatched/ambiguous HSLĐ rows follow
                # with their reason visible near the left edge of the grid.
                preview_rows.sort(key=lambda row: (row["row_id"] is None, not bool(row["hsld"]),
                                                   str(row["hsld"] or "").casefold(), str(row["target_id"])))
                shown = min(5000, len(preview_rows))
                for row in preview_rows[:shown]:
                    row_values = {column: row.get(column, "") for column in self.biography_tree["columns"]}
                    row_values["select"] = "☐" if row["row_id"] is not None else ""
                    item = self.biography_tree.insert("", "end", values=tuple(row_values.get(column, "") for column in self.biography_tree["columns"]))
                    self.biography_item_ids[item] = row["row_id"]
                extra = " (chỉ hiện 5.000 dòng đầu trong lưới)" if len(preview_rows) > 5000 else ""
                self.biography_status.configure(text=(
                    f"Trại {plan['prison_scope']['code']} • {len(plan['updates']):,} hồ sơ có trường cần cập nhật, "
                    f"{plan['field_count']:,} trường • {len(plan['issues']):,} hồ sơ cần rà soát{extra}. Chưa ghi DB mới."
                ))
                self._set_busy(False, "Đã tải xem trước cập nhật lai lịch.")
            elif event[0] == "biography_done":
                _, result = event
                self.biography_plan = None
                self.biography_item_ids.clear()
                self.biography_checked_items.clear()
                self.biography_selected_label.configure(text="Đã chọn: 0 hồ sơ")
                self.biography_status.configure(text=(
                    f"Đã cập nhật {result['updated_fields']:,} trường trên {result['updated_rows']:,} hồ sơ "
                    f"của trại {result['prison_scope']['code']}."
                ))
                self._set_busy(False, "Cập nhật lai lịch hoàn tất.")
                messagebox.showinfo("Cập nhật hoàn tất", self.biography_status.cget("text"))
            elif event[0] == "same_schema_preview":
                _, plan = event
                self.same_schema_plan = plan
                self.same_schema_item_ids.clear(); self.same_schema_checked_items.clear()
                self.same_schema_selected_label.configure(text="Đã chọn: 0 hồ sơ")
                for item in self.same_schema_tree.get_children(): self.same_schema_tree.delete(item)
                rows = [{**r, "status": "Sẽ cập nhật " + ", ".join(
                    name for col, name in (("LL_PHAN_DOI_ID", "phân đội"), ("LL_PHAN_TRAI_ID", "phân trại")) if col in r["fields"]), "row_id": r["id"]} for r in plan["updates"]]
                rows.extend({"hsld": i.get("hsld", ""), "status": i["status"], "row_id": None,
                             "team_old": "", "team_new": "", "branch_old": "", "branch_new": "", "target_id": ""} for i in plan["issues"])
                rows.sort(key=lambda r: (r["row_id"] is None, str(r.get("hsld", "")).casefold()))
                for row in rows[:5000]:
                    values = ("☐" if row["row_id"] is not None else "", row.get("hsld", ""), row.get("status", ""),
                              row.get("id", ""), row.get("team_old", ""), row.get("team_new", ""), row.get("branch_old", ""), row.get("branch_new", ""))
                    item = self.same_schema_tree.insert("", "end", values=values)
                    self.same_schema_item_ids[item] = row["row_id"]
                extra = " (lưới hiển thị tối đa 5.000 dòng)" if len(rows) > 5000 else ""
                self.same_schema_status.configure(text=(f"Trại {plan['prison_scope']['code']} • {len(plan['updates']):,} hồ sơ lệch, "
                    f"{plan['field_count']:,} trường sẽ cập nhật • {len(plan['issues']):,} dòng cần rà soát{extra}. Chưa ghi DB mới."))
                self._set_busy(False, "Đã tải xem trước lai lịch không chuyển đổi.")
            elif event[0] == "same_schema_done":
                _, result = event
                self.same_schema_plan = None; self.same_schema_item_ids.clear(); self.same_schema_checked_items.clear()
                for item in self.same_schema_tree.get_children(): self.same_schema_tree.delete(item)
                self.same_schema_selected_label.configure(text="Đã chọn: 0 hồ sơ")
                self.same_schema_status.configure(text=(
                    f"Đã COMMIT {result['updated_fields']:,} trường trên {result['updated_rows']:,} hồ sơ "
                    f"của trại {result['prison_scope']['code']}. Hãy lấy xem trước lại để xác nhận DB mới đã khớp."))
                self._set_busy(False, "Cập nhật lai lịch không chuyển đổi hoàn tất.")
                messagebox.showinfo("Cập nhật hoàn tất", self.same_schema_status.cget("text"))
            elif event[0] == "execution_preview":
                _, plan = event
                if self._selected_execution_fields() != set(plan.get("selected_fields", [])):
                    self.execution_status.configure(text="Tùy chọn cột đã đổi trong lúc tải. Hãy lấy xem trước lại.")
                    self._set_busy(False, "Preview cũ đã bỏ vì tùy chọn cột thay đổi.")
                    continue
                self.execution_plan = plan
                self.execution_item_ids.clear()
                self.execution_checked_items.clear()
                self.execution_selected_label.configure(text="Đã chọn: 0 hồ sơ")
                for item in self.execution_tree.get_children():
                    self.execution_tree.delete(item)
                field_labels = dict(EXECUTION_DURATION_FIELD_GROUPS)
                preview_rows = []
                for row in plan["updates"]:
                    update_columns = list(row.get("tha_fields", {}))
                    update_names = [field_labels.get(column, column) for column in update_columns]
                    status = f"Sẽ cập nhật {len(update_names)} trường: {', '.join(update_names)}"
                    if row.get("warnings"):
                        status += " • " + "; ".join(row["warnings"])
                    values = {"hsld": row["hsld"], "target_id": row.get("tha_id") or "", "status": status,
                              "row_id": row["id"]}
                    for field in row["display"]:
                        if field["field"] in field_labels:
                            values[f"{field['field']}_old"] = field["old"]
                            values[f"{field['field']}_new"] = field["new"]
                    preview_rows.append(values)
                for issue in plan["issues"]:
                    values = {"hsld": issue.get("hsld", ""), "target_id": "",
                              "status": issue["status"], "row_id": None}
                    preview_rows.append(values)
                preview_rows.sort(key=lambda row: (row["row_id"] is None,
                                                   str(row["hsld"] or "").casefold(),
                                                   str(row["target_id"])))
                shown = min(5000, len(preview_rows))
                for row in preview_rows[:shown]:
                    row_values = {column: row.get(column, "") for column in self.execution_tree["columns"]}
                    row_values["select"] = "☐" if row["row_id"] is not None else ""
                    item = self.execution_tree.insert(
                        "", "end", values=tuple(row_values.get(column, "")
                                                 for column in self.execution_tree["columns"]))
                    self.execution_item_ids[item] = row["row_id"]
                extra = " (chỉ hiện 5.000 dòng đầu trong lưới)" if len(preview_rows) > 5000 else ""
                self.execution_status.configure(text=(
                    f"Trại {plan['prison_scope']['code']} • {len(plan['updates']):,} hồ sơ có thời gian cần cập nhật, "
                    f"{plan['field_count']:,} trường • {len(plan['issues']):,} hồ sơ cần rà soát{extra}. Chưa ghi DB mới."
                ))
                self._set_busy(False, "Đã tải xem trước cập nhật thi hành án.")
            elif event[0] == "execution_done":
                _, result = event
                self.execution_plan = None
                self.execution_item_ids.clear()
                self.execution_checked_items.clear()
                self.execution_selected_label.configure(text="Đã chọn: 0 hồ sơ")
                self.execution_status.configure(text=(
                    f"Đã cập nhật {result['updated_fields']:,} trường thời gian trên {result['updated_rows']:,} hồ sơ "
                    f"của trại {result['prison_scope']['code']}."
                ))
                self._set_busy(False, "Cập nhật thi hành án hoàn tất.")
                messagebox.showinfo("Cập nhật hoàn tất", self.execution_status.cget("text"))
            elif event[0] == "classification_preview":
                _, plan = event
                self.classification_plan = plan
                self.classification_item_ids.clear()
                self.classification_checked_items.clear()
                self.classification_selected_label.configure(text="Đã chọn: 0 dòng")
                for item in self.classification_tree.get_children():
                    self.classification_tree.delete(item)
                preview_rows = []
                for row in plan["updates"]:
                    preview_rows.append({
                        "row_id": (row["id"], row["quarter"]), "hsld": row["hsld"],
                        "status": f"Sẽ điền {row['quarter_label']}/2026", "target_id": row["id"],
                        "old_code": row["old_code"], "old_title": row["old_title"],
                        "new_value": row["new_value"], "new_code": row["new_code"],
                        "new_title": row["new_title"],
                    })
                for issue in plan["issues"]:
                    preview_rows.append({
                        "row_id": None, "hsld": issue.get("hsld", ""),
                        "status": issue["status"], "target_id": issue.get("target_id", ""),
                        "old_code": issue.get("old_code", ""), "old_title": "",
                        "new_value": issue.get("new_value", ""), "new_code": "", "new_title": "",
                    })
                preview_rows.sort(key=lambda row: (row["row_id"] is None, not bool(row["hsld"]),
                                                   str(row["hsld"] or "").casefold(), str(row["target_id"])))
                shown = min(5000, len(preview_rows))
                for row in preview_rows[:shown]:
                    values = {column: row.get(column, "") for column in self.classification_tree["columns"]}
                    values["select"] = "☐" if row["row_id"] is not None else ""
                    item = self.classification_tree.insert(
                        "", "end", values=tuple(values.get(column, "") for column in self.classification_tree["columns"]))
                    self.classification_item_ids[item] = row["row_id"]
                extra = " (chỉ hiện 5.000 dòng đầu trong lưới)" if len(preview_rows) > 5000 else ""
                self.classification_status.configure(
                    text=(f"Trại {plan['prison_scope']['code']} • {len(plan['updates']):,} dòng đủ điều kiện cập nhật, "
                          f"{len(plan['issues']):,} dòng cần rà soát{extra}. Chưa ghi DB mới."))
                self._set_busy(False, "Đã tải xem trước xếp loại quý III và quý IV.")
            elif event[0] == "classification_done":
                _, result = event
                self.classification_plan = None
                self.classification_item_ids.clear()
                self.classification_checked_items.clear()
                self.classification_selected_label.configure(text="Đã chọn: 0 dòng")
                self.classification_status.configure(
                    text=(f"Đã cập nhật {result['updated_rows']:,} ô xếp loại quý III/quý IV năm 2026 "
                          f"của trại {result['prison_scope']['code']}."))
                self._set_busy(False, "Cập nhật xếp loại hoàn tất.")
                messagebox.showinfo("Cập nhật hoàn tất", self.classification_status.cget("text"))
            elif event[0] == "province_audit_preview":
                _, result = event
                for item in self.province_audit_tree.get_children():
                    self.province_audit_tree.delete(item)
                rows = result["rows"]
                for row in rows[:10000]:
                    self.province_audit_tree.insert("", "end", values=(row["old_code"], row["old_name"],
                                                                         row["new_code"], row["new_name"], row["status"]))
                counts = result["counts"]
                suffix = " (lưới hiển thị 10.000 dòng đầu)" if len(rows) > 10000 else ""
                self.province_audit_status.configure(
                    text=(f"{result['old_count']:,} mã MA_DP • "
                          f"{counts.get('Mã cũ không có ở DB mới', 0):,} không có ở DB mới • "
                          f"{counts.get('Cùng mã nhưng khác tên', 0):,} cùng mã nhưng khác tên • "
                          f"{counts.get('Mã DB mới bị trùng', 0):,} mã mới bị trùng{suffix}"))
                self._set_busy(False, "Đã đối chiếu danh mục tỉnh/thành phố.")
            elif event[0] == "ward_catalog_preview":
                _, result = event
                self.ward_catalog_plan = result
                for item in self.ward_catalog_tree.get_children():
                    self.ward_catalog_tree.delete(item)
                for row in result["rows"][:10000]:
                    result_text = row["result"]
                    if row.get("province_warning") and row["insertable"]:
                        result_text = "Cảnh báo: MA_QH không có trong TTP_MA"
                    province_display = row["province_code"]
                    self.ward_catalog_tree.insert("", "end", values=(row["code"], province_display, row["name"],
                        row["status"], "SYSTIMESTAMP", row["deleted"], result_text))
                extra = " (lưới hiển thị 10.000 dòng đầu)" if len(result["rows"]) > 10000 else ""
                self.ward_catalog_status.configure(text=(f"{result['old_count']:,} dòng DB cũ • {len(result['rows']):,} mã thiếu • "
                    f"{result['ready_count']:,} dòng insert được • {result['issue_count']:,} dòng cần rà soát{extra}. Chưa ghi DB mới."))
                self._set_busy(False, "Đã preview danh mục xã/phường.")
            elif event[0] == "ward_catalog_done":
                _, result = event
                self.ward_catalog_plan = None
                self.ward_catalog_status.configure(text=(f"Đã COMMIT {result['inserted']:,} dòng; bỏ qua {result['skipped']:,} mã đã có "
                    f"trong DB mới. Hãy Preview lại để xác nhận."))
                self._set_busy(False, "Insert danh mục xã/phường hoàn tất.")
                messagebox.showinfo("Insert hoàn tất", self.ward_catalog_status.cget("text"))
            elif event[0] == "location_preview":
                _, plan = event
                self.location_plan = plan
                self.location_checked_items.clear()
                self.location_item_update_index.clear()
                for item in self.location_tree.get_children(): self.location_tree.delete(item)
                update_indexes = {}
                for index, update in enumerate(plan["updates"]):
                    update_indexes[(update["screen"], engine.norm_text(update["id"]), update["column"])] = index
                status_labels = {
                    "READY": "Sẵn sàng cập nhật", "ALREADY_CORRECT": "Đã đúng",
                    "UNMAPPED_CODE": "Không có mã tương ứng", "AMBIGUOUS_CODE": "Mã đích bị trùng",
                    "AMBIGUOUS_MAPPING": "Mã nguồn trùng trong CSV", "MAPPING_NOT_APPROVED": "Mapping chưa duyệt",
                    "INVALID_MAPPING_ROW": "Dòng CSV thiếu mã", "SOURCE_CODE_NOT_FOUND": "Không tìm thấy mã cũ",
                    "SOURCE_CODE_NOT_UNIQUE": "Mã cũ không duy nhất", "TARGET_CODE_NOT_FOUND": "Không tìm thấy mã giữ",
                    "TARGET_CODE_NOT_UNIQUE": "Mã giữ không duy nhất", "SOURCE_EQUALS_TARGET": "Hai mã cùng ID",
                    "NO_REFERENCES": "Không có FK Lai lịch đang dùng mã này",
                    "EMPTY_SOURCE": "Mã nguồn trống", "NO_UNIQUE_ROW_KEY": "Không có khóa dòng duy nhất",
                    "DUPLICATE_OR_MISSING_EVENT_KEY": "Khóa sự kiện thiếu/trùng",
                }
                for row in plan["rows"][:10000]:
                    update_index = update_indexes.get((row["screen"], row.get("row_id", ""), row["target_column"])) if row["status"] == "READY" else None
                    values = ("☐" if update_index is not None else "", row["screen_name"], row.get("hsld", ""), row["key"],
                              row["source_column"], row["source_code"], row.get("target_code", ""), row["target_column"], row["current_id"], row["target_id"],
                              row["target_name"], status_labels.get(row["status"], row["status"]))
                    item = self.location_tree.insert("", "end", values=values)
                    if update_index is not None:
                        self.location_item_update_index[item] = update_index
                counts = plan["counts"]
                summaries = "; ".join(f'{s["name"]}: {s["message"]}' for s in plan["screens"])
                suffix = " (chỉ hiển thị 10.000 dòng đầu)" if len(plan["rows"]) > 10000 else ""
                self.location_status.configure(text=(
                    f'Trại {plan["prison_scope"]["code"]} • {counts.get("READY", 0):,} sẵn sàng • '
                    f'{counts.get("ALREADY_CORRECT", 0):,} đã đúng • {counts.get("UNMAPPED_CODE", 0):,} không map • '
                    f'{counts.get("AMBIGUOUS_CODE", 0):,} mã trùng • {counts.get("NO_UNIQUE_ROW_KEY", 0)+counts.get("DUPLICATE_OR_MISSING_EVENT_KEY", 0):,} thiếu/trùng khóa. '
                    f'{summaries}{suffix}'))
                self.location_selected_label.configure(text="Đã chọn: 0 dòng")
                self._set_busy(False, "Đã tải preview convert địa phương; chưa ghi DB.")
            elif event[0] == "location_done":
                _, result = event
                self.location_plan = None
                self.location_checked_items.clear()
                self.location_item_update_index.clear()
                self.location_selected_label.configure(text="Đã chọn: 0 dòng")
                self.location_status.configure(text=(
                    f'Đã cập nhật {result["updated"]:,} trường địa phương của trại '
                    f'{result["prison_scope"].get("code", "")}. Hãy preview lại để đối soát. '
                    f'Audit: {result.get("audit_path", "")}. {result.get("audit_error", "")}'))
                self._set_busy(False, "Cập nhật địa phương hoàn tất.")
                messagebox.showinfo("Cập nhật hoàn tất", self.location_status.cget("text"))
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
        self.result_dataset["values"] = ["Tất cả màn", *self.result_options.keys()]
        self.result_dataset_var.set("Tất cả màn")
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
