from collections import Counter, defaultdict
from datetime import datetime
from math import floor
from typing import Any, Dict, List, Tuple

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ortools.sat.python import cp_model
from pydantic import BaseModel, Field


SHIFTS = ("D", "E", "N", "OFF")
WORK_SHIFTS = ("D", "E", "N")
WORK_GROUPS = {"charge", "middle", "junior"}
LEE_HYEMI = "\uc774\ud61c\ubbf8"
SPECIAL_NIGHT_RULES = {
    LEE_HYEMI: {
        "night_total": 6,
        "block_count": 2,
        "block_lengths": [3, 3],
    }
}
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


def nurse_name(nurse: Dict[str, Any]) -> str:
    return str(nurse.get("name") or nurse.get("id") or "")


def role_group(role: Any) -> str:
    raw = str(role or "").strip().lower()
    if raw in {"charge", "\ucc28\uc9c0"}:
        return "charge"
    if raw in {"mid", "middle", "acting", "\uc561\ud305", "\uc911\uac04"}:
        return "middle"
    if raw in {"newn", "junior", "\uc2e0\uaddc"}:
        return "junior"
    return raw


def worker_nurses(nurses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [n for n in nurses if role_group(n.get("role")) in WORK_GROUPS]


def normalize_shift(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if raw in {"O", "OF", "OFF"}:
        return "OFF"
    if raw in {"D", "E", "N"}:
        return raw
    return raw


def request_shift(req: Dict[str, Any]) -> str:
    return normalize_shift(req.get("shift") or req.get("type"))


def preferred_night_lengths(nurse: Dict[str, Any]) -> List[int]:
    return [3] if nurse_name(nurse) == LEE_HYEMI else [2, 3]


def special_night_rule(nurse: Dict[str, Any]) -> Dict[str, Any] | None:
    return SPECIAL_NIGHT_RULES.get(nurse_name(nurse))


def previous_night_run_at_end(previous: Dict[str, List[str]], nurse_id: str) -> int:
    row = [normalize_shift(v) for v in (previous.get(nurse_id, []) or [])]
    if not row or row[-1] != "N":
        return 0
    run = 0
    for value in reversed(row):
        if value != "N":
            break
        run += 1
    return run


def previous_carryover(previous: Dict[str, List[str]], nurse: Dict[str, Any], num_days: int) -> Dict[int, str]:
    run = previous_night_run_at_end(previous, nurse["id"])
    out: Dict[int, str] = {}
    if run == 1:
        target_len = 3 if nurse_name(nurse) == LEE_HYEMI else 2
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


def fixed_schedule_for(nurse: Dict[str, Any], year: int, month: int, num_days: int) -> List[str]:
    role = str(nurse.get("role") or "").lower()
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


def daily_needs(payload: SolveRequest) -> Tuple[Dict[str, int], Dict[str, int]]:
    min_need = {
        "D": max(1, int(payload.needs.get("D") or 8)),
        "E": max(1, int(payload.needs.get("E") or 8)),
        "N": max(1, int(payload.needs.get("N") or 7)),
    }
    max_need = {
        "D": max(min_need["D"], int(payload.maxNeeds.get("D") or 10)),
        "E": max(min_need["E"], int(payload.maxNeeds.get("E") or 9)),
        "N": max(min_need["N"], int(payload.maxNeeds.get("N") or 8)),
    }
    return min_need, max_need


def off_target(payload: SolveRequest) -> int:
    return int(payload.offTarget if payload.offTarget is not None else payload.baseOff if payload.baseOff is not None else 11)


def grouped_off_requests(payload: SolveRequest, workers: List[Dict[str, Any]]) -> Tuple[Dict[Tuple[str, int], str], List[Dict[str, Any]]]:
    worker_ids = {n["id"] for n in workers}
    by_id = {n["id"]: n for n in workers}
    accepted: Dict[Tuple[str, int], str] = {}
    conflicts: List[Dict[str, Any]] = []
    by_day: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    by_day_grade: Dict[Tuple[int, str], List[Dict[str, Any]]] = defaultdict(list)
    num_days = days_in_month(payload.year, payload.month)

    for req in payload.requests:
        nid = req.get("nurseId")
        day = int(req.get("day") or 0)
        if nid not in worker_ids or not (1 <= day <= num_days) or request_shift(req) != "OFF":
            continue
        nurse = by_id[nid]
        item = {
            "nurseId": nid,
            "name": nurse_name(nurse),
            "day": day,
            "shift": "OFF",
            "role": nurse.get("role"),
            "grade": role_group(nurse.get("role")),
        }
        by_day[day].append(item)
        by_day_grade[(day, item["grade"])].append(item)

    blocked = set()
    for day, items in by_day.items():
        if len(items) > 3:
            conflicts.append({"type": "daily_off_request_limit", "day": day, "limit": 3, "requests": items})
            blocked.update((item["nurseId"], day) for item in items[3:])

    for (day, grade), items in by_day_grade.items():
        if len(items) > 1:
            conflicts.append({"type": "same_grade_off_request_conflict", "day": day, "grade": grade, "requests": items})
            blocked.update((item["nurseId"], day) for item in items[1:])

    for items in by_day.values():
        for item in items:
            key = (item["nurseId"], item["day"])
            if key not in blocked:
                accepted[key] = "OFF"
    return accepted, conflicts


def night_targets(worker_count: int, num_days: int, n_required: int) -> Tuple[int, int, int]:
    total = num_days * n_required
    return total, floor(total / worker_count), total % worker_count


def build_precheck(
    payload: SolveRequest,
    workers: List[Dict[str, Any]],
    num_days: int,
    target_off: int,
    min_need: Dict[str, int],
    max_need: Dict[str, int],
    request_conflicts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    problems = []
    worker_count = len(workers)
    if worker_count == 0:
        return [{"type": "no_workers", "message": "3-shift worker list is empty."}]

    total_slots = worker_count * num_days
    required_work_min = num_days * sum(min_need[s] for s in WORK_SHIFTS)
    required_work_max = num_days * sum(max_need[s] for s in WORK_SHIFTS)
    available_work = total_slots - (worker_count * target_off)
    if available_work < required_work_min:
        problems.append({
            "type": "too_many_required_off",
            "message": "Exact OFF target leaves too few work slots for daily minimum staffing.",
            "available_work": available_work,
            "required_work_min": required_work_min,
            "relax": ["lower OFF target", "lower D/E/N minimum", "add more 3-shift nurses"],
        })
    if available_work > required_work_max:
        problems.append({
            "type": "too_few_required_off",
            "message": "Exact OFF target leaves more work slots than daily maximum staffing allows.",
            "available_work": available_work,
            "required_work_max": required_work_max,
            "relax": ["raise OFF target", "raise D/E maximum staffing"],
        })

    grades = Counter(role_group(n.get("role")) for n in workers)
    if grades["charge"] < 1:
        problems.append({"type": "charge_shortage", "message": "No charge nurse is available."})
    if grades["middle"] < 1:
        problems.append({"type": "middle_shortage", "message": "No middle/acting nurse is available."})
    if worker_count - grades["junior"] < 2:
        problems.append({"type": "grade_mix_shortage", "message": "Every shift needs at least one charge and one middle nurse."})

    total_nights, night_floor, night_remainder = night_targets(worker_count, num_days, min_need["N"])
    if total_nights > worker_count * num_days:
        problems.append({"type": "night_total_too_high", "total_nights": total_nights})
    for nurse in workers:
        rule = special_night_rule(nurse)
        if rule and int(rule["night_total"]) not in {night_floor, night_floor + 1}:
            problems.append({
                "type": "hye_mi_night_block_impossible",
                "message": "Lee Hye-mi must receive exactly six nights in two 3-night blocks, but floor/ceil night target is incompatible.",
                "special_rule": rule,
                "night_floor": night_floor,
                "night_remainder": night_remainder,
            })
            break

    if request_conflicts:
        problems.append({"type": "off_request_conflicts", "message": "Some OFF requests conflict and will not be confirmed.", "conflicts": request_conflicts})
    return problems


def solve(payload: SolveRequest) -> Dict[str, Any]:
    year = payload.year
    month = payload.month
    num_days = days_in_month(year, month)
    nurses = payload.nurses
    workers = worker_nurses(nurses)
    target_off = off_target(payload)
    min_need, max_need = daily_needs(payload)
    request_off, request_conflicts = grouped_off_requests(payload, workers)
    precheck = build_precheck(payload, workers, num_days, target_off, min_need, max_need, request_conflicts)
    # OFF request conflicts are returned, but non-blocking; all other precheck issues are hard.
    blocking_precheck = [p for p in precheck if p.get("type") != "off_request_conflicts"]
    if blocking_precheck:
        return failure_response("precheck_failed", "Input conditions are infeasible before solving.", blocking_precheck, precheck, payload, None)

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

            charge = sum(x[(n["id"], day, shift)] for n in workers if role_group(n.get("role")) == "charge")
            middle = sum(x[(n["id"], day, shift)] for n in workers if role_group(n.get("role")) == "middle")
            junior = sum(x[(n["id"], day, shift)] for n in workers if role_group(n.get("role")) == "junior")
            model.Add(charge >= 1)
            model.Add(middle >= 1)
            model.Add(junior <= 4)

    total_required_nights, night_floor, night_remainder = night_targets(len(workers), num_days, min_need["N"])
    high_night: Dict[str, cp_model.IntVar] = {}
    model.Add(sum(x[(n["id"], day, "N")] for n in workers for day in range(1, num_days + 1)) == total_required_nights)
    for nurse in workers:
        nid = nurse["id"]
        high_night[nid] = model.NewBoolVar(f"night_high_{nid}")
    model.Add(sum(high_night.values()) == night_remainder)

    for nurse in workers:
        nid = nurse["id"]
        row_nights = [x[(nid, day, "N")] for day in range(1, num_days + 1)]
        rule = special_night_rule(nurse)
        if rule:
            model.Add(high_night[nid] == int(rule["night_total"]) - night_floor)
            model.Add(sum(row_nights) == int(rule["night_total"]))
        else:
            model.Add(sum(row_nights) == night_floor + high_night[nid])
        model.Add(sum(x[(nid, day, "OFF")] for day in range(1, num_days + 1)) == target_off)

        for day in range(1, num_days):
            model.Add(x[(nid, day, "E")] + x[(nid, day + 1, "D")] <= 1)
            model.Add(x[(nid, day, "N")] + x[(nid, day + 1, "D")] <= 1)
            model.Add(x[(nid, day, "N")] + x[(nid, day + 1, "E")] <= 1)
        for start in range(1, num_days - 5 + 2):
            model.Add(sum(work[(nid, day)] for day in range(start, start + 5)) <= 4)

        carried_nights = {day for day, shift in carry[nid].items() if shift == "N"}
        generated_cover: Dict[int, List[cp_model.IntVar]] = {day: [] for day in range(1, num_days + 1)}
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

        if rule:
            nurse_blocks = [var for (block_nid, _start, length), var in blocks.items() if block_nid == nid and length == 3]
            model.Add(sum(nurse_blocks) == int(rule["block_count"]))

        for day in range(1, num_days + 1):
            if day in carried_nights:
                model.Add(x[(nid, day, "N")] == 1)
                if generated_cover[day]:
                    model.Add(sum(generated_cover[day]) == 0)
            elif generated_cover[day]:
                model.Add(x[(nid, day, "N")] == sum(generated_cover[day]))
            else:
                model.Add(x[(nid, day, "N")] == 0)

    # Phase 1 is satisfaction only: a schedule that breaks no hard rule is more
    # important than a prettier but slow-to-prove objective.

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(DEFAULT_TIME_LIMIT_SECONDS, min(240, int(payload.timeLimitSeconds or DEFAULT_TIME_LIMIT_SECONDS)))
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        reasons = explain_infeasible(payload, workers, num_days, target_off, min_need, max_need, precheck)
        return failure_response("solver_infeasible", "OR-Tools could not find a schedule satisfying all hard constraints.", reasons, precheck, payload, None, solver.StatusName(status))

    schedule: Dict[str, List[str]] = {}
    for nurse in nurses:
        nid = nurse["id"]
        if role_group(nurse.get("role")) not in WORK_GROUPS:
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

    validation = validate_schedule(payload, schedule, precheck)
    if validation["hard_violations"]:
        return failure_response("validation_failed", "Generated schedule failed hard validation and will not be returned as successful.", validation["hard_violations"], precheck, payload, validation, solver.StatusName(status))

    return success_response(schedule, validation, schedule_score(validation), solver.StatusName(status))


def explain_infeasible(
    payload: SolveRequest,
    workers: List[Dict[str, Any]],
    num_days: int,
    target_off: int,
    min_need: Dict[str, int],
    max_need: Dict[str, int],
    precheck: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    reasons = [p for p in precheck if p.get("type") != "off_request_conflicts"]
    if not reasons:
        total_nights, night_floor, night_remainder = night_targets(len(workers), num_days, min_need["N"])
        reasons.append({
            "type": "constraint_combination_conflict",
            "message": "The exact OFF count, daily staffing, grade mix, night block, and recovery rules conflict.",
            "night_total": total_nights,
            "night_floor": night_floor,
            "night_remainder": night_remainder,
            "off_target": target_off,
            "daily_min": min_need,
            "daily_max": max_need,
            "relax": ["lower exact OFF target", "allow one more D/E maximum", "add charge or middle nurse", "reduce OFF requests"],
        })
    return reasons


def success_response(schedule: Dict[str, List[str]], validation: Dict[str, Any], score: int, status: str) -> Dict[str, Any]:
    return {
        "success": True,
        "ok": True,
        "status": status,
        "schedule": schedule,
        "score": score,
        "objective": score,
        "validation": validation,
        "hard_violations": [],
        "warnings": validation["warnings"],
        "infeasible_reasons": [],
        "unmet_requests": validation["unmet_requests"],
        "daily_staffing_summary": validation["daily_staffing_summary"],
        "staffing_summary": validation["daily_staffing_summary"],
        "grade_summary": validation["grade_summary"],
        "individual_shift_counts": validation["individual_shift_counts"],
        "off_summary": validation["off_summary"],
        "night_distribution": validation["night_distribution"],
        "transition_violations": validation["transition_violations"],
        "special_rule_results": validation["special_rule_results"],
        "next_month_carryover_off": validation["next_month_carryover_off"],
    }


def schedule_score(validation: Dict[str, Any]) -> int:
    if validation.get("hard_violations"):
        return 0
    score = 100000
    score -= len(validation.get("warnings", [])) * 100
    for item in validation.get("individual_shift_counts", []):
        score -= abs(int(item.get("D", 0)) - int(item.get("E", 0))) * 12
    for item in validation.get("grade_summary", []):
        score -= abs(int(item.get("charge_count", 0)) - 1) * 8
        score -= abs(int(item.get("middle_count", 0)) - 3) * 3
        score -= abs(int(item.get("junior_count", 0)) - 3) * 3
    return max(0, int(score))


def failure_response(
    kind: str,
    message: str,
    hard_violations: Any,
    precheck: List[Dict[str, Any]],
    payload: SolveRequest,
    validation: Dict[str, Any] | None,
    status: str | None = None,
) -> Dict[str, Any]:
    hard_list = hard_violations if isinstance(hard_violations, list) else [hard_violations]
    return {
        "success": False,
        "ok": False,
        "status": status,
        "error": message,
        "reason": kind,
        "schedule": None,
        "hard_violations": hard_list,
        "warnings": [] if validation is None else validation.get("warnings", []),
        "infeasible_reasons": hard_list,
        "unmet_requests": [] if validation is None else validation.get("unmet_requests", []),
        "request_conflicts": [p for p in precheck if p.get("type") == "off_request_conflicts"],
        "daily_staffing_summary": [] if validation is None else validation.get("daily_staffing_summary", []),
        "staffing_summary": [] if validation is None else validation.get("daily_staffing_summary", []),
        "grade_summary": [] if validation is None else validation.get("grade_summary", []),
        "individual_shift_counts": [] if validation is None else validation.get("individual_shift_counts", []),
        "off_summary": [] if validation is None else validation.get("off_summary", []),
        "night_distribution": [] if validation is None else validation.get("night_distribution", []),
        "transition_violations": [] if validation is None else validation.get("transition_violations", []),
        "special_rule_results": [] if validation is None else validation.get("special_rule_results", []),
        "next_month_carryover_off": [] if validation is None else validation.get("next_month_carryover_off", []),
        "input_summary": {
            "year": payload.year,
            "month": payload.month,
            "worker_count": len(worker_nurses(payload.nurses)),
            "offTarget": off_target(payload),
            "needs": payload.needs,
            "maxNeeds": payload.maxNeeds,
        },
    }


def validate_schedule(payload: SolveRequest, schedule: Dict[str, List[str]], precheck: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    num_days = days_in_month(payload.year, payload.month)
    workers = worker_nurses(payload.nurses)
    by_id = {n["id"]: n for n in workers}
    target_off = off_target(payload)
    min_need, max_need = daily_needs(payload)
    total_required_nights, night_floor, night_remainder = night_targets(len(workers), num_days, min_need["N"])
    hard: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    unmet_requests: List[Dict[str, Any]] = []
    daily_staffing: List[Dict[str, Any]] = []
    grade_summary: List[Dict[str, Any]] = []
    individual: List[Dict[str, Any]] = []
    off_summary: List[Dict[str, Any]] = []
    night_distribution: List[Dict[str, Any]] = []
    transition_violations: List[Dict[str, Any]] = []
    special_rule_results: List[Dict[str, Any]] = []
    next_month_carryover_off: List[Dict[str, Any]] = []

    for item in precheck or []:
        if item.get("type") == "off_request_conflicts":
            warnings.append(item)

    for nurse in workers:
        nid = nurse["id"]
        row = (schedule.get(nid, []) + [""] * num_days)[:num_days]
        counts = Counter(row)
        individual.append({"nurseId": nid, "name": nurse_name(nurse), "role": nurse.get("role"), "grade": role_group(nurse.get("role")), "D": counts["D"], "E": counts["E"], "N": counts["N"], "OFF": counts["OFF"]})
        off_diff = counts["OFF"] - target_off
        off_summary.append({"nurseId": nid, "name": nurse_name(nurse), "required_off": target_off, "actual_off": counts["OFF"], "off_difference": off_diff, "difference": off_diff})
        for value in (night_floor, night_floor + 1):
            if counts["N"] == value:
                break
        else:
            hard.append({"type": "night_distribution_mismatch", "nurseId": nid, "name": nurse_name(nurse), "night": counts["N"], "allowed": [night_floor, night_floor + 1]})
        night_distribution.append({"nurseId": nid, "name": nurse_name(nurse), "night_count": counts["N"], "allowed_floor": night_floor, "allowed_ceil": night_floor + 1})

        for day, value in enumerate(row, start=1):
            if value not in SHIFTS:
                hard.append({"type": "invalid_shift", "nurseId": nid, "name": nurse_name(nurse), "day": day, "value": value})
        if counts["OFF"] != target_off:
            hard.append({"type": "off_target_mismatch", "nurseId": nid, "name": nurse_name(nurse), "actual": counts["OFF"], "required": target_off, "diff": counts["OFF"] - target_off})
        for day in range(1, num_days):
            if row[day - 1] == "E" and row[day] == "D":
                item = {"type": "E_TO_D", "nurseId": nid, "nurse": nurse_name(nurse), "name": nurse_name(nurse), "from_date": day, "to_date": day + 1, "fromDay": day, "toDay": day + 1}
                transition_violations.append(item)
                hard.append(item)
            if row[day - 1] == "N" and row[day] in {"D", "E"}:
                item = {"type": "N_TO_WORK", "nurseId": nid, "nurse": nurse_name(nurse), "name": nurse_name(nurse), "from_date": day, "to_date": day + 1, "fromDay": day, "toDay": day + 1, "actual": row[day]}
                transition_violations.append(item)
                hard.append(item)

        previous_run = previous_night_run_at_end(payload.previousSchedule, nid)
        day = 1
        current_month_night_blocks: List[int] = []
        while day <= num_days:
            if row[day - 1] != "N":
                day += 1
                continue
            start = day
            while day <= num_days and row[day - 1] == "N":
                day += 1
            length = day - start
            current_month_night_blocks.append(length)
            total_length = length + previous_run if start == 1 else length
            allowed = preferred_night_lengths(nurse)
            if total_length not in allowed:
                hard.append({"type": "invalid_night_block_length", "nurseId": nid, "name": nurse_name(nurse), "startDay": start, "length": total_length, "allowed": allowed})
            if total_length == 1:
                hard.append({"type": "single_night", "nurseId": nid, "name": nurse_name(nurse), "day": start})
            if total_length >= 4:
                hard.append({"type": "night_run_too_long", "nurseId": nid, "name": nurse_name(nurse), "startDay": start, "length": total_length})
            future_off_days = []
            for off_day in range(day, day + 2):
                if off_day <= num_days:
                    if row[off_day - 1] != "OFF":
                        hard.append({"type": "night_recovery_off_missing", "nurseId": nid, "name": nurse_name(nurse), "nightStartDay": start, "day": off_day, "actual": row[off_day - 1]})
                else:
                    future_off_days.append(off_day - num_days)
            if future_off_days:
                carry_item = {
                    "nurseId": nid,
                    "nurse_name": nurse_name(nurse),
                    "night_block_start_day": start,
                    "night_block_length": length,
                    "required_off_dates_next_month": future_off_days,
                }
                next_month_carryover_off.append(carry_item)
                warnings.append({"type": "boundary_warning", **carry_item})

        rule = special_night_rule(nurse)
        if rule:
            actual_blocks = sorted(current_month_night_blocks)
            expected_blocks = sorted(int(v) for v in rule["block_lengths"])
            ok = counts["N"] == int(rule["night_total"]) and actual_blocks == expected_blocks
            result = {
                "nurseId": nid,
                "name": nurse_name(nurse),
                "rule": rule,
                "actual_night_total": counts["N"],
                "actual_block_lengths": actual_blocks,
                "passed": ok,
            }
            special_rule_results.append(result)
            if not ok:
                hard.append({"type": "special_night_rule_failed", **result})

    high_count = sum(1 for item in night_distribution if item["night_count"] == night_floor + 1)
    total_nights = sum(item["night_count"] for item in night_distribution)
    if total_nights != total_required_nights:
        hard.append({"type": "night_total_mismatch", "actual": total_nights, "required": total_required_nights})
    if high_count != night_remainder:
        hard.append({"type": "night_remainder_mismatch", "actual_high_count": high_count, "required_high_count": night_remainder})

    for day in range(1, num_days + 1):
        for shift in WORK_SHIFTS:
            assigned = [n for n in workers if (schedule.get(n["id"], []) + [""] * num_days)[day - 1] == shift]
            grades = Counter(role_group(n.get("role")) for n in assigned)
            staffing = {"day": day, "shift": shift, "count": len(assigned), "min": min_need[shift], "max": max_need[shift]}
            daily_staffing.append(staffing)
            grade_item = {
                "day": day,
                "shift": shift,
                "charge_count": grades["charge"],
                "middle_count": grades["middle"],
                "junior_count": grades["junior"],
                "grade_violation": False,
            }
            if len(assigned) < min_need[shift]:
                hard.append({"type": "staffing_under_minimum", **staffing})
            if len(assigned) > max_need[shift]:
                hard.append({"type": "staffing_over_maximum", **staffing})
            if grades["charge"] < 1:
                grade_item["grade_violation"] = True
                hard.append({"type": "no_charge_on_shift", "day": day, "shift": shift, **grade_item})
            if grades["middle"] < 1:
                grade_item["grade_violation"] = True
                hard.append({"type": "no_middle_on_shift", "day": day, "shift": shift, **grade_item})
            if grades["junior"] >= 5:
                grade_item["grade_violation"] = True
                hard.append({"type": "too_many_junior_on_shift", "day": day, "shift": shift, **grade_item})
            grade_summary.append(grade_item)

    request_off, conflicts = grouped_off_requests(payload, workers)
    for conflict in conflicts:
        warnings.append(conflict)
    for (nid, day), shift in request_off.items():
        actual = (schedule.get(nid, []) + [""] * num_days)[day - 1]
        if actual != shift:
            nurse = by_id.get(nid, {"name": nid, "role": ""})
            item = {"nurseId": nid, "name": nurse_name(nurse), "role": nurse.get("role"), "day": day, "requested": shift, "actual": actual}
            unmet_requests.append(item)
            hard.append({"type": "requested_off_unmet", **item})

    return {
        "hard_violations": hard,
        "warnings": warnings,
        "unmet_requests": unmet_requests,
        "daily_staffing_summary": daily_staffing,
        "staffing_summary": daily_staffing,
        "grade_summary": grade_summary,
        "individual_shift_counts": individual,
        "off_summary": off_summary,
        "night_distribution": night_distribution,
        "transition_violations": transition_violations,
        "special_rule_results": special_rule_results,
        "next_month_carryover_off": next_month_carryover_off,
    }


@app.get("/")
def root() -> Dict[str, Any]:
    return {"ok": True, "success": True, "service": "nurse-autoschedule", "engine": "OR-Tools CP-SAT"}


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "success": True}


@app.post("/solve")
def solve_endpoint(payload: SolveRequest) -> Dict[str, Any]:
    return solve(payload)
