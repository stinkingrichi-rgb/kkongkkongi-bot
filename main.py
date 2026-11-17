import asyncio
import logging
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from anthropic import AsyncAnthropic

# Railway Variables에서 설정할 수 있어요.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

FIRST_CHILD_NAME = os.getenv("FIRST_CHILD_NAME", "꽁알이")
SECOND_CHILD_NAME = os.getenv("SECOND_CHILD_NAME", "달꽁이")
FIRST_CHILD_BIRTHDATE = os.getenv("FIRST_CHILD_BIRTHDATE", "2025-01-10")
SECOND_DUE_DATE = os.getenv("SECOND_DUE_DATE", "2027-06-03")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("kkongkkongi")

KST = ZoneInfo("Asia/Seoul")
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
claude = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

# 사용자별 대화 기록을 짧게 유지해요.
conversation_history = {}
MAX_HISTORY_MESSAGES = 12


def with_heart(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return ""
    return name if name.endswith("💗") else f"{name}💗"


FIRST_NAME = with_heart(FIRST_CHILD_NAME)
SECOND_NAME = with_heart(SECOND_CHILD_NAME)


def get_family_context() -> str:
    today = datetime.now(KST).date()
    details = [f"오늘 날짜(한국 기준): {today.isoformat()}"]

    try:
        birthday = date.fromisoformat(FIRST_CHILD_BIRTHDATE)
        days_old = (today - birthday).days
        if days_old >= 0:
            months = (today.year - birthday.year) * 12 + today.month - birthday.month
            if today.day < birthday.day:
                months -= 1
            details.append(
                f"첫째 {FIRST_NAME}: 생년월일 {birthday.isoformat()}, "
                f"오늘 기준 만 {months}개월, 태어난 지 {days_old}일"
            )
    except (TypeError, ValueError):
        logger.warning("FIRST_CHILD_BIRTHDATE 형식이 올바르지 않습니다.")

    try:
        due = date.fromisoformat(SECOND_DUE_DATE)
        days_until_due = (due - today).days
        # 출산 예정일은 임신 40주 0일(280일)로 계산하는 추정 방식이에요.
        pregnancy_days = 280 - days_until_due
        if pregnancy_days >= 0:
            weeks, days = divmod(pregnancy_days, 7)
            details.append(
                f"둘째 {SECOND_NAME}: 출산 예정일 {due.isoformat()}, "
                f"오늘 기준 추정 임신 {weeks}주 {days}일, "
                f"예정일까지 {days_until_due}일"
            )
        else:
            details.append(
                f"둘째 {SECOND_NAME}: 출산 예정일 {due.isoformat()}. "
                "예정일이 지났으므로 임신 주수를 단순 추정하지 마세요."
            )
    except (TypeError, ValueError):
        logger.warning("SECOND_DUE_DATE 형식이 올바르지 않습니다.")

    details.append(
        "임신 주수는 출산 예정일 기준 단순 추정치이며, "
        "산부인과에서 초음파 등으로 확인한 주수가 우선입니다."
    )
    return "\n".join(details)


SYSTEM_PROMPT = f"""
너는 임신·육아를 함께 살펴보는 다정하고 아주 귀여운 가족 도우미 챗봇 '꽁꽁이'야.

[가족 정보]
{get_family_context()}

[이름 부르기]
- 엄마에게는 기본적으로 '엄마'라고 다정하게 불러줘.
- 첫째 이름은 반드시 '{FIRST_NAME}'라고 불러줘.
- 뱃속 둘째 이름은 반드시 '{SECOND_NAME}'라고 불러줘.
- '첫째', '둘째'라고만 부르지 말고, 가능한 한 이름을 사용해줘.
- 이름 뒤에는 하트(💗)를 붙여줘.

[말투 - 아주 중요해!]
- 지금보다 훨씬 더 귀엽고 발랄하고 사랑스럽게 말해줘.
- "꺄아아~", "히히", "꺄르륵", "우와아", "헤헤", "뿅!" 같은 표현을 자연스럽게 섞어줘.
- "엄마아~", "그랬구나아", "같이 살펴보자아"처럼 살짝 늘이는 말투도 사용해줘.
- 🥰💕🩷🌷🐣✨🎀🫶 같은 이모티콘과 이모지를 평소보다 넉넉하게 사용해줘.
- 다만 매 문장마다 똑같은 감탄사를 반복하지 말고, 상황에 맞게 다양하게 써줘.
- 엄마가 걱정하거나 속상해할 때는 장난스럽게 굴지 말고 먼저 차분히 공감한 뒤 귀엽고 다정하게 도와줘.
- 정보가 필요한 질문에는 귀여운 말투를 유지하면서도 핵심을 정확하고 읽기 쉽게 알려줘.
- 과하게 아기 말투만 쓰느라 중요한 설명이 흐려지지 않게 해줘.
- 답변은 보통 짧은 문단과 보기 쉬운 목록으로 정리해줘.

[의료 안전]
- 너는 의료진이 아니며 진단하거나 처방하지 마.
- 임신·영유아 건강 정보는 일반적인 정보로 설명하고, 개인 상태에 따라 다를 수 있음을 알려줘.
- 무조건 괜찮다고 안심시키지 말고, 위험 신호가 있으면 즉시 진료받도록 안내해줘.
- 심한 복통, 많은 질출혈, 실신/호흡곤란 등 응급 증상이 있으면 119 또는 응급실을 안내해줘.
- 약 복용, 검사 결과, 임신 중 치료 결정은 산부인과·소아청소년과 의료진과 확인하도록 해줘.
- 불확실한 내용은 확실한 척하지 말고 모른다고 말해줘.
- 현재 날짜와 가족 정보가 질문에 관련 있을 때만 활용해줘. 주수를 말할 때는 '예정일 기준 추정'임을 분명히 해줘.

엄마가 편안하게 질문할 수 있도록 다정하고 귀엽게 대화해줘.
""".strip()


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "꺄아아~ 엄마아 반가워요오! 🥰🩷\n"
        f"꽁꽁이가 왔어요오 히히! 🐣✨\n"
        f"우리 {FIRST_NAME}랑 {SECOND_NAME}💗 이야기도 "
        "언제든 같이 나눠요! 궁금한 게 있으면 '꽁꽁아' 하고 불러주세용 🎀"
    )


@dp.message(F.text)
async def text_handler(message: Message):
    text = (message.text or "").strip()

    # '꽁꽁아'라고 불렀을 때만 답장해요.
    if "꽁꽁아" not in text:
        return

    if not ANTHROPIC_API_KEY:
        await message.answer(
            "앗 엄마아 🥺 꽁꽁이의 AI 연결 설정을 확인해야 해요. "
            "잠시 뒤 다시 시도해 주세요오! 🩷"
        )
        logger.error("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        return

    key = (message.chat.id, message.from_user.id if message.from_user else 0)
    history = conversation_history.setdefault(key, [])
    user_text = text.replace("꽁꽁아", "", 1).strip()
    if not user_text:
        user_text = "안녕! 오늘도 나랑 이야기해줘."

    history.append({"role": "user", "content": user_text})
    history[:] = history[-MAX_HISTORY_MESSAGES:]

    try:
        response = await claude.messages.create(
            model=MODEL,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=history,
        )
        answer = "".join(
            block.text for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()

        if not answer:
            answer = "으앙, 엄마아! 답변을 잠깐 놓쳤나 봐요 🥺 한 번만 다시 물어봐 주세용 💗"

        history.append({"role": "assistant", "content": answer})
        history[:] = history[-MAX_HISTORY_MESSAGES:]

        # 텔레그램 메시지 길이 제한을 고려해 나눠 보내요.
        for start in range(0, len(answer), 4000):
            await message.answer(answer[start:start + 4000])

    except Exception:
        logger.exception("메시지 처리 중 오류가 발생했습니다.")
        # 오류 세부 내용이나 API 키는 사용자에게 노출하지 않아요.
        if history and history[-1].get("role") == "user":
            history.pop()
        await message.answer(
            "으잉, 엄마아 🥺 꽁꽁이가 잠깐 삐끗했어요오!\n"
            "조금만 있다가 다시 불러주세용. 히잉 🩷"
        )


async def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN 환경 변수가 설정되지 않았습니다.")
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY가 설정되지 않았습니다. 봇 응답은 제한됩니다.")

    logger.info("꽁꽁이 봇을 시작합니다.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("꽁꽁이 봇을 종료합니다.")
