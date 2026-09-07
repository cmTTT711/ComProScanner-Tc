# 变更记录

## 2026-09-06：正式流程净化

- 按文献、Evidence、抽取、结果四个模块重新组织代码与测试。
- 隔离旧 CrewAI、MySQL、Neo4j、图谱及实验代码。
- 属性模型、角色消息、字段和工具规则集中到 presets。
- 保留 Tc 抽取消息与材料恢复结果，增加可回放验收。
- 保存完整解析资产，统一结果表、Review、Gold 导入和严格评估入口。
- 历史数据迁入 data，保留内容及读取旧路径的映射。

原变更记录位于 `reference/documentation_before_cleanup.zip`。
