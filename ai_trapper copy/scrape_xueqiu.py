#!/usr/bin/env python3
"""
雪球用户动态爬虫
抓取"大道无形我有型"（段永平）在雪球的发言
基于 RSSHub 的实现逻辑改写
"""

import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import re
from html import unescape

class XueqiuScraper:
    """雪球用户动态爬虫"""
    
    def __init__(self, user_id: str = "8152922548"):
        """
        初始化爬虫
        
        Args:
            user_id: 雪球用户ID，默认为"大道无形我有型"的ID
        """
        self.user_id = user_id
        self.root_url = "https://xueqiu.com"
        self.session = requests.Session()
        
        # 设置请求头，模拟浏览器
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': f'{self.root_url}/u/{user_id}'
        })
        
        # 动态类型映射
        self.type_name = {
            10: '全部',
            0: '原发布',
            2: '长文',
            4: '问答',
            9: '热门',
            11: '交易'
        }
    
    def get_token(self) -> str:
        """
        获取访问令牌（Cookie）
        访问用户主页以获取必要的 Cookie
        
        Returns:
            token字符串
        """
        try:
            # 先访问主页获取 Cookie
            response = self.session.get(
                f"{self.root_url}/u/{self.user_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ 成功访问用户主页，已获取 Cookie")
                return True
            else:
                print(f"⚠️ 访问用户主页失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 获取 Token 失败: {e}")
            return False
    
    def fetch_user_timeline(self, post_type: int = 10, page: int = 1) -> List[Dict[str, Any]]:
        """
        获取用户时间线动态
        
        Args:
            post_type: 动态类型 (10=全部, 0=原发布, 2=长文, 4=问答, 9=热门, 11=交易)
            page: 页码
            
        Returns:
            动态列表
        """
        # API 地址
        api_url = f"{self.root_url}/v4/statuses/user_timeline.json"
        
        params = {
            'user_id': self.user_id,
            'type': post_type,
            'page': page
        }
        
        try:
            print(f"\n📡 正在获取{self.type_name.get(post_type, '未知')}动态（第 {page} 页）...")
            
            response = self.session.get(
                api_url,
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'statuses' in data and data['statuses']:
                    # 过滤掉被标记删除的动态
                    posts = [s for s in data['statuses'] if s.get('mark') != 1]
                    print(f"✅ 成功获取 {len(posts)} 条动态")
                    return posts
                else:
                    print("⚠️ 未找到动态数据")
                    return []
            else:
                print(f"❌ 请求失败: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ 获取动态失败: {e}")
            return []
    
    def clean_html(self, html_text: str) -> str:
        """
        清理 HTML 标签
        
        Args:
            html_text: HTML 文本
            
        Returns:
            纯文本
        """
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', html_text)
        # 解码 HTML 实体
        text = unescape(text)
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def format_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化单条动态
        
        Args:
            post: 原始动态数据
            
        Returns:
            格式化后的动态
        """
        try:
            # 基本信息
            post_id = post.get('id', '')
            created_at = post.get('created_at', 0)
            
            # 转换时间戳
            if created_at:
                post_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            else:
                post_time = "未知时间"
            
            # 标题和内容
            title = post.get('title', '')
            description = post.get('description', '')
            text = post.get('text', '')
            
            # 优先使用 text，否则使用 description
            content = text if text else description
            
            # 清理 HTML
            clean_content = self.clean_html(content) if content else ''
            clean_title = self.clean_html(title) if title else clean_content[:50]
            
            # 链接
            target = post.get('target', '')
            link = f"{self.root_url}{target}" if target else ''
            
            # 转发信息
            retweeted_status = post.get('retweeted_status')
            retweet_info = None
            
            if retweeted_status:
                retweet_user = retweeted_status.get('user', {}).get('screen_name', '未知用户')
                retweet_text = self.clean_html(retweeted_status.get('description', ''))
                retweet_info = f"转发 @{retweet_user}: {retweet_text}"
            
            return {
                'id': post_id,
                'time': post_time,
                'title': clean_title,
                'content': clean_content,
                'retweet': retweet_info,
                'link': link,
                'raw': post  # 保留原始数据
            }
            
        except Exception as e:
            print(f"⚠️ 格式化动态失败: {e}")
            return None
    
    def scrape(self, post_type: int = 10, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        爬取用户动态
        
        Args:
            post_type: 动态类型
            max_pages: 最大爬取页数
            
        Returns:
            格式化的动态列表
        """
        print(f"\n{'='*80}")
        # print(f"🎯 开始爬取"大道无形我有型"的雪球动态")
        print(f"📌 用户ID: {self.user_id}")
        print(f"📌 动态类型: {self.type_name.get(post_type, '未知')}")
        print(f"📌 最大页数: {max_pages}")
        print(f"{'='*80}")
        
        # 获取 Token
        if not self.get_token():
            print("❌ 无法获取访问令牌，爬取终止")
            return []
        
        all_posts = []
        
        for page in range(1, max_pages + 1):
            # 获取动态
            posts = self.fetch_user_timeline(post_type, page)
            
            if not posts:
                print(f"⚠️ 第 {page} 页没有更多数据，停止爬取")
                break
            
            # 格式化动态
            for post in posts:
                formatted = self.format_post(post)
                if formatted:
                    all_posts.append(formatted)
            
            # 避免请求过快
            if page < max_pages:
                time.sleep(2)
        
        print(f"\n{'='*80}")
        print(f"✅ 爬取完成！共获取 {len(all_posts)} 条动态")
        print(f"{'='*80}\n")
        
        return all_posts
    
    def save_to_json(self, posts: List[Dict[str, Any]], filename: str = None):
        """
        保存到 JSON 文件
        
        Args:
            posts: 动态列表
            filename: 文件名
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"xueqiu_posts_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(posts, f, ensure_ascii=False, indent=2)
            print(f"💾 已保存到文件: {filename}")
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
    
    def save_to_text(self, posts: List[Dict[str, Any]], filename: str = None):
        """
        保存到文本文件（更易读）
        
        Args:
            posts: 动态列表
            filename: 文件名
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"xueqiu_posts_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("大道无形我有型（段永平）- 雪球动态\n")
                f.write(f"爬取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"共 {len(posts)} 条动态\n")
                f.write("="*80 + "\n\n")
                
                for i, post in enumerate(posts, 1):
                    f.write(f"\n{'='*80}\n")
                    f.write(f"动态 #{i}\n")
                    f.write(f"{'='*80}\n")
                    f.write(f"📅 时间: {post['time']}\n")
                    f.write(f"📝 标题: {post['title']}\n")
                    f.write(f"🔗 链接: {post['link']}\n")
                    f.write(f"\n内容:\n{'-'*80}\n")
                    f.write(f"{post['content']}\n")
                    
                    if post['retweet']:
                        f.write(f"\n{'-'*80}\n")
                        f.write(f"{post['retweet']}\n")
                    
                    f.write(f"\n")
            
            print(f"📄 已保存到文本文件: {filename}")
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
    
    def print_posts(self, posts: List[Dict[str, Any]], max_display: int = 10):
        """
        在终端打印动态（预览）
        
        Args:
            posts: 动态列表
            max_display: 最大显示数量
        """
        print(f"\n{'='*80}")
        print(f"📰 最新 {min(len(posts), max_display)} 条动态预览")
        print(f"{'='*80}\n")
        
        for i, post in enumerate(posts[:max_display], 1):
            print(f"\n{'-'*80}")
            print(f"【动态 #{i}】")
            print(f"🕐 {post['time']}")
            print(f"📝 {post['title']}")
            print(f"🔗 {post['link']}")
            print(f"\n{post['content'][:200]}{'...' if len(post['content']) > 200 else ''}")
            
            if post['retweet']:
                print(f"\n💬 {post['retweet'][:150]}{'...' if len(post['retweet']) > 150 else ''}")


def main():
    """主函数"""
    # 创建爬虫实例（默认为"大道无形我有型"的ID）
    scraper = XueqiuScraper(user_id="8152922548")
    
    # 爬取全部动态，最多 5 页
    posts = scraper.scrape(post_type=10, max_pages=5)
    
    if posts:
        # 在终端预览
        scraper.print_posts(posts, max_display=5)
        
        # 保存到文件
        scraper.save_to_json(posts)
        scraper.save_to_text(posts)
    else:
        print("❌ 未能获取任何动态")


if __name__ == "__main__":
    main()
