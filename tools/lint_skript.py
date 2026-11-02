#!/usr/bin/env python3
"""
Skript 스크립트 정적 검사 (서버 없이 할 수 있는 범위).
- 들여쓰기: 탭만 사용, 블록 머리(:)로 끝나는 줄 다음에만 한 단계 깊어짐
- 옵션 {@이름} 이 같은 파일 options: 에 정의되어 있는지
- 호출한 함수가 어딘가에 정의되어 있고 인자 수가 맞는지
- 자바 엔진이 호출하는 /vhook 이벤트를 모두 처리하는지
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "bukkit", "plugins", "Skript", "scripts")
errors = []


def main():
    files = glob.glob(os.path.join(SK, "**", "*.sk"), recursive=True)
    functions = {}
    calls = []
    handled_events = set()
    for f in files:
        rel = os.path.relpath(f, SK)
        lines = open(f, encoding="utf-8").read().split("\n")
        options = set()
        in_options = False
        prev_indent = 0
        prev_header = False
        for no, raw in enumerate(lines, 1):
            if not raw.strip() or raw.strip().startswith("#"):
                continue
            if " " in raw[: len(raw) - len(raw.lstrip())]:
                errors.append(f"{rel}:{no} 들여쓰기에 공백 사용 (탭만 사용)")
            indent = len(raw) - len(raw.lstrip("\t"))
            line = raw.strip()
            if indent > prev_indent and not prev_header:
                errors.append(f"{rel}:{no} 블록 머리 없이 들여쓰기가 깊어짐")
            if indent > prev_indent + 1:
                errors.append(f"{rel}:{no} 들여쓰기가 두 단계 이상 깊어짐")
            code = line.split(" #")[0].rstrip()
            prev_header = code.endswith(":")
            prev_indent = indent
            if indent == 0:
                in_options = line == "options:"
            elif in_options and indent == 1:
                m = re.match(r"([a-zA-Z0-9_\-]+):", line)
                if m:
                    options.add(m.group(1))
            m = re.match(r"function (\w+)\(([^)]*)\)", line)
            if m and indent == 0:
                params = [p for p in m.group(2).split(",") if p.strip()]
                functions[m.group(1)] = len(params)
                for p in params:
                    if ":" not in p:
                        errors.append(f"{rel}:{no} 함수 매개변수 형식 오류: {p}")
            for opt in re.findall(r"\{@([a-zA-Z0-9_\-]+)\}", line):
                if opt not in options:
                    errors.append(f"{rel}:{no} 정의되지 않은 옵션 {{@{opt}}}")
            for fn, args in re.findall(r"\b(violence\w+)\(([^()]*(?:\([^()]*\)[^()]*)*)\)", line):
                if not line.startswith("function "):
                    n = 0 if not args.strip() else len(split_args(args))
                    calls.append((rel, no, fn, n))
            m = re.match(r'(?:else )?if \{_event\} is "(\w+)":', line)
            if m:
                handled_events.add(m.group(1))
            if line.count('"') % 2 == 1:
                errors.append(f"{rel}:{no} 따옴표 짝이 맞지 않음")
            if line.count("%") % 2 == 1 and '"' in line:
                errors.append(f"{rel}:{no} % 짝이 맞지 않음 (문자열 안 표현식)")
    for rel, no, fn, n in calls:
        if fn not in functions:
            errors.append(f"{rel}:{no} 정의되지 않은 함수 {fn}")
        elif functions[fn] != n:
            errors.append(f"{rel}:{no} {fn} 인자 수 {n} (정의 {functions[fn]})")
    # 자바에서 보내는 훅 이벤트
    java = "\n".join(open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(ROOT, "plugin-src", "src", "main", "java", "**", "*.java"), recursive=True))
    sent = set(re.findall(r'bridge\.call\("(\w+)"', java)) | set(re.findall(r'\bcall\("(\w+)"', java))
    for ev in sent:
        if ev not in handled_events:
            errors.append(f"/vhook 이벤트 '{ev}' 를 처리하는 Skript 코드가 없음")
    # Skript → 자바 콜백 명령어
    for sub in ("award", "combobonus", "start", "stop"):
        if f'case "{sub}"' not in java and f'"{sub}", ' not in java and f'case "award", "combobonus"' not in java:
            errors.append(f"자바 /violence {sub} 하위 명령이 없음")
    print(f"Skript 파일 {len(files)}개, 함수 {len(functions)}개, 호출 {len(calls)}건, 훅 이벤트 {sorted(sent)}")
    if errors:
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    print("Skript 정적 검사 통과")


def split_args(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


if __name__ == "__main__":
    main()
