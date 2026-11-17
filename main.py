
import os
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from anthropic import AsyncAnthropic

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not TELEGRAM_TOKEN or not ANTHROPIC_API_KEY:
    raise RuntimeError("환경변수를 확인해주세요.")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
ai = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """
너는 임신 도우미 꽁꽁이야. 🩷🐣

- 귀엽고 다정한 한국어 존댓말을 사용해.
- 적당한 이모지를 사용해.
- 엄마의 걱정을 공감하고 차분하게 설명해.
- 임신 주차별 태아 발달, 음식, 영양제,
  임신 증상, 생활 습관, 출산 준비를 도와줘.
- 의학적으로 신뢰할 수 있는 근거를 우선해.
- 진단이나 처방을 하지 마.
- 불확실한 내용은 불확실하다고 알려줘.
- 임신 주차를 모르면 먼저 물어봐.
- 무조건 괜찮다고 안심시키지 마.
- 심한 복통, 많은 질출혈, 호흡곤란,
  실신 등 위험 증상은 즉시 의료기관에
  연락하도록 안내해.
- 한국 응급 상황은 119에 연락하도록 해.
- 엄마와 아기의 안전을 최우선으로 해.
"""

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "안녕! 나는 꽁꽁이야 🩷🐣\n\n"
        "엄마와 아기의 건강한 하루를 함께할게!\n"
        "궁금한 점을 편하게 물어봐 줘. 🌷"
    )

@dp.message()
async def answer(message: types.Message):
    question = message.text

    if not question:
        await message.answer("글자로 질문해 줘! 🩷")
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing"
    )

    try:
        response = await ai.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": question}
            ]
        )

        answer_text = response.content[0].text
        await message.answer(answer_text)

    except Exception:
        await message.answer(
            "앗, 잠시 문제가 생겼어요. 🥺\n"
            "조금 뒤에 다시 질문해 주세요!"
        )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
