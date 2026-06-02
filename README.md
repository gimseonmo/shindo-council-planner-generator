# 행사 기획서 생성기

학교 행사 이름과 소개를 입력하면 Gemini API로 행사 기획서를 작성해주는 Python 웹앱입니다.
양식은 제공된 예시를 따라 `활동 명칭`, `활동 목적`, `필요 예산`, `활동 계획`, `기대 효과`를 작성합니다.
`활동 기간`은 제외하고, `필요 예산`은 제목만 남깁니다.

## API 키 설정

[app.py](./app.py)의 `GEMINI_API_KEYS`에 Gemini API 키 3개를 넣어주세요.

```python
GEMINI_API_KEYS = [
    "첫 번째 키",
    "두 번째 키",
    "세 번째 키",
]
```

첫 번째 키가 사용량 초과나 오류로 실패하면 다음 키로 자동 재시도합니다.
환경 변수 `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3`로 넣어도 동작합니다.

Vercel에 배포할 때는 API 키를 코드에 넣지 말고 Vercel 환경 변수로 설정하세요.

```text
GEMINI_API_KEY_1=첫 번째 키
GEMINI_API_KEY_2=두 번째 키
GEMINI_API_KEY_3=세 번째 키
```

## 실행

```bash
python3 app.py
```

브라우저에서 아래 주소를 열면 됩니다.

```text
http://127.0.0.1:8000
```

생성 결과는 화면에서 복사하거나 `TXT 저장`, `DOCX 저장` 버튼으로 저장할 수 있습니다.

## Vercel 배포

이 프로젝트는 Vercel 배포용으로 `api/` 서버리스 함수와 `vercel.json`을 포함합니다.

1. 이 폴더를 GitHub 저장소에 올립니다.
2. Vercel에서 `Add New Project`를 누르고 해당 GitHub 저장소를 선택합니다.
3. Project Settings의 Environment Variables에 `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3`를 추가합니다.
4. Deploy를 누릅니다.

Vercel 배포 후 사이트 주소에 접속하면 `/api/generate`, `/api/docx` 함수가 자동으로 사용됩니다.
