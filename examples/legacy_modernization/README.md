# Legacy Modernization Example

## 场景描述

遗留 COBOL/PL-SQL 系统现代化为 Python 微服务架构。

## 迁移策略

1. **语义理解**：Neural Embedder 理解遗留代码业务逻辑
2. **业务规则提取**：符号推理引擎提取 Horn 子句规则
3. **代码生成**：Synthesis Agent 生成现代等价实现
4. **等价验证**：Oracle Agent 形式化验证功能等价性

## Token 消耗参考

| 阶段 | Token 消耗 | 说明 |
|------|-----------|------|
| 语义分析 | ~2000万 | 理解遗留代码逻辑 |
| 规则提取 | ~500万 | 业务规则形式化 |
| 代码生成 | ~5000万 | 生成 Python 实现 |
| 等价验证 | ~3000万 | 形式化验证 |
| **总计** | **~1.05亿** | 单模块现代化 |

## 运行示例

```bash
codeweaver modernize start \
  --source ./cobol-system \
  --target-language python \
  --strategy legacy-modernization \
  --verification strict
```
