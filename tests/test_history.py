from ninjarmy.core.model import save_history, load_history

def test_save_load_history(state_dir):
    history = [{"role": "user", "content": "hello world"}]
    save_history("proj", history)

    assert load_history("proj") == history

def test_load__false_history(state_dir):
    history = [{"role": "user", "content": "hello world"}]
    save_history("proj", history)

    assert load_history("computer") == None