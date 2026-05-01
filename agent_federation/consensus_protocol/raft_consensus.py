"""
联邦共识协议：基于 RAFT 改进的多 Agent 决策共识
解决多 Agent 对重构方案意见不一致时的决策问题
"""
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import random
import time


class AgentRole(Enum):
    LEADER = "leader"  # 协调者（Architect Agent）
    FOLLOWER = "follower"  # 执行者
    CANDIDATE = "candidate"  # 候选者


class ProposalStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMMITTED = "committed"


@dataclass
class Proposal:
    id: str
    term: int
    proposer: str
    action: Dict[str, Any]
    votes: Dict[str, bool] = field(default_factory=dict)
    status: ProposalStatus = ProposalStatus.PENDING
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class FederationConsensus:
    """
    联邦共识引擎
    特性：
    1. 基于 RAFT 的领导者选举
    2. 多轮投票机制（支持置信度加权）
    3. 分区容错（网络隔离时降级运行）
    """

    def __init__(self, node_id: str, peers: List[str]):
        self.node_id = node_id
        self.peers = [p for p in peers if p != node_id]
        self.role = AgentRole.FOLLOWER
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.leader_id: Optional[str] = None
        self.proposal_log: List[Proposal] = []
        self.committed_index = -1

        # 选举超时（随机化避免活锁）
        self.election_timeout = random.uniform(1.5, 3.0)
        self.heartbeat_interval = 0.5

        # 置信度权重（基于 Agent 历史准确率）
        self.agent_weights: Dict[str, float] = {}

    async def start(self):
        """启动共识引擎"""
        asyncio.create_task(self._election_timer())
        if self.role == AgentRole.LEADER:
            asyncio.create_task(self._send_heartbeats())

    async def _election_timer(self):
        """选举定时器"""
        while True:
            await asyncio.sleep(self.election_timeout)
            if self.role != AgentRole.LEADER:
                await self._start_election()

    async def _start_election(self):
        """发起选举"""
        self.current_term += 1
        self.role = AgentRole.CANDIDATE
        self.voted_for = self.node_id

        votes = {self.node_id}

        # 并行请求投票
        tasks = [self._request_vote(peer) for peer in self.peers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if result is True:
                votes.add(result)

        # 获得多数票成为 Leader
        if len(votes) > (len(self.peers) + 1) / 2:
            self.role = AgentRole.LEADER
            self.leader_id = self.node_id
            print(f"[{self.node_id}] 当选为 Leader (term {self.current_term})")
            asyncio.create_task(self._send_heartbeats())

    async def _request_vote(self, peer: str) -> bool:
        """向节点请求投票"""
        # 模拟网络请求
        await asyncio.sleep(random.uniform(0.01, 0.1))
        return random.random() > 0.3  # 70% 概率同意

    async def _send_heartbeats(self):
        """Leader 发送心跳"""
        while self.role == AgentRole.LEADER:
            for peer in self.peers:
                asyncio.create_task(self._send_heartbeat(peer))
            await asyncio.sleep(self.heartbeat_interval)

    async def _send_heartbeat(self, peer: str):
        """发送单个心跳"""
        await asyncio.sleep(random.uniform(0.01, 0.05))

    async def propose(self, action: Dict[str, Any], confidence: float = 1.0) -> bool:
        """
        发起提案（仅 Leader 可调用）
        返回：是否达成共识
        """
        if self.role != AgentRole.LEADER:
            # 转发给 Leader
            if self.leader_id:
                return await self._forward_to_leader(action)
            return False

        proposal = Proposal(
            id=f"prop_{self.current_term}_{len(self.proposal_log)}",
            term=self.current_term,
            proposer=self.node_id,
            action=action,
        )

        # 第一阶段：预提交（获取多数预投票）
        pre_votes = await self._request_pre_votes(proposal)
        weighted_pre_votes = sum(
            self.agent_weights.get(voter, 1.0)
            for voter, accepted in pre_votes.items()
            if accepted
        )

        if weighted_pre_votes <= sum(self.agent_weights.values()) / 2:
            proposal.status = ProposalStatus.REJECTED
            self.proposal_log.append(proposal)
            return False

        # 第二阶段：正式提交
        proposal.status = ProposalStatus.ACCEPTED
        self.proposal_log.append(proposal)

        # 广播提交
        await self._broadcast_commit(proposal)
        proposal.status = ProposalStatus.COMMITTED
        self.committed_index = len(self.proposal_log) - 1

        return True

    async def _request_pre_votes(self, proposal: Proposal) -> Dict[str, bool]:
        """请求预投票"""
        votes = {self.node_id: True}

        tasks = []
        for peer in self.peers:
            tasks.append(self._request_pre_vote(peer, proposal))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for peer, result in zip(self.peers, results):
            if isinstance(result, bool):
                votes[peer] = result

        return votes

    async def _request_pre_vote(self, peer: str, proposal: Proposal) -> bool:
        """请求单个预投票"""
        # 模拟：基于提案质量和节点置信度
        await asyncio.sleep(random.uniform(0.05, 0.2))

        # 模拟评估逻辑
        action_complexity = proposal.action.get("complexity", 50)
        agent_expertise = random.uniform(0.7, 1.0)  # 该 Agent 在此领域的专业度

        # 专业度越高，对复杂任务越谨慎
        if action_complexity > 80 and agent_expertise < 0.9:
            return False  # 能力不足，拒绝

        return random.random() < 0.85  # 85% 基础同意率

    async def _broadcast_commit(self, proposal: Proposal):
        """广播提交"""
        tasks = [self._notify_commit(peer, proposal) for peer in self.peers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _notify_commit(self, peer: str, proposal: Proposal):
        """通知单个节点提交"""
        await asyncio.sleep(random.uniform(0.01, 0.05))

    async def _forward_to_leader(self, action: Dict[str, Any]) -> bool:
        """转发给 Leader"""
        await asyncio.sleep(0.1)
        # 模拟转发成功
        return random.random() > 0.1

    def get_committed_actions(self) -> List[Dict[str, Any]]:
        """获取已共识的行动序列"""
        return [
            p.action
            for p in self.proposal_log[: self.committed_index + 1]
            if p.status == ProposalStatus.COMMITTED
        ]

    def update_agent_weight(self, agent_id: str, accuracy: float):
        """更新 Agent 置信度权重（基于历史表现）"""
        # EMA 更新
        old_weight = self.agent_weights.get(agent_id, 1.0)
        self.agent_weights[agent_id] = 0.7 * old_weight + 0.3 * accuracy


if __name__ == "__main__":

    async def demo():
        # 5 个 Agent 的联邦
        agents = ["architect", "quantum", "semantic", "synthesis", "oracle"]

        federation = [FederationConsensus(aid, agents) for aid in agents]

        # 设置初始权重
        for f in federation:
            f.agent_weights = {
                "architect": 1.5,  # 架构师权重最高
                "quantum": 1.2,
                "semantic": 1.0,
                "synthesis": 1.0,
                "oracle": 1.3,  # 验证者权重较高
            }

        # 启动
        for f in federation:
            asyncio.create_task(f.start())

        await asyncio.sleep(2)  # 等待选举

        # 找到 Leader
        leader = next((f for f in federation if f.role == AgentRole.LEADER), None)

        if leader:
            print(f"\nLeader 是 {leader.node_id}")

            # 发起重构提案
            action = {
                "type": "refactor",
                "target": "payment_module",
                "complexity": 75,
                "strategy": "extract_service",
                "estimated_tokens": 500000,
            }

            result = await leader.propose(action)
            print(f"提案结果: {'通过' if result else '拒绝'}")

            print(f"\n已共识行动数: {len(leader.get_committed_actions())}")

    asyncio.run(demo())
