"""
数据流追踪器：污点分析 + 数据依赖追踪
追踪敏感数据在代码中的传播路径
"""
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx


class TaintLevel(Enum):
    CLEAN = "clean"  # 无污点
    TAINTED = "tainted"  # 来自外部输入
    SANITIZED = "sanitized"  # 已清洗
    SENSITIVE = "sensitive"  # 敏感数据（密码、密钥等）


@dataclass
class DataNode:
    """数据节点"""
    name: str
    file_path: str
    line: int
    taint_level: TaintLevel = TaintLevel.CLEAN
    data_type: str = "unknown"
    source: str = ""  # 数据来源描述


@dataclass
class DataFlowEdge:
    """数据流边"""
    source: str  # 源变量
    target: str  # 目标变量
    operation: str  # 操作类型：assign, pass, return, call
    file_path: str
    line: int
    transforms: List[str] = field(default_factory=list)  # 经过的转换


class DataFlowTracker:
    """
    数据流追踪器
    功能：
    1. 污点分析：追踪外部输入到敏感操作的传播
    2. 数据依赖图：构建变量级依赖关系
    3. 敏感数据检测：识别密码、密钥等硬编码
    """

    # 外部输入源
    TAINT_SOURCES = {
        "input", "sys.argv", "request.form", "request.args",
        "request.json", "request.data", "os.environ",
        "open", "urllib", "requests.get", "requests.post",
    }

    # 敏感操作（污点汇聚点）
    SINKS = {
        "execute", "cursor.execute", "os.system", "subprocess",
        "eval", "exec", "render_template_string", "send_file",
        "pickle.loads", "yaml.load", "open(..., 'w')",
    }

    # 清洗函数
    SANITIZERS = {
        "escape", "sanitize", "validate", "bleach.clean",
        "html.escape", "markupsafe.escape", "int", "float",
    }

    # 敏感数据模式
    SENSITIVE_PATTERNS = {
        "password", "passwd", "pwd", "secret", "token",
        "api_key", "apikey", "private_key", "credential",
        "auth", "session_key", "encryption_key",
    }

    def __init__(self):
        self.data_graph = nx.DiGraph()
        self.data_nodes: Dict[str, DataNode] = {}
        self.taint_flows: List[Dict[str, Any]] = []
        self.vulnerabilities: List[Dict[str, Any]] = []

    def analyze_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """分析单个文件的数据流"""
        lines = content.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            self._analyze_line(stripped, file_path, i + 1)

        return {
            "file_path": file_path,
            "data_nodes": len(self.data_nodes),
            "taint_flows": len(self.taint_flows),
            "vulnerabilities": self.vulnerabilities,
        }

    def _analyze_line(self, line: str, file_path: str, line_num: int):
        """分析单行代码"""
        # 检测敏感数据硬编码
        self._detect_hardcoded_secrets(line, file_path, line_num)

        # 检测赋值操作
        if "=" in line and not line.startswith(("if ", "for ", "while ", "class ", "def ")):
            self._analyze_assignment(line, file_path, line_num)

        # 检测函数调用中的数据流
        if "(" in line and ")" in line:
            self._analyze_function_call(line, file_path, line_num)

    def _detect_hardcoded_secrets(self, line: str, file_path: str, line_num: int):
        """检测硬编码敏感数据"""
        lower_line = line.lower()
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in lower_line and "=" in line:
                # 检查是否赋值了字符串字面量
                parts = line.split("=", 1)
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    value = parts[1].strip()
                    if (value.startswith('"') or value.startswith("'")) and len(value) > 3:
                        self.vulnerabilities.append({
                            "type": "hardcoded_secret",
                            "severity": "critical",
                            "file": file_path,
                            "line": line_num,
                            "variable": var_name,
                            "description": f"疑似硬编码敏感数据: {var_name}",
                        })

    def _analyze_assignment(self, line: str, file_path: str, line_num: int):
        """分析赋值语句"""
        parts = line.split("=", 1)
        if len(parts) != 2:
            return

        target = parts[0].strip()
        source_expr = parts[1].strip()

        # 检查源是否是污点源
        taint_level = TaintLevel.CLEAN
        for source in self.TAINT_SOURCES:
            if source in source_expr:
                taint_level = TaintLevel.TAINTED
                break

        # 检查是否经过清洗
        for sanitizer in self.SANITIZERS:
            if sanitizer in source_expr:
                taint_level = TaintLevel.SANITIZED
                break

        node_id = f"{file_path}:{target}:{line_num}"
        self.data_nodes[node_id] = DataNode(
            name=target,
            file_path=file_path,
            line=line_num,
            taint_level=taint_level,
        )
        self.data_graph.add_node(node_id, taint=taint_level.value, var=target)

        # 如果源变量也存在，添加数据流边
        source_var = source_expr.split("(")[0].split(".")[0].strip()
        source_candidates = [
            nid for nid, n in self.data_nodes.items()
            if n.name == source_var and n.file_path == file_path
        ]
        if source_candidates:
            latest_source = source_candidates[-1]
            self.data_graph.add_edge(latest_source, node_id, operation="assign")
            self.data_nodes[node_id].taint_level = max(
                self.data_nodes[node_id].taint_level,
                self.data_nodes[latest_source].taint_level,
                key=lambda x: list(TaintLevel).index(x),
            )

    def _analyze_function_call(self, line: str, file_path: str, line_num: int):
        """分析函数调用中的数据流"""
        # 检查是否是敏感汇聚点
        for sink in self.SINKS:
            if sink in line:
                # 检查参数是否来自污点源
                for node_id, node in self.data_nodes.items():
                    if (node.taint_level == TaintLevel.TAINTED
                            and node.name in line
                            and node.file_path == file_path):
                        self.taint_flows.append({
                            "source": node_id,
                            "sink": sink,
                            "file": file_path,
                            "line": line_num,
                            "description": f"污点数据 {node.name} 流入 {sink}",
                        })
                        self.vulnerabilities.append({
                            "type": "taint_injection",
                            "severity": "critical",
                            "file": file_path,
                            "line": line_num,
                            "variable": node.name,
                            "sink": sink,
                            "description": f"污点数据 {node.name} 未经清洗直接传入 {sink}",
                        })

    def trace_taint_path(self, start_var: str) -> List[List[str]]:
        """追踪污点传播路径"""
        tainted_nodes = [
            nid for nid, n in self.data_nodes.items()
            if n.name == start_var and n.taint_level in (TaintLevel.TAINTED, TaintLevel.SENSITIVE)
        ]

        all_paths = []
        for start in tainted_nodes:
            for target in self.data_graph.nodes():
                if self.data_graph.nodes[target].get("taint") in ("tainted", "sensitive"):
                    try:
                        paths = list(nx.all_simple_paths(self.data_graph, start, target, cutoff=10))
                        all_paths.extend(paths)
                    except nx.NetworkXNoPath:
                        continue

        return all_paths

    def get_data_dependency_graph(self) -> nx.DiGraph:
        """获取数据依赖图"""
        return self.data_graph


if __name__ == "__main__":
    tracker = DataFlowTracker()

    sample_code = '''
username = request.args.get("username")
password = request.args.get("password")
query = "SELECT * FROM users WHERE name='" + username + "'"
cursor.execute(query)
api_key = "sk-1234567890abcdef"
token = hashlib.sha256(password.encode()).hexdigest()
'''.strip()

    result = tracker.analyze_file(sample_code, "app.py")
    print(f"数据节点: {result['data_nodes']}")
    print(f"污点流: {result['taint_flows']}")
    print(f"漏洞数: {len(result['vulnerabilities'])}")
    for v in result["vulnerabilities"]:
        print(f"  [{v['severity']}] {v['type']}: {v['description']}")
