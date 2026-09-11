from ninjarmy.core.tools import make_agent_tools

def test_claim_task(state_dir):
    tools, _ =  make_agent_tools("default_worker")

    result = tools["claim_task"]("src/a.py, src/b.py")

    assert result == {"success": True}

    task_board = (state_dir / "task_board.md").read_text()
    assert "default_worker | working | src/a.py, src/b.py" in task_board

def test_claim_overlap(state_dir):
    alice_tools, _ =  make_agent_tools("alice")
    bob_tools, _ =  make_agent_tools("bob")
    
    alice_tools["claim_task"]("src/shared.py")
    result = bob_tools["claim_task"]("src/shared.py")
    assert "error" in result
    assert "alice" in result['error']

def test_claim_finished(state_dir):
    alice_tools, _ =  make_agent_tools("alice")
    bob_tools, _ =  make_agent_tools("bob")
        
    assert alice_tools["claim_task"]("src/shared.py") == {"success": True}

    assert alice_tools["finish_task"]() == {"success": True}

    result = bob_tools["claim_task"]("src/shared.py")

    assert result == {"success": True}

def test_claim_double(state_dir):
    tools, _ =  make_agent_tools("default_worker")

    tools["claim_task"]("src/a.py")

    assert tools["claim_task"]("src/a.py, src/b.py") == {"success": True}
    task_board = (state_dir / "task_board.md").read_text()
    lines = [l for l in task_board.splitlines() if l.startswith("default_worker |")]
    assert len(lines) == 1

def test_not_overlapping(state_dir):
    alice_tools, _ =  make_agent_tools("alice")
    bob_tools, _ =  make_agent_tools("bob")
        
    assert alice_tools["claim_task"]("src/a.py") == {"success": True}

    result = bob_tools["claim_task"]("src/b.py")

    assert result == {"success": True}