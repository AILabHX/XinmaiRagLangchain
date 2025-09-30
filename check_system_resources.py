import psutil
import time
import os
import threading
from datetime import datetime

def monitor_system_resources(duration=60, interval=5):
    """
    监控系统资源使用情况
    :param duration: 监控时长（秒）
    :param interval: 采样间隔（秒）
    """
    print(f"开始监控系统资源，持续 {duration} 秒...")
    print("=" * 60)
    
    start_time = time.time()
    end_time = start_time + duration
    
    while time.time() < end_time:
        try:
            # 获取 CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 获取内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used / (1024**3)  # GB
            memory_total = memory.total / (1024**3)  # GB
            
            # 获取磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used = disk.used / (1024**3)  # GB
            disk_total = disk.total / (1024**3)  # GB
            
            # 获取网络信息
            network = psutil.net_io_counters()
            
            # 打印当前状态
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"[{current_time}]")
            print(f"  CPU 使用率: {cpu_percent:.1f}%")
            print(f"  内存使用率: {memory_percent:.1f}% ({memory_used:.1f}GB/{memory_total:.1f}GB)")
            print(f"  磁盘使用率: {disk_percent:.1f}% ({disk_used:.1f}GB/{disk_total:.1f}GB)")
            print(f"  网络发送: {network.bytes_sent/1024/1024:.1f}MB")
            print(f"  网络接收: {network.bytes_recv/1024/1024:.1f}MB")
            print("-" * 40)
            
            # 检查是否有资源耗尽风险
            if cpu_percent > 90:
                print(f"⚠️  警告: CPU 使用率过高 ({cpu_percent:.1f}%)")
            if memory_percent > 90:
                print(f"⚠️  警告: 内存使用率过高 ({memory_percent:.1f}%)")
            if disk_percent > 90:
                print(f"⚠️  警告: 磁盘使用率过高 ({disk_percent:.1f}%)")
            
            time.sleep(interval - 1)  # 减去CPU测量的1秒
            
        except Exception as e:
            print(f"监控出错: {e}")
            time.sleep(interval)
    
    print("监控完成！")

def check_redis_process():
    """检查 Redis 进程资源使用情况"""
    print("\n检查 Redis 进程...")
    print("=" * 40)
    
    redis_found = False
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
        try:
            if 'redis' in proc.info['name'].lower():
                redis_found = True
                print(f"Redis 进程信息:")
                print(f"  PID: {proc.info['pid']}")
                print(f"  名称: {proc.info['name']}")
                print(f"  CPU 使用率: {proc.info['cpu_percent']:.1f}%")
                print(f"  内存使用率: {proc.info['memory_percent']:.1f}%")
                print(f"  内存使用: {proc.info['memory_info'].rss/1024/1024:.1f}MB")
                
                # 检查进程状态
                if proc.info['cpu_percent'] > 80:
                    print(f"⚠️  警告: Redis CPU 使用率过高")
                if proc.info['memory_percent'] > 80:
                    print(f"⚠️  警告: Redis 内存使用率过高")
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    if not redis_found:
        print("未找到 Redis 进程")

def check_system_info():
    """检查系统基本信息"""
    print("\n系统基本信息:")
    print("=" * 40)
    
    # 系统信息
    print(f"操作系统: {os.name}")
    
    # Windows 兼容的系统信息
    try:
        import platform
        print(f"平台: {platform.system()} {platform.release()}")
        print(f"架构: {platform.machine()}")
        print(f"版本: {platform.version()}")
        print(f"处理器: {platform.processor()}")
    except Exception as e:
        print(f"平台信息获取失败: {e}")
    
    print(f"处理器数量: {psutil.cpu_count()}")
    print(f"逻辑处理器: {psutil.cpu_count(logical=True)}")
    
    # 启动时间
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    print(f"系统启动时间: {boot_time}")
    
    # 当前时间
    print(f"当前时间: {datetime.now()}")

def check_memory_details():
    """检查详细内存信息"""
    print("\n详细内存信息:")
    print("=" * 40)
    
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    print(f"总内存: {memory.total / (1024**3):.2f} GB")
    print(f"可用内存: {memory.available / (1024**3):.2f} GB")
    print(f"已用内存: {memory.used / (1024**3):.2f} GB")
    print(f"内存使用率: {memory.percent:.1f}%")
    
    # Windows 兼容的内存信息
    try:
        if hasattr(memory, 'active'):
            print(f"活跃内存: {memory.active / (1024**3):.2f} GB")
        if hasattr(memory, 'inactive'):
            print(f"非活跃内存: {memory.inactive / (1024**3):.2f} GB")
        if hasattr(memory, 'cached'):
            print(f"缓存: {memory.cached / (1024**3):.2f} GB")
        if hasattr(memory, 'buffers'):
            print(f"缓冲区: {memory.buffers / (1024**3):.2f} GB")
    except Exception as e:
        print(f"详细内存信息获取失败: {e}")
    
    print(f"\n交换内存:")
    print(f"总交换内存: {swap.total / (1024**3):.2f} GB")
    print(f"已用交换内存: {swap.used / (1024**3):.2f} GB")
    print(f"交换内存使用率: {swap.percent:.1f}%")

def check_disk_details():
    """检查详细磁盘信息"""
    print("\n详细磁盘信息:")
    print("=" * 40)
    
    # 获取所有磁盘分区
    disk_partitions = psutil.disk_partitions()
    
    for partition in disk_partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            print(f"\n磁盘: {partition.device}")
            print(f"  挂载点: {partition.mountpoint}")
            print(f"  文件系统: {partition.fstype}")
            print(f"  总空间: {usage.total / (1024**3):.2f} GB")
            print(f"  已用空间: {usage.used / (1024**3):.2f} GB")
            print(f"  可用空间: {usage.free / (1024**3):.2f} GB")
            print(f"  使用率: {usage.percent:.1f}%")
            
            if usage.percent > 90:
                print(f"  ⚠️  警告: 磁盘使用率过高")
                
        except PermissionError:
            print(f"  权限不足，无法访问 {partition.mountpoint}")
        except Exception as e:
            print(f"  检查磁盘 {partition.device} 时出错: {e}")

def check_network_details():
    """检查详细网络信息"""
    print("\n详细网络信息:")
    print("=" * 40)
    
    # 网络IO统计
    net_io = psutil.net_io_counters()
    print(f"网络IO统计:")
    print(f"  发送字节: {net_io.bytes_sent / (1024**2):.2f} MB")
    print(f"  接收字节: {net_io.bytes_recv / (1024**2):.2f} MB")
    print(f"  发送包数: {net_io.packets_sent}")
    print(f"  接收包数: {net_io.packets_recv}")
    print(f"  发送错误: {net_io.errin}")
    print(f"  接收错误: {net_io.errout}")
    print(f"  发送丢弃: {net_io.dropin}")
    print(f"  接收丢弃: {net_io.dropout}")
    
    # 网络接口
    print(f"\n网络接口:")
    net_if_addrs = psutil.net_if_addrs()
    for interface_name, interface_addresses in net_if_addrs.items():
        print(f"  {interface_name}:")
        for address in interface_addresses:
            if address.family == socket.AF_INET:
                print(f"    IPv4: {address.address}")
            elif address.family == socket.AF_INET6:
                print(f"    IPv6: {address.address}")

def check_process_details():
    """检查进程详细信息"""
    print("\n进程详细信息:")
    print("=" * 40)
    
    # 获取CPU使用率最高的进程
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    # 按CPU使用率排序
    cpu_top = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:5]
    
    print(f"CPU使用率最高的5个进程:")
    for proc in cpu_top:
        if proc['cpu_percent'] is not None:
            print(f"  {proc['name']} (PID: {proc['pid']}) - CPU: {proc['cpu_percent']:.1f}%")
    
    # 按内存使用率排序
    memory_top = sorted(processes, key=lambda x: x['memory_percent'] or 0, reverse=True)[:5]
    
    print(f"\n内存使用率最高的5个进程:")
    for proc in memory_top:
        if proc['memory_percent'] is not None:
            print(f"  {proc['name']} (PID: {proc['pid']}) - 内存: {proc['memory_percent']:.1f}%")

def main():
    """主函数"""
    print("系统资源监控工具")
    print("=" * 60)
    
    # 检查系统基本信息
    check_system_info()
    
    # 检查Redis进程
    check_redis_process()
    
    # 检查详细内存信息
    check_memory_details()
    
    # 检查详细磁盘信息
    check_disk_details()
    
    # 检查详细网络信息
    check_network_details()
    
    # 检查进程详细信息
    check_process_details()
    
    # 开始持续监控
    print(f"\n开始持续监控（按 Ctrl+C 停止）...")
    try:
        monitor_system_resources(duration=300, interval=5)  # 监控5分钟
    except KeyboardInterrupt:
        print("\n监控已停止")

if __name__ == "__main__":
    import socket  # 导入socket模块用于网络地址检查
    main()
