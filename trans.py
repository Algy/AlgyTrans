#!/usr/bin/env python
# coding: utf-8
import json
import sys

from urllib2 import urlopen, quote
from corrector import correct


def plus_quote(s):
    idx = 0
    last_idx = 0

    result = []
    while idx < len(s):
        while idx < len(s) and s[idx] != ' ':
            idx += 1
        result.append(quote(s[last_idx:idx]))
        while idx < len(s) and s[idx] == ' ':
            result.append("+")
            idx += 1
        last_idx = idx
    return "".join(result)



def form_encoded(d):
    return "&".join(["%s=%s"%(plus_quote(str(k)), plus_quote(str(v))) for k, v in d.items()])
    

def build_trans(src_lang="ja", target_lang="ko"):
    base_data = {
        "srcLang": src_lang,
        "tarLang": target_lang,
        "highlight": 1,
        "hurigana": 0,
        "noprelog": 1,
        "svcCode": "",
        "cht": 0
    }

    def trans(content):
        if isinstance(content, unicode):
            content = content.encode("UTF-8")
        data = dict(base_data)
        data["query"] = content
        resp = urlopen("http://translate.naver.com/translate.dic", data=form_encoded(data))
        try:
            resp_payload = resp.read()
            return (content, json.loads(resp_payload)["resultData"])
        except (KeyError, ValueError, TypeError):
            return None

    return trans


if __name__ == '__main__':
    trans = build_trans()

    src = sys.stdin.read().decode("utf-8")
    print "[Original]"
    print src.encode("UTF-8")
    src = correct(src)
    orig, result = trans(src)
    if result is None:
        sys.exit(1)
    result = result.encode("utf-8")

    print "[Translated]"
    sys.stdout.write(orig)
    sys.stdout.write("\n")
    sys.stdout.write(result)
