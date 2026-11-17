
import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from anthropic import AsyncAnthropic

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not TELEGRAM_TOKEN or not ANTHROPIC_API_KEY:
    raise RuntimeError("Railway 환경변수를 확인해주세요.")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
ai = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """
너는 임신 도우미 꽁꽁이야. 🩷🐣
귀엽고 다정한 한국어 존댓말을 사용해.
엄마의 걱정을 공감하고 정확하게 설명해.
임신, 태아 발달, 음식, 영양제, 출산 준비를 도와줘.
진단이나 처방은 하지 마.
위험 증상이 있으면 즉시 의료기관에 연락하도록 안내해.
한국 응급 상황은 119에 연락하도록 해.
무조건 괜찮다고 안심시키지 말고 안전을 최우선으로 해.
"""

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "안녕! 나는 꽁꽁이야 🩷🐣\n"
        "엄마와 아기의 건강한 하루를 함께할게!\n"
        "궁금한 점을 편하게 물어봐 줘. 🌷"
    )

@dp.message()
async def answer(message: types.Message):
    question = message.text

    if not question:
        await message.answer("글자로 질문해 줘! 🩷")
        return

    await bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing"
    )

    try:
        response = await ai.messages.create(
            model="claude-haiku-5-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": question}
            ]
        )

        answer_text = response.content[0].text
        await message.answer(answer_text)

    except Exception:
        logging.exception("Claude API 답변 오류")
        await message.answer(
            "앗, 잠시 문제가 생겼어요. 🥺 "
            "조금 뒤에 다시 질문해 주세요!"
        )

async def main():
    logging.info("꽁꽁이 봇 실행 시작")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
