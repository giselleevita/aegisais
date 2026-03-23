from app.modules.integrations.adapters_opensky import OpenSkyAdapter, OpenSkyQuotaManager


def test_opensky_maps_state_vectors_to_canonical():
    payload = {
        "time": 1710000000,
        "states": [
            [
                "abc123",
                "EZY123 ",
                "United Kingdom",
                1710000000,
                1710000001,
                10.1,
                54.2,
                11000.0,
                False,
                230.5,
                180.0,
                -1.0,
            ]
        ],
    }

    adapter = OpenSkyAdapter(fetcher=lambda _url: payload, cache_ttl_sec=0)
    rows = adapter.fetch_states()
    assert len(rows) == 1
    r = rows[0]
    assert r.provider == "opensky"
    assert r.transponder_id == "abc123"
    assert r.latitude == 54.2
    assert r.longitude == 10.1
    assert r.speed_mps == 230.5
    assert r.raw["origin_country"] == "United Kingdom"


def test_opensky_quota_blocks_after_limit():
    payload = {"time": 1710000000, "states": []}
    quota = OpenSkyQuotaManager(minute_limit=1, day_limit=10, now_fn=lambda: 1000.0)
    calls = {"n": 0}

    def _fetcher(_url: str):
        calls["n"] += 1
        return payload

    adapter = OpenSkyAdapter(fetcher=_fetcher, cache_ttl_sec=0, quota=quota)
    assert adapter.fetch_states() == []
    assert adapter.fetch_states() == []
    assert calls["n"] == 1


def test_opensky_cache_reuses_recent_payload():
    payload = {"time": 1710000000, "states": []}
    calls = {"n": 0}

    def _fetcher(_url: str):
        calls["n"] += 1
        return payload

    adapter = OpenSkyAdapter(fetcher=_fetcher, cache_ttl_sec=300)
    adapter.fetch_states()
    adapter.fetch_states()
    assert calls["n"] == 1

