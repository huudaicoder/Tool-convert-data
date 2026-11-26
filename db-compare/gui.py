#!/usr/bin/env python3
"""Giao dien GUI cho tool so sanh DB cu (QLPN_SUOI_HAI) / DB moi (QLPN).

Chay truc tiep:  python gui.py
Dong goi .exe :  xem build_exe.bat
"""
import os
import queue
import sys
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from types import SimpleNamespace

import compare as C
import mapping as M

GROUP_LABEL = {
    "LAI_LICH": "Thông tin lai lịch",
    "DIEN_BIEN": "Diễn biến",
    "KET_THUC": "Kết thúc",
}


class QueueWriter:
    """Thay sys.stdout trong luc chay nen, de day dong log ve GUI thread chinh."""

    def __init__(self, q):
        self.q = q

    def write(self, s):
        if s:
            self.q.put(("log", s))

    def flush(self):
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("So sánh dữ liệu QLPN (cũ ↔ mới)")
        self.geometry("980x820")
        self.minsize(860, 640)

        self.log_q = queue.Queue()
        self.running = False

        self._build_ui()
        self.after(150, self._poll_queue)
        try:
            self.state("zoomed")  # mo toi da man hinh de chac chan thay het, nhat la khung Nhat ky
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        pad = dict(padx=6, pady=4)

        conn = ttk.LabelFrame(self, text="Kết nối Oracle")
        conn.pack(fill="x", padx=10, pady=(10, 4))
        for i in range(4):
            conn.columnconfigure(i, weight=1)

        ttk.Label(conn, text="DB CŨ (QLPN_SUOI_HAI)", font=("", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", **pad)
        ttk.Label(conn, text="DB MỚI (QLPN)", font=("", 9, "bold")).grid(row=0, column=2, columnspan=2, sticky="w", **pad)

        self.old_dsn = self._field(conn, 1, 0, "DSN (host:port/service)")
        self.old_user = self._field(conn, 2, 0, "User")
        self.old_pwd = self._field(conn, 3, 0, "Mật khẩu", show="*")
        self.old_schema = self._field(conn, 4, 0, "Schema")
        self.btn_test_old = ttk.Button(conn, text="Kiểm tra kết nối", command=lambda: self.on_test_conn("old"))
        self.btn_test_old.grid(row=5, column=0, columnspan=2, sticky="w", padx=6, pady=(2, 6))

        self.new_dsn = self._field(conn, 1, 2, "DSN (host:port/service)")
        self.new_user = self._field(conn, 2, 2, "User")
        self.new_pwd = self._field(conn, 3, 2, "Mật khẩu", show="*")
        self.new_schema = self._field(conn, 4, 2, "Schema")
        self.btn_test_new = ttk.Button(conn, text="Kiểm tra kết nối", command=lambda: self.on_test_conn("new"))
        self.btn_test_new.grid(row=5, column=2, columnspan=2, sticky="w", padx=6, pady=(2, 6))

        screens_frame = ttk.LabelFrame(self, text="Chọn 1 màn cần so sánh")
        screens_frame.pack(fill="x", padx=10, pady=4)

        tree_wrap = ttk.Frame(screens_frame)
        tree_wrap.pack(fill="both", padx=4, pady=4)
        self.tree = ttk.Treeview(tree_wrap, columns=("name",), show="tree", selectmode="browse", height=9)
        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        by_group = {}
        for s in M.SCREENS:
            by_group.setdefault(s["group"], []).append(s)
        first_code = None
        for group, items in by_group.items():
            gid = f"group:{group}"
            self.tree.insert("", "end", iid=gid, text=f"{GROUP_LABEL.get(group, group)} ({len(items)})", open=True)
            for s in items:
                self.tree.insert(gid, "end", iid=s["code"], text=s["name"])
                if first_code is None:
                    first_code = s["code"]

        # Nhom (group) chi de hien thi, khong cho chon truc tiep.
        self._group_ids = {f"group:{g}" for g in by_group}
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        if first_code:
            self.tree.selection_set(first_code)

        opts = ttk.LabelFrame(self, text="Tùy chọn")
        opts.pack(fill="x", padx=10, pady=4)

        ttk.Label(opts, text="File kết quả (.xlsx)").grid(row=0, column=0, sticky="w", **pad)
        self.out_var = tk.StringVar(value=os.path.join(os.getcwd(), "ket_qua_so_sanh.xlsx"))
        ttk.Entry(opts, textvariable=self.out_var, width=60).grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(opts, text="Chọn...", command=self._pick_out).grid(row=0, column=2, **pad)

        self.ignore_case = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Bỏ qua hoa/thường khi so chuỗi", variable=self.ignore_case).grid(row=1, column=0, columnspan=2, sticky="w", **pad)

        self.only_missing = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Chỉ kiểm tra thiếu bản ghi (bỏ qua so lệch giá trị từng cột)",
                        variable=self.only_missing).grid(row=2, column=0, columnspan=4, sticky="w", **pad)

        ttk.Label(opts, text="Số dòng lệch tối đa / sheet").grid(row=1, column=2, sticky="e", **pad)
        self.limit_var = tk.StringVar(value="50000")
        ttk.Entry(opts, textvariable=self.limit_var, width=10).grid(row=1, column=3, sticky="w", **pad)
        opts.columnconfigure(1, weight=1)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=4)
        self.btn_run = ttk.Button(btns, text="Chạy so sánh", command=self.on_run)
        self.btn_run.pack(side="left")

        log_frame = ttk.LabelFrame(self, text="Nhật ký")
        log_frame.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.log = scrolledtext.ScrolledText(log_frame, height=12, state="normal")
        self.log.pack(fill="both", expand=True)

    def _field(self, parent, row, col, label, show=None):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=6)
        var = tk.StringVar()
        ttk.Entry(parent, textvariable=var, show=show or "").grid(row=row, column=col + 1, sticky="we", padx=6, pady=2)
        return var

    def _on_tree_select(self, _event):
        sel = self.tree.selection()
        if sel and sel[0] in self._group_ids:
            self.tree.selection_remove(sel[0])  # dong nhom chi de hien thi, khong cho chon

    def _pick_out(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel", "*.xlsx")],
                                             initialfile="ket_qua_so_sanh.xlsx")
        if path:
            self.out_var.set(path)

    # ------------------------------------------------------------------ actions
    def _log(self, text):
        self.log.insert("end", text)
        self.log.see("end")

    def _set_running(self, running):
        self.running = running
        state = "disabled" if running else "normal"
        self.btn_run.config(state=state)
        self.btn_test_old.config(state=state)
        self.btn_test_new.config(state=state)

    def on_test_conn(self, side):
        if self.running:
            return
        if side == "old":
            label, dsn, user, pwd, schema = "DB cũ", self.old_dsn, self.old_user, self.old_pwd, self.old_schema
        else:
            label, dsn, user, pwd, schema = "DB mới", self.new_dsn, self.new_user, self.new_pwd, self.new_schema
        dsn_v, user_v, pwd_v = dsn.get().strip(), user.get().strip(), pwd.get()
        if not dsn_v or not user_v or not pwd_v:
            messagebox.showwarning("Thiếu thông tin", f"Hãy nhập đủ DSN/User/Mật khẩu cho {label} trước.")
            return
        if "/" not in dsn_v:
            messagebox.showwarning("Thiếu tên service trong DSN",
                                    f"DSN {label} có vẻ thiếu phần /tên_service (vd: 192.168.1.1:1521/pdb1).")
            return
        self.log.delete("1.0", "end")
        self._set_running(True)
        threading.Thread(target=self._worker_test_conn, args=(label, dsn_v, user_v, pwd_v, schema.get().strip()),
                          daemon=True).start()

    def _worker_test_conn(self, label, dsn_v, user_v, pwd_v, schema_v):
        old_stdout = sys.stdout
        sys.stdout = QueueWriter(self.log_q)
        try:
            print(f"Dang ket noi {label} ({user_v}@{dsn_v})...")
            conn = C.connect(dsn_v, user_v, pwd_v)
            cur = conn.cursor()
            cur.execute("SELECT SYSDATE FROM DUAL")
            row = cur.fetchone()
            conn.close()
            print(f"  OK - ket noi thanh cong, gio server: {row[0]}")
            self.log_q.put(("done_test", label))
        except Exception:
            self.log_q.put(("error", traceback.format_exc()))
        finally:
            sys.stdout = old_stdout

    def on_run(self):
        if self.running:
            return
        missing = []
        for label, var in (("DSN DB cũ", self.old_dsn), ("User DB cũ", self.old_user),
                            ("Mật khẩu DB cũ", self.old_pwd), ("DSN DB mới", self.new_dsn),
                            ("User DB mới", self.new_user), ("Mật khẩu DB mới", self.new_pwd)):
            if not var.get().strip():
                missing.append(label)
        if missing:
            messagebox.showwarning("Thiếu thông tin", "Chưa nhập: " + ", ".join(missing))
            return
        bad_dsn = [label for label, var in (("DSN DB cũ", self.old_dsn), ("DSN DB mới", self.new_dsn))
                   if "/" not in var.get()]
        if bad_dsn:
            messagebox.showwarning(
                "Thiếu tên service trong DSN",
                "Các ô sau có vẻ thiếu phần /tên_service (vd: 4.120.255.101:1521/pdb1):\n"
                + "\n".join(bad_dsn) + "\n\nSửa lại DSN rồi bấm Chạy so sánh lại (ô Schema để trống "
                "nếu schema trùng tên User).")
            return
        sel = self.tree.selection()
        if not sel or sel[0] in self._group_ids:
            messagebox.showwarning("Thiếu lựa chọn", "Hãy chọn một màn để so sánh.")
            return
        picked = sel[0]
        out = self.out_var.get().strip()
        if not out:
            messagebox.showwarning("Thiếu đường dẫn", "Hãy chọn nơi lưu file kết quả.")
            return
        try:
            limit = int(self.limit_var.get())
        except ValueError:
            messagebox.showwarning("Sai giá trị", "Số dòng lệch tối đa phải là số nguyên.")
            return

        screens = [s for s in M.SCREENS if s["code"] == picked]
        ns = SimpleNamespace(
            old_dsn=self.old_dsn.get().strip(), old_user=self.old_user.get().strip(),
            old_pwd=self.old_pwd.get(), old_schema=self.old_schema.get().strip(),
            new_dsn=self.new_dsn.get().strip(), new_user=self.new_user.get().strip(),
            new_pwd=self.new_pwd.get(), new_schema=self.new_schema.get().strip(),
            out=out, limit=limit, ignore_case=self.ignore_case.get(),
            only_missing=self.only_missing.get(),
        )
        self.log.delete("1.0", "end")
        self._set_running(True)
        threading.Thread(target=self._worker_run, args=(ns, screens), daemon=True).start()

    def _worker_run(self, ns, screens):
        old_stdout = sys.stdout
        sys.stdout = QueueWriter(self.log_q)
        try:
            out_path = C.run_compare(ns, screens)
            self.log_q.put(("done_run", out_path))
        except Exception:
            self.log_q.put(("error", traceback.format_exc()))
        finally:
            sys.stdout = old_stdout

    # ------------------------------------------------------------------ queue poll
    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.log_q.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "done_test":
                    self._set_running(False)
                    messagebox.showinfo("Kiểm tra kết nối", f"Kết nối {payload} thành công.")
                elif kind == "done_run":
                    self._set_running(False)
                    if messagebox.askyesno("Hoàn tất", f"Đã ghi kết quả: {payload}\nMở file ngay bây giờ?"):
                        try:
                            os.startfile(payload)  # noqa: S606 - Windows only, user-chosen path
                        except Exception as e:  # noqa: BLE001
                            messagebox.showerror("Lỗi mở file", str(e))
                elif kind == "error":
                    self._set_running(False)
                    self._log("\n" + payload + "\n")
                    messagebox.showerror("Lỗi", "Có lỗi xảy ra, xem chi tiết trong nhật ký.")
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
