"""
Saber 核心策略类
整合市场过滤、策略选择、风控等所有模块
"""

import pandas as pd
from typing import Dict, Optional, List
from datetime import datetime

from saber.config.strategy_config import StrategyConfig
from saber.strategy.market_filter import MarketFilter
from saber.strategy.bull_call_spread import BullCallSpread
from saber.strategy.bull_put_spread import BullPutSpread
from saber.strategy.risk_manager import RiskManager
from saber.utils.market_data import MarketDataLoader


class SaberStrategy:
    """Saber 慢牛双模组期权策略"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化策略
        
        Args:
            config: 策略配置（可选）
        """
        self.config = config or StrategyConfig.get_config()
        
        # 初始化各模块
        self.market_filter = MarketFilter(self.config)
        self.bull_call_spread = BullCallSpread(self.config)
        self.bull_put_spread = BullPutSpread(self.config)
        self.risk_manager = RiskManager(
            self.config,
            self.config.get('initial_capital', 100000)
        )
        self.data_loader = MarketDataLoader(self.config)
        
        # 策略状态
        self.current_date = None
    
    def run_daily(self, symbol: str, date: str) -> Dict:
        """
        执行每日策略
        
        Args:
            symbol: 交易标的（如 'BTC'）
            date: 日期
            
        Returns:
            执行结果
        """
        self.current_date = date
        results = {
            'date': date,
            'symbol': symbol,
            'actions': [],
            'signals': [],
            'portfolio': {}
        }
        
        print(f"\n{'='*60}")
        print(f"执行日期: {date} | 标的: {symbol}")
        print(f"{'='*60}")
        
        # 1. 加载市场数据
        end_date = pd.to_datetime(date)
        start_date = end_date - pd.Timedelta(days=90)
        
        price_data = self.data_loader.load_price_data(
            f"{symbol}USDT",
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if price_data.empty:
            print("无法获取价格数据")
            return results
        
        # 2. 获取IV数据（模拟）
        current_iv = 0.6 + (price_data['close'].pct_change().std() * 10)
        iv_history = pd.Series([0.5 + i * 0.01 for i in range(90)])
        
        # 3. 市场状态过滤
        is_slow_bull, reason = self.market_filter.check_slow_bull(
            price_data, current_iv, iv_history
        )
        
        print(f"\n市场状态: {'✅ 慢牛' if is_slow_bull else '❌ 非慢牛'}")
        print(f"原因: {reason}")
        
        if not is_slow_bull:
            results['reason'] = reason
            return results
        
        # 4. 检查持仓止损/止盈
        exit_actions = self._check_exit_signals(price_data, current_iv)
        results['actions'].extend(exit_actions)
        
        # 5. 判断IV状态，选择策略
        iv_regime = self.market_filter.get_iv_regime(current_iv, iv_history)
        
        print(f"\nIV状态: {iv_regime}")
        print(f"当前IV: {current_iv:.2f}")
        
        # 6. 生成开仓信号
        if iv_regime == 'low':
            signal = self._generate_call_spread_signal(price_data, current_iv, date)
            if signal:
                results['signals'].append(signal)
                print(f"\n🎯 模式A信号: 牛市认购价差 (Bull Call Spread)")
        
        elif iv_regime == 'high':
            signal = self._generate_put_spread_signal(price_data, current_iv, date)
            if signal:
                results['signals'].append(signal)
                print(f"\n🎯 模式B信号: 牛市认沽价差 (Bull Put Spread)")
        
        else:
            print(f"\n⏸️  IV中性，观望")
        
        # 7. 执行开仓
        entry_actions = self._execute_entry_signals(results['signals'])
        results['actions'].extend(entry_actions)
        
        # 8. 检查尾部对冲
        self._check_tail_hedge()
        
        # 9. 更新组合状态
        results['portfolio'] = self.risk_manager.get_portfolio_status()
        
        # 10. 打印总结
        self._print_daily_summary(results)
        
        return results
    
    def _generate_call_spread_signal(self, price_data: pd.DataFrame,
                                    current_iv: float, date: str) -> Optional[Dict]:
        """生成牛市认购价差信号"""
        spot_price = price_data['close'].iloc[-1]
        support, resistance = self.data_loader.find_support_resistance(price_data)
        
        # 选择行权价
        long_strike, short_strike = self.bull_call_spread.select_strikes(
            spot_price, support, resistance
        )
        
        # 选择到期日（假设30天后）
        expiry_date = (pd.to_datetime(date) + pd.Timedelta(days=30)).strftime('%Y-%m-%d')
        
        # 计算指标
        metrics = self.bull_call_spread.calculate_position_metrics(
            spot_price, long_strike, short_strike, expiry_date, current_iv
        )
        
        # 检查开仓条件
        can_enter, reason = self.bull_call_spread.check_entry_conditions(
            spot_price, metrics, current_iv
        )
        
        if can_enter:
            return {
                'type': 'bull_call_spread',
                'metrics': metrics,
                'initial_iv': current_iv,
                'support': support,
                'resistance': resistance
            }
        
        print(f"Call Spread 不满足开仓条件: {reason}")
        return None
    
    def _generate_put_spread_signal(self, price_data: pd.DataFrame,
                                   current_iv: float, date: str) -> Optional[Dict]:
        """生成牛市认沽价差信号"""
        spot_price = price_data['close'].iloc[-1]
        support, resistance = self.data_loader.find_support_resistance(price_data)
        
        # 选择行权价
        short_strike, long_strike = self.bull_put_spread.select_strikes(
            spot_price, support
        )
        
        # 选择到期日
        expiry_date = (pd.to_datetime(date) + pd.Timedelta(days=30)).strftime('%Y-%m-%d')
        
        # 计算指标
        metrics = self.bull_put_spread.calculate_position_metrics(
            spot_price, short_strike, long_strike, expiry_date, current_iv
        )
        
        # 检查开仓条件
        can_enter, reason = self.bull_put_spread.check_entry_conditions(
            spot_price, metrics, current_iv
        )
        
        if can_enter:
            return {
                'type': 'bull_put_spread',
                'metrics': metrics,
                'initial_iv': current_iv,
                'support': support
            }
        
        print(f"Put Spread 不满足开仓条件: {reason}")
        return None
    
    def _check_exit_signals(self, price_data: pd.DataFrame, current_iv: float) -> List[Dict]:
        """检查平仓信号"""
        actions = []
        spot_price = price_data['close'].iloc[-1]
        support, resistance = self.data_loader.find_support_resistance(price_data)
        
        for pos_id, position in list(self.risk_manager.positions.items()):
            strategy_type = position['type']
            entry_metrics = position['metrics']
            
            # 重新计算当前指标
            if strategy_type == 'bull_call_spread':
                current_metrics = self.bull_call_spread.calculate_position_metrics(
                    spot_price,
                    entry_metrics['long_strike'],
                    entry_metrics['short_strike'],
                    entry_metrics['expiry_date'],
                    current_iv
                )
                
                should_exit, reason, ratio = self.bull_call_spread.check_exit_conditions(
                    spot_price, current_metrics, entry_metrics, current_iv, support
                )
                
            elif strategy_type == 'bull_put_spread':
                current_metrics = self.bull_put_spread.calculate_position_metrics(
                    spot_price,
                    entry_metrics['short_strike'],
                    entry_metrics['long_strike'],
                    entry_metrics['expiry_date'],
                    current_iv
                )
                
                should_exit, reason, ratio = self.bull_put_spread.check_exit_conditions(
                    spot_price, current_metrics, entry_metrics, current_iv, support
                )
            else:
                continue
            
            if should_exit:
                # 计算盈亏
                if strategy_type == 'bull_call_spread':
                    pnl = (current_metrics['short_premium'] - current_metrics['long_premium']) - entry_metrics['net_debit']
                else:
                    pnl = entry_metrics['net_credit'] - (current_metrics['short_premium'] - current_metrics['long_premium'])
                
                # 平仓
                self.risk_manager.close_position(pos_id, {
                    'reason': reason,
                    'pnl': pnl * position['invested_capital'] / entry_metrics.get('net_debit', entry_metrics.get('net_credit', 1))
                })
                
                actions.append({
                    'type': 'CLOSE',
                    'position_id': pos_id,
                    'reason': reason,
                    'pnl': pnl
                })
                
                print(f"\n❌ 平仓: {pos_id}")
                print(f"   原因: {reason}")
                print(f"   盈亏: ${pnl:,.2f}")
        
        return actions
    
    def _execute_entry_signals(self, signals: List[Dict]) -> List[Dict]:
        """执行开仓信号"""
        actions = []
        
        for signal in signals:
            # 检查是否可以开仓
            can_open, reason = self.risk_manager.can_open_position()
            
            if not can_open:
                print(f"无法开仓: {reason}")
                continue
            
            # 计算仓位
            metrics = signal['metrics']
            position_size = self.risk_manager.calculate_position_size(metrics['max_loss'])
            
            # 添加持仓
            position_id = f"{signal['type']}_{datetime.now().timestamp()}"
            self.risk_manager.add_position(position_id, {
                **signal,
                'invested_capital': position_size
            })
            
            actions.append({
                'type': 'OPEN',
                'strategy': signal['type'],
                'position_id': position_id,
                'invested': position_size
            })
            
            print(f"\n✅ 开仓: {signal['type']}")
            print(f"   投入资金: ${position_size:,.2f}")
            print(f"   最大利润: ${metrics['max_profit']:,.2f}")
            print(f"   最大亏损: ${metrics['max_loss']:,.2f}")
        
        return actions
    
    def _check_tail_hedge(self):
        """检查尾部对冲"""
        should_hedge, available = self.risk_manager.should_add_tail_hedge()
        
        if should_hedge:
            print(f"\n🛡️  建议添加尾部对冲，可用资金: ${available:,.2f}")
    
    def _print_daily_summary(self, results: Dict):
        """打印每日总结"""
        print(f"\n{'='*60}")
        print(f"每日总结")
        print(f"{'='*60}")
        
        portfolio = results['portfolio']
        print(f"当前资金: ${portfolio['current_capital']:,.2f}")
        print(f"持仓数: {portfolio['position_count']}")
        print(f"仓位比例: {portfolio['exposure_ratio']:.1%}")
        print(f"总收益: ${portfolio['total_pnl']:,.2f} ({portfolio['total_return']:+.2%})")
    
    def get_performance_report(self) -> Dict:
        """获取策略表现报告"""
        portfolio = self.risk_manager.get_portfolio_status()
        trade_stats = self.risk_manager.get_trade_statistics()
        
        return {
            'portfolio': portfolio,
            'trade_statistics': trade_stats,
            'positions': self.risk_manager.positions
        }
