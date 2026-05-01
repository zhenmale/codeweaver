"""
控制流分析器：构建函数级控制流图
支持分支、循环、异常处理的结构化表示
"""
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx


class CFGNodeType(Enum):
    ENTRY = "entry"
    EXIT = "exit"
    BASIC_BLOCK = "basic_block"
    CONDITION = "condition"
    LOOP_HEADER = "loop_header"
    EXCEPTION = "exception"


@dataclass
class CFGNode:
    id: str
    type: CFGNodeType
    line_start: int
    line_end: int
    statements: List[str] = field(default_factory=list)


@dataclass
class CFGEdge:
    source: str
    target: str
    label: str = ""  # true/false/exception/loop_body/loop_exit
    probability: float = 0.5  # 分支概率估计


class ControlFlowGraph:
    """控制流图"""

    def __init__(self, function_name: str, file_path: str):
        self.function_name = function_name
        self.file_path = file_path
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, CFGNode] = {}
        self.entry_node: Optional[str] = None
        self.exit_nodes: List[str] = []

    def add_node(self, node: CFGNode) -> None:
        self.graph.add_node(node.id, type=node.type.value, lines=(node.line_start, node.line_end))
        self.nodes[node.id] = node
        if node.type == CFGNodeType.ENTRY:
            self.entry_node = node.id
        elif node.type == CFGNodeType.EXIT:
            self.exit_nodes.append(node.id)

    def add_edge(self, edge: CFGEdge) -> None:
        self.graph.add_edge(edge.source, target=edge.target, label=edge.label, probability=edge.probability)

    def compute_cyclomatic_complexity(self) -> int:
        """计算圈复杂度 V(G) = E - N + 2P"""
        e = self.graph.number_of_edges()
        n = self.graph.number_of_nodes()
        return e - n + 2

    def find_all_paths(self) -> List[List[str]]:
        """找到所有从入口到出口的路径"""
        if not self.entry_node or not self.exit_nodes:
            return []
        all_paths = []
        for exit_node in self.exit_nodes:
            try:
                paths = list(nx.all_simple_paths(self.graph, self.entry_node, exit_node, cutoff=50))
                all_paths.extend(paths)
            except nx.NetworkXNoPath:
                continue
        return all_paths

    def detect_unreachable_code(self) -> List[str]:
        """检测不可达代码"""
        if not self.entry_node:
            return []
        reachable = nx.descendants(self.graph, self.entry_node)
        reachable.add(self.entry_node)
        unreachable = set(self.nodes.keys()) - reachable
        return list(unreachable)

    def get_dominators(self) -> Dict[str, Set[str]]:
        """计算支配节点"""
        if not self.entry_node:
            return {}
        return nx.immediate_dominators(self.graph, self.entry_node)


class ControlFlowAnalyzer:
    """控制流分析器"""

    def analyze_function(self, lines: List[str], function_name: str, file_path: str, start_line: int = 0) -> ControlFlowGraph:
        """分析单个函数的控制流"""
        cfg = ControlFlowGraph(function_name, file_path)

        # 创建入口和出口节点
        entry = CFGNode(f"{function_name}_entry", CFGNodeType.ENTRY, start_line, start_line)
        exit_node = CFGNode(f"{function_name}_exit", CFGNodeType.EXIT, start_line + len(lines), start_line + len(lines))
        cfg.add_node(entry)
        cfg.add_node(exit_node)

        # 简化的控制流分析：识别分支和循环
        block_id = 0
        current_block_start = 0
        prev_node_id = entry.id

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 检测分支
            if stripped.startswith(("if ", "elif ", "else:")):
                # 结束当前基本块
                if i > current_block_start:
                    block_id += 1
                    block = CFGNode(
                        f"{function_name}_bb{block_id}",
                        CFGNodeType.BASIC_BLOCK,
                        start_line + current_block_start,
                        start_line + i - 1,
                        lines[current_block_start:i],
                    )
                    cfg.add_node(block)
                    cfg.add_edge(CFGEdge(prev_node_id, block.id))
                    prev_node_id = block.id

                # 创建条件节点
                block_id += 1
                cond_node = CFGNode(
                    f"{function_name}_cond{block_id}",
                    CFGNodeType.CONDITION,
                    start_line + i,
                    start_line + i,
                    [stripped],
                )
                cfg.add_node(cond_node)
                cfg.add_edge(CFGEdge(prev_node_id, cond_node.id))
                prev_node_id = cond_node.id
                current_block_start = i + 1

            # 检测循环
            elif stripped.startswith(("for ", "while ")):
                if i > current_block_start:
                    block_id += 1
                    block = CFGNode(
                        f"{function_name}_bb{block_id}",
                        CFGNodeType.BASIC_BLOCK,
                        start_line + current_block_start,
                        start_line + i - 1,
                        lines[current_block_start:i],
                    )
                    cfg.add_node(block)
                    cfg.add_edge(CFGEdge(prev_node_id, block.id))
                    prev_node_id = block.id

                block_id += 1
                loop_node = CFGNode(
                    f"{function_name}_loop{block_id}",
                    CFGNodeType.LOOP_HEADER,
                    start_line + i,
                    start_line + i,
                    [stripped],
                )
                cfg.add_node(loop_node)
                cfg.add_edge(CFGEdge(prev_node_id, loop_node.id, label="loop_body"))
                prev_node_id = loop_node.id
                current_block_start = i + 1

        # 最后的基本块
        if current_block_start < len(lines):
            block_id += 1
            block = CFGNode(
                f"{function_name}_bb{block_id}",
                CFGNodeType.BASIC_BLOCK,
                start_line + current_block_start,
                start_line + len(lines) - 1,
                lines[current_block_start:],
            )
            cfg.add_node(block)
            cfg.add_edge(CFGEdge(prev_node_id, block.id))
            cfg.add_edge(CFGEdge(block.id, exit_node.id))
        else:
            cfg.add_edge(CFGEdge(prev_node_id, exit_node.id))

        return cfg


if __name__ == "__main__":
    analyzer = ControlFlowAnalyzer()

    sample_code = [
        "def process_data(items):",
        "    result = []",
        "    for item in items:",
        "        if item > 0:",
        "            result.append(item * 2)",
        "        else:",
        "            result.append(0)",
        "    return result",
    ]

    cfg = analyzer.analyze_function(sample_code, "process_data", "example.py")
    print(f"函数: {cfg.function_name}")
    print(f"节点数: {cfg.graph.number_of_nodes()}")
    print(f"边数: {cfg.graph.number_of_edges()}")
    print(f"圈复杂度: {cfg.compute_cyclomatic_complexity()}")
    print(f"不可达节点: {cfg.detect_unreachable_code()}")
