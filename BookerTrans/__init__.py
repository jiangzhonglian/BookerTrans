# coding: utf-8

import re
import time
from os import path
from bs4 import BeautifulSoup as bs
from .api import GoTransApi
from . import config

__author__ = "ApacheCN"
__email__ = "apachecn@163.com"
__license__ = "SATA"
__version__ = "2020.04.29"

RE_CODE = r'<(pre|code)[^>]*?>[\s\S]*?</\1>'
RE_TAG = r'<[^>]*?>'
RE_ENTITY = r'&(\w+|#x?\d+);'

api = GoTransApi()

def set_inner_html(elem, html):
    body = bs('<body>' + html + '</body>', 'lxml').body
    elem.clear()
    for ch in list(body.children):
        elem.append(ch)

def tags_preprocess(html):

    '''
    # 去头去尾
    html = html.replace("<?xml version='1.0' encoding='utf-8'?>", '')
    html = re.sub(r'<html[^>]*?>.*?<body[^>]*?>', '', html, flags=re.RegexFlag.DOTALL)
    html = re.sub(r'</body>.*?</html>', '', html, flags=re.RegexFlag.DOTALL)
    '''
    
    tags = []
    
    def replace_func(m):
        s = m.group()
        tags.append(s)
        idx = len(tags) - 1
        tk = f' [HTG{idx}] '
        return tk
        
    # 移除 <pre|code>
    html = re.sub(RE_CODE, replace_func, html)
    # 移除其它标签
    html = re.sub(RE_TAG, replace_func, html)
    # 移除实体
    html = re.sub(RE_ENTITY, replace_func, html)
    
    # 去掉 Unix 和 Windows 换行
    html = html.replace('\n', ' ')
    html = html.replace('\r', '')
    return html, tags

def tags_recover(html, tags):

    # 还原标签
    for i, t in enumerate(tags):
        html = html.replace(f'[HTG{i}]', t)
        
    return html

def trans_real(src):

    dst = None
    for i in range(config.retry):
        try:
            print(src)
            dst = api.translate(
                src, 
                src=config.src, 
                dst=config.dst
            )
            print(dst)
            if dst: break
            time.sleep(config.wait_sec)
        except Exception as ex:
            print(ex)
            time.sleep(config.wait_sec)
    
    if not dst: return None
    
    # 修复占位符
    dst = re.sub(r'\[\s*(?:htg|HTG)\s*(\d+)\s*\]', r'[HTG\1]', dst)
    return dst

def trans_one(html):
    if html.strip() == '':
        return ''
    
    # 标签预处理
    html, tokens = tags_preprocess(html)
    
    # 按句子翻译
    html = trans_real(html)
    if not html: return None
    
    # 标签还原
    html = tags_recover(html, tokens)
    return html

def trans_html(html):
    html = process_code(html)
    root = bs(html, 'lxml')
    
    # 处理 <p> <h?>
    elems = root.select('p, h1, h2, h3, h4, h5, h6')
    for elem in elems:
        to_trans = elem.decode_contents()
        trans = trans_one(to_trans)
        if not trans: continue
        set_inner_html(elem, trans)
        
    # 处理 <blockquote> <td> <th>
    elems = root.select('blockquote, td, th')
    for elem in elems:
        if elem.p: continue
        to_trans = elem.decode_contents()
        trans = trans_one(to_trans)
        if not trans: continue
        set_inner_html(elem, trans)
    
    # 处理 <li>
    elems = root.select('li')
    for elem in elems:
        if elem.p: continue
        
        # 如果有子列表，就取下来
        sub_list = None
        if elem.ul: sub_list = elem.ul
        if elem.ol: sub_list = elem.ol
        if sub_list: sub_list.extract()
        
        to_trans = elem.decode_contents()
        trans = trans_one(to_trans)
        if not trans: continue
        set_inner_html(elem, trans)
        
        # 将子列表还原
        if sub_list: elem.append(sub_list)
    
    return root.decode()

def process_code(html):
    root = bs(html, 'lxml')
    
    pres = root.select('div.code, div.Code')
    for p in pres:
        newp = bs('<pre></pre>', 'lxml').pre
        newp.append(p.text)
        p.replace_with(newp)
        
    codes = root.select('span.inline-code, span.CodeInline')
    for c in codes:
        newc = bs('<code></code>', 'lxml').code
        newc.append(c.text)
        c.replace_with(newc)
        
    return str(root)
