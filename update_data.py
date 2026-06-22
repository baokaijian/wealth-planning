import urllib.request
import json
import time
import os
from datetime import datetime

# 加载 assets.json 动态提取代码
script_dir = os.path.dirname(os.path.abspath(__file__))
assets_path = os.path.join(script_dir, 'assets.json')

try:
    with open(assets_path, 'r', encoding='utf-8') as f:
        assets_data = json.load(f)
    SEC_IDS = [f"sh{item['code']}" for item in assets_data]
except Exception as e:
    print("Error loading assets.json, fallback to hardcoded list:", e)
    SEC_IDS = ['sh512890', 'sh515450', 'sh510880', 'sh515080', 'sh513530', 'sh511360', 'sh518880']

# ETF基准参数 (基准价格, 基准股息率)，用于根据最新价格反算实时股息率
ETF_BASE = {
    '512890': {'base_price': 1.17, 'base_yield': 4.5},
    '515450': {'base_price': 1.43, 'base_yield': 4.2},
    '510880': {'base_price': 3.20, 'base_yield': 4.0},
    '515080': {'base_price': 1.50, 'base_yield': 4.1},
    '513530': {'base_price': 1.61, 'base_yield': 4.8},
    '511360': {'base_price': 108.0, 'base_yield': 2.5},
    '518880': {'base_price': 4.50, 'base_yield': 0.0}
}

url = f"http://qt.gtimg.cn/q={','.join(SEC_IDS)}"

def fetch_live_data():
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('gbk')
            
        lines = [line.strip() for line in html.split('\n') if line.strip()]
        result = {}
        
        for line in lines:
            # 格式例如: v_sh600941="1~中国移动~600941~95.12~..."
            if '=' not in line:
                continue
            parts = line.split('=')
            var_name = parts[0].strip()
            code = var_name.replace('v_sh', '')
            
            content = parts[1].strip().replace('"', '').replace(';', '')
            data_fields = content.split('~')
            
            if len(data_fields) < 4:
                continue
                
            name = data_fields[1]
            price = float(data_fields[3])
            
            # 计算股息率
            if code in ETF_BASE:
                base = ETF_BASE[code]
                if price > 0 and base['base_yield'] > 0:
                    dividend_yield = round(base['base_yield'] * (base['base_price'] / price), 2)
                else:
                    dividend_yield = 0.0
            else:
                dividend_yield = 0.0
                
            result[code] = {
                'name': name,
                'price': price,
                'yield': dividend_yield
            }
            
        output = {
            'status': 'success',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': result
        }
        
        output_path = os.path.join(script_dir, 'live_data.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=4)
            
        print("Live data updated successfully at:", output['timestamp'])
        print(json.dumps(output, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print("Error fetching live data:", e)

if __name__ == '__main__':
    fetch_live_data()
