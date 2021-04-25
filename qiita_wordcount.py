import sys
import re

from janome.tokenizer import Tokenizer
from janome.analyzer import Analyzer
from janome.charfilter import UnicodeNormalizeCharFilter
from janome.tokenfilter import LowerCaseFilter
import collections

import http.client
import json
import requests
from bs4 import BeautifulSoup


# 投稿記事URL取得
def article_urlget(user_name, item_num):

    print("投稿記事URL取得試行中...", end="")

    page = "1"  # ページ番号
    par_page = "100"  # 1ページあたりの最大記事数

    # HTML取得(Qiita APIを叩く)
    conn = http.client.HTTPSConnection("qiita.com", 443)
    conn.request("GET", "/api/v2/users/" + user_name + "/items?page=" + page + "&per_page=" + par_page)
    r = conn.getresponse()

    # HTML取得失敗時->例外
    if r.status != 200:
        print("失敗")
        print("ステータスコード:" + str(r.status))
        sys.exit()

    data = r.read().decode("utf-8")  # UTF-8デコード
    jsonstr = json.loads(data)  # 文字列からJSON形式に変換

    # URLを取得
    url = {}
    for num in range(item_num):
        try:
            title = jsonstr[num]['title']  # 記事タイトル取得

            url[title] = jsonstr[num]['url']
        except IndexError:
            break

    conn.close()
    print("成功")
    print("")

    return url


# 文字列取得
def text_get(soup):

    # 文字列を格納する関数
    def text_store(tags, text_list):
        for i in range(0, len(tags)):
            text_list.append(tags[i].text)
        
        return text_list

    # 各要素取得
    h1tags = soup.find_all('h1')  # h1タグ
    h2tags = soup.find_all('h2')  # h2タグ
    h3tags = soup.find_all('h3')  # h3タグ
    h4tags = soup.find_all('h4')  # h4タグ
    h5tags = soup.find_all('h5')  # h5タグ
    h6tags = soup.find_all('h6')  # h6タグ

    # codeタグを除去
    for p in soup.find_all('code'):
        p.decompose()
    ptags = soup.find_all('p')  # pタグ

    # 文字列を格納
    text_list = []
    text_list = text_store(h1tags, text_list)
    text_list = text_store(h2tags, text_list)
    text_list = text_store(h3tags, text_list)
    text_list = text_store(h4tags, text_list)
    text_list = text_store(h5tags, text_list)
    text_list = text_store(h6tags, text_list)

    # pタグ
    for i in range(0, len(ptags)):
        ptags[i] = ptags[i].text
        # Texの除去
        ptags[i] = re.sub(r'\$\$(.*?)\$\$', '', ptags[i])
        ptags[i] = re.sub(r'\$(.*?)\$', '', ptags[i])
        text_list.append(ptags[i])

    # 空白文字などの除去
    text = "\n".join(text_list)  # リスト->文字列
    table = str.maketrans({
        '\u3000': '',
        ' ': '',
        '\t': '',
    })
    text = text.translate(table)

    return text


# 形態素解析&カウント
def text_analyze8count(text, all_words):

    # Unicode正規化
    char_filters = [UnicodeNormalizeCharFilter()]
    # 小文字表記(英語)
    token_filters = [LowerCaseFilter()]
    # Analyzerセット
    a = Analyzer(char_filters, Tokenizer(), token_filters)

    # 大分類:名詞,小分類:一般の単語を取得
    word = []
    for token in a.analyze(text):
        h = token.part_of_speech
        h = h.split(',')

        if '名詞' in h[0] and ('一般' in h[1] or '固有名詞' in h[1]):
            word.append(token.surface)
            all_words.append(token.surface)

    # 出現回数カウント
    c = collections.Counter(word)

    return c


# 各記事中の単語の出現回数カウント
def article_textcount(url):
    all_words = []

    for key, item in url.items():
        print("記事\"" + key + "\"の内容を取得中...", end='')

        # HTML取得
        r = requests.get(item)

        # HTML取得失敗時->例外
        if r.status_code != 200:
            print("失敗")
            print("ステータスコード:" + str(r.status_code))
            sys.exit()
        else:
            print("成功")
        print("記事\"" + key + "\"中の形態素を解析中...", end='')

        # HTML解析
        html = r.text
        soup = BeautifulSoup(html, 'html.parser')

        # 文字列取得
        text = text_get(soup)

        # 形態素解析&出現回数カウント
        res = text_analyze8count(text, all_words)
        print("成功")

        for i in range(0, 8):
            try:
                m = res.most_common()[i]
                print("単語: {0}\t出現回数: {1}".format(m[0], m[1]))
            except IndexError:
                break
        print("")

    return all_words


# Qiitaユーザー名入力
user_name = ''
while True:
    user_name = input("Qiitaユーザー名を入力: ")
    if user_name != '':
        break

# 投稿記事数入力
while True:
    try:
        item_num = int(input("投稿記事数を入力: "))
    except ValueError:
        continue
    else:
        break
print("")

# 投稿記事のURLを一挙取得
url = article_urlget(user_name, item_num)
# 各記事中の単語の出現回数をカウント
all_words = article_textcount(url)

# 記事全体での単語の出現回数
print("記事全体での出現回数")
c = collections.Counter(all_words)
for i in range(10):
    try:
        m = c.most_common()[i]
        print("単語: {0}\t出現回数: {1}".format(m[0], m[1]))
    except IndexError:
        break
