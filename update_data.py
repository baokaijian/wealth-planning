import urllib.request
import json
import time
from datetime import datetime

# 定义每股年度分红 (元/股) 与 ETF 基准参数
STOCK_DPS = {
    '600941': 4.7037,  # 中国移动 (2025年中期 2.5025 + 末期 2.2012)
    '600900': 1.0000,  # 长江电力
    '601398': 0.3103,  # 工商银行 (中期 0.1414 + 末期 0.1689)
    '601088': 2.0100,  # 中国神华 (中期 0.9800 + 末期 1.0300)
    '601668': 0.2718,  # 中国建筑 (每10股派 2.718元)
}

ETF_BASE = {
    '512890': {'base_price': 1.40, 'base_yield': 4.5},  # 中证红利低波 ETF
    '515450': {'base_price': 1.15, 'base_yield': 4.2},  # 标普大盘红利低波 ETF
    '513530': {'base_price': 1.00, 'base_yield': 4.8},  # 恒生红利低波 ETF
}

# 证券代码映射
SEC_IDS = ['sh600941', 'sh600900', 'sh601398', 'sh601088', 'sh601668', 'sh512890', 'sh515450', 'sh513530']
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
            if code in STOCK_DPS:
                dps = STOCK_DPS[code]
                dividend_yield = round((dps / price) * 100, 2)
            elif code in ETF_BASE:
                base = ETF_BASE[code]
                # ETF 股息率与价格呈反比关系
                dividend_yield = round(base['base_yield'] * (base['base_price'] / price), 2)
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
        
        with open('/Users/baokaijian/Project/gemini-invest/live_data.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=4)
            
        print("Live data updated successfully at:", output['timestamp'])
        print(json.dumps(output, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print("Error fetching live data:", e)

if __name__ == '__main__':
    fetch_live_data()
