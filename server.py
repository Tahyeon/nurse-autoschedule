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
                "warning_only": True,
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


def requested_assignments(
    payload: SolveRequest,
    worker_ids: set[str],
    num_days: int,
) -> tuple[dict[tuple[str, int], str], list[dict[str, Any]]]:
    assignments: dict[tuple[str, int], str] = {}
    conflicts: list[dict[str, Any]] = []
    for item in payload.requests:
        nurse_id = str(item.get("nurseId") or item.get("nurse_id") or "")
        day = int(item.get("day") or 0)
        shift = normalize_shift(item.get("shift") or item.get("type"))
        if nurse_id not in worker_ids or not 1 <= day <= num_days or shift not in SHIFTS:
            continue
        key = (nurse_id, day)
        existing = assignments.get(key)
        if existing and existing != shift:
            conflicts.append({
                "type": "duplicate_shift_request",
                "nurseId": nurse_id,
                "day": day,
                "actual": f"{existing}, {shift}",
                "warning_only": True,
                "required": "하루에 하나의 근무 신청",
                "message": f"{day}일에 {existing}와 {shift} 신청이 동시에 존재합니다.",
            })
            continue
        assignments[key] = shift
    return assignments, conflicts


def request_boundary_conflicts(
    payload: SolveRequest,
    workers: list[dict[str, Any]],
    assignments: dict[tuple[str, int], str],
    num_days: int,
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for nurse in workers:
        nurse_id = str(nurse["id"])
        fixed, previous_ends_evening, _previous_nights = previous_boundary(
            payload, nurse, num_days
        )
        for day in range(1, num_days + 1):
            requested = assignments.get((nurse_id, day))
            if not requested:
                continue
            fixed_shift = fixed.get(day)
            if fixed_shift and fixed_shift != requested:
                conflicts.append({
                    "type": "request_previous_boundary_conflict",
                    "nurseId": nurse_id,
                    "name": nurse_name(nurse),
                    "day": day,
                    "actual": requested,
                    "required": fixed_shift,
                    "message": (
                        f"{nurse_name(nurse)} {day}일 {requested} 신청이 이전 달 "
                        f"근무에 따른 필수 {fixed_shift}와 충돌합니다."
                    ),
                })
            if day == 1 and previous_ends_evening and requested == "D":
                conflicts.append({
                    "type": "request_previous_e_to_d_conflict",
                    "nurseId": nurse_id,
                    "name": nurse_name(nurse),
                    "day": day,
                    "actual": "이전 달 E → 이번 달 D 신청",
                    "required": "E 다음날 D 금지",
                    "message": (
                        f"{nurse_name(nurse)}의 1일 D 신청이 이전 달 말일 E와 충돌합니다."
                    ),
                })
            if requested == "N" and day in previous_night_cooldown_days(
                payload, nurse, num_days
            ):
                conflicts.append({
                    "type": "request_night_cooldown_conflict",
                    "nurseId": nurse_id,
                    "name": nurse_name(nurse),
                    "day": day,
                    "actual": "N 신청",
                    "required": "이전 Night 종료 후 4일간 N 금지",
                    "message": (
                        f"{nurse_name(nurse)} {day}일 N 신청이 이전 달 Night 종료 후 "
                        "4일 재배정 금지 조건과 충돌합니다."
                    ),
                })
    return conflicts


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
    exact_work_slots = worker_count * (num_days - exact_off)
    required_work_slots = num_days * sum(minimum.values())
    relaxation_capacity = worker_count if exact_off > 0 else 0
    work_slots = max(exact_work_slots, required_work_slots)
    if work_slots > exact_work_slots + relaxation_capacity:
        raise ValueError("OFF를 직원별 1개까지 줄여도 일별 최소 인원을 채울 수 없습니다.")
    remaining = work_slots - required_work_slots
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


def previous_shifts(
    payload: SolveRequest,
    nurse: dict[str, Any],
) -> list[str]:
    row = [
        normalize_shift(value)
        for value in payload.previousSchedule.get(str(nurse["id"]), [])
    ]
    return [value for value in row if value in SHIFTS][-7:]


def previous_boundary(
    payload: SolveRequest,
    nurse: dict[str, Any],
    num_days: int,
) -> tuple[dict[int, str], bool, int]:
    row = previous_shifts(payload, nurse)
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


def previous_trailing_work_days(payload: SolveRequest, nurse: dict[str, Any]) -> int:
    count = 0
    for value in reversed(previous_shifts(payload, nurse)):
        if value == "OFF":
            break
        count += 1
    return count


def previous_night_cooldown_days(
    payload: SolveRequest,
    nurse: dict[str, Any],
    num_days: int,
) -> list[int]:
    row = previous_shifts(payload, nurse)
    if not row or "N" not in row:
        return []

    trailing_nights = 0
    for value in reversed(row):
        if value != "N":
            break
        trailing_nights += 1

    if trailing_nights:
        target_length = 3 if nurse_name(nurse) == LEE_HYEMI else 2
        continuation = max(0, target_length - trailing_nights)
        start = continuation + 1
        return list(range(start, min(num_days, continuation + 4) + 1))

    last_night = max(index for index, value in enumerate(row) if value == "N")
    days_since_night_end = len(row) - last_night - 1
    remaining = max(0, 4 - days_since_night_end)
    return list(range(1, min(num_days, remaining) + 1))


def solve_night_plan(
    payload: SolveRequest,
    workers: list[dict[str, Any]],
    num_days: int,
    daily_targets: list[dict[str, int]],
    shift_requests: dict[tuple[str, int], str],
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
            requested = shift_requests.get((nurse_id, day))
            if boundaries[nurse_id][0].get(day) == "OFF":
                model.Add(night[nurse_id, day] == 0)
        for day in previous_night_cooldown_days(payload, nurse, num_days):
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
                for recovery_day in range(start + length, start + length + 4):
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


def scheduling_capacity_reasons(
    payload: SolveRequest,
    workers: list[dict[str, Any]],
    num_days: int,
    minimum: dict[str, int],
    minimum_off: int,
    off_requests: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    grades = Counter(role_group(n.get("role")) for n in workers)
    requested_by_grade = Counter()
    worker_by_id = {str(n["id"]): n for n in workers}
    for nurse_id, _day in off_requests:
        nurse = worker_by_id.get(nurse_id)
        if nurse:
            requested_by_grade[role_group(nurse.get("role"))] += 1

    reasons: list[dict[str, Any]] = [{
        "type": "night_staff_capacity",
        "message": (
            f"Night는 매일 {minimum['N']}명, 총 {num_days * minimum['N']}명분이 필요합니다. "
            f"현재 Night 가능 3교대 인원은 {len(workers)}명입니다."
        ),
        "required_per_day": minimum["N"],
        "required_total": num_days * minimum["N"],
        "available_workers": len(workers),
    }]
    for grade in ("charge", "middle"):
        reasons.append({
            "type": f"night_{grade}_capacity",
            "message": (
                f"Night마다 {grade} 최소 1명이 필요합니다. 현재 {grade} 인원은 "
                f"{grades[grade]}명이고 확정 OFF 신청은 {requested_by_grade[grade]}건입니다."
            ),
            "grade": grade,
            "available_workers": grades[grade],
            "confirmed_off_requests": requested_by_grade[grade],
            "required_assignments": num_days,
        })
    reasons.extend((
        {
            "type": "night_cooldown_capacity",
            "message": "각 Night 블록 종료 후 4일 동안 Night 재배정 금지 조건과 날짜별 Night 필요 인원이 충돌할 수 있습니다.",
            "required": "Night 종료 후 4일간 N 금지",
        },
        {
            "type": "consecutive_work_capacity",
            "message": "연속근무 최대 5일, OFF 목표, 확정 희망 OFF 및 일별 최소 인원을 동시에 충족해야 합니다.",
            "required": "6일 연속근무 금지",
            "off_target": minimum_off,
        },
    ))
    return reasons


def max_night_days_with_spacing(num_days: int) -> int:
    """Optimistic monthly N capacity for one nurse with 3N + 4 non-N cycles."""
    day = 1
    total = 0
    while day <= num_days:
        block_len = min(3, num_days - day + 1)
        total += block_len
        day += block_len + 4
    return total


def enhanced_scheduling_capacity_reasons(
    payload: SolveRequest,
    workers: list[dict[str, Any]],
    num_days: int,
    minimum: dict[str, int],
    minimum_off: int,
    off_requests: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    grades = Counter(role_group(n.get("role")) for n in workers)
    worker_by_id = {str(n["id"]): n for n in workers}
    off_by_day: dict[int, set[str]] = defaultdict(set)
    off_by_day_grade: dict[int, Counter[str]] = defaultdict(Counter)
    requested_by_grade = Counter()
    cooldown_by_day: dict[int, set[str]] = defaultdict(set)
    fixed_by_day: dict[int, dict[str, str]] = defaultdict(dict)

    for nurse_id, day in off_requests:
        nurse = worker_by_id.get(nurse_id)
        if not nurse:
            continue
        off_by_day[day].add(nurse_id)
        grade = role_group(nurse.get("role"))
        off_by_day_grade[day][grade] += 1
        requested_by_grade[grade] += 1

    for nurse in workers:
        nurse_id = str(nurse["id"])
        fixed, _previous_evening, _previous_nights = previous_boundary(
            payload, nurse, num_days
        )
        for day, shift in fixed.items():
            fixed_by_day[day][nurse_id] = shift
        for day in previous_night_cooldown_days(payload, nurse, num_days):
            cooldown_by_day[day].add(nurse_id)

    def ceil_div(left: int, right: int) -> int:
        return 0 if right <= 0 else -(-left // right)

    worker_count = len(workers)
    total_minimum_staff = sum(minimum.values())
    total_night_required = minimum["N"] * num_days
    target_low = total_night_required // worker_count if worker_count else 0
    target_high = ceil_div(total_night_required, worker_count) if worker_count else 0
    theoretical_night_capacity = worker_count * target_high
    spacing_capacity_per_worker = max_night_days_with_spacing(num_days)
    spacing_capacity_total = worker_count * spacing_capacity_per_worker
    minimum_workers_by_target = ceil_div(total_night_required, max(1, target_high))
    minimum_workers_by_spacing = ceil_div(total_night_required, max(1, spacing_capacity_per_worker))
    exact_work_slots = worker_count * max(0, num_days - minimum_off)
    relaxed_work_slots = exact_work_slots + (worker_count if minimum_off > 0 else 0)
    required_work_slots = num_days * total_minimum_staff

    reasons: list[dict[str, Any]] = [
        {
            "type": "night_capacity_summary",
            "severity": "critical",
            "message": (
                "현재 조건으로는 Night 배치가 가장 큰 병목일 가능성이 높습니다. "
                f"Night 최소 {minimum['N']}명 × {num_days}일 = 총 {total_night_required}명분이 필요하고, "
                f"Night 가능 3교대 인원은 {worker_count}명입니다. "
                "Night 2~3연속, Night 후 OFF 2일, Night 종료 후 4일 재배정 금지를 함께 적용하면 "
                "단순 총량보다 실제 배치 가능성이 크게 줄어듭니다."
            ),
            "night_min_per_day": minimum["N"],
            "days": num_days,
            "night_required_total": total_night_required,
            "night_available_workers": worker_count,
            "even_distribution_target_range": f"{target_low}~{target_high}",
            "theoretical_night_capacity_at_high_target": theoretical_night_capacity,
            "optimistic_capacity_with_3n_4non_n_cycles": spacing_capacity_total,
            "optimistic_capacity_per_worker_with_spacing": spacing_capacity_per_worker,
            "estimated_minimum_workers_by_monthly_target": minimum_workers_by_target,
            "estimated_minimum_workers_by_spacing_only": minimum_workers_by_spacing,
            "suggested_actions": [
                "N 최소 인원을 낮출 수 있는지 확인",
                "Night 가능 인원을 늘릴 수 있는지 확인",
                "Night 종료 후 4일 재배정 금지를 권장조건으로 완화할 수 있는지 확인",
                "이전달 마지막 주 Night/OFF 경계 조건이 과도하게 막고 있는지 확인",
            ],
        },
        {
            "type": "work_off_capacity_summary",
            "severity": "critical" if relaxed_work_slots < required_work_slots else "info",
            "message": (
                f"전체 최소 근무 필요량은 D/E/N 최소 인원 합계 {total_minimum_staff}명 × {num_days}일 = "
                f"{required_work_slots}명분입니다. OFF 목표 {minimum_off}개를 적용하면 정확 기준 근무 가능량은 "
                f"{exact_work_slots}명분이고, OFF를 1개 부족하게 허용해도 최대 {relaxed_work_slots}명분입니다."
            ),
            "required_work_slots_from_daily_minimum": required_work_slots,
            "available_work_slots_with_exact_off": exact_work_slots,
            "available_work_slots_with_one_less_off": relaxed_work_slots,
            "off_target": minimum_off,
            "suggested_actions": [
                "D/E/N 최소 인원 합계를 낮출 수 있는지 확인",
                "OFF 목표를 현실적으로 조정할 수 있는지 확인",
                "3교대 가능 인원을 늘릴 수 있는지 확인",
            ],
        },
    ]

    for grade in ("charge", "middle"):
        grade_count = grades[grade]
        grade_capacity_at_high_target = grade_count * target_high
        reasons.append({
            "type": f"night_{grade}_capacity",
            "severity": "critical" if grade_capacity_at_high_target < num_days else "warning",
            "message": (
                f"Night마다 {grade} 최소 1명이 필요하므로 한 달 {num_days}일 동안 "
                f"{grade} Night가 최소 {num_days}명분 필요합니다. 현재 {grade} 인원은 {grade_count}명이고, "
                f"Night 균등 목표 상한 {target_high}개 기준 이론상 {grade_capacity_at_high_target}명분을 감당할 수 있습니다. "
                "다만 2~3연속 Night 블록과 Night 후 4일 재배정 금지 때문에 특정 날짜에 배치가 끊길 수 있습니다."
            ),
            "grade": grade,
            "available_workers": grade_count,
            "required_night_assignments": num_days,
            "estimated_monthly_target_high": target_high,
            "theoretical_grade_night_capacity": grade_capacity_at_high_target,
            "minimum_grade_workers_by_target": ceil_div(num_days, max(1, target_high)),
            "confirmed_off_requests": requested_by_grade[grade],
            "suggested_actions": [
                f"{grade} Night 가능 인원을 늘릴 수 있는지 확인",
                f"{grade}의 확정 OFF가 Night 필요 날짜에 몰려 있는지 확인",
                "Night charge/middle 최소 1명 조건을 완화할 수 있는지 검토",
            ],
        })

    daily_shortages: list[dict[str, Any]] = []
    for day in range(1, num_days + 1):
        off_ids = off_by_day.get(day, set())
        available_total = worker_count - len(off_ids)
        if available_total < total_minimum_staff:
            daily_shortages.append({
                "day": day,
                "type": "daily_total_staff_after_confirmed_off",
                "available": available_total,
                "required": total_minimum_staff,
                "confirmed_off_count": len(off_ids),
            })
        for grade in ("charge", "middle"):
            available_grade = grades[grade] - off_by_day_grade.get(day, Counter())[grade]
            if available_grade < 3:
                daily_shortages.append({
                    "day": day,
                    "type": f"daily_{grade}_staff_after_confirmed_off",
                    "grade": grade,
                    "available": available_grade,
                    "required": 3,
                    "confirmed_off_count": off_by_day_grade.get(day, Counter())[grade],
                    "message": (
                        f"{day}일 확정 OFF를 반영하면 {grade} 가능 인원이 {available_grade}명입니다. "
                        "D/E/N 각각 최소 1명씩 배치하려면 같은 날 최소 3명이 필요합니다."
                    ),
                })

    night_day_shortages: list[dict[str, Any]] = []
    for day in range(1, num_days + 1):
        eligible_ids = []
        eligible_by_grade = Counter()
        fixed_night_count = 0
        for nurse in workers:
            nurse_id = str(nurse["id"])
            fixed_shift = fixed_by_day.get(day, {}).get(nurse_id)
            if fixed_shift == "N":
                fixed_night_count += 1
            if nurse_id in off_by_day.get(day, set()):
                continue
            if nurse_id in cooldown_by_day.get(day, set()):
                continue
            if fixed_shift and fixed_shift != "N":
                continue
            eligible_ids.append(nurse_id)
            eligible_by_grade[role_group(nurse.get("role"))] += 1
        if len(eligible_ids) < minimum["N"]:
            night_day_shortages.append({
                "day": day,
                "type": "night_eligible_staff_shortage",
                "eligible": len(eligible_ids),
                "required": minimum["N"],
                "fixed_night_from_previous_month": fixed_night_count,
                "confirmed_off_count": len(off_by_day.get(day, set())),
                "cooldown_blocked_count": len(cooldown_by_day.get(day, set())),
            })
        for grade in ("charge", "middle"):
            if eligible_by_grade[grade] < 1:
                night_day_shortages.append({
                    "day": day,
                    "type": f"night_{grade}_eligible_shortage",
                    "grade": grade,
                    "eligible": eligible_by_grade[grade],
                    "required": 1,
                    "confirmed_off_count": off_by_day_grade.get(day, Counter())[grade],
                    "cooldown_blocked_count": sum(
                        1
                        for nurse_id in cooldown_by_day.get(day, set())
                        if role_group(worker_by_id.get(nurse_id, {}).get("role")) == grade
                    ),
                })

    if daily_shortages:
        reasons.append({
            "type": "confirmed_off_daily_staffing_shortages",
            "severity": "critical",
            "message": "확정 희망 OFF를 반영하면 특정 날짜의 전체 인원 또는 직급 인원이 부족해질 수 있습니다.",
            "shortages": daily_shortages[:20],
            "omitted_count": max(0, len(daily_shortages) - 20),
            "suggested_actions": [
                "해당 날짜의 확정 OFF 일부를 조정",
                "해당 날짜 D/E/N 최소 인원을 낮출 수 있는지 확인",
                "부족한 직급 인원을 보강",
            ],
        })

    if night_day_shortages:
        reasons.append({
            "type": "night_daily_eligibility_shortages",
            "severity": "critical",
            "message": (
                "확정 OFF, 이전달 Night 경계, Night 후 4일 재배정 금지를 반영하면 "
                "특정 날짜에 Night 가능 인원 또는 Night 직급 인원이 부족해질 수 있습니다."
            ),
            "shortages": night_day_shortages[:20],
            "omitted_count": max(0, len(night_day_shortages) - 20),
            "suggested_actions": [
                "해당 날짜 전후의 Night 확정/이전달 근무표를 확인",
                "Night 후 4일 재배정 금지를 권장조건으로 낮출 수 있는지 검토",
                "N 최소 인원을 낮추거나 Night 가능 인원을 보강",
            ],
        })

    reasons.append({
        "type": "recommended_relaxation_order",
        "severity": "info",
        "message": (
            "해를 찾지 못했다면 먼저 N 최소 인원, Night 가능 인원, Night 후 4일 재배정 금지, "
            "Night charge/middle 최소 조건, OFF 목표 순서로 완화 가능성을 검토하세요."
        ),
        "recommended_order": [
            "N 최소 인원 낮추기",
            "Night 가능 인원 늘리기",
            "Night 후 4일 재배정 금지를 권장조건으로 완화",
            "Night charge/middle 최소 조건 완화 또는 해당 직급 보강",
            "OFF 목표 또는 확정 OFF 조정",
        ],
    })
    return reasons


def schedule_quality_metrics(
    payload: SolveRequest,
    schedule: dict[str, list[str]],
    workers: list[dict[str, Any]],
    minimum_off: int,
) -> dict[str, Any]:
    de_gaps: list[int] = []
    work_off_work = 0
    alternating_work_off = 0
    shortfall_employees: list[dict[str, Any]] = []
    shortfall_by_role = {role: 0 for role in WORK_GROUPS}

    for nurse in workers:
        nurse_id = str(nurse["id"])
        row = list(schedule.get(nurse_id) or [])
        counts = Counter(row)
        de_gaps.append(abs(counts["D"] - counts["E"]))
        if minimum_off > 0 and counts["OFF"] == minimum_off - 1:
            role = role_group(nurse.get("role"))
            shortfall_employees.append({
                "nurse_id": nurse_id,
                "name": nurse_name(nurse),
                "role": role,
                "off_count": counts["OFF"],
                "target": minimum_off,
            })
            if role in shortfall_by_role:
                shortfall_by_role[role] += 1

        previous = previous_shifts(payload, nurse)
        combined = previous + row
        current_start = len(previous)
        for index in range(0, len(combined) - 2):
            if index + 2 < current_start:
                continue
            window = combined[index:index + 3]
            if window[0] != "OFF" and window[1] == "OFF" and window[2] != "OFF":
                work_off_work += 1
        for index in range(0, len(combined) - 4):
            if index + 4 < current_start:
                continue
            window = combined[index:index + 5]
            if (
                window[0] != "OFF"
                and window[1] == "OFF"
                and window[2] != "OFF"
                and window[3] == "OFF"
                and window[4] != "OFF"
            ):
                alternating_work_off += 1

    return {
        "hard_violation_count": 0,
        "average_de_difference": round(
            sum(de_gaps) / len(de_gaps) if de_gaps else 0,
            3,
        ),
        "de_difference_over_4_count": sum(1 for gap in de_gaps if gap > 4),
        "work_off_work_count": work_off_work,
        "work_off_work_off_work_count": alternating_work_off,
        "off_shortfall_employees": shortfall_employees,
        "off_shortfall_by_role": shortfall_by_role,
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
    exact_work_slots = count * (num_days - minimum_off)
    relaxed_work_slots = exact_work_slots + (count if minimum_off > 0 else 0)
    required_work_min = num_days * sum(minimum.values())
    allowed_work_max = num_days * sum(maximum.values())
    if relaxed_work_slots < required_work_min:
        hard.append({
            "type": "required_off_capacity",
            "actual": relaxed_work_slots,
            "required": required_work_min,
            "message": "OFF를 직원별 1개까지 줄여도 D/E/N 최소 인원을 채울 수 없습니다.",
        })
    elif exact_work_slots < required_work_min:
        warnings.append({
            "type": "off_relaxation_required",
            "actual": exact_work_slots,
            "required": required_work_min,
            "message": "일별 최소 인원을 충족하기 위해 일부 직원의 OFF가 설정값보다 1개 적을 수 있습니다.",
            "warning_only": True,
        })
    if exact_work_slots > allowed_work_max:
        hard.append({
            "type": "required_off_exceeds_daily_maximum_capacity",
            "actual": exact_work_slots,
            "required": allowed_work_max,
            "message": "required_off를 정확히 적용하면 D/E/N 최대 인원을 초과합니다.",
        })
    for nurse in workers:
        trailing_work = previous_trailing_work_days(payload, nurse)
        if trailing_work > 5:
            hard.append({
                "type": "previous_consecutive_work_exceeds_limit",
                "nurseId": str(nurse["id"]),
                "name": nurse_name(nurse),
                "actual": trailing_work,
                "required": "5 이하",
                "message": (
                    f"{nurse_name(nurse)}의 이전 달 말일 기준 연속근무가 "
                    f"{trailing_work}일이어서 월 경계 최대 5일 조건을 만족할 수 없습니다."
                ),
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
        early_off_requests, _early_off_conflicts = requested_off(
            payload, worker_ids, num_days
        )
        return infeasible_response(
            "현재 인원·OFF·최소인원·최대인원 조건을 동시에 만족할 수 없습니다.",
            [{"type": "staffing_capacity", "message": str(error)}]
            + enhanced_scheduling_capacity_reasons(
                payload, workers, num_days, minimum, minimum_off, early_off_requests
            ),
            "PRECHECK_FAILED",
        )
    off_requests, off_request_conflicts = requested_off(payload, worker_ids, num_days)
    shift_requests, shift_request_conflicts = requested_assignments(
        payload, worker_ids, num_days
    )
    request_conflicts = off_request_conflicts + shift_request_conflicts
    request_conflicts.extend(
        {**item, "warning_only": True}
        for item in request_boundary_conflicts(payload, workers, shift_requests, num_days)
    )
    precheck_hard, precheck_warnings = precheck(
        payload, workers, num_days, minimum, maximum, minimum_off, request_conflicts
    )
    if precheck_hard:
        return infeasible_response(
            "현재 인원·OFF·최소인원·Grade 조건을 동시에 만족할 수 없습니다.",
            precheck_hard
            + enhanced_scheduling_capacity_reasons(
                payload, workers, num_days, minimum, minimum_off, off_requests
            ),
            "PRECHECK_FAILED",
        )
    night_plan, night_status = solve_night_plan(
        payload, workers, num_days, daily_targets, shift_requests
    )
    if not night_plan:
        return infeasible_response(
            "Night 가능 인원·연속 블록·종료 후 4일 재배정 금지·Grade 조건을 동시에 만족할 수 없습니다.",
            [{
                "type": "night_plan_infeasible",
                "message": "Night 선행 배치 단계에서 조건을 만족하는 해를 찾지 못했습니다.",
                "solver_status": night_status,
            }] + enhanced_scheduling_capacity_reasons(
                payload, workers, num_days, minimum, minimum_off, off_requests
            ),
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
    request_unmet_terms: list[cp_model.LinearExpr] = []
    de_extreme_terms: list[cp_model.LinearExpr] = []
    de_shortfall_terms: list[cp_model.LinearExpr] = []
    de_excess_terms: list[cp_model.LinearExpr] = []
    repetition_terms: list[cp_model.LinearExpr] = []
    single_shift_terms: list[cp_model.LinearExpr] = []
    other_quality_terms: list[cp_model.LinearExpr] = []
    de_balance_vars: dict[str, tuple[cp_model.LinearExpr, cp_model.LinearExpr, cp_model.IntVar]] = {}
    off_shortfall_vars: dict[str, cp_model.IntVar] = {}

    def soft_pattern(
        name: str,
        terms: list[cp_model.LinearExpr | int],
        weight: int,
        bucket: list[cp_model.LinearExpr],
    ) -> cp_model.IntVar:
        matched = model.NewBoolVar(name)
        total = sum(terms)
        model.Add(total == len(terms)).OnlyEnforceIf(matched)
        model.Add(total <= len(terms) - 1).OnlyEnforceIf(matched.Not())
        bucket.append(matched * weight)
        return matched

    for nurse in workers:
        nurse_id = str(nurse["id"])
        name = nurse_name(nurse)
        previous_row = previous_shifts(payload, nurse)
        for day in range(1, num_days + 1):
            requested_shift = shift_requests.get((nurse_id, day))
            if requested_shift:
                request_unmet_terms.append(1 - x[nurse_id, day, requested_shift])

        def shift_expr(day: int, shift: str) -> cp_model.LinearExpr | int | None:
            if day >= 1:
                if day > num_days:
                    return None
                return x[nurse_id, day, shift]
            previous_index = len(previous_row) + day - 1
            if previous_index < 0 or previous_index >= len(previous_row):
                return None
            return int(previous_row[previous_index] == shift)

        def work_expr(day: int) -> cp_model.LinearExpr | int | None:
            off = shift_expr(day, "OFF")
            return None if off is None else 1 - off

        off_shortfall = model.NewIntVar(
            0, 1 if minimum_off > 0 else 0, f"off_shortfall_{nurse_id}"
        )
        off_shortfall_vars[nurse_id] = off_shortfall
        model.Add(
            sum(x[nurse_id, day, "OFF"] for day in range(1, num_days + 1))
            + off_shortfall
            == minimum_off
        )
        for day in range(1, num_days):
            model.Add(x[nurse_id, day, "E"] + x[nurse_id, day + 1, "D"] <= 1)
            model.Add(x[nurse_id, day, "N"] + x[nurse_id, day + 1, "D"] <= 1)
            model.Add(x[nurse_id, day, "N"] + x[nurse_id, day + 1, "E"] <= 1)

        # No employee may work six consecutive days.
        for start in range(1, num_days - 4):
            model.Add(sum(
                x[nurse_id, day, "OFF"]
                for day in range(start, start + 6)
            ) >= 1)
        trailing_work = previous_trailing_work_days(payload, nurse)
        if 1 <= trailing_work <= 5:
            boundary_days = min(num_days, 6 - trailing_work)
            model.Add(sum(
                x[nurse_id, day, "OFF"]
                for day in range(1, boundary_days + 1)
            ) >= 1)

        for day in previous_night_cooldown_days(payload, nurse, num_days):
            model.Add(x[nurse_id, day, "N"] == 0)

        # Prefer practical D/E runs without making them hard constraints.
        for shift in ("D", "E"):
            first_single = model.NewBoolVar(f"single_{shift}_{nurse_id}_1")
            previous_same_shift = bool(previous_row and previous_row[-1] == shift)
            if previous_same_shift:
                model.Add(first_single == 0)
            else:
                model.Add(first_single <= x[nurse_id, 1, shift])
                model.Add(first_single + x[nurse_id, 2, shift] <= 1)
                model.Add(first_single >= x[nurse_id, 1, shift] - x[nurse_id, 2, shift])
            single_shift_terms.append(first_single * 100)

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
                single_shift_terms.append(single * 100)

            last_single = model.NewBoolVar(f"single_{shift}_{nurse_id}_{num_days}")
            model.Add(last_single <= x[nurse_id, num_days, shift])
            model.Add(last_single + x[nurse_id, num_days - 1, shift] <= 1)
            model.Add(
                last_single
                >= x[nurse_id, num_days, shift] - x[nurse_id, num_days - 1, shift]
            )
            single_shift_terms.append(last_single * 100)

            # Two-to-four day D/E runs are preferred. Five-day runs remain
            # valid, but receive a small penalty after singleton reduction.
            for start in range(1, num_days - 3):
                five_same = model.NewBoolVar(f"five_{shift}_{nurse_id}_{start}")
                five_total = sum(
                    x[nurse_id, day, shift] for day in range(start, start + 5)
                )
                model.Add(five_total == 5).OnlyEnforceIf(five_same)
                model.Add(five_total <= 4).OnlyEnforceIf(five_same.Not())
                single_shift_terms.append(five_same * 10)

            for start in range(1, num_days - 4):
                six_same = model.NewBoolVar(f"six_{shift}_{nurse_id}_{start}")
                six_total = sum(
                    x[nurse_id, day, shift] for day in range(start, start + 6)
                )
                model.Add(six_total == 6).OnlyEnforceIf(six_same)
                model.Add(six_total <= 5).OnlyEnforceIf(six_same.Not())
                objective_terms.append(six_same * 20)

            previous_tail = previous_row[-5:]
            for previous_count in range(1, len(previous_tail) + 1):
                previous_segment = previous_tail[-previous_count:]
                current_count = 6 - previous_count
                if current_count > num_days or any(value != shift for value in previous_segment):
                    continue
                boundary_six_same = model.NewBoolVar(
                    f"boundary_six_{shift}_{nurse_id}_{previous_count}"
                )
                current_total = sum(
                    x[nurse_id, day, shift]
                    for day in range(1, current_count + 1)
                )
                model.Add(current_total == current_count).OnlyEnforceIf(boundary_six_same)
                model.Add(current_total <= current_count - 1).OnlyEnforceIf(boundary_six_same.Not())
                objective_terms.append(boundary_six_same * 20)

        # Prefer an OFF before a sixth consecutive D/E/N workday.
        for start in range(1, num_days - 4):
            six_work = model.NewBoolVar(f"six_work_{nurse_id}_{start}")
            off_total = sum(
                x[nurse_id, day, "OFF"] for day in range(start, start + 6)
            )
            model.Add(off_total == 0).OnlyEnforceIf(six_work)
            model.Add(off_total >= 1).OnlyEnforceIf(six_work.Not())
            objective_terms.append(six_work * 40)

        previous_tail = previous_shifts(payload, nurse)[-5:]
        for previous_count in range(1, len(previous_tail) + 1):
            previous_segment = previous_tail[-previous_count:]
            current_count = 6 - previous_count
            if current_count > num_days or any(value == "OFF" for value in previous_segment):
                continue
            boundary_six_work = model.NewBoolVar(
                f"boundary_six_work_{nurse_id}_{previous_count}"
            )
            current_work_total = sum(
                1 - x[nurse_id, day, "OFF"]
                for day in range(1, current_count + 1)
            )
            model.Add(current_work_total == current_count).OnlyEnforceIf(boundary_six_work)
            model.Add(current_work_total <= current_count - 1).OnlyEnforceIf(boundary_six_work.Not())
            objective_terms.append(boundary_six_work * 40)

        # Lowest-priority quality preferences. Every indicator only contributes
        # to the final objective and never restricts schedule feasibility.
        first_combined_day = 1 - len(previous_row)
        for start in range(first_combined_day, num_days - 4):
            window = [work_expr(day) for day in range(start, start + 6)]
            if start + 5 < 1 or any(term is None for term in window):
                continue
            soft_pattern(
                f"quality_six_work_{nurse_id}_{start}",
                window,
                60,
                other_quality_terms,
            )

        for day in range(1, num_days):
            before = work_expr(day - 1)
            current_off = shift_expr(day, "OFF")
            after = work_expr(day + 1)
            is_requested_off = (nurse_id, day) in off_requests
            if (
                not is_requested_off
                and before is not None
                and current_off is not None
                and after is not None
            ):
                soft_pattern(
                    f"quality_isolated_off_{nurse_id}_{day}",
                    [before, current_off, after],
                    100,
                    repetition_terms,
                )

        for start in range(first_combined_day, num_days - 3):
            off_days = (start + 1, start + 3)
            if any(
                day >= 1 and (nurse_id, day) in off_requests
                for day in off_days
            ):
                continue
            alternating = [
                work_expr(start),
                shift_expr(start + 1, "OFF"),
                work_expr(start + 2),
                shift_expr(start + 3, "OFF"),
                work_expr(start + 4),
            ]
            if start + 4 < 1 or any(term is None for term in alternating):
                continue
            soft_pattern(
                f"quality_alternating_work_off_{nurse_id}_{start}",
                alternating,
                300,
                repetition_terms,
            )

        transition_start = 0 if previous_row else 1
        for day in range(transition_start, num_days):
            day_shift = shift_expr(day, "D")
            next_night = shift_expr(day + 1, "N")
            if day_shift is not None and next_night is not None:
                transition_weight = 18 if role_group(nurse.get("role")) == "junior" else 10
                soft_pattern(
                    f"quality_d_to_n_{nurse_id}_{day}",
                    [day_shift, next_night],
                    transition_weight,
                    other_quality_terms,
                )

        triple_start = -1 if len(previous_row) >= 2 else (0 if previous_row else 1)
        for day in range(triple_start, num_days - 1):
            evening = shift_expr(day, "E")
            middle_off = shift_expr(day + 1, "OFF")
            following_day = shift_expr(day + 2, "D")
            if evening is None or middle_off is None or following_day is None:
                continue
            soft_pattern(
                f"quality_e_off_d_{nurse_id}_{day}",
                [evening, middle_off, following_day],
                12,
                other_quality_terms,
            )

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
                for cooldown_day in range(start + length, start + length + 4):
                    if cooldown_day <= num_days:
                        model.Add(x[nurse_id, cooldown_day, "N"] == 0).OnlyEnforceIf(block)

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
        d_shortfall = model.NewIntVar(0, 4, f"d_shortfall_{nurse_id}")
        e_shortfall = model.NewIntVar(0, 4, f"e_shortfall_{nurse_id}")
        de_excess_4 = model.NewIntVar(0, num_days, f"de_excess_4_{nurse_id}")
        d_very_low = model.NewBoolVar(f"d_very_low_{nurse_id}")
        e_very_low = model.NewBoolVar(f"e_very_low_{nurse_id}")
        model.AddAbsEquality(de_gap, d_total - e_total)
        model.AddMaxEquality(d_shortfall, [4 - d_total, 0])
        model.AddMaxEquality(e_shortfall, [4 - e_total, 0])
        model.AddMaxEquality(de_excess_4, [de_gap - 4, 0])
        model.Add(d_total <= 2).OnlyEnforceIf(d_very_low)
        model.Add(d_total >= 3).OnlyEnforceIf(d_very_low.Not())
        model.Add(e_total <= 2).OnlyEnforceIf(e_very_low)
        model.Add(e_total >= 3).OnlyEnforceIf(e_very_low.Not())
        de_extreme_terms.extend((d_very_low, e_very_low))
        de_shortfall_terms.extend((d_shortfall, e_shortfall))
        de_excess_terms.append(de_excess_4)
        de_balance_vars[nurse_id] = (d_total, e_total, de_gap)

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

            charge_over_two = model.NewIntVar(
                0, len(workers), f"quality_charge_over_two_{day}_{shift}"
            )
            middle_over_three = model.NewIntVar(
                0, len(workers), f"quality_middle_over_three_{day}_{shift}"
            )
            junior_over_four = model.NewIntVar(
                0, len(workers), f"quality_junior_over_four_{day}_{shift}"
            )
            model.Add(charge_over_two >= charge_count - 2)
            model.Add(middle_over_three >= middle_count - 3)
            model.Add(junior_over_four >= junior_count - 4)
            other_quality_terms.extend((
                charge_over_two * 4,
                middle_over_three * 4,
                junior_over_four * 8,
            ))

    objective = sum(objective_terms)
    request_objective = sum(request_unmet_terms)
    de_balance_objective = (
        sum(de_extreme_terms) * 10_000_000_000
        + sum(de_shortfall_terms) * 10_000_000
        + sum(de_excess_terms) * 10_000
    )
    repetition_objective = sum(repetition_terms)
    single_shift_objective = sum(single_shift_terms)
    total_off_shortfall = sum(off_shortfall_vars.values())
    off_dispersion_terms: list[cp_model.IntVar] = []
    role_workers = {
        role: [n for n in workers if role_group(n.get("role")) == role]
        for role in WORK_GROUPS
    }
    for left_index, left_role in enumerate(WORK_GROUPS):
        for right_role in WORK_GROUPS[left_index + 1:]:
            left_group = role_workers[left_role]
            right_group = role_workers[right_role]
            if not left_group or not right_group:
                continue
            left_total = sum(off_shortfall_vars[str(n["id"])] for n in left_group)
            right_total = sum(off_shortfall_vars[str(n["id"])] for n in right_group)
            difference = model.NewIntVar(
                0,
                len(left_group) * len(right_group),
                f"off_shortfall_distribution_{left_role}_{right_role}",
            )
            model.AddAbsEquality(
                difference,
                left_total * len(right_group) - right_total * len(left_group),
            )
            off_dispersion_terms.append(difference)
    off_objective = total_off_shortfall * 10_000 + sum(off_dispersion_terms)
    other_quality_objective = objective * 1_000 + sum(other_quality_terms)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(
        15, min(180, int(payload.timeLimitSeconds or DEFAULT_TIME_LIMIT_SECONDS))
    )
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 202607
    model.Minimize(0)
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return infeasible_response(
            "현재 인원·OFF·최소인원·Grade 조건을 동시에 만족할 수 없습니다.",
            [{
                "type": "constraint_combination_conflict",
                "message": "OFF, 일별 인원, Grade, Night 블록 및 휴식 조건의 조합에서 해를 찾지 못했습니다.",
                "solver_status": solver.StatusName(status),
            }] + enhanced_scheduling_capacity_reasons(
                payload, workers, num_days, minimum, minimum_off, off_requests
            ),
            solver.StatusName(status),
        )

    active_solver = solver
    active_status = status
    request_solver: cp_model.CpSolver | None = None
    request_status: cp_model.CpSolverStatus | None = None
    request_succeeded = not request_unmet_terms
    request_baseline_value = int(round(active_solver.Value(request_objective)))
    if request_unmet_terms:
        model.ClearHints()
        for variable in x.values():
            model.AddHint(variable, active_solver.Value(variable))
        model.Minimize(request_objective)
        request_solver = cp_model.CpSolver()
        request_solver.parameters.max_time_in_seconds = min(
            15, max(5, int(payload.timeLimitSeconds or DEFAULT_TIME_LIMIT_SECONDS) // 6)
        )
        request_solver.parameters.num_search_workers = 8
        request_solver.parameters.random_seed = 202607
        request_status = request_solver.Solve(model)
        if request_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            active_solver = request_solver
            active_status = request_status
            request_succeeded = True
            best_request = int(round(request_solver.Value(request_objective)))
            model.Add(request_objective <= best_request)

    balance_baseline_solver = active_solver
    balance_solver: cp_model.CpSolver | None = None
    balance_status: cp_model.CpSolverStatus | None = None
    balance_succeeded = False
    if de_balance_vars and request_succeeded:
        model.ClearHints()
        for variable in x.values():
            model.AddHint(variable, balance_baseline_solver.Value(variable))
        model.Minimize(de_balance_objective)
        balance_solver = cp_model.CpSolver()
        balance_solver.parameters.max_time_in_seconds = min(
            15, max(5, int(payload.timeLimitSeconds or DEFAULT_TIME_LIMIT_SECONDS) // 5)
        )
        balance_solver.parameters.num_search_workers = 8
        balance_solver.parameters.random_seed = 202607
        balance_status = balance_solver.Solve(model)
        if balance_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            active_solver = balance_solver
            active_status = balance_status
            balance_succeeded = True
            best_de_balance = int(round(balance_solver.Value(de_balance_objective)))
            model.Add(de_balance_objective <= best_de_balance)

    repetition_solver: cp_model.CpSolver | None = None
    repetition_status: cp_model.CpSolverStatus | None = None
    repetition_succeeded = False
    repetition_baseline_value = int(round(active_solver.Value(repetition_objective)))
    if balance_succeeded:
        model.ClearHints()
        for variable in x.values():
            model.AddHint(variable, active_solver.Value(variable))
        model.Minimize(repetition_objective)
        repetition_solver = cp_model.CpSolver()
        repetition_solver.parameters.max_time_in_seconds = min(
            20, max(5, int(payload.timeLimitSeconds or DEFAULT_TIME_LIMIT_SECONDS) // 5)
        )
        repetition_solver.parameters.num_search_workers = 8
        repetition_solver.parameters.random_seed = 202607
        repetition_status = repetition_solver.Solve(model)
        if repetition_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            active_solver = repetition_solver
            active_status = repetition_status
            repetition_succeeded = True
            best_repetition = int(round(repetition_solver.Value(repetition_objective)))
            model.Add(repetition_objective <= best_repetition)

    single_shift_solver: cp_model.CpSolver | None = None
    single_shift_status: cp_model.CpSolverStatus | None = None
    single_shift_succeeded = False
    single_shift_baseline_value = int(round(
        active_solver.Value(single_shift_objective)
    ))
    if repetition_succeeded:
        model.ClearHints()
        for variable in x.values():
            model.AddHint(variable, active_solver.Value(variable))
        model.Minimize(single_shift_objective)
        single_shift_solver = cp_model.CpSolver()
        single_shift_solver.parameters.max_time_in_seconds = min(
            20, max(5, int(payload.timeLimitSeconds or DEFAULT_TIME_LIMIT_SECONDS) // 5)
        )
        single_shift_solver.parameters.num_search_workers = 8
        single_shift_solver.parameters.random_seed = 202607
        single_shift_status = single_shift_solver.Solve(model)
        if single_shift_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            active_solver = single_shift_solver
            active_status = single_shift_status
            single_shift_succeeded = True
            best_single_shift = int(round(
                single_shift_solver.Value(single_shift_objective)
            ))
            model.Add(single_shift_objective <= best_single_shift)

    off_solver: cp_model.CpSolver | None = None
    off_status: cp_model.CpSolverStatus | None = None
    off_succeeded = False
    off_baseline_value = int(round(active_solver.Value(off_objective)))
    if single_shift_succeeded:
        model.ClearHints()
        for variable in x.values():
            model.AddHint(variable, active_solver.Value(variable))
        model.Minimize(off_objective)
        off_solver = cp_model.CpSolver()
        off_solver.parameters.max_time_in_seconds = min(
            15, max(5, int(payload.timeLimitSeconds or DEFAULT_TIME_LIMIT_SECONDS) // 6)
        )
        off_solver.parameters.num_search_workers = 8
        off_solver.parameters.random_seed = 202607
        off_status = off_solver.Solve(model)
        if off_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            active_solver = off_solver
            active_status = off_status
            off_succeeded = True
            best_off = int(round(off_solver.Value(off_objective)))
            model.Add(off_objective <= best_off)

    quality_baseline_solver = active_solver
    quality_baseline_value = int(round(
        quality_baseline_solver.Value(other_quality_objective)
    ))
    quality_solver: cp_model.CpSolver | None = None
    quality_status: cp_model.CpSolverStatus | None = None
    if other_quality_terms and off_succeeded:
        model.ClearHints()
        for variable in x.values():
            model.AddHint(variable, quality_baseline_solver.Value(variable))
        model.Minimize(other_quality_objective)
        quality_solver = cp_model.CpSolver()
        quality_solver.parameters.max_time_in_seconds = min(
            20, max(5, int(payload.timeLimitSeconds or DEFAULT_TIME_LIMIT_SECONDS) // 5)
        )
        quality_solver.parameters.num_search_workers = 8
        quality_solver.parameters.random_seed = 202607
        quality_status = quality_solver.Solve(model)
        if quality_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            active_solver = quality_solver
            active_status = quality_status

    def de_balance_snapshot(snapshot_solver: cp_model.CpSolver) -> dict[str, Any]:
        individual: list[dict[str, Any]] = []
        for nurse in workers:
            nurse_id = str(nurse["id"])
            d_total, e_total, de_gap = de_balance_vars[nurse_id]
            individual.append({
                "nurse_id": nurse_id,
                "name": nurse_name(nurse),
                "day_count": snapshot_solver.Value(d_total),
                "evening_count": snapshot_solver.Value(e_total),
                "difference": snapshot_solver.Value(de_gap),
            })
        average = (
            sum(item["difference"] for item in individual) / len(individual)
            if individual else 0
        )
        return {
            "average_difference": round(average, 3),
            "individual": individual,
        }

    balance_before = de_balance_snapshot(balance_baseline_solver)
    balance_after = de_balance_snapshot(active_solver)

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
    quality_metrics = schedule_quality_metrics(
        payload, schedule, workers, minimum_off
    )
    final_off_shortfall = int(round(active_solver.Value(total_off_shortfall)))

    return {
        "success": True,
        "schedule": schedule,
        "message": "근무표가 생성되었습니다.",
        "hard_violations": [],
        "warnings": precheck_warnings + validation["warnings"],
        "unmet_requests": validation["unmet_requests"],
        "validation": validation,
        "staffing_summary": validation["staffing_summary"],
        "grade_summary": validation["grade_summary"],
        "individual_shift_counts": validation["individual_shift_counts"],
        "off_shortfall_count": final_off_shortfall,
        "quality_metrics": quality_metrics,
        "de_balance_summary": {
            "before_average_difference": balance_before["average_difference"],
            "after_average_difference": balance_after["average_difference"],
            "individual": balance_after["individual"],
            "status": (
                balance_solver.StatusName(balance_status)
                if balance_solver is not None and balance_status is not None
                else "SKIPPED"
            ),
            "fallback_used": not balance_succeeded,
        },
        "soft_quality_summary": {
            "baseline_penalty": quality_baseline_value,
            "final_penalty": int(round(active_solver.Value(other_quality_objective))),
            "status": (
                quality_solver.StatusName(quality_status)
                if quality_solver is not None and quality_status is not None
                else "SKIPPED"
            ),
            "fallback_used": bool(
                quality_solver is not None
                and quality_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE)
            ),
        },
        "optimization_stages": {
            "shift_requests": {
                "baseline_unmet": request_baseline_value,
                "final_unmet": int(round(active_solver.Value(request_objective))),
                "status": (
                    request_solver.StatusName(request_status)
                    if request_solver is not None and request_status is not None
                    else "NO_REQUESTS"
                ),
                "fallback_used": bool(
                    request_solver is not None
                    and request_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE)
                ),
            },
            "de_balance": {
                "status": (
                    balance_solver.StatusName(balance_status)
                    if balance_solver is not None and balance_status is not None
                    else "SKIPPED"
                ),
                "fallback_used": not balance_succeeded,
            },
            "work_off_repetition": {
                "baseline_penalty": repetition_baseline_value,
                "final_penalty": int(round(active_solver.Value(repetition_objective))),
                "status": (
                    repetition_solver.StatusName(repetition_status)
                    if repetition_solver is not None and repetition_status is not None
                    else "SKIPPED"
                ),
                "fallback_used": bool(
                    repetition_solver is not None
                    and repetition_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE)
                ),
            },
            "single_de_blocks": {
                "baseline_penalty": single_shift_baseline_value,
                "final_penalty": int(round(
                    active_solver.Value(single_shift_objective)
                )),
                "status": (
                    single_shift_solver.StatusName(single_shift_status)
                    if single_shift_solver is not None
                    and single_shift_status is not None
                    else "SKIPPED"
                ),
                "fallback_used": bool(
                    single_shift_solver is not None
                    and single_shift_status
                    not in (cp_model.OPTIMAL, cp_model.FEASIBLE)
                ),
            },
            "off_target_distribution": {
                "baseline_penalty": off_baseline_value,
                "final_penalty": int(round(active_solver.Value(off_objective))),
                "status": (
                    off_solver.StatusName(off_status)
                    if off_solver is not None and off_status is not None
                    else "SKIPPED"
                ),
                "fallback_used": bool(
                    off_solver is not None
                    and off_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE)
                ),
            },
            "other_preferences": {
                "baseline_penalty": quality_baseline_value,
                "final_penalty": int(round(active_solver.Value(other_quality_objective))),
                "status": (
                    quality_solver.StatusName(quality_status)
                    if quality_solver is not None and quality_status is not None
                    else "SKIPPED"
                ),
                "fallback_used": bool(
                    quality_solver is not None
                    and quality_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE)
                ),
            },
        },
        "solver_seconds": round(
            solver.WallTime()
            + (request_solver.WallTime() if request_solver is not None else 0)
            + (balance_solver.WallTime() if balance_solver is not None else 0)
            + (repetition_solver.WallTime() if repetition_solver is not None else 0)
            + (single_shift_solver.WallTime() if single_shift_solver is not None else 0)
            + (off_solver.WallTime() if off_solver is not None else 0)
            + (quality_solver.WallTime() if quality_solver is not None else 0),
            3,
        ),
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
    off_requests, off_request_conflicts = requested_off(payload, worker_ids, num_days)
    shift_requests, shift_request_conflicts = requested_assignments(
        payload, worker_ids, num_days
    )
    request_conflicts = off_request_conflicts + shift_request_conflicts
    hard: list[dict[str, Any]] = []
    warnings = [item for item in request_conflicts if item.get("warning_only")]
    unmet_requests: list[dict[str, Any]] = []
    staffing_summary: list[dict[str, Any]] = []
    grade_summary: list[dict[str, Any]] = []
    counts_summary: list[dict[str, Any]] = []

    def violation(kind: str, message: str, **details: Any) -> None:
        hard.append({"type": kind, "message": message, **details})

    for nurse in workers:
        nurse_id = str(nurse["id"])
        row = list(schedule.get(nurse_id) or [])
        previous_row = previous_shifts(payload, nurse)
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
        if previous_row and previous_row[-1] == "N" and row[0] in {"D", "E"}:
            violation(
                "PREVIOUS_N_TO_DE",
                f"{names[nurse_id]}의 이전 달 말일 N 다음에 이번 달 1일 {row[0]}가 배정되었습니다.",
                nurseId=nurse_id,
                day=1,
                actual=f"N → {row[0]}",
                required="N 연속 또는 OFF",
                boundary=True,
            )
        for day in previous_night_cooldown_days(payload, nurse, num_days):
            if row[day - 1] == "N":
                violation(
                    "previous_month_night_cooldown",
                    (
                        f"{names[nurse_id]}의 이전 달 Night 종료 후 4일 이내인 "
                        f"이번 달 {day}일에 Night가 재배정되었습니다."
                    ),
                    nurseId=nurse_id,
                    day=day,
                    actual="N",
                    required="이전 Night 종료 후 4일간 N 금지",
                    boundary=True,
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
        allowed_off_counts = {minimum_off, max(0, minimum_off - 1)}
        if counts["OFF"] not in allowed_off_counts:
            violation(
                "off_count_mismatch",
                f"{names[nurse_id]} OFF {counts['OFF']}개 / 허용 {minimum_off}개 또는 {max(0, minimum_off - 1)}개",
                nurseId=nurse_id,
                name=names[nurse_id],
                actual=counts["OFF"],
                required=f"{minimum_off} 또는 {max(0, minimum_off - 1)}",
            )
        elif minimum_off > 0 and counts["OFF"] == minimum_off - 1:
            warnings.append({
                "type": "off_one_below_target",
                "message": f"{names[nurse_id]} OFF가 목표 {minimum_off}개보다 1개 적은 {counts['OFF']}개입니다.",
                "nurseId": nurse_id,
                "name": names[nurse_id],
                "actual": counts["OFF"],
                "preferred": minimum_off,
                "warning_only": True,
            })
        for shift in ("D", "E"):
            if counts[shift] < 4:
                warnings.append({
                    "type": f"{shift.lower()}_below_preferred",
                    "message": (
                        f"{names[nurse_id]} {shift} 근무가 {counts[shift]}회입니다. "
                        "권장 횟수는 4회 이상입니다."
                    ),
                    "nurseId": nurse_id,
                    "name": names[nurse_id],
                    "shift": shift,
                    "actual": counts[shift],
                    "preferred": "4 이상",
                    "warning_only": True,
                })
        de_difference = abs(counts["D"] - counts["E"])
        if de_difference > 4:
            warnings.append({
                "type": "de_balance_preference",
                "message": (
                    f"{names[nurse_id]} D/E 차이가 {de_difference}회입니다. "
                    "권장 차이는 4회 이하입니다."
                ),
                "nurseId": nurse_id,
                "name": names[nurse_id],
                "actual": de_difference,
                "preferred": "4 이하",
                "day_count": counts["D"],
                "evening_count": counts["E"],
                "warning_only": True,
            })
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
                previous_run = 0
                if shift_start == 0:
                    for value in reversed(previous_row):
                        if value != shift:
                            break
                        previous_run += 1
                combined_run_length = run_length + previous_run
                if combined_run_length < 2 or combined_run_length > 5:
                    warnings.append({
                        "type": (
                            f"previous_month_{shift.lower()}_block_preference"
                            if previous_run else f"{shift.lower()}_block_preference"
                        ),
                        "message": (
                            f"{names[nurse_id]} {'이전 달부터 이어진 ' if previous_run else ''}{shift} "
                            f"연속근무가 {combined_run_length}일입니다. 권장 범위는 2~5일입니다."
                        ),
                        "nurseId": nurse_id,
                        "day": shift_start + 1,
                        "actual": combined_run_length,
                        "preferred": "2~5",
                        "boundary": bool(previous_run),
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
            previous_work = 0
            if work_start == 0:
                for value in reversed(previous_row):
                    if value == "OFF":
                        break
                    previous_work += 1
            combined_work_length = work_length + previous_work
            if combined_work_length > 5:
                violation(
                    (
                        "previous_month_consecutive_work_preference"
                        if previous_work else "consecutive_work_preference"
                    ),
                    (
                        f"{names[nurse_id]} {'이전 달부터 이어진 ' if previous_work else ''}연속근무가 "
                        f"{combined_work_length}일입니다. 연속근무는 최대 5일까지 허용됩니다."
                    ),
                    nurseId=nurse_id,
                    day=work_start + 1,
                    actual=combined_work_length,
                    required="5 이하",
                    boundary=bool(previous_work),
                )

        blocks: list[tuple[int, int]] = []
        if previous_night_run and row[0] != "N":
            blocks.append((0, previous_night_run))
            allowed = {3} if names[nurse_id] == LEE_HYEMI else {2, 3}
            if previous_night_run not in allowed:
                violation(
                    "previous_month_night_block_length",
                    f"{names[nurse_id]}의 이전 달에서 끝난 N 블록이 {previous_night_run}일입니다.",
                    nurseId=nurse_id,
                    day=1,
                    actual=previous_night_run,
                    required="3" if names[nurse_id] == LEE_HYEMI else "2~3",
                    boundary=True,
                )
            recovery = row[:2]
            if len(recovery) == 2 and recovery != ["OFF", "OFF"]:
                violation(
                    "previous_month_night_recovery",
                    f"{names[nurse_id]}의 이전 달 N 블록 후 이번 달 OFF 2일이 없습니다.",
                    nurseId=nurse_id,
                    day=1,
                    actual="/".join(recovery),
                    required="OFF/OFF",
                    boundary=True,
                )
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
                    boundary=bool(start == 0 and previous_night_run),
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
                    boundary=bool(start == 0 and previous_night_run),
                )
            cooldown = row[index:min(index + 4, num_days)]
            next_night_offset = next(
                (offset for offset, value in enumerate(cooldown) if value == "N"),
                None,
            )
            if next_night_offset is not None:
                violation(
                    "night_cooldown",
                    (
                        f"{names[nurse_id]} {start + 1}일 시작 Night 블록 종료 후 "
                        f"{next_night_offset + 1}일 만에 Night가 재배정되었습니다."
                    ),
                    nurseId=nurse_id,
                    day=index + next_night_offset + 1,
                    actual=f"종료 후 {next_night_offset + 1}일",
                    required="Night 종료 후 4일간 N 금지",
                    boundary=bool(start == 0 and previous_night_run),
                )
        if names[nurse_id] == LEE_HYEMI and (len(blocks) != 2 or any(length != 3 for _, length in blocks)):
            violation(
                "lee_hyemi_night_rule",
                "이혜미 간호사의 Night는 3일 연속 블록 2개여야 합니다.",
                nurseId=nurse_id,
                actual=blocks,
                required="3N 블록 2개",
            )

    for (nurse_id, day), requested_shift in shift_requests.items():
        row = schedule.get(nurse_id, [])
        if len(row) >= day and row[day - 1] != requested_shift:
            item = {
                "type": "shift_request_unmet",
                "message": (
                    f"{names[nurse_id]} {day}일 신청 {requested_shift}가 "
                    "절대조건과 충돌하여 반영되지 않았습니다."
                ),
                "nurseId": nurse_id,
                "day": day,
                "actual": row[day - 1],
                "required": requested_shift,
                "warning_only": True,
            }
            unmet_requests.append(item)
            warnings.append(item)

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
        "unmet_requests": unmet_requests,
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
