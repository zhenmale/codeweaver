"""
知识图谱引擎：将代码库建模为异构图网络
节点类型：函数、类、模块、变量、API
边类型：调用、继承、依赖、数据流、控制流
"""
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx
from collections import defaultdict
import json


class NodeType(Enum):
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    VARIABLE = "variable"
    API_ENDPOINT = "api_endpoint"
    DATABASE_TABLE = "db_table"
    CONFIGURATION = "configuration"


class EdgeType(Enum):
    CALLS = "calls"
    INHERITS = "inherits"
    IMPORTS = "imports"
    DATA_FLOW = "data_flow"
    CONTROL_FLOW = "control_flow"
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"


@dataclass
class CodeNode:
    id: str
    type: NodeType
    name: str
    file_path: str
    line_start: int
    line_end: int
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    semantic_signature: Optional[str] = None  # 语义指纹


@dataclass
class CodeEdge:
    source: str
    target: str
    type: EdgeType
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


class CodeKnowledgeGraph:
    """
    代码知识图谱
    支持：增量更新、社区发现、关键路径分析
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_index: Dict[str, CodeNode] = {}
        self.edge_index: Dict[Tuple[str, str, EdgeType], CodeEdge] = {}
        self.module_map: Dict[str, Set[str]] = defaultdict(set)
        self._version = 0

    def add_node(self, node: CodeNode) -> None:
        """添加代码节点"""
        self.graph.add_node(
            node.id,
            type=node.type.value,
            name=node.name,
            file=node.file_path,
            lines=(node.line_start, node.line_end),
            props=node.properties,
            version=self._version,
        )
        self.node_index[node.id] = node
        self.module_map[node.file_path].add(node.id)

    def add_edge(self, edge: CodeEdge) -> None:
        """添加关系边"""
        key = (edge.source, edge.target, edge.type)
        if key in self.edge_index:
            # 合并权重
            existing = self.edge_index[key]
            existing.weight += edge.weight
            self.graph[edge.source][edge.target]["weight"] = existing.weight
        else:
            self.graph.add_edge(
                edge.source,
                edge.target,
                type=edge.type.value,
                weight=edge.weight,
                props=edge.properties,
            )
            self.edge_index[key] = edge

    def find_communities(self) -> List[Set[str]]:
        """
        社区发现：识别高内聚模块
        使用 Louvain 算法
        """
        undirected = self.graph.to_undirected()
        communities = nx.community.louvain_communities(undirected, weight="weight", seed=42)
        return [set(c) for c in communities]

    def find_critical_paths(self, start: str, end: str) -> List[List[str]]:
        """
        关键路径分析：识别核心调用链
        """
        try:
            paths = list(nx.all_simple_paths(self.graph, start, end, cutoff=10))
            # 按路径权重排序
            scored_paths = []
            for path in paths:
                score = sum(
                    self.graph[path[i]][path[i + 1]].get("weight", 1)
                    for i in range(len(path) - 1)
                )
                scored_paths.append((score, path))
            scored_paths.sort(reverse=True)
            return [p for _, p in scored_paths[:5]]
        except nx.NetworkXNoPath:
            return []

    def detect_architecture_smells(self) -> List[Dict[str, Any]]:
        """
        架构异味检测
        """
        smells = []

        # 1. 循环依赖
        cycles = list(nx.simple_cycles(self.graph))
        for cycle in cycles[:10]:  # 限制报告数量
            smells.append(
                {
                    "type": "circular_dependency",
                    "severity": "critical",
                    "nodes": cycle,
                    "description": f"循环依赖: {' -> '.join(cycle)} -> {cycle[0]}",
                }
            )

        # 2. 上帝节点（入度+出度过高）
        for node_id, degree in self.graph.degree():
            if degree > 50:
                node = self.node_index.get(node_id)
                smells.append(
                    {
                        "type": "god_node",
                        "severity": "high",
                        "node": node_id,
                        "name": node.name if node else "unknown",
                        "degree": degree,
                        "description": f"上帝节点 {node.name if node else node_id} 连接数 {degree}",
                    }
                )

        # 3. 孤岛模块
        for node_id in self.graph.nodes():
            if self.graph.degree(node_id) == 0:
                node = self.node_index.get(node_id)
                smells.append(
                    {
                        "type": "island_module",
                        "severity": "medium",
                        "node": node_id,
                        "description": f"孤立模块 {node.name if node else node_id}",
                    }
                )

        return smells

    def compute_impact_radius(
        self, changed_nodes: List[str], depth: int = 3
    ) -> Dict[str, Any]:
        """
        计算变更影响半径
        返回：直接影响、间接影响、传播概率
        """
        impact = {"direct": set(), "indirect": set(), "propagation_paths": []}

        for node in changed_nodes:
            # BFS 遍历影响范围
            visited = {node}
            queue = [(node, 0)]

            while queue:
                current, dist = queue.pop(0)
                if dist >= depth:
                    continue

                for successor in self.graph.successors(current):
                    if successor not in visited:
                        visited.add(successor)
                        queue.append((successor, dist + 1))
                        if dist == 0:
                            impact["direct"].add(successor)
                        else:
                            impact["indirect"].add(successor)

        # 计算传播概率（基于边权重）
        for node in impact["direct"]:
            successors = list(self.graph.successors(node))
            if successors:
                edge_data = self.graph.get_edge_data(node, successors[0])
                if edge_data:
                    impact["propagation_paths"].append(
                        {"from": node, "probability": min(edge_data.get("weight", 1) / 10, 1.0)}
                    )

        impact["direct"] = list(impact["direct"])
        impact["indirect"] = list(impact["indirect"])
        return impact

    def export_neo4j(self) -> List[str]:
        """导出 Neo4j Cypher 语句"""
        cypher = []

        # 创建节点
        for node_id, node in self.node_index.items():
            props = json.dumps(
                {
                    "name": node.name,
                    "type": node.type.value,
                    "file": node.file_path,
                    "lines": [node.line_start, node.line_end],
                }
            )
            cypher.append(f"CREATE (n:{node.type.value} {{id: '{node_id}', {props[1:-1]}}})")

        # 创建关系
        for (src, tgt, etype), edge in self.edge_index.items():
            cypher.append(
                f"MATCH (a {{id: '{src}'}}), (b {{id: '{tgt}'}}) "
                f"CREATE (a)-[:{etype.value} {{weight: {edge.weight}}}]->(b)"
            )

        return cypher

    def incremental_update(
        self,
        file_path: str,
        new_nodes: List[CodeNode],
        new_edges: List[CodeEdge],
        removed_ids: List[str],
    ) -> None:
        """
        增量更新：文件变更时只更新相关子图
        """
        self._version += 1

        # 移除旧节点
        for rid in removed_ids:
            if rid in self.graph:
                self.graph.remove_node(rid)
                self.node_index.pop(rid, None)

        # 移除旧边（属于该文件的）
        edges_to_remove = [
            key
            for key, edge in self.edge_index.items()
            if edge.source in removed_ids or edge.target in removed_ids
        ]
        for key in edges_to_remove:
            self.edge_index.pop(key)

        # 添加新节点和边
        for node in new_nodes:
            self.add_node(node)
        for edge in new_edges:
            self.add_edge(edge)

        # 更新模块映射
        self.module_map[file_path] = {n.id for n in new_nodes}


if __name__ == "__main__":
    # 演示
    ckg = CodeKnowledgeGraph()

    # 构建示例图
    nodes = [
        CodeNode("user_service", NodeType.MODULE, "user_service", "src/user.py", 1, 100),
        CodeNode("auth_module", NodeType.MODULE, "auth_module", "src/auth.py", 1, 80),
        CodeNode("db_conn", NodeType.FUNCTION, "get_connection", "src/db.py", 10, 25),
        CodeNode("api_login", NodeType.API_ENDPOINT, "/api/login", "src/routes.py", 5, 30),
    ]

    for n in nodes:
        ckg.add_node(n)

    edges = [
        CodeEdge("api_login", "user_service", EdgeType.CALLS, 5.0),
        CodeEdge("user_service", "db_conn", EdgeType.CALLS, 3.0),
        CodeEdge("api_login", "auth_module", EdgeType.CALLS, 4.0),
        CodeEdge("auth_module", "db_conn", EdgeType.CALLS, 2.0),
    ]

    for e in edges:
        ckg.add_edge(e)

    print("=== 社区发现 ===")
    communities = ckg.find_communities()
    for i, c in enumerate(communities):
        print(f"社区 {i}: {c}")

    print("\n=== 架构异味 ===")
    smells = ckg.detect_architecture_smells()
    for s in smells:
        print(f"[{s['severity']}] {s['type']}: {s.get('description', '')}")

    print("\n=== 变更影响半径 (api_login) ===")
    impact = ckg.compute_impact_radius(["api_login"], depth=2)
    print(f"直接影响: {impact['direct']}")
    print(f"间接影响: {impact['indirect']}")
