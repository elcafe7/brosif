import unittest

from brosif.importers.stepbible import clean_html, part_of_speech


class StepBibleImporterTests(unittest.TestCase):
    def test_html_is_reduced_to_readable_text(self):
        self.assertEqual(
            "father\nsecond line",
            clean_html("<b>father</b><br>second&nbsp;line"),
        )

    def test_morphology_prefix_maps_to_part_of_speech(self):
        self.assertEqual("noun", part_of_speech("G:N-M"))
        self.assertEqual("verb", part_of_speech("H:V-Qal"))


if __name__ == "__main__":
    unittest.main()
