# Import necessary libraries
from pydantic import BaseModel
from typing import Optional, List
import requests
from datetime import datetime

import logging
logger = logging.getLogger(__name__)
# Define Pydantic model for the notification request
class PushDTOModel(BaseModel):
    user_id: int
    pet_id: Optional[int] = None
    notifName: Optional[str] = "unknown"
    title: str
    message: Optional[str] = None
    content_id: Optional[int] = None
    examId: Optional[int] = None
    action: Optional[str] = "deeplink"
    link: Optional[str] = None
    digest_words: Optional[str] = "기본 알림"

# The PushDTO class and send function as defined in your initial code
class PushDTO:
    def __init__(self, target, state, gbn, dtype, tn, pet_id=None, contents_id=None, examId=None, cn=None, **kwargs):
        self.target = target
        self.state = state
        self.gbn = gbn
        self.dtype = dtype
        self.pet_id = pet_id
        self.contents_id = contents_id
        self.examId = examId
        self.tn = tn
        self.cn = cn
        self.action = kwargs.get('action', 'deeplink')  # default action
        self.link = kwargs.get('link', '')
        self.digest_words = kwargs.get('digest_words', '')
        self.update_properties()

    def update_properties(self):
        actions = {
            'petRegistration': self.petRegistration,
            'questionnaire': self.questionnaire,
            'questionnaireComplete': self.questionnaireComplete,
            'newArticle': self.newArticle,
            'event': self.event,
            'notice': self.notice,
            'subscription': self.subscription,
            'orderList': self.orderList,
            'intake': self.intake,
            'shippingInfo': self.shippingInfo,
            'paymentInfo': self.paymentInfo,
            'notifications': self.notifications,
            'account': self.account,
            'nutrientReport': self.nutrientReport
        }
        action_method = actions.get(self.gbn, lambda: None)
        action_method()

    def petRegistration(self):
        self.link = self.link if self.link else f"equalhybrid://registration_pet={self.pet_id}"
        self.digest_words = "아이 등록"
        self.tn = "우리 아이에 대해 알려주세요"
        self.cn = "우리 아이 정보를 등록하고 맞춤형 콘텐츠 및 1:1 건강 종합 결과를 확인해 보세요."

    def questionnaire(self):
        self.link = self.link if self.link else f"equalhybrid://navigation?scene=examination&petId={self.pet_id}"
        self.digest_words = "건강스켄"
        self.tn = f"{self.pet_id} 건강 스켄 필요해요."
        self.cn = "건강스켄을 완료하고 우리 아이에 대한 종합 건강 상태를 확인해 보아요."

    def questionnaireComplete(self):
        self.link = self.link if self.link else f"equalhybrid://navigation?scene=examinationResult&examinationId={self.examId}&petId={self.pet_id}"
        self.digest_words = "건강스켄 완료"
        self.tn = f"{self.pet_id} 건강 분석 완료"
        self.cn = "우리 아이의 건강스켄 완료되었으니 건강 상태를 확인해 보아요."

    def newArticle(self):
        self.link = self.link if self.link else f"equalhybrid://navigation?scene=publication&contentId={self.contents_id}"
        self.digest_words = "새로운 건강정보"
        self.tn = "신규 아티클"
        self.cn = "새로운 건강 정보를 확인하세요."
        self.action = "deeplink"

    def event(self):
        self.action = "inAppBrowser"
        self.link = self.link if self.link else ""
        self.digest_words = "이벤트"
        self.tn = "새로운 이벤트"
        self.cn = "참여하고 상품을 받아보세요!"

    def notice(self):
        self.action = "osBrowser"
        self.link = "https://equal.pet/board/notice/Notice"
        self.digest_words = "공지사항"
        self.tn = "새로운 공지사항"
        self.cn = "최신 공지사항을 확인하세요."

    def subscription(self):
        self.link = f"equal-pet://navigation?scene=subscription&subscriptionId="
        self.digest_words = "구독 상세정보"
        self.tn = "구독 정보와 혜택을 확인하세요."

    def orderList(self):
        self.link = "equal-pet://navigation?scene=orderList"
        self.digest_words = "결제 내역"
        self.tn = "결제 내역을 확인하세요."

    def intake(self):
        self.link = "equal-pet://navigation?scene=intake"
        self.digest_words = "복용 체크"
        self.tn = "약 복용을 체크하세요."

    def shippingInfo(self):
        self.link = "equal-pet://navigation?scene=addressList"
        self.digest_words = "배송 정보 관리"
        self.tn = "배송 정보를 관리하세요."

    def paymentInfo(self):
        self.link = "equal-pet://navigation?scene=paymentList"
        self.digest_words = "결제 관리"
        self.tn = "결제 수단과 내역을 관리하세요."

    def notifications(self):
        self.link = "equal-pet://navigation?scene=notificationSetting"
        self.digest_words = "알림 설정"
        self.tn = "알림 설정을 조정하세요."

    def account(self):
        self.link = "equal-pet://navigation?scene=accountSetting"
        self.digest_words = "계정 관리"
        self.tn = "계정 설정을 관리하세요."

    def nutrientReport(self):
        self.link = "equal-pet://navigation?scene=producList"
        self.digest_words = "영양제 정보 리스트"
        self.tn = "영양제 정보를 확인하세요."

    def unknown(self):
        """Default action if gbn is not recognized"""

def send(base_push_dto):
    print("Admin login:")
    login_data = {
        "id": "000878.e26f2d8ee29348e9a9204486277240b7.0715",
        "type": "APPLE"
    }
    login_url = 'http://dev.promptinsight.ai:10002/user-service/v1/auth/social'
    login_response = requests.post(login_url, json=login_data)
    login_response_data = login_response.json()
    access_token = login_response_data.get('data', {}).get('accessToken')
    admin_id = login_response_data.get('data', {}).get('id')
    print(f"access_token: {access_token}")
    print(f"admin_id: {admin_id}")
    base_push_dto.update({
        'insert_date': datetime.now().isoformat(),
        'update_date': datetime.now().isoformat(),
        'insert_user': admin_id,
        "state": 1,
        'dtype': 'FCM'
    })

    # Reverse mapping before creating PushDTO instance
    base_push_dto = {
        'target': base_push_dto.pop('user_id'),
        'gbn': base_push_dto.pop('notifName'),
        'tn': base_push_dto.pop('title'),
        'cn': base_push_dto.pop('message'),
        'contents_id': base_push_dto.pop('content_id'),
        **base_push_dto
    }

    push_dto = PushDTO(**base_push_dto)

    push_url = 'http://dev.promptinsight.ai:10002/push-service/v1/admin/push'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    logger.info(f"Sending push notification: {vars(push_dto)}")
    push_response = requests.post(push_url, headers=headers, json=vars(push_dto))
    return push_response.json()
    
