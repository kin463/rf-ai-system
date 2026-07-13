import re

def get_member_schedule(input_name: str):
    try:
        with open("rules.txt", "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print("ファイル読み込みエラー:", str(e))
        return []

    results = []
    pattern = re.compile(r"\[(RandF .+?課)\]\s*メンバー:(.+?)\n帰社日:(.+?)(?=\n\[|$)", re.DOTALL)
    for department, member_text, date_text in pattern.findall(content):
        member_list = [name.strip() for name in member_text.split(",")]
        for name in member_list:
            if input_name in name:
                # (フルネーム, 部門名, 帰社日) の順番で返却
                results.append((name, department, date_text.strip()))
    return results
