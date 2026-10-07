import unittest

from update_data import parse_distribution_events


class DistributionParserTests(unittest.TestCase):
    def test_parses_flexible_table_markup_and_unit_scales(self):
        html = """
        <tr class="row"><td>2026年</td><td>2026-01-20</td><td>2026-01-21</td>
        <td> 每10份派现金 1.4300 元 </td><td>2026-01-26</td></tr>
        <tr><td>2026年</td><td>2026-02-20</td><td>2026-02-21</td>
        <td>每份派现金0.0500元</td><td>2026-02-26</td></tr>
        """
        events = parse_distribution_events(html)
        self.assertEqual(len(events), 2)
        self.assertAlmostEqual(events[0]["cash_per_unit"], 0.143)
        self.assertAlmostEqual(events[1]["cash_per_unit"], 0.05)

    def test_detects_upstream_markup_change_instead_of_silently_returning_empty(self):
        html = "<div>2026-01-21 每10份派现金1.4300元</div>"
        with self.assertRaisesRegex(ValueError, "页面结构已变化"):
            parse_distribution_events(html)

    def test_allows_a_page_with_no_cash_distribution(self):
        self.assertEqual(parse_distribution_events("<div>暂无分红记录</div>"), [])


if __name__ == "__main__":
    unittest.main()
