<div align="center">

# 🔥 GitHubHot

### 每天一份值得读的 GitHub 热点中文深度日报

[![Daily](https://img.shields.io/badge/更新-每日-e11d48?style=for-the-badge)](daily/)
[![Language](https://img.shields.io/badge/内容-中文深度分析-8b5cf6?style=for-the-badge)](daily/)
[![License](https://img.shields.io/badge/License-MIT-16a34a?style=for-the-badge)](LICENSE)

<!-- DAILY_LATEST_START -->
**[📖 阅读今日日报](daily/2026/08/2026-08-17.md)** · **[🗓️ 浏览历史](#-日报归档)** · **[💬 推荐项目](CONTRIBUTING.md)** · [English](README_EN.md)

</div>

> [!TIP]
> 不只看 Stars。每天先读趋势，再看 3 个重点项目、7 个快速判断，以及 1 篇重点项目深挖。

## 📖 今日日报

### [2026-08-17 · 今日值得关注的开源项目 →](daily/2026/08/2026-08-17.md)

| # | 项目 |
|---:|---|
| 1 | [public-apis/public-apis](https://github.com/public-apis/public-apis) |
| 2 | [OpenCut-app/OpenCut](https://github.com/OpenCut-app/OpenCut) |
| 3 | [unslothai/unsloth](https://github.com/unslothai/unsloth) |

> **推荐阅读方式：** 先看“今日趋势”和 TOP 10 榜单；前三名提供完整分析，其余七项快速浏览，第一名另有独立深挖长文。
<!-- DAILY_LATEST_END -->

## 🧭 每份日报有什么

GitHubHot 不只罗列 Stars。每个入选项目都会从以下角度展开：

| 今日趋势 | TOP 3 深读 | 7 项速览 | 每日深挖 |
|---|---|---|---|
| 📊 技术分布 | 🧩 技术观察 | 🎯 中文定位 | 🔬 痛点与机制 |
| 💡 机会雷达 | ⚠️ 风险边界 | 👥 适合人群 | 🚀 快速体验 |

## 🗓️ 日报归档

<!-- DAILY_INDEX_START -->
- [2026-08-17 · 🔥 GitHubHot 日报](daily/2026/08/2026-08-17.md)
- [2026-08-16 · 🔥 GitHubHot 日报](daily/2026/08/2026-08-16.md)
- [2026-08-15 · 🔥 GitHubHot 日报](daily/2026/08/2026-08-15.md)
- [2026-08-14 · 🔥 GitHubHot 日报](daily/2026/08/2026-08-14.md)
- [2026-08-13 · 🔥 GitHubHot 日报](daily/2026/08/2026-08-13.md)
<!-- DAILY_INDEX_END -->

<details>
<summary><strong>🔎 我们如何选择项目</strong></summary>

每天扫描近期创建且快速增长的公开仓库，综合观察：

- Star 规模与增长速度
- Fork、Issues 等参与度
- 最近提交和 Release 活跃度
- README、许可证和项目描述完整度
- 是否具备明确的开发者价值和进一步分析空间

热度只是发现信号，不代表项目质量、安全性或商业价值。日报会明确列出事实依据、推断边界和采用风险。

</details>

<details>
<summary><strong>🛡️ 内容原则</strong></summary>

- 以官方仓库、README 和 Release 为主要来源；
- 中文分析不得补充来源中不存在的事实；
- 不把 Stars 等同于质量或成功；
- 安装命令优先引用官方 README；
- 区分事实、判断与机会假设；
- 项目成熟度、安全性和生产可用性由读者最终判断。

</details>

## 💬 推荐项目或修正内容

欢迎通过 Issue 推荐近期值得关注的项目，或通过 Pull Request 修正日报中的事实错误。自荐允许，但请说明你与项目的关系。

<details>
<summary><strong>⚙️ 关于自动化</strong></summary>

日报由自动流程收集 GitHub 公开数据、官方 README 和 Release；配置 DeepSeek API 后会生成中文结构化分析，也支持人工编辑稿覆盖和校订。生成器和测试保留在仓库中以便审计，但这个项目的主要产物始终是 `daily/` 下的日报。

本机任务每天 10:00 首次发布，并在 12:00、18:00 自动检查和补偿未完成日期；若 10:00 遇到持续网络故障，不需要人工再次启动。每次运行都会从首篇日报开始检查日期缺口，并按时间顺序补齐（单次最多 7 天）。Git pull/push 设置 90 秒硬超时和三次退避重试，默认重试间隔为 60、120 秒；系统 DNS 返回不可达的 GitHub 区域节点时，Git 传输会自动尝试经过 TLS 校验的官方备用节点。GitHub 暂时不可达时不会阻断可继续执行的步骤，未生成日期与未推送提交会由本轮或后续补偿任务继续处理。日志会标记每个日期和执行阶段，便于直接定位失败点。

流水线会以「赛博木匠」的内容风格，把 Top 3 自动改写为微信公众号长文、小红书图文文案和一条高密度 X 摘要，保存到本地 `.local/social-drafts/YYYY-MM-DD/`，并附带统一的赛博木匠 V3 封面。微信公众号配置完成后，程序会在首次运行时自动把封面上传为永久素材、缓存 `media_id`，随后通过官方草稿 API 自动进入草稿箱；同一日期在 `manifest.json` 已记录成功时会自动跳过，避免重复创建草稿。

小红书和普通 X 账号没有公开的服务端草稿 API，因此本机流程使用一个独立 Chrome 用户目录保存登录态。小红书等待页面出现「编辑于」自动保存标志，X 只点击「保存」，绝不点击发布按钮。首次使用前运行 `scripts/run_social_browser_drafts.sh`，在打开的专用 Chrome 中分别登录小红书创作服务平台和 X；以后本机任务会复用该登录态。页面改版导致保存状态无法识别时，流程会停止并在 `manifest.json` 记录错误，不会误发布。

维护和本地运行方式见 [CONTRIBUTING.md](CONTRIBUTING.md)。

</details>

## License

[MIT](LICENSE)
