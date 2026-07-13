import re

def get_member_schedule(input_name: str):
    with open("rules.txt", "r", encoding="utf-8") as f:
        content = f.read()
    results = []
    pattern = re.compile(r"\[(RandF .+?課)\]\s*メンバー:(.+?)\n帰社日:(.+?)(?=\n\[|$)", re.DOTALL)
    for dept_name, member_text, date_text in pattern.findall(content):
        members = [name.strip() for name in member_text.split(",")]
        for name in members:
            if input_name in name:
                results.append((dept_name, date_text.strip()))
    return results
