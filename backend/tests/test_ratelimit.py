from app.ratelimit import RateLimiter


def test_per_minute_cap_blocks_and_messages():
    rl = RateLimiter(per_minute=2, per_day=100)
    assert rl.check("1.2.3.4")[0] is True
    assert rl.check("1.2.3.4")[0] is True
    allowed, message = rl.check("1.2.3.4")
    assert allowed is False
    assert message


def test_separate_ips_are_independent():
    rl = RateLimiter(per_minute=1, per_day=100)
    assert rl.check("a")[0] is True
    assert rl.check("b")[0] is True  # different IP not affected
    assert rl.check("a")[0] is False


def test_daily_cap():
    rl = RateLimiter(per_minute=1000, per_day=3)
    for _ in range(3):
        assert rl.check("ip")[0] is True
    assert rl.check("ip")[0] is False
