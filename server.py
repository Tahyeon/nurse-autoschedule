from datetime import datetime
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ortools.sat.python import cp_model


SHIFTS = ("D", "E", "N", "OFF")
WORK_ROLES = {"charge", "mid", "newn"}
NIGHT_MIN = 7
NIGHT_MAX = 8


app = FastAPI(title="Nurse AutoSchedule OR-Tools API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SolveRequest(BaseModel):
    year: int
    month: int
    nurses: List[Dict[str, Any]]
    requests: List[Dict[str, Any]] = []
    previousSchedule: Dict[str, List[str]] = {}
    needs: Dict[str, int] = {}
    maxNeeds: Dict[str, int] = {}
    timeLimitSeconds: int = 30


def days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (datetime(year, month + 1, 1) - datetime(year, month, 1)).days


def preferred_night_len(nurse: Dict[str, Any]) -> int:
    return 3 if nurse.get("name") == "이혜미" else 2


def fixed_schedule_for(nurse: Dict[str, Any], year: int, month: int, num_days: int) -> List[str]:
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


def previous_assignments(previous: Dict[str, List[str]], nurse: Dict[str, Any], num_days: int) -> Dict[int, str]:
    arr = previous.get(nurse["id"], []) or []
    out: Dict[int, str] = {}
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
            extra_nights = max(1, target - run)
            for day in range(1, min(extra_nights, num_days) + 1):
                out[day] = "N"
            for day in range(extra_nights + 1, min(extra_nights + 2, num_days) + 1):
                out[day] = "OFF"
        else:
            out[1] = "OFF"
            if num_days >= 2:
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
    for day in range(1, min(max(0, 2 - off_after), num_days) + 1):
        out[day] = "OFF"
    return out


def normalize_shift(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if raw in {"O", "OFF", "OF"}:
        return "OFF"
    if raw in {"D", "E", "N"}:
        return raw
    return raw


def solve(payload: SolveRequest) -> Dict[str, Any]:
    year = payload.year
    month = payload.month
    num_days = days_in_month(year, month)
    nurses = payload.nurses
    workers = [n for n in nurses if n.get("role") in WORK_ROLES]

    min_need = {
        "D": max(7, int(payload.needs.get("D") or 8)),
        "E": max(7, int(payload.needs.get("E") or 8)),
        "N": NIGHT_MIN,
    }
    max_need = {
        "D": max(min_need["D"], int(payload.maxNeeds.get("D") or 10)),
        "E": max(min_need["E"], int(payload.maxNeeds.get("E") or 10)),
        "N": NIGHT_MAX,
    }

    model = cp_model.CpModel()
    x: Dict[tuple, cp_model.IntVar] = {}
    work: Dict[tuple, cp_model.IntVar] = {}
    block: Dict[tuple, cp_model.IntVar] = {}
    carry: Dict[str, Dict[int, str]] = {}

    for nurse in workers:
        nid = nurse["id"]
        carry[nid] = previous_assignments(payload.previousSchedule, nurse, num_days)
        for day in range(1, num_days + 1):
            for shift in SHIFTS:
                x[(nid, day, shift)] = model.NewBoolVar(f"x_{nid}_{day}_{shift}")
            work[(nid, day)] = model.NewBoolVar(f"work_{nid}_{day}")
            model.AddExactlyOne(x[(nid, day, shift)] for shift in SHIFTS)
            model.Add(work[(nid, day)] == sum(x[(nid, day, shift)] for shift in ("D", "E", "N")))
            if carry[nid].get(day):
                model.Add(x[(nid, day, carry[nid][day])] == 1)

    for req in payload.requests:
        nid = req.get("nurseId")
        day = int(req.get("day") or 0)
        shift = normalize_shift(req.get("shift") or req.get("type"))
        if (nid, day, shift) in x:
            model.Add(x[(nid, day, shift)] == 1)

    for day in range(1, num_days + 1):
        for shift in ("D", "E", "N"):
            assigned = [x[(n["id"], day, shift)] for n in workers]
            model.Add(sum(assigned) >= min_need[shift])
            model.Add(sum(assigned) <= max_need[shift])

    for nurse in workers:
        nid = nurse["id"]
        for day in range(1, num_days):
            model.Add(x[(nid, day, "E")] + x[(nid, day + 1, "D")] <= 1)
        for start in range(1, num_days - 5 + 2):
            model.Add(sum(work[(nid, day)] for day in range(start, start + 5)) <= 4)

    for nurse in workers:
        nid = nurse["id"]
        night_len = preferred_night_len(nurse)
        cover = {day: [] for day in range(1, num_days + 1)}
        carried_nights = {day for day, shift in carry[nid].items() if shift == "N"}

        for start in range(1, num_days - night_len + 2):
            if any(day in carried_nights for day in range(start, start + night_len)):
                continue
            b = model.NewBoolVar(f"night_block_{nid}_{start}_{night_len}")
            block[(nid, start, night_len)] = b
            for day in range(start, start + night_len):
                cover[day].append(b)
            for off_day in range(start + night_len, min(num_days, start + night_len + 1) + 1):
                model.Add(x[(nid, off_day, "OFF")] == 1).OnlyEnforceIf(b)

        for day in range(1, num_days + 1):
            if day in carried_nights:
                model.Add(x[(nid, day, "N")] == 1)
                if cover[day]:
                    model.Add(sum(cover[day]) == 0)
            elif cover[day]:
                model.Add(x[(nid, day, "N")] == sum(cover[day]))
            else:
                model.Add(x[(nid, day, "N")] == 0)

        total_nights = sum(x[(nid, day, "N")] for day in range(1, num_days + 1))
        model.Add(total_nights >= 6)
        model.Add(total_nights <= 7)

    penalties = []

    for day in range(1, num_days + 1):
        for shift in ("D", "E", "N"):
            charge_count = sum(x[(n["id"], day, shift)] for n in workers if n.get("role") == "charge")
            over = model.NewIntVar(0, 6, f"charge_overlap_{day}_{shift}")
            model.Add(over >= charge_count - 1)
            penalties.append(over * 30)

    for nurse in workers:
        nid = nurse["id"]
        for day in range(1, num_days - 2 + 1):
            scattered = model.NewBoolVar(f"scattered_{nid}_{day}")
            model.AddBoolAnd([work[(nid, day)], x[(nid, day + 1, "OFF")], work[(nid, day + 2)]]).OnlyEnforceIf(scattered)
            model.AddBoolOr([work[(nid, day)].Not(), x[(nid, day + 1, "OFF")].Not(), work[(nid, day + 2)].Not(), scattered])
            penalties.append(scattered * 3)

    model.Minimize(sum(penalties) if penalties else 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(5, min(120, int(payload.timeLimitSeconds or 30)))
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "ok": False,
            "status": solver.StatusName(status),
            "error": "조건을 만족하는 근무표를 찾지 못했습니다. 신청근무, 이전달 근무표, N 7~8명 조건이 충돌하는지 확인하세요.",
        }

    schedule: Dict[str, List[str]] = {}
    for nurse in nurses:
        nid = nurse["id"]
        if nurse.get("role") not in WORK_ROLES:
            schedule[nid] = fixed_schedule_for(nurse, year, month, num_days)
            continue
        arr = []
        for day in range(1, num_days + 1):
            value = "OFF"
            for shift in SHIFTS:
                if solver.BooleanValue(x[(nid, day, shift)]):
                    value = shift
                    break
            arr.append(value)
        schedule[nid] = arr

    return {
        "ok": True,
        "status": solver.StatusName(status),
        "schedule": schedule,
        "score": int(solver.ObjectiveValue()),
        "objective": solver.ObjectiveValue(),
    }


@app.get("/")
def root() -> Dict[str, Any]:
    return {"ok": True, "service": "nurse-autoschedule", "engine": "OR-Tools CP-SAT"}


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True}


@app.post("/solve")
def solve_endpoint(payload: SolveRequest) -> Dict[str, Any]:
    return solve(payload)
