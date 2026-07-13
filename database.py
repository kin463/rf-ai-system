import re

def get_member_schedule(input_name: str):
    try:
        with open("rules.txt", "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print("ファイル読み込みエラー:", str(e))
        return []

    results = []
    # パターンを2種類用意
    # パターン1：帰社日が存在するグループ（〇〇課）
    pattern_with_date = re.compile(r"\[(RandF .+?)\]\s*メンバー:(.+?)\n帰社日:(.+?)(?=\n\[|$)", re.DOTALL)
    # パターン2：帰社日の記載がないグループ（営業部）
    pattern_no_date = re.compile(r"\[(RandF .+?部)\]\s*メンバー:(.+?)(?=\n\[|$)", re.DOTALL)

    # 帰社日ありのグループを処理
    for department, member_text, date_text in pattern_with_date.findall(content):
        member_list = [name.strip() for name in member_text.split(",")]
        if input_name in department:
            for name in member_list:
                results.append((name, department, date_text.strip()))
        else:
            for name in member_list:
                if input_name in name:
                    results.append((name, department, date_text.strip()))

    # 帰社日がない営業部を処理（date_textを空文字列とする）
    for department, member_text in pattern_no_date.findall(content):
        member_list = [name.strip() for name in member_text.split(",")]
        if input_name in department:
            for name in member_list:
                results.append((name, department, ""))
        else:
            for name in member_list:
                if input_name in name:
                    results.append((name, department, ""))

    return results
