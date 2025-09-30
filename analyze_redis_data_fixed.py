import redis
import os
import time
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter

class RedisDataAnalyzer:
    def __init__(self, redis_url=None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.r = redis.from_url(self.redis_url)
        self.analysis_results = {}
        
    def _bytes_to_human(self, bytes_value):
        """将字节数转换为人类可读格式"""
        if bytes_value == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f}{unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f}PB"
    
    def _safe_redis_operation(self, operation, *args, **kwargs):
        """安全执行 Redis 操作，避免错误"""
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            return f"ERROR: {e}"
    
    def get_basic_info(self):
        """获取 Redis 基本信息"""
        print("📊 Redis 基本信息")
        print("=" * 50)
        
        try:
            info = self.r.info()
            
            # 基本信息
            print(f"Redis 版本: {info.get('redis_version', 'Unknown')}")
            print(f"运行模式: {info.get('redis_mode', 'standalone')}")
            print(f"运行时间: {timedelta(seconds=int(info.get('uptime_in_seconds', 0)))}")
            print(f"连接的客户端数: {info.get('connected_clients', 0)}")
            
            # 内存信息
            memory_info = self.r.info('memory')
            used_memory = memory_info.get('used_memory', 0)
            used_memory_peak = memory_info.get('used_memory_peak', 0)
            mem_fragmentation_ratio = memory_info.get('mem_fragmentation_ratio', 0)
            
            print(f"\n💾 内存使用情况:")
            print(f"  当前使用: {self._bytes_to_human(used_memory)}")
            print(f"  峰值使用: {self._bytes_to_human(used_memory_peak)}")
            print(f"  内存碎片率: {mem_fragmentation_ratio:.2f}")
            
            # 数据库信息
            db_stats = {}
            for key in info.keys():
                if key.startswith('db'):
                    db_stats[key] = info[key]
            
            print(f"\n🗄️  数据库统计:")
            for db, stats in db_stats.items():
                print(f"  {db}: {stats}")
            
            self.analysis_results['basic_info'] = {
                'version': info.get('redis_version'),
                'mode': info.get('redis_mode'),
                'used_memory': used_memory,
                'used_memory_peak': used_memory_peak,
                'mem_fragmentation_ratio': mem_fragmentation_ratio,
                'db_stats': db_stats
            }
            
        except Exception as e:
            print(f"获取基本信息时出错: {e}")
    
    def analyze_key_distribution(self):
        """分析键的分布情况"""
        print("\n🔑 键分布分析")
        print("=" * 50)
        
        try:
            # 获取所有键（限制数量以避免性能问题）
            all_keys = self.r.keys('*')
            total_keys = len(all_keys)
            
            print(f"总键数量: {total_keys}")
            
            if total_keys == 0:
                print("没有找到任何键")
                return
            
            # 按类型统计
            type_stats = Counter()
            type_memory = defaultdict(int)
            
            # 限制分析的键数量（避免性能问题）
            sample_size = min(total_keys, 1000)
            sample_keys = all_keys[:sample_size]
            
            for key in sample_keys:
                try:
                    key_type = self.r.type(key)
                    type_stats[key_type] += 1
                    
                    # 获取键的内存使用
                    memory_usage = self.r.memory_usage(key)
                    type_memory[key_type] += memory_usage
                    
                except Exception as e:
                    print(f"分析键 {key} 时出错: {e}")
            
            print(f"\n📈 键类型分布 (基于 {sample_size} 个样本):")
            for key_type, count in type_stats.most_common():
                percentage = (count / sample_size) * 100
                memory_mb = type_memory[key_type] / 1024 / 1024
                print(f"  {key_type}: {count} 个 ({percentage:.1f}%) - {self._bytes_to_human(type_memory[key_type])}")
            
            # 按前缀分析
            prefix_stats = Counter()
            for key in sample_keys:
                try:
                    # 提取键的前缀（第一个冒号之前的部分）
                    if ':' in key:
                        prefix = key.split(':')[0]
                    else:
                        prefix = 'no_prefix'
                    prefix_stats[prefix] += 1
                except:
                    continue
            
            print(f"\n🏷️  键前缀分布:")
            for prefix, count in prefix_stats.most_common(10):
                percentage = (count / sample_size) * 100
                print(f"  {prefix}: {count} 个 ({percentage:.1f}%)")
            
            self.analysis_results['key_distribution'] = {
                'total_keys': total_keys,
                'sample_size': sample_size,
                'type_stats': dict(type_stats),
                'type_memory': dict(type_memory),
                'prefix_stats': dict(prefix_stats)
            }
            
        except Exception as e:
            print(f"分析键分布时出错: {e}")
    
    def find_large_keys(self, top_n=20):
        """找出占用内存最大的键"""
        print(f"\n🔍 大键分析 (Top {top_n})")
        print("=" * 50)
        
        try:
            all_keys = self.r.keys('*')
            total_keys = len(all_keys)
            
            if total_keys == 0:
                print("没有找到任何键")
                return
            
            # 分析所有键的内存使用
            key_memory_list = []
            analyzed_count = 0
            
            print(f"正在分析 {total_keys} 个键的内存使用...")
            
            for key in all_keys:
                try:
                    memory_usage = self.r.memory_usage(key)
                    key_type = self.r.type(key)
                    
                    key_memory_list.append({
                        'key': key,
                        'type': key_type,
                        'memory': memory_usage,
                        'memory_mb': memory_usage / 1024 / 1024
                    })
                    
                    analyzed_count += 1
                    
                    # 每分析100个键显示进度
                    if analyzed_count % 100 == 0:
                        print(f"  已分析 {analyzed_count}/{total_keys} 个键...")
                    
                except Exception as e:
                    print(f"分析键 {key} 时出错: {e}")
                    continue
            
            # 按内存使用排序
            key_memory_list.sort(key=lambda x: x['memory'], reverse=True)
            
            print(f"\n📊 内存占用最大的 {top_n} 个键:")
            total_memory = sum(item['memory'] for item in key_memory_list)
            
            for i, item in enumerate(key_memory_list[:top_n], 1):
                percentage = (item['memory'] / total_memory) * 100
                print(f"  {i:2d}. {item['key']}")
                print(f"      类型: {item['type']}")
                print(f"      内存: {self._bytes_to_human(item['memory'])} ({percentage:.1f}%)")
                
                # 如果是字符串类型，显示部分内容
                if item['type'] == 'string' and item['memory'] < 1024 * 1024:  # 小于1MB
                    try:
                        value = self.r.get(item['key'])
                        if value:
                            value_str = value.decode('utf-8', errors='ignore')[:100]
                            print(f"      内容预览: {value_str}...")
                    except:
                        pass
                print()
            
            # 统计大键的类型分布
            large_key_types = Counter()
            for item in key_memory_list[:top_n]:
                large_key_types[item['type']] += 1
            
            print(f"📈 大键类型分布:")
            for key_type, count in large_key_types.most_common():
                print(f"  {key_type}: {count} 个")
            
            self.analysis_results['large_keys'] = {
                'total_analyzed': analyzed_count,
                'total_memory': total_memory,
                'top_keys': key_memory_list[:top_n],
                'large_key_types': dict(large_key_types)
            }
            
        except Exception as e:
            print(f"查找大键时出错: {e}")
    
    def analyze_key_patterns(self):
        """分析键的模式和过期时间"""
        print("\n🎯 键模式分析")
        print("=" * 50)
        
        try:
            all_keys = self.r.keys('*')
            
            if len(all_keys) == 0:
                print("没有找到任何键")
                return
            
            # 分析过期时间
            ttl_stats = {
                'no_expire': 0,
                'expired': 0,
                'short_term': 0,    # < 1小时
                'medium_term': 0,   # 1小时 - 1天
                'long_term': 0,     # > 1天
            }
            
            key_patterns = defaultdict(int)
            
            sample_size = min(len(all_keys), 500)
            sample_keys = all_keys[:sample_size]
            
            print(f"正在分析 {sample_size} 个键的模式...")
            
            for key in sample_keys:
                try:
                    # 分析 TTL
                    ttl = self.r.ttl(key)
                    if ttl == -1:
                        ttl_stats['no_expire'] += 1
                    elif ttl == -2:
                        ttl_stats['expired'] += 1
                    elif ttl < 3600:
                        ttl_stats['short_term'] += 1
                    elif ttl < 86400:
                        ttl_stats['medium_term'] += 1
                    else:
                        ttl_stats['long_term'] += 1
                    
                    # 分析键名模式
                    if ':' in key:
                        pattern = key.split(':')[0]
                        key_patterns[pattern] += 1
                    else:
                        key_patterns['simple'] += 1
                        
                except Exception as e:
                    print(f"分析键 {key} 时出错: {e}")
                    continue
            
            print(f"\n⏰ TTL 分布:")
            total_with_ttl = sum(ttl_stats.values()) - ttl_stats['expired']
            for category, count in ttl_stats.items():
                if total_with_ttl > 0:
                    percentage = (count / total_with_ttl) * 100
                else:
                    percentage = 0
                print(f"  {category}: {count} ({percentage:.1f}%)")
            
            print(f"\n🔑 键模式分布:")
            for pattern, count in Counter(key_patterns).most_common(10):
                percentage = (count / sample_size) * 100
                print(f"  {pattern}: {count} ({percentage:.1f}%)")
            
            # 分析特定模式的键
            common_patterns = ['celery', 'session', 'cache', 'vector', 'temp', 'task']
            
            print(f"\n📋 常见模式键统计:")
            for pattern in common_patterns:
                pattern_keys = [k for k in sample_keys if pattern.lower() in k.lower()]
                if pattern_keys:
                    total_memory = 0
                    for key in pattern_keys:
                        try:
                            total_memory += self.r.memory_usage(key)
                        except:
                            continue
                    
                    print(f"  {pattern}: {len(pattern_keys)} 个键, {self._bytes_to_human(total_memory)}")
            
            self.analysis_results['key_patterns'] = {
                'ttl_stats': ttl_stats,
                'key_patterns': dict(key_patterns),
                'common_patterns': {p: len([k for k in sample_keys if p.lower() in k.lower()]) for p in common_patterns}
            }
            
        except Exception as e:
            print(f"分析键模式时出错: {e}")
    
    def analyze_specific_data_types(self):
        """分析特定数据类型的详细内容"""
        print("\n📋 特定数据类型分析")
        print("=" * 50)
        
        try:
            all_keys = self.r.keys('*')
            
            if len(all_keys) == 0:
                print("没有找到任何键")
                return
            
            # 分析不同数据类型
            data_types = {
                'string': [],
                'hash': [],
                'list': [],
                'set': [],
                'zset': [],
                'none': []
            }
            
            sample_size = min(len(all_keys), 200)
            sample_keys = all_keys[:sample_size]
            
            for key in sample_keys:
                try:
                    key_type = self.r.type(key)
                    if key_type in data_types:
                        data_types[key_type].append(key)
                except Exception as e:
                    print(f"分析键 {key} 类型时出错: {e}")
                    continue
            
            # 分析字符串类型
            if data_types['string']:
                print(f"\n📝 字符串类型分析 ({len(data_types['string'])} 个键):")
                string_memory = 0
                large_strings = []
                
                for key in data_types['string'][:50]:  # 限制分析数量
                    try:
                        memory = self.r.memory_usage(key)
                        string_memory += memory
                        
                        if memory > 1024 * 1024:  # > 1MB
                            large_strings.append((key, memory))
                            
                        # 显示一些示例键的内容
                        if len(large_strings) < 5:
                            value = self.r.get(key)
                            if value:
                                value_str = value.decode('utf-8', errors='ignore')[:50]
                                print(f"  示例: {key} = {value_str}...")
                                
                    except Exception as e:
                        continue
                
                print(f"  总内存: {self._bytes_to_human(string_memory)}")
                print(f"  大字符串 (>1MB): {len(large_strings)} 个")
                
                for key, memory in large_strings[:5]:
                    print(f"    {key}: {self._bytes_to_human(memory)}")
            
            # 分析哈希类型
            if data_types['hash']:
                print(f"\n🗂️  哈希类型分析 ({len(data_types['hash'])} 个键):")
                hash_memory = 0
                large_hashes = []
                
                for key in data_types['hash'][:50]:
                    try:
                        memory = self.r.memory_usage(key)
                        hash_memory += memory
                        
                        field_count = self.r.hlen(key)
                        if memory > 1024 * 1024 or field_count > 1000:  # > 1MB 或 > 1000字段
                            large_hashes.append((key, memory, field_count))
                            
                    except Exception as e:
                        continue
                
                print(f"  总内存: {self._bytes_to_human(hash_memory)}")
                print(f"  大哈希: {len(large_hashes)} 个")
                
                for key, memory, field_count in large_hashes[:5]:
                    print(f"    {key}: {self._bytes_to_human(memory)}, {field_count} 个字段")
            
            # 分析列表类型
            if data_types['list']:
                print(f"\n📋 列表类型分析 ({len(data_types['list'])} 个键):")
                list_memory = 0
                large_lists = []
                
                for key in data_types['list'][:50]:
                    try:
                        memory = self.r.memory_usage(key)
                        list_memory += memory
                        
                        list_length = self.r.llen(key)
                        if memory > 1024 * 1024 or list_length > 1000:  # > 1MB 或 > 1000元素
                            large_lists.append((key, memory, list_length))
                            
                    except Exception as e:
                        continue
                
                print(f"  总内存: {self._bytes_to_human(list_memory)}")
                print(f"  大列表: {len(large_lists)} 个")
                
                for key, memory, list_length in large_lists[:5]:
                    print(f"    {key}: {self._bytes_to_human(memory)}, {list_length} 个元素")
            
            self.analysis_results['specific_data_types'] = {
                'type_counts': {k: len(v) for k, v in data_types.items()},
                'string_memory': string_memory if 'string_memory' in locals() else 0,
                'hash_memory': hash_memory if 'hash_memory' in locals() else 0,
                'list_memory': list_memory if 'list_memory' in locals() else 0,
                'large_strings': len(large_strings) if 'large_strings' in locals() else 0,
                'large_hashes': len(large_hashes) if 'large_hashes' in locals() else 0,
                'large_lists': len(large_lists) if 'large_lists' in locals() else 0
            }
            
        except Exception as e:
            print(f"分析特定数据类型时出错: {e}")
    
    def generate_recommendations(self):
        """基于分析结果生成优化建议"""
        print("\n💡 优化建议")
        print("=" * 50)
        
        recommendations = []
        
        # 基于基本信息的建议
        if 'basic_info' in self.analysis_results:
            basic_info = self.analysis_results['basic_info']
            
            # 内存碎片率建议
            if basic_info.get('mem_fragmentation_ratio', 0) > 1.5:
                recommendations.append({
                    'priority': 'high',
                    'category': '内存优化',
                    'issue': f'内存碎片率过高 ({basic_info["mem_fragmentation_ratio"]:.2f})',
                    'suggestion': '建议重启 Redis 或使用 MEMORY PURGE 命令清理碎片'
                })
            
            # 版本建议
            version = basic_info.get('version', '')
            if version.startswith('3.0'):
                recommendations.append({
                    'priority': 'medium',
                    'category': '版本升级',
                    'issue': f'Redis 版本过旧 ({version})',
                    'suggestion': '建议升级到 Redis 5.0 或更高版本以获得更好的性能和安全性'
                })
        
        # 基于键分布的建议
        if 'key_distribution' in self.analysis_results:
            key_dist = self.analysis_results['key_distribution']
            
            # 检查是否有过多无过期时间的键
            if 'key_patterns' in self.analysis_results:
                ttl_stats = self.analysis_results['key_patterns'].get('ttl_stats', {})
                no_expire_count = ttl_stats.get('no_expire', 0)
                total_keys = key_dist.get('total_keys', 0)
                
                if total_keys > 0 and (no_expire_count / total_keys) > 0.7:
                    recommendations.append({
                        'priority': 'high',
                        'category': '过期策略',
                        'issue': f'过多键没有设置过期时间 ({no_expire_count}/{total_keys})',
                        'suggestion': '为缓存数据设置合理的过期时间，避免内存无限增长'
                    })
        
        # 基于大键的建议
        if 'large_keys' in self.analysis_results:
            large_keys = self.analysis_results['large_keys']
            top_keys = large_keys.get('top_keys', [])
            
            if top_keys:
                # 检查是否有超大键
                for key_info in top_keys[:5]:
                    if key_info['memory_mb'] > 100:  # > 100MB
                        recommendations.append({
                            'priority': 'high',
                            'category': '大键优化',
                            'issue': f'发现超大键 {key_info["key"]} ({key_info["memory_mb"]:.1f}MB)',
                            'suggestion': '考虑拆分大键或使用数据压缩'
                        })
        
        # 基于数据类型的建议
        if 'specific_data_types' in self.analysis_results:
            data_types = self.analysis_results['specific_data_types']
            
            # 检查大字符串
            if data_types.get('large_strings', 0) > 5:
                recommendations.append({
                    'priority': 'medium',
                    'category': '数据结构优化',
                    'issue': f'发现 {data_types["large_strings"]} 个大字符串',
                    'suggestion': '考虑使用哈希或列表替代大字符串，提高内存使用效率'
                })
            
            # 检查大哈希
            if data_types.get('large_hashes', 0) > 3:
                recommendations.append({
                    'priority': 'medium',
                    'category': '数据结构优化',
                    'issue': f'发现 {data_types["large_hashes"]} 个大哈希',
                    'suggestion': '考虑拆分大哈希或使用 Redis Cluster'
                })
        
        # 通用建议
        recommendations.extend([
            {
                'priority': 'high',
                'category': '内存限制',
                'issue': '未设置 Redis 最大内存限制',
                'suggestion': '设置 maxmemory 配置，避免 Redis 占用过多系统内存'
            },
            {
                'priority': 'medium',
                'category': '监控',
                'issue': '缺乏 Redis 内存监控',
                'suggestion': '设置内存监控告警，及时发现内存异常'
            },
            {
                'priority': 'low',
                'category': '维护',
                'issue': '缺乏定期数据清理',
                'suggestion': '建立定期数据清理机制，清理过期和无用数据'
            }
        ])
        
        # 显示建议
        for i, rec in enumerate(recommendations, 1):
            priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
            print(f"{i}. {priority_icon[rec['priority']]} [{rec['category']}]")
            print(f"   问题: {rec['issue']}")
            print(f"   建议: {rec['suggestion']}")
            print()
        
        self.analysis_results['recommendations'] = recommendations
        
        return recommendations
    
    def save_analysis_report(self, filename=None):
        """保存分析报告到文件"""
        if filename is None:
            filename = f"redis_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_results, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"\n💾 分析报告已保存到: {filename}")
            return filename
            
        except Exception as e:
            print(f"保存分析报告时出错: {e}")
            return None
    
    def run_full_analysis(self):
        """运行完整的 Redis 数据分析"""
        print("🚀 Redis 数据完整分析")
        print("=" * 60)
        print(f"分析时间: {datetime.now()}")
        print(f"Redis 连接: {self.redis_url}")
        print("=" * 60)
        
        start_time = time.time()
        
        # 执行所有分析
        self.get_basic_info()
        self.analyze_key_distribution()
        self.find_large_keys()
        self.analyze_key_patterns()
        self.analyze_specific_data_types()
        self.generate_recommendations()
        
        end_time = time.time()
        analysis_duration = end_time - start_time
        
        print(f"\n⏱️  分析完成！")
        print(f"总耗时: {analysis_duration:.2f} 秒")
        print("=" * 60)
        
        # 保存报告
        report_file = self.save_analysis_report()
        
        return {
            'analysis_results': self.analysis_results,
            'duration': analysis_duration,
            'report_file': report_file
        }

def main():
    """主函数"""
    print("Redis 数据结构分析工具")
    print("=" * 60)
    
    # 创建分析器
    analyzer = RedisDataAnalyzer()
    
    try:
        # 运行完整分析
        results = analyzer.run_full_analysis()
        
        print("\n📊 分析摘要:")
        print("=" * 30)
        
        if 'analysis_results' in results:
            analysis_results = results['analysis_results']
            
            # 基本信息
            if 'basic_info' in analysis_results:
                basic_info = analysis_results['basic_info']
                print(f"Redis 版本: {basic_info.get('version', 'Unknown')}")
                print(f"内存使用: {analyzer._bytes_to_human(basic_info.get('used_memory', 0))}")
                print(f"内存碎片率: {basic_info.get('mem_fragmentation_ratio', 0):.2f}")
            
            # 键统计
            if 'key_distribution' in analysis_results:
                key_dist = analysis_results['key_distribution']
                print(f"总键数量: {key_dist.get('total_keys', 0)}")
            
            # 大键统计
            if 'large_keys' in analysis_results:
                large_keys = analysis_results['large_keys']
                top_keys = large_keys.get('top_keys', [])
                if top_keys:
                    largest_key = top_keys[0]
                    print(f"最大键: {largest_key.get('key', 'Unknown')} ({analyzer._bytes_to_human(largest_key.get('memory', 0))})")
            
            # 建议数量
            if 'recommendations' in analysis_results:
                recommendations = analysis_results['recommendations']
                high_priority = len([r for r in recommendations if r['priority'] == 'high'])
                medium_priority = len([r for r in recommendations if r['priority'] == 'medium'])
                low_priority = len([r for r in recommendations if r['priority'] == 'low'])
                
                print(f"优化建议: {high_priority} 个高优先级, {medium_priority} 个中优先级, {low_priority} 个低优先级")
        
        print(f"\n📄 详细报告已保存到: {results.get('report_file', 'Unknown')}")
        print(f"⏱️  分析耗时: {results.get('duration', 0):.2f} 秒")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  分析被用户中断")
    except Exception as e:
        print(f"\n❌ 分析过程中出错: {e}")
        print("请检查 Redis 连接是否正常")

if __name__ == "__main__":
    main()
