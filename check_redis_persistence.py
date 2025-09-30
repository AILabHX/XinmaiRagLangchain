import redis
import os
import time
import json
from datetime import datetime

def check_redis_persistence():
    """检查 Redis 持久化配置"""
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    try:
        r = redis.from_url(REDIS_URL)
        
        print("Redis 持久化配置检查")
        print("=" * 50)
        
        # 获取 Redis 配置信息
        config = r.config_get('*')
        
        # 检查 RDB 持久化配置
        print("\n📁 RDB 持久化配置:")
        print("-" * 30)
        
        rdb_enabled = config.get('save', '')
        if rdb_enabled and rdb_enabled != '':
            print(f"✅ RDB 已启用: {rdb_enabled}")
            
            # 检查 RDB 文件路径
            rdb_path = config.get('dir', '') + config.get('dbfilename', 'dump.rdb')
            print(f"📂 RDB 文件路径: {rdb_path}")
            
            # 检查 RDB 压缩
            rdb_compression = config.get('rdbcompression', 'yes')
            print(f"🗜️  RDB 压缩: {rdb_compression}")
            
            # 检查 RDB 校验和
            rdb_checksum = config.get('rdbchecksum', 'yes')
            print(f"✅ RDB 校验和: {rdb_checksum}")
            
            # 检查 RDB 快照策略
            save_configs = rdb_enabled.split()
            for save_config in save_configs:
                if save_config.startswith('save'):
                    print(f"💾 快照策略: {save_config}")
            
        else:
            print("❌ RDB 持久化未启用")
        
        # 检查 AOF 持久化配置
        print("\n📝 AOF 持久化配置:")
        print("-" * 30)
        
        aof_enabled = config.get('appendonly', 'no')
        if aof_enabled == 'yes':
            print(f"✅ AOF 已启用")
            
            # 检查 AOF 文件路径
            aof_path = config.get('dir', '') + config.get('appendfilename', 'appendonly.aof')
            print(f"📂 AOF 文件路径: {aof_path}")
            
            # 检查 AOF 同步策略
            appendfsync = config.get('appendfsync', 'everysec')
            print(f"⚡ AOF 同步策略: {appendfsync}")
            
            # 检查 AOF 重写策略
            auto_aof_rewrite_percentage = config.get('auto-aof-rewrite-percentage', '100')
            auto_aof_rewrite_min_size = config.get('auto-aof-rewrite-min-size', '64mb')
            print(f"🔄 AOF 自动重写: {auto_aof_rewrite_percentage}% (最小: {auto_aof_rewrite_min_size})")
            
            # 检查 AOF 加载方式
            aof_load_truncated = config.get('aof-load-truncated', 'yes')
            print(f"📖 AOF 加载截断: {aof_load_truncated}")
            
        else:
            print("❌ AOF 持久化未启用")
        
        # 检查其他相关配置
        print("\n⚙️  其他相关配置:")
        print("-" * 30)
        
        # 检查最大内存策略
        maxmemory_policy = config.get('maxmemory-policy', 'noeviction')
        print(f"🧠 最大内存策略: {maxmemory_policy}")
        
        # 检查最大内存限制
        maxmemory = config.get('maxmemory', '0')
        if maxmemory == '0':
            print("💾 最大内存限制: 无限制")
        else:
            # 转换为可读格式
            try:
                maxmemory_bytes = int(maxmemory)
                if maxmemory_bytes < 1024:
                    print(f"💾 最大内存限制: {maxmemory_bytes} B")
                elif maxmemory_bytes < 1024**2:
                    print(f"💾 最大内存限制: {maxmemory_bytes/1024:.1f} KB")
                elif maxmemory_bytes < 1024**3:
                    print(f"💾 最大内存限制: {maxmemory_bytes/1024**2:.1f} MB")
                else:
                    print(f"💾 最大内存限制: {maxmemory_bytes/1024**3:.1f} GB")
            except:
                print(f"💾 最大内存限制: {maxmemory}")
        
        # 检查持久化目录
        dir_path = config.get('dir', '.')
        print(f"📁 持久化目录: {dir_path}")
        
        # 检查是否启用了慢查询日志
        slowlog_enabled = config.get('slowlog-enabled', 'yes')
        slowlog_max_len = config.get('slowlog-max-len', '128')
        slowlog_log_slower_than = config.get('slowlog-log-slower-than', '10000')
        print(f"📊 慢查询日志: {slowlog_enabled} (最大长度: {slowlog_max_len}, 阈值: {slowlog_log_slower_than}μs)")
        
        # 检查持久化状态
        print("\n📊 持久化状态:")
        print("-" * 30)
        
        # 获取最后保存时间
        try:
            lastsave = r.lastsave()
            print(f"💾 最后保存时间: {lastsave}")
            
            # 计算距离现在的时间
            time_diff = datetime.now() - lastsave
            if time_diff.total_seconds() < 60:
                print(f"⏰ 距离现在: {int(time_diff.total_seconds())} 秒")
            elif time_diff.total_seconds() < 3600:
                print(f"⏰ 距离现在: {int(time_diff.total_seconds()/60)} 分钟")
            else:
                print(f"⏰ 距离现在: {int(time_diff.total_seconds()/3600)} 小时")
        except:
            print("💾 最后保存时间: 无法获取")
        
        # 获取数据库信息
        try:
            info = r.info('persistence')
            print(f"📈 RDB 变化次数: {info.get('rdb_changes_since_last_save', 'N/A')}")
            print(f"📝 AOF 当前大小: {info.get('aof_current_size', 'N/A')} bytes")
            print(f"📝 AOF 基础大小: {info.get('aof_base_size', 'N/A')} bytes")
            print(f"📝 AOF 重写次数: {info.get('aof_rewrite_in_progress', 'N/A')}")
        except:
            print("📊 持久化详细信息获取失败")
        
        # 检查数据持久化建议
        print("\n💡 持久化建议:")
        print("-" * 30)
        
        if rdb_enabled == '' and aof_enabled == 'no':
            print("⚠️  警告: 未启用任何持久化配置！数据在重启后会丢失")
            print("建议: 启用 RDB 或 AOF 持久化")
            print("风险等级: 🔴 高风险")
        elif rdb_enabled == '' and aof_enabled == 'yes':
            print("✅ 仅使用 AOF 持久化")
            print("建议: 考虑同时启用 RDB 以获得更好的性能")
            print("风险等级: 🟡 中等风险")
        elif rdb_enabled != '' and aof_enabled == 'no':
            print("✅ 仅使用 RDB 持久化")
            print("建议: 考虑同时启用 AOF 以获得更好的数据安全性")
            print("风险等级: 🟡 中等风险")
        else:
            print("✅ 同时使用 RDB + AOF 持久化")
            print("建议: 这是最佳配置，兼顾性能和数据安全")
            print("风险等级: 🟢 低风险")
        
        # 检查 Redis 版本兼容性
        try:
            info = r.info()
            redis_version = info.get('redis_version', '3.0.504')
            print(f"\n🔍 Redis 版本: {redis_version}")
            
            if redis_version.startswith('3.0'):
                print("⚠️  注意: Redis 3.0 版本较老，建议升级到更新版本")
                print("   - 当前版本可能存在安全漏洞")
                print("   - 新版本提供更好的性能和功能")
                print("   - 建议升级到 Redis 6.0 或更高版本")
        except:
            print("🔍 Redis 版本: 无法获取")
        
        # 检查配置文件位置
        print(f"\n📄 配置文件信息:")
        print("-" * 30)
        try:
            config_file = config.get('configfile', 'unknown')
            print(f"📄 配置文件路径: {config_file}")
        except:
            print("📄 配置文件路径: 无法获取")
        
        # 检查运行模式
        try:
            info = r.info()
            redis_mode = info.get('redis_mode', 'standalone')
            print(f"🏃 运行模式: {redis_mode}")
            
            if redis_mode == 'cluster':
                print("⚠️  集群模式检测到，持久化配置可能需要特殊处理")
        except:
            print("🏃 运行模式: 无法获取")
        
    except Exception as e:
        print(f"检查 Redis 持久化配置时出错: {e}")
        print("请确保 Redis 服务正在运行，并且网络连接正常")

def test_persistence():
    """测试持久化功能"""
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    try:
        r = redis.from_url(REDIS_URL)
        
        print("\n🧪 测试持久化功能:")
        print("-" * 30)
        
        # 设置测试键值
        test_key = "persistence_test_key"
        test_value = f"test_value_{int(time.time())}"
        
        print(f"设置测试键: {test_key} = {test_value}")
        result = r.set(test_key, test_value)
        print(f"设置结果: {result}")
        
        # 手动触发保存
        print("手动触发保存...")
        save_result = r.save()
        print(f"保存结果: {save_result}")
        
        # 等待一下
        time.sleep(2)
        
        # 验证数据是否存在
        retrieved_value = r.get(test_key)
        if retrieved_value and retrieved_value.decode() == test_value:
            print("✅ 持久化测试成功 - 数据保存和读取正常")
        else:
            print("❌ 持久化测试失败 - 数据读取异常")
        
        # 测试 BGSAVE（后台保存）
        print("\n测试后台保存 (BGSAVE)...")
        try:
            bgsave_result = r.bgsave()
            print(f"BGSAVE 结果: {bgsave_result}")
            
            # 等待 BGSAVE 完成
            time.sleep(3)
            
            # 检查 BGSAVE 状态
            info = r.info('persistence')
            if info.get('rdb_bgsave_in_progress', 0) == 0:
                print("✅ BGSAVE 完成")
            else:
                print("⚠️  BGSAVE 仍在进行中")
                
        except Exception as e:
            print(f"BGSAVE 测试失败: {e}")
        
        # 测试 AOF 重写（如果启用）
        try:
            aof_enabled = r.config_get('appendonly').get('appendonly', 'no')
            if aof_enabled == 'yes':
                print("\n测试 AOF 重写...")
                bgrewriteaof_result = r.bgrewriteaof()
                print(f"BGREWRITEAOF 结果: {bgrewriteaof_result}")
                print("✅ AOF 重写命令已发送")
            else:
                print("\n跳过 AOF 重写测试（AOF 未启用）")
        except Exception as e:
            print(f"AOF 重写测试失败: {e}")
        
        # 清理测试数据
        delete_result = r.delete(test_key)
        print(f"\n🧹 清理测试数据: {delete_result} 个键已删除")
        
    except Exception as e:
        print(f"测试持久化功能时出错: {e}")

def check_memory_usage():
    """检查 Redis 内存使用情况"""
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    try:
        r = redis.from_url(REDIS_URL)
        
        print("\n🧠 Redis 内存使用情况:")
        print("-" * 30)
        
        # 获取内存信息
        info = r.info('memory')
        
        used_memory = info.get('used_memory', 0)
        used_memory_human = _bytes_to_human(used_memory)
        used_memory_peak = info.get('used_memory_peak', 0)
        used_memory_peak_human = _bytes_to_human(used_memory_peak)
        used_memory_lua = info.get('used_memory_lua', 0)
        used_memory_lua_human = _bytes_to_human(used_memory_lua)
        
        print(f"当前内存使用: {used_memory_human}")
        print(f"内存使用峰值: {used_memory_peak_human}")
        print(f"Lua 脚本内存: {used_memory_lua_human}")
        
        # 内存碎片率
        mem_fragmentation_ratio = info.get('mem_fragmentation_ratio', 0)
        print(f"内存碎片率: {mem_fragmentation_ratio:.2f}")
        
        if mem_fragmentation_ratio > 1.5:
            print("⚠️  内存碎片率过高，建议重启 Redis 或使用 MEMORY PURGE")
        
        # 内存分配器
        mem_allocator = info.get('mem_allocator', 'unknown')
        print(f"内存分配器: {mem_allocator}")
        
        # 键的数量
        db_size = r.dbsize()
        print(f"键的数量: {db_size}")
        
        # 平均每个键的内存使用
        if db_size > 0:
            avg_key_size = used_memory / db_size
            print(f"平均每个键内存: {_bytes_to_human(avg_key_size)}")
        
        # 检查大键
        print("\n🔍 检查大键:")
        try:
            # 获取所有键的信息
            all_keys = r.keys('*')
            if len(all_keys) > 0:
                # 按大小排序前10个键
                key_sizes = []
                for key in all_keys[:100]:  # 限制检查数量
                    try:
                        key_size = r.memory_usage(key)
                        key_sizes.append((key, key_size))
                    except:
                        continue
                
                key_sizes.sort(key=lambda x: x[1], reverse=True)
                
                print("最大的 5 个键:")
                for i, (key, size) in enumerate(key_sizes[:5]):
                    print(f"  {i+1}. {key}: {_bytes_to_human(size)}")
            else:
                print("没有找到键")
        except Exception as e:
            print(f"检查大键时出错: {e}")
        
    except Exception as e:
        print(f"检查内存使用情况时出错: {e}")

def _bytes_to_human(bytes_value):
    """将字节数转换为人类可读格式"""
    if bytes_value == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f}{unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f}PB"

def main():
    """主函数"""
    print("Redis 持久化配置检查工具")
    print("=" * 60)
    print(f"检查时间: {datetime.now()}")
    print("=" * 60)
    
    # 检查持久化配置
    check_redis_persistence()
    
    # 检查内存使用情况
    check_memory_usage()
    
    # 测试持久化功能
    test_persistence()
    
    print("\n" + "=" * 60)
    print("检查完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
