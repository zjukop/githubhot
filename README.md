# GitHubHot

> 每天精选一个正在快速增长的开源项目，解释它解决什么问题、为什么受到关注，以及它背后还有哪些开发机会。

GitHubHot 不是 GitHub Trending 的搬运站。它由两部分组成：

1. 一个透明、可复现的候选仓库扫描工具；
2. 一份经过人工选择、事实核验和技术判断的中文日报。

[English](README_EN.md)

## 为什么做这个项目

热门仓库能反映技术势能，却不能直接证明项目质量或商业需求。GitHubHot 先用公开数据发现异常活跃的候选，再由人工回答：

- 它服务谁、解决什么问题？
- 为什么最近受到关注？
- 与现有方案有什么区别？
- 最短的可验证运行方式是什么？
- 有哪些局限、安全风险和平台依赖？
- Issues 中还暴露了哪些二阶开发机会？

## 每日精选

<!-- DAILY_INDEX_START -->
- 暂无已发布内容
<!-- DAILY_INDEX_END -->

## 快速开始

要求 Python 3.11+。

```bash
python -m githubhot scan --days 30 --min-stars 100 --limit 30
```

扫描结果写入 `data/candidates.json`，每日指标快照写入 `data/snapshots/`。未配置 Token 时也能使用 GitHub 公共 API，但限额较低：

```bash
export GITHUB_TOKEN="your-fine-grained-token"
python -m githubhot scan --topic ai-agent --topic developer-tools
```

从候选列表生成一篇需要人工审核的草稿：

```bash
python -m githubhot draft owner/repository
```

完成事实核验并清除所有 `TODO` 后，更新首页索引：

```bash
python -m githubhot index
```

也可以安装为本地 CLI：

```bash
python -m pip install -e .
githubhot scan
```

## 评分说明

当前 GitHub 公共搜索接口不提供历史 Star 数，因此第一天的评分只使用候选发现信号：

- Star 规模：25%
- 按仓库年龄估算的 Star 速度：35%
- Fork 与 Issue 参与度：15%
- 最近提交活跃度：15%
- 可识别许可证：5%
- 清晰描述：5%

评分只用于缩小人工筛选范围，**不代表项目质量、安全性或投资价值**。每日快照积累后，后续版本会使用真实的 1/7/30 日 Star 增量取代估算速度。

## 发布原则

- 自动化只生成候选和资料草稿，不自动发布文章；
- 安装与运行命令必须人工验证；
- 无法证明的流行原因必须标记为推测；
- 每篇至少包含一个 README 中没有的技术判断；
- 明确记录成熟度、安全、隐私、成本和平台依赖；
- 热度不等于推荐，收录不构成背书。

## 路线图

- [x] GitHub 仓库搜索与候选评分
- [x] 每日数据快照
- [x] 人工审核型日报模板
- [x] README 历史索引
- [ ] 真实 1/7/30 日 Star 增量
- [ ] Release、Issue 和 Discussion 资料包
- [ ] 重复痛点聚类与开发机会报告
- [ ] GitHub Action 检查日报中的未完成项和失效链接
- [ ] 静态站点和 RSS

## 贡献

欢迎推荐项目、修正事实、完善扫描规则或提交新的数据源。请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

[MIT](LICENSE)

