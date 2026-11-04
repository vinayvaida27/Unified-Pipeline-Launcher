import json

from launcher.app_registry import set_app_archived


def test_set_app_archived_updates_only_requested_app(tmp_path):
    registry = tmp_path / "apps.json"
    registry.write_text(
        json.dumps({"applications": [{"id": "one"}, {"id": "two"}]}),
        encoding="utf-8",
    )

    set_app_archived(registry, "two", True)

    data = json.loads(registry.read_text(encoding="utf-8"))
    assert data["applications"] == [{"id": "one"}, {"id": "two", "archived": True}]
