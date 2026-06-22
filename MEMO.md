# 1. 파이썬 가상환경 활성화
cd /Users/sewon/Projects/aim
source venv/bin/activate

# 2. 전처리 실행
python -m src.kakao_collector.main

# 3. md파일 생성 실행
python -m src.kakao_collector.journal_generator