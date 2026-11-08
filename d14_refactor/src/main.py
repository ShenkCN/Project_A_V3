import argparse
from parser import find_top_error_ip

def main():
    # 1. 设置命令行参数解析器
    parser = argparse.ArgumentParser(description="日志分析工具：找出报错最多的IP")
    parser.add_argument("--log_file", required=True, help="指定日志文件的路径")
    args = parser.parse_args()
    
    # 2. 调用我们在 parser.py 写的函数
    result = find_top_error_ip(args.log_file)
    
    # 3. 打印结果
    print(f"最猖狂的 ERROR IP 是: {result}")

if __name__ == "__main__":
    main()