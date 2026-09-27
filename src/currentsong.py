import json
from dataclasses import dataclass
from html import unescape
from pathlib import Path

FIELDS = {'file', 'title', 'artist', 'album', 'state', 'track', 'duration'}
RENDERERS = {
    'AirPlay Active': ('AirPlay', 'aplmeta.json'),
    'Spotify Active': ('Spotify', 'spotmeta.json'),
}


@dataclass(frozen=True, slots=True)
class Song:
    title: str
    artist: str
    album: str = ''
    state: str = ''
    source: str = 'MPD'
    tracknumber: int | None = None
    duration_ms: int | None = None

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.title, self.artist, self.album


def _int(text: object, scale: float = 1) -> int | None:
    try:
        return int(float(text) * scale) or None
    except (TypeError, ValueError):
        return None


def _renderer_duration(meta_file: Path, title: str, artist: str) -> int | None:
    """Renderer sessions carry no duration in currentsong.txt; moOde's own
    metadata cache does, in ms. Used only when it describes the same track."""
    try:
        meta = json.loads(meta_file.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(meta, dict) or (meta.get('title'), meta.get('artist')) != (title, artist):
        return None
    return _int(meta.get('duration'))


def read(path: Path) -> Song | None:
    """Parse moOde's currentsong.txt.

    MPD mode carries state=. Renderer mode carries only file=<Name> Active,
    plus track metadata for AirPlay/Spotify while audio is flowing; without
    it the renderer is paused. Any other renderer publishes no metadata and
    reads as stop. None: file empty or mid-rewrite, nothing to act on."""
    fields = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        key, sep, value = line.partition('=')
        if sep and key in FIELDS:
            fields[key] = unescape(value).strip()
    if 'file' not in fields:
        return None

    title, artist = fields.get('title', ''), fields.get('artist', '')
    playable = bool(title and artist)
    state = fields.get('state', '').lower()
    source, duration_ms = 'MPD', _int(fields.get('duration'), 1000)

    if not state:
        renderer = fields['file']
        if renderer in RENDERERS:
            source, meta_name = RENDERERS[renderer]
            state = 'play' if playable else 'pause'
            if playable:
                duration_ms = _renderer_duration(path.with_name(meta_name), title, artist)
        elif renderer.endswith(' Active'):
            source, state = renderer.removesuffix(' Active'), 'stop'
        else:
            return None
    elif state == 'play' and not playable:
        return None

    return Song(
        title=title,
        artist=artist,
        album=fields.get('album', ''),
        state=state,
        source=source,
        tracknumber=_int(fields.get('track', '').split('/')[0]),
        duration_ms=duration_ms,
    )
