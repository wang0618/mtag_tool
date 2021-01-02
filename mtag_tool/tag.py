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
        infos = {self.tag[key].FrameID: key for key in self.tag.keys()}
        title = self.tag[infos['TIT2']].text[0] if 'TIT2' in infos else ''
        album = self.tag[infos['TALB']].text[0] if 'TALB' in infos else ''
        artist = self.tag[infos['TPE1']].text[0] if 'TPE1' in infos else ''
        img = self.tag[infos['APIC']].data if 'APIC' in infos else None
        unsync_lrc = self.tag[infos['USLT']].text if 'USLT' in infos else ''
        sync_lrc = self.tag[infos['SYLT']].text if 'SYLT' in infos else []

        return MusicInfo(title, album, artist, img, unsync_lrc, sync_lrc)

    def save(self, *, file_path=None, title=None, album=None, artist=None, sync_lrc=None, unsync_lrc=None,
             img_content=None, url=None):

        if img_content:
            self.tag.setall('APIC', [APIC(
                encoding=Encoding.LATIN1,  # if other apple music/itunes  can't display img
                mime='image/jpeg',  # image/jpeg or image/png
                type=PictureType.COVER_FRONT,  # 3 is for the cover image
                data=img_content)])

        # lrc = [("Do you know what's worth fighting for\n", 17640),..]
        # format=2, type=1,  text=[("\nDo you know what's worth fighting for'", 17640), ("\nWhen it's not worth dying for?", 23640), ('\nDoes it take your breath away', 29690), ('\nAnd you feel yourself suffocating?', 34360), ('\nDoes the pain weigh out the pride?', 41950), ('\nAnd you look for a place to hide?', 47990), ('\nDid someone break your heart inside?', 53990), ("\nYo're in ruins", 58640), ("\nOne' 21 guns", 65400), ('\nLay down your arms', 69860), ('\nGive up the fight', 72840), ("\nOne' 21 guns", 77110), ("\nThrow up your arms into the sky'", 81600), ('\nYou and I', 88420), ("\nWhen yo're at the end of the road", 95720), ('\nAnd you lost all sense of control', 101990), ('\nAnd your thoughts have taken their toll', 107950), ('\nWhen your mind breaks the spirit of your soul', 113510), ('\nYour faith walks on broken glass', 119730), ("\nAnd the hangover doesn't pass", 125590), ("\nNothing's ever built to last", 131559), ("\nYo're in ruins", 136119), ("\nOne' 21 guns", 142890), ('\nLay down your arms', 147349), ('\nGive up the fight', 150289), ("\nOne' 21 guns", 154749), ("\nThrow up your arms into the sky'", 159890), ('\nYou and I', 165869), ('\nDid you try to live on your own', 173149), ('\nWhen you burned down the house and home?', 178899), ('\nDid you stand too close to the fire?', 184670), ('\nLike a liar looking for forgiveness from a stone', 189790), ("\nWhen it's time to live and let die", 237309), ("\nAnd you can't get another try", 243359), ('\nSomething inside this heart has died', 249299), ("\nYo're in ruins", 254179), ("\nOne' 21 guns", 261000), ('\nLay down your arms', 265190), ('\nGive up the fight', 268169), ("\nOne' 21 guns", 271909), ("\nThrow up your arms into the sky'", 276960), ("\nOne' 21 guns", 284380), ('\nLay down your arms', 288770), ('\nGive up the fight', 291719), ("\nOne' 21 guns", 296150), ("\nThrow up your arms into the sky'", 301299), ('\nYou and I', 307210)])
        if sync_lrc:
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


class ID3TagItem:
    def __init__(self, tag_name, getter, setter):
        self.tag_name = tag_name
        self.getter = getter
        self.setter = setter

    def __get__(self, obj: "ID3Tags", type=None):
        items = obj.tag.getall(self.tag_name)
        if len(items) >= 1:
            return items[0]
        return None

    def __set__(self, obj: "ID3Tags", value) -> None:
        if value:
            obj.tag.setall(self.tag_name, [self.setter(value)])


class ID3Tags_:
    title = ID3TagItem('TIT2', lambda i: i.text[0], lambda i: TIT2(encoding=Encoding.UTF8, text=i))
    album = ID3TagItem('TALB', lambda i: i.text[0], lambda i: TALB(encoding=Encoding.UTF8, text=i))
    artist = ID3TagItem('TPE1', lambda i: i.text[0], lambda i: TPE1(encoding=Encoding.UTF8, text=i))
    sync_lrc = ID3TagItem('SYLT', lambda i: i.text,
                          lambda i: SYLT(encoding=Encoding.UTF8, lang='eng', format=2, type=1, text=i))
    unsync_lrc = ID3TagItem('USLT', lambda i: i.text, lambda i: USLT(encoding=Encoding.UTF8, lang='eng', text=i))
    url = ID3TagItem('WXXX', lambda i: i.url, lambda i: WXXX(encoding=Encoding.UTF8, url=i))
    cover = ID3TagItem('APIC', lambda i: i.data, lambda i: APIC(
        encoding=Encoding.LATIN1,  # if other apple music/itunes  can't display img
        mime='image/jpeg',  # image/jpeg or image/png
        type=PictureType.COVER_FRONT,
        data=i))

    def __init__(self, mp3path):
        self.file_path = mp3path
        try:
            self.tag = ID3(mp3path)
        except ID3NoHeaderError:
            self.tag = ID3()

    def save(self, file_path=None):
        file_path = file_path or self.file_path
        self.tag.save(file_path or self.file_path, v2_version=3)
