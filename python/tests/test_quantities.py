from volt_trace.quantities import round_kwh, sum_kwh


def test_round_kwh_four_decimals():
    assert round_kwh(1.234567) == 1.2346


def test_sum_kwh_within_esl_tolerance():
    parts = [0.3333, 0.3333, 0.3333]
    total = sum_kwh(parts)
    assert abs(total - 1.0) < 0.001
