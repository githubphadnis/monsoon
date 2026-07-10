from app.services.outbound_guard import is_bot_reply_text


def test_is_bot_reply_text_task_created():
    assert is_bot_reply_text("Task #83 created: buy milk.")
    assert is_bot_reply_text("Note #5 created: ideas.")
    assert is_bot_reply_text("Saved · #90 buy pc for P3")
    assert is_bot_reply_text("Done · #90 buy pc for P3")
    assert is_bot_reply_text("Noted · #18 waiting for callback")


def test_is_bot_reply_text_chained_echo():
    assert is_bot_reply_text(
        "Task #83 created: Task #82 created: Task #81 created: todo test"
    )


def test_is_bot_reply_text_user_todo():
    assert not is_bot_reply_text("todo buy milk tomorrow")
    assert not is_bot_reply_text("help")
    assert not is_bot_reply_text("elaborate on what berberich is saying")
