# 2026-11-18（周三）· 端侧流式生成的 Compose 增量呈现

## 0 速览（30 秒读完）
- **今日主题**：Android × AI 第 3 讲，续 11-01 Streaming；将 ML Kit Prompt API 的**正文增量**归并成可取消、可隔离草稿的 Compose 状态。
- **学完你能做到**：先确认 Android 官方流式契约，再把新增文本、最终结束原因、取消/超时转换为 ViewModel 的不可变快照，让 Compose 只呈现当前请求。
- **预计时长**：2 小时＝速览 0.5 + 概念 30 + 代码 40 + 动手 20 + 动态 20 + 收尾 8 + 缓冲 1.5＝120 分钟。
- **进度依据〔ARTIFACT〕**：完整台账（20 讲）、规则备份 `00_进度/智能体规则.md`、11-17 全文及明日预告、11-01 全文均实读。保持 `02_AndroidAI`，不重讲 SSE/HTTP 解析、不重开设备门禁或非流式调用。今天周三，无周总结。台账勾选表示材料产出，学习复述仍待填。
- **验证边界〔TOOL〕**：Python **3.9.6** 零依赖固定 fixture 在 `/tmp` 实跑，17 个测试方法通过；Kotlin/Compose 为 **SPEC_CHECK，NOT_EXECUTED**。未编译 Android、运行 Compose、连接/操作手机、下载模型、安装依赖、改真实工程、读取凭据或调用云模型；不提供虚构 Token usage、推理输出或性能数字。

## 1 概念精讲（30 min）
- **一句话定义**：Compose 增量呈现不是把 SDK 流直接交给 UI，而是先把每个正文增量归并成**属于当前请求的完整 UI 快照**，再按生命周期订阅它。
- **它解决什么问题 / 为什么现在必须懂**：昨日的一次完整响应只需校验终点；流式中间态会不断进入界面，错误拼接、丢片、旧请求迟到或退出页面后仍生成，都可能把“半成品”冒充已完成结果。

### 1.1 从官方契约开始，而不是照搬云端 SSE
当天已实读以下签名与语义〔S01/S02/S04/S05〕：
```kotlin
// 官方签名摘录；不是本课伪造的SDK接口。
fun generateContentStream(request: GenerateContentRequest): Flow<GenerateContentResponse>
suspend fun generateContent(
    request: GenerateContentRequest,
    streamingCallback: StreamingCallback
): GenerateContentResponse
interface StreamingCallback {
    fun onNewText(additionalText: String)
    fun onNewThought(additionalThought: String)
}
```
- **Flow 路线（今天采用）**：每次响应只有一个候选；`candidateCount > 1` 抛 `IllegalArgumentException`，所以显式设为 1。中间候选 `finishReason == null`；最后一帧 `finishReason` 非空，例如 `STOP` / `MAX_TOKENS`。收集协程可取消，异常可能中断流。
- **新增，不是累计**：参考页只说 partial/incremental，本身不足以猜 `text` 是全量还是增量；**接入指南的实际示例明确 `fullResponse += newChunkReceived`**，这才是本课追加语义的直接证据。最终帧也先追加其中的文本，再记录结束原因；不能见标记就丢掉最后一个字。
- **Callback 路线（只核对，不接入）**：`onNewText(additionalText)` 给新增正文；挂起函数返回**完整最终响应**。若以后采用它，最终完整正文应覆盖/校准预览，不能再追加一次。完成/失败来自挂起函数返回/异常，接口**没有** `onComplete/onError`。本课不实现 Callback 适配，不订阅、保存或呈现思考过程。
- **不要把本 SDK 的契约推广到所有 SDK**：若另一个适配器明确返回累计快照 `你 → 你好`，就覆盖而非追加。没有文档时写“待核实”，不能用前缀猜测算法自动混用。

### 1.2 唯一主线：增量归并 → 快照 → 受控呈现
```text
用户点击 + 昨日门禁 + 当前最上层前台
  → 新请求代号 id，旧代号失效，取消旧 Job
  → 单飞锁：等待旧请求 finally，再创建新客户端并复查状态
  → SDK Flow："哈" / "哈" / "！"(STOP)
  → 归并正文："哈" / "哈哈" / "哈哈！"（不按文本内容去重）
  → MutableStateFlow<StreamUi>：不可变、累计UI快照
  → collectAsStateWithLifecycle(RESUMED) → Text(state.draft)
  → collect正常完成且 STOP+非空，才进入 SUCCESS → 用户明确点击采纳
任何中断 → 取消/超时/失败状态，隔离草稿，finally尝试close
```
**增量流不能丢片，UI 快照可以合并更新**：SDK 的两个 `"哈"` 是合法重复内容，`distinctUntilChanged()` 会误删；在增量归并前加 `conflate()` 也会掉字。归并后的完整 UI 快照进入 StateFlow，即使 Compose 没画出每个中间帧，最新快照仍有全文。这里不做“每 Token 都重组一次”的性能承诺。

### 1.3 终态、草稿与生命周期（应用策略，不是 SDK 枚举）
| 条件 | 应用状态 | UI 与采纳策略 |
|---|---|---|
| 中间帧或最终标记已到，但 collect 尚未正常完成 | STREAMING | 显示预览，禁止采纳 |
| 正常完成 + STOP + 正文非空 | SUCCESS | 显示正文；仅用户点击采纳才写回 |
| 正常完成 + STOP + 仅空白正文 | EMPTY_RESULT | 保留原输入，禁止采纳 |
| 正常完成 + MAX_TOKENS（含零文本） | TRUNCATED | 未完成草稿，默认隔离，不伪称成功 |
| 正常完成但无标记/OTHER/未知结束原因 | INCOMPLETE | EOF不是成功凭证；隔离草稿 |
| 异常，包括见过STOP后仍发生异常或多余帧 | FAILED | 草稿保留在独立字段，默认不作为正文显示 |
| 用户停止、ON_PAUSE、页面移除、父协程取消 | CANCELLED | 撤销发布权限并传播取消；禁止采纳 |
| 生成预算耗尽 | GENERATION_TIMEOUT | 隔离已有草稿；不自动重试/上云 |

- **安全中断**：官方建议错误时考虑移除已流出的部分输出。本课选择“内存留草稿，但默认隐藏正文、取消采纳资格”，不是把错误字符串拼进回答；生产应用对安全失败可直接清空，不应让用户误认成功。
- **取消分两层**：生命周期感知收集只停 UI 对 StateFlow 的订阅，**不会因此自动取消 ViewModel 已启动的 SDK 推理**。ON_PAUSE/onDispose 明确 `stop()`；ViewModel 清理则取消 `viewModelScope`。本课选择暂停也停止（含旋转），不自动续跑；输入可保存，生成结果不承诺跨进程持久化。
- **旧请求隔离**：先递增请求代号，再 cancel。所有结果/错误/取消发布都检查代号；单飞锁使新实例等旧 finally 完成。锁只保障应用生命周期串行，**不证明设备计算已停止或资源释放成功**。
- **前台与资源**：页面 RESUMED 还需调用方提供应用最上层前台证据；前台服务不替代。`close()` 文档允许多次调用；本课一次请求一次实例，在 finally 尝试关闭，关闭错误独立计数不掩盖原错。超时预算是教学策略，不是 SDK 延迟保证。

**常见误区（3 条）**：
1. 很多人以为“所有流值都是累计答案”，其实这里的官方指南使用追加；不能只看方法名，也不能把 Callback 最终完整响应追加到已有草稿。
2. 很多人以为“去重/丢中间帧更顺滑”，其实在**增量层**会丢合法重复字；应先完整归并，再向 UI 发布累计快照。
3. 很多人以为“停止 UI collect 或拿到 STOP 就完成”，其实在途生成要明确取消，STOP后也要等 collect正常完成；失败和旧请求不得恢复采纳资格。

**来源登记（全部实际读取，HTTP 200；教学旧链接继续使用，非新动态）**：页面更新时间/版本不是今天的发布日期；候选检索与未引用链接不算新动态。原文及来源哈希见证据目录。

@@SOURCE_TABLE@@

- 📝 **我的复述（这段留空给你自己写，不代写）**：


## 2 代码片段（40 min）
- **场景**：虚构便签本地改写。正文逐渐出现在预览区；用户换输入/点击停止/离开页面时停止请求；失败草稿不能污染原文或新回答。
- **依赖与版本**：Host＝CPython **3.9.6** 标准库 `asyncio/dataclasses/typing`，测试用 `unittest`，零第三方依赖。Android 片段＝`com.google.mlkit:genai-prompt:1.0.0-beta4`、`androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.7`、`androidx.lifecycle:lifecycle-runtime-compose:2.8.7`、`androidx.compose.material3:material3:1.3.0`；四份 Google Maven POM 均200。Prompt POM声明 Kotlin标准库2.3.21、协程核心1.7.3；**这不是本机已安装或完整依赖解析结果**。Android API ≥26，仍需已有工程的 Compose/编译插件/Gradle/SDK 与支持 Nano 的准备好设备。
- **版本边界**：当前在线 Compose 参考页标注2.10.0，不能直接当作2.8.7证明；已额外从 Google Maven **2.8.7 sources.jar 在内存读取 FlowExt 与 LocalLifecycleOwner 源码**〔S21〕，确认本片段使用的 StateFlow重载、参数默认值、包路径与 repeatOnLifecycle机制。只留文本，不安装/保留二进制依赖；完整版本组合兼容性仍未编译验证。

### 2.1 最小可运行 Host fixture（EXECUTED）
以下与 `../00_进度/验证/2026-11-18/stream_contract.py` 逐字一致。`FakeClient` 输出固定中文，不是真实端侧模型；它验证**归并与状态控制逻辑**，不是 SDK、Compose或性能。`CUMULATIVE`只是对照适配器，Android固定走DELTA。
```python
@@PYTHON@@
```

### 2.2 实跑命令、真实输出与覆盖
首次执行在 `/tmp/ai-study-20261118-f8xlkrwu` 的本任务副本，退出后仅清理该无引用副本；永久源码/日志在当天证据目录。可复跑：
```bash
cd '/Users/alion/DemoProjects/ToDoList/AI每日学习/00_进度/验证/2026-11-18'
python3 -B stream_contract.py
python3 -B -m unittest -v test_stream_contract.py
```
**真实输出**（两条命令退出码均0；未调用模型，所以无usage）：
```text
@@FIXTURE_LOG@@
Ran 17 tests
OK
```
**覆盖证据**：测试源码 `test_stream_contract.py` 与完整 `tests.log` 保留，可逐项查看；17个测试方法均实跑，不把未执行的真机用例算通过。
| 必查边界 | Host测试定位 |
|---|---|
| 不同分片、重复文本、最后一帧含字、空终止帧 | test_partitions_and_repeated_words |
| 逐片空格保留、明确累计快照适配 | test_whitespace_preserved / test_explicit_cumulative_not_append |
| STOP/MAX_TOKENS/OTHER/未知/无标记、空流/空白/空文本 | test_finish_table / test_empty_and_null |
| 标记后多余帧、标记后失败、已有草稿后失败 | test_terminal_then_extra_is_invalid / test_stop_marker_then_failure_not_success / test_failure_keeps_unacceptable_draft |
| 草稿后超时、用户取消/父协程取消继续传播 | test_timeout_after_draft / test_user_cancel_propagates / test_parent_cancel_propagates |
| 页面暂停/移除/销毁对应stop、流中失去前台 | test_page_pause_foreground_and_dispose / test_foreground_lost_during_stream |
| 旧请求吞取消后迟到、新实例等旧close后创建 | test_replacement_blocks_stale_and_serializes_release |
| 清理错误不覆盖原失败/取消、关闭失败不称已释放 | test_cleanup_failure_does_not_mask_original |
| 前置拒绝零次创建、不可用不生成且关闭 | test_preflight_no_client / test_unavailable_closes_without_stream |
空流、空文本、标记后多余帧是**坏适配器防御fixture**，不宣称正常SDK会如此返回。Host页面事件只是动作模拟，不能证明Android生命周期顺序。0.03秒预算仅让等待fixture结束，0.070秒是Host测试耗时，均不是推理指标。

### 2.3 ViewModel / Compose实际API接入片段（SPEC_CHECK，NOT_EXECUTED）
下面与 `NanoStreamScreen.kt` 逐字一致。**不是独立可运行App**：需要已有 Android 工程提供页面作用域 VM、门禁结果、最上层前台证据、Material/Compose宿主及完整工具链；还需支持且已准备好模型的设备。本次按安全边界不创建/改动工程、不安装依赖、不编译、不连手机；不能声称本片段已在Android运行。
```kotlin
@@KOTLIN@@
```

**逐行要点（5条）**：
1. `generateContentStream(request)` 每帧先 `draft + candidate.text` 再读 `finishReason`；相同文本不能删除，空格不能逐片trim。
2. `MutableStateFlow<StreamUi>` 存完整正文快照，`copy()`发布新不可变值；Compose只读最新快照，不自己重复拼接SDK响应。
3. `epoch` 先撤销旧发布权，`Mutex` 串行包住创建到finally；取消旧任务后的新请求不会复用已关闭实例。
4. `complete==true`、正常collect结束、`STOP`和非空同时满足才采纳；见过STOP后异常仍FAILED。
5. `withTimeoutOrNull`吸收自己创建的超时，外层取消继续重抛；ON_PAUSE/onDispose明确stop，finally尝试close，清理错误独立计数。

**踩坑提示**：
- 主线程入口、回调不抛异常、页面作用域VM是调用方接入约束；如果把VM放全局或多页面共享，某页dispose可能取消另一页请求，需要另做作用域设计，不是本课已解决的能力。
- StateFlow合并的是UI快照；不对SDK增量流做 `conflate/distinctUntilChanged`。当前短输出预算64 tokens，简单字符串追加用于教学，不宣传长文本性能。
- 参考页 `Candidate.text` 声明String，说明又提仅函数结果时可能null。本课不启用工具，仍使用 `orEmpty()`防御；不读取思考过程、不产生函数调用。
- 本片段仅状态/生成链路，未加滚动定位/渲染节流/聊天持久化。若真实SDK取消不合作或close失败，可能等待或资源残留；请求代号能防UI污染，不能替代真机资源与延迟验证。

## 3 动手 / 联想（20 min）
- **动手任务（仅一个小改动）**：在Host测试新增 `test_cancel_then_new_request`：旧fixture输出“旧草稿”后等待→调用stop→确认旧task抛取消且不可采纳→再启动 `Frame("新", "STOP")`→确认正文只剩“新”、新旧客户端均各close一次。已有replacement测试覆盖直接替换；今天练的是**显式停止后再开始**，不是再加一个概念。
- **时间分配**：5分钟画请求id/草稿/采纳资格三列，10分钟写新增测试，5分钟复跑。只在练习副本敲，不改真实Android工程、不安装SDK。参考测试已保留，不代填你的练习或复述。
- **与我的工作结合**：Android便签与聊天输入区用“预览与采纳分开”避免半成品覆盖原文；小程序/React可复用请求代号与累计UI快照，但它们不能直接调用Android ML Kit。你已有UI与状态管理经验，今天补的是**生成任务的生命周期契约**，不是打字机动画技巧。
- **自检标准**：停止后草稿不可采纳；新结果不夹旧字；父取消继续传播；失败不自动重试/下载/上云；Host通过不记为Android真机通过。

## 4 动态与机会（20 min）
> 观察日期2026-11-18；**1条新动向 + 1条岗位 + 1条工具**。canonical URL与完整旧台账核对后首次收录。新收录不等于今天发布；全部链接curl核验200。官方教学旧链接不算动态。以下事实来自实读正文，影响判断与补课建议标〔PROPOSAL〕。

- 🔥 **新动向（1条）｜Google AI Studio支持构建全栈Android应用** — 官方《Build full-stack Android apps with Gemini in Google AI Studio》**2026-11-17发布**，正文与datePublished实读。文章介绍Cloud Firestore/登录配置、Firebase AI Logic保护调用、浏览器模拟器迭代与个人Play库发布；**这是云端Gemini接入与AI辅助开发，不是本课Nano端侧推理**。“快速生产可用”是官方产品描述，本次未亲测。**影响判断〔PROPOSAL〕**：生成代码越来越快，取消、失败隔离与凭据边界的验收能力更有价值；不要把生成成功当工程质量通过。— [来源](https://developers.googleblog.com/build-full-stack-android-apps-with-gemini-in-google-ai-studio/)
- 💼 **岗位观察（1条）｜腾讯微信小程序：大模型应用开发工程师—智能体方向（广州）** — 正式详情API实读，业务Code=200；网页200但仅JS壳。**更新时间2026-11-11，原发布日期未提供**。职责涉及生成式UI、可观测与复杂任务调度；要求至少1年工作经验、本科、LLM/Agent/Harness/MCP/A2A实践与前后端全栈/系统设计。**对应该补〔PROPOSAL〕**：你的小程序/前端背景有切入点，仍需后端与Agent工程作品；今天的可取消状态链只能补一块，不代表已经满足岗位要求。不编薪资或岗位趋势。— [来源](https://careers.tencent.com/jobdesc.html?postId=2086789748948643840)
- 🧰 **其他有价值信息（1条）｜Android官方compose-samples中的Jetchat聊天样例** — 仓库页与Jetchat README均200实读；README列UI状态、ViewModel、输入焦点、配置变化及UI测试，注明仍有功能在开发。**未提供原发布日**，版权年份不当发布日期。**值得看〔PROPOSAL〕**：观察聊天UI状态与输入的职责分离；这不是Nano流式示例，也不能用它证明端侧推理。本次仅阅读，不克隆/编译或运行。— [来源](https://github.com/android/compose-samples)

**20分钟安排**：新动向8分钟（区分云端调用/端侧推理），岗位6分钟（圈出现有强项与后端缺口），Jetchat6分钟（只看UI状态与输入职责，不复制完整工程）。

## 5 明日预告与待复习（8 min）
- **明日主题〔PROPOSAL〕**：Android × AI 第4讲：**端侧生成的性能测量：首字时延与完整耗时**。重点是测量边界、真机条件和记录方法，未具备设备时仍只做契约与待测项；不重复今天的SDK拼接/Compose接入，不把Host时间冒充Nano性能。
- **待复习（3条）**：
  1. 官方指南明确正文新增片段要追加，最终帧也含新增字；Callback最终完整响应不能二次追加。
  2. 先归并增量再发布累计不可变快照；重复文本合法，只有正常完成+STOP+非空可采纳。
  3. 停UI订阅不等于停VM推理；请求代号挡旧结果，取消继续传播，finally尝试close，失败草稿隔离。
- **一句话复盘**：最容易忘的是——**UI拿到的应该是完整快照，SDK拿到的却是新增片段；这两层不能用同一套丢帧策略**。
- **收尾**：5分钟自己填复述，3分钟对照新增测试。缓冲1.5分钟记录Android尚未编译/真机未测，不替你勾练习完成。
- **证据与交付口径**：`../00_进度/验证/2026-11-18/` 保留输入哈希、实读来源/日期/去重注册表、源码、真实执行日志/退出码、台账写前备份、ledger.diff与验收结果。USER＝目标和禁令；ARTIFACT＝完整台账/规则/前置材料；TOOL＝源契约/HTTP/Host实跑；PROPOSAL＝预算与练习/明日安排。无隐含假设。摘要仅交主智能体草稿，**not_sent**，本执行者不发送/编辑飞书。
