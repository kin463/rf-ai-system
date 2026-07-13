import re

def get_member_schedule(input_name: str):
    """
    rules.txtを読み込み、入力した名前に部分一致するメンバーの部門と帰社日を返す
    戻り値： [(部門名,帰社日),...]
    """
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []

    results = []
    # 正規表現で部門名、メンバー一覧、帰社日を抽出
    pattern = re.compile(r"\[(RandF .+?課)\]\s*メンバー:(.+?)\n帰社日:(.+?)(?=\n\[|$)", re.DOTALL)
    for department, member_text, date_text in pattern.findall(content):
        member_list = [name.strip() for name in member_text.split(",")]
        for name in member_list:
            if input_name in name:
                results.append((department, date_text.strip()))
    return results
