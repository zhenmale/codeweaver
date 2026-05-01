# Framework Migration Example

## 场景描述

金融科技公司 80万行 Java Spring 4.x 代码迁移到 Spring Boot 3.x + 云原生架构。

## 迁移策略

1. **API 兼容性分析**：映射旧 API 到新框架等价物
2. **依赖升级**：逐模块升级依赖版本
3. **配置迁移**：XML -> YAML/注解配置
4. **云原生改造**：添加健康检查、指标暴露、容器化

## Token 消耗参考

| 阶段 | Token 消耗 | 说明 |
|------|-----------|------|
| 代码分析 | ~300万 | API 映射和依赖分析 |
| 重构执行 | ~8亿 | 持续 3 个月 |
| 验证回归 | ~2亿 | 接口兼容性验证 |
| **总计** | **~10亿/月** | 月均消耗 |

## 运行示例

```bash
codeweaver migrate start \
  --source ./spring-app \
  --target-framework spring-boot-3 \
  --strategy framework-migration \
  --compatibility-check strict
```
