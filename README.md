# seed — Python SEED-ECB 포터블 도구

**Python 3.10 이상만 있으면 pip 설치 없이 실행할 수 있는 SEED-128 ECB 암복호화 도구입니다.** 암호화 구현과 화면을 `.py` 파일 하나에 포함했습니다. 긴 문자열과 파일을 처리하고 키, 입력, 출력의 문자열/Hex/Base64 형식을 선택할 수 있습니다.

## 다운로드와 실행

[포터블 ZIP 다운로드](https://raw.githubusercontent.com/bw-kim/seed/main/downloads/SEED_ECB_Python_portable.zip)를 풀어 실행하세요. [SEED_ECB_portable.py 하나만 다운로드](https://raw.githubusercontent.com/bw-kim/seed/main/SEED_ECB_portable.py)해도 됩니다.

```sh
python SEED_ECB_portable.py
```

Windows에서는 ZIP에 포함된 `시작_SEED_ECB.bat`를 더블클릭해도 됩니다. 화면은 Python 기본 tkinter를 사용합니다. tkinter가 없는 환경에서는 아래 명령줄 방식을 사용할 수 있습니다. 키와 본문은 외부 서버로 전송하지 않습니다.

## 화면 사용

1. 암호화 또는 복호화를 선택합니다.
2. 키 형식을 고르고 키를 입력합니다. 키는 **정확히 16바이트**이며, 영문/숫자 16자 또는 Hex 32자리에 해당합니다. 한글은 UTF-8 바이트 수로 계산합니다.
3. 입력 형식을 선택하고 본문을 붙여넣거나 **입력 파일 선택**을 누릅니다.
4. **암호화하기/복호화하기**를 누릅니다. 파일은 결과 저장 위치를 지정합니다.
5. 텍스트 결과를 복사하거나 저장합니다. **결과를 입력으로**를 누르면 반대 작업으로 전환하고 결과를 입력에 옮깁니다.

**본문은 16자로 제한되지 않습니다.** 파일은 64 KiB씩 읽으므로 메모리에 전부 올리지 않습니다. 텍스트 결과가 길면 화면에는 앞의 20만 자만 표시하며 복사와 저장은 전체 결과를 사용합니다. 텍스트 처리는 메모리를 사용하므로 큰 자료는 파일 선택 방식으로 처리하세요.

파일 결과는 Hex/Base64 문서가 아니라 암호문 또는 복호문의 **원본 바이트**로 저장합니다. 실패하면 임시 결과를 지우고 기존 출력 파일을 유지합니다. 순수 Python 구현이므로 큰 파일은 외부 암호화 라이브러리를 쓰는 프로그램보다 느릴 수 있습니다.

## 기존 암호문과 맞추기

SEED-128 ECB는 IV를 사용하지 않습니다. 다른 시스템에서 만든 암호문을 복호화하려면 키, 패딩, 암호문 표시 형식을 맞추세요.

| 패딩 | 처리 방식 |
| --- | --- |
| PKCS#7 (기본) | 입력을 16바이트 배수로 채우고 복호화 시 패딩을 검사해 제거합니다. |
| 없음 | 평문이 이미 16바이트의 배수인 경우에 사용합니다. |
| 0x00 채우기 | 마지막 블록을 0x00으로 채우고 복호화 시 끝의 0x00을 모두 제거합니다. 원문의 실제 0x00과 구분할 수 없습니다. |

복호화 결과가 UTF-8 문자열이 아니면 결과 형식을 Hex 또는 Base64로 바꾸세요. ECB는 같은 평문 블록이 같은 암호문 블록으로 나타나므로 기존 시스템과의 호환이 필요한 경우에 사용하세요.

## 명령줄

```sh
python SEED_ECB_portable.py --cli encrypt input.bin output.seed
python SEED_ECB_portable.py --cli decrypt output.seed recovered.bin
python SEED_ECB_portable.py --cli decrypt output.seed recovered.bin --key-format hex --padding none
```

키는 명령 인자에 쓰지 않고 실행 후 따로 입력합니다. 기존 결과 파일을 바꾸려면 `--overwrite`를 추가하세요. `--key-format`은 `utf8`, `hex`, `base64`를, `--padding`은 `pkcs7`, `none`, `zero`를 지원합니다.

## 소스와 검증

알고리즘은 [RFC 4269](https://www.rfc-editor.org/rfc/rfc4269.html)의 SEED-128 정의를 따릅니다.

| 파일 | 용도 |
| --- | --- |
| `SEED_ECB_portable.py` | 실행에 필요한 코드가 모두 들어 있는 단일 파일 |
| `seed_ecb_core.py` | SEED 알고리즘, 패딩, 형식 변환, 파일 스트림 처리 |
| `seed_ecb_tool.py` | 화면과 명령줄 도구의 원본 소스 |
| `build_seed_portable.py` | 단일 파일과 배포 ZIP 생성 |
| `check_seed.py` | 표준 예제와 스트림 경계 검증 |

원본 소스를 수정한 뒤 배포 파일을 다시 만드세요.

```sh
python build_seed_portable.py
python -S check_seed.py
```

외부 패키지를 제외한 환경에서 공식 SEED 예제 4개, 패딩 경계, 긴 입력과 분할 읽기, 실패 시 출력 보존, 배포 ZIP의 독립 실행을 확인합니다. Python 외의 설치 항목은 없습니다.
