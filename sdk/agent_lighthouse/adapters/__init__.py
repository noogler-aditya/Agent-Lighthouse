"""
Framework adapters for zero-touch auto-instrumentation.
"""
from .langchain import LighthouseLangChainCallbackHandler, register_langchain_callbacks
from .crewai import register_crewai_hooks
from .autogen import register_autogen_logging

__all__ = [
    "LighthouseLangChainCallbackHandler",
    "register_langchain_callbacks",
    "register_crewai_hooks",
    "register_autogen_logging",
]
