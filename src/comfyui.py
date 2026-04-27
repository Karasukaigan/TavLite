# ./src/comfyui.py
import hashlib
import json
import secrets
import time
from typing import Any, Dict, Optional
import aiohttp
import asyncio
import os

class ComfyUIClient:
    def __init__(
            self, 
            base_url: str = "http://127.0.0.1:8188/", 
            aspect_ratio: str = "portrait",
            type: str = "zit", 
            diffusion: str = "z_image_turbo_bf16.safetensors",
            clip: str = "qwen_3_4b.safetensors",
            vae: str = "ae.safetensors"
        ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.aspect_ratio = (aspect_ratio or "portrait").lower()
        if self.aspect_ratio not in {"portrait", "landscape", "square"}:
            self.aspect_ratio = "portrait"
        self.type = (type.strip() or "zit").lower()
        if self.type not in {"zit", "sdxl"}:
            self.type = "zit"
        self.diffusion = diffusion.strip()
        self.clip = clip.strip()
        self.vae = vae.strip()

        self._public_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public")
        self.workflow_path = os.path.join(self._public_dir, "json", "workflows", f"{self.type}_t2i.json")
        self.output_dir = os.path.join(self._public_dir, "img", "comfyui")
        os.makedirs(self.output_dir, exist_ok=True)

    async def check(self, timeout: int = 10) -> bool:
        if not self.base_url or not self.diffusion:
            return False
        if self.type in {"zit"}:
            if not self.clip or not self.vae:
                return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/system_stats", timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status != 200:
                        return False
        except Exception:
            return False
        return True

    async def run_t2i(
        self,
        prompt: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        timeout_seconds: int = 240,
    ) -> str:
        if not await self.check():
            return ""
        workflow = self._load_workflow()
        if not workflow:
            return ""
        self._apply_models(workflow)
        if prompt:
            self._apply_prompt(workflow, prompt)
        if width is None or height is None:
            ar = (self.aspect_ratio or "portrait").lower()
            if ar == "landscape":
                w, h = 1280, 960
            elif ar == "square":
                w, h = 1024, 1024
            else:
                w, h = 960, 1280
            width = width or w
            height = height or h
        self._apply_size(workflow, width, height)
        prompt_id = await self._submit_workflow(workflow)
        if not prompt_id:
            return ""
        history_entry = await self._wait_for_history(prompt_id, timeout_seconds)
        if not history_entry:
            return ""
        image_info = self._extract_first_image_info(history_entry)
        if not image_info:
            return ""
        return await self._download_image(image_info)

    def _load_workflow(self) -> Dict[str, Any]:
        try:
            with open(self.workflow_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
                self._apply_random_seeds(workflow)
                return workflow
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            return {}
        
    def _apply_random_seeds(self, workflow: Dict[str, Any]) -> None:
        # ComfyUI versions may reject -1; treat <=0 as "randomize".
        for node in workflow.values():
            class_type = node.get("class_type")
            inputs = node.get("inputs", {})
            if class_type == "KSampler":
                seed = inputs.get("seed")
                if seed is None or (isinstance(seed, int) and seed <= 0):
                    inputs["seed"] = secrets.randbelow(2**63 - 1)
            if class_type == "RandomNoise":
                noise_seed = inputs.get("noise_seed")
                if noise_seed is None or (isinstance(noise_seed, int) and noise_seed <= 0):
                    inputs["noise_seed"] = secrets.randbelow(2**63 - 1)

    def _apply_models(self, workflow: Dict[str, Any]) -> None:
        if self.type == "sdxl":
            for node in workflow.values():
                if node.get("class_type") == "CheckpointLoaderSimple" and self.diffusion:
                    node.get("inputs", {})["ckpt_name"] = self.diffusion
        else:
            for node in workflow.values():
                class_type = node.get("class_type")
                inputs = node.get("inputs", {})
                if class_type == "UNETLoader" and self.diffusion:
                    inputs["unet_name"] = self.diffusion
                if class_type == "CLIPLoader" and self.clip:
                    inputs["clip_name"] = self.clip
                if class_type == "VAELoader" and self.vae:
                    inputs["vae_name"] = self.vae

    def _apply_prompt(self, workflow: Dict[str, Any], prompt: str) -> None:
        pos_node = self._find_positive_prompt_node(workflow)
        if not pos_node:
            return
        inputs = pos_node.get("inputs", {})
        existing = inputs.get("text", "")
        if self.type == "zit":
            inputs["text"] = prompt
            return
        if not existing:
            inputs["text"] = prompt
            return
        trimmed = existing.rstrip()
        if trimmed.endswith((",", ".", "!", "?", ":", ";")):
            sep = " "
        else:
            sep = ", "
        inputs["text"] = f"{existing}{sep}{prompt}"

    def _apply_size(self, workflow: Dict[str, Any], width: int, height: int) -> None:
        for node in workflow.values():
            inputs = node.get("inputs", {})
            if "width" in inputs and "height" in inputs:
                inputs["width"] = int(width)
                inputs["height"] = int(height)

    def _find_positive_prompt_node(self, workflow: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for node in workflow.values():
            if node.get("class_type") == "KSampler":
                positive = node.get("inputs", {}).get("positive")
                if isinstance(positive, list) and len(positive) >= 1:
                    node_id = str(positive[0])
                    return workflow.get(node_id)
        return None

    async def _submit_workflow(self, workflow: Dict[str, Any]) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/prompt",
                    json={"prompt": workflow},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    return data.get("prompt_id")
        except Exception:
            return None

    async def _wait_for_history(self, prompt_id: str, timeout_seconds: int) -> Optional[Dict[str, Any]]:
        deadline = time.monotonic() + max(1, int(timeout_seconds))
        async with aiohttp.ClientSession() as session:
            while time.monotonic() < deadline:
                try:
                    async with session.get(
                        f"{self.base_url}/history/{prompt_id}",
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            entry = data.get(prompt_id)
                            if entry and entry.get("outputs"):
                                return entry
                except Exception:
                    pass
                await asyncio.sleep(1)
        return None

    def _extract_first_image_info(self, history_entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        outputs = history_entry.get("outputs", {})
        for node_output in outputs.values():
            images = node_output.get("images")
            if isinstance(images, list) and images:
                if isinstance(images[0], dict):
                    return images[0]
        return None

    async def _download_image(self, image_info: Dict[str, Any]) -> str:
        filename = image_info.get("filename")
        if not filename:
            return ""
        params = {
            "filename": filename,
            "subfolder": image_info.get("subfolder", ""),
            "type": image_info.get("type", ""),
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/view",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        return ""
                    content = await resp.read()
        except Exception:
            return ""
        if not content:
            return ""
        image_hash = hashlib.sha256(content).hexdigest()

        output_path = os.path.join(self.output_dir, f"{image_hash}.png")
        with open(output_path, 'wb') as f:
            f.write(content)
        return f"/img/comfyui/{image_hash}.png"
    
if __name__ == "__main__":
    pass