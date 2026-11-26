from __future__ import annotations
import csv, queue, threading, tkinter as tk
from tkinter import ttk, messagebox, filedialog
import engine

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Chuyển địa phương tòa xử Tiền án"); self.geometry("1460x790"); self.minsize(1050,600)
        self.events=queue.Queue(); self.plan=None; self.busy=False
        box=ttk.LabelFrame(self,text="Kết nối DB mới",padding=10); box.pack(fill="x",padx=10,pady=8)
        self.vars={k:tk.StringVar() for k in ("dsn","user","password","schema")}
        fields=(("dsn","DSN (host:port/service)"),("user","User"),("password","Mật khẩu"),("schema","Schema (tùy chọn)"))
        for i,(key,label) in enumerate(fields):
            row,col=divmod(i,2); col*=2
            ttk.Label(box,text=label).grid(row=row,column=col,sticky="w",padx=4,pady=4)
            ttk.Entry(box,textvariable=self.vars[key],width=42,show="*" if key=="password" else "").grid(row=row,column=col+1,sticky="ew",padx=4,pady=4)
        box.columnconfigure(1,weight=1); box.columnconfigure(3,weight=1)
        ttk.Label(self,text="Trong cùng DB: lấy DP_MA từ DM_DIA_PHUONG theo ID hiện tại, tìm mã tương ứng ở DM_TINH_THANH_PHO.TTP_MA và cập nhật ID vào PN_TIEN_AN.PNTA_DIA_PHUONG_ID. Chỉ mã khớp duy nhất mới được cập nhật.",wraplength=1400,justify="left").pack(anchor="w",padx=12,pady=4)
        bar=ttk.Frame(self);bar.pack(fill="x",padx=10,pady=5)
        self.preview_btn=ttk.Button(bar,text="Preview",command=self.preview);self.preview_btn.pack(side="left")
        self.selected_btn=ttk.Button(bar,text="Cập nhật dòng chọn",command=lambda:self.apply(True),state="disabled");self.selected_btn.pack(side="left",padx=6)
        self.all_btn=ttk.Button(bar,text="Cập nhật tất cả dòng khớp",command=lambda:self.apply(False),state="disabled");self.all_btn.pack(side="left",padx=6)
        self.csv_btn=ttk.Button(bar,text="Xuất CSV preview",command=self.export,state="disabled");self.csv_btn.pack(side="left",padx=6)
        self.status=ttk.Label(bar,text="Chưa preview.");self.status.pack(side="left",padx=10)
        frame=ttk.Frame(self);frame.pack(fill="both",expand=True,padx=10,pady=5)
        self.cols=("row_id","old_id","old_code","old_name","new_id","new_code","new_name","status")
        self.tree=ttk.Treeview(frame,columns=self.cols,show="headings",selectmode="extended")
        titles=("PN_TIEN_AN.ID","ID DM_DIA_PHUONG","DP_MA","DP_TEN","ID DM_TINH_THANH_PHO","TTP_MA","TTP_TEN","Trạng thái")
        widths=(120,150,100,220,180,100,220,250)
        for c,t,w in zip(self.cols,titles,widths):self.tree.heading(c,text=t);self.tree.column(c,width=w,anchor="w")
        ys=ttk.Scrollbar(frame,orient="vertical",command=self.tree.yview);xs=ttk.Scrollbar(frame,orient="horizontal",command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set);frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
        self.tree.grid(row=0,column=0,sticky="nsew");ys.grid(row=0,column=1,sticky="ns");xs.grid(row=1,column=0,sticky="ew")
        self.tree.bind("<<TreeviewSelect>>",lambda _e:self.refresh_buttons());self.after(100,self.poll)
    def cfg(self):
        cfg={k:v.get().strip() for k,v in self.vars.items()}
        if not all(cfg[k] for k in ("dsn","user","password")):raise ValueError("Nhập DSN, user và mật khẩu DB mới.")
        if "/" not in cfg["dsn"]:raise ValueError("DSN cần dạng host:port/service.")
        return cfg
    def run_bg(self,fn,*args):
        self.busy=True;self.preview_btn.configure(state="disabled");self.refresh_buttons();self.status.configure(text="Đang xử lý...")
        def worker():
            try:self.events.put(("ok",fn(*args)))
            except Exception as exc:self.events.put(("error",str(exc)))
        threading.Thread(target=worker,daemon=True).start()
    def preview(self):
        try:cfg=self.cfg()
        except Exception as exc:messagebox.showwarning("Thiếu thông tin",str(exc));return
        self.plan=None
        for item in self.tree.get_children():self.tree.delete(item)
        self.run_bg(engine.preview_tien_an_dia_phuong_conversion,cfg)
    def apply(self,selected):
        if not self.plan:return
        ready=[r for r in self.plan["rows"] if r.get("ready")]
        if selected:
            ids={self.tree.item(item,"values")[0] for item in self.tree.selection()};ready=[r for r in ready if str(r["row_id"]) in ids]
        if not ready:messagebox.showinfo("Không có dòng", "Không có dòng khớp duy nhất để cập nhật.");return
        if not messagebox.askyesno("Xác nhận cập nhật",f"Sẽ cập nhật {len(ready):,} dòng PN_TIEN_AN.PNTA_DIA_PHUONG_ID trong một transaction. Tool kiểm tra lại dữ liệu trước khi ghi; nếu có dòng thay đổi thì toàn bộ sẽ rollback. Tiếp tục?"):return
        try:cfg=self.cfg()
        except Exception as exc:messagebox.showwarning("Thiếu thông tin",str(exc));return
        self.run_bg(engine.apply_tien_an_dia_phuong_conversion,cfg,self.plan,[r["row_id"] for r in ready])
    def export(self):
        if not self.plan:return
        path=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=(("CSV UTF-8","*.csv"),),initialfile="preview_dia_phuong_tien_an.csv")
        if not path:return
        fields=("row_id","old_id","old_code","old_name","new_id","new_code","new_name","status")
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows({k:r.get(k,"") for k in fields} for r in self.plan["rows"])
        messagebox.showinfo("Đã xuất CSV",path)
    def refresh_buttons(self):
        ready=bool(self.plan and self.plan.get("ready_count")) and not self.busy
        self.all_btn.configure(state="normal" if ready else "disabled")
        selected=any(self.tree.item(item,"values")[7]=="Sẵn sàng cập nhật" for item in self.tree.selection()) and not self.busy
        self.selected_btn.configure(state="normal" if selected else "disabled")
        self.csv_btn.configure(state="normal" if self.plan and not self.busy else "disabled")
    def poll(self):
        while not self.events.empty():
            kind,value=self.events.get();self.busy=False;self.preview_btn.configure(state="normal")
            if kind=="error":self.status.configure(text="Có lỗi.");messagebox.showerror("Không chạy được",value);self.refresh_buttons();continue
            if isinstance(value,dict) and "rows" in value:
                self.plan=value
                labels={"READY":"Sẵn sàng cập nhật","NOT_IN_DP_CATALOG":"ID không có trong DM_DIA_PHUONG","NO_TTP_CODE":"Không có mã tương ứng trong TTP","DUPLICATE_TTP_CODE":"Mã TTP bị trùng","LEDGER_CONFLICT":"ID đã đổi sau cập nhật trước"}
                for r in value["rows"][:20000]:self.tree.insert("","end",values=(r.get("row_id",""),r.get("old_id",""),r.get("old_code",""),r.get("old_name",""),r.get("new_id",""),r.get("new_code",""),r.get("new_name",""),labels.get(r["status"],r["status"])))
                extra=" (lưới hiển thị 20.000 dòng đầu)" if len(value["rows"])>20000 else ""
                self.status.configure(text=f"{value['total_rows']:,} dòng có địa phương • {value['ready_count']:,} sẵn sàng • {value['unchanged_count']:,} đã đúng • {value['issue_count']:,} cần rà soát{extra}. Chưa ghi DB.")
                self.refresh_buttons()
            else:
                self.plan=None;self.status.configure(text=f"Đã COMMIT {value['updated']:,} dòng. Hãy Preview lại để kiểm tra.");self.refresh_buttons();messagebox.showinfo("Cập nhật hoàn tất",self.status.cget("text"))
        self.after(100,self.poll)
if __name__=="__main__":App().mainloop()
