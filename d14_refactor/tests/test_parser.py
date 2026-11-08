import sys
import os

# 这一步是为了让测试文件能找到上一级 src 目录里的 parser 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from parser import find_top_error_ip

def test_find_top_error_ip(tmp_path):
    # tmp_path 是 pytest 自动生成的临时文件夹
    fake_log = tmp_path / "fake.log"
    
    # 我们故意造几条日志：1.1.1.1 报错 3 次，2.2.2.2 报错 1 次
    fake_log.write_text(
        "1.1.1.1 ERROR timeout\n"
        "2.2.2.2 ERROR disk full\n"
        "1.1.1.1 ERROR memory\n"
        "1.1.1.1 ERROR network\n",
        encoding="utf-8"
    )
    
    # 调用函数，看结果对不对
    result = find_top_error_ip(str(fake_log))
    
    # 断言：期望结果必须是 ('1.1.1.1', 3)
    assert result == ('1.1.1.1', 3)