#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
csv_to_rime_dict.py

修复点：CUSTOM_WORD_PINYIN 命中时，不再对其 tokens 做“英文强制大写”处理。
（也就是说：CUSTOM_WORD_PINYIN 给什么就用什么，完全原样。）

其余规则保持不变：
- 英文段（源文本里出现的 ASCII 字母连续段）输出时统一转为全大写，例如 立flag -> li FLAG
- 多音字单字统计输出到 accent.txt，并按“默认读音出现次数”降序排序读音
- 支持人名中间点、数字转读音、去重、输出多个文件
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from pypinyin import lazy_pinyin, pinyin, Style
except ImportError:
    print("缺少依赖：pypinyin。请先运行：pip install pypinyin", file=sys.stderr)
    raise


# ================= 配置区（按需修改） =================
INPUT_CSV = "thd.csv"

WEIGHT = 100
MIN_LEN = 999

NAME_SEPARATOR = "·"
COL_SEP = "\t"

OUT_FULL = "./mid/output_full.txt"
OUT_SIMP = "./mid/output_simp.txt"
OUT_ALL = "./mid/output_all.txt"
OUT_MS = "./mid/output_ms.txt"
OUT_MULTI = "./mid/output_multiaccent.txt"
OUT_NODUP = "./mid/output_nodup.txt"
OUT_ACCENT = "./mid/accent.txt"

# 单字自定义读音（最高优先级之一）
CUSTOM_PINYIN: dict[str, str] = {
    "丁": "ding",
    "万": "wan",
    "不": "bu",
    "个": "ge",
    "乃": "nai",
    "之": "zhi",
    "乙": "yi",
    "也": "ye",
    "了": "le",
    "事": "shi",
    "于": "yu",
    "亡": "wang",
    "仇": "chou",
    "介": "jie",
    "从": "cong",
    "令": "ling",
    "以": "yi",
    "仰": "yang",
    "价": "jia",
    "任": "ren",
    "份": "fen",
    "伎": "ji",
    "休": "xiu",
    "众": "zhong",
    "会": "hui",
    "伴": "ban",
    "伽": "jia",
    "位": "wei",
    "体": "ti",
    "余": "yu",
    "佛": "fo",
    "侧": "ce",
    "便": "bian",
    "信": "xin",
    "倍": "bei",
    "偲": "si",
    "僧": "seng",
    "儿": "er",
    "兔": "tu",
    "六": "liu",
    "其": "qi",
    "典": "dian",
    "兹": "zi",
    "内": "nei",
    "冒": "mao",
    "冥": "ming",
    "冰": "bing",
    "冷": "leng",
    "净": "jing",
    "凹": "ao",
    "刀": "dao",
    "切": "qie",
    "划": "hua",
    "刹": "sha",
    "刺": "ci",
    "刻": "ke",
    "前": "qian",
    "副": "fu",
    "助": "zhu",
    "勒": "le",
    "勺": "shao",
    "化": "hua",
    "匿": "ni",
    "单": "dan",
    "南": "nan",
    "卡": "ka",
    "印": "yin",
    "卵": "luan",
    "卷": "juan",
    "参": "can",
    "受": "shou",
    "古": "gu",
    "可": "ke",
    "台": "tai",
    "叶": "ye",
    "号": "hao",
    "司": "si",
    "叹": "tan",
    "吃": "chi",
    "合": "he",
    "吞": "tun",
    "吟": "yin",
    "吧": "ba",
    "听": "ting",
    "吴": "wu",
    "吽": "hong",
    "和": "he",
    "咖": "ka",
    "咪": "mi",
    "哆": "duo",
    "哈": "ha",
    "哦": "o",
    "哮": "xiao",
    "啡": "fei",
    "喰": "can",
    "嘲": "chao",
    "囃": "ca",
    "团": "tuan",
    "园": "yuan",
    "土": "tu",
    "圣": "sheng",
    "地": "di",
    "垂": "chui",
    "垠": "yin",
    "埋": "mai",
    "堇": "jin",
    "塔": "ta",
    "塞": "sai",
    "墨": "mo",
    "声": "sheng",
    "壳": "ke",
    "夏": "xia",
    "夕": "xi",
    "大": "da",
    "太": "tai",
    "失": "shi",
    "奇": "qi",
    "奏": "zou",
    "奘": "zang",
    "奥": "ao",
    "女": "nv",
    "妃": "fei",
    "妖": "yao",
    "姐": "jie",
    "姥": "mu",
    "姬": "ji",
    "娜": "na",
    "孛": "bei",
    "完": "wan",
    "客": "ke",
    "宪": "xian",
    "家": "jia",
    "容": "rong",
    "宿": "su",
    "寺": "si",
    "封": "feng",
    "射": "she",
    "将": "jiang",
    "尾": "wei",
    "居": "ju",
    "属": "shu",
    "崎": "qi",
    "巨": "ju",
    "己": "ji",
    "已": "yi",
    "币": "bi",
    "市": "shi",
    "帕": "pa",
    "幕": "mu",
    "干": "gan",
    "平": "ping",
    "年": "nian",
    "幸": "xing",
    "幺": "yao",
    "幼": "you",
    "广": "guang",
    "庄": "zhuang",
    "庇": "bi",
    "底": "di",
    "度": "du",
    "庵": "an",
    "弁": "bian",
    "弄": "nong",
    "式": "shi",
    "弟": "di",
    "弹": "dan",
    "强": "qiang",
    "彦": "yan",
    "彷": "pang",
    "得": "de",
    "御": "yu",
    "忒": "te",
    "怀": "huai",
    "怜": "lian",
    "思": "si",
    "怨": "yuan",
    "恶": "e",
    "惊": "jing",
    "愁": "chou",
    "感": "gan",
    "戎": "rong",
    "戏": "xi",
    "承": "cheng",
    "技": "ji",
    "抄": "chao",
    "把": "ba",
    "投": "tou",
    "折": "zhe",
    "拂": "fu",
    "拍": "pai",
    "挟": "xie",
    "捷": "jie",
    "探": "tan",
    "控": "kong",
    "提": "ti",
    "揭": "jie",
    "搜": "sou",
    "摩": "mo",
    "攘": "rang",
    "支": "zhi",
    "敌": "di",
    "敕": "chi",
    "数": "shu",
    "斗": "dou",
    "斥": "chi",
    "斯": "si",
    "方": "fang",
    "族": "zu",
    "无": "wu",
    "昂": "ang",
    "明": "ming",
    "昔": "xi",
    "映": "ying",
    "是": "shi",
    "景": "jing",
    "暴": "bao",
    "曾": "ceng",
    "最": "zui",
    "月": "yue",
    "有": "you",
    "服": "fu",
    "朝": "chao",
    "期": "qi",
    "末": "mo",
    "札": "zha",
    "术": "shu",
    "朱": "zhu",
    "机": "ji",
    "杂": "za",
    "杜": "du",
    "果": "guo",
    "枝": "zhi",
    "柏": "bai",
    "柜": "gui",
    "栖": "qi",
    "核": "he",
    "格": "ge",
    "桃": "tao",
    "桐": "tong",
    "桔": "ju",
    "槌": "chui",
    "槽": "cao",
    "横": "heng",
    "橙": "cheng",
    "次": "ci",
    "歇": "xie",
    "殖": "zhi",
    "毋": "wu",
    "母": "mu",
    "毒": "du",
    "比": "bi",
    "氏": "shi",
    "汀": "ting",
    "池": "chi",
    "汽": "qi",
    "沌": "dun",
    "沙": "sha",
    "治": "zhi",
    "泛": "fan",
    "波": "bo",
    "注": "zhu",
    "泷": "long",
    "洁": "jie",
    "洋": "yang",
    "洞": "dong",
    "洩": "xie",
    "活": "huo",
    "浅": "qian",
    "涡": "wo",
    "混": "hun",
    "温": "wen",
    "港": "gang",
    "渴": "ke",
    "游": "you",
    "溺": "ni",
    "漂": "piao",
    "澄": "cheng",
    "激": "ji",
    "瀑": "pu",
    "灯": "deng",
    "炎": "yan",
    "烟": "yan",
    "焉": "yan",
    "熙": "xi",
    "爆": "bao",
    "爪": "zhao",
    "片": "pian",
    "狂": "kuang",
    "狄": "di",
    "狼": "lang",
    "猎": "lie",
    "猫": "mao",
    "率": "lv",
    "王": "wang",
    "甫": "fu",
    "由": "you",
    "町": "ting",
    "畜": "chu",
    "疑": "yi",
    "痕": "hen",
    "登": "deng",
    "白": "bai",
    "百": "bai",
    "的": "de",
    "皇": "huang",
    "皿": "min",
    "盛": "sheng",
    "盼": "pan",
    "眠": "mian",
    "眩": "xuan",
    "眼": "yan",
    "矜": "jin",
    "石": "shi",
    "硬": "ying",
    "碟": "die",
    "祇": "qi",
    "祈": "qi",
    "祖": "zu",
    "祢": "mi",
    "祭": "ji",
    "离": "li",
    "种": "zhong",
    "秘": "mi",
    "积": "ji",
    "移": "yi",
    "穰": "rang",
    "穴": "xue",
    "穹": "qiong",
    "穿": "chuan",
    "窒": "zhi",
    "立": "li",
    "童": "tong",
    "簇": "cu",
    "粥": "zhou",
    "粹": "cui",
    "精": "jing",
    "红": "hong",
    "约": "yue",
    "给": "gei",
    "绿": "lv",
    "缩": "suo",
    "缺": "que",
    "羽": "yu",
    "耳": "er",
    "耶": "ye",
    "肉": "rou",
    "胜": "sheng",
    "能": "neng",
    "脉": "mai",
    "脚": "jiao",
    "臂": "bi",
    "至": "zhi",
    "臾": "yu",
    "舌": "she",
    "舍": "she",
    "般": "ban",
    "色": "se",
    "艾": "ai",
    "芥": "jie",
    "芦": "lu",
    "苑": "yuan",
    "苞": "bao",
    "若": "ruo",
    "苦": "ku",
    "英": "ying",
    "茇": "ba",
    "草": "cao",
    "荒": "huang",
    "荼": "tu",
    "莉": "li",
    "莎": "sha",
    "菅": "jian",
    "菩": "pu",
    "萌": "meng",
    "落": "luo",
    "蓝": "lan",
    "蕉": "jiao",
    "藉": "ji",
    "虫": "chong",
    "虹": "hong",
    "蚕": "can",
    "蛇": "she",
    "蛙": "wa",
    "蛾": "e",
    "蜴": "yi",
    "蝶": "die",
    "血": "xue",
    "被": "bei",
    "袿": "gui",
    "见": "jian",
    "觉": "jue",
    "角": "jiao",
    "解": "jie",
    "言": "yan",
    "识": "shi",
    "说": "shuo",
    "谜": "mi",
    "谷": "gu",
    "豫": "yu",
    "貌": "mao",
    "赫": "he",
    "超": "chao",
    "越": "yue",
    "足": "zu",
    "跋": "ba",
    "路": "lu",
    "跳": "tiao",
    "身": "shen",
    "车": "che",
    "转": "zhuan",
    "达": "da",
    "迦": "jia",
    "迭": "die",
    "逐": "zhu",
    "造": "zao",
    "逢": "feng",
    "遁": "dun",
    "遇": "yu",
    "遗": "yi",
    "那": "na",
    "邪": "xie",
    "部": "bu",
    "都": "dou",
    "醒": "xing",
    "野": "ye",
    "钿": "dian",
    "长": "zhang",
    "阻": "zu",
    "阿": "a",
    "陆": "lu",
    "限": "xian",
    "陶": "tao",
    "雀": "que",
    "零": "ling",
    "震": "zhen",
    "霍": "huo",
    "露": "lu",
    "青": "qing",
    "靡": "mi",
    "革": "ge",
    "鞠": "ju",
    "顿": "dun",
    "食": "shi",
    "餐": "can",
    "骸": "hai",
    "魄": "po",
    "鸟": "niao",
    "鹿": "lu",
    "龟": "gui",
}

# 整词自定义拼音（最高优先级）
# value 是“空格分隔”的全拼，例如 "le shan"
CUSTOM_WORD_PINYIN: dict[str, str] = {
    "西行寺幽幽子": "xi xing si you you zi",
    "二岩猯藏": "er yan tuan zang",
    "西行寺": "xi xing si",
    "猯藏": "tuan zang",
    "东方灵异传": "dong fang ling yi zhuan",
    "东方绀珠传": "dong fang gan zhu zhuan",
    "东方智灵奇传": "dong fang zhi ling qi zhuan",
    "莲台野夜行": "lian tai ye ye xing",
    "灵异传": "ling yi zhuan",
    "绀珠传": "gan zhu zhuan",
    "智灵奇传": "zhi ling qi zhuan",
    "天使传说": "tian shi chuan shuo",
    "传说中的仙境": "chuan shuo zhong de xian jing",
    "永远的乐园": "yong yuan de le yuan",
    "神魔讨绮传": "shen mo tao qi zhuan",
    "妖怪宇宙旅行": "yao guai yu zhou lv xing",
    "神域的捉迷藏生活": "shen yu de zhuo mi cang sheng huo",
    "蓬莱传说": "peng lai chuan shuo",
    "妖魔夜行": "yao mo ye xing",
    "献给已逝公主的七重奏": "xian gei yi shi gong zhu de qi chong zou",
    "幽灵乐团": "you ling yue tuan",
    "夜幕降临": "ye mu jiang lin",
    "天狗正凝视着": "tian gou zheng ning shi zhe",
    "浪漫逃飞行": "lang man tao fei xing",
    "收藏家的忧郁午后": "shou cang jia de you yu wu hou",
    "厄神降临之路": "e shen jiang lin zhi lu",
    "神明降下恩惠之雨": "shen ming jiang xia en hui zhi yu",
    "散发着香气的树叶花": "san fa zhe xiang qi de shu ye hua",
    "尸体旅行": "shi ti lv xing",
    "传说的巨神": "chuan shuo de ju shen",
    "欲望深重的灵魂": "yu wang shen zhong de ling hun",
    "大神神话传": "da shen shen hua zhuan",
    "圣德传说": "sheng de chuan shuo",
    "震撼心灵的都市传说": "zhen han xin ling de du shi chuan shuo",
    "显现的传承形态": "xian xian de chuan cheng xing tai",
    "兔已着陆": "tu yi zhao lu",
    "湖上倒映着洁净的月光": "hu shang dao ying zhe jie jing de yue guang",
    "宇宙巫女归还": "yu zhou wu nv gui huan",
    "行云流水": "xing yun liu shui",
    "魔法的笠地藏": "mo fa de li di cang",
    "是此世还是彼世": "shi ci shi hai shi bi shi",
    "只有地藏知晓的哀叹": "zhi you di zang zhi xiao de ai tan",
    "从地下的归还": "cong di xia de gui huan",
    "被水淹没的沉愁地狱": "bei shui yan mo de chen chou di yu",
    "少女秘封俱乐部": "shao nv mi feng ju le bu",
    "广重三十六号": "guang zhong san shi liu hao",
    "青木原的传说": "qing mu yuan de chuan shuo",
    "欢迎来到月面旅行团": "huan ying lai dao yue mian lv xing tuan",
    "独自一人的常陆行路": "du zi yi ren de chang lu xing lu",
    "四重存在": "si chong cun zai",
    "之后就一个人都没有了吗": "zhi hou jiu yi ge ren dou mei you le ma",
    "二重结界": "er chong jie jie",
    "少女文乐": "shao nv wen le",
    "二重黑死蝶": "er chong hei si die",
    "小行星带": "xiao xing xing dai",
    "百万鬼夜行": "bai wan gui ye xing",
    "幻想乡传说": "huan xiang xiang chuan shuo",
    "幻视调律": "huan shi tiao lv",
    "不死鸟重生": "bu si niao chong sheng",
    "西行寺无余涅槃": "xi xing si wu yu nie pan",
    "一脉单传之弹幕": "yi mai dan chuan zhi dan mu",
    "一脉单传": "yi mai dan chuan",
    "单传": "dan chuan",
    "飞行虫之巢": "fei xing chong zhi chao",
    "飞行虫": "fei xing chong",
    "地狱极乐熔毁": "di yu ji le rong hui",
    "极乐的紫色云路": "ji le de zi se yun lu",
    "魔法银河系": "mo fa yin he xi",
    "西行樱吹雪": "xi xing ying chui xue",
    "星辰降落": "xing chen jiang luo",
    "星降": "xing jiang",
    "诸行无常的琴声": "zhu xing wu chang de qin sheng",
    "诸行无常": "zhu xing wu chang",
    "薄雪草": "bao xue cao",
    "天马行空": "tian ma xing kong",
    "太田飞行阵": "tai tian fei xing zhen",
    "飞行阵": "fei xing zhen",
    "肉体强化地藏": "rou ti qiang hua di zang",
    "幻想浪漫纪行": "huan xiang lang man ji xing",
    "连缘灵烈传": "lian yuan ling lie zhuan",
    "灵烈传": "ling lie zhuan",
    "梦行远游": "meng xing yuan you",
    "鞍马乐": "an ma le",
    "海重乃汐": "hai zhong nai xi",
    "江西䌷": "jiang xi",
    "八重咲杏": "ba chong xiao xing",
    "御剑缝重子": "yu jian feng chong zi",
    "饕喰乐魔喰乐": "tao can le mo can le",
    "藏人未见": "zang ren wei jian",
    "乐冢魇音": "le zhong yan yin",
    "六地藏千鹤": "liu di zang qian he",

}
# =====================================================


# ---------- 数字转中文读音（<10000） ----------
_DIGITS = ["ling", "yi", "er", "san", "si", "wu", "liu", "qi", "ba", "jiu"]

def num_lt_10000_to_pinyin(n: int) -> list[str]:
    if n < 0 or n >= 10000:
        raise ValueError("number out of range (<10000 required)")
    if n == 0:
        return ["ling"]

    parts: list[str] = []
    qian = n // 1000
    bai = (n // 100) % 10
    shi = (n // 10) % 10
    ge = n % 10

    if qian:
        parts += [_DIGITS[qian], "qian"]

    if bai:
        parts += [_DIGITS[bai], "bai"]
    else:
        if qian and (shi or ge):
            parts += ["ling"]

    if shi:
        if not qian and not bai and shi == 1:
            parts += ["shi"]
        else:
            parts += [_DIGITS[shi], "shi"]
    else:
        if (qian or bai) and ge:
            parts += ["ling"]

    if ge:
        parts += [_DIGITS[ge]]
    return parts


# ---------- 分段：汉字 / 数字 / 英文(ASCII字母连续段) / 其他 ----------
@dataclass(frozen=True)
class Segment:
    kind: str   # "han" | "num" | "eng" | "other"
    text: str

def is_han_char(ch: str) -> bool:
    return len(ch) == 1 and ("\u4e00" <= ch <= "\u9fff")

def is_ascii_letter(ch: str) -> bool:
    return ("A" <= ch <= "Z") or ("a" <= ch <= "z")

def segment_text(s: str) -> list[Segment]:
    segs: list[Segment] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if "\u4e00" <= ch <= "\u9fff":
            j = i + 1
            while j < len(s) and ("\u4e00" <= s[j] <= "\u9fff"):
                j += 1
            segs.append(Segment("han", s[i:j]))
            i = j
        elif ch.isdigit():
            j = i + 1
            while j < len(s) and s[j].isdigit():
                j += 1
            segs.append(Segment("num", s[i:j]))
            i = j
        elif is_ascii_letter(ch):
            j = i + 1
            while j < len(s) and is_ascii_letter(s[j]):
                j += 1
            segs.append(Segment("eng", s[i:j]))  # 连续英文作为一个 token
            i = j
        else:
            j = i + 1
            while j < len(s) and (
                not ("\u4e00" <= s[j] <= "\u9fff")
                and not s[j].isdigit()
                and not is_ascii_letter(s[j])
            ):
                j += 1
            segs.append(Segment("other", s[i:j]))
            i = j
    return segs


# ---------- 多音字统计结构 ----------
MULTI_CHAR_ALL_READINGS: dict[str, set[str]] = {}
MULTI_CHAR_READING_COUNTS: dict[str, dict[str, int]] = {}

def han_char_all_readings(ch: str) -> list[str]:
    if ch in CUSTOM_PINYIN:
        return [CUSTOM_PINYIN[ch]]

    pys = pinyin(ch, style=Style.NORMAL, heteronym=True, errors=lambda _: [])
    if not pys or not pys[0]:
        return []
    seen = set()
    out = []
    for x in pys[0]:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def han_char_default_reading(ch: str) -> str | None:
    if ch in CUSTOM_PINYIN:
        return CUSTOM_PINYIN[ch]
    lp = lazy_pinyin(ch, errors=lambda _: [])
    return lp[0] if lp else None

def record_multi_char_usage(ch: str, all_readings: list[str], default_reading: str | None) -> None:
    if ch in CUSTOM_PINYIN:
        return
    if len(all_readings) <= 1:
        return
    MULTI_CHAR_ALL_READINGS.setdefault(ch, set()).update(all_readings)
    if default_reading:
        per = MULTI_CHAR_READING_COUNTS.setdefault(ch, {})
        per[default_reading] = per.get(default_reading, 0) + 1

def han_pinyin_tokens_with_custom(text: str) -> tuple[list[str], bool, bool]:
    tokens: list[str] = []
    has_multi = False
    has_unparsed = False

    for ch in text:
        if not is_han_char(ch):
            continue

        if ch in CUSTOM_PINYIN:
            tokens.append(CUSTOM_PINYIN[ch])
            continue

        all_readings = han_char_all_readings(ch)
        if not all_readings:
            has_unparsed = True
            continue

        default = han_char_default_reading(ch)
        if len(all_readings) > 1:
            has_multi = True
            record_multi_char_usage(ch, all_readings, default)

        if default:
            tokens.append(default)
        else:
            has_unparsed = True

    return tokens, has_multi, has_unparsed


# ---------- 整词自定义拼音 ----------
def tokens_from_custom_word_pinyin(source_text: str) -> list[str] | None:
    if source_text not in CUSTOM_WORD_PINYIN:
        return None
    val = CUSTOM_WORD_PINYIN[source_text].strip()
    if not val:
        return []
    return [x for x in val.split() if x]


# ---------- 生成 tokens（英文统一转大写，但不影响 CUSTOM_WORD_PINYIN） ----------
def pinyin_tokens_for_text(source_text: str) -> tuple[list[str], bool, bool]:
    """
    返回 (tokens, has_multiaccent, has_unparsed_non_english)

    优先级：
    1) CUSTOM_WORD_PINYIN：命中则 tokens 完全原样使用，不做英文大写处理
    2) 正常分段：汉/数/英/其他（英文字段强制转大写）
    """
    custom = tokens_from_custom_word_pinyin(source_text)
    if custom is not None:
        return custom, False, False

    tokens: list[str] = []
    has_multiaccent = False
    has_unparsed_non_english = False

    for seg in segment_text(source_text):
        if seg.kind == "han":
            tks, multi, unparsed = han_pinyin_tokens_with_custom(seg.text)
            tokens.extend(tks)
            if multi:
                has_multiaccent = True
            if unparsed:
                has_unparsed_non_english = True

        elif seg.kind == "num":
            n = int(seg.text)
            if n >= 10000:
                has_unparsed_non_english = True
            else:
                tokens.extend(num_lt_10000_to_pinyin(n))

        elif seg.kind == "eng":
            tokens.append(seg.text.upper())  # 英文统一大写

        else:
            has_unparsed_non_english = True

    return tokens, has_multiaccent, has_unparsed_non_english


# ---------- 人名中间点展开 ----------
def expand_name_entries(word: str) -> list[tuple[str, str]]:
    w = word.strip()
    if not w:
        return []
    if NAME_SEPARATOR not in w:
        return [(w, w)]

    parts = [p.strip() for p in w.split(NAME_SEPARATOR)]
    first = parts[0] if parts else ""

    out: list[tuple[str, str]] = []
    if first:
        out.append((first, first))

    if len(parts) == 2:
        last = parts[1]
        if last:
            out.append((last, last))
        if first:
            out.append((w, first))
    else:
        if first:
            out.append((w, first))
    return out


# ---------- 输出格式 ----------
def format_rime_line(text: str, code: str, weight: int) -> str:
    if weight >= 0:
        return f"{text}{COL_SEP}{code}{COL_SEP}{weight}"
    return f"{text}{COL_SEP}{code}"

def dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def accent_lines_sorted() -> list[str]:
    lines: list[str] = []
    for ch in sorted(MULTI_CHAR_ALL_READINGS.keys()):
        if ch in CUSTOM_PINYIN:
            continue
        all_readings = MULTI_CHAR_ALL_READINGS.get(ch, set())
        counts = MULTI_CHAR_READING_COUNTS.get(ch, {})

        def key_fn(r: str):
            return (-counts.get(r, 0), r)

        readings_sorted = sorted(all_readings, key=key_fn)
        lines.append(ch + " " + " ".join(readings_sorted))
    return lines


def main() -> int:
    in_path = Path(INPUT_CSV)
    if not in_path.exists():
        print(f"找不到输入文件：{in_path.resolve()}", file=sys.stderr)
        return 1

    with in_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        print("CSV 为空。", file=sys.stderr)
        return 1

    data_rows = rows[1:]  # 跳过标题
    max_cols = max((len(r) for r in data_rows), default=0)

    # 按列收集并列内去重
    cols: list[list[str]] = []
    for c in range(max_cols):
        col_items: list[str] = []
        for r in data_rows:
            if c < len(r):
                v = r[c].strip()
                if v:
                    col_items.append(v)
        cols.append(dedupe_keep_order(col_items))

    full_lines: list[str] = []
    simp_lines: list[str] = []
    multi_lines: list[str] = []

    nodup_words: list[str] = []
    nodup_seen: set[str] = set()

    seen_full: set[tuple[str, str]] = set()
    seen_simp: set[tuple[str, str]] = set()
    seen_multi: set[tuple[str, str]] = set()

    def emit_full(text: str, code_full: str, weight: int):
        k = (text, code_full)
        if k not in seen_full:
            seen_full.add(k)
            full_lines.append(format_rime_line(text, code_full, weight))

    def emit_simp(text: str, code_simp: str, weight: int):
        k = (text, code_simp)
        if k not in seen_simp:
            seen_simp.add(k)
            simp_lines.append(format_rime_line(text, code_simp, weight))

    def emit_multi(text: str, code_full: str | None):
        k = (text, code_full or "")
        if k in seen_multi:
            return
        seen_multi.add(k)
        if code_full:
            multi_lines.append(format_rime_line(text, code_full, WEIGHT))
        else:
            multi_lines.append(f"{text}{COL_SEP}<<<UNPARSED>>>")

    for col in cols:
        for raw_word in col:
            entries = expand_name_entries(raw_word)

            # output_nodup：只输出 display_text（去重保序）
            for display_text, _ in entries:
                if display_text not in nodup_seen:
                    nodup_seen.add(display_text)
                    nodup_words.append(display_text)

            for display_text, source_text in entries:
                tokens, has_multi, has_unparsed = pinyin_tokens_for_text(source_text)
                code_full = " ".join(tokens).strip()
                code_simp = "".join(t[0] for t in tokens if t).strip()

                if code_full:
                    emit_full(display_text, code_full, WEIGHT)
                if code_simp and len(code_simp) >= MIN_LEN:
                    emit_simp(display_text, code_simp, WEIGHT)

                if has_multi or has_unparsed:
                    emit_multi(display_text, code_full if code_full else None)

    # 写 output_full/simp/all
    Path(OUT_FULL).write_text("\n".join(full_lines) + ("\n" if full_lines else ""), encoding="utf-8")
    Path(OUT_SIMP).write_text("\n".join(simp_lines) + ("\n" if simp_lines else ""), encoding="utf-8")

    all_lines = full_lines + simp_lines
    Path(OUT_ALL).write_text("\n".join(all_lines) + ("\n" if all_lines else ""), encoding="utf-8")

    # output_ms：与 output_all 一致，但权重全部为 1
    ms_lines = []
    for line in all_lines:
        parts = line.split(COL_SEP)
        if len(parts) >= 3:
            parts[-1] = "1"
            ms_lines.append(COL_SEP.join(parts))
        elif len(parts) == 2:
            ms_lines.append(line + COL_SEP + "1")
        else:
            ms_lines.append(line)
    Path(OUT_MS).write_text("\n".join(ms_lines) + ("\n" if ms_lines else ""), encoding="utf-8")

    Path(OUT_MULTI).write_text("\n".join(multi_lines) + ("\n" if multi_lines else ""), encoding="utf-8")
    Path(OUT_NODUP).write_text("\n".join(nodup_words) + ("\n" if nodup_words else ""), encoding="utf-8")

    acc_lines = accent_lines_sorted()
    Path(OUT_ACCENT).write_text("\n".join(acc_lines) + ("\n" if acc_lines else ""), encoding="utf-8")

    print(
        "完成输出：\n"
        f"- {OUT_FULL}: {len(full_lines)} 行\n"
        f"- {OUT_SIMP}: {len(simp_lines)} 行 (MIN_LEN={MIN_LEN})\n"
        f"- {OUT_ALL}: {len(all_lines)} 行\n"
        f"- {OUT_MS}: {len(ms_lines)} 行（权重全部为 1）\n"
        f"- {OUT_MULTI}: {len(multi_lines)} 行\n"
        f"- {OUT_NODUP}: {len(nodup_words)} 行\n"
        f"- {OUT_ACCENT}: {len(acc_lines)} 行（多音字单字；读音按出现次数排序）\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
