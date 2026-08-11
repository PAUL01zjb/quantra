"""Observability providers: Langfuse tracer with a no-op fallback."""

from __future__ import annotations

from quantra.config import Settings


class NullTracer:
    def trace(self, name: str, **attributes):
        return None


class LangfuseTracer:
    def __init__(self, settings: Settings):
        try:
            from langfuse import Langfuse
        except ImportError as exc:
            raise RuntimeError(
                "langfuse not installed. Add the production extras: "
                "pip install -e '.[production]'"
            ) from exc
        self.client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )

    def trace(self, name: str, **attributes):
        return self.client.trace(name=name, **attributes)


def build_tracer(settings: Settings) -> NullTracer | LangfuseTracer:
    if settings.observability == "langfuse":
        return LangfuseTracer(settings)
    return NullTracer()
