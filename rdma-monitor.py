#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import re
import json
import sys
import time
from datetime import datetime
from prettytable import PrettyTable

def run_command(cmd):
    """执行命令并返回输出"""
    try:
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"命令执行失败: {cmd}")
            print(f"错误: {result.stderr}")
            return None
        return result.stdout
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return None

def parse_rdma_links():
    """解析rdma link show命令输出，获取LID和端口信息，过滤掉以太网设备"""
    rdma_links = []
    output = run_command("rdma link show")
    
    if not output:
        return []
    
    # 解析每一行
    for line in output.strip().split('\n'):
        # 检查是否是有效的链路信息行
        if line.startswith('link '):
            # 提取设备/端口标识符 (如 mlx5_0/1)
            dev_port_match = re.search(r'link ([a-zA-Z0-9_]+)/(\d+)', line)
            if not dev_port_match:
                continue
                
            device = dev_port_match.group(1)
            port = dev_port_match.group(2)
            
            # 检查是否是以太网设备（有netdev字段）
            if 'netdev' in line:
                continue  # 跳过以太网设备
                
            # 提取LID
            lid_match = re.search(r'lid (\d+)', line)
            if not lid_match:
                continue  # 跳过没有LID的设备
                
            lid = lid_match.group(1)
            lid_hex = f"0x{int(lid):x}"
            
            # 提取状态
            state_match = re.search(r'state ([A-Z_]+)', line)
            state = state_match.group(1) if state_match else "UNKNOWN"
            
            # 提取物理状态
            phys_state_match = re.search(r'physical_state ([A-Z_]+)', line)
            phys_state = phys_state_match.group(1) if phys_state_match else "UNKNOWN"
            
            # 提取子网前缀
            subnet_match = re.search(r'subnet_prefix ([0-9a-fA-F:]+)', line)
            subnet = subnet_match.group(1) if subnet_match else ""
            
            # 提取SM LID
            sm_lid_match = re.search(r'sm_lid (\d+)', line)
            sm_lid = sm_lid_match.group(1) if sm_lid_match else ""
            
            # 添加到结果列表
            rdma_links.append({
                'device': device,
                'port': port,
                'lid': lid,
                'lid_hex': lid_hex,
                'state': state,
                'physical_state': phys_state,
                'subnet_prefix': subnet,
                'sm_lid': sm_lid
            })
    
    return rdma_links

def get_port_performance(device, port, lid):
    """使用perfquery命令获取端口性能计数器"""
    perf_data = {}
    
    # 执行perfquery命令获取性能计数器
    cmd = f"perfquery -x {lid} {port}"
    output = run_command(cmd)
    
    if not output:
        print(f"无法获取设备 {device} 端口 {port} 的性能数据")
        return perf_data
    
    # 解析perfquery输出
    for line in output.strip().split('\n'):
        if ':' in line:
            parts = line.split(':')
            if len(parts) == 2:
                counter_name = parts[0].strip()
                counter_value = parts[1].strip()
                # 尝试将计数器值转换为整数
                try:
                    # 提取数字部分
                    num_match = re.search(r'(\d+)$', counter_value)
                    if num_match:
                        counter_value = int(num_match.group(1))
                    else:
                        counter_value = 0
                except ValueError:
                    # 如果无法转换为整数，保留为字符串但记录警告
                    print(f"警告: 无法将 {counter_name} 的值 '{counter_value}' 转换为整数")
                    counter_value = 0
                perf_data[counter_name] = counter_value
    
    return perf_data

def calculate_rates(current_data, previous_data, interval):
    """计算两次采集之间的速率"""
    if not previous_data:
        return {}
    
    rates = {}
    
    # 需要计算速率的计数器列表
    rate_counters = [
        'PortXmitData', 'PortRcvData', 
        'PortXmitPkts', 'PortRcvPkts'
    ]
    
    for counter in rate_counters:
        if counter in current_data and counter in previous_data:
            # 确保两个值都是数字类型
            if isinstance(current_data[counter], str):
                try:
                    current_value = int(current_data[counter])
                except ValueError:
                    print(f"警告: 跳过 {counter} 速率计算 - 当前值不是有效数字")
                    continue
            else:
                current_value = current_data[counter]
                
            if isinstance(previous_data[counter], str):
                try:
                    previous_value = int(previous_data[counter])
                except ValueError:
                    print(f"警告: 跳过 {counter} 速率计算 - 上一次值不是有效数字")
                    continue
            else:
                previous_value = previous_data[counter]
            
            # 计算差值
            diff = current_value - previous_value
            # 防止计数器溢出或重置导致的负值
            if diff < 0:
                diff = current_value
            
            # 根据计数器类型计算对应的速率
            if counter in ['PortXmitData', 'PortRcvData']:
                # 数据量单位为四字节，转换为字节并计算每秒速率
                rate_value = (diff * 4) / interval
                # 转换为更友好的单位（MB/s）
                rates[f"{counter}Rate"] = rate_value / (1024 * 1024)
            else:
                # 包数量直接计算每秒速率
                rates[f"{counter}Rate"] = diff / interval
    
    return rates

def format_data_rate(value):
    """将数据速率格式化为易读形式"""
    if value is None:
        return "N/A"
    
    if value < 1:
        return f"{value*1024:.2f} KB/s"
    elif value < 1024:
        return f"{value:.2f} MB/s"
    else:
        return f"{value/1024:.2f} GB/s"

def format_packet_rate(value):
    """将包速率格式化为易读形式"""
    if value is None:
        return "N/A"
    
    if value < 1000:
        return f"{value:.2f} pkt/s"
    elif value < 1000000:
        return f"{value/1000:.2f} Kpkt/s"
    else:
        return f"{value/1000000:.2f} Mpkt/s"

def monitor_performance_continuously(rdma_links, interval=5, count=None, output_file=None):
    """持续监控RDMA设备性能并计算速率"""
    all_data = []
    previous_perf_data = {}  # 存储上一次的性能数据，用于计算速率
    current_iteration = 0
    
    # 记录连接超时的设备，避免重复尝试
    timed_out_devices = set()
    
    # 创建一个表格，将在整个监控过程中重复使用
    table = PrettyTable()
    table.field_names = ["设备", "端口", "发送速率", "接收速率", "发送包速率", "接收包速率", "丢包数", "错误数"]
    
    # 清屏函数
    def clear_screen():
        try:
            # 尝试使用os.system方法
            import os
            os.system('cls' if os.name == 'nt' else 'clear')
        except:
            # 回退到ANSI转义序列
            print("\033[H\033[J", end="")
    
    # 首次数据收集时的提示
    if current_iteration == 0:
        print(f"\n开始性能监控 (间隔: {interval}秒, {'持续运行' if count is None else f'次数: {count}'})")
        print("正在进行首次数据采集，请等待...")
    
    try:
        while count is None or current_iteration < count:
            if current_iteration > 0:
                time.sleep(interval)
                # 清屏以便更新表格
                clear_screen()
            
            timestamp = datetime.now().isoformat()
            current_data = {
                'timestamp': timestamp,
                'devices': []
            }
            
            # 如果不是第一次迭代，清空表格行以准备更新
            if current_iteration > 0:
                table.clear_rows()
            
            # 首先采集所有设备的数据
            if current_iteration == 0:
                print("\n采集初始性能数据...")
            
            device_perf_data = {}  # 存储所有设备的性能数据
            active_devices = 0  # 跟踪活跃设备数量
            
            for link in rdma_links:
                device = link['device']
                port = link['port']
                lid = link['lid']
                device_key = f"{device}_{port}"
                
                # 跳过之前已超时的设备
                if device_key in timed_out_devices:
                    if current_iteration == 0:
                        print(f"跳过已知超时设备 {device} 端口 {port}")
                    continue
                
                # 使用try-except捕获可能的错误
                try:
                    if current_iteration == 0:
                        print(f"采集 {device} 端口 {port} 的初始性能数据...")
                    
                    perf_data = get_port_performance(device, port, lid)
                    
                    if not perf_data:
                        print(f"设备 {device} 端口 {port} 未返回性能数据，可能连接超时")
                        timed_out_devices.add(device_key)
                        continue
                    
                    # 存储性能数据
                    device_perf_data[device_key] = {
                        'link': link,
                        'perf_data': perf_data
                    }
                    active_devices += 1
                    
                except Exception as e:
                    print(f"处理设备 {device} 端口 {port} 时出现未预期错误: {e}")
                    continue
            
            # 然后计算速率并添加到表格中
            for device_key, data in device_perf_data.items():
                link = data['link']
                perf_data = data['perf_data']
                device = link['device']
                port = link['port']
                
                # 计算速率
                rates = {}
                if current_iteration > 0 and device_key in previous_perf_data:
                    try:
                        rates = calculate_rates(perf_data, previous_perf_data[device_key], interval)
                    except Exception as e:
                        print(f"计算设备 {device} 端口 {port} 的速率时出错: {e}")
                        continue
                
                # 更新上一次的性能数据
                previous_perf_data[device_key] = perf_data
                
                # 添加到当前数据
                device_data = link.copy()
                device_data['performance'] = perf_data
                device_data['rates'] = rates
                current_data['devices'].append(device_data)
                
                # 添加到表格 (对后续迭代添加行，第一次迭代只收集基准数据)
                if current_iteration > 0:
                    # 获取发送和接收速率
                    tx_rate = rates.get('PortXmitDataRate')
                    rx_rate = rates.get('PortRcvDataRate')
                    tx_pkt_rate = rates.get('PortXmitPktsRate')
                    rx_pkt_rate = rates.get('PortRcvPktsRate')
                    
                    # 获取丢包和错误数
                    discards = perf_data.get('PortXmitDiscards', 0)
                    errors = perf_data.get('PortRcvErrors', 0)
                    
                    # 添加到表格
                    table.add_row([
                        device,
                        port,
                        format_data_rate(tx_rate),
                        format_data_rate(rx_rate),
                        format_packet_rate(tx_pkt_rate),
                        format_packet_rate(rx_pkt_rate),
                        discards,
                        errors
                    ])
            
            # 在所有设备处理完成后，输出表格和更新时间
            if current_iteration > 0:
                # 输出基本信息和表格
                print(f"RDMA性能监控 - {active_devices}个活跃设备")
                print(f"监控间隔: {interval}秒   当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                if timed_out_devices:
                    skipped_devices = ', '.join([d.split('_')[0] for d in timed_out_devices])
                    print(f"已跳过的超时设备: {skipped_devices}")
                print("-" * 80)
                print(table)
                print("-" * 80)
                print(f"按Ctrl+C终止监控")
            elif current_iteration == 0:
                # 首次迭代完成的消息
                print(f"\n初始数据采集完成，发现{active_devices}个活跃设备。")
                print(f"开始监控性能数据，等待{interval}秒后显示第一次性能统计...")
            
            # 添加到所有数据
            all_data.append(current_data)
            
            # 写入数据到文件（如果需要）
            if output_file:
                try:
                    with open(output_file, 'w') as f:
                        json.dump(all_data, f, indent=2)
                except Exception as e:
                    print(f"保存到文件时出错: {e}")
            
            current_iteration += 1
            
    except KeyboardInterrupt:
        print("\n用户中断监控...")
    
    return all_data

def main():
    """主函数"""
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='RDMA设备监控工具')
    parser.add_argument('-i', '--interval', type=int, default=5, help='采集间隔时间(秒)')
    parser.add_argument('-c', '--count', type=int, default=None, help='采集次数(不指定则持续运行)')
    parser.add_argument('-o', '--output', type=str, default='rdma_monitor.json', help='输出文件名')
    args = parser.parse_args()
    
    # 获取RDMA链路信息
    rdma_links = parse_rdma_links()
    
    if not rdma_links:
        print("未找到合格的RDMA设备")
        return
    
    # 输出基本链路信息
    print(f"找到 {len(rdma_links)} 个RDMA设备（已过滤以太网设备）:")
    print("设备\t端口\tLID\tLID(Hex)\t状态\t物理状态")
    print("-" * 70)
    
    for link in rdma_links:
        print(f"{link['device']}\t{link['port']}\t{link['lid']}\t{link['lid_hex']}\t{link['state']}\t{link['physical_state']}")
    
    # 开始持续监控
    print(f"\n开始性能监控 (间隔: {args.interval}秒, {'持续运行' if args.count is None else f'次数: {args.count}'})")
    performance_data = monitor_performance_continuously(
        rdma_links, 
        interval=args.interval, 
        count=args.count,
        output_file=args.output
    )
    
    print(f"\n监控结束，详细信息已保存到 {args.output}")

if __name__ == "__main__":
    main() 