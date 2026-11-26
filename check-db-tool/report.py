"""Create the four-sheet C10 comparison workbook."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def _safe(value):
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def _sheet(wb, title, headers, rows):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for row in rows:
        ws.append([_safe(v) for v in row])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    header_fill = PatternFill("solid", fgColor="17365D")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 32
    for column in ws.columns:
        letter = get_column_letter(column[0].column)
        width = max((len(str(c.value or "")) for c in column[:300]), default=10)
        ws.column_dimensions[letter].width = min(48, max(12, width + 2))
    ws.sheet_view.showGridLines = False
    return ws


def write_report(path, result, old_cfg, new_cfg, selected_count):
    wb = Workbook()
    wb.remove(wb.active)
    patients = result["patients"]
    patient_counts = {}
    for row in patients:
        patient_counts[row["status"]] = patient_counts.get(row["status"], 0) + 1
    summaries = result["summaries"]
    totals = {k: sum((r.get(k, 0) or 0) for r in summaries if isinstance(r.get(k), (int, float)))
              for k in ("old_total", "new_total", "matched", "diff", "old_only", "new_only", "duplicates")}
    overview_rows = [
        ["Thời điểm xuất", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["DB cũ", f"{old_cfg.get('user','')} / schema {old_cfg.get('schema') or '(mặc định)'}"],
        ["DB mới", f"{new_cfg.get('user','')} / schema {new_cfg.get('schema') or '(mặc định)'}"],
        ["Dataset được chọn", selected_count],
        ["Hồ sơ ghép theo HSLĐ", result.get("matched_people", 0)],
        ["Chỉ có ở DB cũ", patient_counts.get("Chỉ có ở DB cũ", 0)],
        ["Chỉ có ở DB mới", patient_counts.get("Chỉ có ở DB mới", 0)],
        ["HSLĐ trống / trùng", sum(v for k, v in patient_counts.items() if "trống" in k or "Trùng" in k)],
        ["Tổng dòng DB cũ (dataset đã chạy)", totals["old_total"]],
        ["Tổng dòng DB mới (dataset đã chạy)", totals["new_total"]],
        ["Bản ghi khớp chính xác", totals["matched"]],
        ["Bản ghi lệch giá trị", totals["diff"]],
        ["Bản ghi chỉ có ở DB cũ", totals["old_only"]],
        ["Bản ghi chỉ có ở DB mới", totals["new_only"]],
        ["Dòng thuộc hồ sơ không ghép được", sum(r.get("unmapped_old_person_rows", 0) + r.get("unmapped_new_person_rows", 0) for r in summaries)],
    ]
    _sheet(wb, "Tổng quan", ["Chỉ tiêu", "Kết quả"], overview_rows)

    summary_headers = ["Cụm", "Mã dataset", "Màn / lưới", "Bảng DB cũ", "Bảng DB mới",
                       "Số dòng DB cũ", "Số dòng DB mới", "Khớp", "Lệch giá trị", "Chỉ có DB cũ",
                       "Chỉ có DB mới", "Trùng khóa", "Dòng người chưa ghép (cũ)",
                       "Dòng người chưa ghép (mới)", "Trạng thái"]
    summary_rows = [[r.get("group"), r.get("code"), r.get("name"), r.get("old_table"), r.get("new_table"),
                     r.get("old_total"), r.get("new_total"), r.get("matched"), r.get("diff"),
                     r.get("old_only"), r.get("new_only"), r.get("duplicates"),
                     r.get("unmapped_old_person_rows"), r.get("unmapped_new_person_rows"), r.get("status")]
                    for r in summaries]
    _sheet(wb, "Đối soát số lượng", summary_headers, summary_rows)

    patient_rows = [[r.get("old_hsld"), r.get("old_id"), r.get("new_hsld"), r.get("new_id"), r.get("status")]
                    for r in patients]
    _sheet(wb, "Ghép phạm nhân", ["HSLĐ DB cũ", "PN_ID cũ", "HSLĐ DB mới", "ID DB mới", "Kết quả"], patient_rows)

    detail_headers = ["Cụm", "Mã dataset", "Màn / lưới", "Trạng thái", "HSLĐ", "PN_ID cũ", "ID mới",
                      "Khóa bản ghi", "Cột DB cũ", "Cột DB mới", "Giá trị DB cũ", "Giá trị DB mới"]
    details = [[d.get("group", ""), d.get("code"), d.get("dataset"), d.get("status"), d.get("hsld"),
                d.get("old_person_id"), d.get("new_person_id"), d.get("key"), d.get("old_column"),
                d.get("new_column"), d.get("old_value"), d.get("new_value")] for d in result["details"]]
    _sheet(wb, "Chi tiết sai lệch", detail_headers,
           details or [["", "", "", "Không có sai lệch bản ghi/trường trong các dataset đã chạy.", "", "", "", "", "", "", "", ""]])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
