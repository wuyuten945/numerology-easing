"""
cli.py — 數字易經分析 命令列介面 v1.0

使用方式：
  python cli.py --auto --id A123456789 --phone 0912345678 --license 1234
  python cli.py --manual 13311331
  python cli.py --age A123456789
  python cli.py --recommend phone --length 10 --prefix 09 --top 5
"""
from __future__ import annotations

import argparse
import json
import sys
import io
from pathlib import Path

# 確保 stdout 為 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import engine

GOOD = {"天醫", "生氣", "延年", "伏位"}
BAD = {"絕命", "五鬼", "六煞", "禍害"}


def fmt_count(counts: dict, indent: str = "  ") -> str:
    """格式化磁場計數（吉星 ✓、凶星 ✗、中性 •）"""
    lines = []
    order = ["天醫", "生氣", "延年", "伏位", "絕命", "五鬼", "六煞", "禍害", "中性"]
    for m in order:
        n = counts.get(m, 0)
        bar_len = min(n, 10)
        bar = "█" * bar_len + "░" * (10 - bar_len)
        prefix = "✓" if m in GOOD else ("✗" if m in BAD else "•")
        lines.append(f"{indent}{prefix} {m:4} {bar} {n} 個")
    return "\n".join(lines)


def print_analysis(label: str, result: dict):
    print(f"\n{'=' * 60}")
    print(f"  {label}: {result['input']}")
    print(f"{'=' * 60}")
    print(f"  decoded:    {result['decoded']}")
    if result['simplified'] != result['decoded']:
        print(f"  simplified: {result['simplified']}")

    # 逐對配對拆解（滑動視窗）
    print()
    print("  逐對配對（滑動視窗，含 0/5 同化）:")
    physical_pairs = [p for p in result['pairs'] if not p.get('extended')]
    for p in physical_pairs:
        raw = p['raw_pair']
        after = p['after_assimilation']
        magnet = p['magnet']
        level = p['level']
        flag = ''
        if not p.get('active', True):
            consumed = p.get('consumed_by_rule', '')
            flag = f' [被 {consumed} 消除]'
        # 伏位延續標記
        cont = ''
        if magnet == '伏位' and p.get('continues'):
            cont = f' (延續{p["continues"]})'
        elif magnet == '伏位' and p.get('active', True):
            cont = ' (純伏位)'
        if raw != after:
            print(f"    {raw} → {after}  {magnet:4} L{level}{cont}{flag}")
        else:
            print(f"    {raw}      {magnet:4} L{level}{cont}{flag}")
    extended = [p for p in result['pairs'] if p.get('extended')]
    if extended:
        print(f"    ─── B5 延年延長補入 ─── ({len(extended)} 個)")
        for p in extended:
            print(f"    19 (延長)  延年 L1")

    print()
    print("  磁場分布（套用全部規則後）:")
    print(fmt_count(result['magnet_count']))

    # 伏位細分
    fuwei_bd = result.get('fuwei_breakdown', {})
    if fuwei_bd:
        print()
        print("  伏位細分:")
        for source, n in fuwei_bd.items():
            if source == "純伏位":
                print(f"    純伏位 ×{n}")
            else:
                print(f"    伏位 (延續{source}) ×{n}")
    if result.get('duplicate_marks'):
        print()
        print("  能量強化標記:")
        for m in result['duplicate_marks']:
            print(f"    • {m}")
    if result.get('rules_applied'):
        print()
        print("  規則套用:")
        for r in result['rules_applied'][:8]:  # 最多顯示 8 條
            print(f"    {r['rule']}: {r['note']}")
        if len(result['rules_applied']) > 8:
            print(f"    ... 共 {len(result['rules_applied'])} 條")
    if result.get('fuwei_flags'):
        print()
        print("  伏位特殊:")
        for f in result['fuwei_flags']:
            print(f"    {f['flag']}: {f['note']}")
    if result.get('energy_flow'):
        print()
        print("  能量流向:")
        for f in result['energy_flow'][:5]:
            print(f"    {f['from']} → {f['to']}: {f['interpretation']}")


def cmd_auto(args):
    if args.id:
        r = engine.analyze(args.id, mode="id")
        print_analysis("身分證（先天磁場）", r)
        if not args.no_age:
            am = engine.age_mapping(args.id)
            print(f"\n{'=' * 60}")
            print(f"  身分證年齡分區（{am['id_decoded']}）")
            print(f"{'=' * 60}")
            print()
            print("  Timeline（按身分證 11 位區段）:")
            for entry in am['timeline']:
                cont = ''
                if entry['magnet'] == '伏位' and entry.get('continues'):
                    cont = f" (延續{entry['continues']})"
                elif entry['magnet'] == '伏位':
                    cont = " (純伏位)"
                kind = "主" if entry['is_main'] else "過渡"
                print(f"    {entry['label']:8} {entry['age_range']:7}歲  {entry['pair']:8}  "
                      f"{entry['magnet']:4} L{entry['level']} [{kind}]{cont}")
            print()
            print("  主磁場連續影響範圍（含伏位延續，可重疊）:")
            for r in am['primary_ranges']:
                print(f"    {r['start']:3}-{r['end']:3} 歲  {r['magnet']}")
    if args.phone:
        r = engine.analyze(args.phone)
        print_analysis("電話", r)
    if args.license:
        r = engine.analyze(args.license)
        print_analysis("車牌", r)


def cmd_manual(args):
    r = engine.analyze(args.input, mode="general")
    print_analysis("手動測試", r)


def cmd_age(args):
    am = engine.age_mapping(args.input)
    print(f"\n{'=' * 70}")
    print(f"  身分證年齡分區: {args.input}")
    print(f"{'=' * 70}")
    print(f"  decoded:    {am['id_decoded']}")
    print(f"  simplified: {am['simplified']}")
    if am['delay_count']:
        print(f"  延年延長次數: {am['delay_count']} 次")

    print()
    print("  Timeline（按身分證 11 位區段：主配對 / 過渡配對）:")
    for entry in am['timeline']:
        cont = ''
        if entry['magnet'] == '伏位' and entry.get('continues'):
            cont = f" (延續{entry['continues']})"
        elif entry['magnet'] == '伏位':
            cont = " (純伏位)"
        kind = "主" if entry['is_main'] else "過渡"
        print(f"    {entry['label']:8} {entry['age_range']:7}歲  {entry['pair']:8}  "
              f"{entry['magnet']:4} L{entry['level']} [{kind}]{cont}")

    print()
    print("  主磁場連續影響範圍（含伏位延續，可重疊）:")
    for r in am['primary_ranges']:
        print(f"    {r['start']:3}-{r['end']:3} 歲  {r['magnet']}")


def cmd_recommend(args):
    constraints = {
        "purpose": args.purpose,
        "length": args.length,
        "prefix": args.prefix,
        "exclude_magnets": args.exclude.split(",") if args.exclude else [],
        "candidate_pool": args.pool,
    }
    print(f"\n{'=' * 60}")
    print(f"  智能建議: {args.purpose}（長度 {args.length}, prefix '{args.prefix}'）")
    print(f"{'=' * 60}")
    print(f"  候選池: {args.pool}, Top {args.top}")
    if args.exclude:
        print(f"  排除磁場: {args.exclude}")
    print()

    recs = engine.recommend(constraints, top_n=args.top)
    if not recs:
        print("  沒找到符合條件的推薦。")
        return
    for rec in recs:
        print(f"  排名 {rec['rank']:2}: {rec['number']}")
        counts_summary = " ".join(
            f"{m}{n}" for m, n in rec['magnet_count'].items() if n > 0
        )
        print(f"    {counts_summary}")
        if rec['duplicate_marks']:
            for m in rec['duplicate_marks']:
                print(f"    強化: {m}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="數字易經分析系統 v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python cli.py --auto --id A123456789 --phone 0912345678
  python cli.py --manual 13311331
  python cli.py --age A123456789
  python cli.py --recommend phone --length 10 --prefix 09 --top 5
""",
    )
    parser.add_argument("--auto", action="store_true", help="自動分析模式")
    parser.add_argument("--manual", dest="manual_input", help="手動測試（任意數字串）")
    parser.add_argument("--age", dest="age_input", help="身分證年齡分區分析")
    parser.add_argument("--recommend", dest="purpose",
                        choices=["phone", "license", "pin", "door"],
                        help="智能建議模式 + 用途")

    # 自動模式參數
    parser.add_argument("--id", help="身分證字號")
    parser.add_argument("--phone", help="電話")
    parser.add_argument("--license", help="車牌（4 位數字）")
    parser.add_argument("--no-age", action="store_true", help="跳過年齡分區（自動模式）")

    # 推薦模式參數
    parser.add_argument("--length", type=int, default=10, help="號碼長度")
    parser.add_argument("--prefix", default="", help="開頭限制")
    parser.add_argument("--top", type=int, default=10, help="推薦前 N 名")
    parser.add_argument("--pool", type=int, default=1000, help="候選池大小")
    parser.add_argument("--exclude", default="", help="排除磁場（逗號分隔）")

    args = parser.parse_args()

    if args.manual_input:
        args.input = args.manual_input
        cmd_manual(args)
    elif args.age_input:
        args.input = args.age_input
        cmd_age(args)
    elif args.purpose:
        cmd_recommend(args)
    elif args.auto or args.id or args.phone or args.license:
        cmd_auto(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
