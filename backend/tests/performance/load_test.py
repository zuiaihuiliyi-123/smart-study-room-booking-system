"""API 基线性能测试（asyncio + httpx，无第三方压测工具依赖）。

前置：
    1. 已运行 tests/performance/seed_perf.py 生成隔离数据；
    2. 后端以隔离 DATABASE_URL 启动，并调高登录/注册限流（压测登录时）。

用法：
    .venv/Scripts/python.exe -m tests.performance.load_test \
      --context .perf/context.json \
      --scenarios available_seats,seats_directory,my_reservations,\
dashboard_overview,dashboard_slot_usage,audit_logs,create_reservation,login \
      --out .perf/results.json

说明：客户端与服务端同机，结果用于基线对比，不等同于生产容量规划。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

SCENARIOS: dict[str, dict[str, int]] = {
    # 核心读接口
    "available_seats": {"concurrency": 50, "duration": 20},
    "seats_directory": {"concurrency": 50, "duration": 20},
    "my_reservations": {"concurrency": 50, "duration": 20},
    # 管理端
    "dashboard_overview": {"concurrency": 30, "duration": 20},
    "dashboard_slot_usage": {"concurrency": 10, "duration": 15},
    "audit_logs": {"concurrency": 30, "duration": 15},
    # 写接口
    "create_reservation": {"concurrency": 20, "duration": 60},
    # 认证（Argon2）
    "login": {"concurrency": 5, "duration": 10},
}


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100) * (len(ordered) - 1)))))
    return ordered[index]


def _build_request(
    scenario: str,
    ctx: dict,
    token: str,
    today: date,
    tomorrow: date,
    case: dict | None,
) -> tuple[str, str, dict | None, dict | None]:
    """返回 (method, url, headers, json_body)。"""
    auth = {"Authorization": f"Bearer {token}"}
    admin = {"Authorization": f"Bearer {ctx['admin_token']}"}
    if scenario == "available_seats":
        return (
            "GET",
            "/api/v1/reservations/available-seats",
            auth,
            {
                "room_id": ctx["room_id"],
                "reserve_date": tomorrow.isoformat(),
                "start_time": "14:00",
                "end_time": "16:00",
            },
        )
    if scenario == "seats_directory":
        return ("GET", f"/api/v1/rooms/{ctx['room_id']}/seats", auth, None)
    if scenario == "my_reservations":
        return (
            "GET",
            "/api/v1/reservations/me",
            auth,
            {"page": 1, "page_size": 20},
        )
    if scenario == "dashboard_overview":
        return ("GET", "/api/v1/dashboard/overview", admin, None)
    if scenario == "dashboard_slot_usage":
        return (
            "GET",
            "/api/v1/dashboard/seat-usage",
            admin,
            {
                "start_date": (today - timedelta(days=6)).isoformat(),
                "end_date": today.isoformat(),
                "room_id": ctx["room_id"],
                "group_by": "slot",
            },
        )
    if scenario == "audit_logs":
        return (
            "GET",
            "/api/v1/audit-logs",
            admin,
            {"page": 1, "page_size": 20},
        )
    if scenario == "create_reservation":
        assert case is not None
        return (
            "POST",
            "/api/v1/reservations",
            {"Authorization": f"Bearer {case['token']}"},
            {
                "seat_id": case["seat_id"],
                "reserve_date": case["reserve_date"],
                "start_time": case["start_time"],
                "end_time": case["end_time"],
                "idempotency_key": case["idempotency_key"],
            },
        )
    if scenario == "login":
        return ("POST", "/api/v1/auth/login", {}, ctx["admin_login"])
    raise ValueError(scenario)


async def _worker(
    client: httpx.AsyncClient,
    scenario: str,
    ctx: dict,
    stop_at: float,
    today: date,
    tomorrow: date,
    latencies: list[float],
    outcomes: list[tuple[int | None, str]],
    queue: asyncio.Queue | None,
) -> None:
    while time.perf_counter() < stop_at:
        case = None
        if queue is not None:
            try:
                case = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
        token = (
            case["token"]
            if case is not None
            else ctx["student_tokens"][len(latencies) % len(ctx["student_tokens"])]
        )
        method, url, headers, body = _build_request(
            scenario, ctx, token, today, tomorrow, case
        )
        started = time.perf_counter()
        try:
            if method == "GET":
                response = await client.get(url, headers=headers, params=body)
            else:
                response = await client.post(url, headers=headers, json=body)
            elapsed = (time.perf_counter() - started) * 1000
            latencies.append(elapsed)
            ok = 200 <= response.status_code < 300
            outcomes.append((response.status_code, "" if ok else response.text[:200]))
        except Exception as exc:  # noqa: BLE001
            elapsed = (time.perf_counter() - started) * 1000
            latencies.append(elapsed)
            outcomes.append((None, f"{type(exc).__name__}: {exc}"))


async def run_scenario(name: str, ctx: dict, config: dict[str, int]) -> dict:
    scenario = name
    today = date.today()
    tomorrow = date.fromisoformat(ctx["tomorrow"])
    concurrency = config["concurrency"]
    duration = config["duration"]

    limits = httpx.Limits(
        max_connections=concurrency + 5, max_keepalive_connections=concurrency + 5
    )
    async with httpx.AsyncClient(
        base_url=ctx["base_url"], timeout=30.0, limits=limits
    ) as client:
        # 预热：忽略前几次结果，避免连接建立影响首包
        try:
            await client.get("/health")
        except Exception:  # noqa: BLE001
            pass

        latencies: list[float] = []
        outcomes: list[tuple[int | None, str]] = []
        queue: asyncio.Queue | None = None
        if scenario == "create_reservation":
            queue = asyncio.Queue()
            for case in ctx["write_cases"]:
                queue.put_nowait(case)
            stop_at = time.perf_counter() + duration
        else:
            stop_at = time.perf_counter() + duration

        started = time.perf_counter()
        workers = [
            asyncio.create_task(
                _worker(
                    client,
                    scenario,
                    ctx,
                    stop_at,
                    today,
                    tomorrow,
                    latencies,
                    outcomes,
                    queue,
                )
            )
            for _ in range(concurrency)
        ]
        await asyncio.gather(*workers)
        elapsed = time.perf_counter() - started

    successes = sum(1 for status, _ in outcomes if status is not None and 200 <= status < 300)
    errors = [
        {"status": status, "body": body}
        for status, body in outcomes
        if status is None or not (200 <= status < 300)
    ]
    result = {
        "scenario": scenario,
        "concurrency": concurrency,
        "duration_s": round(elapsed, 2),
        "requests": len(outcomes),
        "rps": round(len(outcomes) / elapsed, 1) if elapsed else 0,
        "success": successes,
        "success_rate": round(successes / len(outcomes) * 100, 2) if outcomes else 0,
        "latency_ms": {
            "avg": round(statistics.mean(latencies), 1) if latencies else 0,
            "p50": round(_percentile(latencies, 50), 1),
            "p90": round(_percentile(latencies, 90), 1),
            "p95": round(_percentile(latencies, 95), 1),
            "p99": round(_percentile(latencies, 99), 1),
            "max": round(max(latencies), 1) if latencies else 0,
        },
        "errors_sample": errors[:3],
        "error_count": len(errors),
    }
    return result


async def main_async(args: argparse.Namespace) -> None:
    ctx = json.loads(Path(args.context).read_text(encoding="utf-8"))
    selected = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    results = []
    for scenario in selected:
        if scenario not in SCENARIOS:
            raise SystemExit(f"未知场景：{scenario}")
        print(f"running {scenario} ...", flush=True)
        result = await run_scenario(scenario, ctx, SCENARIOS[scenario])
        results.append(result)
        print(
            f"{scenario}: rps={result['rps']} p95={result['latency_ms']['p95']}ms "
            f"success={result['success_rate']}% errors={result['error_count']}",
            flush=True,
        )

    payload = {
        "base_url": ctx["base_url"],
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": "客户端与服务端同机，结果为基线而非生产容量结论",
        "results": results,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"results written to {args.out}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", required=True)
    parser.add_argument("--scenarios", default=",".join(SCENARIOS))
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
