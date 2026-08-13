# Contributing to GitHubHot

感谢你帮助 GitHubHot 提高信息质量。

## 推荐项目

请创建 Issue，并说明：

- 仓库地址；
- 它解决的具体问题；
- 最近受到关注的可验证证据；
- 你与项目是否存在关联。

Star 数不是收录的唯一标准。自荐完全允许，但必须披露关系。

## 提交日报

1. 运行扫描并从候选中人工选择项目；
2. 使用 `python -m githubhot draft owner/repo` 生成草稿；
3. 阅读官方仓库、文档、Release 和相关 Issues；
4. 实际验证所列安装命令；
5. 删除所有 `TODO`；
6. 运行测试和 `python -m githubhot index`；
7. 提交 Pull Request，并披露与项目的关系。

文章不得复制大段上游 README，也不得把推测写成事实。

## 修改代码

保持改动小而明确。新增评分规则时必须：

- 说明数据来源；
- 解释它衡量的是热度、活跃度还是质量；
- 添加确定性测试；
- 避免把单一指标包装成成功预测。

运行测试：

```bash
python -m unittest discover -s tests -v
```

## 本地生成日报

需要一个可读取公开仓库的 GitHub Token。启用中文深度分析时还需要 OpenAI-compatible API：

```bash
export GITHUB_TOKEN="your-token"
export ANALYSIS_API_KEY="your-model-api-key"
export ANALYSIS_MODEL="gpt-4.1-mini"
# 可选：export ANALYSIS_BASE_URL="https://your-provider.example/v1/chat/completions"
python -m githubhot scan --days 30 --min-stars 100 --limit 50 --enrich 10 --analyze 10
python -m githubhot digest --top 10
```

GitHub Actions 中将模型密钥保存为 `ANALYSIS_API_KEY` Secret；可选设置 `ANALYSIS_BASE_URL` 和 `ANALYSIS_MODEL` Variables。未配置密钥时，日报会降级为官方 README 事实资料版，不会发布伪造的深度分析。
