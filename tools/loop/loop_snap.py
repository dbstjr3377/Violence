#!/usr/bin/env python3
"""루프 회차 스냅샷·점수 기록 도구 ("루프로 진행해줘" 절차, .claude/skills/loop-craft 참고).

  init    <slug> "<요청 원문>"                     loop_runs/<slug>/ 생성
  save    <slug> <회차> <파일...>                  결과물을 snap_NN/files/<레포 상대경로>로 복사(+sha256)
  attach  <slug> <회차> <파일...>                  렌더·스크린샷 등 증빙을 snap_NN/evidence/로 복사
  record  <slug> <회차> --speck <speck.json> --ai X --tacz Y
          [--judge <judge.json>] --blocker "막힌 곳" --fix "뭘 왜 고쳤나" [--next "다음 회차 계획"]
                                                   점수 기록 후 LOG.md / PASSED.md 재생성
  restore <slug> <회차>                            스냅샷 파일을 레포 원래 경로로 되돌림
  list    <slug>                                   회차별 점수·통과 여부 출력
통과 = 잡티 검사 통과 AND AI티 <= 3.0 AND TACZ 화풍 >= 7.0
"""
import argparse, hashlib, json, os, shutil, sys, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUNS = os.path.join(ROOT, "loop_runs")
AI_MAX, TACZ_MIN = 3.0, 7.0


def run_dir(slug):
    return os.path.join(RUNS, slug)


def snap_dir(slug, n):
    return os.path.join(run_dir(slug), f"snap_{int(n):02d}")


def rel(p):
    a = os.path.abspath(p)
    if not a.startswith(ROOT + os.sep):
        sys.exit(f"레포 밖 파일은 결과물로 저장할 수 없음: {p}")
    return os.path.relpath(a, ROOT)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def load(p, default=None):
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return default


def dump(p, o):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)


def snaps(slug):
    d = run_dir(slug)
    out = []
    for name in sorted(os.listdir(d)):
        if name.startswith("snap_"):
            s = load(os.path.join(d, name, "score.json"))
            out.append((int(name[5:]), s))
    return out


def regen(slug):
    d = run_dir(slug)
    meta = load(os.path.join(d, "run.json"), {})
    rows = snaps(slug)
    lines = [f"# 루프 기록: {slug}", "", f"요청: {meta.get('request', '')}", "",
             f"통과 기준: 잡티 검사 통과, AI티 ≤ {AI_MAX}, TACZ 화풍 ≥ {TACZ_MIN}", "",
             "| 회차 | 잡티 | AI티 | TACZ 화풍 | 통과 | 막힌 곳 | 뭘 왜 고쳤나 |",
             "|---|---|---|---|---|---|---|"]
    for n, s in rows:
        if not s:
            lines.append(f"| {n:02d} | - | - | - | 미채점 | | |")
            continue
        lines.append(f"| {n:02d} | {'통과' if s['speck_pass'] else '불합격'} | {s['ai']:.1f} | {s['tacz']:.1f} | "
                     f"{'✅' if s['pass'] else '❌'} | {s['blocker']} | {s['fix']} |")
    lines.append("")
    for n, s in rows:
        if s:
            lines += [f"## 회차 {n:02d}", "", f"- 막힌 곳: {s['blocker']}", f"- 고친 것과 이유: {s['fix']}"]
            if s.get("next"):
                lines.append(f"- 다음 계획: {s['next']}")
            if s.get("judge_summary"):
                lines.append(f"- 심사 요약: {s['judge_summary']}")
            if s.get("speck_fails"):
                lines.append(f"- 잡티 불합격 항목: {', '.join(s['speck_fails'])}")
            lines.append("")
    with open(os.path.join(d, "LOG.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    ok = [(n, s) for n, s in rows if s and s["pass"]]
    best = sorted(ok, key=lambda t: (t[1]["tacz"] - t[1]["ai"], t[0]), reverse=True)
    pl = [f"# 통과 스냅샷: {slug}", "", "| 스냅샷 | AI티 | TACZ 화풍 | 종합(TACZ−AI) |", "|---|---|---|---|"]
    for n, s in best:
        pl.append(f"| snap_{n:02d} | {s['ai']:.1f} | {s['tacz']:.1f} | {s['tacz'] - s['ai']:.1f} |")
    if not best:
        pl.append("| (아직 없음) | | | |")
    with open(os.path.join(d, "PASSED.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(pl) + "\n")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("init"); a.add_argument("slug"); a.add_argument("request")
    a = sp.add_parser("save"); a.add_argument("slug"); a.add_argument("n", type=int); a.add_argument("files", nargs="+")
    a = sp.add_parser("attach"); a.add_argument("slug"); a.add_argument("n", type=int); a.add_argument("files", nargs="+")
    a = sp.add_parser("record"); a.add_argument("slug"); a.add_argument("n", type=int)
    a.add_argument("--speck", required=True); a.add_argument("--ai", type=float, required=True)
    a.add_argument("--tacz", type=float, required=True); a.add_argument("--judge")
    a.add_argument("--blocker", required=True); a.add_argument("--fix", required=True); a.add_argument("--next", default="")
    a = sp.add_parser("restore"); a.add_argument("slug"); a.add_argument("n", type=int)
    a = sp.add_parser("list"); a.add_argument("slug")
    o = ap.parse_args()

    if o.cmd == "init":
        os.makedirs(run_dir(o.slug), exist_ok=True)
        dump(os.path.join(run_dir(o.slug), "run.json"),
             {"slug": o.slug, "request": o.request, "started": datetime.datetime.now().isoformat(timespec="seconds"),
              "ai_max": AI_MAX, "tacz_min": TACZ_MIN, "rounds": 20})
        regen(o.slug)
    elif o.cmd == "save":
        d = snap_dir(o.slug, o.n)
        man = load(os.path.join(d, "manifest.json"), {"files": {}})
        for p in o.files:
            r = rel(p)
            dst = os.path.join(d, "files", r)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(p, dst)
            man["files"][r] = sha(p)
        dump(os.path.join(d, "manifest.json"), man)
        regen(o.slug)
        print(f"saved {len(o.files)} file(s) -> {os.path.relpath(d, ROOT)}")
    elif o.cmd == "attach":
        d = os.path.join(snap_dir(o.slug, o.n), "evidence")
        os.makedirs(d, exist_ok=True)
        for p in o.files:
            shutil.copy2(p, os.path.join(d, os.path.basename(p)))
    elif o.cmd == "record":
        d = snap_dir(o.slug, o.n)
        if not os.path.isdir(d):
            sys.exit("먼저 save 하세요")
        sk = load(o.speck)
        shutil.copy2(o.speck, os.path.join(d, "speck.json"))
        js = ""
        if o.judge:
            shutil.copy2(o.judge, os.path.join(d, "judge.json"))
            j = load(o.judge, {})
            js = j.get("summary", "")
        fails = sorted({f for r in sk.get("files", []) for f in r.get("fails", [])})
        s = {"round": o.n, "speck_pass": bool(sk.get("pass")), "speck_fails": fails, "ai": o.ai, "tacz": o.tacz,
             "blocker": o.blocker, "fix": o.fix, "next": o.next, "judge_summary": js}
        s["pass"] = s["speck_pass"] and o.ai <= AI_MAX and o.tacz >= TACZ_MIN
        dump(os.path.join(d, "score.json"), s)
        regen(o.slug)
        print(f"snap_{o.n:02d}: speck={'PASS' if s['speck_pass'] else 'FAIL'} ai={o.ai} tacz={o.tacz} -> "
              f"{'PASS' if s['pass'] else 'FAIL'}")
    elif o.cmd == "restore":
        d = snap_dir(o.slug, o.n)
        man = load(os.path.join(d, "manifest.json"))
        if not man:
            sys.exit("스냅샷 없음")
        for r in man["files"]:
            dst = os.path.join(ROOT, r)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(d, "files", r), dst)
            print("restored", r)
    elif o.cmd == "list":
        for n, s in snaps(o.slug):
            if s:
                print(f"snap_{n:02d} speck={'P' if s['speck_pass'] else 'F'} ai={s['ai']:.1f} tacz={s['tacz']:.1f} "
                      f"{'PASS' if s['pass'] else 'fail'}")
            else:
                print(f"snap_{n:02d} (미채점)")


if __name__ == "__main__":
    main()
