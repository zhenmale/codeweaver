# Contributing to CodeWeaver

感谢您对 CodeWeaver 项目的关注！我们欢迎各种形式的贡献。

## 开发环境

```bash
# 克隆仓库
git clone https://github.com/zhenmale/codeweaver.git
cd codeweaver

# 安装开发依赖
pip install -e ".[dev]"

# 安装 pre-commit hooks
pre-commit install
```

## 代码规范

- 使用 Black 格式化代码（行宽 100）
- 使用 Ruff 进行 lint 检查
- 使用 mypy 进行类型检查
- 所有新功能必须附带测试

## 提交规范

使用 Conventional Commits 格式：

```
feat(scope): add new feature
fix(scope): fix bug
docs(scope): update documentation
test(scope): add tests
refactor(scope): refactor code
```

scope 可选值：cognitive, federation, perception, action, metacognition, platform, observability

## Pull Request 流程

1. Fork 项目
2. 创建特性分支 (`git checkout -b feat/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到远程 (`git push origin feat/amazing-feature`)
5. 创建 Pull Request

## 报告问题

使用 GitHub Issues 报告 bug 或提出功能建议。请包含：
- 问题描述
- 复现步骤
- 期望行为
- 实际行为
- 环境信息（Python 版本、操作系统等）

## 行为准则

- 尊重所有参与者
- 接受建设性批评
- 专注于对社区最有利的事情
- 对他人表示同理心
