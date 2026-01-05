# ai/macro_bot.py
import os
import sys
from dotenv import load_dotenv

from config_loader import load_config

# stdout utf-8
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

base_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.normpath(os.path.join(base_dir, "..", ".env"))
load_dotenv(dotenv_path=dotenv_path, override=True)


class MacroBot:
    def __init__(self):
        from exaone_loader import ExaoneLoader
        self.loader = ExaoneLoader()
        self.model = self.loader._model

        self.config = load_config()

    def get_suggestion(self, current_text: str, history: list = None):
        if not self.model or not current_text.strip():
            return None

        persona = self.config.get("personalization", {})
        user_role = persona.get("user_role", "회의 참가자")
        topic = persona.get("meeting_topic", "일반 회의")
        style = persona.get("speaking_style", "정중한 구어체")

        recent_history = history[-10:] if history else []
        context_str = "\n".join([f"- {h}" for h in recent_history])

        prompt = f"""
당신은 온라인 비대면 '실시간 강의'를 수강 중인 대학생의 AI 비서입니다.
목표: 교수님의 말에 대해 학생이 직접 채팅한 것 같은 자연스러운 한국어 답변을 '단 한 문장' 제안.

[학생 페르소나]
- 역할: {user_role}
- 과목/주제: {topic}
- 말투: {style}

[지침]
- 15자 이내 단문
- 결과만 출력(설명 금지)

[최근 맥락]
{context_str if context_str else "(방금 시작)"}

[교수 발화]
"{current_text}"

채팅 답변:
""".strip()

        try:
            response_text = self.loader.generate_content(prompt)
            return response_text.strip().replace('"', "").replace("\n", " ")
        except Exception as e:
            print(f"❌ EXAONE Generation Error: {e}")
            return None
