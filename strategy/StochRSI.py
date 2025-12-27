import numpy as np 
from backtesting import Backtest, Strategy 
from backtesting.lib import crossover, MultiBacktest 
from backtesting.test import SMA, GOOG 
# from test.utils import *
from src.utils import *
from datetime import datetime, timedelta 
import requests
import json
import os
from dotenv import load_dotenv

import json

import lark_oapi as lark
from lark_oapi.api.drive.v1 import *

import time

def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        
        # 转换为小时、分钟、秒
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # 根据时长选择不同的格式
        if hours >= 1:
            print(f"{func.__name__} 用时: {int(hours)}小时{int(minutes)}分{seconds:.2f}秒")
        elif minutes >= 1:
            print(f"{func.__name__} 用时: {int(minutes)}分{seconds:.2f}秒")
        else:
            print(f"{func.__name__} 用时: {seconds:.2f}秒")
            
        return result
    return wrapper


TODAY = datetime.today().strftime('%Y%m%d') 


@timer 
def lucy_strategy_backtest():
    def get_single_data(params):
        
        ts_code = params['all_stock'][params['all_stock']['name']==params['stock_name']]['ts_code'].values[0]

        start_date = datetime.strptime(params['start_date'], '%Y%m%d') - timedelta(days=int(params['period']))
        start_date = start_date.strftime('%Y%m%d')

        end_date = params['end_date'] if params['end_date'] != '' else datetime.today().strftime('%Y%m%d')

        data = params['daily_data'][
            (params['daily_data']['ts_code']==ts_code) & (params['daily_data']['trade_date'] >= int(start_date)) & (params['daily_data']['trade_date'] <= int(end_date))
        ].sort_values(by=['trade_date'], ascending=True).reset_index(drop=True)
        data = data.rename(columns={
            'high': 'High',
            'low': 'Low',
            'open': 'Open',
            'close': 'Close',
            'vol': 'Volume'
        })
        
        data['trade_date'] = pd.to_datetime(data['trade_date'], format='%Y%m%d')
        data = data.set_index(['trade_date'])[['Open', 'High', 'Low', 'Close', 'Volume']]
        return data 

    all_stock   = pd.read_csv('E:/Messi/StockInfoDeliver/tushare/data/base_info/stock/all_stock.csv')
    a_basic_df = pd.read_csv('E:/Messi/StockInfoDeliver/tushare/data/daily/stock/a_stock_daily.csv')
    a_basic_df = a_basic_df[a_basic_df.trade_date >= 20240101].reset_index(drop=True)

    params = {
                'type'       : '股票',
                # 'stock_name' : ts_name,
                'start_date' : '20240101',
                'end_date'   : '20251221',
                'end_date'   : datetime.today().strftime('%Y%m%d'),
                'period'     : 20,
                'save_root'  : 'E:\\Messi\\StockInfoDeliver\\StockInfoDeliver\\data\\backtest',
                'all_stock'  : all_stock,
                'daily_data' : a_basic_df,
            }

    # data = get_single_data(params)

    from test.lingma.examples.LucyStrategy import run_lucy_strategy

    all_data_results = []
    candidate_stock = all_stock['name'].tolist()[:]

    for ts_name in tqdm(candidate_stock, total=len(candidate_stock)):

        try:
            params['stock_name'] = ts_name
            data = get_single_data(params)
            data = run_lucy_strategy(data)
            data['stock_name'] = ts_name
            data = data.reset_index()
            all_data_results.append(data)
        except Exception as e:
            print(f"{ts_name} 出错，错误原因：{e}")
            continue

    all_data_results = pd.concat(all_data_results).reset_index(drop=True)
    return all_data_results[(all_data_results['trade_date'] == all_data_results['trade_date'].max())
                            & (
                                (all_data_results['ut_buy'] == True) | 
                                (all_data_results['ut_sell'] == True)    
                            )
                            ]

@timer
def lark_upload(file_path):
    
    
    # 加载环境变量
    load_dotenv()

    app_id = os.getenv("LARK_APP_ID")
    app_secret = os.getenv("LARK_APP_SECRET")

    # 准备请求参数
    url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }
    data = {
    "app_id": app_id,
    "app_secret": app_secret
    }

    # 发送POST请求
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # 如果请求返回了不成功的状态码，这行代码会抛出异常
        
        # 解析响应内容
        response_data = response.json()
        # print("API响应内容:", response_data)
        if response_data.get("code") == 0:
            tenant_access_token = response_data["tenant_access_token"]
            app_access_token = response_data["app_access_token"]
            # print(f"tenant_access_token: {tenant_access_token}")
        else:
            print(f"获取失败: code={response_data.get('code')}, msg={response_data.get('msg')}")
        
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")

    

    today = datetime.today().strftime('%Y%m%d')

    folder_token = 'NGdDfSRj4lyYssda3SkccmpAnjc'

    # SDK 使用说明: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/server-side-sdk/python--sdk/preparations-before-development
    # 以下示例代码默认根据文档示例值填充，如果存在代码问题，请在 API 调试台填上相关必要参数后再复制代码使用
    # 复制该 Demo 后, 需要将 "YOUR_APP_ID", "YOUR_APP_SECRET" 替换为自己应用的 APP_ID, APP_SECRET.
    if True:
        # 创建client
        client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.DEBUG) \
            .build()

        # 构造请求对象
        file = open(file_path, "rb")
        file_size = os.path.getsize(file_path)
        request: UploadAllFileRequest = UploadAllFileRequest.builder() \
            .request_body(UploadAllFileRequestBody.builder()
                .file_name(f"{TODAY}_LUCY_股票筛选结果v1.csv")
                .parent_type("explorer")
                .parent_node(folder_token)
                .size(file_size)
                .file(file)
                # .file_type("docx")
                .build()) \
            .build()

        # 发起请求
        response: UploadAllFileResponse = client.drive.v1.file.upload_all(request)

        # 处理失败返回
        if not response.success():
            lark.logger.error(
                f"client.drive.v1.file.upload_all failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
            print("请求飞书文档上传文件失败")

        # 处理业务结果
        lark.logger.info(lark.JSON.marshal(response.data, indent=4))




@timer
def main():
    
    ################################################################################
    ## 游资选股 
    print("STARTING LUCY STRATEGY BACKTEST...")
    from test.lingma.examples.LucyStrategy import run_lucy_strategy

    save_name = f"E:\\Messi\\StockInfoDeliver\\tushare\\data\\daily\\recommendations\\lucy\\{TODAY}_股票筛选结果_LUCY_v1.csv"
    if os.path.exists(save_name):
        print("Loading existing recommendations...")
        recommendations = pd.read_csv(save_name)

    else:
        print("Preparing data...")
        stock_root = "E:\\Messi\\StockInfoDeliver\\tushare\\data\\base_info\\stock\\all_stock.csv"
        all_stock = pd.read_csv('E:/Messi/StockInfoDeliver/tushare/data/base_info/stock/all_stock.csv')

        # today = datetime.today().strftime('%Y%m%d')
        start_date = '20240904'

        calender = pd.read_csv('E:\\Messi\\StockInfoDeliver\\tushare\\data\\base_info\\calender\\trade_calender.csv')
        calender['cal_date'] = calender['cal_date'].astype(str)
        calender = calender[(calender['is_open']==1) & 
                            (calender['cal_date'] <= TODAY) & 
                            (calender['cal_date'] >= start_date)].reset_index(drop=True)

        daily_df = pd.read_csv("E:\\Messi\\StockInfoDeliver\\tushare\\data\\daily\\stock\\a_stock_daily.csv")
        daily_df['trade_date'] = daily_df['trade_date'].astype(str)        

        # 结合游资选股和涨幅选股，生成最终推荐名单
        print("Generating recommendations...")
        recommendations = lucy_strategy_backtest()
        recommendations.to_csv(save_name, index=False, encoding='utf-8-sig')

    # 上传到飞书
    print("Uploading results to Lark...")
    lark_upload(save_name)

    print('成功完成股票筛选与新闻爬取任务！')



if __name__ == '__main__':
    
    main()