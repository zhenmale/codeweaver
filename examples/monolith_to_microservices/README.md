# Monolith to Microservices Migration Example

## 场景描述

某 SaaS 平台使用 Django 单体架构，120万行代码，需要拆分为 8 个微服务。

## 迁移策略

1. **依赖分析**：使用 CodeWeaver 知识图谱分析模块间依赖
2. **服务识别**：Louvain 社区发现识别高内聚模块
3. **接口提取**：识别服务间 API 边界
4. **渐进迁移**：Strangler Fig 模式逐步剥离

## Token 消耗参考

| 阶段 | Token 消耗 | 说明 |
|------|-----------|------|
| 依赖图构建 | ~500万 | 120万行代码全量分析 |
| 服务边界规划 | ~200万 | 5-Agent 联邦共识 |
| 代码重构 | ~1.5亿 | 300+ 函数重构 |
| 验证测试 | ~5000万 | Oracle Agent 四级验证 |
| **总计** | **~2.3亿** | 单次完整迁移 |

## 运行示例

```bash
codeweaver migrate start \
  --source ./monolith \
  --strategy monolith-to-microservices \
  --services 8 \
  --mode gradual
```
