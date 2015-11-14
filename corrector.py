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
           u'\u30E3': u'\u3083',
           u'\u30E4': u'\u3084',
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

def filter_hira_so(s):
    def fn(chk, lb, la):
        if is_hira(lb) or is_hira(la):
            return u"\u305D" # hiragana so
    return replace_in(fn, s, u"\\", 1, 1)
    

def filter_ij(s):
    return (s
        .replace(u"ij", u"\u3044")
        .replace(u"lj", u"\u3044")
        .replace(u"``", u"\u3044")
        .replace(u'l`', u"\u3044")
        .replace(u"fl", u"\u3066")
        .replace(u"lf", u"\u3052")
    )

def filter_weird_opening_braket(s, op, cl):
    # japanese opening bracket -> hiragana ku
    if not s:
        return s
    toklst = s.split(op)
    result = [toklst[0]]
    toklst = toklst[1:]
    for idx, tok in enumerate(toklst):
        clbrk_pos = tok.find(cl)
        endl_pos = tok.find(u'\n')
        if endl_pos == -1 and idx == (len(toklst) - 1):
            endl_pos = len(tok) - 1

        if clbrk_pos == -1 or clbrk_pos > endl_pos:
            result.append(u"\u304f")
        else:
            result.append(op)
        result.append(tok)
    return u''.join(result)

def filter_person_counting(s):
    return (s
        .replace(u'\u30fc\u4eba', u'\u4e00\u4eba')
        .replace(u'\u30cb\u4eba', u'\u4e8c\u4eba')
    )

# xfilter: when false positive is possible
def xfilter_kata_idiom(s):
    return (s
        .replace(u'\u30cb\u30d2', u'\u3053\u3068')
    )
            
def filter_chock(s):
    # TODO
    return s

def correct(s):
    s = filter_space(s)
    s = filter_noise_lines(s)
    s = filter_wrong_ku(s)
    s = filter_wrong_kata(s)
    s = filter_kata_no(s)
    s = filter_hira_so(s)
    s = filter_ij(s)
    s = filter_weird_opening_braket(s, u'\u3008', u'\u3009')
    s = filter_person_counting(s)
    s = filter_chock(s)
    s = xfilter_kata_idiom(s)
    return s
