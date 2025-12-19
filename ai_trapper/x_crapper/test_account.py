import asyncio
import twscrape
from twscrape import API
import traceback


async def test_account():
    print("初始化API...")
    api = API()
    
    print("添加账户...")
    # 添加你的账户信息
    await api.pool.add_account("Tst3pu6FWY9283", "!Jh19980808", "19011288807@189.cn", "!Jiehai987654")
    
    print("正在尝试登录...")
    try:
        # 尝试登录
        await api.pool.login_all()
        print("登录尝试完成")
        
        # 检查账户状态
        print("获取账户信息...")
        accounts = await api.pool.accounts_info()
        print(f"账户信息类型: {type(accounts)}")
        print(f"账户信息内容: {accounts}")
        
        # 检查是否有活动账户
        print("检查活动账户...")
        # 尝试不同的方法获取账户信息
        try:
            # 方法1: 直接打印
            print("账户详情:")
            print(accounts)
        except Exception as e:
            print(f"获取账户详情时出错: {e}")
            
    except Exception as e:
        print(f"登录失败: {e}")
        print("详细错误信息:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_account())