import re
from flask import Flask, request, jsonify
from RAG import generate_answer_with_rag, generate_answer_with_llm
from QR import query_rewrite, yoyak
from personal import *
import threading
import time
import json
import requests

app = Flask(__name__)


doc_links = {
    "(LH)화성동탄2 10년 분양전환공공임대주택(리츠) 예비입주자모집공고('25.03)": "https://drive.google.com/file/d/1XxPHrqkEUr314legVOFCwe2G1w8Lkqe7/view?usp=sharing",
    "(LH)청년신혼부부매입임대리츠-2502-경기북부": "https://drive.google.com/file/d/19fi78YxpdHt-fHy0nwykPWzWAlTuHP3B/view?usp=sharing",
    "(LH)청년신혼부부매입임대리츠-2502-경기남부": "https://drive.google.com/file/d/1Jc-BLthfJ1qyxMt3S5JA6a8ck8T3spxw/view?usp=sharing",
    "(LH)김포한강 Ac-05블록 10년 공공임대주택(리츠) 예비입주자 모집 공고": "https://drive.google.com/file/d/1Kd9tCOPDWDa-Sdfc8-7IgkubHpMMUGwk/view?usp=sharing",
    "(LH)군포시 영구임대주택 예비입주자 모집": "https://drive.google.com/file/d/1GHKyOBfRv5JhezXcLTG0xyi5xmg_PS2L/view?usp=sharing",
    "(LH)관악봉천 H-1ㆍ2ㆍ3BL 행복주택 입주자격완화 추가모집": "https://drive.google.com/file/d/1zvlff3xFf_ZHUpCS2rhyalPCPeZhQMAd/view?usp=sharing",
    "(LH)2025년 청년 전세임대 1순위 입주자 수시모집": "https://drive.google.com/file/d/1rxmq1L7vDMV9lSYsKxZpFkvQeUCiDezP/view?usp=sharing",
    "(LH)[정정공고]전북 남부권 지역 국민임대주택 예비입주자 모집": "https://drive.google.com/file/d/1F4IwYQJHIT3cOAQQNlB9rZG4Va9LsTVE/view?usp=sharing",
    "(LH)[정정공고]구리갈매 이스트힐 10년 공공임대주택 예비입주자 모집 공고": "https://drive.google.com/file/d/1aQR9pFFPJ3e5Zwk94NDQBegtpoDyeSKE/view?usp=sharing",
    "(LH)[정정공고][서울지역본부] 기존주택 등 매입임대주택 예비입주자 모집공고": "https://drive.google.com/file/d/1TmXmTNIjC_dnzHPEfoL6Ai4TV6doRVbY/view?usp=sharing",
    "(LH)[정정공고][서울지역본부] 고령자 매입임대주택 예비입주자 모집공고": "https://drive.google.com/file/d/1cUJSi36rMt2S0b7KWP5fAq9Q5ZRsfxDU/view?usp=sharing",
    "(LH)[정정공고][경기남부] 25년 1차 청년 매입임대주택 예비입주자 모집공고": "https://drive.google.com/file/d/1Gd5WmTx8Yve5deDm2CyoDyQK-9XZvxBl/view?usp=sharing",
    "(LH)[서울지역본부] 25년 1차 청년 매입임대주택 예비입주자 모집공고": "https://drive.google.com/file/d/1NbKhqstJ2SQ0bSJzAeY-tjFVkTTe0Lf2/view?usp=sharing",
    "(LH)[경기북부] 25년 1차 청년매입임대 예비입주자 모집공고": "https://drive.google.com/file/d/1qMRIMOd51hNJSnWjPJuf1svpII6PaRSd/view?usp=sharing",
    "(LH)(인천) 청년.신혼부부 매입임대리츠주택 입주자 모집공고": "https://drive.google.com/file/d/1v4e6stxAC9E9bO5C6tZpaaMDb98nzggG/view?usp=sharing",
    "(GH)[주택] 25년 1차 청년매입임대주택 예비입주자 모집공고": "https://drive.google.com/file/d/1A-h0NMaAF3oEt0QrNr6FhamA8EJbQOWc/view?usp=sharing",
    "(GH)[주택] 25년 1차 기존주택 등 매입임대주택 예비입주자 모집공고(경기도 27개 시군)": "https://drive.google.com/file/d/1nrEyfpDpA7iehmhkd-KzafdEZTQVWg2N/view?usp=sharing"

}





# 사용자별 source_filter 저장
user_file_choices = {}
user_inputs = {}
# 사용자별 최근 answer 저장
user_answers = {}

@app.route("/kakao-webhook", methods=["POST"])
def kakao_webhook():
    req = request.get_json()
    user_input = req['userRequest']['utterance']
    user_id = req['userRequest']['user']['id']
    callback_url = req['userRequest'].get('callbackUrl')
    source_filter = req.get("action", {}).get("clientExtra", {}).get("source_filter")
    
    age = req.get("action", {}).get("clientExtra", {}).get("age")
    marriage = req.get("action", {}).get("clientExtra", {}).get("marriage")
    job = req.get("action", {}).get("clientExtra", {}).get("job")
    
    print("\n📥 질문 수신:", user_input)
    print("🔁 callback_url:", callback_url)
    print("🔑 source_filter:", source_filter)


    # ✅ 나이 블록 처리
    if age:
        user_inputs.setdefault(user_id, {})['age'] = age
        print(f"✅ age 저장: {user_id} → {age}")

        if callback_url:
            threading.Thread(
                target=process_answer_and_callback,
                args=(user_input, callback_url, 'age', age, user_id)
            ).start()

        return jsonify({
        "version": "2.0",
        "useCallback": True,
        "data": { "text": "" }
    })

    # ✅ 결혼 블록 처리
    if marriage:
        user_inputs.setdefault(user_id, {})['marriage'] = marriage
        print(f"✅ marriage 저장: {user_id} → {marriage}")

        if callback_url:
            threading.Thread(
                target=process_answer_and_callback,
                args=(user_input, callback_url, 'marriage', marriage, user_id)
            ).start()

        return jsonify({
        "version": "2.0",
        "useCallback": True,
        "data": { "text": "" }
    })
        
    if job:
        user_inputs.setdefault(user_id, {})['job'] = job
        print(f"✅ job 저장: {user_id} → {job}")

        if callback_url:
            threading.Thread(
                target=process_answer_and_callback,
                args=(user_input, callback_url, 'job', job, user_id)
            ).start()

        return jsonify({
        "version": "2.0",
        "useCallback": True,
        "data": { "text": "" }
    })    
    user_data = user_inputs.get(user_id, {})
    age_val = user_data.get("age")
    marriage_val = user_data.get("marriage")
    job_val = user_data.get("job")
    print(f"[📦 누적 저장값] user_inputs[{user_id}] = {user_inputs.get(user_id)}")
    print(f"[✅ 최종 처리용] age_val = {age_val}, marriage_val = {marriage_val}, job_val = {job_val}")
    
    if age_val and marriage_val and job_val and user_input == '결과 확인하기':
        threading.Thread(
        target=generate_final_result_and_callback,args=(user_id, user_input, callback_url)).start()

        return jsonify({
            "version": "2.0",
            "useCallback": True,
            "data": { "text": "" }
        })
    
    # ✅ 1) 선택완료 블록에서 들어온 요청: source_filter 저장만
    if source_filter:
        user_file_choices[user_id] = source_filter
        print(f"✅ source_filter 저장됨: {user_id} → {source_filter}")
        return jsonify({ "status": "ok" })  # 카카오에서 봇 응답 따로 지정했으니 최소 응답만

    # ✅ 2) '요약하기' 요청인 경우
    if user_input.strip() == "요약하기":
        prev_answer = user_answers.get(user_id, {}).get("general")
        if not prev_answer:
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": "⚠️ 요약할 응답이 없습니다. 먼저 질문을 해주세요."}}]
                }
            })
        
        summarized = yoyak(prev_answer)
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": summarized}}]
            }
        })

    # ✅ 3) 일반 질문 처리 (폴백 블록)
    chosen_file = user_file_choices.get(user_id)
    if not chosen_file:
        print("⚠️ 선택된 파일 없음 → 전체 데이터 또는 기본 응답으로 처리합니다.")
        chosen_file = None  # 전체 소스로 RAG 처리하거나 기본 설정으로

    user_input = query_rewrite(user_input)

    if callback_url:
        threading.Thread(target=process_request, args=(user_input, callback_url, chosen_file, user_id)).start()
        return jsonify({
            "version": "2.0",
            "useCallback": True,
            "data": { "text": "" }
        })
    else:
        if chosen_file:
            answer = generate_answer_with_rag(user_input, source_filter=chosen_file)
        else:
            answer = generate_answer_with_llm(user_input)
        if not isinstance(user_answers.get(user_id), dict):
            user_answers[user_id] = {}
        user_answers[user_id]["general"] = answer

        # 여기서 answer가 JSON 문자열(구조화된 답변)라고 가정
        try:
            answer_json = json.loads(answer)
            sections = answer_json.get("sections", [])
        except json.JSONDecodeError:
            # JSON 파싱 실패시 fallback: 전체 답변을 하나의 섹션으로 처리
            sections = [{"title": "답변", "content": answer}]

        # 각 섹션을 BasicCard 형식 아이템으로 변환
        items = []
        for sec in sections:
            items.append({
                "title": sec.get("title", ""),
                "description": sec.get("content", "")
            })

        # 최종 카카오톡 Carousel 응답 JSON 구성
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "carousel": {
                            "type": "basicCard",
                            "items": items
                        }
                    }
                ],
                "quickReplies": [
                    {
                        "label": "요약하기",
                        "action": "message",
                        "messageText": "요약하기"
                    }
                ]
            }
        })
def process_answer_and_callback(user_input, callback_url, field_name, field_value, user_id):
    print(f"⏱ 백그라운드 처리 시작: {field_name} = {field_value}")
    if field_name == 'age':
        field_value = f'{field_value}살 공고 추천'
    elif field_name == 'marriage':
        field_value = f'결혼 여부 : {field_value} 공고 추천'
    elif field_name == 'job':
        field_value = f' 현재 신분 : {field_value} 공고 추천'
    
        
    answer = personal_generate_answer_with_rag(field_value,source_filter=None)
    user_answers.setdefault(user_id, {})[field_name] = answer
    print(f"✅ RAG 응답 저장: {user_id} → {field_name}: {answer}")

    response_body = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": f"✅ 조건에 맞는 공공주택 정보를 찾았어요!"
                    }
                }
            ],
            "quickReplies": []
        }
    }

    if field_name == "age":
        response_body["template"]["quickReplies"].append({
            "label": "결혼 정보 입력하기",
            "action": "block",
            "blockId": "67fcf8d2ee0d3d20803848f8"  # messageText 제거
        })
    elif field_name == "marriage":
        response_body["template"]["quickReplies"].append({
            "label": "직업 여부 입력하기",
            "action": "block",
            "blockId": "67fd1e80379f2578c3b83f2d"  # messageText 제거
        })
    elif field_name == "job":
        response_body["template"]["quickReplies"].append({
            "label": "결과 확인하기",
            "action": "message",
            "blockId": "67fdb6c104044e3457a1fa07"  # messageText 제거
        })

    # 디버깅용 출력 추가
    print("📤 [DEBUG] 최종 응답 JSON ↓↓↓")
    print(json.dumps(response_body, ensure_ascii=False, indent=2))

    try:
        resp = requests.post(callback_url, headers={"Content-Type": "application/json"}, json=response_body)
        print(f"📤 Callback 전송 완료 → {field_name}, 상태 코드: {resp.status_code}")
        print("📥 카카오 응답 내용:", resp.text)
    except Exception as e:
        print(f"❌ Callback 실패: {e}")



def generate_final_result_and_callback(user_id, user_input, callback_url):
    age_val = user_inputs.get(user_id, {}).get("age")
    marriage_val = user_inputs.get(user_id, {}).get("marriage")
    job_val = user_inputs.get(user_id, {}).get("job")

    if not (age_val and marriage_val and job_val):
        return

    print(f"🧠 최종 응답 생성 시작: age={age_val}, marriage={marriage_val}")
    condition = f'나이 : {age_val}, 결혼여부 : {marriage_val}, 직업 : {job_val}'

    final = (
        user_answers[user_id].get('age', '') + '\n' +
        user_answers[user_id].get('marriage', '') + '\n' +
        user_answers[user_id].get('job', '')
    )
    final_result = final_gpt(final, condition)
    user_answers.setdefault(user_id, {})['final'] = final_result

    cards = []
    for i, part in enumerate(final_result.split("&")):
        title = f"{i + 1}위 추천 공고"
        content = part.strip()
        print('💩content',content)
        # 🔍 공고문 이름 추출
        match = re.search(r"\[(.*)\]", content)
        name_raw = match.group(1).strip() if match else None
        print('🖥️match',match)
        print('🖥️name_raw',name_raw)
        matched_url = None
        for key in doc_links:
            print('🤔key',key)
            print('🤔match',match)
            if key == name_raw:
                print('-'*20)
                print(key)
                print(match)
                print(name_raw)
                print('-'*20)
                matched_url = doc_links[key]
                print('♥️zz',matched_url)
                break
        if matched_url:
            content += f"\n📎 관련 링크: {matched_url}"
        # 📦 카드 구성
        card = {
            "title": title,
            "description": content,
            "buttons": [
                {
                    "action": "block",
                    "label": "공고 검색",
                    "blockId": "67f7c16ed608767625119a61",  
                    "extra": {
                        "source_filter": name_raw
                    }
                }
            ]
        }

        cards.append(card)



    # 최종 응답 (carousel 형태)
    response_body = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "carousel": {
                        "type": "basicCard",
                        "items": cards
                    }
                }
            ],
            "quickReplies": [
                {
                    "label": "정보 다시 입력하기",
                    "action": "block",
                    "blockId": "67fcf6b9379f2578c3b838b6"
                },
                {
                    "label": "메뉴로 돌아가기",
                    "action": "block",
                    "blockId": "67fb9b2c202e764481ad480e"
                }
            ]
        }
    }



    try:
        print("📤 [DEBUG] 최종 결과 콜백 전송 ↓↓↓")
        print(json.dumps(response_body, ensure_ascii=False, indent=2))

        resp = requests.post(callback_url, headers={"Content-Type": "application/json"}, json=response_body)
        print(f"📤 Callback 전송 완료 → 결과 확인, 상태 코드: {resp.status_code}")
        print("📥 카카오 응답 내용:", resp.text)

    except Exception as e:
        print(f"❌ Callback 실패: {e}")


def process_request(user_input, callback_url, source_filter, user_id):
    print("⏱ 백그라운드에서 LLM 처리 시작")
    start = time.time()

    if source_filter:
        answer = generate_answer_with_rag(user_input, source_filter)
    else:
        answer = generate_answer_with_llm(user_input)
    
    if not isinstance(user_answers.get(user_id), dict):
        user_answers[user_id] = {}
    user_answers[user_id]["general"] = answer
    
    elapsed = time.time() - start
    print(f"✅ 응답 완료 (처리 시간: {elapsed:.2f}초)")

    try:
        answer_json = json.loads(answer)
        sections = answer_json.get("sections", [])
    except json.JSONDecodeError:
        sections = [{"title": "답변", "content": answer}]
    
    items = []
    for sec in sections:
        items.append({
            "title": sec.get("title", ""),
            "description": sec.get("content", "")
        })
    
    response_body = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "carousel": {
                        "type": "basicCard",
                        "items": items
                    }
                }
            ],
            "quickReplies": [
                {
                    "label": "요약하기",
                    "action": "message",
                    "messageText": "요약하기"
                }
            ]
        }
    }
    
    headers = { "Content-Type": "application/json" }
    try:
        resp = requests.post(callback_url, headers=headers, json=response_body)
        print("📤 Callback 응답 전송, 상태 코드:", resp.status_code)
    except Exception as e:
        print("❌ Callback 전송 실패:", e)

if __name__ == "__main__":
    print("✅ Flask 서버 실행 중 (port 5000)...")
    app.run(port=5000)
