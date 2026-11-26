"""Create the C10 comparison workbook."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import csv

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from mapping import SCREENS


def _safe(value):
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def _quantity_result(row):
    old_total, new_total = row.get("old_total"), row.get("new_total")
    status = str(row.get("status", ""))
    if (not isinstance(old_total, (int, float))
            or not isinstance(new_total, (int, float))
            or status.startswith(("Chưa", "Lỗi truy vấn"))):
        return "Chưa đối soát"
    if old_total != new_total:
        return "Đối soát lệch"
    if row.get("unmapped_old_person_rows", 0) or row.get("unmapped_new_person_rows", 0):
        return "Chưa đối soát"
    return "Đối soát khớp"


EXCEL_MAX_ROWS = 1_048_576


def _sheet(wb, title, headers, rows, row_count, output_path, spills, banner=None):
    ws = wb.create_sheet(title)
    header_row = 2 if banner else 1
    if banner:
        ws.append([banner])
    ws.append(headers)
    if row_count > EXCEL_MAX_ROWS - header_row:
        csv_path = Path(output_path).with_name(f"{Path(output_path).stem}_{title}.csv")
        with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            if banner:
                writer.writerow([banner])
            writer.writerow(headers)
            writer.writerows([_safe(v) for v in row] for row in rows)
        ws.append([f"Có {row_count:,} dòng, vượt giới hạn Excel. Toàn bộ dữ liệu được xuất ra: {csv_path.name}"])
        spills.append(str(csv_path))
    else:
        for row in rows:
            ws.append([_safe(v) for v in row])
    ws.freeze_panes = f"A{header_row + 1}"
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(headers))}{ws.max_row}"
    header_fill = PatternFill("solid", fgColor="17365D")
    for cell in ws[header_row]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[header_row].height = 32
    if banner:
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        title_cell = ws.cell(row=1, column=1)
        title_cell.font = Font(bold=True, color="FFFFFF", size=14)
        title_cell.fill = PatternFill("solid", fgColor="1F4E78")
        title_cell.alignment = Alignment(vertical="center", horizontal="left")
        ws.row_dimensions[1].height = 28
    for column in ws.columns:
        letter = get_column_letter(column[0].column)
        width = max((len(str(c.value or "")) for c in column[:300]), default=10)
        ws.column_dimensions[letter].width = min(48, max(12, width + 2))
    ws.sheet_view.showGridLines = False
    return ws


def write_report(path, result, old_cfg, new_cfg, selected_count):
    spills = []
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
        ["Phạm vi trại đối soát", result.get("prison_scope", {}).get("code", "")],
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
    _sheet(wb, "Tổng quan", ["Chỉ tiêu", "Kết quả"], overview_rows, len(overview_rows), path, spills)

    # Keep the quantity sheet's columns aligned with the supplied checklist template.
    summary_headers = ["STT", "Nhóm", "Bảng đích", "Nội dung", "Kết quả",
                       "SL bản ghi nguồn", "SL bản ghi đích", "Chênh lệch",
                       "SL phạm nhân có dữ liệu (nguồn)", "SL phạm nhân có dữ liệu (đích)",
                       "Chênh lệch PN", "Bảng nguồn tương ứng", "Bảng cha / khóa liên kết",
                       "Thứ tự nạp", "Số cột", "Người kiểm tra", "Ngày kiểm tra", "Ghi chú"]
    screens_by_code = {screen["code"]: screen for screen in SCREENS}
    summary_rows = []
    group_names = {"LAI_LICH": "Lý lịch", "DIEN_BIEN": "Diễn biến", "KET_THUC": "Kết thúc"}
    for index, row in enumerate(summaries, 1):
        screen = screens_by_code.get(row.get("code"), {})
        old_total, new_total = row.get("old_total"), row.get("new_total")
        count_delta = new_total - old_total if isinstance(old_total, (int, float)) and isinstance(new_total, (int, float)) else "—"
        old_people = row.get("old_people_with_data", "—")
        new_people = row.get("new_people_with_data", "—")
        people_delta = (new_people - old_people
                        if isinstance(old_people, (int, float)) and isinstance(new_people, (int, float))
                        else "—")
        link = "—"
        if screen.get("old_pn") or screen.get("new_pn"):
            link = f'{screen.get("old_pn", "—")} → {screen.get("new_pn", "—")}'
        summary_rows.append([
            index, group_names.get(row.get("group"), row.get("group", "")),
            row.get("new_table", ""), row.get("name", ""), _quantity_result(row),
            old_total, new_total, count_delta,
            old_people, new_people, people_delta,
            row.get("old_table", ""),
            link, index, len(screen.get("cols", [])) if screen else "—", "", "", "",
        ])
    prison_scope = result.get("prison_scope", {})
    prison_name = str(prison_scope.get("name") or "").strip()
    if prison_name and not prison_name.casefold().startswith("trại giam"):
        prison_name = f"Trại giam {prison_name}"
    banner = f"{prison_name} - {prison_scope.get('code', '')}".strip(" -")
    _sheet(wb, "Đối soát số lượng", summary_headers, summary_rows, len(summary_rows),
           path, spills, banner=banner)

    # Detail rows are restricted to datasets represented in the quantity sheet,
    # then collapsed to one row per person and dataset (never one row per field).
    summary_codes = {str(row.get("code", "")) for row in summaries}
    presence_statuses = {
        "Chỉ có ở DB cũ (thiếu ở DB mới)",
        "Chỉ có ở DB mới (thiếu ở DB cũ)",
    }
    details = [detail for detail in result.get("details", [])
               if str(detail.get("code", "")) in summary_codes
               and detail.get("status") in presence_statuses]
    affected = {}
    for detail in details:
        key = (str(detail.get("code", "")), str(detail.get("hsld", "")),
               str(detail.get("old_person_id", "")), str(detail.get("new_person_id", "")))
        bucket = affected.setdefault(key, {"screen": detail.get("dataset", ""),
                                           "statuses": set(), "records": set()})
        bucket["statuses"].add(str(detail.get("status", "")))
        # A field mismatch produces several engine detail rows for one record.
        # Count the record once using its key and status, not once per column.
        bucket["records"].add((str(detail.get("key", "")), str(detail.get("status", ""))))
    detail_headers = ["STT", "Nhóm", "Màn", "Bảng đích", "HSLĐ", "ID phạm nhân DB cũ",
                      "ID phạm nhân DB mới", "Số bản ghi cần rà soát", "Loại sai lệch"]
    detail_rows = []
    for index, ((code, hsld, old_id, new_id), item) in enumerate(sorted(affected.items()), 1):
        screen = screens_by_code.get(code, {})
        detail_rows.append([
            index, group_names.get(screen.get("group"), ""), item["screen"], screen.get("new_table", ""),
            hsld, old_id, new_id, len(item["records"]), "; ".join(sorted(item["statuses"])),
        ])
    _sheet(wb, "Chi tiết sai lệch", detail_headers, detail_rows, len(detail_rows), path, spills)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path, spills
