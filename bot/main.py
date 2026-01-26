import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, MenuButtonCommands
from redis.asyncio import Redis

from app.core import load
from bot.core import BotSettings
from bot.handlers import register_handlers


async def main():
    """Main function to start the bot."""
    config = load()
    # Setup logging
    bot_settings = BotSettings(
        bot_token=config.environment.bot_token,
        redis_url=config.environment.redis_url,
        api_base_url=config.environment.api_base_url,
    )
    logging.basicConfig(level=config.environment.log_level)

    # Initialize Redis for FSM
    redis = Redis.from_url(bot_settings.redis_url)
    storage = RedisStorage(redis)

    # Initialize bot and dispatcher
    bot = Bot(token=bot_settings.bot_token)
    dp = Dispatcher(storage=storage)

    # Register handlers
    register_handlers(dp)

    # Set bot commands
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(
            command="parse", description="Start parsing Instagram reels"
        ),
    ]
    await bot.set_my_commands(commands)

    # Set menu button to commands
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
