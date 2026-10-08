import time
import json
import logging
import re
from typing import Any, Optional, Type
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger(__name__)


class GemmaClient:
    """
    Unified LLM client supporting:
    - google_ai_studio (google-generativeai SDK)
    - self_hosted_openai_compatible / huggingface (OpenAI-compat HTTP, e.g. Ollama)
    """

    def __init__(self):
        self.provider = settings.gemma_provider
        self._setup_provider()

    def _setup_provider(self):
        if self.provider == "google_ai_studio":
            import google.generativeai as genai
            genai.configure(api_key=settings.gemma_api_key)
            self._genai = genai
            self._model = genai.GenerativeModel(settings.gemma_model)
        elif self.provider in ("huggingface", "self_hosted_openai_compatible"):
            self.base_url = settings.gemma_base_url
        else:
            logger.warning("Unknown GEMMA_PROVIDER=%s, defaulting to google_ai_studio", self.provider)
            self.provider = "google_ai_studio"
            self._setup_provider()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_json(
        self,
        system: str,
        user: str,
        image: Optional[bytes] = None,
        schema: Optional[Type[BaseModel]] = None,
        db=None,
        skill: str = "unknown",
    ) -> dict:
        """
        Call the LLM and parse its response as JSON.
        Retries once on parse failure. Falls back to empty dict and logs failure.
        """
        start = time.time()
        raw = ""
        error_msg: Optional[str] = None
        success = False
        result: dict = {}
        fallback_used = False

        for attempt in range(2):
            try:
                raw = await self._call_provider(system, user, image)
                parsed = self._extract_json(raw)
                if schema:
                    validated = schema(**parsed)
                    result = validated.model_dump()
                else:
                    result = parsed
                success = True
                break
            except Exception as exc:
                error_msg = str(exc)
                logger.warning("Gemma attempt %d failed (%s): %s", attempt + 1, skill, exc)

        if not success:
            fallback_used = True
            result = {}

        latency = (time.time() - start) * 1000

        if db is not None:
            try:
                await self._log(
                    db, skill, system, user, raw,
                    result if success else None,
                    latency, success, error_msg, fallback_used,
                )
            except Exception as log_exc:
                logger.error("Failed to write AI log: %s", log_exc)

        return result

    # ------------------------------------------------------------------
    # Provider dispatch
    # ------------------------------------------------------------------

    async def _call_provider(self, system: str, user: str, image: Optional[bytes]) -> str:
        if self.provider == "google_ai_studio":
            return await self._call_google(system, user, image)
        return await self._call_openai_compat(system, user, image)

    async def _call_google(self, system: str, user: str, image: Optional[bytes]) -> str:
        import asyncio
        import io
        from PIL import Image

        genai = self._genai
        model = self._model

        if image:
            img = Image.open(io.BytesIO(image))
            parts = [img, user]
            gen_cfg = genai.GenerationConfig(temperature=0.1)
        else:
            parts = [user]
            gen_cfg = genai.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json",
            )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(
                [system, *parts],
                generation_config=gen_cfg,
            ),
        )
        return response.text

    async def _call_openai_compat(self, system: str, user: str, image: Optional[bytes]) -> str:
        import httpx
        import base64

        messages: list = [{"role": "system", "content": system}]
        if image:
            b64 = base64.b64encode(image).decode()
            messages.append({
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": user},
                ],
            })
        else:
            messages.append({"role": "user", "content": user})

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json={"model": settings.gemma_model, "messages": messages, "temperature": 0.1},
                headers={"Authorization": f"Bearer {settings.gemma_api_key or 'ollama'}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    # ------------------------------------------------------------------
    # JSON extraction
    # ------------------------------------------------------------------

    def _extract_json(self, text: str) -> dict:
        # Strip markdown fences
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = text.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Find the outermost JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())

        raise ValueError(f"No JSON object found in response: {text[:200]}")

    # ------------------------------------------------------------------
    # AI log persistence
    # ------------------------------------------------------------------

    async def _log(
        self, db, skill, system, user, raw, parsed,
        latency, success, error, fallback,
    ):
        from app.models.models import AILog

        log = AILog(
            skill=skill,
            prompt_system=system[:2000],
            prompt_user=user[:2000],
            response_raw=(raw or "")[:5000],
            response_parsed=parsed,
            latency_ms=latency,
            success=success,
            error=error,
            fallback_used=fallback,
        )
        db.add(log)
        await db.commit()


gemma_client = GemmaClient()
