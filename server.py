from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Tuple

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ortools.sat.python import cp_model
from pydantic import BaseModel, Field


SHIFTS = ("D", "E", "N", "OFF")
WORK_SHIFTS = ("D", "E", "N")
WORK_ROLES = {"charge", "mid", "newn"}
ROLE_LABEL = {"charge": "차지", "mid": "중간", "newn": "신규"}
NIGHT_MIN = 7
NIGHT_MAX = 8
DEFAULT_TIME_LIMIT_SECONDS = 60


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
    requests: List[Dict[str, Any]] = Field(default_factory=list)
    previousSchedule: Dict[str, List[str]] = Field(default_factory=dict)
    needs: Dict[str, int] = Field(default_factory=dict)
    maxNeeds: Dict[str, int] = Field(default_factory=dict)
    offTarget: int | None = None
    baseOff: int | None = None
    nightTolerance: int = 1
    timeLimitSeconds: int = DEFAULT_TIME_LIMIT_SECONDS


def days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (datetime(year, month + 1, 1) - datetime(year, month, 1)).days


def worker_nurses(nurses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [n for n in nurses if n.get("role") in WORK_ROLES]


def nurse_name(nurse: Dict[str, Any]) -> str:
    return str(nurse.get("name") or nurse.get("id") or "")


def preferred_night_lengths(nurse: Dict[str, Any]) -> List[int]:
    return [3] if nurse_name(nurse) == "이혜미" else [2, 3]


def normalize_shift(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if raw in {"O", "OF", "OFF"}:
        return "OFF"
    if raw in {"D", "E", "N"}:
        return raw
    return raw


def fixed_schedule_for(nurse: Dict[str, Any], year: int, month: int, num_days: int) -> List[str]:
    role = nurse.get("role")
    out = []
    for day in range(1, num_days + 1):
        weekday = datetime(year, month, day).weekday()
        if role == "head":
            out.append("OFF" if weekday >= 5 else "D")
        elif role == "edu":
            if weekday == 6:
                out.append("OFF")
            elif weekday == 5:
                out.append("MD")
            else:
                out.append("D")
        else:
            out.append("OFF")
    return out


def previous_night_run_at_end(previous: Dict[str, List[str]], nurse_id: str) -> int:
    arr = previous.get(nurse_id, []) or []
    if not arr or arr[-1] != "N":
        return 0
    run = 0
    for value in reversed(arr):
        if value == "N":
            run += 1
        else:
            break
    return run


def previous_carryover(previous: Dict[str, List[str]], nurse: Dict[str, Any], num_days: int) -> Dict[int, str]:
    nid = nurse["id"]
    run = previous_night_run_at_end(previous, nid)
    out: Dict[int, str] = {}
    if run == 1:
        target_len = 3 if nurse_name(nurse) == "이혜미" else 2
        extra_nights = max(1, target_len - run)
        for day in range(1, min(extra_nights, num_days) + 1):
            out[day] = "N"
        for day in range(extra_nights + 1, min(extra_nights + 2, num_days) + 1):
            out[day] = "OFF"
    elif run >= 2:
        out[1] = "OFF"
        if num_days >= 2:
            out[2] = "OFF"
    return out


def request_shift(req: Dict[str, Any]) -> str:
    return normalize_shift(req.get("shift") or req.get("type"))


def grouped_off_requests(payload: SolveRequest, workers: List[Dict[str, Any]]) -> Tuple[Dict[Tuple[str, int], str], List[Dict[str, Any]]]:
    worker_ids = {n["id"] for n in workers}
    by_id = {n["id"]: n for n in workers}
    accepted: Dict[Tuple[str, int], str] = {}
    conflicts: List[Dict[str, Any]] = []
    by_day: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    by_day_role: Dict[Tuple[int, str], List[Dict[str, Any]]] = defaultdict(list)
    num_days = days_in_month(payload.year, payload.month)

    for req in payload.requests:
        nid = req.get("nurseId")
        day = int(req.get("day") or 0)
        shift = request_shift(req)
        if nid not in worker_ids or not (1 <= day <= num_days) or shift != "OFF":
            continue
        nurse = by_id[nid]
        item = {"nurseId": nid, "name": nurse_name(nurse), "day": day, "shift": shift, "role": nurse.get("role")}
        by_day[day].append(item)
        by_day_role[(day, nurse.get("role"))].append(item)

    blocked = set()
    for day, items in by_day.items():
        if len(items) > 3:
            conflicts.append({"type": "daily_off_request_limit", "day": day, "limit": 3, "requests": items})
            blocked.update((item["nurseId"], day) for item in items[3:])

    for (day, role), items in by_day_role.items():
        if len(items) > 1:
            conflicts.append({"type": "same_grade_off_request_conflict", "day": day, "role": role, "requests": items})
            blocked.update((item["nurseId"], day) for item in items[1:])

    for items in by_day.values():
        for item in items:
            key = (item["nurseId"], item["day"])
            if key not in blocked:
                accepted[key] = "OFF"
    return accepted, conflicts


def build_precheck(payload: SolveRequest, workers: List[Dict[str, Any]], num_days: int, off_target: int, min_need: Dict[str, int], max_need: Dict[str, int]) -> List[Dict[str, Any]]:
    problems = []
    worker_count = len(workers)
    total_slots = worker_count * num_days
    required_work_min = num_days * sum(min_need[s] for s in WORK_SHIFTS)
    required_work_max = num_days * sum(max_need[s] for s in WORK_SHIFTS)
    exact_off_total = worker_count * off_target
    exact_work_total = total_slots - exact_off_total
    if exact_work_total < required_work_min:
        problems.append({
            "type": "too_many_off_slots",
            "message": "OFF 목표가 너무 많아 최소 필요 인원을 채울 수 없습니다.",
            "worker_count": worker_count,
            "off_target": off_target,
            "required_work_min": required_work_min,
            "available_work": exact_work_total,
            "relax": ["OFF 목표 개수 감소", "D/E/N 최소 인원 감소", "근무 가능 간호사 추가"],
        })
    if exact_work_total > required_work_max:
        problems.append({
            "type": "too_few_off_slots",
            "message": "OFF 목표가 너무 적어 최대 인원 범위 안에 모든 근무를 배치할 수 없습니다.",
            "worker_count": worker_count,
            "off_target": off_target,
            "required_work_max": required_work_max,
            "available_work": exact_work_total,
            "relax": ["OFF 목표 개수 증가", "D/E 최대 인원 증가"],
        })
    total_night_min = num_days * NIGHT_MIN
    total_night_max = num_days * NIGHT_MAX
    personal_night_min = worker_count * 6
    personal_night_max = worker_count * 7
    if personal_night_min > total_night_max or personal_night_max < total_night_min:
        problems.append({
            "type": "night_total_mismatch",
            "message": "일별 N 7~8명 조건과 개인별 N 6~7개 조건이 총량에서 충돌합니다.",
            "daily_night_total_range": [total_night_min, total_night_max],
            "personal_night_total_range": [personal_night_min, personal_night_max],
            "relax": ["개인별 N 범위 조정", "일별 N 인원 조정", "3교대 대상자 수 조정"],
        })
    return problems


def solve(payload: SolveRequest) -> Dict[str, Any]:
    year = payload.year
    month = payload.month
    num_days = days_in_month(year, month)
    nurses = payload.nurses
    workers = worker_nurses(nurses)
    off_target = int(payload.offTarget if payload.offTarget is not None else payload.baseOff if payload.baseOff is not None else 10)
    min_need = {
        "D": max(1, int(payload.needs.get("D") or 8)),
        "E": max(1, int(payload.needs.get("E") or 8)),
        "N": NIGHT_MIN,
    }
    max_need = {
        "D": max(min_need["D"], int(payload.maxNeeds.get("D") or 10)),
        "E": max(min_need["E"], int(payload.maxNeeds.get("E") or 10)),
        "N": NIGHT_MAX,
    }

    request_off, request_conflicts = grouped_off_requests(payload, workers)
    precheck = build_precheck(payload, workers, num_days, off_target, min_need, max_need)
    if precheck:
        return failure_response("precheck_failed", "입력 조건의 총량이 충돌해 해를 만들 수 없습니다.", precheck, request_conflicts, payload, None)

    model = cp_model.CpModel()
    x: Dict[Tuple[str, int, str], cp_model.IntVar] = {}
    work: Dict[Tuple[str, int], cp_model.IntVar] = {}
    blocks: Dict[Tuple[str, int, int], cp_model.IntVar] = {}
    carry: Dict[str, Dict[int, str]] = {}

    for nurse in workers:
        nid = nurse["id"]
        carry[nid] = previous_carryover(payload.previousSchedule, nurse, num_days)
        for day in range(1, num_days + 1):
            for shift in SHIFTS:
                x[(nid, day, shift)] = model.NewBoolVar(f"x_{nid}_{day}_{shift}")
            work[(nid, day)] = model.NewBoolVar(f"work_{nid}_{day}")
            model.AddExactlyOne(x[(nid, day, shift)] for shift in SHIFTS)
            model.Add(work[(nid, day)] == sum(x[(nid, day, shift)] for shift in WORK_SHIFTS))
            if carry[nid].get(day):
                model.Add(x[(nid, day, carry[nid][day])] == 1)
            elif request_off.get((nid, day)) == "OFF":
                model.Add(x[(nid, day, "OFF")] == 1)

    for day in range(1, num_days + 1):
        for shift in WORK_SHIFTS:
            assigned = [x[(n["id"], day, shift)] for n in workers]
            model.Add(sum(assigned) >= min_need[shift])
            model.Add(sum(assigned) <= max_need[shift])

    for nurse in workers:
        nid = nurse["id"]
        for day in range(1, num_days):
            model.Add(x[(nid, day, "E")] + x[(nid, day + 1, "D")] <= 1)
        for start in range(1, num_days - 5 + 2):
            model.Add(sum(work[(nid, day)] for day in range(start, start + 5)) <= 4)
        model.Add(sum(x[(nid, day, "OFF")] for day in range(1, num_days + 1)) == off_target)

    for nurse in workers:
        nid = nurse["id"]
        previous_run = previous_night_run_at_end(payload.previousSchedule, nid)
        carried_nights = {day for day, shift in carry[nid].items() if shift == "N"}
        generated_cover = {day: [] for day in range(1, num_days + 1)}
        for length in preferred_night_lengths(nurse):
            for start in range(1, num_days - length + 2):
                if any(day in carried_nights for day in range(start, start + length)):
                    continue
                b = model.NewBoolVar(f"night_block_{nid}_{start}_{length}")
                blocks[(nid, start, length)] = b
                for day in range(start, start + length):
                    generated_cover[day].append(b)
                for off_day in range(start + length, min(num_days, start + length + 1) + 1):
                    model.Add(x[(nid, off_day, "OFF")] == 1).OnlyEnforceIf(b)

        for day in range(1, num_days + 1):
            if day in carried_nights:
                model.Add(x[(nid, day, "N")] == 1)
                if generated_cover[day]:
                    model.Add(sum(generated_cover[day]) == 0)
            elif generated_cover[day]:
                model.Add(x[(nid, day, "N")] == sum(generated_cover[day]))
            else:
                model.Add(x[(nid, day, "N")] == 0)

        total_nights = previous_run + sum(x[(nid, day, "N")] for day in range(1, num_days + 1))
        model.Add(total_nights >= 6)
        model.Add(total_nights <= 7)

    penalties = []
    for day in range(1, num_days + 1):
        for shift in WORK_SHIFTS:
            role_counts = {
                role: sum(x[(n["id"], day, shift)] for n in workers if n.get("role") == role)
                for role in WORK_ROLES
            }
            charge_short = model.NewIntVar(0, 1, f"charge_short_{day}_{shift}")
            model.Add(charge_short >= 1 - role_counts["charge"])
            penalties.append(charge_short * 400)
            charge_over = model.NewIntVar(0, 6, f"charge_over_{day}_{shift}")
            model.Add(charge_over >= role_counts["charge"] - 1)
            penalties.append(charge_over * 80)
            mid_diff = model.NewIntVar(0, 20, f"mid_diff_{day}_{shift}")
            new_diff = model.NewIntVar(0, 20, f"new_diff_{day}_{shift}")
            model.AddAbsEquality(mid_diff, role_counts["mid"] - 3)
            model.AddAbsEquality(new_diff, role_counts["newn"] - 3)
            penalties.extend([mid_diff * 8, new_diff * 8])
            new_over = model.NewIntVar(0, 20, f"new_over_{day}_{shift}")
            model.Add(new_over >= role_counts["newn"] - 4)
            penalties.append(new_over * 30)

    for nurse in workers:
        nid = nurse["id"]
        d_count = sum(x[(nid, day, "D")] for day in range(1, num_days + 1))
        e_count = sum(x[(nid, day, "E")] for day in range(1, num_days + 1))
        de_diff = model.NewIntVar(0, num_days, f"de_diff_{nid}")
        model.AddAbsEquality(de_diff, d_count - e_count)
        penalties.append(de_diff * 3)
        for day in range(1, num_days - 2 + 1):
            scattered = model.NewBoolVar(f"work_off_work_{nid}_{day}")
            model.Add(work[(nid, day)] + x[(nid, day + 1, "OFF")] + work[(nid, day + 2)] == 3).OnlyEnforceIf(scattered)
            model.Add(work[(nid, day)] + x[(nid, day + 1, "OFF")] + work[(nid, day + 2)] <= 2).OnlyEnforceIf(scattered.Not())
            penalties.append(scattered * 7)

    # Prefer 2-night blocks unless the model needs 3-night blocks.
    for (nid, start, length), var in blocks.items():
        if length == 3:
            penalties.append(var * 12)

    model.Minimize(sum(penalties) if penalties else 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(DEFAULT_TIME_LIMIT_SECONDS, min(180, int(payload.timeLimitSeconds or DEFAULT_TIME_LIMIT_SECONDS)))
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return failure_response(
            "solver_infeasible",
            "OR-Tools가 모든 필수조건을 만족하는 근무표를 찾지 못했습니다.",
            explain_infeasible(payload, workers, num_days, off_target, min_need, max_need, request_conflicts),
            request_conflicts,
            payload,
            None,
            solver.StatusName(status),
        )

    schedule: Dict[str, List[str]] = {}
    for nurse in nurses:
        nid = nurse["id"]
        if nurse.get("role") not in WORK_ROLES:
            schedule[nid] = fixed_schedule_for(nurse, year, month, num_days)
            continue
        row = []
        for day in range(1, num_days + 1):
            value = "OFF"
            for shift in SHIFTS:
                if solver.BooleanValue(x[(nid, day, shift)]):
                    value = shift
                    break
            row.append(value)
        schedule[nid] = row

    validation = validate_schedule(payload, schedule, request_conflicts)
    if validation["hard_violations"]:
        return failure_response(
            "validation_failed",
            "생성 후 검증에서 필수조건 위반이 발견되어 근무표를 반환하지 않습니다.",
            validation["hard_violations"],
            request_conflicts,
            payload,
            validation,
            solver.StatusName(status),
        )

    return {
        "ok": True,
        "status": solver.StatusName(status),
        "schedule": schedule,
        "score": int(solver.ObjectiveValue()),
        "objective": solver.ObjectiveValue(),
        "validation": validation,
        "hard_violations": [],
        "warnings": validation["warnings"],
        "unmet_requests": validation["unmet_requests"],
        "staffing_summary": validation["staffing_summary"],
        "grade_summary": validation["grade_summary"],
        "individual_shift_counts": validation["individual_shift_counts"],
    }


def explain_infeasible(payload: SolveRequest, workers: List[Dict[str, Any]], num_days: int, off_target: int, min_need: Dict[str, int], max_need: Dict[str, int], request_conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    reasons = build_precheck(payload, workers, num_days, off_target, min_need, max_need)
    if request_conflicts:
        reasons.append({"type": "off_request_conflicts", "message": "OFF 신청 충돌이 있습니다.", "conflicts": request_conflicts})
    reasons.append({
        "type": "generic_relaxation_suggestions",
        "message": "총량 조건이 맞아도 연속 N/OFF/연속근무/요청 OFF가 조합상 충돌할 수 있습니다.",
        "relax": ["OFF 목표 정확 일치 완화", "개인별 N 6~7개 완화", "일별 N 7~8명 완화", "요청 OFF 일부 미반영 허용"],
    })
    return reasons


def failure_response(kind: str, message: str, hard_violations: Any, request_conflicts: List[Dict[str, Any]], payload: SolveRequest, validation: Dict[str, Any] | None, status: str | None = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "status": status,
        "error": message,
        "reason": kind,
        "schedule": None,
        "hard_violations": hard_violations if isinstance(hard_violations, list) else [hard_violations],
        "warnings": [] if validation is None else validation.get("warnings", []),
        "unmet_requests": [] if validation is None else validation.get("unmet_requests", []),
        "request_conflicts": request_conflicts,
        "staffing_summary": [] if validation is None else validation.get("staffing_summary", []),
        "grade_summary": [] if validation is None else validation.get("grade_summary", []),
        "individual_shift_counts": [] if validation is None else validation.get("individual_shift_counts", []),
        "input_relaxation_suggestions": hard_violations,
        "input_summary": {
            "year": payload.year,
            "month": payload.month,
            "worker_count": len(worker_nurses(payload.nurses)),
            "offTarget": payload.offTarget if payload.offTarget is not None else payload.baseOff,
            "needs": payload.needs,
            "maxNeeds": payload.maxNeeds,
        },
    }


def validate_schedule(payload: SolveRequest, schedule: Dict[str, List[str]], request_conflicts: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    year = payload.year
    month = payload.month
    num_days = days_in_month(year, month)
    nurses = payload.nurses
    workers = worker_nurses(nurses)
    by_id = {n["id"]: n for n in workers}
    off_target = int(payload.offTarget if payload.offTarget is not None else payload.baseOff if payload.baseOff is not None else 10)
    min_need = {"D": max(1, int(payload.needs.get("D") or 8)), "E": max(1, int(payload.needs.get("E") or 8)), "N": NIGHT_MIN}
    max_need = {"D": max(min_need["D"], int(payload.maxNeeds.get("D") or 10)), "E": max(min_need["E"], int(payload.maxNeeds.get("E") or 10)), "N": NIGHT_MAX}
    hard: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    staffing_summary: List[Dict[str, Any]] = []
    grade_summary: List[Dict[str, Any]] = []
    individual: List[Dict[str, Any]] = []
    unmet_requests: List[Dict[str, Any]] = []

    for nurse in workers:
        nid = nurse["id"]
        row = schedule.get(nid, [])
        counts = Counter(row)
        individual.append({"nurseId": nid, "name": nurse_name(nurse), "role": nurse.get("role"), "D": counts["D"], "E": counts["E"], "N": counts["N"], "OFF": counts["OFF"]})
        for idx, value in enumerate(row, start=1):
            if value not in SHIFTS:
                hard.append({"type": "invalid_shift", "nurseId": nid, "name": nurse_name(nurse), "day": idx, "value": value})
        if counts["OFF"] != off_target:
            hard.append({"type": "off_target_mismatch", "nurseId": nid, "name": nurse_name(nurse), "off": counts["OFF"], "target": off_target})
        for day in range(1, num_days):
            if row[day - 1] == "E" and row[day] == "D":
                hard.append({"type": "evening_to_day", "nurseId": nid, "name": nurse_name(nurse), "fromDay": day, "toDay": day + 1})
        previous_run = previous_night_run_at_end(payload.previousSchedule, nid)
        day = 1
        while day <= num_days:
            if row[day - 1] != "N":
                day += 1
                continue
            start = day
            while day <= num_days and row[day - 1] == "N":
                day += 1
            length = day - start
            total_length = length + previous_run if start == 1 else length
            allowed = preferred_night_lengths(nurse)
            if total_length not in allowed:
                hard.append({"type": "invalid_night_block_length", "nurseId": nid, "name": nurse_name(nurse), "startDay": start, "length": total_length, "allowed": allowed})
            if total_length == 1:
                hard.append({"type": "single_night", "nurseId": nid, "name": nurse_name(nurse), "day": start})
            if total_length >= 4:
                hard.append({"type": "night_run_too_long", "nurseId": nid, "name": nurse_name(nurse), "startDay": start, "length": total_length})
            for off_day in range(day, min(num_days, day + 1) + 1):
                if row[off_day - 1] != "OFF":
                    hard.append({"type": "night_recovery_off_missing", "nurseId": nid, "name": nurse_name(nurse), "nightStartDay": start, "day": off_day, "actual": row[off_day - 1]})
            if day <= num_days and row[day - 1] in {"D", "E"}:
                hard.append({"type": "night_next_day_work", "nurseId": nid, "name": nurse_name(nurse), "day": day, "actual": row[day - 1]})
        if counts["N"] and (counts["N"] < 6 or counts["N"] > 7):
            hard.append({"type": "night_count_out_of_range", "nurseId": nid, "name": nurse_name(nurse), "night": counts["N"], "range": [6, 7]})

    night_counts = [item["N"] for item in individual]
    if night_counts and max(night_counts) - min(night_counts) > max(1, int(payload.nightTolerance or 1)):
        hard.append({"type": "night_count_variance", "min": min(night_counts), "max": max(night_counts), "allowedDifference": max(1, int(payload.nightTolerance or 1))})

    for day in range(1, num_days + 1):
        for shift in WORK_SHIFTS:
            assigned = [n for n in workers if (schedule.get(n["id"], []) + [""] * num_days)[day - 1] == shift]
            role_counts = Counter(n.get("role") for n in assigned)
            item = {"day": day, "shift": shift, "count": len(assigned), "min": min_need[shift], "max": max_need[shift]}
            staffing_summary.append(item)
            grade_summary.append({"day": day, "shift": shift, "charge": role_counts["charge"], "mid": role_counts["mid"], "newn": role_counts["newn"]})
            if len(assigned) < min_need[shift]:
                hard.append({"type": "staffing_under_minimum", **item})
            if len(assigned) > max_need[shift]:
                hard.append({"type": "staffing_over_maximum", **item})
            if len(assigned) > 0 and role_counts["charge"] == 0:
                warnings.append({"type": "no_charge_on_shift", "day": day, "shift": shift})
            if role_counts["newn"] > 4:
                warnings.append({"type": "too_many_newn", "day": day, "shift": shift, "newn": role_counts["newn"]})

    request_off, conflicts = grouped_off_requests(payload, workers)
    for (nid, day), shift in request_off.items():
        if (schedule.get(nid, []) + [""] * num_days)[day - 1] != shift:
            nurse = by_id.get(nid, {"name": nid, "role": ""})
            unmet_requests.append({"nurseId": nid, "name": nurse_name(nurse), "role": nurse.get("role"), "day": day, "requested": shift, "actual": schedule.get(nid, [None] * num_days)[day - 1]})
    if unmet_requests:
        hard.extend({"type": "requested_off_unmet", **item} for item in unmet_requests)
    for conflict in conflicts:
        warnings.append(conflict)

    same_grade_conflicts = []
    for day in range(1, num_days + 1):
        role_off = defaultdict(list)
        for nurse in workers:
            if (schedule.get(nurse["id"], []) + [""] * num_days)[day - 1] == "OFF" and request_off.get((nurse["id"], day)) == "OFF":
                role_off[nurse.get("role")].append({"nurseId": nurse["id"], "name": nurse_name(nurse)})
        for role, items in role_off.items():
            if len(items) > 1:
                same_grade_conflicts.append({"type": "same_grade_requested_off_overlap", "day": day, "role": role, "requests": items})
    warnings.extend(same_grade_conflicts)

    return {
        "hard_violations": hard,
        "warnings": warnings,
        "unmet_requests": unmet_requests,
        "staffing_summary": staffing_summary,
        "grade_summary": grade_summary,
        "individual_shift_counts": individual,
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
