import unittest
from unittest.mock import patch

from githubhot.analysis import AnalysisError, GitHubModelsClient, normalize_analysis, parse_analysis_response, validate_analysis
from githubhot.cli import build_parser


def valid_analysis():
    return {
        "positioning": "这是一个面向开发者的本地工具，用来解决可复现报告生成问题。",
        "target_users": ["需要审查仓库的开发者。", "维护多个项目的小团队。"],
        "core_capabilities": ["读取本地项目并生成报告。", "导出便于分享的结果。"],
        "technical_analysis": ["核心流程可以在本地运行。", "当前资料显示主要使用 Python。"],
        "why_it_matters": ["从现有信息看，它降低了重复检查成本。", "近期仍有代码更新。"],
        "limitations": ["生产使用前仍需核实大型仓库性能。", "需要检查安全边界。"],
        "opportunities": ["机会假设：增加编辑器集成。", "机会假设：增加团队报告比较。"],
        "maturity": "项目已有发布记录，但 Stars 只能说明关注度，不能证明生产成熟度。",
    }


class AnalysisValidationTests(unittest.TestCase):
    def test_scan_defaults_to_bounded_analysis_concurrency(self) -> None:
        args = build_parser().parse_args(["scan"])
        self.assertEqual(args.analysis_workers, 3)
        self.assertEqual(args.enrich_workers, 5)

    def test_accepts_complete_analysis(self) -> None:
        validate_analysis(valid_analysis())

    def test_rejects_missing_or_wrong_fields(self) -> None:
        value = valid_analysis()
        value["limitations"] = "not a list"
        with self.assertRaises(AnalysisError):
            validate_analysis(value)

    def test_rejects_unsupported_absence_claim(self) -> None:
        value = valid_analysis()
        value["limitations"] = ["官方未提供贡献指南。"]
        with self.assertRaisesRegex(AnalysisError, "unsupported claim"):
            validate_analysis(value)

    def test_normalizes_string_list_fields(self) -> None:
        value = valid_analysis()
        value["target_users"] = "需要审查仓库的开发者。"
        normalized = normalize_analysis(value)
        self.assertEqual(normalized["target_users"], ["需要审查仓库的开发者。"])
        validate_analysis(normalized)

    @patch.object(GitHubModelsClient, "_complete")
    def test_client_normalizes_string_list_field(self, complete) -> None:
        value = valid_analysis()
        value["target_users"] = "需要审查仓库的开发者。"
        complete.return_value = {"choices": [{"message": {"content": __import__('json').dumps(value, ensure_ascii=False)}}]}
        result = GitHubModelsClient(token="test").analyze(__import__('tests.test_reporting', fromlist=['repo']).repo())
        self.assertEqual(result["target_users"], ["需要审查仓库的开发者。"])

    def test_parses_json_code_fence(self) -> None:
        body = {"choices": [{"message": {"content": f"```json\n{__import__('json').dumps(valid_analysis(), ensure_ascii=False)}\n```"}}]}
        self.assertEqual(parse_analysis_response(body), valid_analysis())

    def test_parses_json_surrounded_by_text(self) -> None:
        body = {"choices": [{"message": {"content": f"结果如下：\n{__import__('json').dumps(valid_analysis(), ensure_ascii=False)}\n结束"}}]}
        self.assertEqual(parse_analysis_response(body), valid_analysis())

    def test_reports_empty_content_without_leaking_reasoning(self) -> None:
        body = {"choices": [{"finish_reason": "length", "message": {"content": "", "reasoning_content": "secret"}}]}
        with self.assertRaisesRegex(AnalysisError, "finish_reason=length, reasoning_content=True"):
            parse_analysis_response(body)

    @patch.object(GitHubModelsClient, "_complete")
    def test_retries_invalid_response_once(self, complete) -> None:
        complete.side_effect = [
            {"choices": [{"message": {"content": "not json"}}]},
            {"choices": [{"message": {"content": __import__('json').dumps(valid_analysis(), ensure_ascii=False)}}]},
        ]
        client = GitHubModelsClient(token="test", max_attempts=2)
        self.assertEqual(client.analyze(__import__('tests.test_reporting', fromlist=['repo']).repo()), valid_analysis())
        self.assertEqual(complete.call_count, 2)


if __name__ == "__main__":
    unittest.main()
