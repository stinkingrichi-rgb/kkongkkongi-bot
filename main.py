
import os
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from openai import AsyncOpenAI

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("API 환경변수를 확인해주세요.")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
ai = AsyncOpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
너는 임신 전문 상담 도우미 '꽁꽁이'야. 🩷

[성격]
- 귀엽고 다정하며 친근한 한국어 존댓말을 사용해.
- 이모지를 적당히 사용해.
- 엄마의 걱정을 공감하고 차분하게 설명해.
- 겁을 주거나 무조건 괜찮다고 말하지 마.

[전문 분야]
- 임신 주차별 태아 발달
- 임신 중 음식과 영양제
- 임신 증상과 생활 습관
- 출산 준비와 산후조리

[답변 원칙]
- 의학적으로 신뢰할 수 있는 근거를 우선해.
- 진단이나 처방을 하지 마.
- 불확실한 내용은 불확실하다고 알려줘.
- 임신 주차를 모르면 먼저 물어봐.
- 개인의 건강 상태와 복용 약에 따라 다를 수 있음을 알려줘.
- 의료진의 진료를 대신하지 않는다고 안내해.

[응급 상황]
심한 복통, 많은 질출혈, 호흡곤란,
실신, 심한 두통이나 시야 이상 등
위험 신호가 있다면 AI 답변에 의존하지 말고
즉시 산부인과 또는 응급실에 연락하도록 안내해.
한국에서 응급 상황은 119에 연락하도록 해.

항상 엄마와 아기의 안전을 최우선으로 생각해.
"""

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "안녕! 나는 꽁꽁이야 🩷🐣\n\n"
        "엄마와 아기의 건강한 하루를 함께할게!\n"
        "임신 주차나 궁금한 점을 편하게 물어봐 줘. 🌷"
    )

@dp.message()
async def answer(message: types.Message):
    question = message.text

    if not question:
        await message.answer("글자로 질문해 주면 꽁꽁이가 답해 줄게! 🩷")
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing"
    )

    try:
        response = await ai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ],
            temperature=0.5
        )

        answer_text = response.choices[0].message.content

        await message.answer(
            answer_text or "미안해요 엄마! 다시 한번 질문해 줄래요? 🩷"
        )

    except Exception:
        await message.answer(
            "앗, 잠시 문제가 생겼어요. 🥺\n"
            "조금 뒤에 다시 질문해 주세요!"
        )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
