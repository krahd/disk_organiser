"""Limited synthetic provider-cost illustrations; no billing/provider access."""

from decimal import Decimal, ROUND_HALF_UP


AS_OF = "2026-10-06"


def _bytes(value):
    if type(value) is not int or value < 0 or value > 2**63 - 1:
        raise ValueError("Expected a bounded non-negative byte quantity")
    return Decimal(value)


def _money(value):
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def b2_illustration(*, average_stored_bytes, monthly_download_bytes):
    stored = _bytes(average_stored_bytes)
    downloaded = _bytes(monthly_download_bytes)
    storage = stored / Decimal(10**12) * Decimal("6.95")
    egress = max(Decimal(0), downloaded - 3 * stored) / Decimal(10**9) * Decimal("0.01")
    return {"provider": "Backblaze B2", "currency": "USD", "as_of": AS_OF,
            "billing_cycle_days_assumed": 30,
            "illustrative_only": True, "source": "https://www.backblaze.com/cloud-storage/pricing",
            "storage_usd": _money(storage), "excess_egress_usd": _money(egress),
            "storage_and_egress_subtotal_usd": _money(storage + egress),
            "assumed_billing_bytes_per_tb": 10**12, "billing_unit_verified_in_this_review": False,
            "complete_total": False,
            "notice": "Decimal TB/GB is an explicit modelling assumption; confirm the invoice contract before quoting.",
            "excluded": ["Account-level free storage allowance", "Class D transactions", "Taxes", "Contract variations",
                         "Support, software, payment fees and risk reserve", "Future retention, growth and restore traffic"]}


def wasabi_illustration(*, average_active_bytes, monthly_download_bytes, billable_deleted_byte_days_in_cycle=None):
    active = _bytes(average_active_bytes)
    downloaded = _bytes(monthly_download_bytes)
    unit = Decimal(2**40)
    storage = max(Decimal(1), active / unit) * Decimal("7.99")
    deleted = None if billable_deleted_byte_days_in_cycle is None else _bytes(billable_deleted_byte_days_in_cycle) / unit / 30 * Decimal("7.99")
    return {"provider": "Wasabi pay-as-you-go", "currency": "USD", "as_of": AS_OF,
            "billing_cycle_days_assumed": 30,
            "illustrative_only": True, "source": "https://wasabi.com/pricing/faq",
            "active_storage_with_account_minimum_usd": _money(storage),
            "timed_deleted_storage_this_cycle_usd": None if deleted is None else _money(deleted),
            "known_storage_subtotal_usd": None if deleted is None else _money(storage + deleted),
            "billing_bytes_per_tb": 2**40, "billing_unit_verified_in_this_review": True,
            "unit_source": "https://docs.wasabi.com/docs/does-wasabi-use-base-2-or-base-10-in-billing-calculations",
            "complete_total": False,
            "egress_policy_warning": downloaded > active,
            "excluded": ["Minimum object-size adjustment", "Taxes", "Contract variations", "Actual time-weighted invoice",
                         "Future early-deletion liability", "Support, software, payment fees and risk reserve"],
            "notice": "Free egress is subject to policy; excess is a suitability warning, not a zero-cost entitlement."}
