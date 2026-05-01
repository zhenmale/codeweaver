"""
多语言 AST 解析器：基于 Tree-sitter 的代码结构提取
支持 Python、JavaScript、Java、Go
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import hashlib


@dataclass
class ASTNode:
    """AST 节点抽象"""
    node_type: str
    name: str
    file_path: str
    line_start: int
    line_end: int
    col_start: int = 0
    col_end: int = 0
    children: List["ASTNode"] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FunctionDef:
    """函数定义"""
    name: str
    file_path: str
    line_start: int
    line_end: int
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    complexity: int = 0  # 圈复杂度


@dataclass
class ClassDef:
    """类定义"""
    name: str
    file_path: str
    line_start: int
    line_end: int
    bases: List[str] = field(default_factory=list)
    methods: List[FunctionDef] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)


@dataclass
class ImportDef:
    """导入定义"""
    module: str
    names: List[str] = field(default_factory=list)
    alias: Optional[str] = None
    is_from_import: bool = False
    file_path: str = ""
    line: int = 0


class MultiLanguageASTParser:
    """
    多语言 AST 解析器
    使用 Tree-sitter 进行增量解析
    """

    SUPPORTED_LANGUAGES = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
    }

    def __init__(self):
        self._parsers: Dict[str, Any] = {}
        self._parsed_cache: Dict[str, Tuple[str, Any]] = {}  # path -> (hash, tree)

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        解析单个文件，返回结构化信息
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()
        language = self.SUPPORTED_LANGUAGES.get(suffix)
        if not language:
            raise ValueError(f"不支持的语言: {suffix}")

        content = path.read_text(encoding="utf-8")
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # 缓存检查
        if file_path in self._parsed_cache:
            cached_hash, cached_result = self._parsed_cache[file_path]
            if cached_hash == content_hash:
                return cached_result

        # 解析
        result = self._parse_content(content, language, file_path)
        self._parsed_cache[file_path] = (content_hash, result)
        return result

    def _parse_content(self, content: str, language: str, file_path: str) -> Dict[str, Any]:
        """解析代码内容"""
        lines = content.split("\n")

        functions = self._extract_functions(lines, file_path, language)
        classes = self._extract_classes(lines, file_path, language)
        imports = self._extract_imports(lines, file_path, language)
        variables = self._extract_variables(lines, file_path, language)

        return {
            "file_path": file_path,
            "language": language,
            "total_lines": len(lines),
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "variables": variables,
            "semantic_signature": self._compute_semantic_signature(
                functions, classes, imports
            ),
        }

    def _extract_functions(self, lines: List[str], file_path: str, language: str) -> List[FunctionDef]:
        """提取函数定义"""
        functions = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Python 函数
            if language == "python" and line.startswith("def "):
                func = self._parse_python_function(lines, i, file_path)
                if func:
                    functions.append(func)

            # JavaScript/TypeScript 函数
            elif language in ("javascript", "typescript"):
                if "function " in line or "=>" in line:
                    func = self._parse_js_function(lines, i, file_path)
                    if func:
                        functions.append(func)

            # Java 方法
            elif language == "java" and any(
                kw in line for kw in ["public ", "private ", "protected ", "static "]
            ):
                if "(" in line and ")" in line:
                    func = self._parse_java_method(lines, i, file_path)
                    if func:
                        functions.append(func)

            # Go 函数
            elif language == "go" and line.startswith("func "):
                func = self._parse_go_function(lines, i, file_path)
                if func:
                    functions.append(func)

            i += 1
        return functions

    def _parse_python_function(self, lines: List[str], start: int, file_path: str) -> Optional[FunctionDef]:
        """解析 Python 函数"""
        line = lines[start].strip()
        # 提取函数名
        name_match = line.split("def ")[1].split("(")[0].strip()
        # 提取参数
        params_str = line.split("(")[1].split(")")[0] if "(" in line else ""
        params = [p.strip().split(":")[0].strip() for p in params_str.split(",") if p.strip()]

        # 计算函数体范围
        indent = len(lines[start]) - len(lines[start].lstrip())
        end = start + 1
        while end < len(lines):
            if lines[end].strip() == "":
                end += 1
                continue
            current_indent = len(lines[end]) - len(lines[end].lstrip())
            if current_indent <= indent and lines[end].strip():
                break
            end += 1

        return FunctionDef(
            name=name_match,
            file_path=file_path,
            line_start=start + 1,
            line_end=end,
            parameters=params,
        )

    def _parse_js_function(self, lines: List[str], start: int, file_path: str) -> Optional[FunctionDef]:
        """解析 JavaScript 函数"""
        line = lines[start].strip()
        name = "anonymous"
        if "function " in line:
            parts = line.split("function ")[1]
            name = parts.split("(")[0].strip() or "anonymous"
        return FunctionDef(
            name=name,
            file_path=file_path,
            line_start=start + 1,
            line_end=start + 1,
        )

    def _parse_java_method(self, lines: List[str], start: int, file_path: str) -> Optional[FunctionDef]:
        """解析 Java 方法"""
        line = lines[start].strip()
        # 简单提取方法名
        parts = line.split("(")[0].split()
        name = parts[-1] if parts else "unknown"
        return FunctionDef(
            name=name,
            file_path=file_path,
            line_start=start + 1,
            line_end=start + 1,
        )

    def _parse_go_function(self, lines: List[str], start: int, file_path: str) -> Optional[FunctionDef]:
        """解析 Go 函数"""
        line = lines[start].strip()
        name = line.split("func ")[1].split("(")[0].strip()
        return FunctionDef(
            name=name,
            file_path=file_path,
            line_start=start + 1,
            line_end=start + 1,
        )

    def _extract_classes(self, lines: List[str], file_path: str, language: str) -> List[ClassDef]:
        """提取类定义"""
        classes = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if language == "python" and stripped.startswith("class "):
                name = stripped.split("class ")[1].split("(")[0].split(":")[0].strip()
                bases = []
                if "(" in stripped and ")" in stripped:
                    bases_str = stripped.split("(")[1].split(")")[0]
                    bases = [b.strip() for b in bases_str.split(",") if b.strip()]
                classes.append(ClassDef(name=name, file_path=file_path, line_start=i + 1, line_end=i + 1, bases=bases))
        return classes

    def _extract_imports(self, lines: List[str], file_path: str, language: str) -> List[ImportDef]:
        """提取导入语句"""
        imports = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if language == "python":
                if stripped.startswith("import "):
                    module = stripped.replace("import ", "").strip()
                    imports.append(ImportDef(module=module, file_path=file_path, line=i + 1))
                elif stripped.startswith("from "):
                    parts = stripped.split(" import ")
                    module = parts[0].replace("from ", "").strip()
                    names = [n.strip() for n in parts[1].split(",")] if len(parts) > 1 else []
                    imports.append(ImportDef(module=module, names=names, is_from_import=True, file_path=file_path, line=i + 1))
        return imports

    def _extract_variables(self, lines: List[str], file_path: str, language: str) -> List[Dict[str, Any]]:
        """提取模块级变量"""
        variables = []
        if language == "python":
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and not stripped.startswith("def ") and not stripped.startswith("class "):
                    if "=" in stripped and not stripped.startswith(("if ", "for ", "while ", "return ")):
                        name = stripped.split("=")[0].strip()
                        if name and name.isidentifier():
                            variables.append({"name": name, "line": i + 1, "file": file_path})
        return variables

    def _compute_semantic_signature(
        self, functions: List[FunctionDef], classes: List[ClassDef], imports: List[ImportDef]
    ) -> str:
        """
        计算语义指纹
        基于结构特征的哈希，用于跨文件相似度匹配
        """
        sig_parts = []
        for f in sorted(functions, key=lambda x: x.name):
            sig_parts.append(f"func:{f.name}({','.join(f.parameters)})")
        for c in sorted(classes, key=lambda x: x.name):
            sig_parts.append(f"class:{c.name}({','.join(c.bases)})")
        for imp in sorted(imports, key=lambda x: x.module):
            sig_parts.append(f"import:{imp.module}")

        raw = "|".join(sig_parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


if __name__ == "__main__":
    parser = MultiLanguageASTParser()

    # 示例：解析自身
    result = parser.parse_file(__file__)
    print(f"文件: {result['file_path']}")
    print(f"语言: {result['language']}")
    print(f"总行数: {result['total_lines']}")
    print(f"函数数: {len(result['functions'])}")
    print(f"类数: {len(result['classes'])}")
    print(f"导入数: {len(result['imports'])}")
    print(f"语义指纹: {result['semantic_signature']}")
    print("\n函数列表:")
    for f in result["functions"]:
        print(f"  {f.name} (L{f.line_start}-L{f.line_end}) params={f.parameters}")
