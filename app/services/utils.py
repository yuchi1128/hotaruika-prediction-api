import numpy as np

# 16方位のマッピング
DIRECTIONS = [
    '北', '北北東', '北東', '東北東', '東', '東南東', '南東', '南南東',
    '南', '南南西', '南西', '西南西', '西', '西北西', '北西', '北北西'
]

def degree_to_direction(degree: float) -> str:
    """
    風向の角度（0-360度）を16方位の文字列に変換する。
    北を0度とし、時計回り。
    """
    if np.isnan(degree):
        return "" # 不明な場合は空文字
    
    # 22.5度ごとに区切るための計算
    val = int((degree / 22.5) + 0.5)
    return DIRECTIONS[val % 16]