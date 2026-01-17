"""
快速开始示例
演示如何使用松松策略进行简单的回测
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from wanzhu.strategy.songsong_strategy import SongSongStrategy
from wanzhu.config.strategy_config import StrategyConfig


def main():
    """快速开始示例"""
    
    print("=" * 60)
    print("顽主杯松松策略 - 快速开始")
    print("=" * 60)
    
    # 1. 获取配置
    config = StrategyConfig.get_config(mode='backtest')
    
    print("\n策略配置：")
    print(f"  初始资金: {config['initial_capital']:,.0f} 元")
    print(f"  策略模式: {config['strategy_mode']}")
    print(f"  最大持仓数: {config['max_positions']}")
    print(f"  最大仓位: {config['risk']['max_position_ratio']*100:.0f}%")
    print(f"  止损比例: {config['risk']['max_single_loss_pct']*100:.2f}%")
    
    # 2. 初始化策略
    print("\n初始化策略...")
    strategy = SongSongStrategy(config)
    
    # 3. 运行回测
    print("\n开始回测...")
    print(f"  回测期间: {config['backtest']['start_date']} 至 {config['backtest']['end_date']}")
    
    try:
        results = strategy.run(
            start_date=config['backtest']['start_date'],
            end_date=config['backtest']['end_date']
        )
        
        # 4. 输出结果
        print("\n" + "=" * 60)
        print("回测结果")
        print("=" * 60)
        
        if len(results) > 0:
            final_value = results.iloc[-1]['total_value']
            initial_value = config['initial_capital']
            total_return = (final_value - initial_value) / initial_value
            
            print(f"\n期末资金: {final_value:,.2f} 元")
            print(f"总收益率: {total_return*100:.2f}%")
            print(f"交易天数: {len(results)} 天")
            
            # 显示性能报告
            print("\n" + "-" * 60)
            print("策略表现统计")
            print("-" * 60)
            
            report = strategy.get_performance_report()
            for key, value in report.items():
                print(f"  {key}: {value}")
            
            # 保存结果
            output_file = 'wanzhu/data/backtest_results.csv'
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            results.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n回测结果已保存至: {output_file}")
            
        else:
            print("\n未生成回测数据，请检查数据源配置")
            
    except Exception as e:
        print(f"\n回测过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("回测完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
