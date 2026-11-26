"""Standalone GUI: map old-database court/province codes to new-database IDs."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

import engine
import mapping as M

TITLE = "Convert địa phương DB cũ → DB mới"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TITLE)
        width = min(1580, max(1100, self.winfo_screenwidth() - 100))
        height = min(900, max(650, self.winfo_screenheight() - 100))
        self.geometry(f"{width}x{height}")
        self.minsize(1000, 600)
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.plan = None
        self.selected_screen = tk.StringVar()
        self.update_by_item = {}
        self.checked = set()
        self.fields = {side: {} for side in ("old", "new")}
        self._build()
        self.after(100, self._poll)

    def _build(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=25, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        outer = ttk.Frame(self, padding=10)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer,
            text="Mỗi lần chọn một màn/bảng. Mỗi dòng preview là một bản ghi DB; mỗi cột động hiển thị riêng một trường địa danh cần rà/cập nhật.",
            wraplength=1450, justify="left").pack(anchor="w", pady=(0, 8))
        conn_frame = ttk.Frame(outer)
        conn_frame.pack(fill="x", pady=(0, 6))
        for col, side, title in ((0, "old", "DB CŨ — chỉ đọc"), (1, "new", "DB MỚI — preview / cập nhật")):
            box = ttk.LabelFrame(conn_frame, text=title, padding=8)
            box.grid(row=0, column=col, sticky="nsew", padx=4)
            conn_frame.columnconfigure(col, weight=1)
            entries = (("dsn", "DSN (host:port/service)", False), ("user", "User", False),
                       ("password", "Mật khẩu", True), ("schema", "Schema (tùy chọn)", False))
            for row, (key, label, secret) in enumerate(entries):
                ttk.Label(box, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
                var = tk.StringVar()
                ttk.Entry(box, textvariable=var, show="*" if secret else "").grid(row=row, column=1, sticky="ew", pady=2)
                self.fields[side][key] = var
            box.columnconfigure(1, weight=1)
            ttk.Button(box, text="Kiểm tra kết nối", command=lambda s=side: self._test(s)).grid(
                row=len(entries), column=1, sticky="e", pady=(5, 0))
        scope = ttk.LabelFrame(outer, text="Phạm vi trại", padding=7)
        scope.pack(fill="x", pady=(0, 6))
        ttk.Label(scope, text="DB cũ: toàn bộ dữ liệu của trại nguồn (DB chỉ có một trại). Không cần nhập mã trại cũ.").grid(row=0,column=0,columnspan=2,sticky="w")
        ttk.Label(scope, text="Mã trại DB mới (TG_MA):").grid(row=0,column=2,sticky="w",padx=(18,0))
        self.new_prison = tk.StringVar()
        ttk.Entry(scope, textvariable=self.new_prison, width=22).grid(row=0,column=3,sticky="w",padx=6)

        screens_box = ttk.LabelFrame(outer, text="Chọn một màn/bảng cho mỗi lần preview", padding=6)
        screens_box.pack(fill="x", pady=(0, 6))
        for index, screen in enumerate(M.SCREENS):
            if index == 0:
                self.selected_screen.set(screen["code"])
            ttk.Radiobutton(screens_box, text=screen["name"], variable=self.selected_screen,
                value=screen["code"]).grid(
                row=index//4, column=index%4, sticky="w", padx=5, pady=2)

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 5))
        self.preview_button = ttk.Button(actions, text="Lấy preview", command=self._preview)
        self.preview_button.pack(side="left")
        self.apply_selected_button = ttk.Button(actions, text="Cập nhật bản ghi chọn", command=lambda:self._apply(True),state="disabled")
        self.apply_selected_button.pack(side="left", padx=(7,0))
        self.apply_all_button = ttk.Button(actions, text="Cập nhật tất cả READY", command=lambda:self._apply(False),state="disabled")
        self.apply_all_button.pack(side="left", padx=(7,0))
        ttk.Button(actions, text="Hủy truy vấn", command=self.cancel.set).pack(side="left", padx=(7,0))
        self.selected_label = ttk.Label(actions, text="Đã chọn: 0 bản ghi")
        self.selected_label.pack(side="left", padx=10)
        self.status = ttk.Label(outer, text="Chưa preview. Tool chỉ ghi các cột địa danh đã khai báo.", wraplength=1450)
        self.status.pack(anchor="w", pady=(0,5))

        columns=("pick","screen","hsld","oldpid","newpid","rowid","event","status")
        table_frame=ttk.Frame(outer)
        table_frame.pack(fill="both",expand=True)
        self.tree=ttk.Treeview(table_frame,columns=columns,show="headings",selectmode="none")
        labels=(
            ("pick","Chọn",42),("screen","Màn / bảng",190),("hsld","Số HSLĐ",105),
            ("oldpid","ID hồ sơ cũ",110),("newpid","ID hồ sơ mới",110),("rowid","ID bản ghi mới",110),
            ("event","Khóa bản ghi",180),
            ("status","Trạng thái",190))
        for key,label,colwidth in labels:
            self.tree.heading(key,text=label)
            self.tree.column(key,width=colwidth,anchor="w",stretch=(key in {"screen","event","status"}))
        self.tree.bind("<Button-1>",self._toggle_row)
        y=ttk.Scrollbar(table_frame,orient="vertical",command=self.tree.yview)
        x=ttk.Scrollbar(table_frame,orient="horizontal",command=self.tree.xview)
        self.tree.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        table_frame.rowconfigure(0,weight=1);table_frame.columnconfigure(0,weight=1)
        self.tree.grid(row=0,column=0,sticky="nsew");y.grid(row=0,column=1,sticky="ns");x.grid(row=1,column=0,sticky="ew")

    def _cfg(self, side):
        return {key:var.get().strip() for key,var in self.fields[side].items()}

    def _test(self, side):
        if self.busy: return
        cfg=self._cfg(side)
        self._set_busy(True,f"Đang kiểm tra kết nối DB {'cũ' if side=='old' else 'mới'}...")
        threading.Thread(target=self._test_worker,args=(side,cfg),daemon=True).start()

    def _test_worker(self, side, cfg):
        try:
            schema=engine.test_connection(cfg,side)
            self.events.put(("test_ok",side,schema))
        except Exception as exc:
            self.events.put(("error",f"Kiểm tra DB {'cũ' if side=='old' else 'mới'} thất bại: {exc}"))

    def _preview(self):
        if self.busy:return
        old_cfg,new_cfg=self._cfg("old"),self._cfg("new")
        if not all(old_cfg.get(k) for k in ("dsn","user")) or not all(new_cfg.get(k) for k in ("dsn","user")):
            messagebox.showwarning("Thiếu kết nối","Nhập DSN và user cho cả DB cũ lẫn DB mới.");return
        selected=[self.selected_screen.get()] if self.selected_screen.get() else []
        if not selected:
            messagebox.showwarning("Chưa chọn màn","Chọn ít nhất một màn/bảng cần preview.");return
        if not self.new_prison.get().strip():
            messagebox.showwarning("Thiếu mã trại","Nhập TG_MA của trại trong DB mới để giới hạn hồ sơ.");return
        self.plan=None;self.checked.clear();self.update_by_item.clear()
        for item in self.tree.get_children():self.tree.delete(item)
        self.cancel.clear();self._set_busy(True,"Đang ghép hồ sơ và lập preview; DB cũ chỉ đọc...")
        threading.Thread(target=self._preview_worker,args=(old_cfg,new_cfg,selected,self.new_prison.get().strip()),daemon=True).start()

    def _preview_worker(self,old_cfg,new_cfg,selected,new_code):
        try:
            plan=engine.preview(old_cfg,new_cfg,selected,new_code,self.cancel)
            self.events.put(("preview_ok",plan))
        except InterruptedError:self.events.put(("cancelled",))
        except Exception as exc:self.events.put(("error",f"Không lập được preview: {exc}"))

    def _toggle_row(self,event):
        if self.tree.identify_column(event.x)!="#1":return
        item=self.tree.identify_row(event.y)
        if not item or item not in self.update_by_item:return
        if item in self.checked:
            self.checked.remove(item);self.tree.set(item,"pick","☐")
        else:
            self.checked.add(item);self.tree.set(item,"pick","☑")
        self.selected_label.configure(text=f"Đã chọn: {len(self.checked):,} bản ghi")
        self._refresh_buttons()

    def _refresh_buttons(self):
        ready=bool(self.plan and self.plan.get("updates"))
        self.apply_all_button.configure(state="normal" if ready and not self.busy else "disabled")
        self.apply_selected_button.configure(state="normal" if ready and self.checked and not self.busy else "disabled")

    def _fit_preview_columns(self):
        measure=tkfont.Font(self, family="Segoe UI", size=9).measure
        for column in self.tree["columns"]:
            width=measure(self.tree.heading(column,"text"))+36
            for item in self.tree.get_children(""):
                width=max(width,measure(str(self.tree.set(item,column)))+36)
            self.tree.column(column,width=width,stretch=False)

    def _apply(self,selected_only):
        if self.busy or not self.plan:return
        indexes={index for item in self.checked for index in self.update_by_item.get(item,set())} if selected_only else None
        updates=self.plan.get("updates",[])
        chosen=[u for i,u in enumerate(updates) if indexes is None or i in indexes]
        if not chosen:
            messagebox.showwarning("Chưa chọn dòng","Chọn dòng READY hoặc dùng nút cập nhật tất cả READY.");return
        summary=(f"Sẽ cập nhật {len(chosen):,} trường địa danh trên DB mới "
                 f"(trại {self.plan['prison_scope']['new_code']}). DB cũ chỉ đọc. Tiếp tục?")
        if not messagebox.askyesno("Xác nhận cập nhật",summary):return
        self._set_busy(True,"Đang cập nhật DB mới trong một transaction...")
        new_cfg=self._cfg("new")
        threading.Thread(target=self._apply_worker,args=(new_cfg,self.plan,indexes),daemon=True).start()

    def _apply_worker(self,cfg,plan,indexes):
        try:self.events.put(("apply_ok",engine.apply_updates(cfg,plan,indexes)))
        except Exception as exc:self.events.put(("error",f"Cập nhật thất bại; transaction đã rollback nếu chưa commit: {exc}"))

    def _set_busy(self,value,message=None):
        self.busy=value
        if message:self.status.configure(text=message)
        self.preview_button.configure(state="disabled" if value else "normal")
        self._refresh_buttons()

    def _render(self,plan):
        screen_code=plan["screens"][0]["code"] if plan.get("screens") else ""
        screen=next((item for item in M.SCREENS if item["code"]==screen_code),None)
        location_fields=screen["fields"] if screen else []
        base_columns=("pick","screen","hsld","oldpid","newpid","rowid","event")
        field_columns=tuple(f"field_{index}" for index in range(len(location_fields)))
        columns=(*base_columns,*field_columns,"status")
        self.tree.configure(columns=columns)
        base_labels=(("pick","Chọn",42),("screen","Màn / bảng",190),("hsld","Số HSLĐ",105),
            ("oldpid","ID hồ sơ cũ",110),("newpid","ID hồ sơ mới",110),("rowid","ID bản ghi mới",110),
            ("event","Khóa bản ghi",180))
        for key,label,width in base_labels:
            self.tree.heading(key,text=label)
            self.tree.column(key,width=width,anchor="w",stretch=(key in {"screen","event"}))
        for key,field in zip(field_columns,location_fields):
            self.tree.heading(key,text=f"{field['source']} → {field['target']}")
            self.tree.column(key,width=440,anchor="w",stretch=True)
        self.tree.heading("status",text="Trạng thái")
        self.tree.column("status",width=190,anchor="w",stretch=True)

        ward_statuses={"WARD_PARENT_EMPTY","WARD_NAME_NOT_FOUND","WARD_NAME_NOT_UNIQUE",
            "WARD_CODE_NOT_FOUND","WARD_CODE_NOT_UNIQUE"}
        visible_statuses={"READY","CODE_NOT_FOUND","CODE_NOT_UNIQUE","EVENT_KEY_NOT_UNIQUE",
            "ROW_NOT_UNIQUE","SCHEMA_MISSING",*ward_statuses}
        groups={}
        for row in plan["rows"]:
            if row.get("status") not in visible_statuses:
                continue
            identity=row.get("row_id") or row.get("source_row_key") or row.get("event_key")
            if not identity:
                identity=f"issue:{row.get('status')}:{row.get('note')}"
            key=(row.get("screen"),row.get("old_person_id"),row.get("new_person_id"),identity)
            groups.setdefault(key,[]).append(row)

        for rows in groups.values():
            first=rows[0]
            update_indexes={r["update_index"] for r in rows if r.get("update_index") is not None}
            field_values={}
            statuses=[]
            for row in rows:
                status=row.get("status","")
                statuses.append(status)
                if row.get("source_kind")=="ward":
                    old_code=(f"Mã xã/phường cũ {row.get('old_code')}" if row.get("old_code")
                              else f"Tên xã/phường cũ {row.get('old_name') or '(trống)'}")
                    if row.get("old_code") and row.get("old_name"):
                        old_code+=f" ({row['old_name']})"
                else:
                    old_code=f"Mã cũ {row.get('old_code')}"
                    if row.get("old_name"):old_code+=f" ({row['old_name']})"
                if status=="READY":
                    current=f"ID {row.get('current_id') or '(trống)'}"
                    if row.get("current_id") and row.get("current_name"):current+=f" ({row['current_name']})"
                    target=f"{row.get('target_id')}"
                    if row.get("target_name"):target+=f" ({row['target_name']})"
                    detail=f"{old_code}; {current} → {target}"
                else:
                    current=f"ID {row.get('current_id') or '(trống)'}"
                    if row.get("current_id") and row.get("current_name"):current+=f" ({row['current_name']})"
                    detail=old_code
                    detail+=f"; {current}; chưa xác định ID mới — {status}: {row.get('note','')}"
                field_values.setdefault(row.get("target_field"),[]).append(detail)
            status_summary=", ".join(f"{name}: {statuses.count(name)}" for name in dict.fromkeys(statuses))
            field_cells=[" | ".join(field_values.get(field["target"],[])) for field in location_fields]
            vals=("☐" if update_indexes else "",first.get("screen_name",""),first.get("hsld",""),
                first.get("old_person_id",""),first.get("new_person_id",""),first.get("row_id",""),
                first.get("event_key",""),*field_cells,status_summary)
            item=self.tree.insert("","end",values=vals)
            if update_indexes:self.update_by_item[item]=update_indexes
        self._fit_preview_columns()
        ready=len(plan["updates"])
        errors=sum(1 for r in plan["rows"] if r.get("status") in {
            "CODE_NOT_FOUND","CODE_NOT_UNIQUE","EVENT_KEY_NOT_UNIQUE","ROW_NOT_UNIQUE","SCHEMA_MISSING",*ward_statuses})
        scope=plan["prison_scope"]
        self.status.configure(text=(f"Preview xong: bảng {screen['name'] if screen else screen_code}; {len(groups):,} bản ghi lệch/cần rà; "
            f"{ready:,} trường READY; {errors:,} lỗi/không ghép được. "
            f"Toàn bộ DB cũ → trại mới {scope['new_code']} ({scope['new_name']}). "
            f"Bản ghi đúng/trùng và mã nguồn trống được ẩn, không cập nhật."))
        self.selected_label.configure(text="Đã chọn: 0 bản ghi")
        self._refresh_buttons()

    def _poll(self):
        try:
            while True:
                event=self.events.get_nowait()
                kind=event[0]
                if kind=="test_ok":
                    self._set_busy(False,f"Kết nối DB {'cũ' if event[1]=='old' else 'mới'} thành công. Schema: {event[2]}")
                    messagebox.showinfo("Kết nối thành công",f"Kết nối DB {'cũ' if event[1]=='old' else 'mới'} thành công.\nSchema: {event[2]}")
                elif kind=="preview_ok":
                    self.plan=event[1];self._render(self.plan);self._set_busy(False)
                elif kind=="apply_ok":
                    result=event[1];self.plan=None;self.checked.clear();self.update_by_item.clear()
                    message=(f"Đã cập nhật {result['updated']:,} trường vào DB mới.\nAudit: {result['audit_path']}")
                    if result.get("audit_error"):
                        message += "\n\n" + result["audit_error"]
                        self._set_busy(False,message)
                        messagebox.showwarning("Đã cập nhật DB",message)
                    else:
                        self._set_busy(False,message)
                        messagebox.showinfo("Hoàn tất",message)
                elif kind=="cancelled":
                    self._set_busy(False,"Đã hủy truy vấn; DB chưa bị cập nhật.")
                elif kind=="error":
                    self._set_busy(False,event[1]);messagebox.showerror("Có lỗi",event[1])
        except queue.Empty:pass
        self.after(100,self._poll)


if __name__=="__main__":
    App().mainloop()
