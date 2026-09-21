# 演示：<feature 中文名>

小组: <名字> · 日期: <日期>

## 1. Spec 展示（3 min）
- EARS 验收标准 <Y> 条（P0 <b> 条），任务 <n> 个，总估时 <h> 小时。
- 一句话讲清做了什么、没做什么。

## 2. 追溯演示（5 min）
### AC-xx <一句话>（正常流）
- EARS：`…`
- 测试：`tests/…::test_ac_xx_…`
  ```python
  # 贴 5 行断言
  ```
- 实现：`src/…:函数`
  ```python
  # 贴 5–10 行
  ```
- 现场命令：`npx vitest run -t "AC-xx"`（或 `uv run pytest -k ac_xx -v`）· `grep -rn "Implements: AC-xx" src/` · 页面上操作对应场景

### AC-yy <一句话>（异常流 / Unwanted）
（同上）

## 3. 测试结果（2 min）
- `npm test`（或 `uv run pytest -q`）→ **通过 X / Y 条 EARS（P0 a / b）**；`typecheck` / `lint` 通过
- 原型：`npm run dev` → `http://localhost:3000/…` → 操作步骤 1/2/3 → 预期看到什么（贴文本，演示失败时可读）
- T0 从零脚手架实际用时：<n> 分钟
- （Agent 类）live 评估：`live-eval.txt` 摘要，现场只跑 1 条

## 4. 未完成项（2 min）
| AC | 原因 | 预计工时 |
|---|---|---|

## 5. 会后跟进（2 min）
- [ ] 补齐 P1/P2；synthetic 样本替换为客户真实数据
- [ ] 需客户提供：…
- [ ] 入口增强（可选）：为业务类课题加一个纯静态 Web 页（无后端、无数据库；历史/配置存 localStorage，输出文件本地下载），研发类课题保留 CLI。
- [ ] 若将来要接入真实系统：把 mock 换成真实接口、把 fake 换成真实模型，测试不变。

## 6. 时间线与复盘三行
| 阶段 | 开始 | 结束 |
|---|---|---|
- 顺：
- 卡：
- 下次：
