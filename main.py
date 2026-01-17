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

WEIGHT = 3000
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
    "片": "pian",
    "狂": "kuang",
    "狄": "di",
    "狼": "lang",
    "猎": "lie",
    "猫": "mao",
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
    "醒": "xing",
    "野": "ye",
    "钿": "dian",
    "阻": "zu",
    "阿": "a",
    "陆": "lu",
    "限": "xian",
    "陶": "tao",
    "雀": "que",
    "零": "ling",
    "震": "zhen",
    "霍": "huo",
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
    "牢": "lao",
    "包": "bao",
    "半": "ban",
    "堕": "duo",
    "夹": "jia",
    "扭": "niu",
    "抱": "bao",
    "炮": "pao",
    "络": "luo",
    "蚣": "gong",
    "蛤": "ha",
    "蟆": "ma",
    "蹲": "dun",
    "亲": "qin",
    "抗": "kang",
    "豚": "tun",
    "劲": "jin",
    "茧": "jian",
    "乾": "qian",
    "予": "yu",
    "仔": "zai",
    "促": "cu",
    "允": "yun",
    "共": "gong",
    "凿": "zao",
    "列": "lie",
    "剽": "piao",
    "区": "qu",
    "卑": "bei",
    "厕": "ce",
    "厘": "li",
    "召": "zhao",
    "吵": "chao",
    "吾": "wu",
    "呀": "ya",
    "告": "gao",
    "呐": "na",
    "员": "yuan",
    "味": "wei",
    "呼": "hu",
    "咀": "ju",
    "喊": "han",
    "喜": "xi",
    "嚣": "xiao",
    "嚼": "jue",
    "均": "jun",
    "坏": "huai",
    "块": "kuai",
    "垩": "e",
    "埃": "ai",
    "堆": "dui",
    "增": "zeng",
    "契": "qi",
    "宛": "wan",
    "彗": "hui",
    "彭": "peng",
    "忏": "chan",
    "慎": "shen",
    "或": "huo",
    "房": "fang",
    "扎": "zha",
    "扑": "pu",
    "拔": "ba",
    "拘": "ju",
    "招": "zhao",
    "掉": "diao",
    "排": "pai",
    "掘": "jue",
    "接": "jie",
    "敦": "dun",
    "施": "shi",
    "旬": "xun",
    "昆": "kun",
    "暖": "nuan",
    "朦": "meng",
    "杉": "shan",
    "枯": "ku",
    "栗": "li",
    "棱": "leng",
    "汤": "tang",
    "沾": "zhan",
    "泄": "xie",
    "泣": "qi",
    "泥": "ni",
    "洒": "sa",
    "浩": "hao",
    "浸": "jin",
    "涂": "tu",
    "涌": "yong",
    "液": "ye",
    "淡": "dan",
    "湛": "zhan",
    "溃": "kui",
    "溪": "xi",
    "漆": "qi",
    "焦": "jiao",
    "熟": "shu",
    "燥": "zao",
    "牟": "mou",
    "犍": "jian",
    "狡": "jiao",
    "疵": "ci",
    "盖": "gai",
    "盾": "dun",
    "研": "yan",
    "碌": "lu",
    "磷": "lin",
    "禅": "chan",
    "稠": "chou",
    "笏": "hu",
    "筒": "tong",
    "累": "lei",
    "繁": "fan",
    "综": "zong",
    "而": "er",
    "肢": "zhi",
    "肥": "fei",
    "胶": "jiao",
    "脱": "tuo",
    "致": "zhi",
    "芒": "mang",
    "莫": "mo",
    "著": "zhu",
    "薄": "bao",
    "蜷": "quan",
    "衰": "shuai",
    "许": "xu",
    "貉": "he",
    "赶": "gan",
    "踢": "ti",
    "蹴": "cu",
    "辟": "pi",
    "这": "zhe",
    "迫": "po",
    "追": "zhui",
    "透": "tou",
    "陀": "tuo",
    "附": "fu",
    "除": "chu",
    "隔": "ge",
    "隘": "ai",
    "隧": "sui",
    "霸": "ba",
    "颈": "jing",
    "驮": "tuo",
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
    "兔已着陆": "tu yi zhuo lu",
    "湖上倒映着洁净的月光": "hu shang dao ying zhe jie jing de yue guang",
    "宇宙巫女归还": "yu zhou wu nv gui huan",
    "行云流水": "xing yun liu shui",
    "魔法的笠地藏": "mo fa de li di cang",
    "是此世还是彼世": "shi ci shi hai shi bi shi",
    "禁忌之门对侧是此世还是彼世": "jin ji zhi men dui ce shi ci shi hai shi bi shi",
    "背面的暗黑猿乐": "bei mian de an hei yuan yue",
    "只有地藏知晓的哀叹": "zhi you di zang zhi xiao de ai tan",
    "从地下的归还": "cong di xia de gui huan",
    "被水淹没的沉愁地狱": "bei shui yan mo de chen chou di yu",
    "少女秘封俱乐部": "shao nv mi feng ju le bu",
    "广重三十六号": "guang zhong san shi liu hao",
    "广重36号": "guang zhong san shi liu hao",
    "青木原的传说": "qing mu yuan de chuan shuo",
    "欢迎来到月面旅行团": "huan ying lai dao yue mian lv xing tuan",
    "独自一人的常陆行路": "du zi yi ren de chang lu xing lu",
    "四重存在": "si chong cun zai",
    "之后就一个人都没有了吗": "zhi hou jiu yi ge ren dou mei you le ma",
    "二重结界": "er chong jie jie",
    "少女文乐": "shao nv wen yue",
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
    "江西䌷": "jiang xi chou",
    "八重咲杏": "ba chong xiao xing",
    "御剑缝重子": "yu jian feng chong zi",
    "饕喰乐魔喰乐": "tao can le mo can le",
    "藏人未见": "zang ren wei jian",
    "乐冢魇音": "le zhong yan yin",
    "六地藏千鹤": "liu di zang qian he",
    "河童重工": "he tong zhong gong",
    "幺乐团的历史": "yao yue tuan de li shi",
    "禁系统": "jin xi tong",
    "替身地藏": "ti shen di zang",
    "鸟兽伎乐": "niao shou ji yue",
    "置行堀": "zhi xing ku",
    "上海爱丽丝幻乐团": "shang hai ai li si huan yue tuan",
    "露米娅": "lu mi ya",
    "琪露诺": "qi lu nuo",
    "芙兰朵露": "fu lan duo lu",
    "芙兰朵露·斯卡蕾特": "fu lan duo lu",
    "露娜萨": "lu na sa",
    "露娜萨·普莉兹姆利巴": "lu na sa",
    "梅露兰": "mei lu lan",
    "梅露兰·普莉兹姆利巴": "mei lu lan",
    "莉格露": "li ge lu",
    "莉格露·奈特巴格": "li ge lu",
    "水桥帕露西": "shui qiao pa lu xi",
    "物部布都": "wu bu bu du",
    "豫母都日狭美": "yu mu du ri xia mei",
    "露易兹": "lu yi zi",
    "露娜切露德": "lu na qie lu de",
    "玛艾露贝莉": "ma ai lu bei li",
    "玛艾露贝莉·赫恩": "ma ai lu bei li",
    "豫母都": "yu mu du",
    "帕露西": "pa lu xi",
    "布都": "bu du",
    "露娜": "lu na",
    "船长": "chuan zhang",
    "弹幕天邪鬼": "dan mu tian xie gui",
    "弹幕狂们的黑市": "dan mu kuang men de hei shi",
    "东方大炮弹": "dong fang da pao dan",
    "东方弹幕神乐": "dong fang dan mu shen yue",
    "大炮弹": "da pao dan",
    "弹幕神乐": "dan mu shen yue",
    "幻想帝都": "huan xiang di du",
    "天空的花都": "tian kong de hua du",
    "回忆京都": "hui yi jing du",
    "以犯规对不可能的弹幕": "yi fan gui dui bu ke neng de dan mu",
    "拿起弹幕吧弹幕狂们": "na qi dan mu ba dan mu kuang men",
    "魔界地方都市秘境": "mo jie di fang du shi mi jing",
    "冻结的永远之都": "dong jie de yong yuan zhi du",
    "卫星露天咖啡座": "wei xing lu tian ka fei zuo",
    "处理落率": "chu li luo lv",
    "擦弹": "ca dan",
    "通过率": "tong guo lv",
    "点弹": "dian dan",
    "菌弹": "jun dan",
    "粒弹": "li dan",
    "滴弹": "di dan",
    "链弹": "lian dan",
    "苦无弹": "ku wu dan",
    "针弹": "zhen dan",
    "札弹": "zha dan",
    "鳞弹": "lin dan",
    "铳弹": "chong dan",
    "杆菌弹": "gan jun dan",
    "小星弹": "xiao xing dan",
    "大星弹": "da xing dan",
    "星弹": "xing dan",
    "钱弹": "qian dan",
    "椭弹": "tuo dan",
    "剑弹": "jian dan",
    "刀弹": "dao dan",
    "蝶弹": "die dan",
    "炎弹": "yan dan",
    "水光弹": "shui guang dan",
    "音符弹": "yin fu dan",
    "休止符弹": "xiu zhi fu dan",
    "心弹": "xin dan",
    "箭弹": "jian dan",
    "菱弹": "ling dan",
    "消弹": "xiao dan",
    "死尸弹": "si shi dan",
    "随机弹": "sui ji dan",
    "交叉弹": "jiao cha dan",
    "爆菊弹": "bao ju dan",
    "护身弹": "hu shen dan",
    "反击弹": "fan ji dan",
    "奇数弹": "qi shu dan",
    "偶数弹": "ou shu dan",
    "弹幕": "dan mu",
    "弹幕异夜剧": "dan mu yi ye ju",
    "露娜的最终防线": "lu na de zui zhong fang xian",
    "露妮": "lu ni",
    "长光切": "zhang guang qie",
    "梅露": "mei lu",
    "梅露·阿库娅珀莉": "mei lu",
    "奴露": "nu lu",
    "奴露·莉葵忒": "nu lu",
    "勇帕露": "yong pa lu",
    "灵长园": "ling zhang yuan",
    "旧都": "jiu du",
    "月之都": "yue zhi du",
    "蔓越莓陷阱": "man yue mei xian jing",
    "刻着过去的钟表": "ke zhe guo qu de zhong biao",
    "无差别伤害": "wu cha bie shang hai",
    "延长的冬日": "yan chang de dong ri",
    "轮回的西藏人偶": "lun hui de xi zang ren ou",
    "春之京都人偶": "chun zhi jing du ren ou",
    "饭纲权现降临": "fan gang quan xian jiang lin",
    "弹幕结界": "dan mu jie jie",
    "太阳系仪": "tai yang xi yi",
    "二重的苦轮": "er chong de ku lun",
    "西行春风斩": "xi xing chun feng zhan",
    "黄泉平坂行路": "huang quan ping ban xing lu",
    "四重结界": "si chong jie jie",
    "充满魅力的四重结界": "chong man mei li de si chong jie jie",
    "二重大结界": "er chong da jie jie",
    "二重弹幕结界": "er chong dan mu jie jie",
    "博丽弹幕结界": "bo li dan mu jie jie",
    "二重火花": "er chong huo hua",
    "狂视调律": "kuang shi tiao lv",
    "不朽的弹幕": "bu xiu de dan mu",
    "深弹幕结界": "shen dan mu jie jie",
    "月之都市": "yue zhi du shi",
    "快乐的灵魂": "kuai le de ling hun",
    "梅露兰快乐演奏": "mei lu lan kuai le yan zou",
    "露娜萨现场独奏": "lu na sa xian chang du zou",
    "双重人类之笼": "shuang chong ren lei zhi long",
    "仿若涅槃寂静": "fang ruo nie pan ji jing",
    "蕾米莉亚潜行者": "lei mi li ya qian xing zhe",
    "大师的密传": "da shi de mi zhuan",
    "八重雾中渡": "ba chong wu zhong du",
    "手长足长大人": "shou chang zu zhang da ren",
    "闪光跳弹": "shan guang tiao dan",
    "未来文乐": "wei lai wen yue",
    "没有灵魂的民间舞": "mei you ling hun de min jian wu",
    "楼观赋予我能斩断弹幕的心之眼": "lou guan fu yu wo neng zhan duan dan mu de xin zhi yan",
    "狂躁高速飞行体": "kuang zao gao su fei xing ti",
    "地灵活性弹": "di ling huo xing dan",
    "着魔之人": "zhao mo zhi ren",
    "恐吓弹幕": "kong he dan mu",
    "平行相交": "ping xing xiang jiao",
    "天孙降临的道标": "tian sun jiang lin de dao biao",
    "到处都是的浮游灵": "dao chu dou shi de fu you ling",
    "不惜身命，可惜身命": "bu xi shen ming ke xi shen ming",
    "雷鼓弹": "lei gu dan",
    "雷云鱼游泳弹": "lei yun yu you yong dan",
    "龙宫使者的游泳弹": "long gong shi zhe de you yong dan",
    "先忧后乐之剑": "xian you hou le zhi jian",
    "粗暴的地母啊": "cu bao de di mu a",
    "俯瞰世界的遥远的大地啊": "fu kan shi jie de yao yuan de da di a",
    "弹幕偏执症": "dan mu pian zhi zheng",
    "弹幕的墨迹测验": "dan mu de mo ji ce yan",
    "幽灵船永久停泊": "you ling chuan yong jiu ting bo",
    "悄然袭来的长勺": "qiao ran xi lai de chang shao",
    "传说的飞空圆盘": "chuan shuo de fei kong yuan pan",
    "唐伞惊吓闪光": "tang san jing xia shan guang",
    "鵺的蛇行表演": "ye de she xing biao yan",
    "弹幕奇美拉": "dan mu qi mei la",
    "沉没之锚": "chen mo zhi mao",
    "长勺": "chang shao",
    "蛇行表演": "she xing biao yan",
    "星脉弹": "xing mai dan",
    "星脉地转弹": "xing mai di zhuan dan",
    "缓行的太阳": "huan xing de tai yang",
    "热木星降落模型": "re mu xing jiang luo mo xing",
    "最凶恶的吓人巫女玉": "zui xiong e de xia ren wu nv yu",
    "重力一击": "zhong li yi ji",
    "深层生态炸弹": "shen ceng sheng tai zha dan",
    "离心的小行星": "li xin de xiao xing xing",
    "旅鼠的盛装游行": "lv shu de sheng zhuang you xing",
    "祖母绿都市": "zu mu lv du shi",
    "假想时轴": "jia xiang shi zhou",
    "光速跳弹": "guang su tiao dan",
    "这一招出来连尘世都要完结了": "zhe yi zhao chu lai lian chen shi dou yao wan jie le",
    "甜美的番薯房": "tian mei de fan shu fang",
    "幽灵船长期停泊": "you ling chuan chang qi ting bo",
    "深深沉没": "shen shen chen mo",
    "没我之爱": "mei wo zhi ai",
    "游行圣": "you xing sheng",
    "自行星而来的弹幕X": "zi xing xing er lai de dan mu X",
    "报刊推销团降伏": "bao kan tui xiao tuan xiang fu",
    "三重陨石": "san chong yun shi",
    "三重光芒": "san chong guang mang",
    "闪亮之星一般的捉迷藏": "shan liang zhi xing yi ban de zhuo mi cang",
    "剧毒杀害": "ju du sha hai",
    "星辰降落神灵庙": "xing chen jiang luo shen ling miao",
    "灵长类弹幕变化": "ling zhang lei dan mu bian hua",
    "肉食类弹幕变化": "rou shi lei dan mu bian hua",
    "羽鸟类弹幕变化": "yu niao lei dan mu bian hua",
    "两栖类弹幕变化": "liang qi lei dan mu bian hua",
    "狸猫的变身学校": "li mao de bian shen xue xiao",
    "魔奴化巫女的伪降伏": "mo nu hua wu nv de wei xiang fu",
    "猯藏化弹幕十变化": "tuan zang hua dan mu shi bian hua",
    "面灵气大降伏": "mian ling qi da xiang fu",
    "释迦牟尼的五行山": "shi jia mou ni de wu xing shan",
    "先祖大人在看着你": "xian zu da ren zai kan zhe ni",
    "喜怒哀乐附体": "xi nu ai le fu ti",
    "假面丧心舞": "jia mian sang xin wu",
    "暗黑能乐": "an hei neng yue",
    "昂扬的神乐狮子": "ang yang de shen yue shi zi",
    "双重消失": "shuang chong xiao shi",
    "飞行之头": "fei xing zhi tou",
    "双重乐谱": "shuang chong yue pu",
    "你给我变大吧": "ni gei wo bian da ba",
    "极长的脖子": "ji chang de bo zi",
    "乐谱之网": "yue pu zhi wang",
    "星辰降落之歌": "xing chen jiang luo zhi ge",
    "调换魔法": "diao huan mo fa",
    "地狱极乐胡乱斩": "di yu ji le hu luan zhan",
    "人类真好啊": "ren lei zhen hao a",
    "不可能弹幕结界": "bu ke neng dan mu jie jie",
    "十七条宪法炸弹": "shi qi tiao xian fa zha dan",
    "弹幕富翁": "dan mu fu weng",
    "被诅咒的历代校长的肖像": "bei zu zhou de li dai xiao zhang de xiao xiang",
    "夜间学校怪谈云游": "ye jian xue xiao guai tan yun you",
    "假肢变形": "jia zhi bian xing",
    "猿之手啊捏碎敌人": "yuan zhi shou a nie sui di ren",
    "到死都会实现愿望的猴爪": "dao si dou hui shi xian yuan wang de hou zhua",
    "到死还是少一盘": "dao si hai shi shao yi pan",
    "特别让你两边都选": "te bie rang ni liang bian dou xuan",
    "外星机密泄露即刻处置": "wai xing ji mi xie lou ji ke chu zhi",
    "差不多该回家了外星人们啊": "cha bu duo gai hui jia le wai xing ren men a",
    "无差别起火之符": "wu cha bie qi huo zhi fu",
    "传说中的大宴席": "chuan shuo zhong de da yan xi",
    "绿巨人啊变大吧": "lv ju ren a bian da ba",
    "现在就给你打电话别忘了接哦": "xian zai jiu gei ni da dian hua bie wang le jie o",
    "月面跳弹": "yue mian tiao dan",
    "地上跳弹": "di shang tiao dan",
    "凶弹": "xiong dan",
    "乌合的二重咒": "wu he de er chong zhou",
    "众神的光辉弹冠": "zhong shen de guang hui tan guan",
    "擦弹的狱意": "ca dan de yu yi",
    "纯粹的弹幕地狱": "chun cui de dan mu di yu",
    "爬行的子弹": "pa xing de zi dan",
    "用于逼死瓮中鼠的单纯弹幕": "yong yu bi si weng zhong shu de dan chun dan mu",
    "地狱的非理想弹幕": "di yu de fei li xiang dan mu",
    "用于杀人的纯粹弹幕": "yong yu sha ren de chun cui dan mu",
    "最初与最后的无名弹幕": "zui chu yu zui hou de wu ming dan mu",
    "弹冠": "tan guan",
    "擦弹地狱火": "ca dan di yu huo",
    "小行星带噩梦": "xiao xing xing dai e meng",
    "入道丛云水泡弹拳": "ru dao cong yun shui pao dan quan",
    "引导着你的王道的金刚杵射击": "yin dao zhe ni de wang dao de jin gang chu she ji",
    "引导着你的梦王道的威光": "yin dao zhe ni de meng wang dao de wei guang",
    "水泡弹假面舞会": "shui pao dan jia mian wu hui",
    "喜怒哀乐风水术": "xi nu ai le feng shui shu",
    "喜怒哀乐发狂假面舞会": "xi nu ai le fa kuang jia mian wu hui",
    "务光的雷弹梦想封印": "wu guang de lei dan meng xiang feng yin",
    "务光与叶叶的弹幕变化": "wu guang yu ye ye de dan mu bian hua",
    "务光的雷霆闪光梦幻弹": "wu guang de lei ting shan guang meng huan dan",
    "燃烧的秘匿弹幕": "ran shao de mi ni dan mu",
    "大判小判弹幕变化": "da pan xiao pan dan mu bian hua",
    "念力传送": "nian li chuan song",
    "绝体绝命都市人": "jue ti jue ming du shi ren",
    "世纪的二重超人宇佐见堇子": "shi ji de er chong chao ren yu zuo jian jin zi",
    "双重疯狂": "shuang chong feng kuang",
    "大气圈尽在吾之手中": "da qi quan jin zai wu zhi shou zhong",
    "载着我们的梦变大吧": "zai zhe wo men de meng bian da ba",
    "梦坠入大气圈变大吧": "meng zhui ru da qi quan bian da ba",
    "飞向遥远的宇宙吧载着我们的梦想": "fei xiang yao yuan de yu zhou ba zai zhe wo men de meng xiang",
    "落入大气圈梦想倾泻地表": "luo ru da qi quan meng xiang qing xie di biao",
    "把大地重塑成有梦的世界吧": "ba da di chong su cheng you meng de shi jie ba",
    "无人废线车辆炸弹": "wu ren fei xian che liang zha dan",
    "活体巨大弹宠物": "huo ti ju da dan chong wu",
    "狂乱天狗怖吓": "kuang luan tian gou bu he",
    "异常降雪之雪人": "yi chang jiang xue zhi xue ren",
    "弹幕的玉茧": "dan mu de yu jian",
    "安那其弹幕地狱": "an na qi dan mu di yu",
    "巨大弹": "ju da dan",
    "慈爱的地藏": "ci ai de di zang",
    "生机勃勃的弹幕魔像": "sheng ji bo bo de dan mu mo xiang",
    "双重条纹": "shuang chong tiao wen",
    "众神的难摄之弹冠": "zhong shen de nan she zhi tan guan",
    "逢魔之刻 梦": "feng mo zhi ke meng",
    "月亮掉下来啦！": "yue liang diao xia lai la",
    "噩梦中的切实杀人用弹幕": "e meng zhong de qie shi sha ren yong dan mu",
    "摩多罗悦乐": "mo duo luo yue yue",
    "秘神的暗跃弹幕": "mi shen de an yue dan mu",
    "超人浩劫行脚": "chao ren hao jie xing jiao",
    "蓬莱壶中的弹枝": "peng lai hu zhong de dan zhi",
    "要石也给我变大吧": "yao shi ye gei wo bian da ba",
    "蓬莱的巨大弹枝": "peng lai de ju da dan zhi",
    "蓬莱之弹的要石": "peng lai zhi dan de yao shi",
    "纯粹与不纯的弹幕": "chun cui yu bu chun de dan mu",
    "偷拍者降伏极限火花": "tou pai zhe xiang fu ji xian huo hua",
    "来自背后的偷拍者降伏": "lai zi bei hou de tou pai zhe xiang fu",
    "击穿弹幕结界吧！": "ji chuan dan mu jie jie ba",
    "未经许可禁止弹幕摄影": "wei jing xu ke jin zhi dan mu she ying",
    "沉重的石之婴儿": "chen zhong de shi zhi ying er",
    "龙纹弹": "long wen dan",
    "黑色天马流星弹": "hei se tian ma liu xing dan",
    "无理由的无差别降伏": "wu li you de wu cha bie xiang fu",
    "荒诞至极的无差别降伏": "huang dan zhi ji de wu cha bie xiang fu",
    "无差别咒杀降伏": "wu cha bie zhou sha xiang fu",
    "村纱船长的不幸出航": "cun sha chuan zhang de bu xing chu hang",
    "御柱摇曳弹": "yu zhu yao ye dan",
    "御柱掩体炸弹": "yu zhu yan ti zha dan",
    "船上御柱摇曳弹": "chuan shang yu zhu yao ye dan",
    "极乐温泉地狱": "ji le wen quan di yu",
    "地狱火燃烧弹": "di yu huo ran shao dan",
    "幽灵们啊回归自己应属之地": "you ling men a hui gui zi ji ying shu zhi di",
    "鲁莽的子弹": "lu mang de zi dan",
    "秘而不宣的弹幕界之门": "mi er bu xuan de dan mu jie zhi men",
    "弹幕万来": "dan mu wan lai",
    "弹灾招福": "dan zai zhao fu",
    "天马行空乱舞": "tian ma xing kong luan wu",
    "献给无主的供物": "xian gei wu zhu de gong wu",
    "弹幕收集狂的妄执": "dan mu shou ji kuang de wang zhi",
    "弹幕自由市场": "dan mu zi you shi chang",
    "无道的弹幕领土": "wu dao de dan mu ling tu",
    "弹幕的庇护所": "dan mu de bi hu suo",
    "满员御礼弹币红包": "man yuan yu li dan bi hong bao",
    "延迟性管狐弹": "yan chi xing guan hu dan",
    "月狂火炬传递": "yue kuang huo ju chuan di",
    "空前绝后大排长龙的黑市": "kong qian jue hou da pai chang long de hei shi",
    "弹币过剩": "dan bi guo sheng",
    "正规的弹幕市场": "zheng gui de dan mu shi chang",
    "降伏鬼畜生无须慈悲": "xiang fu gui chu sheng wu xu ci bei",
    "多重伏击猎人": "duo chong fu ji lie ren",
    "美丽的地狱弹幕夜行": "mei li de di yu dan mu ye xing",
    "纯灵弹": "chun ling dan",
    "无心纯灵弹": "wu xin chun ling dan",
    "逻辑长城": "luo ji chang cheng",
    "弹幕金字塔": "dan mu jin zi ta",
    "弹幕的化石": "dan mu de hua shi",
    "人工灾害": "ren gong zai hai",
    "幻想一重": "huan xiang yi chong",
    "双壳贝上的幻觉": "shuang ke bei shang de huan jue",
    "五爪龙之珠": "wu zhao long zhi zhu",
    "毒爪": "du zhao",
    "僵尸之爪": "jiang shi zhi zhao",
    "绝望之爪": "jue wang zhi zhao",
    "忘不了那曾依藉的绿意": "wang bu liao na ceng yi ji de lv yi",  # le->liao
}

extra = '''
灵异传\tlyz\t15000
封魔录\tfml\t15000
梦时空\tmsk\t15000
幻想乡\thxx\t15000
怪绮谈\tgqt\t15000
红魔乡\thmx\t15000
妖妖梦\tyym\t15000
萃梦想\tcmx\t15000
永夜抄\tyyc\t15000
花映塚\thyz\t15000
文花帖\twht\t15000
风神录\tfsl\t15000
绯想天\tfxt\t15000
地灵殿\tdld\t15000
星莲船\txlc\t15000
大战争\tdzz\t15000
神灵庙\tslm\t15000
心绮楼\txyl\t15000
辉针城\thzc\t15000
天邪鬼\ttxg\t15000
深秘录\tsml\t15000
绀珠传\tgzz\t15000
凭依华\tpyh\t15000
天空璋\ttkz\t15000
鬼形兽\tgxs\t15000
虹龙洞\thld\t15000
兽王园\tswy\t15000
锦上京\tjsj\t15000
非想天则\tfxtz\t15000
噩梦日记\temrj\t15000
刚欲异闻\tgyyw\t15000

'''
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
    Path(OUT_ALL).write_text("\n".join(all_lines) + ("\n" if all_lines else "") + extra, encoding="utf-8")

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
