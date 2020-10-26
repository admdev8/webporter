# coding: utf8
from pathlib import Path

import argparse
import asyncio
import functools
import logging
import os
import requests
import sys
import urllib
from bs4 import BeautifulSoup
import urllib3
import time
import random
from urllib.parse import urlparse

header = {
    "User-Agent": r'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  r'Chrome/86.0.4240.111 Safari/537.36', }

Welcome = """
WebPorter now!
"""

class Log(object):

    def __init__(self, level=logging.NOTSET):
        self.level = logging.NOTSET
        if self.level >= logging.ERROR:
            self.level = logging.ERROR
        elif level >= logging.DEBUG:
            self.level = logging.DEBUG
        else:
            self.level = logging.NOTSET

    def __call__(self, *args, **kwargs):
        if self.level == logging.ERROR:
            logging.error(*args)
        elif self.level == logging.DEBUG:
            logging.debug(*args)
        else:
            pass


log = Log()
loge = Log(logging.ERROR)
processed_pages = {}

urllib3.disable_warnings()


def get_page_modified(url):
    if not url.lower().strip().startswith("http"):
        url = "http://" + url
    parse_url = urlparse(url)
    if True if [parse_url.netloc, parse_url.scheme, parse_url.path] else False:
        head_res = requests.head(url, headers=header, timeout=10, allow_redirects=True, verify=False)
        page_update = head_res.headers.get("Last-Modified") if head_res.headers.get(
            "Last-Modified") else head_res.headers.get("Date")
        log("%s last modified %s" % (url, page_update))
        return time.mktime(time.strptime(page_update, "%a, %d %b %Y %H:%M:%S %Z"))
    else:
        log("%s get non modified time" % url)
        return time.time()


def parse_args():
    parser = argparse.ArgumentParser(epilog='\tExample: \r\npython ' + sys.argv[0] + " -u http://www.techyself.com")
    parser.add_argument("-c", "--cookie", help="cookie from the website")
    parser.add_argument("-u", "--url", help="The address where you want to get the source code")
    parser.add_argument("-s", "--urls", help="Download multiple urls from file")
    parser.add_argument("-d", "--depth", help="Number of loops to get links")
    parser.add_argument("-t", "--threads", help="Number of threads for task execution")
    parser.add_argument("-e", "--entire", help="Download entire website", action="store_true")
    parser.add_argument("--log_path", help="Log path")
    parser.add_argument("-l", "--log_level", help="Log level")
    return parser.parse_args()


def init_log(log_path, log_level=logging.DEBUG):
    logger = logging.getLogger()
    if not isinstance(log_level, int):
        log_level = logging.DEBUG
    logger.setLevel(log_level)
    fh = logging.FileHandler(log_path, mode='a', encoding="utf8")
    fh.setLevel(log_level)

    ch = logging.StreamHandler()
    ch.setLevel(log_level)

    formatter = logging.Formatter("%(asctime)s   %(levelname)s: %(message)s")
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return Log(log_level)


# Get the page source
def ExtractContent(url):
    sleep_time = 1 + 2 * random.random()
    time.sleep(sleep_time)
    log("requests for %s" % url)
    try:
        raw = requests.get(url, headers=header, timeout=10, allow_redirects=True, verify=False)
        raw = raw.content
        if raw != "":
            return raw
    except Exception as e:
        loge("requests get %s error %s" % (url, str(e)))
        return None


def Md5Encrypt(text):
    import hashlib
    hl = hashlib.md5()
    hl.update(text.encode(encoding='utf-8'))
    return hl.hexdigest()


def GetUrlPart(url, part=""):
    from urllib.parse import urlparse
    # http://www.example.com/a/b/index.php?id=1#h1
    # domain : www.example.com
    # scheme : http
    # path   : /a/b/index.php
    # id   : id=1
    # fragment : h1
    # completepath : /a/b/
    # completedomain : http://www.example.com
    # filename : index.php
    # filesuffix : php

    if not url.startswith("http"):
        if part == "path":
            return url[:url.rfind("/") + 1]
        if part == "filename":
            temp = url[url.rfind("/") + 1:]
            if temp.find("?") != -1:
                temp = temp[:temp.find("?")]
            if temp.find("#") != -1:
                temp = temp[:temp.find("#")]
            return temp

    parsed = urlparse(url)
    if part == "domain":
        return parsed.netloc
    elif part == "scheme":
        return parsed.scheme
    elif part == "path":
        return parsed.path
    elif part == "query":
        return parsed.query
    elif part == "fragment":
        return parsed.fragment
    elif part == "completepath":
        return parsed.path[:parsed.path.rfind("/") + 1]
    elif part == "completedomain":
        return parsed.scheme + "://" + parsed.netloc
    elif part == "filename":
        return parsed.path[parsed.path.rfind("/") + 1:]
    elif part == "filesuffix":
        temp = parsed.path[parsed.path.rfind("/") + 1:]
        if temp.find(".") == -1:
            return ""
        return temp[temp.find("."):]
    else:
        return parsed


def ProcessResourcePath(pages_url, source_url):
    """
    Handle the relationship between relative paths and absolute paths,
    and give replacement results and save paths
    """

    source_download_url = ""
    processed_source_url = ""
    source_save_path = ""
    source_url_kind = 0

    relative_path = ""
    url_path = GetUrlPart(pages_url, "completepath")
    for i in range(url_path.count("/") - 1):
        relative_path += "../"
    # process others
    if_others = False
    if not source_url.startswith("data:image"):
        # process absolute and special path
        if_abslote_url = False
        if source_url.startswith("http"):
            source_url_kind = 1
            source_download_url = source_url
            if_abslote_url = True
        elif source_url.startswith("//"):
            log("handle source 2 url %s" % source_url)
            source_url_kind = 2
            _scheme = GetUrlPart(pages_url, "scheme")
            source_download_url = (_scheme if _scheme else "http") + ":" + source_url
            if_abslote_url = True

        if_special_url = False
        if source_url.startswith("../"):
            log("handle source 3 url %s" % source_url)
            source_url_kind = 3
            cleared_source_url = GetUrlPart(source_url, "filename")
            cleared_source_path = GetUrlPart(source_url, "path").replace("../", "")
            temp = url_path
            for i in range(source_url.count("../") + 1):
                temp = temp[:temp.rfind("/")]
            absolute_url_path = temp + "/"
            source_download_url = GetUrlPart(pages_url,
                                             "completedomain") + absolute_url_path + cleared_source_path + cleared_source_url
            temp = relative_path
            for i in range(source_url.count("../") + 1):
                temp = temp[:temp.rfind("/") + 1]
            processed_source_url = source_url
            if absolute_url_path.startswith("/"):
                absolute_url_path = absolute_url_path[1:]
            source_save_path = absolute_url_path + cleared_source_path + cleared_source_url
            if_special_url = True
        elif not source_url.startswith("/") and source_url.startswith("//") and not source_url.startswith(
                "/./"):
            log("handle source 4 url %s" % source_url)
            source_url_kind = 4
            source_download_url = GetUrlPart(pages_url, "completedomain") + source_url
            if relative_path == "":
                processed_source_url = GetUrlPart(source_url, "path")[1:] + GetUrlPart(source_url, "filename")
            else:
                processed_source_url = relative_path[:-1] + GetUrlPart(source_url, "path") + GetUrlPart(source_url,
                                                                                                        "filename")
            source_save_path = GetUrlPart(source_url, "path")[1:] + GetUrlPart(source_url, "filename")
            if_special_url = True
        elif source_url.startswith("/./"):
            log("handle source 5 url %s" % source_url)
            source_url_kind = 5
            source_download_url = GetUrlPart(pages_url, "completedomain") + "/" + source_url[3:]
            processed_source_url = relative_path + GetUrlPart(source_url, "path")[3:] + GetUrlPart(source_url,
                                                                                                   "filename")
            source_save_path = GetUrlPart(source_url, "path")[3:] + GetUrlPart(source_url, "filename")
            if_special_url = True

        # process relative path
        if if_abslote_url:
            tmp_fsubffix=GetUrlPart(source_download_url, "filesuffix")
            temp_source_name = Md5Encrypt(source_url) + tmp_fsubffix
            processed_source_url = relative_path + "site_resource/" + temp_source_name
            source_save_path = "site_resource/" + temp_source_name
        elif if_special_url:
            loge("ignore special url %s, %s" %(source_url, source_download_url))
            pass
        elif source_url.startswith("./"):
            log("handle source 6 url %s" % source_url)
            source_url_kind = 6
            cleared_source_url = GetUrlPart(source_url[2:], "path") + GetUrlPart(source_url, "filename")
        else:
            log("handle source 7 url %s" % source_url)
            source_url_kind = 7
            cleared_source_url = GetUrlPart(source_url, "path") + GetUrlPart(source_url, "filename")

        if if_abslote_url == False and if_special_url == False:
            log("handle source NN url %s" % source_url)
            source_download_url = GetUrlPart(pages_url, "completedomain") + GetUrlPart(pages_url,
                                                                                       "completepath") + cleared_source_url
            processed_source_url = cleared_source_url
            source_save_path = url_path[1:] + cleared_source_url
    else:
        source_url_kind = 0

    result = {
        "pages_url": pages_url,
        "source_url": source_url,
        "source_download_url": source_download_url,
        "processed_source_url": processed_source_url,
        "source_save_path": source_save_path,
        "source_url_kind": source_url_kind
    }
    log("dump page info %s" % result)
    return result


def IfBlackName(black_name_list, text, kind=1):
    # 1: equal
    # 2: exist
    # 3: startswith
    for temp in black_name_list:
        if kind == 1:
            if text == temp:
                return True
        if kind == 2:
            if text.find(temp) != -1:
                return True
        if kind == 3:
            if text.startswith(temp):
                return True
    return False


def ExtractLinks(url, lable_name, attribute_name):
    single_black_names = ["/", "#"]
    starts_black_names = ["#", "javascript:"]
    html_raw = ExtractContent(url)
    if html_raw is None:
        return []
    html = BeautifulSoup(html_raw.decode("utf-8", "ignore"), "html.parser")
    lables = html.findAll({lable_name})
    old_links = []
    for lable in lables:
        lable_attribute = lable.get(attribute_name)
        if lable_attribute is None or lable_attribute.strip() == "":
            continue
        lable_attribute = lable_attribute.strip()
        if IfBlackName(single_black_names, lable_attribute):
            continue
        if IfBlackName(starts_black_names, lable_attribute, 3):
            continue
        if lable_attribute not in old_links:
            old_links.append(lable_attribute)
    return old_links


def SaveFile(file_content, file_path, utf8=True):
    processed_path = urllib.parse.unquote(file_path)
    if not isinstance(file_content, str):
        log("%s not str, bytes instead" % file_path)
        utf8 = None
    try:
        path = Path(GetUrlPart(processed_path, "path"))
        path.mkdir(parents=True, exist_ok=True)
        if not utf8:
            with open(processed_path, "wb") as fobject:
                fobject.write(file_content)
        else:
            with open(processed_path, "w", encoding="utf8") as fobject:
                fobject.write(file_content)
    except Exception as e:
        loge("save %s failed %s" % (file_path, str(e)))


def ProcessLink(page_url, link, if_page_url=False):
    temp = ProcessResourcePath(page_url, link)
    processed_link = temp["source_download_url"]
    if GetUrlPart(page_url, "domain") != GetUrlPart(processed_link, "domain"):
        log("%s has been processed" % GetUrlPart(page_url, "domain"))
        return None
    if if_page_url:
        processed_link = GetUrlPart(processed_link, "completedomain") + GetUrlPart(processed_link, "path")
    else:
        temp = ProcessResourcePath(page_url, link)
        processed_link = temp["processed_source_url"]
    url_filename = GetUrlPart(processed_link, "filename")
    url_suffix = GetUrlPart(processed_link, "filesuffix")
    if url_suffix == ".html":
        pass
    elif url_filename == "":
        processed_link += "index.html"
    else:
        processed_link += ".html"
    if not if_page_url:
        if processed_link.startswith("/"):
            processed_link = processed_link[1:]
    return processed_link


def CrawlSinglePage(page_url):
    sleep_time = 2 + 2 * random.random()
    time.sleep(sleep_time)
    log("save single page %s in %fss" % (page_url, sleep_time))
    domain = GetUrlPart(page_url, "domain")
    domain_path = domain.replace(".", "_")
    processed_page_url = ProcessLink("http://" + domain, page_url, True)
    if processed_page_url is None:
        raise ValueError("invalid url %s:%s" % (domain, page_url))
    page_save_path = "website/" + domain_path + "/" + GetUrlPart(processed_page_url, "path")

    if os.path.exists(page_save_path):
        f_mtime = os.path.getmtime(page_save_path)
        page_update = get_page_modified(page_url)
        if f_mtime >= page_update:
            log("page %s updated at %s", page_url, time.asctime(time.localtime(page_update)))
            return None
    log("processing " + page_url)
    links_js = ExtractLinks(page_url, "script", "src")
    links_css = ExtractLinks(page_url, "link", "href")
    links_img = ExtractLinks(page_url, "img", "src")
    links_a = ExtractLinks(page_url, "a", "href")
    links_all = links_js + links_css + links_img
    log("dump all links %s" % str(links_all))
    page_raw = ExtractContent(page_url)
    if page_raw is None:
        return None
    page_raw = page_raw.decode("utf-8", "ignore")
    processed_links = []
    for link in links_all:
        link_info = ProcessResourcePath(page_url, link.strip())
        try:
            page_raw = page_raw.replace(link, link_info["processed_source_url"])
        except Exception as e:
            loge("ProcessResourcePath error %s" % str(e))
            continue
        source_save_path = "website/" + domain_path + "/" + link_info["source_save_path"]
        source_save_path.replace("\\\\", "")
        if os.path.exists(source_save_path):
            #check file size and web page header size
            continue
        source_raw = ExtractContent(link_info["source_download_url"])
        # log(source_save_path)
        if source_raw is None:
            continue
        SaveFile(source_raw, source_save_path, True)
    links = []
    links_copy = []
    for link_a in links_a:
        processed_link = ProcessLink(page_url, link_a)
        if processed_link in links_copy:
            continue
        if processed_link is None:
            continue
        links_copy.append(processed_link)
        link_temp = {
            "link": link_a,
            "processed_link": processed_link
        }
        links.append(link_temp)

    for link in links:
        if link["link"] == '/':
            continue
        page_raw = page_raw.replace(link["link"], link["processed_link"])
    SaveFile(page_raw, page_save_path, True)


def CollectUrls(page_url):
    filename_black_names = [":", "?", "'", '"', "<", ">", "|"]
    #black_suffix_str = ".tgz|.jar|.so|.docx|.py|.js|.css|.jpg|.jpeg|.png|.gif|.bmp|.pic|.tif|.txt|.doc|.hlp|.wps|.rtf|.pdf|.rar|.zip|.gz|.arj|.z|.wav|.aif|.au|.mp3|.ram|.wma|.mmf|.amr|.aac|.flac|.avi|.mpg|.mov|.swf|.int|.sys|.dll|.adt|.exe|.com|.c|.asm|.for|.lib|.lst|.msg|.obj|.pas|.wki|.bas|.map|.bak|.tmp|.dot|.bat|.cmd|.com"
    black_suffix_str = ".so|.js|.css"
    black_suffix = black_suffix_str.split("|")
    links_a = ExtractLinks(page_url, "a", "href")
    result = []
    for link in links_a:
        link_info = ProcessResourcePath(page_url, link)
        processed_link = link_info["source_download_url"]
        if GetUrlPart(processed_link, "domain") != GetUrlPart(page_url, "domain"):
            log("ignore external domain %s %s" % (GetUrlPart(processed_link, "domain"), GetUrlPart(page_url, "domain")))
            continue
        if IfBlackName(filename_black_names, GetUrlPart(processed_link, "path"), 2):
            log("ignore black names %s" % GetUrlPart(processed_link, "path"))
            continue
        if IfBlackName(black_suffix, GetUrlPart(processed_link, "filesuffix")):
            log("ignore black suffix names %s" % GetUrlPart(processed_link, "path"))
            continue
        processed_link = GetUrlPart(processed_link, "completedomain") + GetUrlPart(processed_link, "path")
        if processed_link not in result:
            result.append(processed_link)
    return result


async def coroutine_execution(function, param1):
    """
    use run_in_executor to create thread to run time consuming functions
    ps：functools.partial's args should be consistent with target funcs
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, functools.partial(function, page_url=param1))
    return result


def coroutine_init(function, parameters, threads):
    """
    work threads
    use coroutine_execution to invoke coroutine
    """
    times = int(len(parameters) / threads) + 1
    if len(parameters) == threads or int(len(parameters) % threads) == 0: times -= 1
    result = []
    for num in range(times):
        tasks = []
        Minimum = threads * num
        Maximum = threads * (num + 1)
        if num == times - 1 and len(parameters) % threads != 0:
            Minimum = (times - 1) * threads
            Maximum = len(parameters)
        if len(parameters) <= threads:
            Minimum = 0
            Maximum = len(parameters)
        for i in range(Minimum, Maximum):
            # you can adjust the count from parameters[i], single value at present.
            future = asyncio.ensure_future(coroutine_execution(function, param1=parameters[i]))
            tasks.append(future)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait(tasks))
        for task in tasks:
            result.append(task.result())
        # log("[*] The {}th thread ends".format(str(num + 1)))
    return result


def ExtractUrls(main_url, depth=20, threads=10):
    log("Main url: {url} Depth: {depth} Threads:{threads}".format(url=main_url, depth=depth, threads=threads))
    domain = GetUrlPart(main_url, "domain")
    domain_path = domain.replace(".", "_")
    urls = CollectUrls(main_url)
    if main_url not in urls:
        urls.append(main_url)
    collected_urls = []
    urls_count = 0
    for i in range(0, depth):
        log("start " + str(i + 1) + "th loop traversal in progress")
        copy_urls = urls[:]
        if len(copy_urls) == len(collected_urls):
            break
        not_extracted_urls = []
        for url in copy_urls:
            if url not in collected_urls:
                not_extracted_urls.append(url)
        results = coroutine_init(CollectUrls, parameters=not_extracted_urls, threads=threads)
        collected_urls.extend(not_extracted_urls)
        for result in results:
            for temp_url in result:
                if temp_url not in urls:
                    urls.append(temp_url.strip())
        log("Collected {0} URL links in this cycle".format(len(urls) - urls_count))
        urls_count = len(urls)
    log("Urls collection completed")
    log("Collected a total of {0} URLs".format(str(urls_count)))
    log("Getting source and resources for each page...")
    results = coroutine_init(CrawlSinglePage, parameters=urls, threads=threads)


def main():
    global log
    log(Welcome)
    args = parse_args()
    if args.cookie is not None:
        header["cookie"] = args.cookie

    if args.log_path is not None:
        log = init_log(args.log_path, args.log_level)
        log("save log into %s" % args.log_path)

    urls = []
    if args.urls is not None:
        with open(args.urls, "r", encoding="utf-8") as fobject:
            urls = fobject.read().split("\n")
    elif args.url is not None:
        urls.append(args.url)
    for crawl_url in urls:
        if args.entire:
            depth = 20
            threads = 10
            if args.depth is not None:
                depth = int(args.depth)
            if args.threads is not None:
                threads = int(args.threads)
            log("save the whole index page %s" % crawl_url)
            ExtractUrls(crawl_url, depth, threads)
        elif not args.entire:
            log("save the single page %s" % crawl_url)
            CrawlSinglePage(crawl_url)
    log("All resources have been downloaded")


if __name__ == "__main__":
    main()
