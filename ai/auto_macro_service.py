import time
import threading
import os
import sys
from collections import deque
from typing import Optional

# ai/sound 폴더를 path에 추가하여 모듈 임포트 가능하게 함
current_dir = os.path.dirname(os.path.abspath(__file__))
sound_dir = os.path.join(current_dir, "sound")
if sound_dir not in sys.path:
    sys.path.append(sound_dir)

# Import dependencies
try:
    from macro_bot import MacroBot
    from zoom_automation import ZoomAutomator
    from stt_core import GhostEars, load_config
    from summarizer import MeetingSummarizer
except ImportError as e:
    print(f"⚠️ [AutoAssistant] 모듈 임포트 경고: {e}")
    # 서버 실행 시점에는 에러가 안 나도록 처리 (실제 실행 시 에러 발생)


class AutoAssistantService:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.config = load_config()
        self.ears = None
        self.bot = None
        self.automator = None
        self.summarizer = None
        
        # State
        self.history = deque(maxlen=10)
        self.sentence_buffer = []
        self.last_received_time = 0.0
        self.MERGE_THRESHOLD = 2.0

        # Lazy init status
        self._initialized = False

    def start(self):
        """서비스를 별도 스레드에서 시작"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("🚀 [AutoAssistant] AI 비서 서비스 스레드 시작")

    def stop(self):
        """서비스 중지 요청"""
        if not self._running:
            return
            
        print("🛑 [AutoAssistant] 서비스 종료 중...")
        self._running = False
        
        # GhostEars의 리스닝 중단
        if self.ears and hasattr(self.ears, 'stopper'):
            try:
                self.ears.stopper(wait_for_stop=False)
            except:
                pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        print("👋 [AutoAssistant] 서비스 종료 완료")

    def _initialize_models(self):
        """무거운 모델 로딩"""
        if self._initialized:
            return True
            
        try:
            print("⏳ [AutoAssistant] 모델 초기화 중... (시간이 걸릴 수 있습니다)")
            self.ears = GhostEars(self.config)
            self.bot = MacroBot()
            self.automator = ZoomAutomator()
            self.summarizer = MeetingSummarizer()
            self._initialized = True
            print("✅ [AutoAssistant] 모델 로딩 완료!")
            return True
        except Exception as e:
            print(f"❌ [AutoAssistant] 모델 로딩 실패: {e}")
            return False

    def _run_loop(self):
        """실제 작업이 돌아가는 메인 루프 (Thread Safe)"""
        if not self._initialize_models():
            self._running = False
            return

        print(f"🎤 마이크 인덱스: {self.ears.device_index}")
        
        if not self.ears.start_listening():
            print("❌ [AutoAssistant] 마이크 리스닝 시작 실패")
            self._running = False
            return

        print("👂 [AutoAssistant] 듣기 시작... (서버 백그라운드)")
        
        self.last_received_time = time.time()
        self.sentence_buffer = []

        try:
            while self._running:
                # GhostEars.process_queue() generator 사용
                # timeout=0.5로 설정되어 있으므로 루프가 너무 빨리 돌지 않음
                # generator가 끝나면(보통 안 끝남) 다시 호출하거나 대기
                
                # process_queue 자체가 무한루프(yield)가 아니라면 while로 감싸야 함
                # stt_core.py를 보면 while True로 되어 있으나 yield 후 continue 함
                # 따라서 이 loop 하나가 계속 돔.
                # 하지만 중간에 외부에서 멈추고 싶으면 loop를 탈출해야 함.
                
                # 직접 process_queue를 호출하는 대신, 
                # 여기서 우리가 직접 queue를 폴링하는 것이 제어권 갖기 좋음.
                # 하지만 GhostEars의 로직(파일 저장, 변환 등)을 재사용하려면 process_queue를 써야 함.
                
                # stt_core.py의 process_queue는 다음과 같이 돔:
                # while True: queue.get(timeout=0.5) ... yield text
                # 즉, 우리가 break를 안 하면 영원히 갇힘.
                
                for text in self.ears.process_queue():
                    if not self._running: 
                        break # 루프 탈출
                        
                    if text:
                        self._handle_text(text)
                    
                    # 약간의 슬립은 process_queue 내부 timeout으로 대체되지만
                    # 안전을 위해 여기서 체크해줌
                
                # 만약 process_queue가 종료되면(그럴리 없지만) 
                if not self._running:
                    break

        except Exception as e:
            print(f"⚠️ [AutoAssistant] 런타임 에러: {e}")
        finally:
            print("💤 [AutoAssistant] 루프 종료")

    def _handle_text(self, text: str):
        """텍스트 처리 및 답변 생성 로직"""
        current_time = time.time()
        
        # 문장 병합 로직
        if current_time - self.last_received_time < self.MERGE_THRESHOLD:
            self.sentence_buffer.append(text)
        else:
            if self.sentence_buffer:
                merged_sentence = " ".join(self.sentence_buffer)
                self.history.append(merged_sentence)
            self.sentence_buffer = [text]
        
        self.last_received_time = current_time
        
        # 로그 저장
        self.ears.save_to_log(text)
        current_processing_text = " ".join(self.sentence_buffer)
        print(f"▶ [STT]: {text}")

        # 트리거 체크
        # 주의: process_queue에서 너무 빈번하게 호출되면 부하가 걸릴 수 있음
        trigger = self.ears.check_trigger(current_processing_text)
        if trigger:
            self._handle_trigger(trigger, current_processing_text)

    def _handle_trigger(self, trigger, current_processing_text):
        trigger_type, matched = trigger
        print(f"🎯 [AutoAssistant] 트리거 감지! ({trigger_type}: {matched})")
        
        # 요약 및 답변 생성
        try:
            full_transcript = self.ears.get_full_transcript()
            current_summary = self.summarizer.summarize(full_transcript)
            
            full_context = list(self.history) + [current_processing_text]
            suggestion = self.bot.get_suggestion(current_processing_text, full_context, current_summary)
            
            if suggestion:
                print(f"💡 [AI 추천]: {suggestion}")
                # 서버 모드에서는 사용자 입력을 기다릴 수 없으므로(input() 불가)
                # 자동화 봇이 있다면 바로 실행하거나, 프론트엔드로 알림을 보내야 함.
                # 현재는 로그만 출력하고 넘어감 (사용자가 복붙해서 쓰도록)
                pass
            else:
                print("⚠️ [AutoAssistant] 답변 생성 실패")
        except Exception as e:
            print(f"⚠️ [AutoAssistant] 답변 생성 중 에러: {e}")

        # 처리 후 버퍼 비우기
        self.history.append(current_processing_text)
        self.sentence_buffer = []

    def get_transcript_state(self):
        """현재 STT 상태 반환 (history + current buffer)"""
        return {
            "history": list(self.history),
            "current": " ".join(self.sentence_buffer) if self.sentence_buffer else ""
        }

# Singleton instance
assistant_service = AutoAssistantService()

if __name__ == "__main__":
    # Test execution
    svc = AutoAssistantService()
    svc.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        svc.stop()