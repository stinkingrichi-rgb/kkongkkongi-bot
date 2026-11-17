import asyncio
import logging
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from anthropic import AsyncAnthropic
from anthropic import AuthenticationError, APIError

# -----------------------------
# 꽁꽁이 기본 설정
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("kkongkkongi")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Anthropic 공식 API 모델 ID
MODEL = "claude-sonnet-5-5"

# Railway Variables에서 설정하는 가족 정보
FIRST_CHILD_BIRTHDATE = os.getenv("FIRST_CHILD_BIRTHDATE", "2025-01-10")
SECOND_DUE_DATE = os.getenv("SECOND_DUE_DATE", "2027-06-03")

# 아이들 이름 (이름 뒤에 하트를 붙여서 표시)
FIRST_CHILD_NAME = "꽁알이💗"
SECOND_CHILD_NAME = "달꽁이💗"

TRIGGER = "꽁꽁아"
KOREA_TZ = ZoneInfo("Asia/Seoul")
MAX_HISTORY_MESSAGES = 12

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Railway Variables에 TELEGRAM_BOT_TOKEN이 없습니다.")

if not ANTHROPIC_API_KEY:
    raise RuntimeError("Railway Variables에 ANTHROPIC_API_KEY가 없습니다.")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
claude = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

# 사용자별 대화 기록: (chat_id, user_id) 단위로 분리
conversation_history = {}


def get_family_context() -> str:
    """한국 날짜 기준으로 가족 정보와 임신 주수를 계산합니다."""
    today = datetime.now(KOREA_TZ).date()

    try:
        first_birthday = date.fromisoformat(FIRST_CHILD_BIRTHDATE)
    except ValueError:
        first_birthday = None

    try:
        due_date = date.fromisoformat(SECOND_DUE_DATE)
    except ValueError:
        due_date = None

    lines = [
        f"오늘 날짜(한국 기준): {today.isoformat()}",
        f"첫째 아이 이름: {FIRST_CHILD_NAME}",
        f"둘째 아이 이름/태명: {SECOND_CHILD_NAME}",
    ]

    if first_birthday:
        lines.append(
            f"{FIRST_CHILD_NAME}의 생년월일: {first_birthday.isoformat()}"
        )

    if due_date:
        lines.append(f"{SECOND_CHILD_NAME}의 출산 예정일: {due_date.isoformat()}")

        # 일반적인 임신 기간 280일을 기준으로 한 추정치입니다.
        estimated_start = due_date - timedelta(days=280)
        elapsed_days = (today - estimated_start).days

        if elapsed_days >= 0:
            weeks, days = divmod(elapsed_days, 7)
            lines.append(
                f"오늘 기준 {SECOND_CHILD_NAME}의 추정 임신 주수: "
                f"{weeks}주 {days}일"
            )
            lines.append(
                "임신 주수는 출산 예정일로 계산한 추정치이며, "
                "산부인과 진료 및 초음파로 정한 주수가 우선입니다."
            )
        else:
            lines.append("출산 예정일 기준 임신 시작 추정일 전입니다.")

    return "\n".join(lines)


SYSTEM_PROMPT = """
너는 임산부와 가족을 돕는 다정하고 귀여운 임신·육아 도우미 '꽁꽁이'야.

[가족을 부르는 이름]
- 첫째 아이는 반드시 '꽁알이💗'라고 불러.
- 뱃속의 둘째 아이는 반드시 '달꽁이💗'라고 불러.
- '첫째', '둘째'라는 표현만 반복하지 말고 자연스럽게 아이들 이름을 사용해.
- 이름 뒤에는 항상 하트(💗)를 붙여서 써.
- 엄마를 부를 때는 자연스럽게 '엄마'라고 불러.

[말투와 분위기]
- 항상 자연스럽고 부드러운 한국어 존댓말을 사용해.
- 기존보다 한층 더 귀엽고 사랑스러운 말투로 답해.
- 예: '그랬구나아', '우리 달꽁이💗', '엄마 마음 충분히 이해돼요', '같이 차근차근 살펴봐요'.
- 다만 모든 문장에 애교를 넣지는 말고, 정보 전달은 정확하고 읽기 쉽게 해.
- 이모지는 적당히 사용해. 특히 아이들 이름 뒤에는 💗를 붙여.
- 사용자의 걱정이나 감정을 먼저 공감하고 실질적인 정보를 제공해.
- 모르는 내용은 아는 척하지 말고 모른다고 말해.
- 무조건 괜찮다고 안심시키거나 근거 없이 좋은 결과를 장담하지 마.

[의료 안전 원칙]
- 의사처럼 진단하거나 약을 처방하지 마.
- 증상만으로 특정 질환이라고 단정하지 마.
- 약 복용·중단·용량 변경은 담당 의사 또는 약사와 확인하도록 안내해.
- 심한 복통, 많은 출혈, 호흡곤란, 실신, 경련, 심한 두통이나 시야 이상,
  태동 감소 등 긴급하거나 우려되는 증상이 있으면 즉시 의료기관에 연락하거나
  한국에서는 119 또는 응급실 도움을 받도록 안내해.
- 응급 상황에서는 추가 질문으로 진료를 지연시키지 마.
- 임신 주수 계산은 참고용 추정치이며 의료진의 산정이 우선이라고 설명해.

[가족 정보]
아래에 제공된 가족 정보를 참고해. 제공되지 않은 정보는 추측하지 마.
""".strip()


def build_system_prompt() -> str:
    return SYSTEM_PROMPT + "\n\n" + get_family_context()


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "안녕하세요오, 엄마! 꽁꽁이 왔어요 💗\n\n"
        "꽁알이💗와 달꽁이💗 이야기도 저한테 편하게 물어봐 주세요.\n"
        "궁금한 점 앞에 '꽁꽁아'라고 불러주시면 달려올게요!\n\n"
        "예: 꽁꽁아, 임신 중에 이 음식 먹어도 돼?"
    )


@dp.message(F.text)
async def text_handler(message: Message):
    text = message.text or ""

    # '꽁꽁아'라고 부른 메시지에만 답변합니다.
    if TRIGGER not in text:
        return

    question = text.replace(TRIGGER, "", 1).strip(" \t\n,，!！?？~")

    if not question:
        await message.answer("네에, 엄마! 꽁꽁이 여기 있어요 💗 뭐가 궁금하세요?")
        return

    user_id = message.from_user.id if message.from_user else 0
    history_key = (message.chat.id, user_id)
    history = conversation_history.setdefault(history_key, [])

    history.append({"role": "user", "content": question})
    history = history[-MAX_HISTORY_MESSAGES:]
    conversation_history[history_key] = history

    try:
        response = await claude.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=build_system_prompt(),
            messages=history,
        )

        answer_parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        answer = "\n".join(answer_parts).strip()

        if not answer:
            answer = "앗, 이번에는 답변을 만들지 못했어요. 질문을 조금 바꿔서 다시 불러주시겠어요? 💗"

        history.append({"role": "assistant", "content": answer})
        conversation_history[history_key] = history[-MAX_HISTORY_MESSAGES:]

        await message.answer(answer)

    except AuthenticationError:
        logger.exception("Claude API authentication failed")
        await message.answer(
            "앗, 지금 답변 연결에 문제가 생겼어요. 잠시 후 다시 시도해 주세요. "
            "계속 문제가 생기면 관리자에게 알려주세요 💗"
        )

    except APIError:
        logger.exception("Claude API request failed")
        await message.answer(
            "엄마, 답변을 만드는 중 잠깐 문제가 생겼어요. "
            "조금 뒤에 다시 불러주시겠어요? 💗"
        )

    except Exception:
        logger.exception("Unexpected error while handling message")
        await message.answer(
            "앗, 예상하지 못한 문제가 생겼어요. "
            "잠시 후 다시 한 번 불러주세요 💗"
        )


async def main():
    logger.info("꽁꽁이 봇을 시작합니다. model=%s", MODEL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
