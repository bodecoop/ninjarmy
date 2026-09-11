from ninjarmy.core.model import _clean_block, _serialize_message


# Cover claim, conflicting claim from a second agent, finish, re-claim after finish, 
# and a claim with overlapping-but-not-identical file lists.


def test_clean_block_cleans_dirty():
    # Basic block, asserts that its stripped down to nessecary values only
    block = {"type": "text", "text": "hello world", "citations": [], "parsed_output": 1}
    result = _clean_block(block)
    assert result == {"type": "text", "text": "hello world"}

def test_clean_block_cleans_valid():
    # Basic block, asserts values are left untouched
    block = {"type": "image", "source": "google"}
    result = _clean_block(block)
    assert result == block

def test_serialize_message():
    msg = {"role": "user", "content": "hello world"}
    result = _serialize_message(msg)
    assert result == msg
