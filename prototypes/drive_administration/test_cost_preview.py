import unittest

from cost_preview import b2_illustration, wasabi_illustration


class CostPreviewTests(unittest.TestCase):
    def test_b2_current_rate_and_three_times_allowance(self):
        result = b2_illustration(average_stored_bytes=10**12, monthly_download_bytes=3 * 10**12)
        self.assertEqual(result["storage_and_egress_subtotal_usd"], "6.95")
        self.assertEqual(result["excess_egress_usd"], "0.00")
        self.assertFalse(result["complete_total"])
        self.assertEqual(result["billing_cycle_days_assumed"], 30)

    def test_b2_excess_download_cost(self):
        result = b2_illustration(average_stored_bytes=10**12, monthly_download_bytes=4 * 10**12)
        self.assertEqual(result["excess_egress_usd"], "10.00")
        self.assertEqual(result["storage_and_egress_subtotal_usd"], "16.95")

    def test_wasabi_minimum_for_small_account(self):
        result = wasabi_illustration(average_active_bytes=100 * 10**9, monthly_download_bytes=0)
        self.assertEqual(result["active_storage_with_account_minimum_usd"], "7.99")
        self.assertIsNone(result["known_storage_subtotal_usd"])

    def test_wasabi_deleted_storage_not_hidden(self):
        result = wasabi_illustration(average_active_bytes=2**40, monthly_download_bytes=0,
                                    billable_deleted_byte_days_in_cycle=30 * 2**40)
        self.assertEqual(result["timed_deleted_storage_this_cycle_usd"], "7.99")
        self.assertEqual(result["known_storage_subtotal_usd"], "15.98")

    def test_wasabi_download_policy_warning(self):
        result = wasabi_illustration(average_active_bytes=2**40, monthly_download_bytes=2 * 2**40,
                                    billable_deleted_byte_days_in_cycle=0)
        self.assertTrue(result["egress_policy_warning"])

    def test_units_are_explicit_and_distinct(self):
        b2 = b2_illustration(average_stored_bytes=2**40, monthly_download_bytes=0)
        wasabi = wasabi_illustration(average_active_bytes=2**40, monthly_download_bytes=0)
        self.assertEqual(b2["storage_usd"], "7.64")
        self.assertEqual(wasabi["active_storage_with_account_minimum_usd"], "7.99")
        self.assertNotEqual(b2["assumed_billing_bytes_per_tb"], wasabi["billing_bytes_per_tb"])
        self.assertFalse(b2["billing_unit_verified_in_this_review"])

    def test_negative_boolean_and_float_bytes_rejected(self):
        for value in (-1, True, 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    b2_illustration(average_stored_bytes=value, monthly_download_bytes=0)


if __name__ == "__main__":
    unittest.main()
