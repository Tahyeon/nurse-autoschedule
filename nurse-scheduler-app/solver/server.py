from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from datetime import datetime

try:
    from ortools.sat.python import cp_model
except Exception as exc:
    cp_model = None
    ORTOOLS_IMPORT_ERROR = str(exc)
else:
    ORTOOLS_IMPORT_ERROR = ""


SHIFTS = ("D", "E", "N", "OFF")
WORK_ROLES = {"charge", "mid", "newn"}
NIGHT_MIN = 7
NIGHT_MAX = 8


def days_in_month(year, month):
    if month == 12:
        return 31
    return (datetime(year, month + 1, 1) - datetime(year, month, 1)).days


def preferred_night_len(nurse):
    return 3 if nurse.get("name") == "\uc774\ud61c\ubbf8" else 2


def previous_assignments(prev, nurse):
    arr = prev.get(nurse["id"], []) or []
    out = {}
    if not arr:
        return out
    last = len(arr) - 1
    if arr[last] == "N":
        start = last
        while start > 0 and arr[start - 1] == "N":
            start -= 1
        run = last - start + 1
        if run == 1:
            target = preferred_night_len(nurse)
            extra = max(1, target - run)
            for day in range(1, extra + 1):
                out[day] = "N"
            out[extra + 1] = "OFF"
            out[extra + 2] = "OFF"
        else:
            out[1] = "OFF"
            out[2] = "OFF"
        return out
    last_n = -1
    for idx in range(last, max(-1, len(arr) - 8), -1):
        if arr[idx] == "N":
            last_n = idx
            break
    if last_n < 0:
        return out
    off_after = 0
    for idx in range(last_n + 1, len(arr)):
        if arr[idx] == "OFF":
            off_after += 1
        else:
            break
    for day in range(1, max(0, 2 - off_after) + 1):
        out[day] = "OFF"
    return out


def fixed_schedule_for(nurse, year, month, num_days):
    role = nurse.get("role")
    arr = []
    for day in range(1, num_days + 1):
        weekday = datetime(year, month, day).weekday()
        if role == "head":
            arr.append("OFF" if weekday >= 5 else "D")
        elif role == "edu":
            if weekday == 6:
                arr.append("OFF")
            elif weekday == 5:
                arr.append("MD")
            else:
                arr.append("D")
        else:
            arr.append("OFF")
    return arr


def solve_schedule(payload):
    if cp_model is None:
        return {"ok": False, "error": "OR-Tools import failed: " + ORTOOLS_IMPORT_ERROR}

    year = int(payload.get("year") or datetime.now().year)
    month = int(payload.get("month") or datetime.now().month)
    num_days = days_in_month(year, month)
    nurses = payload.get("nurses") or []
    workers = [n for n in nurses if n.get("role") in WORK_ROLES]
    requests = payload.get("requests") or []
    previous = payload.get("previousSchedule") or {}
    needs = payload.get("needs") or {}
    max_needs = payload.get("maxNeeds") or {}
    min_need = {"D": max(7, int(needs.get("D") or 8)), "E": max(7, int(needs.get("E") or 8)), "N": NIGHT_MIN}
    max_need = {
        "D": max(min_need["D"], int(max_needs.get("D") or 10)),
        "E": max(min_need["E"], int(max_needs.get("E") or 10)),
        "N": NIGHT_MAX,
    }

    model = cp_model.CpModel()
    x = {}
    block = {}
    carry = {}

    for n in workers:
        nid = n["id"]
        forced = previous_assignments(previous, n)
        carry[nid] = forced
        for d in range(1, num_days + 1):
            for s in SHIFTS:
                x[(nid, d, s)] = model.NewBoolVar(f"x_{nid}_{d}_{s}")
            model.AddExactlyOne(x[(nid, d, s)] for s in SHIFTS)
            if forced.get(d):
                model.Add(x[(nid, d, forced[d])] == 1)

    by_req = {}
    for req in requests:
        nid = req.get("nurseId")
        day = int(req.get("day") or 0)
        shift = req.get("shift") or req.get("type")
        if shift == "O":
            shift = "OFF"
        if nid and 1 <= day <= num_days and shift in SHIFTS:
            by_req[(nid, day)] = shift
            if (nid, day, shift) in x:
                model.Add(x[(nid, day, shift)] == 1)

    for d in range(1, num_days + 1):
        for shift in ("D", "E", "N"):
            expr = [x[(n["id"], d, shift)] for n in workers]
            model.Add(sum(expr) >= min_need[shift])
            model.Add(sum(expr) <= max_need[shift])

    for n in workers:
        nid = n["id"]
        for d in range(1, num_days):
            model.Add(x[(nid, d, "E")] + x[(nid, d + 1, "D")] <= 1)
        for d in range(1, num_days - 5 + 2):
            model.Add(sum(x[(nid, k, s)] for k in range(d, d + 5) for s in ("D", "E", "N")) <= 4)

    for n in workers:
        nid = n["id"]
        allowed_len = [preferred_night_len(n)]
        cover = {d: [] for d in range(1, num_days + 1)}
        forced_nights = {d for d, s in carry[nid].items() if s == "N"}
        for length in allowed_len:
            for start in range(1, num_days - length + 2):
                if any(day in forced_nights for day in range(start, start + length)):
                    continue
                b = model.NewBoolVar(f"nb_{nid}_{start}_{length}")
                block[(nid, start, length)] = b
                for day in range(start, start + length):
                    cover[day].append(b)
                for off_day in range(start + length, min(num_days, start + length + 1) + 1):
                    model.Add(x[(nid, off_day, "OFF")] == 1).OnlyEnforceIf(b)
        for d in range(1, num_days + 1):
            if d in forced_nights:
                model.Add(x[(nid, d, "N")] == 1)
                model.Add(sum(cover[d]) == 0)
            else:
                model.Add(x[(nid, d, "N")] == sum(cover[d]) if cover[d] else x[(nid, d, "N")] == 0)
        total_n = sum(x[(nid, d, "N")] for d in range(1, num_days + 1))
        model.Add(total_n >= 6)
        model.Add(total_n <= 7)

    penalties = []

    for d in range(1, num_days + 1):
        for shift in ("D", "E", "N"):
            charge_count = sum(x[(n["id"], d, shift)] for n in workers if n.get("role") == "charge")
            over = model.NewIntVar(0, 6, f"charge_over_{d}_{shift}")
            model.Add(over >= charge_count - 1)
            penalties.append(over * 20)

    model.Minimize(sum(penalties) if penalties else 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(payload.get("timeLimitSeconds") or 25)
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"ok": False, "error": "조건을 모두 만족하는 근무표를 찾지 못했습니다.", "status": solver.StatusName(status)}

    schedule = {}
    for n in nurses:
        nid = n["id"]
        if n.get("role") not in WORK_ROLES:
            schedule[nid] = fixed_schedule_for(n, year, month, num_days)
            continue
        arr = []
        for d in range(1, num_days + 1):
            val = "OFF"
            for s in SHIFTS:
                if solver.BooleanValue(x[(nid, d, s)]):
                    val = s
                    break
            arr.append(val)
        schedule[nid] = arr

    return {
        "ok": True,
        "schedule": schedule,
        "score": int(solver.ObjectiveValue()) if status == cp_model.OPTIMAL else int(solver.ObjectiveValue()),
        "status": solver.StatusName(status),
    }


class Handler(BaseHTTPRequestHandler):
    def _headers(self, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.end_headers()

    def do_OPTIONS(self):
        self._headers()
        self.wfile.write(b"{}")

    def do_GET(self):
        self._headers()
        self.wfile.write(json.dumps({"ok": True, "service": "nurse-scheduler-ortools"}).encode("utf-8"))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = solve_schedule(payload)
            self._headers(200 if result.get("ok") else 422)
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        except Exception as exc:
            self._headers(500)
            self.wfile.write(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8787), Handler).serve_forever()
