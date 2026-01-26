from aiogram import Dispatcher

from . import parse_handler, start_handler


def register_handlers(dp: Dispatcher):
    """Register all handlers"""
    start_handler.register(dp)
    parse_handler.register(dp)
