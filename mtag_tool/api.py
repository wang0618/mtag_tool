from collections import namedtuple

import re
import requests

Song = namedtuple('Song', 'id name artists album image')

netease_headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",  # noqa
    "Accept-Charset": "UTF-8,*;q=0.5",
    "Accept-Encoding": "gzip,deflate,sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:60.0) Gecko/20100101 Firefox/60.0",  # noqa
    "referer": "https://www.google.com",
}


def search(key):
    """网易云搜索歌曲"""
    data = {
        's': key,
        'offset': 0,
        'limit': 10,
        'type': 1
    }

    r = requests.post('http://music.163.com/api/search/pc', data=data, timeout=10, headers=netease_headers)
    # print(json.dump(r.json(), open('out.json', 'w'), indent=4, ensure_ascii=False))
    res_ = r.json()
    if res_['code'] != 200 or res_['result']['songCount'] == 0:
        return False

    songs = []
    for song in res_['result']['songs']:
        songs.append(Song(
            song['id'],
            song['name'],
            ','.join(i.get('name', '') for i in song['artists']),
            song.get('album', {}).get('name', ''),
            song.get('album', {}).get('picUrl', ''),
        ))

    return songs


def get_lyric(id, include_trans=True):
    """返回带时间轴和纯文本歌词"""
    r = requests.get('http://music.163.com/api/song/lyric?os=pc&id=%s&lv=-1&kv=-1&tv=-1' % id, timeout=10,
                     headers=netease_headers)
    res = r.json()
    if res.get('nolyric'):
        return [], ''

    lrc_text = res['lrc']['lyric'].strip()
    if include_trans:
        lrc_text += '\n' + (res['tlyric'].get('lyric') or '').strip()

    sync_lrc = []
    for line in lrc_text.splitlines():
        match = re.search(r'\[([0-9].*?):([0-9].*?)\.([0-9].*?)\]', line)
        if not match:
            continue

        text = line.split(']', 1)[-1]
        min, sec, mil = match.group(1), match.group(2), match.group(3)
        t = (int(min) * 60 + int(sec)) * 1000 + int(mil) * 10
        sync_lrc.append([text, t])

    sync_lrc.sort(key=lambda i: (i[1], i[0]))
    unsync_lrc = '\n'.join(line[0] for line in sync_lrc)
    return sync_lrc, unsync_lrc


if __name__ == '__main__':
    s = search('王若琳')
    print(s)
    print(get_lyric('1383841268'))
