import pytest

from app.services.ai_engine import get_mock_response, mock_states


@pytest.fixture(autouse=True)
def clear_mock_state():
    mock_states.clear()
    yield
    mock_states.clear()


@pytest.mark.asyncio
async def test_schedule_then_skin_moves_to_intake_collection():
    session_id = "test_schedule_skin"

    first_reply, _ = await get_mock_response("I would like to schedule an appointment", session_id)
    assert "what you'd like to be seen for" in first_reply.lower()

    second_reply, _ = await get_mock_response("skin", session_id)
    assert "dermatology" in second_reply.lower()
    assert "full name" in second_reply.lower()
    assert "date of birth" in second_reply.lower()


@pytest.mark.asyncio
async def test_scheduling_intent_restarts_flow_from_terminal_stage():
    session_id = "test_schedule_restart"

    # Seed a completed stage to simulate an old conversation context.
    state_reply, _ = await get_mock_response("hello", session_id)
    assert "welcome" in state_reply.lower()
    mock_states[session_id].stage = "booked"

    reply, _ = await get_mock_response("I want to book an appointment", session_id)
    assert "what you'd like to be seen for" in reply.lower()


@pytest.mark.asyncio
async def test_specialty_message_does_not_fall_back_to_generic_help():
    session_id = "test_no_generic_loop"

    reply, _ = await get_mock_response("skin", session_id)
    assert "i'm here to help! i can assist you with" not in reply.lower()
    assert "dermatology" in reply.lower()

