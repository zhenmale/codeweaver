"""
Token 遥测系统：企业级 Token 消耗追踪与成本优化
支持实时告警、预算预测、异常检测
"""
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import statistics
import asyncio


@dataclass
class TokenUsage:
    timestamp: datetime
    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    task_type: str
    success: bool
    cache_hit: bool = False


class TokenTelemetryCollector:
    """
    Token 遥测收集器
    特性：
    1. 滑动窗口统计（实时性能指标）
    2. 异常检测（消耗突增告警）
    3. 预算预测（基于趋势线性回归）
    4. 成本归因（按 Agent/团队/项目拆分）
    """

    # 模型定价（元/百万token）
    PRICING = {
        "MiMo-V2.5": {"input": 0.5, "output": 2.0},
        "MiMo-V2.5-Pro": {"input": 2.0, "output": 8.0},
        "claude-3-opus": {"input": 30.0, "output": 150.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},
    }

    def __init__(self, window_size: int = 10000):
        self.window_size = window_size
        self.usage_buffer: deque = deque(maxlen=window_size)
        self.daily_totals: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "total_tokens": 0,
                "total_cost": 0.0,
                "agent_breakdown": defaultdict(
                    lambda: {"tokens": 0, "cost": 0.0, "calls": 0}
                ),
                "model_breakdown": defaultdict(lambda: {"tokens": 0, "cost": 0.0}),
                "hourly": [0] * 24,
            }
        )

        self.budget_limit_daily = 5000.0  # 日预算上限（元）
        self.alert_callbacks: List[Callable] = []
        self.anomaly_threshold = 3.0  # 标准差倍数

    def record(self, usage: TokenUsage) -> None:
        """记录一次 Token 使用"""
        self.usage_buffer.append(usage)

        # 更新日统计
        day_key = usage.timestamp.strftime("%Y-%m-%d")
        day_stats = self.daily_totals[day_key]
        day_stats["total_tokens"] += usage.input_tokens + usage.output_tokens
        day_stats["total_cost"] += usage.cost_usd

        agent_stats = day_stats["agent_breakdown"][usage.agent]
        agent_stats["tokens"] += usage.input_tokens + usage.output_tokens
        agent_stats["cost"] += usage.cost_usd
        agent_stats["calls"] += 1

        model_stats = day_stats["model_breakdown"][usage.model]
        model_stats["tokens"] += usage.input_tokens + usage.output_tokens
        model_stats["cost"] += usage.cost_usd

        hour = usage.timestamp.hour
        day_stats["hourly"][hour] += usage.input_tokens + usage.output_tokens

        # 实时告警检查
        self._check_alerts(day_key, day_stats)

    def _check_alerts(self, day_key: str, day_stats: Dict):
        """检查是否需要触发告警"""
        # 预算告警
        if day_stats["total_cost"] > self.budget_limit_daily * 0.8:
            self._trigger_alert(
                "budget_warning",
                {
                    "day": day_key,
                    "current": day_stats["total_cost"],
                    "limit": self.budget_limit_daily,
                    "percentage": day_stats["total_cost"] / self.budget_limit_daily * 100,
                },
            )

        # 异常检测（基于滑动窗口）
        if len(self.usage_buffer) >= 100:
            recent = list(self.usage_buffer)[-100:]
            latencies = [u.latency_ms for u in recent]
            mean_lat = statistics.mean(latencies)
            std_lat = statistics.stdev(latencies) if len(latencies) > 1 else 0

            last = recent[-1]
            if std_lat > 0 and (last.latency_ms - mean_lat) > self.anomaly_threshold * std_lat:
                self._trigger_alert(
                    "latency_anomaly",
                    {
                        "timestamp": last.timestamp.isoformat(),
                        "latency": last.latency_ms,
                        "mean": mean_lat,
                        "std": std_lat,
                        "agent": last.agent,
                    },
                )

    def _trigger_alert(self, alert_type: str, data: Dict):
        """触发告警"""
        alert = {"type": alert_type, "timestamp": datetime.now().isoformat(), "data": data}
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception:
                pass

    def on_alert(self, callback: Callable):
        """注册告警回调"""
        self.alert_callbacks.append(callback)

    def get_realtime_stats(self) -> Dict[str, Any]:
        """获取实时统计"""
        if not self.usage_buffer:
            return {"status": "no_data"}

        recent = list(self.usage_buffer)
        last_100 = recent[-100:] if len(recent) >= 100 else recent

        return {
            "total_records": len(self.usage_buffer),
            "last_100": {
                "avg_latency_ms": statistics.mean([u.latency_ms for u in last_100]),
                "avg_tokens_per_call": statistics.mean(
                    [u.input_tokens + u.output_tokens for u in last_100]
                ),
                "success_rate": sum(1 for u in last_100 if u.success) / len(last_100),
                "cache_hit_rate": sum(1 for u in last_100 if u.cache_hit) / len(last_100),
            },
            "models_used": list(set(u.model for u in recent)),
            "agents_active": list(set(u.agent for u in recent)),
        }

    def predict_monthly_budget(self) -> Dict[str, Any]:
        """预测月度预算（基于最近7天趋势）"""
        today = datetime.now().date()
        daily_costs = []

        for i in range(7):
            day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if day in self.daily_totals:
                daily_costs.append(self.daily_totals[day]["total_cost"])

        if len(daily_costs) < 3:
            return {"status": "insufficient_data", "prediction": None}

        avg_daily = statistics.mean(daily_costs)
        trend = (daily_costs[0] - daily_costs[-1]) / len(daily_costs) if len(daily_costs) > 1 else 0

        predicted_daily = avg_daily + trend * 7  # 趋势外推
        monthly_prediction = predicted_daily * 30

        return {
            "status": "ok",
            "historical_avg_daily": avg_daily,
            "trend_per_day": trend,
            "predicted_daily": predicted_daily,
            "predicted_monthly": monthly_prediction,
            "budget_limit_monthly": self.budget_limit_daily * 30,
            "risk_level": (
                "high"
                if monthly_prediction > self.budget_limit_daily * 30 * 1.2
                else "medium" if monthly_prediction > self.budget_limit_daily * 30 else "low"
            ),
        }

    def generate_cost_report(self, days: int = 7) -> Dict[str, Any]:
        """生成成本归因报告"""
        today = datetime.now().date()
        report = {
            "period": f"{(today - timedelta(days=days)).isoformat()} to {today.isoformat()}",
            "summary": {"total_tokens": 0, "total_cost": 0.0, "total_calls": 0},
            "by_agent": {},
            "by_model": {},
            "by_day": [],
            "efficiency_metrics": {},
        }

        for i in range(days):
            day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if day not in self.daily_totals:
                continue

            day_data = self.daily_totals[day]
            report["summary"]["total_tokens"] += day_data["total_tokens"]
            report["summary"]["total_cost"] += day_data["total_cost"]
            report["summary"]["total_calls"] += sum(
                a["calls"] for a in day_data["agent_breakdown"].values()
            )

            report["by_day"].append(
                {"date": day, "tokens": day_data["total_tokens"], "cost": day_data["total_cost"]}
            )

            # 合并 Agent 统计
            for agent, stats in day_data["agent_breakdown"].items():
                if agent not in report["by_agent"]:
                    report["by_agent"][agent] = {"tokens": 0, "cost": 0.0, "calls": 0}
                report["by_agent"][agent]["tokens"] += stats["tokens"]
                report["by_agent"][agent]["cost"] += stats["cost"]
                report["by_agent"][agent]["calls"] += stats["calls"]

            # 合并 Model 统计
            for model, stats in day_data["model_breakdown"].items():
                if model not in report["by_model"]:
                    report["by_model"][model] = {"tokens": 0, "cost": 0.0}
                report["by_model"][model]["tokens"] += stats["tokens"]
                report["by_model"][model]["cost"] += stats["cost"]

        # 效率指标
        if report["summary"]["total_calls"] > 0:
            report["efficiency_metrics"] = {
                "cost_per_call": report["summary"]["total_cost"] / report["summary"]["total_calls"],
                "tokens_per_call": report["summary"]["total_tokens"]
                / report["summary"]["total_calls"],
                "cost_per_1k_tokens": report["summary"]["total_cost"]
                / (report["summary"]["total_tokens"] / 1000),
            }

        return report


if __name__ == "__main__":
    collector = TokenTelemetryCollector()

    # 注册告警回调
    def on_alert(alert):
        print(f"\n🚨 告警触发: {alert['type']}")
        print(json.dumps(alert["data"], indent=2, ensure_ascii=False))

    collector.on_alert(on_alert)

    # 模拟 30 天的数据（Max Plan 规模）
    import random

    agents = ["architect", "quantum", "semantic", "synthesis", "oracle"]
    models = ["MiMo-V2.5-Pro", "MiMo-V2.5", "claude-3-opus"]

    base_date = datetime.now() - timedelta(days=30)

    for day in range(30):
        current_date = base_date + timedelta(days=day)
        daily_calls = random.randint(800, 1500)  # 日调用次数

        for _ in range(daily_calls):
            hour = random.randint(9, 23)
            timestamp = current_date.replace(hour=hour)

            agent = random.choice(agents)
            model = random.choice(models)

            # Token 规模：MiMo-Pro 单次 5k-20k，Claude 单次 10k-50k
            if model == "MiMo-V2.5-Pro":
                input_t = random.randint(3000, 10000)
                output_t = random.randint(2000, 10000)
            elif model == "claude-3-opus":
                input_t = random.randint(5000, 20000)
                output_t = random.randint(5000, 30000)
            else:
                input_t = random.randint(1000, 5000)
                output_t = random.randint(500, 3000)

            pricing = collector.PRICING.get(model, {"input": 2.0, "output": 8.0})
            cost = (input_t * pricing["input"] + output_t * pricing["output"]) / 1_000_000

            usage = TokenUsage(
                timestamp=timestamp,
                agent=agent,
                model=model,
                input_tokens=input_t,
                output_tokens=output_t,
                cost_usd=cost * 0.14,  # 换算为 USD
                latency_ms=random.randint(2000, 30000),
                task_type=random.choice(["refactor", "synthesize", "analyze", "validate"]),
                success=random.random() > 0.05,
                cache_hit=random.random() > 0.7,
            )

            collector.record(usage)

    print("=== 实时统计 ===")
    print(json.dumps(collector.get_realtime_stats(), indent=2, ensure_ascii=False))

    print("\n=== 月度预算预测 ===")
    print(json.dumps(collector.predict_monthly_budget(), indent=2, ensure_ascii=False))

    print("\n=== 7日成本报告 ===")
    report = collector.generate_cost_report(days=7)
    print(f"总Token: {report['summary']['total_tokens']:,}")
    print(f"总成本: ¥{report['summary']['total_cost']:.2f}")
    print(f"总调用: {report['summary']['total_calls']:,}")
    print("\nAgent 归因:")
    for agent, stats in report["by_agent"].items():
        print(f"  {agent}: {stats['tokens']:,} tokens, ¥{stats['cost']:.2f}, {stats['calls']} calls")
