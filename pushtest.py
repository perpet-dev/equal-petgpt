import requests
from datetime import datetime

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
            'home': self.home,
            'search': self.search,
            'subscription': self.subscription,
            'more': self.more,
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

    # Definitions for all types of push notifications
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
        self.digest_words = "문진완료"
        self.tn = f"{self.pet_id} 건강 분석 완료"
        self.cn = "우리 아이의 문진이 완료되었으니 건강 상태를 확인해 보아요."

    def newArticle(self):
        self.link = self.link if self.link else f"equalhybrid://navigation?scene=publication&contentId={self.contents_id}"
        self.digest_words = "새로운 건강정보"
        #self.tn = "신규 아티클"
        self.cn = "새로운 건강 정보를 확인하세요."

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

    def home(self):
        self.link = "equal-pet://navigation?scene=home"
        self.digest_words = "메인화면"
        self.tn = ""
        self.cn = "환영합니다! 어떤 정보를 찾고 계신가요?"

    def search(self):
        self.link = f"equal-pet://navigation?scene=search&keyword="
        self.digest_words = "검색"
        self.tn = ""
        self.cn = "원하는 정보를 검색해 보세요."

    def subscription(self):
        self.link = f"equal-pet://navigation?scene=subscription&subscriptionId="
        self.digest_words = "구독 상세정보"
        self.tn = ""
        self.cn = "구독 정보와 혜택을 확인하세요."

    def more(self):
        self.link = "equal-pet://navigation?scene=more"
        self.digest_words = "더보기"
        self.tn = ""
        self.cn = "더 많은 기능과 정보를 확인할 수 있습니다."

    def orderList(self):
        self.link = "equal-pet://navigation?scene=orderList"
        self.digest_words = "결제 내역"
        self.tn = ""
        self.cn = "결제 내역을 확인하세요."

    def intake(self):
        self.link = "equal-pet://navigation?scene=intake"
        self.digest_words = "복용 체크"
        self.tn = ""
        self.cn = "약 복용을 체크하세요."

    def shippingInfo(self):
        self.link = "equal-pet://navigation?scene=addressList"
        self.digest_words = "배송 정보 관리"
        self.tn = ""
        self.cn = "배송 정보를 관리하세요."

    def paymentInfo(self):
        self.link = "equal-pet://navigation?scene=paymentList"
        self.digest_words = "결제 관리"
        self.tn = ""
        self.cn = "결제 수단과 내역을 관리하세요."

    def notifications(self):
        self.link = "equal-pet://navigation?scene=notificationSetting"
        self.digest_words = "알림 설정"
        self.tn = ""
        self.cn = "알림 설정을 조정하세요."

    def account(self):
        self.link = "equal-pet://navigation?scene=accountSetting"
        self.digest_words = "계정 관리"
        self.tn = ""
        self.cn = "계정 설정을 관리하세요."

    def nutrientReport(self):
        self.link = "equal-pet://navigation?scene=producList"
        self.digest_words = "영양제 정보 리스트"
        self.tn = ""
        self.cn = "영양제 정보를 확인하세요."

    def default(self):
        """Default action if gbn is not recognized"""
        self.tn = "Notification"
        self.cn = "Details not available."

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
    })
    push_dto = PushDTO(**base_push_dto)

    push_url = 'http://dev.promptinsight.ai:10002/push-service/v1/admin/push'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    push_response = requests.post(push_url, headers=headers, json=vars(push_dto))
    return push_response.json()

# Example usage of pushing a notification
push_message = {
    'target': 2170,
    'state': 1,
    'gbn': 'petRegistration',
    'dtype': 'FCM',
    'pet_id': 361,
    'examId': None,
    'tn': 'Initial Title',
    'cn': 'Initial Content'
}

# Example usage of pushing a notification
push_message2 = {
    'target': 2170,
    'state': 1,
    'gbn': 'questionnaireComplete',
    'dtype': 'FCM',
    'pet_id': 361,
    'tn': 'questionnaire Complete'
}

push_message3 = {
    'target': 2746,
    'state': 1,
    'gbn': 'newArticle',
    'dtype': 'FCM',
    'contents_id': 123,
    'tn': 'a new Article'
}

response = send(push_message3)
print(response)