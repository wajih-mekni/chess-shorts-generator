"""Piece-attached media syntax and local asset configuration; no rendering side effects."""
from copy import deepcopy
from math import isfinite
from pathlib import Path
import re
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
PIECE_MEME_DEFAULTS = dict(
    when='land',
    dur=.8,
    scale=.58,
    x=0,
    y=0,
    shape='none',
    follow='full',
    loop=False,
    hold=False,
    audio=False
)


# Logical board pixels, based on the 45x45 SVG silhouettes (100px sprites).
# Keep crowns, bases and outlines visible around the small face overlay.
PIECE_MEME_ANCHORS = {
    'pawn': dict(scale=.46, x=0, y=-3),
    'knight': dict(scale=.52, x=-3, y=-5),
    'bishop': dict(scale=.48, x=0, y=-6),
    'rook': dict(scale=.52, x=0, y=0),
    'queen': dict(scale=.55, x=0, y=-8),
    'king': dict(scale=.55, x=0, y=-8),
}


def validate_options(options):
    unknown = options.keys() - PIECE_MEME_DEFAULTS.keys()
    if unknown:
        raise ValueError(f'Unknown piece meme options: {sorted(unknown)}')
    result = dict(options)
    for name, allowed in dict(when={'start', 'land'}, shape={'none', 'circle', 'rounded'},
                              follow={'full'}).items():
        if name in result and result[name] not in allowed:
            raise ValueError(f'Piece meme {name} must be one of {sorted(allowed)}')
    for name in ('dur', 'scale', 'x', 'y'):
        if name not in result:
            continue
        value = result[name]
        if isinstance(value, bool):
            raise ValueError(f'Invalid piece meme {name}')
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValueError(f'Piece meme {name} must be a number') from None
        if not isfinite(value) or (name in ('dur', 'scale') and value <= 0):
            raise ValueError(f'Piece meme {name} must be finite' + (' and positive' if name in ('dur', 'scale') else ''))
        result[name] = value
    for name in ('loop', 'hold', 'audio'):
        if name in result:
            value = result[name]
            if value in ('true', 'false'):
                value = value == 'true'
            if not isinstance(value, bool):
                raise ValueError(f'Piece meme {name} must be true or false')
            result[name] = value
    if result.get('hold') and 'dur' in result:
        raise ValueError('Piece meme dur and hold=true cannot be combined')
    return result


def parse_piece_meme(token, enabled=True):
    """Remove a dedicated parenthesized directive before any existing suffix parsing."""
    pattern = r'\((piece|pm|pm-remove):([^()]*)\)'
    matches = list(re.finditer(pattern, token))
    stripped = re.sub(pattern, '', token)
    if re.search(r'\((?:piece|pm|pm-remove):', stripped):
        raise ValueError(f'Unclosed piece meme directive: {token!r}')
    if not enabled or not matches:
        return stripped, None
    directives = []
    for match in matches:
        fields = match[2].split(',')
        target = None
        name = fields[0]
        if match[1] == 'pm':
            target, separator, name = name.partition(':')
            if not separator or not re.fullmatch(r'[a-h][1-8]', target):
                raise ValueError('Piece meme target must be a square such as e8')
        if match[1] == 'pm-remove':
            target = name
            if not re.fullmatch(r'[a-h][1-8]', target):
                raise ValueError('Piece meme removal target must be a square such as e8')
        if match[1] != 'pm-remove' and not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', name):
            raise ValueError('Piece meme ID must be a registry name, not a path')
        options = {}
        for field in fields[1:]:
            option, separator, value = field.partition('=')
            if not separator or option in options:
                raise ValueError(f'Invalid or duplicate piece meme option: {field!r}')
            options[option] = value
        if match[1] == 'pm-remove':
            if options.keys() - {'when'}:
                raise ValueError('Piece meme removal only accepts when=start or when=land')
            directive = dict(remove=True, **validate_options(options))
        else:
            directive = dict(id=name, **validate_options(options))
        if target is not None:
            directive['target'] = target
        directives.append(directive)
    return stripped, directives[0] if len(directives) == 1 else directives


def configure_piece_memes(scene, mode='off', registry=None, initial=None):
    if mode not in ('on', 'off'):
        raise ValueError('PIECE_MEME_MODE must be "on" or "off"')
    # Copy both lists together to preserve their shared move references.
    scene = deepcopy(scene)
    config = dict(enabled=False, entries={})
    registry = registry or {}
    def add_entry(key, directive):
        if directive.get('remove'):
            config['entries'][key] = dict(remove=True, target=directive['target'],
                                          when=directive.get('when', 'land'))
            return
        name = directive['id']
        if name not in registry:
            raise ValueError(f'Unknown piece meme ID {name!r}; register it in PIECE_MEMES')
        asset = registry[name]
        if asset.get('type') not in ('image', 'video'):
            raise ValueError(f'Piece meme {name!r} type must be image or video')
        src = asset.get('src', '')
        if not isinstance(src, str) or not src.startswith('assets/') or '\\' in src:
            raise ValueError(f'Piece meme {name!r} src must be a local assets/ path')
        path = (ROOT / src).resolve()
        if not path.is_relative_to((ROOT / 'assets').resolve()) or not path.is_file():
            raise ValueError(f'Piece meme {name!r} asset not found inside assets/: {src}')
        options = validate_options({k:v for k,v in asset.items() if k not in ('src','type')})
        options.update(validate_options({k:v for k,v in directive.items() if k not in ('id', 'target')}))
        options = validate_options(options)
        config['entries'][key] = dict(PIECE_MEME_DEFAULTS, **options)
        config['entries'][key].update(id=name, type=asset['type'], src='../'+quote(path.relative_to(ROOT).as_posix()))
        config['entries'][key]['placement'] = {k:v for k,v in options.items() if k in ('scale','x','y')}
        if 'target' in directive:
            config['entries'][key]['target'] = directive['target']
    for index, move in enumerate(scene['moves']):
        directive = move.pop('piece_meme', None)
        if mode == 'off' or directive is None:
            continue
        directives = directive if isinstance(directive, list) else [directive]
        keys = []
        for number, directive in enumerate(directives):
            key = str(index) if len(directives) == 1 else f'{index}:{number}'
            add_entry(key, directive)
            keys.append(key)
        move['piece_meme'] = keys[0] if len(keys) == 1 else keys
    if mode == 'on' and initial:
        if not isinstance(initial, list):
            raise ValueError('INITIAL_PIECE_MEMES must be a list')
        config['initial'] = []
        for index, entry in enumerate(initial):
            if not isinstance(entry, dict) or not re.fullmatch(r'[a-h][1-8]', str(entry.get('square', ''))):
                raise ValueError('Initial piece meme requires a square such as e8')
            if not isinstance(entry.get('meme'), str):
                raise ValueError('Initial piece meme requires a meme registry name')
            options = {k:v for k,v in entry.items() if k not in ('square','meme')}
            if 'when' in options:
                raise ValueError('Initial piece memes attach at t=0; omit when')
            key = f'initial:{index}'
            add_entry(key, dict(id=entry['meme'], target=entry['square'], **options))
            config['initial'].append(key)
    # JSON round-trips do not preserve the compiler's shared move references.
    events = (event['move'] for event in scene.get('timeline', []) if event.get('type') == 'move')
    for move, event_move in zip(scene['moves'], events):
        key = move.get('piece_meme')
        event_move.pop('piece_meme', None)
        if key is not None:
            event_move['piece_meme'] = key
    config['enabled'] = bool(config['entries'])
    if config['enabled']:
        config['anchors'] = deepcopy(PIECE_MEME_ANCHORS)
    return scene, config
