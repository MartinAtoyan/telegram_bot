import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from main import BOT_TOKEN, start, match, delete, load_users, handle_message

telegram_app = Application.builder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("match", match))
telegram_app.add_handler(CommandHandler("delete", delete))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_app.initialize()
    await telegram_app.start()
    asyncio.create_task(telegram_app.updater.start_polling())

    yield

    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"status": "Study Partner Matching Bot - Active", "message": "Ready to connect students!"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "bot_running": telegram_app.running,
        "total_users": len(load_users())
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)