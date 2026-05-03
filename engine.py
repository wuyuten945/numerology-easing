"""
engine.py — 數字易經分析核心引擎 v1.0

依《數字易經分析系統 SPEC v1.0 final》實作。

主要對外接口：
  analyze(seq, mode="general")
    → 回傳 dict 含磁場計數、規則套用紀錄、能量強化標記、能量流向

  analyze_id_full(id_str)
    → 完整身分證分析（含年齡分區 + 後天號碼搭配）

  recommend(constraints, top_n=10)
    → 推薦號碼 Top N

  age_mapping(id_str)
    → 身分證年齡分區（11 區，第六區跨 20 年）

設計原則：
  - Pure functions（除了讀 magnets.json）
  - 不依賴 Flask / Web / DB
  - 所有規則套用順序按 SPEC §3.5 Step 1-8
"""
from __future__ import annotations

import json
import re
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ════════════════════════════════════════════════════════════
# 全域常數與資料載入
# ════════════════════════════════════════════════════════════

DATA_DIR = Path(__file__).parent / "data"

with open(DATA_DIR / "magnets.json", encoding="utf-8") as f:
    MAGNETS: dict = json.load(f)

with open(DATA_DIR / "alphabet.json", encoding="utf-8") as f:
    ALPHABET: dict = json.load(f)

with open(DATA_DIR / "flow_interpretations.json", encoding="utf-8") as f:
    FLOW_INTERPRETATIONS: dict = json.load(f)


LEVEL_WEIGHT = {0: 0.0, 1: 1.00, 2: 0.75, 3: 0.50, 4: 0.25}
GOOD_MAGNETS = {"天醫", "生氣", "延年", "伏位"}
BAD_MAGNETS = {"絕命", "五鬼", "六煞", "禍害"}
ALL_MAGNETS = GOOD_MAGNETS | BAD_MAGNETS  # 8 磁場
DELAY_PAIRS = {"19", "91", "78", "87", "34", "43", "26", "62"}  # 延年配對（B5 用）


# ════════════════════════════════════════════════════════════
# Step 1: 字母轉數字
# ════════════════════════════════════════════════════════════

def letter_to_digits(s: str, mode: str = "general") -> str:
    """
    字母轉數字。支援字母出現在 *任意位置*（車牌「3185E2」、「ABC-1234」皆可）。

    mode="general"：開頭字母區塊轉碼後去前置 0（例：A=01 → 1，ABC=010203 → 10203）
    mode="id"：身分證模式，開頭 0 不消去（例：A=01 保留）

    處理流程：
      1. 去除非字母數字字元（破折號、空白等）
      2. 找連續開頭字母區塊 → 全部轉碼 → general 模式去前置 0
      3. 剩餘字串逐字元處理：字母轉 2 位數字、數字保留
    """
    if not s:
        return ""
    s = re.sub(r"[^A-Za-z0-9]", "", s)
    if not s:
        return ""
    # 開頭字母區塊
    leading_end = 0
    while leading_end < len(s) and s[leading_end].isalpha():
        leading_end += 1
    leading_parts = []
    for c in s[:leading_end]:
        letter = c.upper()
        if letter not in ALPHABET:
            raise ValueError(f"未知字母: {letter}")
        leading_parts.append(ALPHABET[letter])
    leading = "".join(leading_parts)
    if mode == "general" and leading:
        leading = leading.lstrip("0") or "0"
    # 剩餘字元逐個處理（中間 / 尾段字母也轉碼）
    rest_parts = []
    for c in s[leading_end:]:
        if c.isalpha():
            letter = c.upper()
            if letter not in ALPHABET:
                raise ValueError(f"未知字母: {letter}")
            rest_parts.append(ALPHABET[letter])
        else:
            rest_parts.append(c)
    return leading + "".join(rest_parts)


# ════════════════════════════════════════════════════════════
# Step 2: 化簡（套用 B1-B5 + C 時效延續）
# ════════════════════════════════════════════════════════════

def simplify(seq: str) -> dict:
    """
    化簡數字串（v1.0.4 含原始位置追蹤）。

    處理流程同 v1.0.3，外加追蹤每個簡化後字符對應的「原始位置」，
    讓 age_mapping 可以正確處理 5 刪除導致的「年齡吸收」現象（例：14 生氣覆蓋 20-30）。

    回傳：{
      'simplified': str,
      'origin_positions': list[int],  # 每個簡化後字符對應的原始 0-indexed 位置
      'transformations': list[dict],
      'delay_count': int,
    }
    """
    transformations = []
    delay_count = 0

    if not seq:
        return {
            "simplified": "",
            "origin_positions": [],
            "transformations": [],
            "delay_count": 0,
        }

    chars = list(seq)
    n = len(chars)

    # ─── B5: 5 在延年配對中間（先掃描，標記 delay_indices）───
    delay_indices = set()
    i = 1
    while i < n - 1:
        if chars[i] == "5":
            a, b = chars[i-1], chars[i+1]
            if a not in ("0", "5") and b not in ("0", "5"):
                pair = a + b
                if pair in DELAY_PAIRS:
                    delay_indices.add(i)
                    delay_count += 1
                    transformations.append({
                        "step": "B5",
                        "position": i,
                        "note": f"5 在延年 {pair} 中間，延年延長 1 次（刪除 5、加 1 個延年配對）",
                    })
        i += 1

    # ─── B4 + B5: 刪除中間的 5（同步追蹤 origin_positions）───
    new_chars = []
    new_origins = []  # 每個保留 char 對應的原始位置
    for i, c in enumerate(chars):
        if c == "5" and 0 < i < n - 1:
            if i not in delay_indices:
                transformations.append({
                    "step": "B4",
                    "position": i,
                    "note": "5 在串中間，自動刪去",
                })
            continue
        new_chars.append(c)
        new_origins.append(i)

    # ─── B1/B2/B3 數字層重寫：0 與剩餘 5（邊緣）→ 向鄰位同化 ───
    iter_count = 0
    while iter_count < 50:
        iter_count += 1
        changed = False
        n2 = len(new_chars)
        for i in range(n2):
            c = new_chars[i]
            if c not in ("0", "5"):
                continue
            replacement = None
            if i > 0 and new_chars[i-1] not in ("0", "5"):
                replacement = new_chars[i-1]
                direction = "左"
            elif i < n2 - 1 and new_chars[i+1] not in ("0", "5"):
                replacement = new_chars[i+1]
                direction = "右"
            if replacement is not None:
                old = new_chars[i]
                new_chars[i] = replacement
                transformations.append({
                    "step": "B1/B2/B3",
                    "position": i,
                    "note": f"位元 {old} 向{direction}鄰同化為 {replacement}",
                })
                changed = True
                break
        if not changed:
            break

    simplified = "".join(new_chars)

    return {
        "simplified": simplified,
        "origin_positions": new_origins,
        "transformations": transformations,
        "delay_count": delay_count,
    }


# ════════════════════════════════════════════════════════════
# Step 3-4: 拆配對 + 查表
# ════════════════════════════════════════════════════════════

def parse_pairs(seq: str) -> list[dict]:
    """
    把字串拆成兩兩相鄰的配對 + 查表。
    每個配對處理 0/5 同化（B1, B2, B3）。

    回傳：list[dict]，每筆含：
      raw_pair, after_assimilation, magnet, type, level, weight, trait
    """
    pairs = []
    if len(seq) < 2:
        return pairs
    for i in range(len(seq) - 1):
        a, b = seq[i], seq[i+1]
        raw = a + b
        info = MAGNETS[raw].copy()
        # 處理同化
        if info["magnet"] == "中性" and info.get("assimilate_to"):
            assim_pair = info["assimilate_to"]
            assim_info = MAGNETS[assim_pair]
            pairs.append({
                "position": i,
                "raw_pair": raw,
                "after_assimilation": assim_pair,
                "magnet": assim_info["magnet"],
                "type": assim_info["type"],
                "level": assim_info["level"],
                "weight": assim_info["weight"],
                "trait": assim_info["trait"],
                "assimilated": True,
            })
        else:
            pairs.append({
                "position": i,
                "raw_pair": raw,
                "after_assimilation": raw,
                "magnet": info["magnet"],
                "type": info["type"],
                "level": info["level"],
                "weight": info["weight"],
                "trait": info["trait"],
                "assimilated": False,
            })
    return pairs


# ════════════════════════════════════════════════════════════
# Step 5: 相剋規則 A1, A3, A4, A5
# ════════════════════════════════════════════════════════════

def apply_A1(pairs: list, rules_log: list):
    """A1 天醫剋絕命（不相鄰時）：一對一抵銷。

    重要（v1.0.2）：跳過已被 A2 加倍的絕命（A2 涵蓋 A1）。
    """
    # 找出所有非緊鄰的 (天醫_idx, 絕命_idx) 對
    tianyi_indices = [i for i, p in enumerate(pairs) if p["magnet"] == "天醫" and p.get("active", True)]
    jueming_indices = [i for i, p in enumerate(pairs)
                       if p["magnet"] == "絕命"
                       and p.get("active", True)
                       and not p.get("a2_amplified", False)]  # 跳過已加倍

    # 相鄰的對由 A2 處理，這裡只處理「不相鄰」
    pending_tianyi = list(tianyi_indices)
    pending_jueming = list(jueming_indices)

    consumed = []
    for ti in tianyi_indices:
        for ji in pending_jueming:
            if abs(ti - ji) > 1:  # 不相鄰
                # 一對一抵銷
                pairs[ti]["consumed_by_rule"] = "A1"
                pairs[ji]["consumed_by_rule"] = "A1"
                pairs[ti]["active"] = False
                pairs[ji]["active"] = False
                rules_log.append({
                    "rule": "A1",
                    "note": f"天醫(pos={ti}) 消 絕命(pos={ji})",
                })
                pending_jueming.remove(ji)
                consumed.append(ti)
                break  # 一個天醫只消一個絕命
    return pairs


def apply_A2(pairs: list, rules_log: list):
    """A2 絕命緊鄰加倍（v1.0.2 鏈式複利版）：

    新邏輯（用戶 2026-05-02 確認）：
      - 偵測絕命連鎖（連續絕命）
      - 總加倍係數 = Π(1 + 每個絕命的級別權重)，例如連續兩個 L1 絕命 = 2 × 2 = ×4
      - 套用到連鎖左右的非中性磁場（鎖鏈邊界的非絕命鄰居）
      - 每個鎖鏈內的絕命都標記 a2_amplified=True，避免被 A1 抵銷
    """
    i = 0
    while i < len(pairs):
        p = pairs[i]
        if p["magnet"] != "絕命" or not p.get("active", True):
            i += 1
            continue
        # 找絕命連鎖
        j = i
        while (j < len(pairs)
               and pairs[j]["magnet"] == "絕命"
               and pairs[j].get("active", True)):
            j += 1
        # 連鎖是 pairs[i:j]
        chain_size = j - i

        # 計算總加倍係數（複利）
        total_factor = 1.0
        for k in range(i, j):
            total_factor *= (1 + LEVEL_WEIGHT[pairs[k]["level"]])

        # 標記連鎖內所有絕命為 a2_amplified（A1 跳過）
        for k in range(i, j):
            pairs[k]["a2_amplified"] = True

        # 左鄰非中性放大
        if i > 0 and pairs[i-1].get("active", True) and pairs[i-1]["magnet"] != "中性":
            target = pairs[i-1]
            old_w = target["weight"]
            target["weight"] = old_w * total_factor
            target["amplified_by"] = f"A2 chain idx {i}-{j-1}"
            rules_log.append({
                "rule": "A2-chain",
                "note": (f"絕命鏈(idx {i}-{j-1}, {chain_size} 個) "
                         f"放大左鄰 {target['magnet']}(idx {i-1}) "
                         f"{old_w:.2f} × {total_factor:.2f} = {target['weight']:.2f}"),
            })
        # 右鄰非中性放大
        if j < len(pairs) and pairs[j].get("active", True) and pairs[j]["magnet"] != "中性":
            target = pairs[j]
            old_w = target["weight"]
            target["weight"] = old_w * total_factor
            target["amplified_by"] = f"A2 chain idx {i}-{j-1}"
            rules_log.append({
                "rule": "A2-chain",
                "note": (f"絕命鏈(idx {i}-{j-1}, {chain_size} 個) "
                         f"放大右鄰 {target['magnet']}(idx {j}) "
                         f"{old_w:.2f} × {total_factor:.2f} = {target['weight']:.2f}"),
            })
        i = j
    return pairs


def apply_A3(pairs: list, rules_log: list):
    """A3 延年壓六煞：一對一抵銷（不論相鄰）。"""
    yannian = [i for i, p in enumerate(pairs) if p["magnet"] == "延年" and p.get("active", True)]
    liusha = [i for i, p in enumerate(pairs) if p["magnet"] == "六煞" and p.get("active", True)]

    pending_l = list(liusha)
    for yi in yannian:
        if pending_l:
            li = pending_l.pop(0)
            pairs[yi]["consumed_by_rule"] = "A3"
            pairs[li]["consumed_by_rule"] = "A3"
            pairs[yi]["active"] = False
            pairs[li]["active"] = False
            rules_log.append({
                "rule": "A3",
                "note": f"延年(pos={yi}) 消 六煞(pos={li})",
            })
    return pairs


def apply_A4(pairs: list, rules_log: list):
    """A4 生氣組合消禍害（整字串範圍，不需順序、不需緊鄰）。

    觸發條件：整段字串內存在以下任一：
      ① 兩個生氣
      ② 一個生氣 + 一個延年
      ③ 一個生氣 + 一個伏位
    每組合 → 消一個禍害。
    """
    # 取仍 active 的禍害
    huohai = [i for i, p in enumerate(pairs) if p["magnet"] == "禍害" and p.get("active", True)]
    if not huohai:
        return pairs

    # 計算可用「生氣組合」的數量
    shengqi = [i for i, p in enumerate(pairs) if p["magnet"] == "生氣" and p.get("active", True)]
    yannian = [i for i, p in enumerate(pairs) if p["magnet"] == "延年" and p.get("active", True)]
    fuwei = [i for i, p in enumerate(pairs) if p["magnet"] == "伏位" and p.get("active", True)]

    # 每個禍害需要一組組合來消
    sq = list(shengqi)
    yn = list(yannian)
    fw = list(fuwei)
    pending_h = list(huohai)

    for hi in pending_h:
        consumed = False
        # ① 兩個生氣
        if len(sq) >= 2:
            s1, s2 = sq.pop(0), sq.pop(0)
            pairs[hi]["consumed_by_rule"] = "A4-①"
            pairs[s1]["consumed_by_rule"] = "A4-①"
            pairs[s2]["consumed_by_rule"] = "A4-①"
            pairs[hi]["active"] = False
            pairs[s1]["active"] = False
            pairs[s2]["active"] = False
            rules_log.append({
                "rule": "A4-①",
                "note": f"兩個生氣(pos={s1},{s2}) 消 禍害(pos={hi})",
            })
            consumed = True
        # ② 一個生氣 + 一個延年
        elif sq and yn:
            s, y = sq.pop(0), yn.pop(0)
            pairs[hi]["consumed_by_rule"] = "A4-②"
            pairs[s]["consumed_by_rule"] = "A4-②"
            pairs[y]["consumed_by_rule"] = "A4-②"
            pairs[hi]["active"] = False
            pairs[s]["active"] = False
            pairs[y]["active"] = False
            rules_log.append({
                "rule": "A4-②",
                "note": f"生氣(pos={s}) + 延年(pos={y}) 消 禍害(pos={hi})",
            })
            consumed = True
        # ③ 一個生氣 + 一個伏位
        elif sq and fw:
            s, f = sq.pop(0), fw.pop(0)
            pairs[hi]["consumed_by_rule"] = "A4-③"
            pairs[s]["consumed_by_rule"] = "A4-③"
            pairs[f]["consumed_by_rule"] = "A4-③"
            pairs[hi]["active"] = False
            pairs[s]["active"] = False
            pairs[f]["active"] = False
            rules_log.append({
                "rule": "A4-③",
                "note": f"生氣(pos={s}) + 伏位(pos={f}) 消 禍害(pos={hi})",
            })
            consumed = True
    return pairs


def apply_A5(pairs: list, rules_log: list, simplified_seq: str):
    """A5 生氣+天醫+延年消五鬼：必須緊鄰、順序固定、第 2-3 字不可分開。

    從 simplified_seq 找 4 個連續數字 abcd 滿足：
      (a,b)=生氣, (b,c)=天醫, (c,d)=延年

    每組 → 消一個五鬼，並依 5 時效延續次數加倍效果。

    注意：simplified_seq 是 simplify() 處理過的字串（5 已部分刪除/保留）。
    我們需要從原始字串重新檢查 a-b 之間或 c-d 之間是否有 5（C 時效）。
    """
    # 先在原始字串裡找連續 abcd 模式
    n = len(simplified_seq)
    if n < 4:
        return pairs
    found_combos = []
    i = 0
    while i <= n - 4:
        a = simplified_seq[i]
        b = simplified_seq[i+1]
        c = simplified_seq[i+2]
        d = simplified_seq[i+3]
        if a in "05" or b in "05" or c in "05" or d in "05":
            i += 1
            continue
        sq_pair = a + b
        ty_pair = b + c
        yn_pair = c + d
        if (MAGNETS[sq_pair]["magnet"] == "生氣"
            and MAGNETS[ty_pair]["magnet"] == "天醫"
            and MAGNETS[yn_pair]["magnet"] == "延年"):
            found_combos.append((i, i+3))
        i += 1

    # 每個組合消一個五鬼
    wugui = [i for i, p in enumerate(pairs) if p["magnet"] == "五鬼" and p.get("active", True)]
    pending_w = list(wugui)

    for combo_start, combo_end in found_combos:
        if not pending_w:
            break
        wi = pending_w.pop(0)
        pairs[wi]["consumed_by_rule"] = "A5"
        pairs[wi]["active"] = False
        # 注意：消費的「生氣 / 天醫 / 延年」對應 pairs 中的 position
        # combo_start 是字串位置，pairs 的 position 是配對起始位置
        # 配對 (a,b) 的 position 等於 a 在字串的位置
        sq_pos = combo_start
        ty_pos = combo_start + 1
        yn_pos = combo_start + 2
        for ppos in (sq_pos, ty_pos, yn_pos):
            if ppos < len(pairs):
                pairs[ppos]["consumed_by_rule"] = "A5"
                pairs[ppos]["active"] = False
        rules_log.append({
            "rule": "A5",
            "note": f"生氣+天醫+延年(pos={combo_start}-{combo_end}) 消 五鬼(pos={wi})",
        })
    return pairs


# ════════════════════════════════════════════════════════════
# Step 7: 伏位特殊規則 D1-D3
# ════════════════════════════════════════════════════════════

def apply_D(pairs: list, original_seq: str) -> dict:
    """D1-D3 伏位特殊規則。

    D1：伏位 ≥ 6 個 → 黑馬之姿
    D2：伏位 = 3 個 → 行動力差
    D3：整段 5 的數量 ≥ 3 → 有耐心
    """
    fuwei_count = sum(1 for p in pairs if p["magnet"] == "伏位")
    five_count = original_seq.count("5")
    flags = []
    if fuwei_count >= 6:
        flags.append({"flag": "D1", "note": f"伏位 ×{fuwei_count}：黑馬之姿（潛龍勿用）"})
    elif fuwei_count == 3:
        flags.append({"flag": "D2", "note": f"伏位 ×{fuwei_count}：行動力差"})
    if five_count >= 3:
        flags.append({"flag": "D3", "note": f"整段含 5 ×{five_count}：有耐心"})
    return {"flags": flags, "fuwei_count": fuwei_count, "five_count": five_count}


# ════════════════════════════════════════════════════════════
# Step 8: 磁場計數 + 內部分數
# ════════════════════════════════════════════════════════════

def annotate_fuwei_continuity(pairs: list):
    """為伏位配對標記「延續」來源（用戶要求 v1.0.3）。

    規則：
      - 伏位 緊接非伏位 → 延續那個非伏位磁場
      - 伏位 緊接伏位 → 繼承前一個伏位的延續來源（傳遞）
      - 開頭就是伏位 → 純伏位（無延續）
    """
    last_non_fuwei = None  # 上次見到的非伏位磁場
    for p in pairs:
        if not p.get("active", True):
            continue
        m = p["magnet"]
        if m == "伏位":
            if last_non_fuwei:
                p["continues"] = last_non_fuwei
            # else: 純伏位（無 continues 標記）
        elif m != "中性":
            last_non_fuwei = m


def fuwei_breakdown(pairs: list) -> dict:
    """伏位細分計數：返回 {延續XX: count} 跟 {pure: count}。"""
    breakdown = {}
    pure = 0
    for p in pairs:
        if not p.get("active", True) or p["magnet"] != "伏位":
            continue
        if p.get("continues"):
            key = p["continues"]
            breakdown[key] = breakdown.get(key, 0) + 1
        else:
            pure += 1
    if pure:
        breakdown["純伏位"] = pure
    return breakdown


def magnet_count(pairs: list) -> dict:
    """統計各磁場的「active」配對數量（v1.0 對 UI 公開）。

    特殊處理：**連續延年配對用邏輯計數**（每 2 個物理對 = 1 個邏輯延年）。
    用戶 SPEC §12.1 (b)：「1919 邏輯算 2 個（非物理 3 對）」
    其他磁場用物理計數（如 1818 = 五鬼 ×3）。
    """
    counter = {m: 0 for m in ALL_MAGNETS}
    counter["中性"] = 0

    # 先標記連續延年的「邏輯計數位置」（跳過 B5 補入的 extended 延年）
    yan_logical_marks = set()
    i = 0
    while i < len(pairs):
        p = pairs[i]
        if (p.get("active", True) and p["magnet"] == "延年" and not p.get("extended")):
            j = i
            while (j < len(pairs)
                   and pairs[j].get("active", True)
                   and pairs[j]["magnet"] == "延年"
                   and not pairs[j].get("extended")):
                j += 1
            count = j - i
            logical = (count + 1) // 2  # 邏輯計數：(物理數+1)/2
            for k in range(logical):
                yan_logical_marks.add(i + k)
            i = j
        else:
            i += 1

    for idx, p in enumerate(pairs):
        if not p.get("active", True):
            continue
        m = p["magnet"]
        if m == "延年":
            if p.get("extended"):
                counter[m] += 1  # B5 補入的，獨立計數
            elif idx in yan_logical_marks:
                counter[m] += 1
            # 不在標記內的延年配對：算「滑動產生」，不另計
        elif m in counter:
            counter[m] += 1
    return counter


def internal_score(pairs: list) -> float:
    """內部用：用權重計算總分（已套用所有規則後）。"""
    score = 0.0
    for p in pairs:
        if not p.get("active", True):
            continue
        if p["type"] == "吉":
            score += p["weight"]
        elif p["type"] == "凶":
            score -= p["weight"]
    return score


def duplicate_marks(pairs: list) -> list[str]:
    """重複磁場累加標記（純客觀次數，無閾值）。"""
    counter = magnet_count(pairs)
    marks = []
    for m, n in counter.items():
        if m == "中性":
            continue
        if n >= 2:
            note = "能量強化" if n >= 3 else "重複"
            marks.append(f"{m} ×{n}（{note}）")
    return marks


def energy_flow(pairs: list) -> list[dict]:
    """能量流向（連續配對的 magnet → magnet 過渡）。"""
    flow = []
    actives = [p for p in pairs if p.get("active", True)]
    for i in range(len(actives) - 1):
        a, b = actives[i], actives[i+1]
        key = f"{a['magnet']}->{b['magnet']}"
        interp = FLOW_INTERPRETATIONS.get(key, None)
        if interp:
            flow.append({
                "from": a["magnet"],
                "to": b["magnet"],
                "from_pos": a["position"],
                "interpretation": interp,
            })
    return flow


# ════════════════════════════════════════════════════════════
# 主分析入口
# ════════════════════════════════════════════════════════════

def analyze(seq: str, mode: str = "general") -> dict:
    """
    主分析入口。輸入字串（含字母或純數字），輸出完整分析結果。

    mode="general"：一般號碼（電話、車牌等），字母前置 0 消去
    mode="id"：身分證模式，0 不消去
    """
    rules_log = []

    # Step 1: 字母轉數字
    decoded = letter_to_digits(seq, mode=mode)

    # Step 2: 化簡（B1-B5 + C 候選）
    simp_result = simplify(decoded)
    simplified = simp_result["simplified"]
    delay_count = simp_result.get("delay_count", 0)

    # Step 3-4: 拆配對 + 查表（含 0/5 同化）
    pairs = parse_pairs(simplified)

    # B5 延年延長：補 delay_count 個額外的延年配對（用 19 作預設代表）
    for d_idx in range(delay_count):
        pairs.append({
            "position": len(pairs) + d_idx + 1000,  # 用大數字避開實際 position 衝突
            "raw_pair": "19",
            "after_assimilation": "19",
            "magnet": "延年",
            "type": "吉",
            "level": 1,
            "weight": 1.0,
            "trait": "（B5 延年延長補入）",
            "assimilated": False,
            "extended": True,  # 標記為延長產生
        })

    # Step 5+6 重排（v1.0.2）：A2 先跑，標記 a2_amplified，再跑 A1（跳過已加倍）
    # Step 6: 緊鄰絕命加倍（連鎖複利）— 必須先於 A1
    apply_A2(pairs, rules_log)

    # Step 5: 相剋規則
    apply_A1(pairs, rules_log)
    apply_A3(pairs, rules_log)
    apply_A4(pairs, rules_log)
    apply_A5(pairs, rules_log, simplified)

    # Step 7: 伏位特殊
    d_result = apply_D(pairs, decoded)

    # Step 7.5: 標記伏位的「延續」來源
    annotate_fuwei_continuity(pairs)

    # Step 8: 磁場計數
    counts = magnet_count(pairs)
    fuwei_detail = fuwei_breakdown(pairs)
    score = internal_score(pairs)
    marks = duplicate_marks(pairs)
    flow = energy_flow(pairs)

    return {
        "input": seq,
        "decoded": decoded,
        "simplified": simplified,
        "transformations": simp_result["transformations"],
        "pairs": pairs,
        "rules_applied": rules_log,
        "magnet_count": counts,
        "fuwei_breakdown": fuwei_detail,
        "duplicate_marks": marks,
        "energy_flow": flow,
        "fuwei_flags": d_result["flags"],
        "internal_score": round(score, 4),
        "delay_count": simp_result.get("delay_count", 0),
    }


# ════════════════════════════════════════════════════════════
# 身分證年齡分區（§4.4）
# ════════════════════════════════════════════════════════════

@dataclass
class AgeRegion:
    region_id: int
    age_range: str
    midpoint_age: int
    pair: str
    magnet: str
    level: int
    interpretation: str = ""

    def to_dict(self) -> dict:
        return {
            "region_id": self.region_id,
            "age_range": self.age_range,
            "midpoint_age": self.midpoint_age,
            "pair": self.pair,
            "magnet": self.magnet,
            "level": self.level,
            "interpretation": self.interpretation,
        }


def _classify_pair(pair_str: str) -> tuple:
    """查 magnets.json 並處理 0/5 同化，回傳 (magnet, level, trait)。"""
    info = MAGNETS[pair_str]
    if info["magnet"] == "中性" and info.get("assimilate_to"):
        assim_info = MAGNETS[info["assimilate_to"]]
        return assim_info["magnet"], assim_info["level"], info.get("trait", "—")
    return info["magnet"], info["level"], info.get("trait", "—")


def _zone_age_range(zone_id: int) -> tuple[int, int]:
    """身分證 11 位區段的年齡範圍。

    Z1-Z5 各 10 年；Z6 跨 20 年（50-70）；Z7+ 各 10 年。
    """
    if zone_id <= 5:
        return ((zone_id - 1) * 10, zone_id * 10)
    elif zone_id == 6:
        return (50, 70)
    else:
        return (70 + (zone_id - 7) * 10, 80 + (zone_id - 7) * 10)


def age_mapping(id_str: str, max_age: int = 70) -> dict:
    """身分證年齡分區分析（v1.0.5 zone-aware + 重疊主磁場範圍）。

    用戶 2026-05-02 規則：
      - 主配對（origin_a 偶數）= 該區的主磁場，覆蓋整區（10 年；Z6 為 20 年）
      - 過渡配對（origin_a 奇數）= 區段中點冒出的新磁場，覆蓋兩區中點到下區中點
      - 5 刪除導致配對「吸收」相鄰位置：age_end 額外延伸 5 年
      - 伏位主配對若 continues 某磁場，將該磁場區間延伸至此區結尾

    範例 M121540331：
      Z3 主 14 生氣 (20-30) + Z4 主 44 伏位延續生氣 (30-40) → 生氣 20-40
      T4-5 43 延年 (35-45) + Z5 主 33 伏位延續延年 (40-50) → 延年 35-50
      T5-6 31 天醫 (45-60) + Z6 主 11 伏位延續天醫 (50-70) → 天醫 45-70
    """
    decoded = letter_to_digits(id_str, mode="id")
    if len(decoded) != 11:
        raise ValueError(f"身分證解碼長度應為 11，實際 {len(decoded)}: {decoded}")

    simp = simplify(decoded)
    simplified = simp["simplified"]
    origins = simp["origin_positions"]
    delay_count = simp["delay_count"]

    if not simplified:
        return {
            "id_decoded": decoded, "simplified": simplified,
            "delay_count": delay_count, "timeline": [], "primary_ranges": [],
        }

    # 循環延伸 simplified 字串至涵蓋 max_age 歲
    # 每個 cycle 加 11 到 origin（身分證 11 位）
    cycled_chars = list(simplified)
    cycled_origins = list(origins)
    n_simp = len(simplified)
    cycle_count = 1
    while cycled_origins[-1] * 5 < max_age + 10:
        for i in range(n_simp):
            cycled_chars.append(simplified[i])
            cycled_origins.append(origins[i] + cycle_count * 11)
        cycle_count += 1
        if cycle_count > 10:  # 安全停止
            break

    # 建配對（含 origin 追蹤）
    pairs = []
    for i in range(len(cycled_chars) - 1):
        a, b = cycled_chars[i], cycled_chars[i+1]
        oa, ob = cycled_origins[i], cycled_origins[i+1]
        info = MAGNETS[a + b]
        if info["magnet"] == "中性" and info.get("assimilate_to"):
            assim = MAGNETS[info["assimilate_to"]]
            magnet = assim["magnet"]
            level = assim["level"]
            display = f"{a+b}→{info['assimilate_to']}"
        else:
            magnet = info["magnet"]
            level = info["level"]
            display = a + b
        is_main = (oa % 2 == 0)
        # 計算 age_start, age_end（zone-aware）
        absorbed_extra = (ob - oa - 1) * 5  # 5 刪除吸收的額外年齡
        if is_main:
            zone_id = oa // 2 + 1
            zs, ze = _zone_age_range(zone_id)
            age_start = zs
            age_end = ze + absorbed_extra
            label = f"Z{zone_id} 主"
        else:
            i_z = (oa + 1) // 2
            z1 = _zone_age_range(i_z)
            z2 = _zone_age_range(i_z + 1)
            age_start = (z1[0] + z1[1]) // 2  # Z_i 中點
            age_end = (z2[0] + z2[1]) // 2 + absorbed_extra  # Z_{i+1} 中點
            label = f"T{i_z}-{i_z+1}"
        pairs.append({
            "raw_pair": a + b,
            "display": display,
            "magnet": magnet,
            "level": level,
            "origin_a": oa,
            "origin_b": ob,
            "is_main": is_main,
            "label": label,
            "age_start": age_start,
            "age_end": age_end,
        })
        if age_start >= max_age:
            break

    # 標記伏位延續來源
    last_non_fuwei = None
    for p in pairs:
        m = p["magnet"]
        if m == "伏位" and last_non_fuwei:
            p["continues"] = last_non_fuwei
        elif m not in ("中性", "伏位"):
            last_non_fuwei = m

    # Timeline 顯示
    timeline = []
    for p in pairs:
        timeline.append({
            "label": p["label"],
            "age_range": f"{p['age_start']}-{p['age_end']}",
            "age_start": p["age_start"],
            "age_end": p["age_end"],
            "pair": p["display"],
            "magnet": p["magnet"],
            "level": p["level"],
            "is_main": p["is_main"],
            "continues": p.get("continues"),
        })

    # Primary ranges 規則（用戶 2026-05-02 確認）：
    #   - 主配對非伏位：永遠開啟新區間（即使同磁場連續，也分開顯示）
    #   - 過渡配對非伏位：若磁場與 last_emerged 相同 → 不變動（僅確認）；不同 → 新區間
    #   - 伏位（主或過渡）有 continues：延伸該磁場最近區間到此 age_end
    ranges = []
    last_emerged = None
    for p in pairs:
        m = p["magnet"]
        if m == "中性":
            continue
        if m == "伏位":
            target = p.get("continues")
            if target:
                for r in reversed(ranges):
                    if r["magnet"] == target:
                        r["end"] = max(r["end"], p["age_end"])
                        break
            continue
        if p["is_main"]:
            # 主配對非伏位：總是新區間
            ranges.append({"magnet": m, "start": p["age_start"], "end": p["age_end"]})
            last_emerged = m
        else:
            # 過渡配對非伏位
            if m != last_emerged:
                ranges.append({"magnet": m, "start": p["age_start"], "end": p["age_end"]})
                last_emerged = m
            # else: 同磁場過渡 → 不變動

    # 截斷在 max_age（過濾完全超出範圍者）
    filtered = []
    for r in ranges:
        if r["start"] >= max_age:
            continue
        if r["end"] > max_age:
            r["end"] = max_age
        filtered.append(r)
    ranges = filtered

    return {
        "id_decoded": decoded,
        "simplified": simplified,
        "origin_positions": origins,
        "delay_count": delay_count,
        "timeline": timeline,
        "primary_ranges": ranges,
    }


# ════════════════════════════════════════════════════════════
# 推薦演算法（§4.2）
# ════════════════════════════════════════════════════════════

def generate_candidates(constraints: dict, n: int = 1000) -> list[str]:
    """產生 n 個候選號碼。

    車牌（purpose='license'）：監理單位不發含 4 的號碼，suffix 從 {0,1,2,3,5,6,7,8,9} 取。
    """
    length = constraints.get("length", 10)
    prefix = constraints.get("prefix", "")
    purpose = constraints.get("purpose", "")
    digit_pool = list("012356789") if purpose == "license" else list("0123456789")
    candidates = set()
    rest_length = length - len(prefix)
    if rest_length <= 0:
        return [prefix]
    # 上限避免無限迴圈：如池太小（如車牌只剩 9 位數，4 位 = 6561 組）
    max_unique = len(digit_pool) ** rest_length
    target = min(n, max_unique)
    while len(candidates) < target:
        rest = "".join(random.choice(digit_pool) for _ in range(rest_length))
        candidates.add(prefix + rest)
    return list(candidates)


def respects_constraints(result: dict, constraints: dict) -> bool:
    """檢查候選是否滿足排除磁場約束。"""
    counts = result["magnet_count"]
    for m in constraints.get("exclude_magnets", []):
        if counts.get(m, 0) > 0:
            return False
    for m in constraints.get("require_magnets", []):
        if counts.get(m, 0) == 0:
            return False
    return True


def recommend(constraints: dict, top_n: int = 10) -> list[dict]:
    """智能建議（§4.2）。

    流程：
      Step 1：產生 1000 個候選
      Step 2：跑 analyze() 全規則
      Step 3：按 internal_score 排序
      Step 4：（v1.0 不過濾單一磁場占比）
      Step 5：取 Top N
    """
    pool_size = constraints.get("candidate_pool", 1000)
    candidates = generate_candidates(constraints, n=pool_size)
    scored = []
    for c in candidates:
        result = analyze(c, mode="general")
        if not respects_constraints(result, constraints):
            continue
        scored.append((c, result))
    # 排序優先級（v1.0.7）：
    #   1) 凶星總數越少越好（避免 A2 連鎖絕命這種 score 高但實質差的）
    #   2) 對應吉星（require_magnets）越多越好
    #      —— 若使用者有絕命 → require=[天醫]，候選的天醫越多排越前
    #   3) 總吉星越多越好
    #   4) internal_score 越高越好（tiebreaker，含放大效應）
    require_list = constraints.get("require_magnets", []) or []
    def rank_key(item):
        mc = item[1]["magnet_count"]
        bad_total = sum(mc.get(m, 0) for m in BAD_MAGNETS)
        good_total = sum(mc.get(m, 0) for m in GOOD_MAGNETS)
        require_count = sum(mc.get(m, 0) for m in require_list)
        return (-bad_total, require_count, good_total, item[1]["internal_score"])
    scored.sort(key=rank_key, reverse=True)
    return [
        {
            "rank": i + 1,
            "number": c,
            "magnet_count": r["magnet_count"],
            "duplicate_marks": r["duplicate_marks"],
        }
        for i, (c, r) in enumerate(scored[:top_n])
    ]
