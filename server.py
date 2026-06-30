from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ortools.sat.python import cp_model
from pydantic import BaseModel, Field


SHIFTS = ("D", "E", "N", "OFF")
WORK_SHIFTS = ("D", "E", "N")
WORK_GROUPS = ("charge", "middle", "junior")
LEE_HYEMI = "이혜미"
DEFAULT_TIME_LIMIT_SECONDS = 120

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nurse-autoschedule")

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
    nurses: list[dict[str, Any]]
    requests: list[dict[str, Any]] = Field(default_factory=list)
    previousSchedule: dict[str, list[str]] = Field(default_factory=dict)
    needs: dict[str, int] = Field(default_factory=dict)
    maxNeeds: dict[str, int] = Field(default_factory=dict)
    required_off: int | None = None
    offTarget: int | None = None
    baseOff: int | None = None
    timeLimitSeconds: int = DEFAULT_TIME_LIMIT_SECONDS


def days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (datetime(year, month + 1, 1) - datetime(year, month, 1)).days


def role_group(value: Any) -> str:
    role = str(value or "").strip().lower()
    if role in {"charge", "차지"}:
        return "charge"
    if role in {"mid", "middle", "acting", "액팅", "중간"}:
        return "middle"
    if role in {"newn", "junior", "신규"}:
        return "junior"
    return role


def worker_nurses(nurses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [n for n in nurses if role_group(n.get("role")) in WORK_GROUPS]


def nurse_name(nurse: dict[str, Any]) -> str:
    return str(nurse.get("name") or nurse.get("id") or "")


def normalize_shift(value: Any) -> str:
    shift = str(value or "").strip().upper()
    if shift in {"O", "OF", "OFF"}:
        return "OFF"
    return shift


def requested_off(payload: SolveRequest, worker_ids: set[str], num_days: int) -> tuple[set[tuple[str, int]], list[dict[str, Any]]]:
    confirmed: set[tuple[str, int]] = set()
    by_day: dict[int, list[str]] = defaultdict(list)
    by_worker = {str(n["id"]): n for n in worker_nurses(payload.nurses)}

    for item in payload.requests:
        nurse_id = str(item.get("nurseId") or item.get("nurse_id") or "")
        day = int(item.get("day") or 0)
        shift = normalize_shift(item.get("shift") or item.get("type"))
        if nurse_id in worker_ids and 1 <= day <= num_days and shift == "OFF":
            confirmed.add((nurse_id, day))
            by_day[day].append(nurse_id)

    conflicts: list[dict[str, Any]] = []
    for day, ids in sorted(by_day.items()):
        if len(ids) > 3:
            conflicts.append({
                "type": "daily_off_request_limit",
                "day": day,
                "actual": len(ids),
                "required": "3 이하",
                "message": f"{day}일 확정 희망 OFF가 {len(ids)}명으로 하루 최대 3명을 초과합니다.",
            })
        grades = Counter(role_group(by_worker[nid].get("role")) for nid in ids)
        for grade, count in grades.items():
            if count > 1:
                conflicts.append({
                    "type": "same_grade_off_request_conflict",
                    "day": day,
                    "grade": grade,
                    "actual": count,
                    "required": "가능하면 1명",
                    "message": f"{day}일 {grade} 희망 OFF가 {count}명 겹칩니다.",
                    "warning_only": True,
                })
    return confirmed, conflicts


def staffing_limits(payload: SolveRequest) -> tuple[dict[str, int], dict[str, int]]:
    minimum = {
        shift: max(1, int(payload.needs.get(shift) or default))
        for shift, default in (("D", 8), ("E", 8), ("N", 7))
    }
    maximum = {
        shift: max(minimum[shift], int(payload.maxNeeds.get(shift) or default))
        for shift, default in (("D", 10), ("E", 9), ("N", 8))
    }
    return minimum, maximum


def required_off(payload: SolveRequest) -> int:
    values = (payload.required_off, payload.offTarget, payload.baseOff, 11)
    return max(0, int(next(value for value in values if value is not None)))


def balanced_staffing_targets(
    worker_count: int,
    num_days: int,
    exact_off: int,
    minimum: dict[str, int],
    maximum: dict[str, int],
) -> list[dict[str, int]]:
    targets = [{shift: minimum[shift] for shift in WORK_SHIFTS} for _ in range(num_days)]
    remaining = worker_count * (num_days - exact_off) - num_days * sum(minimum.values())
    for shift in WORK_SHIFTS:
        while remaining > 0 and any(day[shift] < maximum[shift] for day in targets):
            for day in targets:
                if remaining <= 0:
                    break
                if day[shift] < maximum[shift]:
                    day[shift] += 1
                    remaining -= 1
    if remaining:
        raise ValueError("Daily maximum staffing cannot absorb all required work slots.")
    return targets


def previous_boundary(
    payload: SolveRequest,
    nurse: dict[str, Any],
    num_days: int,
) -> tuple[dict[int, str], bool, int]:
    row = [normalize_shift(value) for value in payload.previousSchedule.get(str(nurse["id"]), [])]
    row = [value for value in row if value]
    if not row:
        return {}, False, 0

    previous_ends_evening = row[-1] == "E"
    trailing_nights = 0
    for value in reversed(row):
        if value != "N":
            break
        trailing_nights += 1

    fixed: dict[int, str] = {}
    if trailing_nights:
        target_length = 3 if nurse_name(nurse) == LEE_HYEMI else 2
        continuation = max(0, target_length - trailing_nights)
        for day in range(1, min(num_days, continuation) + 1):
            fixed[day] = "N"
        for day in range(continuation + 1, min(num_days, continuation + 2) + 1):
            fixed[day] = "OFF"
    return fixed, previous_ends_evening, trailing_nights


def solve_night_plan(
    payload: SolveRequest,
    workers: list[dict[str, Any]],
    num_days: int,
    daily_targets: list[dict[str, int]],
    off_requests: set[tuple[str, int]],
) -> tuple[dict[str, list[int]], str]:
    model = cp_model.CpModel()
    night: dict[tuple[str, int], cp_model.IntVar] = {}
    blocks: dict[tuple[str, int, int], cp_model.IntVar] = {}
    boundaries = {
        str(nurse["id"]): previous_boundary(payload, nurse, num_days)
        for nurse in workers
    }

    for nurse in workers:
        nurse_id = str(nurse["id"])
        for day in range(1, num_days + 1):
            night[nurse_id, day] = model.NewBoolVar(f"night_{nurse_id}_{day}")
            if (nurse_id, day) in off_requests or boundaries[nurse_id][0].get(day) == "OFF":
                model.Add(night[nurse_id, day] == 0)

        coverage: dict[int, list[cp_model.IntVar]] = defaultdict(list)
        employee_blocks: list[cp_model.IntVar] = []
        fixed_days = set(boundaries[nurse_id][0])
        lengths = (3,) if nurse_name(nurse) == LEE_HYEMI else (2, 3)
        for length in lengths:
            for start in range(1, num_days - length + 2):
                if fixed_days.intersection(range(start, start + length)):
                    continue
                block = model.NewBoolVar(f"night_block_{nurse_id}_{start}_{length}")
                blocks[nurse_id, start, length] = block
                employee_blocks.append(block)
                for day in range(start, start + length):
                    coverage[day].append(block)
                for recovery_day in (start + length, start + length + 1):
                    if recovery_day <= num_days:
                        model.Add(night[nurse_id, recovery_day] == 0).OnlyEnforceIf(block)

        for day in range(1, num_days + 1):
            if boundaries[nurse_id][0].get(day) == "N":
                model.Add(night[nurse_id, day] == 1)
                model.Add(sum(coverage.get(day, [])) == 0)
            else:
                model.Add(night[nurse_id, day] == sum(coverage.get(day, [])))

        if nurse_name(nurse) == LEE_HYEMI:
            carried = 1 if boundaries[nurse_id][2] else 0
            model.Add(sum(employee_blocks) == 2 - carried)

    for day in range(1, num_days + 1):
        model.Add(sum(night[str(n["id"]), day] for n in workers) == daily_targets[day - 1]["N"])
        for grade in ("charge", "middle"):
            model.Add(sum(
                night[str(n["id"]), day]
                for n in workers if role_group(n.get("role")) == grade
            ) >= 1)

    general_workers = sorted(
        [nurse for nurse in workers if nurse_name(nurse) != LEE_HYEMI],
        key=lambda nurse: (
            {"junior": 0, "middle": 1, "charge": 2}.get(role_group(nurse.get("role")), 3),
            str(nurse["id"]),
        ),
    )
    hye_mi = next((nurse for nurse in workers if nurse_name(nurse) == LEE_HYEMI), None)
    hye_total = 0
    if hye_mi:
        hye_id = str(hye_mi["id"])
        carried = 1 if boundaries[hye_id][2] else 0
        continuation = sum(1 for value in boundaries[hye_id][0].values() if value == "N")
        hye_total = continuation + (2 - carried) * 3
    general_required = sum(day["N"] for day in daily_targets) - hye_total
    if general_workers:
        floor_target, high_count = divmod(general_required, len(general_workers))
        for index, nurse in enumerate(general_workers):
            nurse_id = str(nurse["id"])
            target = floor_target + (1 if index < high_count else 0)
            model.Add(sum(night[nurse_id, day] for day in range(1, num_days + 1)) == target)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = min(60, max(20, payload.timeLimitSeconds // 2))
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {}, solver.StatusName(status)
    return {
        str(nurse["id"]): [
            int(solver.BooleanValue(night[str(nurse["id"]), day]))
            for day in range(1, num_days + 1)
        ]
        for nurse in workers
    }, solver.StatusName(status)


def infeasible_response(message: str, reasons: list[dict[str, Any]], status: str = "INFEASIBLE") -> dict[str, Any]:
    return {
        "success": False,
        "schedule": [],
        "message": message,
        "infeasible_reasons": reasons,
        "hard_violations": reasons,
        "warnings": [],
        "status": status,
    }


def precheck(
    payload: SolveRequest,
    workers: list[dict[str, Any]],
    num_days: int,
    minimum: dict[str, int],
    maximum: dict[str, int],
    minimum_off: int,
    request_conflicts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hard = [item for item in request_conflicts if not item.get("warning_only")]
    warnings = [item for item in request_conflicts if item.get("warning_only")]
    count = len(workers)
    grades = Counter(role_group(n.get("role")) for n in workers)

    if not count:
        hard.append({"type": "no_workers", "message": "3교대 직원이 없습니다."})
        return hard, warnings
    if minimum_off > num_days:
        hard.append({"type": "invalid_required_off", "message": "required_off가 해당 월의 일수보다 큽니다."})
    if any(minimum[s] > maximum[s] for s in WORK_SHIFTS):
        hard.append({"type": "invalid_staffing_range", "message": "최소 인원이 최대 인원보다 큽니다."})
    if sum(minimum.values()) > count:
        hard.append({
            "type": "daily_staffing_capacity",
            "actual": count,
            "required": sum(minimum.values()),
            "message": "3교대 직원 수가 하루 D/E/N 최소 인원 합계보다 적습니다.",
        })
    available_work_max = count * (num_days - minimum_off)
    required_work_min = num_days * sum(minimum.values())
    allowed_work_max = num_days * sum(maximum.values())
    if available_work_max < required_work_min:
        hard.append({
            "type": "required_off_capacity",
            "actual": available_work_max,
            "required": required_work_min,
            "message": "required_off를 보장하면 D/E/N 최소 인원을 채울 수 없습니다.",
        })
    if available_work_max > allowed_work_max:
        hard.append({
            "type": "required_off_exceeds_daily_maximum_capacity",
            "actual": available_work_max,
            "required": allowed_work_max,
            "message": "required_off를 정확히 적용하면 D/E/N 최대 인원을 초과합니다.",
        })
    for grade in ("charge", "middle"):
        if grades[grade] < 3:
            hard.append({
                "type": f"{grade}_capacity",
                "actual": grades[grade],
                "required": 3,
                "message": f"매일 D/E/N에 {grade} 1명씩 배치하려면 최소 3명이 필요합니다.",
            })
    if not any(nurse_name(n) == LEE_HYEMI for n in workers):
        warnings.append({"type": "lee_hyemi_missing", "message": "이혜미 간호사가 활성 명단에 없어 전용 Night 규칙을 적용하지 않았습니다."})
    return hard, warnings


def solve(payload: SolveRequest) -> dict[str, Any]:
    num_days = days_in_month(payload.year, payload.month)
    workers = worker_nurses(payload.nurses)
    worker_ids = {str(n["id"]) for n in workers}
    minimum, maximum = staffing_limits(payload)
    minimum_off = required_off(payload)
    try:
        daily_targets = balanced_staffing_targets(
            len(workers), num_days, minimum_off, minimum, maximum
        )
    except ValueError as error:
        return infeasible_response(
            "현재 인원·OFF·최소인원·최대인원 조건을 동시에 만족할 수 없습니다.",
            [{"type": "staffing_capacity", "message": str(error)}],
            "PRECHECK_FAILED",
        )
    off_requests, request_conflicts = requested_off(payload, worker_ids, num_days)
    precheck_hard, precheck_warnings = precheck(
        payload, workers, num_days, minimum, maximum, minimum_off, request_conflicts
    )
    if precheck_hard:
        return infeasible_response(
            "현재 인원·OFF·최소인원·Grade 조건을 동시에 만족할 수 없습니다.",
            precheck_hard,
            "PRECHECK_FAILED",
        )
    night_plan, night_status = solve_night_plan(
        payload, workers, num_days, daily_targets, off_requests
    )
    if not night_plan:
        return infeasible_response(
            "Night 인원·연속 블록·Grade 조건을 동시에 만족할 수 없습니다.",
            [{"type": "night_plan_infeasible", "solver_status": night_status}],
            night_status,
        )

    model = cp_model.CpModel()
    x: dict[tuple[str, int, str], cp_model.IntVar] = {}
    night_blocks: dict[tuple[str, int, int], cp_model.IntVar] = {}
    boundaries = {
        str(nurse["id"]): previous_boundary(payload, nurse, num_days)
        for nurse in workers
    }

    for nurse in workers:
        nurse_id = str(nurse["id"])
        for day in range(1, num_days + 1):
            for shift in SHIFTS:
                x[nurse_id, day, shift] = model.NewBoolVar(f"x_{nurse_id}_{day}_{shift}")
            model.AddExactlyOne(x[nurse_id, day, shift] for shift in SHIFTS)
            model.Add(x[nurse_id, day, "N"] == night_plan[nurse_id][day - 1])
            fixed_shift = boundaries[nurse_id][0].get(day)
            if fixed_shift:
                model.Add(x[nurse_id, day, fixed_shift] == 1)
            if (nurse_id, day) in off_requests:
                model.Add(x[nurse_id, day, "OFF"] == 1)
        if boundaries[nurse_id][1]:
            model.Add(x[nurse_id, 1, "D"] == 0)

    for day in range(1, num_days + 1):
        for shift in WORK_SHIFTS:
            assigned = [x[str(n["id"]), day, shift] for n in workers]
            if shift == "N":
                model.Add(sum(assigned) == daily_targets[day - 1][shift])
            else:
                model.Add(sum(assigned) >= minimum[shift])
                model.Add(sum(assigned) <= maximum[shift])
            model.Add(sum(
                x[str(n["id"]), day, shift]
                for n in workers if role_group(n.get("role")) == "charge"
            ) >= 1)
            model.Add(sum(
                x[str(n["id"]), day, shift]
                for n in workers if role_group(n.get("role")) == "middle"
            ) >= 1)

    general_night_totals: list[cp_model.IntVar] = []
    objective_terms: list[cp_model.LinearExpr] = []

    for nurse in workers:
        nurse_id = str(nurse["id"])
        name = nurse_name(nurse)

        model.Add(sum(x[nurse_id, day, "OFF"] for day in range(1, num_days + 1)) == minimum_off)
        for day in range(1, num_days):
            model.Add(x[nurse_id, day, "E"] + x[nurse_id, day + 1, "D"] <= 1)
            model.Add(x[nurse_id, day, "N"] + x[nurse_id, day + 1, "D"] <= 1)
            model.Add(x[nurse_id, day, "N"] + x[nurse_id, day + 1, "E"] <= 1)

        # Prefer practical D/E runs without making them hard constraints.
        for shift in ("D", "E"):
            first_single = model.NewBoolVar(f"single_{shift}_{nurse_id}_1")
            model.Add(first_single <= x[nurse_id, 1, shift])
            model.Add(first_single + x[nurse_id, 2, shift] <= 1)
            model.Add(first_single >= x[nurse_id, 1, shift] - x[nurse_id, 2, shift])
            objective_terms.append(first_single * 30)

            for day in range(2, num_days):
                single = model.NewBoolVar(f"single_{shift}_{nurse_id}_{day}")
                model.Add(single <= x[nurse_id, day, shift])
                model.Add(single + x[nurse_id, day - 1, shift] <= 1)
                model.Add(single + x[nurse_id, day + 1, shift] <= 1)
                model.Add(
                    single
                    >= x[nurse_id, day, shift]
                    - x[nurse_id, day - 1, shift]
                    - x[nurse_id, day + 1, shift]
                )
                objective_terms.append(single * 30)

            last_single = model.NewBoolVar(f"single_{shift}_{nurse_id}_{num_days}")
            model.Add(last_single <= x[nurse_id, num_days, shift])
            model.Add(last_single + x[nurse_id, num_days - 1, shift] <= 1)
            model.Add(
                last_single
                >= x[nurse_id, num_days, shift] - x[nurse_id, num_days - 1, shift]
            )
            objective_terms.append(last_single * 30)

            for start in range(1, num_days - 4):
                six_same = model.NewBoolVar(f"six_{shift}_{nurse_id}_{start}")
                six_total = sum(
                    x[nurse_id, day, shift] for day in range(start, start + 6)
                )
                model.Add(six_total == 6).OnlyEnforceIf(six_same)
                model.Add(six_total <= 5).OnlyEnforceIf(six_same.Not())
                objective_terms.append(six_same * 20)

        # Prefer an OFF before a sixth consecutive D/E/N workday.
        for start in range(1, num_days - 4):
            six_work = model.NewBoolVar(f"six_work_{nurse_id}_{start}")
            off_total = sum(
                x[nurse_id, day, "OFF"] for day in range(start, start + 6)
            )
            model.Add(off_total == 0).OnlyEnforceIf(six_work)
            model.Add(off_total >= 1).OnlyEnforceIf(six_work.Not())
            objective_terms.append(six_work * 40)

        allowed_lengths = (3,) if name == LEE_HYEMI else (2, 3)
        coverage: dict[int, list[cp_model.IntVar]] = defaultdict(list)
        employee_blocks: list[cp_model.IntVar] = []
        fixed_days = set(boundaries[nurse_id][0])
        for length in allowed_lengths:
            for start in range(1, num_days - length + 2):
                if fixed_days.intersection(range(start, start + length)):
                    continue
                block = model.NewBoolVar(f"nb_{nurse_id}_{start}_{length}")
                night_blocks[nurse_id, start, length] = block
                employee_blocks.append(block)
                for day in range(start, start + length):
                    coverage[day].append(block)
                for recovery_day in (start + length, start + length + 1):
                    if recovery_day <= num_days:
                        model.Add(x[nurse_id, recovery_day, "OFF"] == 1).OnlyEnforceIf(block)

        for day in range(1, num_days + 1):
            if boundaries[nurse_id][0].get(day) == "N":
                model.Add(sum(coverage.get(day, [])) == 0)
            else:
                model.Add(x[nurse_id, day, "N"] == sum(coverage.get(day, [])))

        night_total = sum(x[nurse_id, day, "N"] for day in range(1, num_days + 1))
        if name == LEE_HYEMI:
            carried_block = 1 if boundaries[nurse_id][2] else 0
            continuation_nights = sum(
                1 for shift in boundaries[nurse_id][0].values() if shift == "N"
            )
            model.Add(sum(employee_blocks) == 2 - carried_block)
            model.Add(night_total == continuation_nights + (2 - carried_block) * 3)
        else:
            total_var = model.NewIntVar(0, num_days, f"night_total_{nurse_id}")
            model.Add(total_var == night_total)
            general_night_totals.append(total_var)

        d_total = sum(x[nurse_id, day, "D"] for day in range(1, num_days + 1))
        e_total = sum(x[nurse_id, day, "E"] for day in range(1, num_days + 1))
        de_gap = model.NewIntVar(0, num_days, f"de_gap_{nurse_id}")
        model.AddAbsEquality(de_gap, d_total - e_total)
        objective_terms.append(de_gap * 4)
        objective_terms.append(sum(x[nurse_id, day, "OFF"] for day in range(1, num_days + 1)))

    if general_night_totals:
        min_night = model.NewIntVar(0, num_days, "general_min_night")
        max_night = model.NewIntVar(0, num_days, "general_max_night")
        model.AddMinEquality(min_night, general_night_totals)
        model.AddMaxEquality(max_night, general_night_totals)
        model.Add(max_night - min_night <= 1)

    for day in range(1, num_days + 1):
        for shift in WORK_SHIFTS:
            total = sum(x[str(n["id"]), day, shift] for n in workers)
            objective_terms.append((total - minimum[shift]) * 20)

            charge_count = sum(
                x[str(n["id"]), day, shift]
                for n in workers if role_group(n.get("role")) == "charge"
            )
            middle_count = sum(
                x[str(n["id"]), day, shift]
                for n in workers if role_group(n.get("role")) == "middle"
            )
            junior_count = sum(
                x[str(n["id"]), day, shift]
                for n in workers if role_group(n.get("role")) == "junior"
            )
            charge_extra = model.NewIntVar(0, len(workers), f"charge_extra_{day}_{shift}")
            middle_gap = model.NewIntVar(0, len(workers), f"middle_gap_{day}_{shift}")
            junior_gap = model.NewIntVar(0, len(workers), f"junior_gap_{day}_{shift}")
            model.Add(charge_extra >= charge_count - 1)
            model.AddAbsEquality(middle_gap, middle_count - 3)
            model.AddAbsEquality(junior_gap, junior_count - 3)
            objective_terms.extend((charge_extra * 3, middle_gap, junior_gap))

    objective = sum(objective_terms)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(
        15, min(180, int(payload.timeLimitSeconds or DEFAULT_TIME_LIMIT_SECONDS))
    )
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 202607
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return infeasible_response(
            "현재 인원·OFF·최소인원·Grade 조건을 동시에 만족할 수 없습니다.",
            [{
                "type": "constraint_combination_conflict",
                "message": "OFF, 일별 인원, Grade, Night 블록 및 휴식 조건의 조합에서 해를 찾지 못했습니다.",
                "solver_status": solver.StatusName(status),
            }],
            solver.StatusName(status),
        )

    active_solver = solver
    active_status = status
    for variable in x.values():
        model.AddHint(variable, solver.Value(variable))
    model.Minimize(objective)
    optimizer = cp_model.CpSolver()
    optimizer.parameters.max_time_in_seconds = min(
        15, max(5, int(payload.timeLimitSeconds or DEFAULT_TIME_LIMIT_SECONDS) // 4)
    )
    optimizer.parameters.num_search_workers = 8
    optimizer.parameters.random_seed = 202607
    optimized_status = optimizer.Solve(model)
    if optimized_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        active_solver = optimizer
        active_status = optimized_status

    schedule: dict[str, list[str]] = {}
    for nurse in workers:
        nurse_id = str(nurse["id"])
        schedule[nurse_id] = [
            next(shift for shift in SHIFTS if active_solver.BooleanValue(x[nurse_id, day, shift]))
            for day in range(1, num_days + 1)
        ]

    validation = validate_schedule(payload, schedule)
    if validation["hard_violations"]:
        return infeasible_response(
            "생성 결과 검증에서 절대조건 위반이 발견되었습니다.",
            validation["hard_violations"],
            "VALIDATION_FAILED",
        )

    return {
        "success": True,
        "schedule": schedule,
        "message": "근무표가 생성되었습니다.",
        "hard_violations": [],
        "warnings": precheck_warnings + validation["warnings"],
        "validation": validation,
        "staffing_summary": validation["staffing_summary"],
        "grade_summary": validation["grade_summary"],
        "individual_shift_counts": validation["individual_shift_counts"],
        "solver_seconds": round(solver.WallTime() + (optimizer.WallTime() if active_solver is optimizer else 0), 3),
        "status": active_solver.StatusName(active_status),
    }


def validate_schedule(payload: SolveRequest, schedule: dict[str, list[str]]) -> dict[str, Any]:
    num_days = days_in_month(payload.year, payload.month)
    workers = worker_nurses(payload.nurses)
    worker_ids = {str(n["id"]) for n in workers}
    names = {str(n["id"]): nurse_name(n) for n in workers}
    groups = {str(n["id"]): role_group(n.get("role")) for n in workers}
    minimum, maximum = staffing_limits(payload)
    minimum_off = required_off(payload)
    off_requests, request_conflicts = requested_off(payload, worker_ids, num_days)
    hard: list[dict[str, Any]] = []
    warnings = [item for item in request_conflicts if item.get("warning_only")]
    staffing_summary: list[dict[str, Any]] = []
    grade_summary: list[dict[str, Any]] = []
    counts_summary: list[dict[str, Any]] = []

    def violation(kind: str, message: str, **details: Any) -> None:
        hard.append({"type": kind, "message": message, **details})

    for nurse in workers:
        nurse_id = str(nurse["id"])
        row = list(schedule.get(nurse_id) or [])
        boundary_fixed, previous_ends_evening, previous_night_run = previous_boundary(
            payload, nurse, num_days
        )
        if len(row) != num_days:
            violation("invalid_row_length", f"{names[nurse_id]}의 근무 일수가 올바르지 않습니다.", nurseId=nurse_id)
            continue
        if any(value not in SHIFTS for value in row):
            violation("invalid_shift", f"{names[nurse_id]}에게 잘못된 근무 코드가 있습니다.", nurseId=nurse_id)
        if previous_ends_evening and row[0] == "D":
            violation(
                "PREVIOUS_E_TO_D",
                f"{names[nurse_id]}의 이전 달 말일 E 다음에 이번 달 1일 D가 배정되었습니다.",
                nurseId=nurse_id,
                day=1,
            )
        for day, expected_shift in boundary_fixed.items():
            if row[day - 1] != expected_shift:
                violation(
                    "previous_month_boundary",
                    f"{names[nurse_id]} {day}일이 이전 달 마지막 주와 연결되지 않습니다.",
                    nurseId=nurse_id,
                    day=day,
                    actual=row[day - 1],
                    required=expected_shift,
                )

        counts = Counter(row)
        counts_summary.append({"nurseId": nurse_id, "name": names[nurse_id], **{s: counts[s] for s in SHIFTS}})
        if counts["OFF"] != minimum_off:
            violation(
                "off_count_mismatch",
                f"{names[nurse_id]} OFF {counts['OFF']}개 / 기준 {minimum_off}개",
                nurseId=nurse_id,
                name=names[nurse_id],
                actual=counts["OFF"],
                required=minimum_off,
            )
        for day in range(1, num_days):
            if row[day - 1] == "E" and row[day] == "D":
                violation("E_TO_D", f"{names[nurse_id]} {day}일 E → {day + 1}일 D", nurseId=nurse_id, day=day + 1)
            if row[day - 1] == "N" and row[day] in {"D", "E"}:
                violation("N_TO_DE", f"{names[nurse_id]} {day}일 N → {day + 1}일 {row[day]}", nurseId=nurse_id, day=day + 1)

        for shift in ("D", "E"):
            shift_index = 0
            while shift_index < num_days:
                if row[shift_index] != shift:
                    shift_index += 1
                    continue
                shift_start = shift_index
                while shift_index < num_days and row[shift_index] == shift:
                    shift_index += 1
                run_length = shift_index - shift_start
                if run_length < 2 or run_length > 5:
                    warnings.append({
                        "type": f"{shift.lower()}_block_preference",
                        "message": (
                            f"{names[nurse_id]} {shift_start + 1}일 시작 {shift} "
                            f"연속근무가 {run_length}일입니다. 권장 범위는 2~5일입니다."
                        ),
                        "nurseId": nurse_id,
                        "day": shift_start + 1,
                        "actual": run_length,
                        "preferred": "2~5",
                        "warning_only": True,
                    })

        work_index = 0
        while work_index < num_days:
            if row[work_index] == "OFF":
                work_index += 1
                continue
            work_start = work_index
            while work_index < num_days and row[work_index] != "OFF":
                work_index += 1
            work_length = work_index - work_start
            if work_length > 5:
                warnings.append({
                    "type": "consecutive_work_preference",
                    "message": (
                        f"{names[nurse_id]} {work_start + 1}일 시작 연속근무가 "
                        f"{work_length}일입니다. 권장 범위는 최대 5일입니다."
                    ),
                    "nurseId": nurse_id,
                    "day": work_start + 1,
                    "actual": work_length,
                    "preferred": "5 이하",
                    "warning_only": True,
                })

        blocks: list[tuple[int, int]] = []
        index = 0
        while index < num_days:
            if row[index] != "N":
                index += 1
                continue
            start = index
            while index < num_days and row[index] == "N":
                index += 1
            local_length = index - start
            length = local_length + (previous_night_run if start == 0 else 0)
            blocks.append((start + 1, length))
            allowed = {3} if names[nurse_id] == LEE_HYEMI else {2, 3}
            if length not in allowed:
                violation(
                    "night_block_length",
                    f"{names[nurse_id]} {start + 1}일 시작 N 블록이 {length}일입니다.",
                    nurseId=nurse_id,
                    day=start + 1,
                    actual=length,
                    required="3" if names[nurse_id] == LEE_HYEMI else "2~3",
                )
            recovery = row[index:min(index + 2, num_days)]
            if index + 2 <= num_days and recovery != ["OFF", "OFF"]:
                violation(
                    "night_recovery",
                    f"{names[nurse_id]} {start + 1}일 시작 N 블록 후 OFF 2일이 없습니다.",
                    nurseId=nurse_id,
                    day=index + 1,
                    actual="/".join(recovery),
                    required="OFF/OFF",
                )
        if names[nurse_id] == LEE_HYEMI and (len(blocks) != 2 or any(length != 3 for _, length in blocks)):
            violation(
                "lee_hyemi_night_rule",
                "이혜미 간호사의 Night는 3일 연속 블록 2개여야 합니다.",
                nurseId=nurse_id,
                actual=blocks,
                required="3N 블록 2개",
            )

    for nurse_id, day in off_requests:
        row = schedule.get(nurse_id, [])
        if len(row) >= day and row[day - 1] != "OFF":
            violation(
                "confirmed_off_unmet",
                f"{names[nurse_id]} {day}일 확정 희망 OFF가 반영되지 않았습니다.",
                nurseId=nurse_id,
                day=day,
                actual=row[day - 1],
                required="OFF",
            )

    for day in range(1, num_days + 1):
        for shift in WORK_SHIFTS:
            assigned = [
                nurse_id for nurse_id in worker_ids
                if len(schedule.get(nurse_id, [])) >= day and schedule[nurse_id][day - 1] == shift
            ]
            count = len(assigned)
            staffing_summary.append({
                "day": day, "shift": shift, "actual": count,
                "min": minimum[shift], "max": maximum[shift],
            })
            if count < minimum[shift] or count > maximum[shift]:
                violation(
                    "staffing_range",
                    f"{day}일 {shift} 인원 {count}명 / 기준 {minimum[shift]}~{maximum[shift]}명",
                    day=day, shift=shift, actual=count,
                    required=f"{minimum[shift]}~{maximum[shift]}",
                )
            grade_counts = Counter(groups[nurse_id] for nurse_id in assigned)
            grade_summary.append({"day": day, "shift": shift, **{g: grade_counts[g] for g in WORK_GROUPS}})
            for grade in ("charge", "middle"):
                if grade_counts[grade] < 1:
                    violation(
                        f"{grade}_missing",
                        f"{day}일 {shift}에 {grade} 간호사가 없습니다.",
                        day=day, shift=shift, grade=grade,
                        actual=grade_counts[grade], required=1,
                    )

    general_nights = [
        Counter(schedule.get(str(n["id"]), []))["N"]
        for n in workers if nurse_name(n) != LEE_HYEMI
    ]
    if general_nights and max(general_nights) - min(general_nights) > 1:
        violation(
            "night_distribution",
            f"일반 직원 Night 횟수 편차가 {max(general_nights) - min(general_nights)}회입니다.",
            actual=max(general_nights) - min(general_nights),
            required="1 이하",
        )

    return {
        "hard_violations": hard,
        "warnings": warnings,
        "staffing_summary": staffing_summary,
        "grade_summary": grade_summary,
        "individual_shift_counts": counts_summary,
    }


@app.get("/")
def root() -> dict[str, Any]:
    return {"ok": True, "service": "nurse-autoschedule", "engine": "OR-Tools CP-SAT"}


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "success": True}


@app.post("/solve")
def solve_endpoint(payload: SolveRequest) -> dict[str, Any]:
    result = solve(payload)
    logger.info(
        "SOLVE RESULT success=%s schedule_count=%s hard_violations=%s message=%s",
        result.get("success"),
        len(result.get("schedule", [])),
        len(result.get("hard_violations", [])),
        result.get("message"),
    )
    return result
