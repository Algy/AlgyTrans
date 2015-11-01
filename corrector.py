# coding: utf-8
from functools import partial

def is_hira(c):
    return u"\u3040" <= c <= u"\u309F"

def is_kata(c):
    return u"\u30A0" <= c <= u"\u30FF"

def is_jpn_punc(c):
    return u"\u3000" <= c <= u"\u303F"

def is_kanji(c):
    return u"\u4e00" <= c <= u"\u9FAF"

def is_jpn_chr(c):
    return is_hira(c) or is_kata(c) or is_jpn_punc(c) or is_kanji(c)


def replace_in(fn, s, pat, lookbehind=0, lookahead=0):
    assert (pat != '')
    length = len(s)
    pat_len = len(pat)
    lastidx = 0
    idx = 0
    result = []
    while idx < length:
        idx = s.find(pat, lastidx)
        if idx == -1:
            idx = length
        result.append(s[lastidx:idx])
        chk = s[idx:idx+pat_len]
        if idx >= length:
            break
        p = fn(chk, s[idx-lookbehind:idx], s[idx+pat_len:idx+pat_len+lookahead])
        if type(p) in (str, unicode):
            result.append(p)
        elif p is None:
            result.append(chk)
        lastidx = idx + pat_len
    return u"".join(result)

def filter_space(s):
    return s.replace(u" ", u"")

def _look_kata(MAP, chk, lb, la):
    if is_kata(lb) or is_kata(la):
        return None
    return MAP[chk]

def filter_wrong_kata(s):
    MAP = {u'\u30cb': u'\u3050',
           u'\u30d2': u'\u3068',
           u'\u30d3': u'\u3069',
           u'\u30ab': u'\u304b',
           u'\u30ac': u'\u304c',
            }
    for kata, hira in MAP.items():
        s = replace_in(partial(_look_kata, MAP), s, kata, 1, 1)
    return s


def filter_wrong_ku(s):
    return s.replace(u'<"', u"\u3050")\
            .replace(u'<', u"\u304f")

def filter_noise_lines(s):
    def normal_chr(c):
        return (u'a' <= c <= u'f' or
                u'A' <= c <= u'F' or
                u'0' <= c <= u'9' or
                is_jpn_chr(c))
    
    return "\n".join(
        filter(lambda line:
                 float(len(filter(normal_chr, line))) / len(line) > 0.7,
               s.splitlines()))

def filter_kata_no(s):
    def fn(chk, lb, la):
        if is_kata(lb) or is_kata(la):
            return u"\u30CE" # katakana NO
    return replace_in(fn, s, u"/", 1, 1)
    

def correct(s):
    s = filter_space(s)
    s = filter_noise_lines(s)
    s = filter_wrong_ku(s)
    s = filter_wrong_kata(s)
    s = filter_kata_no(s)
    return s
