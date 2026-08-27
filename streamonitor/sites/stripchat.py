import itertools
import json
import os.path
import random
import re
import requests
import base64
import hashlib

from streamonitor.bot import RoomIdBot
from streamonitor.downloaders.hls import getVideoNativeHLS
from streamonitor.enums import Status, Gender, COUNTRIES

proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890',
}

class StripChat(RoomIdBot):
    site = 'StripChat'
    siteslug = 'SC'

    bulk_update = True
    _static_data = None
    _mouflon_cache_filename = 'stripchat_mouflon_keys.json'
    # https://github.com/lossless1024/StreaMonitor/pull/268/files
    _mouflon_keys: dict = {
        "Zeechoej4aleeshi": "ubahjae7goPoodi6",
        "Zokee2OhPh9kugh4": "Quean4cai9boJa5a",
        "Ook7quaiNgiyuhai": "EQueeGh2kaewa3ch",
    }
    _cached_keys: dict[str, bytes] = None
    _PRIVATE_STATUSES = frozenset(["private", "groupShow", "p2p", "virtualPrivate", "p2pVoice"])
    _OFFLINE_STATUSES = frozenset(["off", "idle"])

    _GENDER_MAP = {
        'female': Gender.FEMALE,
        'male': Gender.MALE,
        'maleFemale': Gender.BOTH
    }

    if os.path.exists(_mouflon_cache_filename):
        with open(_mouflon_cache_filename) as f:
            try:
                if not isinstance(_mouflon_keys, dict):
                    _mouflon_keys = {}
                _mouflon_keys.update(json.load(f))
                print('Loaded StripChat mouflon key cache')
            except Exception as e:
                print('Error loading mouflon key cache:', e)

    def __init__(self, username, room_id=None):
        if StripChat._static_data is None:
            StripChat._static_data = {}
            try:
                self.getInitialData()
            except Exception as e:
                print('Error initializing StripChat static data:', e)

        super().__init__(username, room_id)
        self._id = None
        self.vr = False
        self.getVideo = lambda _, url, filename: getVideoNativeHLS(self, url, filename, StripChat.m3u_decoder)

    @classmethod
    def getInitialData(cls):
        session = requests.Session()
        r = session.get('https://zh.stripchat.com/api/front/v3/config/static', proxies=proxies, headers=cls.headers)
        if r.status_code != 200:
            raise Exception("Failed to fetch static data from StripChat")
        StripChat._static_data = r.json().get('static')
        #
        # mmp_origin = StripChat._static_data['featureSettings']['MMPExternalUnitedSourceOrigin']
        # mmp_version = StripChat._static_data['featuresV2']['playerModuleExternalLoading']['mmpVersion']
        # if mmp_version.startswith('v'):
        #     mmp_base = f"{mmp_origin}/{mmp_version}"
        # else:
        #     mmp_base = f"{mmp_origin}/v{mmp_version}"
        #
        # r = session.get(f"{mmp_base}/main.js", proxies=proxies, headers=cls.headers)
        # if r.status_code != 200:
        #     raise Exception("Failed to fetch main.js from StripChat")
        # StripChat._main_js_data = r.text
        #
        # # Find Doppio JS file
        # doppio_js_name = None
        #
        # # Try direct require pattern first (legacy)
        # DOPPIO_REQUIRE_PATTERN = re.compile(r'require\(["\']\./(Doppio[^"\']+\.js)["\']\)')
        # DOPPIO_CHUNK_PATTERN = re.compile(r'n\.e\((\d+)\)\]\)\.then\(n\.bind\(n,\d+\)\)\)\.DoppioWrapper')
        # CHUNK_HASH_PATTERN = re.compile(r'n\.u=e=>"chunk-"\+\{([^}]+)\}\[e\]\+"\.js"')
        # DOPPIO_INDEX_PATTERN = re.compile(r'([0-9]+):"Doppio"')
        # if match := DOPPIO_REQUIRE_PATTERN.search(StripChat._main_js_data):
        #     doppio_js_name = match[1]
        # # Try new webpack chunk pattern: n.e(184)...DoppioWrapper
        # elif match := DOPPIO_CHUNK_PATTERN.search(StripChat._main_js_data):
        #     chunk_id = match[1]
        #     # Find the chunk hash mapping
        #     if hash_match := CHUNK_HASH_PATTERN.search(StripChat._main_js_data):
        #         chunk_mapping = hash_match[1]
        #         # Parse the mapping to find the hash for our chunk_id
        #         # Format: 149:"hash1",184:"hash2",...
        #         for mapping in chunk_mapping.split(','):
        #             if ':' in mapping:
        #                 cid, chash = mapping.split(':', 1)
        #                 if cid.strip() == chunk_id:
        #                     # Remove quotes from hash
        #                     chash = chash.strip().strip('"')
        #                     doppio_js_name = f"chunk-{chash}.js"
        #                     break
        # elif match := DOPPIO_INDEX_PATTERN.search(StripChat._main_js_data):
        #     idx = match[1]
        #     # Look for hash in various formats
        #     for pattern in [
        #         rf'{idx}:\\"([a-zA-Z0-9]{{20}})\\"',
        #         rf'{idx}:"([a-zA-Z0-9]{{20}})"',
        #         rf'"{idx}":"([a-zA-Z0-9]{{20}})"',
        #     ]:
        #         if hash_match := re.search(pattern, StripChat._main_js_data):
        #             doppio_js_name = f"chunk-Doppio-{hash_match[1]}.js"
        #             break
        #
        # if not doppio_js_name:
        #     raise Exception("Could not find Doppio JS file in main.js")
        #
        # r = session.get(f"{mmp_base}/{doppio_js_name}", proxies=proxies, headers=cls.headers)
        # if r.status_code != 200:
        #     raise Exception("Failed to fetch doppio.js from StripChat")
        # StripChat._doppio_js_data = r.text

        # r = session.get(f"{mmp_base}/main.js", proxies=proxies, headers=cls.headers)
        # if r.status_code != 200:
        #     raise Exception("Failed to fetch main.js from StripChat")
        # StripChat._main_js_data = r.content.decode('utf-8')
        #
        # doppio_js_index = re.findall('([0-9]+):"Doppio"', StripChat._main_js_data)[0]
        # doppio_js_hash = re.findall(f'{doppio_js_index}:\\"([a-zA-Z0-9]{{20}})\\"', StripChat._main_js_data)[0]
        #
        # r = session.get(f"{mmp_base}/chunk-Doppio-{doppio_js_hash}.js", proxies=proxies, headers=cls.headers)
        # if r.status_code != 200:
        #     raise Exception("Failed to fetch doppio.js from StripChat")
        # StripChat._doppio_js_data = r.content.decode('utf-8')

    @classmethod
    def m3u_decoder(cls, content):
        _mouflon_filename = 'media.mp4'

        def _decode(encrypted_b64: str, key: str) -> str:
            if cls._cached_keys is None:
                cls._cached_keys = {}
            hash_bytes = cls._cached_keys[key] if key in cls._cached_keys \
                else cls._cached_keys.setdefault(key, hashlib.sha256(key.encode("utf-8")).digest())
            encrypted_data = base64.b64decode(encrypted_b64 + "==")
            return bytes(a ^ b for (a, b) in zip(encrypted_data, itertools.cycle(hash_bytes))).decode("utf-8")

        psch, pkey, pdkey = StripChat._getMouflonFromM3U(content)

        if psch == 'v1':
            _mouflon_file_attr = "#EXT-X-MOUFLON:FILE:"
        elif psch == 'v2':
            _mouflon_file_attr = "#EXT-X-MOUFLON:URI:"
        else:
            return None

        decoded = ''
        lines = content.splitlines()
        last_decoded_file = None
        for line in lines:
            if line.startswith(_mouflon_file_attr):
                if psch == 'v1':
                    last_decoded_file = _decode(line[len(_mouflon_file_attr):], pdkey)
                elif psch == 'v2':
                    uri = line[len(_mouflon_file_attr):]
                    encoded_part = uri.split('_')[-2]
                    decoded_part = _decode(encoded_part[::-1], pdkey)
                    last_decoded_file = uri.replace(encoded_part, decoded_part).split('/', maxsplit=4)[4]
            elif line.endswith(_mouflon_filename) and last_decoded_file:
                decoded += (line.replace(_mouflon_filename, last_decoded_file)) + '\n'
                last_decoded_file = None
            else:
                decoded += line + '\n'
        return decoded

    @classmethod
    def getMouflonDecKey(cls, pkey):
        if cls._mouflon_keys is None:
            cls._mouflon_keys = {}
        if pkey in cls._mouflon_keys:
            return cls._mouflon_keys[pkey]
        # else: find pdkey
        return None

    @staticmethod
    def _getMouflonFromM3U(m3u8_doc):
        _start = 0
        _needle = '#EXT-X-MOUFLON:'
        while _needle in (_doc := m3u8_doc[_start:]):
            _mouflon_start = _doc.find(_needle)
            if _mouflon_start > 0:
                _mouflon = _doc[_mouflon_start:m3u8_doc.find('\n', _mouflon_start)].strip().split(':')
                psch = _mouflon[2]
                pkey = _mouflon[3]
                pdkey = StripChat.getMouflonDecKey(pkey)
                if pdkey:
                    return psch, pkey, pdkey
            _start += _mouflon_start + len(_needle)
        return None, None, None

    def getWebsiteURL(self):
        return "https://zh.stripchat.com/" + self.username

    def getVideoUrl(self):
        return self.getWantedResolutionPlaylist(None)

    def getPlaylistVariants(self, url):
        url = "https://edge-hls.{host}/hls/{id}{vr}/master/{id}{vr}{auto}.m3u8".format(
                host='doppiocdn.' + random.choice(['org', 'com', 'net']),
                id=self.room_id,
                vr='_vr' if self.vr else '',
                auto='_auto' if not self.vr else ''
            )
        result = self.session.get(url, proxies=proxies, headers=self.headers, cookies=self.cookies)
        m3u8_doc = result.content.decode("utf-8")
        psch, pkey, pdkey = StripChat._getMouflonFromM3U(m3u8_doc)
        if pdkey is None:
            self.log(f'Failed to get mouflon decryption key')
            return []
        self.log(f"Extracted key {psch}, {pkey}, {pdkey}")
        variants = super().getPlaylistVariants(m3u_data=m3u8_doc)
        return [variant | {'url': f'{variant["url"]}{"&" if "?" in variant["url"] else "?"}psch={psch}&pkey={pkey}'}
                for variant in variants]

    @staticmethod
    def uniq(length=16):
        chars = ''.join(chr(i) for i in range(ord('a'), ord('z')+1))
        chars += ''.join(chr(i) for i in range(ord('0'), ord('9')+1))
        return ''.join(random.choice(chars) for _ in range(length))

    def _getStatusData(self, username):
        r = self.session.get(
            # f'https://zh.stripchat.com/api/front/v2/models/username/{username}/cam?uniq={StripChat.uniq()}',
            f'https://zh.stripchat.com/api/front/users/user-ids/{username}',
            proxies=proxies,
            headers=self.headers
        )

        try:
            data = r.json()
        except requests.exceptions.JSONDecodeError:
            self.log('Failed to parse JSON response')
            return None
        return data

    def _update_lastInfo(self, data):
        if data is None:
            return None
        if 'cam' not in data:
            if 'error' in data:
                error = data['error']
                if error == 'Not Found':
                    return Status.NOTEXIST
                self.logger.warn(f'Status returned error: {error}')
            return Status.UNKNOWN

        self.lastInfo = {'model': data['user']['user']}
        if isinstance(data['cam'], dict):
            self.lastInfo |= data['cam']
        return None

    def getRoomIdFromUsername(self, username):
        if username == self.username and self.room_id is not None:
            return self.room_id

        data = self._getStatusData(username)
        # if username == self.username:
        #     self._update_lastInfo(data)
        #
        # if 'user' not in data:
        #     return None
        # if 'user' not in data['user']:
        #     return None
        # if 'id' not in data['user']['user']:
        #     return None

        # return str(data['user']['user']['id'])

        return str(data['id'])

    def getStatus(self):
        data = self._getStatusData(self.username)
        if data is None:
            return Status.UNKNOWN

        error = self._update_lastInfo(data)
        if error:
            return error

        if 'user' in data and 'user' in data['user']:
            model_data = data['user']['user']
            if model_data.get('gender'):
                self.gender = StripChat._GENDER_MAP.get(model_data.get('gender'))

            if model_data.get('country'):
                self.country = model_data.get('country', '').upper()
            elif model_data.get('languages'):
                for lang in model_data['languages']:
                    if lang.upper() in COUNTRIES:
                        self.country = lang.upper()
                        break

        status = self.lastInfo['model'].get('status')
        if status == "public" and self.lastInfo["isCamAvailable"] and self.lastInfo["isCamActive"]:
            return Status.PUBLIC
        if status in self._PRIVATE_STATUSES:
            return Status.PRIVATE
        if status in self._OFFLINE_STATUSES:
            return Status.OFFLINE
        if self.lastInfo['model'].get('isDeleted') is True:
            return Status.NOTEXIST
        if data['user'].get('isGeoBanned') is True:
            return Status.RESTRICTED
        self.logger.warn(f'Got unknown status: {status}')
        return Status.UNKNOWN

    @classmethod
    def getStatusBulk(cls, streamers):
        model_ids = {}
        for streamer in streamers:
            if not isinstance(streamer, StripChat):
                continue
            if streamer.room_id:
                model_ids[streamer.room_id] = streamer

        base_url = 'https://zh.stripchat.com/api/front/models/list?'
        batch_num = 100
        data_map = {}
        model_id_list = list(model_ids)
        for _batch_ids in [model_id_list[i:i+batch_num] for i in range(0, len(model_id_list), batch_num)]:
            session = requests.Session()
            session.headers.update(cls.headers)
            r = session.get(base_url + '&'.join(f'modelIds[]={model_id}' for model_id in _batch_ids), proxies=proxies, timeout=10)

            try:
                data = r.json()
            except requests.exceptions.JSONDecodeError:
                print('Failed to parse JSON response')
                return
            data_map |= {str(model['id']): model for model in data.get('models', [])}

        for model_id, streamer in model_ids.items():
            model_data = data_map.get(model_id)
            if not model_data:
                streamer.setStatus(Status.UNKNOWN)
                continue
            if model_data.get('gender'):
                streamer.gender = cls._GENDER_MAP.get(model_data.get('gender'))
            if model_data.get('country'):
                streamer.country = model_data.get('country', '').upper()
            status = model_data.get('status')
            if status == "public" and model_data.get("isOnline"):
                streamer.setStatus(Status.PUBLIC)
            elif status in cls._PRIVATE_STATUSES:
                streamer.setStatus(Status.PRIVATE)
            elif status in cls._OFFLINE_STATUSES:
                streamer.setStatus(Status.OFFLINE)
            else:
                print(f'[{streamer.siteslug}] {streamer.username}: Bulk update got unknown status: {status}')
                streamer.setStatus(Status.UNKNOWN)
