import pytest
from data.warapi import war_static_cache
from data.db import db

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    # Ensure tables are created for testing
    from data.db.db import setup
    setup()
    yield
    # Optionally, clean up DB after tests


def test_cache_and_retrieve_war(monkeypatch):
    # Mock war_api_client.get_war to return test data
    test_data = {
        'warId': 123,
        'warStartTime': 1690000000000,
        'resistance': 2
    }
    monkeypatch.setattr("data.warapi.war_api_client.get_war", lambda: test_data)
    result = war_static_cache.StaticWarData.cache_war()
    assert result['warId'] == 123
    cached = war_static_cache.StaticWarData.get_cached_war()
    assert cached is not None
    assert cached.war_id == 123


def test_cache_and_retrieve_maps(monkeypatch):
    test_maps = [
        {'code': 'Deadlands', 'name': 'Deadlands'},
        {'code': 'FishermansRow', 'name': 'Fisherman\'s Row'}
    ]
    monkeypatch.setattr("data.warapi.war_api_client.get_maps", lambda: test_maps)
    result = war_static_cache.StaticWarData.cache_maps()
    assert isinstance(result, list)
    cached = war_static_cache.StaticWarData.get_cached_maps()
    assert any(m.name == 'Deadlands' for m in cached)


def test_cache_and_retrieve_map_static(monkeypatch):
    map_name = 'Deadlands'
    static_data = {
        'mapTextItems': [
            {'id': 1, 'iconType': 'Factory', 'regionId': 'A', 'x': 100, 'y': 200},
            {'id': 2, 'iconType': 'Refinery', 'regionId': 'B', 'x': 150, 'y': 250}
        ]
    }
    monkeypatch.setattr("data.warapi.war_api_client.get_map_static", lambda mn: static_data)
    result = war_static_cache.StaticWarData.cache_map_static(map_name)
    assert result['mapTextItems'][0]['iconType'] == 'Factory'
    cached = war_static_cache.StaticWarData.get_cached_map_static(map_name)
    assert cached is not None
    buildings = war_static_cache.StaticWarData.get_cached_buildings(map_name)
    assert any(b.type == 'Factory' for b in buildings)
    assert any(b.type == 'Refinery' for b in buildings)

