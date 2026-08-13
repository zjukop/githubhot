import unittest

from githubhot.analysis import AnalysisError, validate_analysis


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
    def test_accepts_complete_analysis(self) -> None:
        validate_analysis(valid_analysis())

    def test_rejects_missing_or_wrong_fields(self) -> None:
        value = valid_analysis()
        value["limitations"] = "not a list"
        with self.assertRaises(AnalysisError):
            validate_analysis(value)


if __name__ == "__main__":
    unittest.main()
