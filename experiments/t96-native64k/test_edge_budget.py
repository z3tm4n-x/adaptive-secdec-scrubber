"""Regression of the two-edge correction against the published routed reports."""
import re
import unittest
from decimal import Decimal as D
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from check_route import check


def worst_field(reports, pattern):
    values = [D(v) for report in reports for v in re.findall(pattern, report, re.MULTILINE)]
    return max(values)


class EdgeBudgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Read the actual path reports of this routed RTL revision.
        tmp = TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.sta = Path(tmp.name) / "sta"
        evidence = Path(__file__).with_name("results") / "evidence.zip"
        with ZipFile(evidence) as archive:
            for entry in archive.namelist():
                if entry.startswith("sta/"):
                    archive.extract(entry, tmp.name)
        cls.current = check(cls.sta)

    def test_worst_read_from_original_path_reports(self):
        inputs = [p.read_text(encoding="utf-8") for p in self.sta.glob("clocked_input_*.rpt")]
        outputs = [p.read_text(encoding="utf-8") for p in self.sta.glob("clocked_*.rpt")
                   if not p.name.startswith("clocked_input_")]
        self.assertEqual((len(inputs), len(outputs)), (4, 12))
        data_path = r"^\s*Data Path Delay:\s+(-?[\d.]+)ns"
        rounding = D(".001")
        arrival = worst_field(outputs, data_path) + rounding
        capture = worst_field(inputs, data_path) + rounding
        setup = worst_field(inputs, r"\(Setup_\w+\)\s+-(\d+\.\d+)") + rounding
        sta_uncertainty = worst_field(inputs + outputs, r"Clock Uncertainty:\s+([\d.]+)ns") + rounding
        leaves = [D(v) for reports, label in ((inputs, r"Destination Clock Delay \(DCD\)"),
                                              (outputs, r"Source Clock Delay\s+\(SCD\)"))
                  for report in reports for v in re.findall(label + r":\s+(-?[\d.]+)ns", report)]
        clock_spread = max(leaves) - min(leaves) + 2 * rounding
        # Pick the actual worst pair of signed calendar errors, separately
        # from the two physical flights through the FMC adapter.
        launch, sample = D(".5"), 60 * D(".99999") - D(".5")
        margin = sample - launch - clock_spread - arrival - D(".5") - D(".5") \
                 - capture - setup - sta_uncertainty - 45
        self.assertEqual(margin, D("5.18440"))
        self.assertEqual(min(map(D, self.current["external_margin_ns"].values())), margin)
        self.assertEqual(D(self.current["external_margin_ns"]["address_CE_ERR_read_access_45"]), margin)

    def test_every_distinct_edge_interval_pays_both_displacements(self):
        original = check(self.sta, edge_ns=D(0))["external_margin_ns"]
        self.assertEqual(len(original), 14)
        self.assertEqual(D(original["address_CE_ERR_read_access_45"]), D("6.18440"))
        for name, old in original.items():
            with self.subTest(interval=name):
                self.assertEqual(D(self.current["external_margin_ns"][name]), D(old) - 2*D(".5"))

    def test_source_condition_and_internal_clock_row_are_separate(self):
        self.assertEqual(self.current["wns_ns"], "0.064")
        model = self.current["internal_sta_model"]
        timing=(self.sta/"timing.rpt").read_text()
        row=re.search(r"^[ \t]*clk_i\s+([.\d-]+)\s+[.\d-]+\s+\d+\s+\d+\s+([.\d-]+)",timing,re.M)
        self.assertIsNotNone(row)
        self.assertEqual((model["wns_ns"], model["whs_ns"]),row.groups())
        self.assertGreater(min(map(D,row.groups())),0)
        self.assertEqual((D(model["user_setup_uncertainty_ns"]), D(model["user_hold_uncertainty_ns"])),
                         (D(".500"), D(".100")))


if __name__ == "__main__":
    unittest.main()
