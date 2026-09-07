# 开发约定

- 正式代码只放在 `src/comproscanner/`，按 documents、evidence、extraction、results 分工。
- 属性策略只放在 presets；不复制一套新主流程来增加属性。
- 不从 reference 导入代码，也不把数据库、图谱或 CrewAI 重新作为默认依赖。
- 原始文献、Gold 和已有预测不覆盖。新实验使用新的 run-id。
- 纯重构必须通过冻结 Tc 消息、材料恢复和端到端离线回归。
- 科学策略变更与项目整理分开，报告匹配口径，不能用温度覆盖冒充完整事实准确率。

```bash
pip install -e ".[all,test]"
pytest -q
```

默认测试阻断网络连接。需要真实服务的测试使用 integration 标记，并在实际运行前明确数据范围和调用预算。
