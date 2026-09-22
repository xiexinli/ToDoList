# Skill 概念、作用、生成方法 —— Android / H5 开发技能推荐

> 整理日期：2026-09-21
> 适用环境：DHwork（基于 Claude 的云端智能体工作空间）

---

## 一、Skill 是什么（概念）

**Skill（技能）是模块化、自包含的能力包，用于扩展 AI Agent（Claude）的专业能力。**

可以把 Skill 理解为一份「领域上岗指南」：它把特定领域的专业知识、操作流程、工具用法和可复用资源打包在一起，让 Agent 从「通用助手」变成「特定领域的专家」。

Skill 由 **一个必需的 `SKILL.md` 文件 + 可选的捆绑资源** 组成：

```
skill-name/
├── SKILL.md          # 必需：YAML frontmatter + Markdown 指令
├── scripts/          # 可选：可执行脚本（Python / Bash / 等）
├── references/       # 可选：按需加载的参考资料 / 文档
└── assets/           # 可选：最终产出要用的模板、图片、字体等
```

### SKILL.md 的结构

```markdown
---
name: skill-name                 # 必需：技能名称
description: ...                 # 必需：一句话描述 + 何时触发（最重要的触发机制）
---
# 技能正文（Markdown）
...

```

关键点：
- `name` 和 `description` 是 **Agent 判断何时启用该技能的唯一依据**，必须写清楚「做什么」+「什么时候用」。
- 技能正文只在技能被触发后才加载，所以「何时使用」这类信息要写进 `description`，而不是正文。

### 捆绑资源的用途

| 目录 | 用途 | 典型内容 |
|---|---|---|
| `scripts/` | 需要确定性执行、会被反复重写的代码 | `scripts/rotate_pdf.py`、构建脚本、批处理脚本 |
| `references/` | 按需加载进上下文的文档 | API 文档、数据库 Schema、公司规范、迁移指南 |
| `assets/` | 最终产出要使用的文件（不加载进上下文） | Logo、PPT 模板、前端脚手架模板、字体 |

### 渐进式披露（Progressive Disclosure）

Skill 采用**三级加载**机制控制上下文占用：

1. **元数据**（name + description）：始终在上下文中（约 100 词）；
2. **SKILL.md 正文**：技能被触发时加载（建议 < 500 行 / < 5k 词）；
3. **捆绑资源**：Agent 按需加载（可无限，因为脚本可以不读内容直接执行）。

原则：**SKILL.md 保持精简**，详细内容拆到 `references/` 子文件中，并在正文中说明何时去读哪个文件。

---

## 二、Skill 的作用（能解决什么问题）

1. **专业化工作流**：封装多步骤的领域流程，如「Android 性能分析」「飞书会议纪要整理」。
2. **工具集成**：指导 Agent 使用特定 CLI、文件格式或 API（如 `android` CLI、Office 文档处理）。
3. **领域专业知识**：沉淀公司/团队私有知识、Schema、业务逻辑，这些是模型本身不具备的。
4. **捆绑可复用资源**：模板、脚本、示例工程，避免每次重复生成，且执行更可靠。
5. **上下文经济**：只把需要的知识按需加载，不浪费宝贵的上下文窗口。

> 一句话：**Skill = 给 Agent 装上的「专业插件」**，让它可以稳定、高质量地完成某一类特定任务。

---

## 三、如何生成一个 Skill

### 标准流程（6 步，来自官方 skill-creator）

**Step 1：理解使用场景**
明确技能要支持的功能。举例问法：
- 「这个技能应该支持哪些功能？」
- 「用户会怎么用？什么请求应该触发这个技能？」

**Step 2：规划可复用内容**
分析具体用例，决定要放入哪些 `scripts/`、`references/`、`assets/`。
- 反复重写的代码 → 放进 `scripts/`
- 需要查阅的文档/Schema → 放进 `references/`
- 要套用的模板/脚手架 → 放进 `assets/`

**Step 3：初始化技能（生成模板骨架）**
```bash
scripts/init_skill.py <skill-name> --path <输出目录>
```
脚本会自动生成 `SKILL.md` 模板、`scripts/`、`references/`、`assets/` 目录及示例文件。

**Step 4：编辑技能**
- 实现 `scripts/`、`references/`、`assets/` 中的资源，删除用不到的示例文件；
- 编写/改写 `SKILL.md`：填写 frontmatter 的 `name`、`description`，正文使用**祈使句**编写指令；
- 脚本资源要**实际运行测试**过再打包。

**Step 5：打包技能（校验 + 打包）**
```bash
scripts/package_skill.py <path/to/skill-folder>   # 可选加 ./dist 指定输出目录
```
打包前自动校验：frontmatter 格式、命名规范、description 完整性、文件组织等。校验通过后生成 `.skill` 分发文件（本质是 zip）。

**Step 6：基于真实使用迭代**
在实际任务中试用 → 发现卡点 → 更新 SKILL.md / 资源 → 再测试。

### 在本环境（DHwork）中创建技能的实操方式

本环境的技能通过 `cloud_skill_*` 工具管理：

1. **创建**：`cloud_skill_create`（提供 `name`、`description`，内容可内联 Markdown，也可从云端 Markdown 文件或目录导入）；
2. **查看**：`cloud_skill_list` 列出全部技能；
3. **读写文件**：`cloud_skill_file_read` / `cloud_skill_file_write` / `cloud_skill_file_delete`（`SKILL.md` 及其它支持文件）；
4. **更新元信息**：`cloud_skill_update`（改名、改描述、启用/停用）；
5. **挂载生效（关键）**：`cloud_skill_attach` —— **创建 ≠ 可用**，必须 attach 到某个 Agent 上才会被加载；
6. **维护分发**：改动技能文件一律用 `cloud_skill_file_write`，保证共享者能收到更新。

---

## 四、Android 开发相关 Skill 推荐

### 4.1 基础核心（必备）

| 技能 | 说明 | 推荐度 |
|---|---|---|
| **android-cli** | Google 官方 Android 命令行工具技能：创建工程、管理 SDK、运行 App、模拟器、截图、UI 布局检查、查官方文档。**Android 开发的入口技能**（你当前环境已拥有） | ⭐⭐⭐⭐⭐ |

### 4.2 官方 Android 专项技能（当前可获取的 24 个）

**UI / 界面适配类**

| 技能 | 用途 |
|---|---|
| **adaptive** | 让 UI 适配手机/平板/折叠屏/桌面/TV/车机/XR，多窗格布局、Compose MediaQuery/Grid/FlexBox |
| **edge-to-edge** | Jetpack Compose 全面屏（边到边）迁移，修复被导航栏/状态栏遮挡的 UI、IME insets |
| **styles** | 界面样式相关的规范化处理 |
| **migrate-xml-views-to-jetpack-compose** | 从传统 XML View 体系迁移到 Jetpack Compose |
| **leanback-to-compose-tv-migration** | Android TV 从 Leanback 迁移到 Compose for TV |

**架构 / 导航类**

| 技能 | 用途 |
|---|---|
| **navigation-3** | Jetpack Navigation 3 安装与迁移：深链、多返回栈、Scenes、条件导航、Hilt/ViewModel 集成 |
| **navigation-event** | 拦截返回手势、预测性返回动画（NavigationEvent 库，SDK 36+） |

**性能 / 安全 / 构建类**

| 技能 | 用途 |
|---|---|
| **android-profiler** | 性能剖析与调试：系统 trace、heap dump、方法记录、内存分配、卡顿/内存泄漏/启动问题排查 |
| **android-intent-security** | Intent 安全最佳实践：审计 Manifest 组件配置，防 Intent Redirection 与未授权访问 |
| **r8-analyzer** | 分析 R8 keep 规则，优化包体积、去除冗余/过宽规则 |
| **agp-9-upgrade** | 升级项目到 Android Gradle Plugin (AGP) 9（不适用于 KMP 项目） |

**测试 / 质量类**

| 技能 | 用途 |
|---|---|
| **testing-setup** | 制定原生 Android 测试策略：单测、UI 测试、截图测试、端到端测试的基建与框架搭建 |

**平台 / 能力类**

| 技能 | 用途 |
|---|---|
| **camerax** | CameraX 相机开发：异步录制生命周期、底层硬件互操作、ML Kit / Media3 特效集成 |
| **media3-cast-integration** | 基于 Jetpack Media3 接入 Google Cast（含从旧 Cast SDK 迁移） |
| **wear-compose-m3** | Wear OS Compose Material3 开发与迁移 |
| **display-glasses-with-jetpack-compose-glimmer** | 智能眼镜（Android XR）投影式 App 开发，Compose Glimmer UI 工具包 |
| **appfunctions** | 分析 App 关键用户流程，生成 Kotlin 代码暴露给系统/AI 代理在端上发现并执行 |
| **verified-email** | 基于 Android Credential Manager 的无 OTP 邮箱验证流程 |
| **restore-credentials** | 用 androidx.credentials 实现 Restore Credentials，新设备静默登录 |
| **engage-sdk-integration** | Play Engage SDK 集成、调试、问题修复 |
| **play-billing-library-version-upgrade** | Play Billing 库版本升级 |
| **play-policy-insights** | Play 政策合规洞察 |
| **ml-kit-genai-prompt-api** | ML Kit 生成式 AI Prompt API |

### 4.3 按场景推荐的「安装组合」

```bash
# Android CLI 查看/安装技能的命令
android skills list               # 列出已安装与可用技能
android skills find <keyword>     # 按关键词搜索技能
android skills add <id>           # 安装指定技能
android skills remove <id>        # 卸载指定技能
```

- **刚上手 Android / 通用开发**：`android-cli` + `adaptive` + `testing-setup`
- **Compose 化改造（重点推荐）**：`migrate-xml-views-to-jetpack-compose` + `edge-to-edge` + `navigation-3`
- **追求性能与包体积**：`android-profiler` + `r8-analyzer` + `agp-9-upgrade`
- **做安全 / 合规**：`android-intent-security` + `play-policy-insights`
- **多端 / 新形态**：`adaptive` + `wear-compose-m3` + `display-glasses-with-jetpack-compose-glimmer`
- **电视 / 投屏**：`leanback-to-compose-tv-migration` + `media3-cast-integration`

---

## 五、H5 开发相关 Skill 推荐

H5（移动端网页 / Hybrid Web 页面）开发目前**没有独立的官方内置 Skill**，但有两类可用的方案：

### 5.1 现成可复用的通用 Skill（间接服务 H5 场景）

| 技能 | 对 H5 开发的帮助 |
|---|---|
| **mermaid** | 快速绘制架构图、流程图（组件依赖、路由流程、交互时序）并输出 SVG |
| **UI/UX 设计智能助手** | 提供 57 种风格、95 套配色、56 组字体配对与前端技术栈最佳实践，直接服务 H5 页面视觉 |
| **PPT / 文档 / 表格类**（pptx、docx、xlsx、officecli） | 产出方案文档、技术评审 PPT、数据报表 |
| **文件规划助手** | 复杂 H5 项目的任务拆解与多步工作流规划（task_plan.md / findings.md / progress.md） |

### 5.2 建议「自建」的 H5 专项 Skill（按团队/项目沉淀）

H5 开发的高频痛点适合封装成自定义 Skill，推荐方向：

1. **H5 项目脚手架 / 模板（assets/）**
   - 内容：Vite + Vue3 / React + TS 的 boilerplate、目录规范、`.eslintrc`、`tsconfig` 等
   - 触发场景：用户说「新建一个 H5 项目 / 页面」

2. **移动端 H5 适配规范（references/）**
   - 内容：rem / vw 适配方案、安全区（safe-area）处理、viewport meta、兼容性矩阵（iOS Safari / 安卓 WebView）
   - 触发场景：页面在不同机型/浏览器上错乱、需要做移动端适配

3. **WebView 与原生交互 Bridge 规范（references/ + scripts/）**
   - 内容：JSBridge 协议定义、`window.webkit.messageHandlers` 与 `addJavascriptInterface` 用法、事件名/参数约定、调试手段
   - 触发场景：App 内嵌 H5 需要与原生通信、排查 bridge 失效

4. **前端构建 / 发布脚本（scripts/）**
   - 内容：打包、产物裁剪、CDN 上传、版本号/缓存策略、CI 集成脚本

5. **组件库 / 设计规范沉淀（references/）**
   - 内容：团队组件库 API、设计 token、暗黑模式、无障碍要求

### 5.3 H5 Skill 示例骨架（可直接照抄改造）

```
h5-mobile-adapt/
├── SKILL.md
│   └── 描述: 移动端 H5 页面适配与最佳实践……
├── references/
│   ├── viewport-meta.md      # viewport、缩放、双击延迟
│   ├── safe-area.md          # 刘海屏/底部安全区处理
│   ├── rem-vw-strategy.md    # 适配方案与换算规则
│   └── browser-matrix.md     # iOS/安卓 WebView 兼容性矩阵
└── scripts/
    └── px-to-rem.py          # px ↔ rem 批量换算脚本
```

---

## 六、小结

- **Skill = 专业领域「上岗指南」**，由 `SKILL.md`（必需）+ `scripts/` + `references/` + `assets/`（可选）组成。
- **作用**：封装工作流、集成工具、沉淀领域知识、捆绑资源、节省上下文。
- **生成**：理解场景 → 规划内容 → `init_skill.py` 初始化 → 编辑实现 → `package_skill.py` 打包 → 迭代；本环境用 `cloud_skill_create` + `cloud_skill_attach` 落地。
- **Android**：先装 `android-cli`，再按场景挑选官方专项技能（UI 适配 / 导航 / 性能安全 / 构建 / 测试 / 新形态）。
- **H5**：无专门官方技能，可复用通用技能（mermaid、UI/UX 助手、文档类），建议自建「脚手架 / 适配规范 / Bridge 交互 / 构建发布」四大类自定义 Skill。

---

*本文档基于当前环境中可获取的 32 个技能目录与 Google Android CLI 的 24 个官方技能列表整理。*
