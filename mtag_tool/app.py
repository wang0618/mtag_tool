from functools import partial
from os import path, listdir

import requests
import logging
from mtag_tool.api import search, get_lyric, netease_headers
from mtag_tool.tag import ID3Tags
from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import *

here_dir = path.dirname(path.abspath(__file__))

# 全局状态 ###########
files_tag = []
current_idx = 0  # 当前正在处理的音乐文件在files_tag中的索引
current_tag = None  # 当前正在处理的音乐文件的ID3Tags对象
edited_info = {  # 对当前文件的tag信息的改动
    'title': None, 'album': None, 'artist': None, 'sync_lrc': None,
    'unsync_lrc': None, 'img': None, 'url': None
}


####################


def split_filename(name):
    """从文件名中解析歌曲名和演唱者"""
    try:
        artist, title = path.basename(name).split(' - ', 1)
    except Exception:
        return False

    title = title[:-len('.mp3')]
    return artist, title


def edit():
    info = input_group('编辑音乐标签', [
        input('标题', name='title', value=edited_info['title']),
        input('专辑', name='album', value=edited_info['album']),
        input('艺术家', name='artist', value=edited_info['artist']),
        file_upload('封面图像', accept='image/*', name='img'),
    ], cancelable=True)
    if info is None:
        return
    if info.get('img'):
        info['img'] = info['img']['content']
    for k, v in info.items():
        if v:
            edited_info[k] = v

    show_music_info(current_tag)


def save_and_next():
    current_tag.save(**edited_info)
    for k in edited_info:
        edited_info[k] = None
    toast('保存成功')
    process_music(current_idx + 1)


@use_scope('music_tag_info', clear=True)
def show_music_info(tag):
    put_markdown('### 音乐文件Tag信息')
    put_markdown('`%s`' % tag.file_path)

    put_row([
        put_markdown("""
        - Title: %s
        - Artist: %s
        - Album: %s
        """ % (edited_info['title'], edited_info['artist'], edited_info['album']), lstrip=True),
        put_image(edited_info['img'], width='100px') if edited_info['img'] else put_code('无封面图片')
    ], size='1fr 100px')

    if not edited_info['sync_lrc'] and not edited_info['unsync_lrc']:
        put_markdown('**歌词**\n> 无内嵌歌词')
    elif edited_info['sync_lrc'] and edited_info['unsync_lrc']:
        put_markdown('**歌词**')
        lrc = '\n'.join('[%s]%s' % (b, a) for a, b in edited_info['sync_lrc'])
        put_scrollable(lrc, max_height=200)
    elif edited_info['sync_lrc']:
        put_markdown('**歌词(仅有同步歌词)**')
        lrc = '\n'.join('[%s]%s' % (b, a) for a, b in edited_info['sync_lrc'])
        put_scrollable(lrc, max_height=200)
    elif edited_info['unsync_lrc']:
        put_markdown('**歌词(仅有非同步歌词)**')
        put_scrollable(edited_info['unsync_lrc'], max_height=200)

    if any(edited_info[k] != v for k, v in current_tag.info()._asdict().items()):
        style(put_markdown('> ⚠️当前修改未保存'), 'color:red')

    put_buttons(['编辑基本信息', '保存并编辑下一个'], [edit, save_and_next])


def show_netease_info(tag):
    put_markdown('### 网易云歌曲搜索结果')

    artist, title = split_filename(tag.file_path)
    title = title.split('(', 1)[0]
    # key = '%s %s' % (title or info.title, artist or info.artist)
    with use_scope('loading'):
        put_text('加载中')
        put_loading()
        try:
            songs = search(title)
        except Exception:
            toast('网络请求错误', color='error')
            songs = []
        clear()

    res = []
    for song in songs:
        song_action = partial(netease_song_action, song=song)
        res.append([
            put_image(song.image, width='80px'),
            put_link(song.name, "https://music.163.com/#/song?id=%s" % song.id),
            song.artists,
            song.album,
            put_buttons(['查看歌词', '选定'], song_action, small=True)
        ])

    if res:
        put_markdown('> 若要使用以下某个歌曲的信息覆盖当前音乐文件，请点击歌曲右侧的`选定`按钮')
        put_table(res,
                  header=[style(put_text('封面'), 'width:80px'), '标题', '演唱者', '专辑', style(put_text('操作'), 'width:130px')])
    else:
        put_markdown('> 无数据')


def netease_song_action(action, song):
    try:
        sync_lrc, unsync_lrc = get_lyric(song.id)
    except Exception as e:
        logging.exception('exception while getting lyric')
        sync_lrc, unsync_lrc = None, None
        toast('歌词获取失败，可能音乐不含歌词', color='error')

    if action == '查看歌词':
        if unsync_lrc is None:
            return
        with popup('%s - %s 歌词' % (song.artists, song.name)):
            put_code(unsync_lrc)
    elif action == '选定':
        edited_info['img_content'] = requests.get(song.image, timeout=10, headers=netease_headers).content
        edited_info.update(
            img=requests.get(song.image, timeout=10, headers=netease_headers).content,
            title=song.name,
            album=song.album,
            artist=song.artists,
            sync_lrc=sync_lrc,
            unsync_lrc=unsync_lrc,
            url="https://music.163.com/#/song?id=%s" % song.id,
        )
        show_music_info(current_tag)
        scroll_to(scope='music_info', position='top')


@use_scope('music_info', clear=True)
def process_music(idx):
    global current_tag, edited_info, files_tag, current_idx
    current_idx = idx
    put_buttons(buttons=[('转到前一个文件', -1), ('转到下一个文件', 1)],
                onclick=lambda i: process_music(idx + int(i)))

    if idx < 0 or idx >= len(files_tag):
        put_text("已经到头了")
        current_tag = None
        return

    current_tag = files_tag[idx]
    edited_info.update(current_tag.info()._asdict())
    show_music_info(current_tag)

    scroll_to(position='top')

    show_netease_info(current_tag)


def select_music_dir():
    clear('ROOT')
    music_path = input('请输入音乐文件目录')
    open(path.join(here_dir, 'last_path'), 'w').write(music_path)

    main()


def list_music_dir_file(music_path):
    global files_tag
    try:
        files = [path.join(music_path, f) for f in listdir(music_path) if f.lower().endswith('.mp3')]
    except FileNotFoundError:
        return toast('路径不存在', color='error')
    if not files:
        return toast('路径下不存在mp3文件', color='error')

    put_markdown("## 文件列表")

    infos = []
    for file in files:
        tag = ID3Tags(file)
        info = tag.info()
        infos.append({
            "tag": tag,
            "info": info,
            "has_img": info.img is not None,
            "has_lrc": bool(info.sync_lrc),
            "name_valid": split_filename(file) == (info.artist, info.title),
        })

    infos.sort(key=lambda i: (i['has_img'], i['name_valid'], i['has_lrc']))
    files_tag = [i['tag'] for i in infos]

    table = [
        [
            path.basename(i['tag'].file_path),
            i['info'].title,
            i['info'].artist,
            i['info'].album,
            '有' if i['info'].img else '',
            '❌' if split_filename(i['tag'].file_path) != (i['info'].artist, i['info'].title) else '',
            put_buttons(['编辑'], onclick=lambda _, idx=idx: process_music(idx), small=True)
        ]
        for idx, i in enumerate(infos)
    ]

    put_table(table, header=['文件', '歌曲名', '演唱者', '专辑', '封面', '文件名规范', style(put_text('操作'), 'width:50px')])

    put_markdown('---')


def main():
    if not path.exists(path.join(here_dir, 'last_path')):
        return select_music_dir()
    music_path = open(path.join(here_dir, 'last_path')).read()

    put_markdown("# 音乐标签补全")

    put_row([
        put_markdown('扫描目录: `%s`' % music_path),
        put_buttons(['更改目录'], [select_music_dir], small=True)
    ], size='1fr auto')

    list_music_dir_file(music_path)

    hold()


if __name__ == '__main__':
    start_server(main, port=8080, debug=True)
