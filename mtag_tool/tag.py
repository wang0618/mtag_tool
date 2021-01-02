from collections import namedtuple

from mutagen.id3 import ID3, APIC, USLT, TIT2, TALB, TPE1, SYLT, ID3NoHeaderError, Encoding, PictureType, WXXX

MusicInfo = namedtuple('MusicInfo', 'title, album, artist, img, unsync_lrc, sync_lrc')


class ID3Tags:
    def __init__(self, mp3path):
        self.file_path = mp3path
        try:
            self.tag = ID3(mp3path)
        except ID3NoHeaderError:
            self.tag = ID3()

    def info(self):
        """获取歌曲的ID3信息"""
        infos = {self.tag[key].FrameID: key for key in self.tag.keys()}
        title = self.tag[infos['TIT2']].text[0] if 'TIT2' in infos else ''
        album = self.tag[infos['TALB']].text[0] if 'TALB' in infos else ''
        artist = self.tag[infos['TPE1']].text[0] if 'TPE1' in infos else ''
        img = self.tag[infos['APIC']].data if 'APIC' in infos else None
        unsync_lrc = self.tag[infos['USLT']].text if 'USLT' in infos else ''
        sync_lrc = self.tag[infos['SYLT']].text if 'SYLT' in infos else []

        return MusicInfo(title, album, artist, img, unsync_lrc, sync_lrc)

    def save(self, *, file_path=None, title=None, album=None, artist=None, sync_lrc=None, unsync_lrc=None,
             img=None, url=None):
        """保存歌曲的ID3信息"""

        if img:
            self.tag.setall('APIC', [APIC(
                encoding=Encoding.LATIN1,  # if other apple music/itunes  can't display img
                mime='image/jpeg',  # image/jpeg or image/png
                type=PictureType.COVER_FRONT,  # 3 is for the cover image
                data=img)])

        if sync_lrc:
            # Sample: format=2, type=1,  text=[("Do you know what's worth fighting for'", 17640), ...])
            # 不知道 format=2, type=1 的含义，这是使用ID3读取现有mp3逆向得到的
            self.tag.setall("SYLT", [SYLT(encoding=Encoding.UTF8, lang='eng', format=2, type=1, text=sync_lrc)])
        if unsync_lrc:
            self.tag.setall("USLT", [USLT(encoding=Encoding.UTF8, lang='eng', text=unsync_lrc)])
        if title:
            self.tag.setall("TIT2", [TIT2(encoding=Encoding.UTF8, text=title)])
        if album:
            self.tag.setall("TALB", [TALB(encoding=Encoding.UTF8, text=album)])
        if artist:
            self.tag.setall("TPE1", [TPE1(encoding=Encoding.UTF8, text=artist)])
        if url:
            self.tag.setall("WXXX", [WXXX(encoding=Encoding.UTF8, url=url)])

        self.tag.save(file_path or self.file_path, v2_version=3)
