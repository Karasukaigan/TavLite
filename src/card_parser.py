"""SillyTavern PNG Character Card Parser"""

import struct, base64, json, os, time
from typing import Union, Dict, Any
try:
    from PIL import Image
    from io import BytesIO
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from src.state import _save_concept_art_file
from src.logger import get_runtime_logger
_log = get_runtime_logger("card_parser")


class SillyTavernCardParser:
    """Parser for SillyTavern PNG character cards."""

    def __init__(self):
        self._sig = b'\x89PNG\r\n\x1a\n'
        self._base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._public_dir = os.path.join(self._base_dir, "public")

    def parse_png_character_card(self, source: Union[str, bytes], convert_to_webp: bool = True) -> Dict[str, Any]:
        """Parse PNG file and extract character card data."""
        data = open(source, 'rb').read() if isinstance(source, str) else source if isinstance(source, bytes) else (_ for _ in ()).throw(TypeError("source must be a file path (str) or bytes"))
        if data[:8] != self._sig:
            raise ValueError("Invalid PNG file")

        pos, chunks, char_data = 8, [], None
        while pos < len(data):
            length = struct.unpack('>I', data[pos:pos+4])[0]
            chunk_type = data[pos+4:pos+8]
            chunk_data = data[pos+8:pos+8+length]
            raw_chunk = data[pos:pos+8+length+4]
            chunks.append((chunk_type, chunk_data, raw_chunk))

            if chunk_type == b'tEXt':
                null_idx = chunk_data.find(b'\x00')
                if null_idx != -1:
                    keyword = chunk_data[:null_idx].decode('latin-1', errors='replace')
                    if keyword.lower() in ('chara', 'ccv3'):
                        try:
                            parsed = json.loads(base64.b64decode(chunk_data[null_idx+1:]).decode('utf-8'))
                            if char_data is None or keyword.lower() == 'ccv3':
                                char_data = parsed
                        except: pass
            pos += 8 + length + 4

        if char_data is None:
            raise ValueError("No data found")

        clean_chunks = [data[:8]]
        for ct, cd, raw in chunks:
            if ct == b'tEXt':
                null_idx = cd.find(b'\x00')
                if null_idx != -1:
                    keyword = cd[:null_idx].decode('latin-1', errors='replace').lower()
                    if keyword in ('chara', 'ccv3'):
                        continue
            clean_chunks.append(raw)
        
        image_data = b''.join(clean_chunks)
        if convert_to_webp:
            if not HAS_PIL:
                raise
            img = Image.open(BytesIO(image_data))
            webp_buffer = BytesIO()
            img.save(webp_buffer, format='WEBP', quality=85)
            image_data = webp_buffer.getvalue()
        
        _log.info("PNG card parsed: %s", char_data.get("data", {}).get("name", "unknown"))
        return {'card': char_data, 'image_base64': f"data:image/{'webp' if convert_to_webp else 'png'};base64,{base64.b64encode(image_data).decode('ascii')}"}

    def process_data(self, raw: Dict[str, Any]) -> Union[Dict[str, Any], bool]:
        """Convert raw data to specified structure."""
        try:
            rd = raw["card"]["data"]
            name = rd["name"]
            data = {name: {"system_prompt": "", "updated_at": int(time.time() * 1000)}}
            
            if "description" in rd:
                data[name]["system_prompt"] += rd["description"]
            if "first_mes" in rd:
                data[name]["context"] = [{"role": "assistant", "content": rd["first_mes"]}]
            if "alternate_greetings" in rd:
                data[name]["messages"] = rd["alternate_greetings"]
            if "image_base64" in raw:
                data[name]["concept_art"] = _save_concept_art_file(raw["image_base64"], name)
            if "tags" in rd:
                data[name]["tags"] = rd["tags"]
            if "modification_date" in rd:
                data[name]["updated_at"] = rd["modification_date"]
            
            for key in ["mes_example", "system_prompt", "scenario", "personality", "creator_notes"]:
                if key in rd and rd[key].strip():
                    data[name]["system_prompt"] += f'\n\n<{key}>{rd[key]}</{key}>'
            
            # return json.loads(json.dumps(data).replace("{{char}}", name).replace("{{Char}}", name).replace("{{user}}", "player").replace("{{User}}", "Player"))
            return json.loads(json.dumps(data))
        except Exception as e:
            return False

    def save_as_json(self, result: Dict[str, Any], output_dir: str = None) -> str:
        """Save character card as JSON file."""
        if output_dir is None:
            output_dir = os.path.join(self._public_dir, "json", "cards")
        try:
            name = result["card"]["data"]["name"]
            filename = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip() + ".json"
        except (KeyError, TypeError):
            filename = f"{int(time.time() * 1000)}.json"
        
        filepath = os.path.join(output_dir or self._public_dir, filename)
        json_data = self.process_data(result)
        if not json_data:
            return
        
        os.makedirs(output_dir or self._public_dir, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        return filepath

    def convert_file(self, input_path: str, output_dir: str = None) -> Dict[str, Any]:
        """Convert a PNG character card file to JSON."""
        result = self.parse_png_character_card(input_path)
        if output_dir is None:
            output_dir = os.path.join(self._public_dir, "json", "cards")
        return {'result': result, 'saved_path': self.save_as_json(result, output_dir)}


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python sillytavern_card_parser.py <character.png>")
        sys.exit(1)

    parser = SillyTavernCardParser()
    conversion = parser.convert_file(sys.argv[1])
    print(conversion['result'])
    print("Character name:", conversion['result']["card"]["data"]["name"])
    print(f"Saved character card to: {conversion['saved_path']}")