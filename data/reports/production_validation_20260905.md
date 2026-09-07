# ComProScanner 修复与验证记录（2026-09-05）

目标流程保持不变：多来源 PDF/XML → 统一 Article → 五个可选 Evidence 工具 → 每条 Evidence 独立进入旧抽取、材料恢复、清洗 → JSON → review / Gold 评估。没有恢复 30 篇付费抽取，没有开展目录净化。

## 验收结论

**已通过本地链路、异常边界、安装产物验证；尚不应宣称生产完全无错误。**

- 最终测试：750 passed，17 deselected。日志：`tmp/production_tests_final.log`。
- 实际解析常跑集合中的第 1 篇 PDF（本地、无元数据联网），生成 1 篇统一 Article 和 25 条 Evidence；失败数 0。再次 resume 成功复用，未重新解析。产物：`outputs/runs/production_single_pdf_20260905/`。
- 真实加载缓存的 PhysBERT，实际执行 Chroma 索引/检索。规则、RAG、表格、图片说明、公式五个 provider 均参与，得到 4 条 Evidence；规则/RAG 命中同一块，因此合为一条并保留检索方法。产物：`outputs/runs/production_local_tools_20260905/`。
- 真实 CrewAI Flow、GraphExtractorTool、EquationTool、MaterialParserTool、DataCleaner、JSON、Excel 和评分器贯通。**仅 Crew 决策及远程 HTTP/模型响应使用测试夹具**。4 条 Evidence 分别执行 identifier/extractor/formatter，共 12 次 Crew 调用；resume 没有重复调用。原始预测/review 保留 4 条，评估视图去重为 1 条，夹具 TP=1/FP=0/FN=0。这不是 30 篇准确率或真实模型质量测量。产物：`outputs/runs/production_fixture_end_to_end_20260905/`。
- 普通 wheel 构建并安装到工作区独立目录，确认实际导入安装产物而非 src；14 个 YAML 配置全部存在，真实 Crew 的无工具/公式/图片/两者四种组合均可构造。日志：`tmp/production_wheel_runtime_final.log`。
- 禁用 CrewAI、pymatgen、RAG、MySQL 相关导入后，PDF 入口仍可导入，关闭 RAG 的数据库管理器正常初始化。日志：`tmp/production_optional_dependencies.log`。这是一项依赖隔离检查，并非从空机器下载所有 extras 的安装验证。
- 出版社解析器由现有离线 XML/响应夹具测试覆盖，新增 Elsevier/Springer/Wiley 连接连续失败三次即退出的检查；本轮没有向真实出版社下载文章。

## 对原审查 17 项的处理

| 项目 | 本轮处理 | 状态 |
|---|---|---|
| 1 Gold 标识/属性不一致 | evaluate 自动读取同目录 paper_id_map.json，按 preset 对齐属性，报告未映射 Gold 标识；数值格式 1103 与 1103.0 一致 | 已修复接口 |
| 2 逐 Evidence 重复计分 | 原始预测不合并，独立评估视图按文章、材料、值、单位、限定词、conditions 去重；报告原始/重复条数 | 已修复 |
| 3 prepare 缓存过期/吞错误 | 按 Article、provider、切块、查询、preset、图片清单内容计算签名；只恢复成功且匹配的缓存；错误和部分成功重试 | 已修复 |
| 4 review/metrics 过期 | 下游输入签名校验；review 原子更新，匹配事实保留 decision/note，完整旧表备份包括已移除行 | 已修复 |
| 5 工具故障隔离 | 只读取启用工具所需数据；表/图/公式及 PhysBERT 故障分别报告，保留成功 Evidence，部分成功返回非零 | 已修复主链 |
| 6 旧结构科学语义限制 | 保存 identifier/extractor/formatter 原始响应，输出 review_required 与 representation_limits，review 明确要求核查多值、条件、限定词、混合单位 | **已降低静默丢失风险，结构限制未消除** |
| 7 无界等待 | 材料 API 连接/读取超时，图像/公式模型请求设置超时；PDF/元数据/三家出版社重试上限三次 | 已修复所审主链请求；旧 MySQL 非默认路径未做完整生产验证 |
| 8 非法输出正常缓存 | canonical Flow 严格校验 JSON/identifier；记录工具错误；工具出错或选定图/公式工具未调用时失败；保留原始响应供重试/审核 | 已修复主要异常路径 |
| 9 切块超长/零重叠 | 单句和多句均限制 max_words，零重叠不再重复上一句 | 已修复 |
| 10 缺少文章 ID/重复来源丢失 | 无 DOI/paper_id 时使用内容哈希；同 ID 选择正文最长版本并补缺字段，在 metadata 保存来源变体 | 已修复所复现问题 |
| 11 组分分数精度 | 不再强制两位小数，分数转换使用 15 位有效数字；修正旧测试中错误组分预期 | 已修复提前截断；后续算术仍采用旧清洗器精度策略 |
| 12 wheel 缺 YAML | setuptools 显式打包 YAML，验证安装后的真实 Crew 可读取 | 已修复并验证 |
| 13 自定义 provider 注册却不运行 | 无源单元适配器时显式报错；现有五个 provider 可选 | 已消除静默跳过；尚未引入通用自定义 provider 执行接口 |
| 14 reported 名称来源误导 | 保存格式化前原始响应，JSON 声明 legacy_cleaned_output，review 加材料名称来源提示 | 已明确来源，未伪造原文名称 |
| 15 可选依赖强耦合 | ComProScanner 的 Flow/清洗/评估模型按需导入；共享数据库模块的 RAG 部分按需导入；MySQL 可选；补直接依赖与 legacy 清洗依赖 | 已修复已发现的导入耦合 |
| 16 preset 静默忽略 | 未支持配置显式报错；CLI 模型缺省从 preset 读取；可配置抽取模型/凭据/base URL；显式启用 synthesis 时只使用当前 Evidence | 已明确 canonical 配置边界 |
| 17 消耗不透明 | 保存 Crew 返回的 token usage、工具子调用 usage/错误、缓存复用状态；未知费用为 null | **已有实际诊断字段，仍非供应商账单/完整计费审计** |

另修复：显式材料化学式优先于其他样品上下文；Fact 合并键包含 conditions；图表不再强制整数；源 PDF 内容签名隔离解析工作区；图片字节变化使抽取缓存失效；安全缓存文件名增加哈希避免部分路径碰撞；重新建立 Chroma 索引时删除过期 chunk；解析输出数量/请求 DOI 缺失会生成 process_failures，不再只看 CSV 是否存在。

## 仍需满足的生产验收条件

1. 真实模型的逐 Evidence 抽取、VLM 读图、公式工具、材料恢复服务仍需要小规模在线验收；本轮付费模型调用为 0。
2. Elsevier/Springer/IOP/Wiley 的真实下载授权、网络服务及不同版式仍需实际样本验收，不能用离线测试替代。
3. 旧 material→单值、共享单位结构仍不支持自动无损表达同材料多条件、多值。当前结果需按 review 提示核查，不应作为已实现完整科学语义的承诺。
4. 17 项 integration 测试未执行；SQL/知识图谱等旧兼容功能不在本轮主链实测证明范围内。
5. 全项目净化继续推迟到上述真实生产验证完成以后。

## 可复现命令

在现有 comproscanner Conda 环境中运行：

```powershell
python -m pytest -q
python tests/test_pipeline/legacy_runtime_smoke.py
python tests/test_pipeline/production_runtime_smoke.py
```

production_runtime_smoke 需要已有 `production_local_tools_20260905` Evidence 夹具，本次已生成。它明确替换远程响应，不能用其 100% 夹具分数作为模型性能报告。

`.env` 密钥未写入报告，原始 Gold 未修改，已有工作区改动保留，未进行自动提交或目录删除。
