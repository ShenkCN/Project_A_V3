from unittest.mock import patch, mock_open
from src.main import scan_log

def test_scan_log_file_not_found():
    result = scan_log("not_exist.log", ["ERROR"])
    assert result == []

@patch("builtins.open", new_callable=mock_open, read_data="INFO ok\nERROR failed\ntimeout error\n")
def test_scan_log_success(mock_file):
    with patch("src.main.os.path.join", return_value="fake_path"):
        result = scan_log("app.log", ["ERROR", "timeout"])
        assert len(result) == 2
        assert "ERROR failed" in result
        assert "timeout error" in result