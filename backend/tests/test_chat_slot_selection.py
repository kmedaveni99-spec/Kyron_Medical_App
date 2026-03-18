from app.routes.chat import _extract_selected_slot_id


def test_extract_selected_slot_id_from_explicit_slot_id():
    slots = [
        {"id": 101, "display_date": "Thursday, March 19 at 01:00 PM"},
        {"id": 102, "display_date": "Thursday, March 19 at 01:30 PM"},
    ]

    selected = _extract_selected_slot_id("I'll take slot ID: 102", slots)
    assert selected == 102


def test_extract_selected_slot_id_from_display_date_text():
    slots = [
        {"id": 201, "display_date": "Thursday, March 19 at 01:30 PM"},
    ]

    selected = _extract_selected_slot_id("I'll take the Thursday, March 19 at 01:30 PM slot", slots)
    assert selected == 201

