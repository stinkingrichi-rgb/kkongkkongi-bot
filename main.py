import os
import asyncio
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from anthropic import AsyncAnthropic

# Railway Variables에 비밀키와 가족 날짜를 등록하세요.
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
FIRST_CHILD_BIRTHDATE = os.getenv("FIRST_CHILD_BIRTHDATE", "")
SECOND_DUE_DATE = os.getenv("SECOND_DUE_DATE", "")

if not TELEGRAM_TOKEN:
    raise RuntimeError("Railway에 TELEGRAM_BOT_TOKEN 변수가 없습니다.")
if not ANTHROPIC_API_KEY:
    raise RuntimeError("Railway에 ANTHROPIC_API_KEY 변수가 없습니다.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("kkongkkongi")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
ai = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

MODEL = "claude-haiku-5-5"
MAX_HISTORY_MESSAGES = 12
user_histories = {}

def family_context():
    """Calculate pregnancy week using the due date and standard 280-day dating."""
    try:
        if not FIRST_CHILD_BIRTHDATE or not SECOND_DUE_DATE:
            return (
                "가족 날짜 정보가 아직 등록되지 않았습니다. "
                "Railway Variables에 FIRST_CHILD_BIRTHDATE와 SECOND_DUE_DATE를 등록하세요."
            )
        due = date.fromisoformat(SECOND_DUE_DATE)
        first_birthday = date.fromisoformat(FIRST_CHILD_BIRTHDATE)
        today = datetime.now(ZoneInfo("Asia/Seoul")).date()
        days_until_due = (due - today).days
        gestational_days = 280 - days_until_due

        if gestational_days >= 0:
            weeks, days = divmod(gestational_days, 7)
            pregnancy_line = (
                f"둘째 출산 예정일은 {due.isoformat()}이며, "
                f"예정일 기준 계산상 현재 임신 {weeks}주 {days}일입니다."
            )
        else:
            pregnancy_line = (
                f"둘째 출산 예정일은 {due.isoformat()}입니다. "
                "현재 날짜가 예정일보다 이릅니다."
            )

        return (
            f"첫째 아이 생년월일은 {first_birthday.isoformat()}입니다.\n"
            f"{pregnancy_line}\n"
            "임신 주수는 출산 예정일을 기준으로 한 추정치이며, "
            "병원에서 확인한 주수나 초음파에 따른 예정일이 우선입니다."
        )
    except ValueError:
        logger.exception("가족 날짜 환경변수 형식 오류")
        return "가족 날짜 정보가 올바른 YYYY-MM-DD 형식인지 확인해야 합니다."

SYSTEM_PROMPT = f"""
너는 임신 도우미 '꽁꽁이'야. 🩷🐣
항상 자연스러운 한국어 존댓말로, 귀엽고 다정하게 답해.
사용자의 걱정을 공감하되 무조건 괜찮다고 단정하지 마.
답변은 이해하기 쉽게 핵심부터 설명하고, 필요하면 추가 질문을 해.

가족 정보(대화 개인화에만 사용):
{family_context()}

전문 분야:
- 임신 주차별 태아 발달, 임신 중 증상과 생활 습관
- 음식, 영양, 영양제에 관한 일반 정보
- 첫째 아이와 둘째 임신을 함께 돌보는 일상 조언
- 출산 준비와 산후조리

안전 원칙:
- 의학적 진단이나 처방을 하지 마.
- 개인의 병력, 검사 결과, 복용약에 따라 달라질 수 있음을 알려.
- 불확실하면 불확실하다고 말하고 산부인과 의료진에게 확인하도록 해.
- 심한 복통, 많은 질출혈, 호흡곤란, 실신, 심한 두통이나 시야 이상 등
  위험 신호가 있으면 챗봇 답변을 기다리지 말고 즉시 의료기관에 연락하도록 해.
- 한국에서 응급 상황이면 119에 연락하도록 안내해.
- 엄마와 아기의 안전을 최우선으로 해.
"""

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "안녕! 나는 꽁꽁이야 🩷🐣\\n"
        "엄마와 첫째, 뱃속 아기의 하루를 함께할게!\\n"
        "임신이나 육아에 관해 편하게 물어봐 줘. 🌷"
    )

@dp.message()
async def answer(message: types.Message):
    question = message.text
    if not question:
        return

    # "꽁꽁아"라고 부른 메시지에만 답합니다.
    # 호출 문구는 Claude에 전달하지 않습니다.
    if "꽁꽁아" not in question:
        return

    question = question.replace("꽁꽁아", "", 1).strip()
    if not question:
        await message.answer("네, 엄마! 무엇이 궁금하세요? 🩷")
        return

    # 그룹에서는 사용자별로 대화 기록을 분리합니다.
    history_key = f"{message.chat.id}:{message.from_user.id if message.from_user else 'unknown'}"
    history = user_histories.setdefault(history_key, [])

    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        response = await ai.messages.create(
            model=MODEL,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=history + [{"role": "user", "content": question}]
        )

        answer_text = "".join(
            block.text for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()

        if not answer_text:
            answer_text = "답변을 만들지 못했어요. 질문을 조금 바꿔서 다시 보내주세요. 🩷"

        history.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer_text}
        ])
        user_histories[history_key] = history[-MAX_HISTORY_MESSAGES:]

        # Telegram 메시지 길이 제한에 대비해 나눠 보냅니다.
        for start_index in range(0, len(answer_text), 4000):
            await message.answer(answer_text[start_index:start_index + 4000])

    except Exception:
        logger.exception("메시지 처리 중 오류 발생")
        await message.answer(
            "앗, 답변을 만드는 중 문제가 생겼어요. 🥺 "
            "잠시 후 다시 시도해 주세요. 문제가 계속되면 관리자에게 알려주세요."
        )

async def main():
    logger.info("꽁꽁이 봇 시작: polling 준비")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
