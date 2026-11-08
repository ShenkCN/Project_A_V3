import os, time
pid = os.fork()
if pid == 0:
    print("子进程准备死亡...")
    exit()
else:
    print("父进程正在睡觉，不管子进程...")
    time.sleep(300)
