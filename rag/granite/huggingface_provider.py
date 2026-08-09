"""Hugging Face Router IBM Granite Provider for AegisMesh AI using AsyncOpenAI SDK."""
import json
import logging
import re
import time
import asyncio
from typing import Any, Optional
from openai import AsyncOpenAI, APIError, APITimeoutError
from .base import LLMProvider

logger = logging.getLogger('aegismesh.llm')

class HuggingFaceCallFailedError(RuntimeError):
    """Custom exception raised when a Hugging Face Router API request fails."""
    pass

class HuggingFaceProvider(LLMProvider):
    """Provider connecting to IBM Granite via Hugging Face Router OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str = '',
        base_url: str = 'https://router.huggingface.co/v1',
        model: str = 'ibm-granite/granite-7b-instruct:featherless-ai'
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/') if base_url else 'https://router.huggingface.co/v1'
        self.model = model or 'ibm-granite/granite-7b-instruct:featherless-ai'

        if self.is_configured():
            logger.info(f"[LLM] Granite provider initialized with base_url={self.base_url}, model={self.model}")
        else:
            logger.warning("[LLM] Missing configuration: HF_TOKEN is empty or unconfigured.")

        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key or 'unconfigured',
            timeout=30.0
        )

    def is_configured(self) -> bool:
        """Check if HF_TOKEN and Router URL are configured."""
        return bool(self.api_key and self.api_key != 'unconfigured' and self.base_url)

    def is_available(self) -> bool:
        """Check availability status."""
        return self.is_configured()

    def get_provider_name(self) -> str:
        """Return human-readable provider status description."""
        return "IBM Granite 7B via Hugging Face"

    def get_provider_info(self) -> dict[str, Any]:
        """Return health/status details for backend/frontend diagnostics."""
        return {
            "name": self.get_provider_name(),
            "type": "huggingface",
            "configured": self.is_configured(),
            "available": self.is_available(),
            "model": self.model,
            "base_url": self.base_url,
            "status": "configured" if self.is_configured() else "missing_configuration"
        }

    async def generate_structured(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
        schema: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Send prompt to Hugging Face Router OpenAI-compatible Chat Completions API and parse JSON."""
        if not self.is_configured():
            err_msg = "HF_TOKEN missing or empty."
            logger.error(f"[LLM] Missing configuration: {err_msg}")
            raise HuggingFaceCallFailedError(err_msg)

        system_instruction = (
            "You are an AI governance reasoning assistant. "
            "Evaluate the proposed AI action against enterprise policy context. "
            "Return valid JSON containing: policy_findings, reasoning, confidence."
        )

        logger.info(f"[LLM] Model request start: calling {self.model} via Hugging Face Router ({self.base_url})")
        start_time = time.time()

        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt[:1500]}
                ],
                temperature=0.1,
                max_tokens=256
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            logger.info(f"[LLM] Model request success: completed in {latency_ms} ms")

            content = completion.choices[0].message.content or ""

            # Clean markdown code fences if present
            clean_content = re.sub(r'^```(json)?\s*', '', content.strip(), flags=re.MULTILINE)
            clean_content = re.sub(r'\s*```$', '', clean_content, flags=re.MULTILINE)

            try:
                json_match = re.search(r'\{.*\}', clean_content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                else:
                    parsed = json.loads(clean_content)
                
                if isinstance(parsed, dict):
                    parsed["provider"] = self.get_provider_name()
                    parsed["latency_ms"] = latency_ms
                    parsed["status"] = "success"
                    return parsed
                return {
                    "provider": self.get_provider_name(),
                    "raw_text": content,
                    "parse_error": True,
                    "reasoning": content,
                    "confidence": 0.88,
                    "latency_ms": latency_ms
                }

            except Exception as parse_err:
                logger.warning(f"[LLM] Failed to parse JSON response from Granite model: {parse_err}")
                return {
                    "provider": self.get_provider_name(),
                    "raw_text": content,
                    "parse_error": True,
                    "reasoning": content[:300],
                    "policy_findings": ["Evaluated by IBM Granite 7B"],
                    "confidence": 0.85,
                    "latency_ms": latency_ms
                }

        except APITimeoutError as timeout_err:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[LLM] Timeout: Hugging Face Router API request timed out after {latency_ms} ms: {timeout_err}")
            raise HuggingFaceCallFailedError(f"Hugging Face Router API timeout after {latency_ms} ms")

        except Exception as err:
            latency_ms = int((time.time() - start_time) * 1000)
            safe_msg = str(err)
            if self.api_key and self.api_key in safe_msg:
                safe_msg = safe_msg.replace(self.api_key, "[REDACTED_HF_TOKEN]")
            logger.error(f"[LLM] HTTP/API failure: {safe_msg} (after {latency_ms} ms)")
            raise HuggingFaceCallFailedError(f"Hugging Face Router API call failed: {safe_msg}")
