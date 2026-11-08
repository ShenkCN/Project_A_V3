def find_top_error_ip(file_path):
    ip_counts = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if "ERROR" in line:
                ip = line.split()[0]  # 取第一列
                ip_counts[ip] = ip_counts.get(ip, 0) + 1
    
    # 找出出现次数最多的
    if not ip_counts:
        return "没有找到 ERROR 日志"
    
    # 按次数从大到小排序，取第一个
    top_ip = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[0]
    return top_ip