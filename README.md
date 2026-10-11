# SEED-ECB Python 도구

Python 3.10 이상에서 pip 설치 없이 쓸 수 있는 SEED-128 ECB 암복호화 프로그램입니다. [포터블 ZIP을 다운로드](https://raw.githubusercontent.com/bw-kim/seed/main/downloads/SEED_ECB_Python_portable.zip)해 압축을 풀고 실행하세요. Python 파일 하나만 필요하면 [SEED_ECB_portable.py](https://raw.githubusercontent.com/bw-kim/seed/main/SEED_ECB_portable.py)를 받으면 됩니다.

```sh
python SEED_ECB_portable.py
```

Windows에서는 `시작_SEED_ECB.bat`를 더블클릭해도 됩니다. 화면에는 암호화/복호화 방식 선택, 키 입력, 본문 입력, 결과만 표시됩니다. 키는 **16바이트**이며 기본 키 형식은 UTF-8입니다. 본문 길이는 16바이트에 제한되지 않습니다. 키 형식과 패딩은 기존 시스템에 맞춰 선택할 수 있습니다.

암호화 구현과 화면은 포터블 Python 파일 하나에 포함되어 있습니다. 외부 라이브러리를 설치할 필요가 없습니다. 텍스트 처리는 메모리를 사용하며, 순수 Python이라 입력이 매우 크면 처리가 느릴 수 있습니다.

기술 세부 설정, 소스 구성, 검증 방법은 [사용 안내](SEED_ECB_사용안내.txt)를 참고하세요.
